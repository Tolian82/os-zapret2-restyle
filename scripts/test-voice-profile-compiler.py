#!/usr/bin/env python3
"""Fail-closed pure candidate generation contract for Voice/STUN."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
COMPILER = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/voice_profile_compiler.py"
spec = importlib.util.spec_from_file_location("voice_compiler", COMPILER)
assert spec is not None and spec.loader is not None
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)

BASE_ARGS = (
    "--filter-udp=*\n"
    "--filter-l7=stun\n"
    "--payload=stun\n"
    "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2"
)


def payload():
    return {
        "strategy_wan": "wan0",
        "voice_wan": "",
        "services": {
            name: {"enabled": False, "args": "", "ips": ""}
            for name in voice.SERVICES
        },
    }


def enable(source, name="telegram", args=BASE_ARGS, ips="91.108.0.0/16"):
    source["services"][name] = {"enabled": True, "args": args, "ips": ips}
    return source


class VoiceCandidateTests(unittest.TestCase):
    def compile(self, source):
        return voice.compile_candidate(source, Path("/some/managed"))

    def test_default_all_off_preserves_blank_form(self):
        result, plan = self.compile(payload())
        self.assertEqual("", result)
        self.assertEqual([], plan["profiles"])
        self.assertEqual("wan0", plan["wan"])

    def test_old_stun_template_compiles_without_parallel_engine(self):
        result, plan = self.compile(enable(payload()))
        self.assertIn("--name=voice-telegram\n", result)
        self.assertIn("--filter-l3=ipv4\n", result)
        self.assertIn("--ipset=/some/managed/ipset-telegram.txt", result)
        self.assertIn(BASE_ARGS, result)
        self.assertEqual(1, len(plan["profiles"]))
        self.assertEqual("telegram", plan["profiles"][0]["service"])
        self.assertEqual("91.108.0.0/16", plan["profiles"][0]["targets"][0])
        self.assertEqual([[1, 65535]], plan["profiles"][0]["ports"])
        self.assertEqual(64, len(plan["profiles"][0]["profile_sha256"]))
        self.assertNotIn("not-tested", result)

    def test_disabled_service_does_not_validate_or_capture_draft(self):
        source = payload()
        source["services"]["discord"]["args"] = "--new\nbad options"
        source["services"]["discord"]["ips"] = "bad-IP"
        result, plan = self.compile(source)
        self.assertEqual("", result)
        self.assertEqual([], plan["profiles"])

    def test_multiple_profiles_keep_fixed_order(self):
        source = enable(payload(), name="custom", ips="192.0.2.0/24")
        source = enable(source, name="telegram", ips="91.108.0.0/16")
        result, plan = self.compile(source)
        self.assertEqual(["telegram", "custom"], [x["service"] for x in plan["profiles"]])
        self.assertEqual(1, result.count("\n--new\n"))
        self.assertLess(result.index("--name=voice-telegram"), result.index("--name=voice-custom"))

    def test_reject_cross_profile_scope_overlap(self):
        source = enable(payload())
        source = enable(source, "discord", "--filter-udp=596-599\n--filter-l7=stun\n--payload=stun", "91.108.13.10")
        with self.assertRaisesRegex(voice.VoiceConfigurationError, "overlapping UDP.*telegram"):
            self.compile(source)

    def test_disjoint_ports_allow_same_ips(self):
        source = enable(payload(), args="--filter-udp=596-599\n--filter-l7=stun\n--payload=stun")
        source = enable(source, "discord", "--filter-udp=1400\n--filter-l7=stun\n--payload=stun")
        _, plan = self.compile(source)
        self.assertEqual(2, len(plan["profiles"]))

    def test_disjoint_ips_allow_same_ports(self):
        source = enable(payload())
        source = enable(source, "discord", BASE_ARGS, "203.0.113.0/24")
        _, plan = self.compile(source)
        self.assertEqual(2, len(plan["profiles"]))

    def test_invalid_inputs(self):
        invalid = [
            (BASE_ARGS + "\n--new", "forbidden"),
            (BASE_ARGS + "\n--filter-tcp=443", "forbidden"),
            (BASE_ARGS + "\n--ipset=/etc/passwd", "forbidden"),
            (BASE_ARGS + "\n--name=system", "forbidden"),
            (BASE_ARGS + "\n--port=989", "forbidden"),
            (BASE_ARGS + "\n$(touch /tmp/unsafe)", "only printable"),
            (BASE_ARGS + "\n--lua-desync=send:ipfrag", "unsupported"),
            (BASE_ARGS + "\n--lua-desync=fake:blob=0x12:repeats=9999", "unsupported"),
            (BASE_ARGS.replace("--filter-udp=*", "--filter-udp=0"), "invalid UDP"),
            (BASE_ARGS.replace("--filter-udp=*", "--filter-udp=65536"), "invalid UDP"),
            (BASE_ARGS.replace("--filter-l7=stun", "--filter-l7=unknown"), "only --filter-l7=stun"),
            (BASE_ARGS.replace("--payload=stun", "--payload=unknown"), "only --payload=stun"),
            (BASE_ARGS.replace("--filter-udp=*", "--filter-udp=596-500"), "invalid UDP"),
            (BASE_ARGS.replace("--filter-udp=*", "--filter-udp=1-65535;rm"), "invalid UDP"),
        ]
        for args, message in invalid:
            with self.subTest(args=args):
                with self.assertRaisesRegex(voice.VoiceConfigurationError, message):
                    self.compile(enable(payload(), args=args))

    def test_required_fields_and_empty_ipset(self):
        for value in ["", "garbage", "91.108.13.10/24", "2001:db8::1", "1.2.3.4\n1.2.3.5/24"]:
            with self.subTest(value=value):
                with self.assertRaises(voice.VoiceConfigurationError):
                    self.compile(enable(payload(), ips=value))
        for name in ("--filter-udp=*", "--filter-l7=stun", "--payload=stun"):
            with self.subTest(missing=name):
                with self.assertRaisesRegex(voice.VoiceConfigurationError, "required"):
                    self.compile(enable(payload(), args=BASE_ARGS.replace(name, "")))

    def test_single_engine_rejects_independent_wan(self):
        source = enable(payload())
        source["voice_wan"] = "wan1"
        with self.assertRaisesRegex(voice.VoiceConfigurationError, "independent WAN is not yet isolated"):
            self.compile(source)

    def test_cli_fails_before_changing_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source.json"
            out = root / "voice.conf"
            plan = root / "plan.json"
            source.write_text(json.dumps(enable(payload())), encoding="utf-8")
            ok = subprocess.run([sys.executable, str(COMPILER), str(source),
                                 str(root / "managed"), str(out), str(plan)],
                                capture_output=True, text=True)
            self.assertEqual(0, ok.returncode, ok.stderr)
            before = (out.read_bytes(), plan.read_bytes())
            broken = enable(payload(), args=BASE_ARGS + "\n--new")
            source.write_text(json.dumps(broken), encoding="utf-8")
            failure = subprocess.run([sys.executable, str(COMPILER), str(source),
                                      str(root / "managed"), str(out), str(plan)],
                                     capture_output=True, text=True)
            self.assertNotEqual(0, failure.returncode)
            self.assertIn("telegram.args line", failure.stderr)
            self.assertEqual(before, (out.read_bytes(), plan.read_bytes()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
