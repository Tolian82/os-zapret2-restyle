#!/usr/bin/env python3
"""Exact IPFW argv / read-only parsing tests for staged FreeBSD adapter."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
import subprocess

BACKEND = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_ipfw_adapter import (
    FreeBSDIPFWAdapter, IPFWAdapterError, checked_rule_argv,
)

VOICE = ["divert", "989", "udp", "from", "any", "to",
         "table(zapret2_voice_telegram)", "out", "not", "diverted",
         "not", "sockarg", "xmit", "vtnet1"]
TCP = ["divert", "989", "tcp", "from", "any", "to", "any", "443",
       "out", "not", "diverted", "not", "sockarg", "xmit", "vtnet1"]
UDP = ["divert", "989", "udp", "from", "any", "to", "any", "596-599",
       "out", "not", "diverted", "not", "sockarg", "xmit", "vtnet1"]

class SimulateFreeBSD:
    def __init__(self):
        self.operations = []
        self.rule_listing = "\n".join([
            "00001 allow ip from any to any",
            "19000 " + " ".join(VOICE),
            "19001 " + " ".join(TCP),
            "19002 " + " ".join(UDP),
            "65535 deny ip from any to any",
            "",
        ])
        self.table = ["91.108.0.0/16", "91.108.13.10"]
        self.table_output = None
        self.missing = False
        self.error = False

    def __call__(self, argv, **kwargs):
        self.operations.append(tuple(argv))
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        assert kwargs["timeout"] == 15
        if self.error:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="Permission denied")
        command = tuple(argv[1:])
        if command == ("-q", "list"):
            return subprocess.CompletedProcess(argv, 0, stdout=self.rule_listing, stderr="")
        if len(command) == 3 and command[:2] == ("table", "zapret2_voice_telegram"):
            if command[-1] == "info":
                if self.missing:
                    return subprocess.CompletedProcess(argv, 69, stdout="",
                                                       stderr="Table zapret2_voice_telegram does not exist")
                return subprocess.CompletedProcess(argv, 0, stdout="table type: addr\n", stderr="")
            if command[-1] == "list":
                listing = self.table_output
                if listing is None:
                    listing = "\n".join(v + " 0" for v in self.table) + "\n"
                return subprocess.CompletedProcess(argv, 0, stdout=listing, stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


class IPFWAdapterTests(unittest.TestCase):
    def test_reads_known_rules_without_treating_foreign_outside_range_as_ours(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=fake)
        self.assertEqual({19000: VOICE, 19001: TCP, 19002: UDP},
                         adapter.list_rules(19000, 19010))
        self.assertEqual(("/sbin/ipfw", "-q", "list"), fake.operations[0])

    def test_reads_bounded_known_ipv4_table(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=fake)
        self.assertEqual(fake.table, adapter.get_table("zapret2_voice_telegram"))
        fake.missing = True
        self.assertIsNone(adapter.get_table("zapret2_voice_telegram"))
        fake.missing = False
        fake.error = True
        with self.assertRaisesRegex(IPFWAdapterError, "command failed"):
            adapter.get_table("zapret2_voice_telegram")

    def test_foreign_rule_inside_owned_numeric_range_is_not_silently_parsed(self):
        fake = SimulateFreeBSD()
        fake.rule_listing += "19005 allow ip from any to any\n"
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=fake)
        with self.assertRaises(IPFWAdapterError):
            adapter.list_rules(19000,19010)
        fake.rule_listing = "19000 " + " ".join(VOICE) + "\n19000 " + " ".join(VOICE)
        with self.assertRaisesRegex(IPFWAdapterError, "duplicate"):
            adapter.list_rules(19000,19010)

    def test_table_parser_rejects_malformed_ipv6_duplicate_or_spurious_output(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000,19010,runner=fake)
        for value in ("2001:db8::1 0\n", "91.108.4.7/22 0\n",
                      "91.108.13.10\n91.108.13.10\n", "??? a:b\n"):
            fake.table_output = value
            with self.subTest(value=value):
                with self.assertRaises(IPFWAdapterError):
                    adapter.get_table("zapret2_voice_telegram")
        fake.table_output = "9.9.9.9 0\n"
        self.assertEqual(["9.9.9.9"],adapter.get_table("zapret2_voice_telegram"))

    def test_read_only_is_default_and_validate_before_touching_kernel(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000,19010,runner=fake)
        for invoke in (
            lambda:adapter.create_table("zapret2_voice_telegram_stage"),
            lambda:adapter.destroy_table("zapret2_voice_telegram"),
            lambda:adapter.swap_tables("zapret2_voice_telegram","zapret2_voice_telegram_stage"),
            lambda:adapter.add_table_entry("zapret2_voice_telegram_stage","91.108.13.10"),
            lambda:adapter.delete_rule(19000),
            lambda:adapter.add_rule(19000,VOICE),
        ):
            with self.subTest(invoke=invoke):
                with self.assertRaisesRegex(IPFWAdapterError, "read-only"):
                    invoke()
        self.assertEqual([],fake.operations)

    def test_mutating_adapter_uses_exact_safe_argv_and_refuses_arbitrary_shell(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000,19010,allow_mutations=True,runner=fake)
        adapter.create_table("zapret2_voice_telegram_stage")
        adapter.add_table_entry("zapret2_voice_telegram_stage","91.108.13.10")
        adapter.swap_tables("zapret2_voice_telegram","zapret2_voice_telegram_stage")
        adapter.add_rule(19000,VOICE)
        adapter.delete_rule(19000)
        adapter.destroy_table("zapret2_voice_telegram_stage")
        self.assertEqual([
            ("/sbin/ipfw","-q","table","zapret2_voice_telegram_stage","create","type","addr"),
            ("/sbin/ipfw","-q","table","zapret2_voice_telegram_stage","add","91.108.13.10"),
            ("/sbin/ipfw","-q","table","zapret2_voice_telegram","swap","zapret2_voice_telegram_stage"),
            ("/sbin/ipfw","-qf","add","19000",*VOICE),
            ("/sbin/ipfw","-q","delete","19000"),
            ("/sbin/ipfw","-q","table","zapret2_voice_telegram_stage","destroy"),
        ],fake.operations)
        operations = len(fake.operations)
        for invoke in (
            lambda:adapter.create_table("foreign"),
            lambda:adapter.delete_rule(19012),
            lambda:adapter.add_rule(19000, VOICE+[";rm -rf /"]),
            lambda:adapter.add_table_entry("zapret2_voice_telegram", "91.108.13.10;echo"),
            lambda:adapter.swap_tables("zapret2_voice_telegram_stage","zapret2_voice_telegram"),
            lambda:adapter.add_rule(19000,VOICE[:6]+["any"]+VOICE[7:]),
        ):
            with self.assertRaises(IPFWAdapterError):
                invoke()
        self.assertEqual(operations,len(fake.operations))

    def test_missing_table_only_on_specific_diagnostic_and_fail_closed(self):
        fake=SimulateFreeBSD()
        adapter=FreeBSDIPFWAdapter(19000,19010,runner=fake)
        fake.error=True
        with self.assertRaises(IPFWAdapterError):
            adapter.get_table("zapret2_voice_telegram")
        with self.assertRaises(IPFWAdapterError):
            adapter.list_rules(19000,19010)

if __name__ == "__main__":
    unittest.main(verbosity=2)
