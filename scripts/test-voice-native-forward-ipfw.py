#!/usr/bin/env python3
"""Shared IPFW PRECOMMIT fixture used by historical forward supervisor tests.

The independent forward-IPFW executor was never a normal entrypoint and is
retired. Reuse the existing production IPFW transaction API, exercising its
durable journal, reversible kernel state and failure/refusal behavior instead
of recreating a private Voice cutover path.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))

from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_ipfw_runtime import activate_verified, rollback_precommit_verified
from voice_firewall_transaction import plan_postcommit_cleanup
from voice_firewall_ledger import fingerprint, canonical_manifest


def source(name, mod):
    spec = importlib.util.spec_from_file_location(mod, ROOT / "scripts" / name)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


previous = source("test-voice-native-candidate-engine-start.py",
                  "forward_ipfw_engine_fixture")
transaction = source("test-voice-firewall-transaction.py",
                     "forward_ipfw_kernel_fixture")


class SimulatedNativeIPFW(FreeBSDIPFWAdapter):
    """Exact production adapter contract backed by fake kernel resources."""
    def __init__(self, kernel, *, mutable=False):
        super().__init__(19000, 19010, allow_mutations=mutable)
        self.kernel = kernel

    def list_rules(self, first, last):
        return self.kernel.list_rules(first, last)

    def get_table(self, name):
        return self.kernel.get_table(name)

    def create_table(self, name):
        assert self.allow_mutations
        return self.kernel.create_table(name)

    def destroy_table(self, name):
        assert self.allow_mutations
        return self.kernel.destroy_table(name)

    def add_table_entry(self, name, entry):
        assert self.allow_mutations
        return self.kernel.add_table_entry(name, entry)

    def swap_tables(self, active, stage):
        assert self.allow_mutations
        return self.kernel.swap_tables(active, stage)

    def delete_rule(self, number):
        assert self.allow_mutations
        return self.kernel.delete_rule(number)

    def add_rule(self, number, argv):
        assert self.allow_mutations
        return self.kernel.add_rule(number, argv)


class ForwardIPFWTests(unittest.TestCase):
    """Fixture API retained for supervisor/Config historical test consumers."""
    def setUp(self):
        self.phase = previous.CandidateEngineStartTests()
        self.phase.setUp()
        self.addCleanup(self.phase.doCleanups)
        self.phase.call()
        self.fx = self.phase.fx
        self.old = self.fx.ipfw.owned()
        self.desired = self.phase.previous.parent.manifest
        self.kernel = transaction.FakeIPFW(self.old["rules"], self.old["tables"])
        self.read = SimulatedNativeIPFW(self.kernel)
        self.write = SimulatedNativeIPFW(self.kernel, mutable=True)

    def proof(self):
        return {
            "native_argv_sha256":
                self.fx.whole.read()["candidate"]["native_argv_sha256"]
        }

    def call(self, *, desired=None, proof=None):
        return activate_verified(
            self.fx.ipfw, self.write,
            self.desired if desired is None else desired,
            self.fx.whole, self.proof() if proof is None else proof,
        )

    def test_shared_ipfw_precommit_keeps_previous_ownership_and_stage(self):
        result = self.call()
        self.assertEqual("installed-pending-whole-commit", result)
        self.assertEqual("mutating", self.fx.whole.read()["phase"])
        self.assertEqual(self.old, self.fx.ipfw.owned())
        pending = self.fx.ipfw.pending()
        self.assertEqual("mutating", pending["phase"])
        self.assertEqual(fingerprint(canonical_manifest(self.desired)),
                         pending["desired_sha256"])
        self.assertEqual(self.desired["rules"],
                         self.kernel.list_rules(19000, 19010))
        self.assertEqual(self.desired["tables"]["zapret2_voice_telegram"],
                         self.kernel.get_table("zapret2_voice_telegram"))
        self.assertIsNotNone(
            self.kernel.get_table("zapret2_voice_telegram_stage"))
        plan_postcommit_cleanup(self.write, self.old, self.desired)
        self.assertEqual("engine-only",
                         self.phase.probe.observe_candidate_engine_only()["state"])

    def test_shared_ipfw_precommit_rolls_back_after_candidate_stop(self):
        self.call()
        self.phase.engine_pid = None
        self.phase.reader.commands = {}
        self.assertEqual("stopped",
                         self.phase.probe.observe_candidate_engine_only()["state"])
        result = rollback_precommit_verified(
            self.fx.ipfw, self.write, self.fx.whole, self.proof())
        self.assertEqual("restored-previous", result)
        self.assertEqual(self.old["rules"],
                         self.kernel.list_rules(19000, 19010))
        self.assertIsNone(self.kernel.get_table("zapret2_voice_telegram"))
        self.assertIsNone(self.kernel.get_table("zapret2_voice_telegram_stage"))
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual("mutating", self.fx.whole.read()["phase"])

    def test_shared_ipfw_mutation_failure_restores_previous(self):
        self.kernel.failure = "add_rule"
        with self.assertRaises((ValueError, RuntimeError, OSError)):
            self.call()
        self.assertEqual(self.old, self.fx.ipfw.owned())
        self.assertEqual(self.old["rules"],
                         self.kernel.list_rules(19000, 19010))
        self.assertFalse(self.kernel.tables)
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertEqual("mutating", self.fx.whole.read()["phase"])

    def test_foreign_desired_manifest_refused_before_kernel_write(self):
        wrong = {**self.desired, "rules": {
            19000: [*self.desired["rules"][19000][:1], "990",
                    *self.desired["rules"][19000][2:]]
        }}
        with self.assertRaises((ValueError, RuntimeError, OSError)):
            self.call(desired=wrong)
        self.assertFalse(self.kernel.ops)
        self.assertIsNone(self.fx.ipfw.pending())

    def test_foreign_prior_kernel_refused_before_ledger_write(self):
        self.kernel.rules[19005] = [
            "divert", "989", "udp", "from", "any", "to", "any", "596",
            "out", "not", "diverted", "not", "sockarg", "xmit", "vtnet1",
        ]
        with self.assertRaises((ValueError, RuntimeError, OSError)):
            self.call()
        self.assertIsNone(self.fx.ipfw.pending())
        self.assertFalse(self.kernel.ops)

    def test_existing_pending_intent_refuses_duplicate_activation(self):
        self.call()
        with self.assertRaises((ValueError, RuntimeError, OSError)):
            self.call()
        self.assertEqual("mutating", self.fx.whole.read()["phase"])
        self.assertEqual("mutating", self.fx.ipfw.pending()["phase"])
        self.assertEqual(self.desired["rules"],
                         self.kernel.list_rules(19000, 19010))


if __name__ == "__main__":
    unittest.main(verbosity=2)
