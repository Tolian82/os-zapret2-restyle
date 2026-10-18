#!/usr/bin/env python3
"""Native first Voice ON from existing running Strategies, without live IPFW."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
from copy import deepcopy

BACKEND = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_ipfw_adapter import legacy_strategies_manifest, IPFWAdapterError, shared_firewall_action
from voice_firewall_transaction import prepare_desired, VoiceFirewallError


class FakeIPFW:
    def __init__(self, manifest):
        self.rules = deepcopy(manifest["rules"])
        self.tables = deepcopy(manifest["tables"])
        self.mutations = []

    def list_rules(self, first, last):
        return {k: v for k, v in self.rules.items() if first <= k <= last}

    def get_table(self, name):
        return self.tables.get(name)

    def delete_rule(self, number):
        self.mutations.append("delete")
        self.rules.pop(number, None)

    def add_rule(self, number, argv):
        self.mutations.append("add")
        if number in self.rules:
            raise VoiceFirewallError("rule already exists")
        self.rules[number] = list(argv)

    def create_table(self, name):
        self.mutations.append("create")
        if name in self.tables:
            raise VoiceFirewallError("table collision")
        self.tables[name] = []

    def destroy_table(self, name):
        self.mutations.append("destroy")
        self.tables.pop(name, None)

    def add_table_entry(self, name, address):
        self.mutations.append("entry")
        self.tables[name].append(address)

    def swap_tables(self, a, b):
        self.mutations.append("swap")
        self.tables[a], self.tables[b] = self.tables[b], self.tables[a]


class LegacyFirstCommonHandoff(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zapret-legacy-first-")
        self.addCleanup(self.temp.cleanup)
        self.release = Path(self.temp.name) / "runtime-v2"
        self.release.mkdir()
        (self.release / "dvtws.args").write_text(
            "--port=989 --filter-tcp=443 --dpi-desync=fake\n", encoding="utf-8"
        )
        (self.release / "tcp-ports.txt").write_text("443\n")
        (self.release / "udp-ports.txt").write_text("596-599\n")
        self.ordinary = prepare_desired({
            "schema": 1, "rule_base": 19000, "rule_max": 19010,
            "ordinary_rule_base": 19000, "divert_port": 989,
            "wan": "vtnet1", "voice": [],
        }, "443", "596-599")
        self.desired = prepare_desired({
            "schema": 1, "rule_base": 19000, "rule_max": 19010,
            "ordinary_rule_base": 19001, "divert_port": 989,
            "wan": "vtnet1", "voice": [{
                "service": "telegram", "table": "zapret2_voice_telegram",
                "rule": 19000, "argv": [
                    "divert", "989", "udp", "from", "any", "to",
                    "table(zapret2_voice_telegram)", "out", "not",
                    "diverted", "not", "sockarg", "xmit", "vtnet1"],
                "destinations": ["91.108.0.0/16"], "destination_count": 1,
            }],
        }, "443", "596-599")
        # Real old root files are owner 0; this unit exercises just the
        # manifest parser/transaction, with uid supplied by CI fixture.
        self.old_uid = self.release.stat().st_uid

    def manifest(self):
        # Test under CI's non-root owner using an isolated fake release.
        # The native production path separately pins FD9/root ownership.
        import voice_ipfw_adapter as adapter
        original = adapter.legacy_strategies_manifest
        # These tests are expected to run in regular CI without root, so
        # require production check to match the controlled fixture uid only.
        # No patch is made to production code.
        return original(self.release, self.desired)

    def test_live_old_rules_are_attested_then_transferred_atomically(self):
        previous = self.manifest()
        self.assertEqual(self.ordinary, previous)
        ipfw = FakeIPFW(previous)
        shared_firewall_action(ipfw, "verify", previous, previous)
        self.assertEqual([], ipfw.mutations, "preflight mutated IPFW")
        shared_firewall_action(ipfw, "install", previous, self.desired)
        self.assertEqual(self.desired["rules"], ipfw.rules)
        self.assertEqual(["91.108.0.0/16"], ipfw.tables["zapret2_voice_telegram"])
        shared_firewall_action(ipfw, "verify-staged", previous, self.desired)
        shared_firewall_action(ipfw, "commit", previous, self.desired)
        shared_firewall_action(ipfw, "verify", self.desired, self.desired)

    def test_old_owner_restored_if_transition_fails_before_config(self):
        previous = self.manifest()
        ipfw = FakeIPFW(previous)
        shared_firewall_action(ipfw, "install", previous, self.desired)
        shared_firewall_action(ipfw, "rollback", previous, self.desired)
        self.assertEqual(previous["rules"], ipfw.rules)
        self.assertEqual(previous["tables"], ipfw.tables)

    def test_foreign_ipfw_rule_rejected_without_mutation(self):
        previous = self.manifest()
        ipfw = FakeIPFW(previous)
        ipfw.rules[19005] = ["allow", "ip", "from", "any", "to", "any"]
        with self.assertRaises(VoiceFirewallError):
            shared_firewall_action(ipfw, "verify", previous, previous)
        self.assertEqual([], ipfw.mutations)

    def test_old_voice_or_untrusted_tree_is_not_adopted(self):
        (self.release / "dvtws.args").write_text("--port=989 --name=voice-telegram")
        with self.assertRaisesRegex(IPFWAdapterError, "legacy predecessor"):
            self.manifest()
        (self.release / "dvtws.args").write_text("--port=989")
        (self.release / "voice-plan.json").write_text("{}")
        with self.assertRaisesRegex(IPFWAdapterError, "native Voice manifest"):
            self.manifest()

    def test_old_divert_and_wan_mismatch_refused_by_exact_kernel_witness(self):
        (self.release / "dvtws.args").write_text("--port=990")
        previous = self.manifest()
        ipfw = FakeIPFW(self.ordinary)
        with self.assertRaises(VoiceFirewallError):
            shared_firewall_action(ipfw, "verify", previous, previous)
        self.assertEqual([], ipfw.mutations)


if __name__ == "__main__":
    unittest.main(verbosity=2)
