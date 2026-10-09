#!/usr/bin/env python3
"""Simulate Voice IPFW transaction failure injection without touching kernel."""
import importlib.util
from pathlib import Path
import sys
import unittest
from copy import deepcopy

BACKEND = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
def load(name):
    spec = importlib.util.spec_from_file_location(name, BACKEND / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

transaction = load("voice_firewall_transaction")
capture = load("voice_capture_plan")
compiler = load("voice_profile_compiler")
MANAGED = Path("/usr/local/etc/zapret2/runtime-v2/managed")
ARGS = "--filter-udp=*\n--filter-l7=stun\n--payload=stun"

class FakeIPFW:
    def __init__(self, rules=None, tables=None, failure=None):
        self.rules = deepcopy(rules or {})
        self.tables = deepcopy(tables or {})
        self.failure = failure
        self.failed = False
        self.ops = []
    def _try(self, op):
        self.ops.append(op)
        if op == self.failure and not self.failed:
            self.failed = True
            raise OSError(f"simulated failure: {op}")
    def list_rules(self, first, last):
        return {number: deepcopy(argv) for number, argv in self.rules.items() if first <= number <= last}
    def get_table(self, name):
        return deepcopy(self.tables.get(name))
    def create_table(self, name):
        self._try("create_table")
        if name in self.tables:
            raise OSError("IPFW table already exists")
        self.tables[name] = []
    def destroy_table(self, name):
        self._try("destroy_table")
        self.tables.pop(name, None)
    def add_table_entry(self, name, value):
        self._try("add_table_entry")
        self.tables[name].append(value)
    def swap_tables(self, active, stage):
        self._try("swap_tables")
        self.tables[active], self.tables[stage] = self.tables[stage], self.tables[active]
    def delete_rule(self, number):
        self._try("delete_rule")
        self.rules.pop(number, None)
    def add_rule(self, number, argv):
        self._try("add_rule")
        if number in self.rules:
            raise OSError("rule number collision")
        self.rules[number] = deepcopy(argv)

def fixture(*services):
    data = {
        "strategy_wan":"WAN", "voice_wan":"",
        "services":{s:{"enabled":False,"args":"","ips":""} for s in compiler.SERVICES}
    }
    for name, ips in services:
        data["services"][name] = {"enabled":True,"args":ARGS,"ips":ips}
    _, profile = compiler.compile_candidate(data, MANAGED)
    plan = capture.compile_capture_plan(profile, 19000, 19010, 989, physical_wan="vtnet1")
    return transaction.prepare_desired(plan, "443", "596-599")

class VoiceFirewallTransactionTests(unittest.TestCase):
    def test_first_activation_produces_scoped_ipfw_and_keeps_old_ordinary(self):
        previous = fixture()
        desired = fixture(("telegram","91.108.0.0/16"))
        adapter = FakeIPFW(rules=previous["rules"],tables=previous["tables"])
        transaction.apply_transaction(adapter, previous, desired)
        self.assertEqual(desired["rules"], adapter.list_rules(19000,19010))
        self.assertEqual(["91.108.0.0/16"],adapter.get_table("zapret2_voice_telegram"))
        self.assertEqual([], adapter.get_table("zapret2_voice_telegram_stage"))
        self.assertNotIn("to", [])
        self.assertIn("table(zapret2_voice_telegram)", adapter.rules[19000])
        self.assertEqual("tcp", adapter.rules[19001][2])
        self.assertEqual("udp", adapter.rules[19002][2])

    def test_failed_ipfw_operations_restore_rules_and_all_new_tables(self):
        previous = fixture()
        desired = fixture(("telegram","91.108.0.0/16"))
        for step in ("create_table","add_table_entry","swap_tables","delete_rule","add_rule"):
            with self.subTest(step=step):
                adapter = FakeIPFW(previous["rules"],previous["tables"],failure=step)
                with self.assertRaisesRegex(transaction.VoiceFirewallError,"previous owned state restored"):
                    transaction.apply_transaction(adapter,previous,desired)
                self.assertEqual(previous["rules"], adapter.list_rules(19000,19010))
                self.assertIsNone(adapter.get_table("zapret2_voice_telegram"))
                self.assertIsNone(adapter.get_table("zapret2_voice_telegram_stage"))

    def test_existing_active_table_restored_after_failed_replacement(self):
        previous = fixture(("telegram","91.108.0.0/16"))
        desired = fixture(("telegram","91.108.4.0/22"))
        adapter = FakeIPFW(previous["rules"],previous["tables"],failure="add_rule")
        with self.assertRaisesRegex(transaction.VoiceFirewallError,"restored"):
            transaction.apply_transaction(adapter,previous,desired)
        self.assertEqual(previous["rules"], adapter.rules)
        self.assertEqual(["91.108.0.0/16"],adapter.get_table("zapret2_voice_telegram"))
        self.assertIsNone(adapter.get_table("zapret2_voice_telegram_stage"))

    def test_multiple_tables_swapped_and_rolled_back_atomically(self):
        previous=fixture(("telegram","91.108.0.0/16"))
        desired=fixture(("telegram","91.108.4.0/22"),("discord","203.0.113.0/24"))
        adapter=FakeIPFW(previous["rules"],previous["tables"],failure="add_rule")
        with self.assertRaisesRegex(transaction.VoiceFirewallError,"restored"):
            transaction.apply_transaction(adapter,previous,desired)
        self.assertEqual(previous["rules"],adapter.rules)
        self.assertEqual(["91.108.0.0/16"],adapter.get_table("zapret2_voice_telegram"))
        for name in ("zapret2_voice_telegram_stage","zapret2_voice_discord",
                     "zapret2_voice_discord_stage"):
            self.assertIsNone(adapter.get_table(name))

    def test_conflicts_refused_before_destructive_work(self):
        previous=fixture()
        desired=fixture(("telegram","91.108.0.0/16"))
        samples=[
            FakeIPFW({19000:["allow","ip","from","any","to","any"]}),
            FakeIPFW(previous["rules"],{"zapret2_voice_telegram":["1.1.1.1"]}),
            FakeIPFW(previous["rules"],{"zapret2_voice_telegram_stage":[]}),
        ]
        for adapter in samples:
            with self.subTest(state=(adapter.rules,adapter.tables)):
                before=(deepcopy(adapter.rules),deepcopy(adapter.tables))
                with self.assertRaises(transaction.VoiceFirewallError):
                    transaction.apply_transaction(adapter,previous,desired)
                self.assertEqual(before,(adapter.rules,adapter.tables))
                self.assertFalse(adapter.ops)

    def test_foreign_rules_outside_plugin_owned_range_untouched(self):
        previous=fixture()
        desired=fixture(("telegram","91.108.0.0/16"))
        live=dict(previous["rules"])
        live[18500]=["allow","ip","from","any","to","any"]
        adapter=FakeIPFW(live,previous["tables"])
        transaction.apply_transaction(adapter,previous,desired)
        self.assertEqual(["allow","ip","from","any","to","any"],adapter.rules[18500])

    def test_reject_invalid_rule_plan_without_transport_access(self):
        good=fixture(("telegram","91.108.0.0/16"))
        bad=deepcopy(good)
        bad["rules"][19000][6] = "any"
        # The underlying capture argv is checked when preparing desired.
        profile = {
            "schema":1,"wan":"vtnet1","divert_port":989,
            "rule_base":19000,"rule_max":19010,"ordinary_rule_base":19001,
            "voice":[{
                "service":"telegram","rule":19000,"table":"zapret2_voice_telegram",
                "argv":bad["rules"][19000],"destinations":["91.108.0.0/16"],
                "destination_count":1
            }]
        }
        with self.assertRaisesRegex(transaction.VoiceFirewallError,"outside destination-scoped"):
            transaction.prepare_desired(profile,"443","596-599")
        profile["voice"][0]["argv"]=good["rules"][19000]
        profile["voice"][0]["destinations"]=["1.1.1.1;rm"]
        with self.assertRaisesRegex(transaction.VoiceFirewallError,"IPv4"):
            transaction.prepare_desired(profile,"443","596-599")
        with self.assertRaisesRegex(transaction.VoiceFirewallError,"neither TCP nor UDP"):
            transaction.prepare_desired({**profile,"voice":[],"ordinary_rule_base":19000},"","")

if __name__ == "__main__":
    unittest.main(verbosity=2)
