#!/usr/bin/env python3
"""Integration of production Voice IPFW lifecycle entry and owned kernel adapter.

The production executor uses FreeBSD IPFW; CI injects FakeIPFW to exercise
the same ownership and journal operations, never contacting the kernel.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
spec = importlib.util.spec_from_file_location(
    "transaction_fixtures", ROOT / "scripts/test-voice-firewall-transaction.py"
)
assert spec and spec.loader
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)

from voice_firewall_ledger import VoiceOwnershipStore
from voice_cutover_journal import VoiceCutoverJournal
import voice_ipfw_runtime as runtime

FakeIPFW = fixtures.FakeIPFW
manifest = fixtures.fixture


class NativeIPFWExecutor(unittest.TestCase):
    def stores(self, root):
        ipfw = root / "voice-ipfw"
        cutover = root / "voice-cutover"
        ipfw.mkdir(mode=0o700)
        cutover.mkdir(mode=0o700)
        return VoiceOwnershipStore(ipfw), VoiceCutoverJournal(cutover)

    def proof(self):
        return {
            "saved_xml_sha256": "a" * 64,
            "merged_sha256": "b" * 64,
            "native_argv_sha256": "c" * 64,
        }

    def cutover(self, journal, desired):
        previous = {key: "d" * 64 for key in
                    ("config", "runtime", "engine", "firewall", "supervisor")}
        journal.begin_bound(previous, self.proof(), desired)
        journal.mark_mutating()

    def test_verified_ordinary_seed_and_idempotent_seed(self):
        old = manifest()
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.stores(Path(directory))
            adapter = FakeIPFW(old["rules"], old["tables"])
            self.assertEqual("seeded", runtime.seed_verified(store, adapter, old))
            self.assertEqual("already-owned", runtime.seed_verified(store, adapter, old))
            self.assertEqual(old, store.owned())
            self.assertEqual([], adapter.ops)

    def test_foreign_kernel_rule_blocks_seed_before_mutation(self):
        old = manifest()
        foreign = dict(old["rules"])
        foreign[19005] = ["allow", "ip", "from", "any", "to", "any"]
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.stores(Path(directory))
            adapter = FakeIPFW(foreign, old["tables"])
            with self.assertRaisesRegex(Exception, "foreign"):
                runtime.seed_verified(store, adapter, old)
            self.assertIsNone(store.owned())
            self.assertEqual([], adapter.ops)

    def test_bound_cutover_installs_scoped_rules_and_cleans_stage(self):
        old = manifest()
        desired = manifest(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as directory:
            store, journal = self.stores(Path(directory))
            adapter = FakeIPFW(old["rules"], old["tables"])
            runtime.seed_verified(store, adapter, old)
            self.cutover(journal, desired)
            result = runtime.activate_verified(store, adapter, desired, journal, self.proof())
            self.assertEqual("installed-pending-whole-commit", result)
            self.assertEqual(old, store.owned(), "ownership must NOT commit before supervisor")
            self.assertEqual("mutating", store.pending()["phase"])
            self.assertEqual(desired["rules"], adapter.rules)
            self.assertEqual(desired["tables"]["zapret2_voice_telegram"],
                             adapter.tables["zapret2_voice_telegram"])
            self.assertIn("zapret2_voice_telegram_stage", adapter.tables,
                          "prior Voice table snapshot remains until overall commit")
            self.assertEqual("mutating", journal.read()["phase"])
            self.assertTrue(adapter.ops)
            with self.assertRaisesRegex(runtime.VoiceKernelRuntimeError, "cutover"):
                runtime.commit_verified(store, adapter, journal, self.proof())
            self.assertEqual(old, store.owned())
            journal.commit()
            self.assertEqual("committed", runtime.commit_verified(
                store, adapter, journal, self.proof()))
            self.assertEqual(desired, store.owned())
            self.assertIsNone(store.pending())
            self.assertEqual(desired["rules"], adapter.rules)
            self.assertEqual(desired["tables"], adapter.tables)
            self.assertFalse(any(name.endswith("_stage") for name in adapter.tables))

    def test_supervisor_failure_can_restore_previous_ipfw_before_commit(self):
        old = manifest()
        desired = manifest(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as directory:
            store, journal = self.stores(Path(directory))
            adapter = FakeIPFW(old["rules"], old["tables"])
            runtime.seed_verified(store, adapter, old)
            self.cutover(journal, desired)
            runtime.activate_verified(store, adapter, desired, journal, self.proof())
            self.assertEqual("restored-previous", runtime.rollback_precommit_verified(
                store, adapter, journal, self.proof()))
            self.assertEqual(old["rules"], adapter.rules)
            self.assertEqual(old["tables"], adapter.tables)
            self.assertEqual(old, store.owned())
            self.assertIsNone(store.pending())
            self.assertEqual("mutating", journal.read()["phase"],
                             "whole transaction still needs complete rollback verification")
            # The original whole-journal abort is intentionally a separate
            # overall Config/engine/supervisor verification step.

    def test_precommit_rollback_refuses_foreign_rules_and_keeps_journal(self):
        old = manifest()
        desired = manifest(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as directory:
            store, journal = self.stores(Path(directory))
            adapter = FakeIPFW(old["rules"], old["tables"])
            runtime.seed_verified(store, adapter, old)
            self.cutover(journal, desired)
            runtime.activate_verified(store, adapter, desired, journal, self.proof())
            adapter.rules[19005] = ["allow", "ip", "from", "any", "to", "any"]
            before = list(adapter.ops)
            with self.assertRaisesRegex(Exception, "differ|foreign|mismatch"):
                runtime.rollback_precommit_verified(store, adapter, journal, self.proof())
            self.assertEqual(before, adapter.ops)
            self.assertIsNotNone(store.pending())
            self.assertIn(19005, adapter.rules)

    def test_precommit_second_activation_is_refused_before_kernel_changes(self):
        old = manifest()
        desired = manifest(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as directory:
            store, journal = self.stores(Path(directory))
            adapter = FakeIPFW(old["rules"], old["tables"])
            runtime.seed_verified(store, adapter, old)
            self.cutover(journal, desired)
            runtime.activate_verified(store, adapter, desired, journal, self.proof())
            before = list(adapter.ops)
            with self.assertRaisesRegex(runtime.VoiceKernelRuntimeError, "pending"):
                runtime.activate_verified(store, adapter, desired, journal, self.proof())
            self.assertEqual(before, adapter.ops)

    def test_change_existing_voice_ipset_can_rollback_with_exact_old_contents(self):
        old = manifest(("telegram", "91.108.0.0/16"))
        desired = manifest(("telegram", "91.108.13.10"))
        with tempfile.TemporaryDirectory() as directory:
            store, journal = self.stores(Path(directory))
            adapter = FakeIPFW(old["rules"], old["tables"])
            runtime.seed_verified(store, adapter, old)
            self.cutover(journal, desired)
            runtime.activate_verified(store, adapter, desired, journal, self.proof())
            self.assertEqual(["91.108.0.0/16"],
                             adapter.tables["zapret2_voice_telegram_stage"])
            self.assertEqual(["91.108.13.10"],
                             adapter.tables["zapret2_voice_telegram"])
            self.assertEqual("restored-previous", runtime.rollback_precommit_verified(
                store, adapter, journal, self.proof()))
            self.assertEqual(old["rules"], adapter.rules)
            self.assertEqual(old["tables"], adapter.tables)
            self.assertIsNone(store.pending())

    def test_wrong_journal_or_candidate_does_not_mutate_kernel(self):
        old = manifest()
        desired = manifest(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as directory:
            store, journal = self.stores(Path(directory))
            adapter = FakeIPFW(old["rules"], old["tables"])
            runtime.seed_verified(store, adapter, old)
            with self.assertRaisesRegex(runtime.VoiceKernelRuntimeError, "cutover"):
                runtime.activate_verified(store, adapter, desired, journal, self.proof())
            self.cutover(journal, desired)
            changed = self.proof()
            changed["native_argv_sha256"] = "0" * 64
            with self.assertRaisesRegex(runtime.VoiceKernelRuntimeError, "cutover"):
                runtime.activate_verified(store, adapter, desired, journal, changed)
            self.assertEqual([], adapter.ops)
            self.assertEqual(old, store.owned())

    def test_native_cli_cannot_run_without_production_freebsd_fd9(self):
        with self.assertRaises(Exception):
            runtime.require_native_lock()

    def test_service_dispatch_holds_real_lifecycle_lock(self):
        source = (BACKEND.parent / "zapret_service.sh").read_text(encoding="utf-8")
        self.assertIn("native_voice_ipfw_dispatch()", source)
        self.assertIn("native_voice_ipfw_dispatch seed", source)
        self.assertIn("native_voice_ipfw_dispatch activate", source)
        self.assertIn("native_voice_ipfw_dispatch commit", source)
        self.assertIn("native_voice_ipfw_dispatch rollback", source)
        self.assertIn("voice_ipfw_runtime.py", source)
        self.assertIn("service_with_lifecycle_lock", source)
        self.assertIn("native-voice-ipfw-seed|native-voice-ipfw-activate", source)
        self.assertNotIn("native-voice-ipfw-activate", (ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/voice.volt").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
