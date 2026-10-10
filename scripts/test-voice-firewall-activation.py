#!/usr/bin/env python3
"""Simulated Voice IPFW/journal activation across repeated reconfigure and crash."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

transaction_tests = load(ROOT / "scripts/test-voice-firewall-transaction.py",
                         "transaction_mock_fixtures")
import voice_firewall_activation as activation
import voice_firewall_ledger as ledger
import voice_firewall_transaction as transaction
FakeIPFW = transaction_tests.FakeIPFW
fixture = transaction_tests.fixture


class ActivationSequenceTests(unittest.TestCase):
    def ledger(self, path):
        directory = Path(path) / "ipfw-ledger"
        directory.mkdir(mode=0o700)
        return ledger.VoiceOwnershipStore(directory)

    def test_off_on_change_off_is_repeatable_without_orphan_stages(self):
        old = fixture()
        telegram = fixture(("telegram", "91.108.0.0/16"))
        both = fixture(("telegram", "91.108.0.0/16"),
                       ("discord", "203.0.113.0/24"))
        adapter = FakeIPFW(old["rules"], old["tables"])
        with tempfile.TemporaryDirectory() as tmp:
            store = self.ledger(tmp)
            store.seed(old)
            for previous, wanted in [(old, telegram), (telegram, both),
                                     (both, telegram), (telegram, old)]:
                activation.activate_mockable(adapter, store, previous, wanted)
                self.assertEqual(wanted, store.owned())
                self.assertIsNone(store.pending())
                self.assertEqual(wanted["rules"], adapter.list_rules(19000, 19010))
                self.assertEqual(wanted["tables"], adapter.tables)
                self.assertFalse(any(n.endswith("_stage") for n in adapter.tables))
            self.assertEqual(old, store.owned())

    def test_failing_rules_or_table_change_preserves_old_and_clears_intent(self):
        prev = fixture()
        nxt = fixture(("telegram", "91.108.0.0/16"))
        for injected in ("create_table", "add_table_entry", "swap_tables",
                         "delete_rule", "add_rule"):
            with self.subTest(injected=injected), tempfile.TemporaryDirectory() as tmp:
                store = self.ledger(tmp)
                store.seed(prev)
                adapter = FakeIPFW(prev["rules"],prev["tables"],failure=injected)
                with self.assertRaises(transaction.VoiceFirewallError):
                    activation.activate_mockable(adapter,store,prev,nxt)
                self.assertEqual(prev,store.owned())
                self.assertIsNone(store.pending())
                self.assertEqual(prev["rules"],adapter.list_rules(19000,19010))
                self.assertEqual(prev["tables"],adapter.tables)

    def test_foreign_rule_rejected_before_intent_or_mutation(self):
        prev, nxt = fixture(), fixture(("telegram", "91.108.0.0/16"))
        foreign = dict(prev["rules"])
        foreign[19005] = ["allow", "ip", "from", "any", "to", "any"]
        with tempfile.TemporaryDirectory() as tmp:
            store = self.ledger(tmp)
            store.seed(prev)
            adapter = FakeIPFW(foreign, prev["tables"])
            with self.assertRaisesRegex(transaction.VoiceFirewallError, "foreign"):
                activation.activate_mockable(adapter, store, prev, nxt)
            self.assertEqual([],adapter.ops)
            self.assertIsNone(store.pending())
            self.assertIn(19005,adapter.rules)

    def test_cleanup_error_preserves_committed_intent_for_restart_review(self):
        prev, nxt = fixture(), fixture(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as tmp:
            store = self.ledger(tmp)
            store.seed(prev)
            adapter = FakeIPFW(prev["rules"],prev["tables"],failure="destroy_table")
            with self.assertRaises(OSError):
                activation.activate_mockable(adapter,store,prev,nxt)
            self.assertEqual(nxt,store.owned())
            self.assertIsNotNone(store.pending())
            reopened = ledger.VoiceOwnershipStore(store.directory)
            self.assertEqual("manual-review",reopened.inspect(adapter))
            adapter.failure = None
            transaction.cleanup_committed(adapter,prev,nxt)
            self.assertEqual("desired-intact",reopened.inspect(adapter))
            reopened.finish(adapter)
            self.assertIsNone(reopened.pending())

    def test_pre_mutation_crash_allows_verified_abort_but_no_forced_commit(self):
        prev, nxt = fixture(), fixture(("telegram", "91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as tmp:
            store = self.ledger(tmp)
            store.seed(prev)
            store.begin(prev,nxt)  # restart occurs before mark_mutating
            restarted = ledger.VoiceOwnershipStore(store.directory)
            adapter = FakeIPFW(prev["rules"],prev["tables"])
            with self.assertRaisesRegex(transaction.VoiceFirewallError,"pending"):
                activation.activate_mockable(adapter,restarted,prev,nxt)
            restarted.abort(adapter)
            self.assertIsNone(restarted.pending())
            activation.activate_mockable(adapter,restarted,prev,nxt)
            self.assertEqual(nxt,restarted.owned())

    def test_partial_kernel_restart_remains_manual_only(self):
        prev, nxt = fixture(), fixture(("telegram","91.108.0.0/16"))
        with tempfile.TemporaryDirectory() as tmp:
            store = self.ledger(tmp)
            store.seed(prev)
            store.begin(prev,nxt)
            store.mark_mutating()
            adapter = FakeIPFW(prev["rules"],prev["tables"])
            adapter.rules[19000] = nxt["rules"][19000]
            self.assertEqual("manual-review",store.inspect(adapter))
            with self.assertRaisesRegex(ledger.LedgerError,"cannot abort"):
                store.abort(adapter)
            with self.assertRaisesRegex(ledger.LedgerError,"cannot finish"):
                store.finish(adapter)
            self.assertIsNotNone(store.pending())

if __name__ == "__main__":
    unittest.main(verbosity=2)
