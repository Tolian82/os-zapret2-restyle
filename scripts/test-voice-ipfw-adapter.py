#!/usr/bin/env python3
"""Exact IPFW argv / read-only parsing tests for staged FreeBSD adapter."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

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
AUTO_RST = ["divert", "989", "tcp", "from", "any", "443",
            "to", "any", "tcpflags", "rst", "in", "not",
            "diverted", "recv", "vtnet1"]

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
        self.counter_output = None

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
        if command == ("show", "19000"):
            output = self.counter_output
            if output is None:
                output = "19000 7 280 " + " ".join(VOICE) + "\\n"
            return subprocess.CompletedProcess(argv, 0, stdout=output.replace("\\n", "\n"), stderr="")
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
    def test_schema3_native_RST_matches_only_fully_attested_TCP_capture(self):
        from voice_ipfw_adapter import _verified_learning_rst_scope
        args = ("--port=989\n"
                "--filter-tcp=80\n"
                "--new\n"
                "--filter-tcp=443\n"
                "--new\n"
                "--filter-udp=443\n").encode("ascii")
        learning = ((1, "youtube", "/var/db/zapret2-auto-detect/learning-a-1.txt"),
                    (2, "user", "/var/db/zapret2-auto-detect/learning-a-2.txt"),
                    (3, "youtube", "/var/db/zapret2-auto-detect/learning-a-3.txt"))
        self.assertEqual("80,443", _verified_learning_rst_scope(learning, args, "80,443"))
        self.assertIsNone(_verified_learning_rst_scope((learning[2],), args, "80,443"))
        with self.assertRaises(IPFWAdapterError):
            _verified_learning_rst_scope((learning[0],), args, "80,443")
        with self.assertRaises(IPFWAdapterError):
            _verified_learning_rst_scope(learning, args, "443")
        with self.assertRaises(IPFWAdapterError):
            _verified_learning_rst_scope((learning[0], learning[0]), args, "80,443")
        with self.assertRaises(IPFWAdapterError):
            _verified_learning_rst_scope(((4, "foreign", "/tmp/foreign"),), args, "80,443")

    def test_native_auto_inbound_rst_is_exact_and_no_broad_feedback(self):
        self.assertEqual(checked_rule_argv(AUTO_RST), AUTO_RST)
        for slot, value in (
            (2, "udp"), (5, "any"), (9, "syn,ack"), (9, "fin"),
            (10, "out"), (12, "sockarg"), (13, "xmit"),
            (14, "bad interface"),
        ):
            changed = list(AUTO_RST)
            changed[slot] = value
            with self.subTest(slot=slot, value=value), self.assertRaises(
                    IPFWAdapterError):
                checked_rule_argv(changed)
        native = SimulateFreeBSD()
        native.rule_listing += "19003 " + " ".join(AUTO_RST) + "\n"
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=native)
        self.assertEqual(adapter.list_rules(19000, 19010)[19003], AUTO_RST)

    def test_reads_known_rules_without_treating_foreign_outside_range_as_ours(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=fake)
        self.assertEqual({19000: VOICE, 19001: TCP, 19002: UDP},
                         adapter.list_rules(19000, 19010))
        self.assertEqual(("/sbin/ipfw", "-q", "list"), fake.operations[0])

    def test_verified_rule_counters_are_read_only_and_not_foreign(self):
        fake=SimulateFreeBSD()
        adapter=FreeBSDIPFWAdapter(19000,19010,runner=fake)
        self.assertEqual((7,280),adapter.rule_counters(19000,VOICE))
        self.assertEqual(("/sbin/ipfw","show","19000"),fake.operations[-1])
        for output in (
            "19001 7 280 " + " ".join(VOICE) + "\n",
            "19000 7 280 " + " ".join(TCP) + "\n",
            "19000 7 280 " + " ".join(VOICE) + "\n19000 9 900 " + " ".join(VOICE),
            "19000 not_a_number 280 " + " ".join(VOICE),
        ):
            fake.counter_output=output
            with self.subTest(output=output),self.assertRaises(IPFWAdapterError):
                adapter.rule_counters(19000,VOICE)
        with self.assertRaises(IPFWAdapterError):
            adapter.rule_counters(19012,VOICE)
        self.assertTrue(all(x[1] == "show" for x in fake.operations))

    def test_reads_bounded_known_ipv4_table(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=fake)
        self.assertEqual(fake.table, adapter.get_table("zapret2_voice_telegram"))
        fake.table_output = "91.108.0.0/16 0\\n91.108.13.10/32 0\\n".replace("\\n", "\n")
        self.assertEqual(fake.table, adapter.get_table("zapret2_voice_telegram"))
        fake.table_output = None
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

    def test_table_parser_accepts_mixed_family_and_native_host_keys(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=fake)
        fake.table_output = ("91.108.13.10/32 0\\n2001:DB8::1/128 0\\n"
                             "2001:db8:abcd::/48 0\\n::/128 0\\n").replace("\\n", "\n")
        self.assertEqual(["91.108.13.10", "2001:db8::1", "2001:db8:abcd::/48", "::"],
                         adapter.get_table("zapret2_voice_telegram"))

    def test_table_parser_rejects_malformed_duplicates_and_foreign_keys(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000,19010,runner=fake)
        for value in ("91.108.4.7/22 0\\n",
                      "91.108.13.10\\n91.108.13.10/32\\n",
                      "2001:db8::1/128 0\\n2001:0DB8::1 0\\n",
                      "2001:db8::1/32 0\\n",
                      "0.0.0.0/0 0\\n", "::/0 0\\n",
                      "fe80::1%vtnet1 0\\n", "::ffff:192.0.2.10 0\\n", "??? a:b\\n"):
            fake.table_output = value.replace("\\n", "\n")
            with self.subTest(value=value):
                with self.assertRaises(IPFWAdapterError):
                    adapter.get_table("zapret2_voice_telegram")
        fake.table_output = "9.9.9.9 0\\n".replace("\\n", "\n")
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

    def test_mixed_family_mutations_keep_exact_owned_table_and_no_default_any(self):
        fake = SimulateFreeBSD()
        adapter = FreeBSDIPFWAdapter(19000, 19010, allow_mutations=True, runner=fake)
        for address in ("91.108.13.10", "2001:db8:abcd::/48", "::"):
            adapter.add_table_entry("zapret2_voice_telegram_stage", address)
        self.assertEqual([
            ("/sbin/ipfw","-q","table","zapret2_voice_telegram_stage","add", address)
            for address in ("91.108.13.10", "2001:db8:abcd::/48", "::")
        ],fake.operations)
        for bad in ("0.0.0.0/0", "::/0", "2001:db8::1/32",
                    "2001:DB8::1", "::ffff:192.0.2.1", "2001:db8::1/128",
                    "2001:db8::1%vtnet1"):
            with self.subTest(bad=bad), self.assertRaises(IPFWAdapterError):
                adapter.add_table_entry("zapret2_voice_telegram_stage", bad)
        self.assertEqual(3,len(fake.operations), "invalid native keys changed IPFW")

    def test_actual_cli_verify_legacy_branch_is_read_only(self):
        """Regression: _14 helper-only tests missed undefined legacy in main."""
        import voice_ipfw_adapter as module
        from voice_ipfw_adapter import main
        prev = {"rule_base": 19000, "rule_max": 19010,
                "rules": {19000: TCP}, "tables": {}}
        desired = {"rule_base": 19000, "rule_max": 19010,
                   "rules": {19000: VOICE, 19001: TCP}, "tables": {}}
        argv = ["voice_ipfw_adapter.py", "shared", "verify-legacy",
                "/test/ordinary-strategies", "/test/native-candidate"]

        def is_file(path):
            return str(path) == "/test/native-candidate/voice-plan.json"

        with patch.object(module, "require_lifecycle_lock"), \
             patch.object(Path, "stat", return_value=SimpleNamespace(st_uid=0)), \
             patch.object(Path, "is_file", autospec=True, side_effect=is_file), \
             patch.object(module, "shared_release_manifest", return_value=desired) as native, \
             patch.object(module, "legacy_strategies_manifest", return_value=prev) as legacy, \
             patch.object(module, "FreeBSDIPFWAdapter") as backend, \
             patch.object(module, "shared_firewall_action") as action:
            self.assertEqual(0, main(argv))
            native.assert_called_once_with(Path(argv[4]))
            legacy.assert_called_once_with(Path(argv[3]), desired)
            backend.assert_called_once_with(19000, 19010, allow_mutations=False)
            action.assert_called_once_with(backend.return_value, "verify", prev, prev)
            self.assertEqual([], backend.return_value.method_calls)

            # The same real CLI must reject a native predecessor without
            # adopting it as the legacy Strategies owner.
            action.reset_mock()
            legacy.reset_mock()
            with patch.object(Path, "is_file", return_value=True):
                self.assertEqual(1, main(argv))
            action.assert_not_called()
            legacy.assert_not_called()


    def test_actual_freebsd15_missing_table_info_is_not_an_ipfw_failure(self):
        """Owner evidence: all ten unopened Voice tables return code 71."""
        from voice_firewall_transaction import SERVICES, TABLE_PREFIX
        calls = []
        missing = "ipfw: failed to request table info: No such process\n"

        def runner(argv, **kwargs):
            calls.append(tuple(argv))
            return subprocess.CompletedProcess(argv, 71, stdout="", stderr=missing)

        adapter = FreeBSDIPFWAdapter(19000, 19010, runner=runner)
        for service in SERVICES:
            for suffix in ("", "_stage"):
                table = TABLE_PREFIX + service + suffix
                self.assertIsNone(adapter.get_table(table))
        self.assertEqual(
            {("/sbin/ipfw", "table", TABLE_PREFIX + name + suffix, "info")
             for name in SERVICES for suffix in ("", "_stage")},
            set(calls),
        )
        self.assertEqual(10, len(calls))
        # Error 71 is never a general waiver for commands other than
        # the read-only, explicitly allowlisted table-info probe.
        for args in (("-q", "list"), ("table", "zapret2_voice_telegram", "list")):
            with self.subTest(args=args):
                with self.assertRaisesRegex(IPFWAdapterError, "command failed"):
                    adapter._run(*args, allow_missing=True)
        for code, stderr in (
            (1, missing),
            (71, "Permission denied"),
            (71, "ipfw: failed to request table info: No such process\nunsafe extra"),
            (71, "ipfw: failed to request table info: Operation not permitted"),
            (71, ""),
        ):
            def unsafe_runner(argv, **kwargs):
                return subprocess.CompletedProcess(argv, code, stdout="", stderr=stderr)
            unsafe = FreeBSDIPFWAdapter(19000, 19010, runner=unsafe_runner)
            with self.subTest(code=code, stderr=stderr):
                with self.assertRaisesRegex(IPFWAdapterError, "command failed"):
                    unsafe.get_table("zapret2_voice_telegram")

    def test_real_verify_legacy_cli_accepts_only_absent_freebsd15_voice_tables(self):
        """Run actual shared verify-legacy CLI and native adapters, not a stub."""
        import voice_ipfw_adapter as module
        active = {"rule_base": 19000, "rule_max": 19010,
                  "rules": {19000: TCP, 19001: UDP}, "tables": {}}
        candidate = {"rule_base": 19000, "rule_max": 19010,
                     "rules": {19000: VOICE, 19001: TCP, 19002: UDP},
                     "tables": {}}
        ipfw_calls = []
        missing = "ipfw: failed to request table info: No such process\n"

        def native_runner(argv, **kwargs):
            ipfw_calls.append(tuple(argv))
            if argv[1:] == ["-q", "list"]:
                return subprocess.CompletedProcess(argv, 0,
                    stdout="19000 " + " ".join(TCP) + "\n" +
                           "19001 " + " ".join(UDP) + "\n", stderr="")
            if len(argv) == 4 and argv[1] == "table" and argv[3] == "info":
                return subprocess.CompletedProcess(argv, 71, stdout="", stderr=missing)
            raise AssertionError("unplanned IPFW command: " + repr(argv))

        def native_adapter(first, last, *, allow_mutations):
            self.assertFalse(allow_mutations)
            return FreeBSDIPFWAdapter(first, last, runner=native_runner)

        argv = ["voice_ipfw_adapter.py", "shared", "verify-legacy",
                "/test/ordinary-strategies", "/test/native-candidate"]
        with patch.object(module, "require_lifecycle_lock"), \
             patch.object(Path, "stat", return_value=SimpleNamespace(st_uid=0)), \
             patch.object(Path, "is_file", autospec=True,
                          side_effect=lambda p: str(p) == "/test/native-candidate/voice-plan.json"), \
             patch.object(module, "shared_release_manifest", return_value=candidate), \
             patch.object(module, "legacy_strategies_manifest", return_value=active), \
             patch.object(module, "FreeBSDIPFWAdapter", side_effect=native_adapter):
            self.assertEqual(0, module.main(argv))
        self.assertEqual(11, len(ipfw_calls))
        self.assertEqual(("/sbin/ipfw", "-q", "list"), ipfw_calls[0])
        self.assertTrue(all(op[1] == "table" and op[-1] == "info"
                            for op in ipfw_calls[1:]))

    def test_missing_table_only_on_specific_diagnostic_and_fail_closed(self):
        fake=SimulateFreeBSD()
        adapter=FreeBSDIPFWAdapter(19000,19010,runner=fake)
        fake.error=True
        with self.assertRaises(IPFWAdapterError):
            adapter.get_table("zapret2_voice_telegram")
        with self.assertRaises(IPFWAdapterError):
            adapter.list_rules(19000,19010)

    def test_rule_add_rejection_is_typed_only_for_real_admitted_add(self):
        from voice_ipfw_adapter import IPFWRuleAddRejected
        secret = "private-native-stderr-ip-and-argv"
        def rejected(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 75, stdout="", stderr=secret)
        adapter = FreeBSDIPFWAdapter(19000, 19010, allow_mutations=True, runner=rejected)
        with self.assertRaises(IPFWRuleAddRejected) as caught:
            adapter.add_rule(19000, VOICE)
        self.assertNotIn(secret, str(caught.exception))
        with self.assertRaisesRegex(IPFWAdapterError, "command failed"):
            adapter.delete_rule(19000)
        with self.assertRaisesRegex(IPFWAdapterError, "command failed"):
            adapter.list_rules(19000, 19010)

    def test_original_cli_requires_typed_add_and_completed_rollback(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr
        import voice_ipfw_adapter as module
        from voice_firewall_transaction import VoiceFirewallError
        from voice_ipfw_adapter import IPFWRuleAddRejected
        manifest = {"rule_base": 19000, "rule_max": 19010,
                    "rules": {19000: VOICE}, "tables": {}}
        argv = ["voice_ipfw_adapter.py", "shared", "install",
                "/test/native-prev", "/test/native-next"]

        def rejected(*_):
            try:
                raise IPFWRuleAddRejected("IPFW rule add command refused")
            except IPFWRuleAddRejected as original:
                raise VoiceFirewallError(
                    "Voice IPFW activation failed; previous owned state restored"
                ) from original

        def run(action):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(module, "require_lifecycle_lock"), \
                 patch.object(Path, "stat", return_value=SimpleNamespace(st_uid=0)), \
                 patch.object(Path, "is_file", return_value=True), \
                 patch.object(module, "shared_release_manifest", return_value=manifest), \
                 patch.object(module, "FreeBSDIPFWAdapter"), \
                 patch.object(module, "shared_firewall_action", side_effect=action), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                rc = module.main(argv)
            return rc, stdout.getvalue(), stderr.getvalue()

        rc, out, err = run(rejected)
        self.assertEqual(1, rc)
        self.assertEqual("ipfw-attach-failure=rule-add-rejected\n", out)
        self.assertEqual("ERROR: IPFW_ATTACH_FAILED\n", err)
        for failure in (
            VoiceFirewallError("Voice IPFW activation failed; previous owned state restored"),
            VoiceFirewallError("Voice IPFW activation failed; rollback incomplete; appliance inspection required"),
            IPFWRuleAddRejected("IPFW rule add command refused"),
        ):
            def unrelated(*_):
                raise failure
            rc, out, err = run(unrelated)
            self.assertEqual(1, rc)
            self.assertEqual("", out)
            self.assertNotIn("IPFW_ATTACH_FAILED", err)

if __name__ == "__main__":
    unittest.main(verbosity=2)
