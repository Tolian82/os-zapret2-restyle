#!/usr/bin/env python3
"""Stage 5 exact existing FreeBSD adapter and transaction dual-stack contracts.

CI uses the real compiler/adapter/transaction with injected native state,
not a new production firewall implementation. Live installed FreeBSD 15
table/divert/reinjection acceptance remains a distinct owner-visible gate.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_profile_compiler import SERVICES, VoiceConfigurationError, compile_candidate
from voice_capture_plan import compile_capture_plan, CapturePlanError
from voice_firewall_transaction import (
    VoiceFirewallError, apply_transaction, cleanup_committed,
    prepare_desired, rollback_uncommitted, verify_prior_state,
)
from voice_ipfw_adapter import FreeBSDIPFWAdapter, IPFWAdapterError, checked_table_ip
from voice_ipfw_adapter import checked_rule_argv

FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "voice_firewall_transaction_fixture", ROOT / "scripts/test-voice-firewall-transaction.py")
assert FIXTURE_SPEC and FIXTURE_SPEC.loader
FIXTURE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE)
FakeIPFW = FIXTURE.FakeIPFW
MANAGED = Path("/usr/local/etc/zapret2/runtime-v2/managed")
STUN = "--filter-udp=596-599\n--filter-l7=stun\n--payload=stun"


def desired(**targets):
    settings = {"strategy_wan": "WAN", "services": {
        name: {"enabled": name in targets, "ips": targets.get(name, ""),
               "args": STUN if name in targets else ""}
        for name in SERVICES
    }}
    traffic, profiles = compile_candidate(settings, MANAGED)
    capture = compile_capture_plan(profiles, 19000, 19010, 989, physical_wan="vtnet1")
    return traffic, prepare_desired(capture, "443", "596-599")


class NativeIPFWDualStackTests(unittest.TestCase):
    def test_ipv4_ipv6_readback_normalization_and_explicit_no_universal_keys(self):
        self.assertEqual("91.108.13.10", checked_table_ip("91.108.13.10/32", readback=True))
        self.assertEqual("2001:db8::1", checked_table_ip("2001:DB8::1/128", readback=True))
        self.assertEqual("::", checked_table_ip("::/128", readback=True))
        for key in ("0.0.0.0/0", "::/0", "2001:db8::1/32",
                    "::ffff:192.0.2.1", "2001:db8::1%vtnet1"):
            with self.subTest(key=key), self.assertRaises(IPFWAdapterError):
                checked_table_ip(key)
        # Same native syntax as the actual adapter and unchanged WAN/divert.
        voice = ["divert", "989", "udp", "from", "any", "to",
                 "table(zapret2_voice_telegram)", "596-599",
                 "out", "not", "diverted", "not", "sockarg", "xmit", "vtnet1"]
        self.assertEqual(voice, checked_rule_argv(voice))
        with self.assertRaises(IPFWAdapterError):
            checked_rule_argv(voice[:6] + ["any"] + voice[7:-1])

    def test_mixed_ipv4_ipv6_stun_uses_exact_original_table_swap_and_rollback(self):
        _, previous = desired(telegram="91.108.0.0/16\n2001:db8::/32")
        traffic, next_state = desired(
            telegram="91.108.0.0/16\n2001:db8:1::/48",
            discord="203.0.113.0/24\n2001:db8:2::/48",
        )
        self.assertEqual(2, traffic.count("--filter-l3=ipv4,ipv6"))
        self.assertEqual(["91.108.0.0/16", "2001:db8:1::/48"],
                         next_state["tables"]["zapret2_voice_telegram"])
        self.assertEqual("table(zapret2_voice_telegram)", next_state["rules"][19000][6])
        self.assertEqual("table(zapret2_voice_discord)", next_state["rules"][19001][6])
        live = FakeIPFW(previous["rules"], previous["tables"])
        apply_transaction(live, previous, next_state)
        self.assertEqual(next_state["rules"], live.rules)
        self.assertEqual(previous["tables"]["zapret2_voice_telegram"],
                         live.tables["zapret2_voice_telegram_stage"])
        rollback_uncommitted(live, previous, next_state)
        verify_prior_state(live, previous, previous)
        self.assertEqual(previous["tables"], live.tables)

    def test_foreign_ipv6_table_blocks_all_mutations(self):
        _, previous = desired(telegram="91.108.0.0/16")
        _, future = desired(telegram="91.108.0.0/16\n2001:db8::/32")
        live = FakeIPFW(previous["rules"], previous["tables"])
        live.tables["zapret2_voice_telegram"].append("2001:db8:ffff::/48")
        before = (deepcopy(live.rules), deepcopy(live.tables))
        with self.assertRaisesRegex(VoiceFirewallError, "foreign"):
            apply_transaction(live, previous, future)
        self.assertEqual(before, (live.rules, live.tables))
        self.assertEqual([], live.ops)

    def test_faults_from_ipv4_to_dualstack_restore_exact_prior(self):
        _, previous = desired(telegram="91.108.0.0/16")
        _, next_state = desired(telegram="91.108.0.0/16\n2001:db8:1::/48",
                                discord="203.0.113.0/24\n2001:db8:2::/48")
        for failure in ("create_table", "add_table_entry", "swap_tables",
                        "delete_rule", "add_rule"):
            live = FakeIPFW(previous["rules"], previous["tables"], failure=failure)
            with self.subTest(failure=failure):
                with self.assertRaisesRegex(VoiceFirewallError, "previous owned state restored"):
                    apply_transaction(live, previous, next_state)
                verify_prior_state(live, previous, previous)
                self.assertEqual(previous["rules"], live.rules)
                self.assertEqual(previous["tables"], live.tables)

    def test_cleanup_and_ipv4_only_installation(self):
        _, original = desired()
        _, dual = desired(telegram="2001:db8::1", discord="91.108.0.0/16")
        live = FakeIPFW(original["rules"], original["tables"])
        apply_transaction(live, original, dual)
        cleanup_committed(live, original, dual)
        verify_prior_state(live, dual, dual)
        self.assertIsNone(live.get_table("zapret2_voice_telegram_stage"))
        _, ipv4_only = desired(telegram="91.108.0.0/16")
        apply_transaction(live, dual, ipv4_only)
        rollback_uncommitted(live, dual, ipv4_only)
        verify_prior_state(live, dual, dual)

    def test_full_family_unions_do_not_enter_native_ipfw(self):
        for unsafe in ("0.0.0.0/0", "::/0",
                       "0.0.0.0/1\n128.0.0.0/1",
                       "::/1\n8000::/1"):
            with self.subTest(unsafe=unsafe), self.assertRaises(VoiceConfigurationError):
                desired(telegram=unsafe)


@unittest.skipUnless(
    platform.system() == "FreeBSD" and os.geteuid() == 0 and
    os.getenv("ZAPRET2_STAGE5_LIVE_READONLY") == "1",
    "installed FreeBSD 15 read-only operator check is explicitly opt-in")
class InstalledIPFWReadOnlySmoke(unittest.TestCase):
    def test_no_unowned_mutation_on_live_inspection(self):
        # Read-only inspection of existing protected numeric range only.
        # Table snapshots are not assumed to exist on all-OFF installations.
        adapter = FreeBSDIPFWAdapter(19000, 19010)
        rules = adapter.list_rules(19000, 19010)
        self.assertIsInstance(rules, dict)
        for service in SERVICES:
            name = "zapret2_voice_" + service
            observed = adapter.get_table(name)
            self.assertTrue(observed is None or isinstance(observed, list))


if __name__ == "__main__":
    unittest.main(verbosity=2)
