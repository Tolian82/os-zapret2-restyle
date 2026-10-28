#!/usr/bin/env python3
"""Stage 4: existing Voice IPSET family separation, no P2P or new controls."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

BACKEND = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_profile_compiler import SERVICES, compile_candidate, VoiceConfigurationError
from voice_capture_plan import compile_capture_plan, CapturePlanError
from voice_traffic_merge import merge_profiles, VoiceMergeError

MANAGED = Path("/usr/local/etc/zapret2/runtime-v2/managed")
STUN = "--filter-udp=*\n--filter-l7=stun\n--payload=stun"


def state():
    return {
        "strategy_wan": "WAN",
        "services": {
            name: {"enabled": False, "args": "", "ips": ""}
            for name in SERVICES
        }
    }


def on(obj, service, ips, args=STUN):
    obj["services"][service] = {"enabled": True, "args": args, "ips": ips}
    return obj


def compile_scope(obj):
    profile, candidate = compile_candidate(obj, MANAGED)
    capture = compile_capture_plan(candidate, 19000, 19010, 989, physical_wan="vtnet1")
    return profile, candidate, capture


class VoiceDualStackBoundaries(unittest.TestCase):
    def test_all_five_services_keep_one_native_stun_profile_per_service(self):
        obj = state()
        for idx, name in enumerate(SERVICES):
            on(obj, name, f"192.0.2.{idx+1}\n2001:db8:{idx+1}::/48")
        profile, candidate, capture = compile_scope(obj)
        self.assertEqual(5, len(candidate["profiles"]))
        self.assertEqual(5, len(capture["voice"]))
        self.assertEqual(4, profile.count("\n--new\n"))
        self.assertEqual(5, profile.count("--filter-l3=ipv4,ipv6"))
        self.assertEqual(5, profile.count("--filter-l7=stun"))
        self.assertEqual(5, profile.count("--payload=stun"))
        self.assertNotIn("hostlist-exclude", profile)
        self.assertNotIn("0.0.0.0/0", profile)
        self.assertTrue(all("table(zapret2_voice_" + name + ")" in " ".join(row["argv"])
                            for name, row in zip(SERVICES, capture["voice"])))
        for row in candidate["profiles"]:
            expected = (
                "--name=voice-" + row["service"] + "\n"
                "--filter-l3=ipv4,ipv6\n"
                "--ipset=" + row["ipset_path"] + "\n" + STUN
            )
            self.assertEqual(hashlib.sha256(expected.encode()).hexdigest(),
                             row["profile_sha256"])
            self.assertEqual(2, row["target_count"])

    def test_compatible_ipv4_ipv6_and_host_zero_v6_are_accepted(self):
        obj = on(state(), "telegram", "91.108.0.0/16\n::\n2001:db8::1/128")
        _, candidate, capture = compile_scope(obj)
        self.assertEqual(["91.108.0.0/16", "::", "2001:db8::1"],
                         candidate["profiles"][0]["targets"])
        self.assertEqual(candidate["profiles"][0]["targets"], capture["voice"][0]["destinations"])
        self.assertNotIn("to any", " ".join(capture["voice"][0]["argv"]))

    def test_disjoint_families_same_udp_do_not_conflict(self):
        obj = on(state(), "telegram", "91.108.0.0/16")
        on(obj, "discord", "2001:db8::/32")
        _, _, capture = compile_scope(obj)
        self.assertEqual(2, len(capture["voice"]))
        obj = on(state(), "telegram", "2001:db8::/32")
        on(obj, "discord", "2001:db8:1::/48")
        with self.assertRaisesRegex(VoiceConfigurationError, "overlapping"):
            compile_scope(obj)

    def test_overlapping_ipv6_with_nonoverlapping_udp_is_allowed(self):
        obj = on(state(), "telegram", "2001:db8::/32",
                 "--filter-udp=3478\n--filter-l7=stun\n--payload=stun")
        on(obj, "discord", "2001:db8:1::/48",
           "--filter-udp=596-599\n--filter-l7=stun\n--payload=stun")
        _, _, capture = compile_scope(obj)
        self.assertEqual(2, len(capture["voice"]))

    def test_every_user_managed_full_family_form_is_refused(self):
        for source in ("0.0.0.0/0", "::/0", "0.0.0.0/1\n128.0.0.0/1",
                       "::/1\n8000::/1", "2001:db8::1/32",
                       "fe80::1%vtnet1", "not-an-ip"):
            with self.subTest(source=source):
                with self.assertRaises(VoiceConfigurationError):
                    compile_scope(on(state(), "telegram", source))
        obj = state()
        obj["services"]["telegram"]["ips"] = "::/0"
        obj["services"]["telegram"]["args"] = "--new"
        profile, candidate, capture = compile_scope(obj)
        self.assertEqual("", profile)
        self.assertEqual([], candidate["profiles"])
        self.assertEqual([], capture["voice"])

    def test_prepared_targets_mismatch_is_fail_closed(self):
        obj = on(state(), "telegram", "91.108.0.0/16\n2001:db8::/32")
        with self.assertRaisesRegex(VoiceConfigurationError, "prepared managed IPSET differs"):
            compile_candidate(obj, MANAGED, {"telegram": ["91.108.0.0/16"]})

    def test_ordinary_stun_overlap_requires_same_family_and_udp(self):
        voice, _, _ = compile_scope(on(state(), "telegram", "2001:db8::/32"))
        prefix = "--filter-udp=3478\n--filter-l7=stun\n--payload=stun\n"
        scopes = {str(MANAGED / "ipset-telegram.txt"): ["2001:db8::/32"]}
        overlapping = prefix + "--filter-l3=ipv6\n--ipset-ip=2001:db8:1::1\n"
        with self.assertRaisesRegex(VoiceMergeError, "overlaps"):
            merge_profiles(voice, overlapping, scopes)
        disjoint = prefix + "--filter-l3=ipv4\n--ipset-ip=192.0.2.1\n"
        self.assertEqual(voice.rstrip("\n") + "\n--new\n" + disjoint,
                         merge_profiles(voice, disjoint, scopes))
        no_port_overlap = overlapping.replace("--filter-udp=3478", "--filter-udp=1400")
        # Voice wildcard UDP deliberately still overlaps every UDP port.
        with self.assertRaisesRegex(VoiceMergeError, "overlaps"):
            merge_profiles(voice, no_port_overlap, scopes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
