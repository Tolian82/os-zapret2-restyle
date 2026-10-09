#!/usr/bin/env python3
"""Read-only live Voice IPFW inspection with fake kernel and durable journal."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from voice_live_inspect import examine
from voice_firewall_ledger import VoiceOwnershipStore
from voice_firewall_transaction import VoiceFirewallError
import importlib.util
fixture_path=ROOT / "scripts/test-voice-firewall-transaction.py"
spec=importlib.util.spec_from_file_location("voice_fixture_for_probe", fixture_path)
fixture_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
fixtures=fixture_module.fixture

class FakeAdapter:
    def __init__(self, manifest):
        self.rule_base = manifest["rule_base"]
        self.rule_max = manifest["rule_max"]
        self.rules = dict(manifest["rules"])
        self.tables = {name: list(entries) for name, entries in manifest["tables"].items()}
        self.operations = []
    def list_rules(self, first, last):
        self.operations.append("read-rules")
        return self.rules.copy()
    def get_table(self, name):
        self.operations.append("read-table")
        return self.tables.get(name)

class InspectionTests(unittest.TestCase):
    def states(self, tmp):
        folder = Path(tmp) / "ledger"
        folder.mkdir(mode=0o700)
        store = VoiceOwnershipStore(folder)
        previous = fixtures()
        desired = fixtures(("telegram", "91.108.0.0/16"))
        return store,previous,desired
    def test_uninitialized_never_adopts_existing_rules(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            kernel=FakeAdapter(old)
            self.assertEqual("uninitialized",examine(store,kernel)["state"])
            self.assertEqual([],kernel.operations)
    def test_verified_clean_owned_is_ready(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            kernel=FakeAdapter(old)
            self.assertEqual("ready",examine(store,kernel)["state"])
            self.assertTrue(examine(store,kernel)["can_activate"])
            self.assertTrue(all(op.startswith("read-") for op in kernel.operations))
    def test_foreign_rule_and_table_block(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            kernel=FakeAdapter(old)
            kernel.rules[19005]=["allow","ip","from","any","to","any"]
            self.assertEqual("foreign-or-modified-rules",examine(store,kernel)["state"])
            kernel.rules.pop(19005)
            kernel.tables["zapret2_voice_telegram"]=["8.8.8.8"]
            self.assertEqual("foreign-or-modified-table",examine(store,kernel)["state"])
            kernel.tables.pop("zapret2_voice_telegram")
            kernel.tables["zapret2_voice_telegram_stage"]=[]
            self.assertEqual("orphan-stage-table",examine(store,kernel)["state"])
    def test_interrupted_previous_or_partial_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old);store.begin(old,new);store.mark_mutating()
            kernel=FakeAdapter(old)
            report=examine(store,kernel)
            self.assertEqual("interrupted",report["state"])
            self.assertEqual("previous-intact",report["condition"])
            self.assertFalse(report["can_activate"])
            kernel.rules[19000]=new["rules"][19000]
            self.assertEqual("manual-review",examine(store,kernel)["condition"])
            self.assertTrue(all(op.startswith("read-") for op in kernel.operations))
    def test_different_rule_range_denied(self):
        with tempfile.TemporaryDirectory() as d:
            store,old,new=self.states(d)
            store.seed(old)
            kernel=FakeAdapter(old)
            kernel.rule_base=19200
            self.assertEqual("mismatched-range",examine(store,kernel)["state"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
