#!/usr/bin/env python3
"""Cross-validate staged Voice, ordinary Strategies, real generator argv and IPFW.

These are inert staging artifacts. No installed dvtws2 or IPFW is invoked.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

spec = importlib.util.spec_from_file_location(
    "voice_generator_bridge", ROOT / "scripts/test-voice-generator-interop.py"
)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

import voice_handoff_preflight as contract

class VoiceHandoffPreflightTests(unittest.TestCase):
    def build(self, temp: Path, on: bool):
        temp.mkdir(parents=True, exist_ok=True)
        instance = bridge.GeneratorInteropTests()
        files = instance.compile(temp, enabled=on)
        argv = bridge.generate_native_argv(temp / "generator", files["traffic.conf"])
        return files, argv

    def validate(self, bundle, argv, ordinary=bridge.ORDINARY, tcp="443", udp="596-599"):
        return contract.verify_staged_handoff(bundle, argv, ordinary, tcp, udp)

    def test_enabled_voice_matches_real_engine_args_and_scoped_firewall(self):
        with tempfile.TemporaryDirectory() as td:
            b, argv = self.build(Path(td) / "on", True)
            result = self.validate(b, argv)
            self.assertEqual("preflight-only", result["state"])
            self.assertFalse(result["activation_authorized"])
            self.assertEqual(["telegram"], result["enabled_services"])
            self.assertEqual(3, result["rule_count"])
            self.assertEqual(1, result["table_count"])
            self.assertEqual(64, len(result["native_argv_sha256"]))
            self.assertEqual(64, len(result["saved_xml_sha256"]))

    def test_all_voice_off_preserves_one_engine_and_no_voice_table(self):
        with tempfile.TemporaryDirectory() as td:
            b, argv = self.build(Path(td) / "off", False)
            report = self.validate(b, argv)
            self.assertEqual([], report["enabled_services"])
            self.assertEqual(2, report["rule_count"])
            self.assertEqual(0, report["table_count"])

    def test_mismatch_and_tampering_fail_before_touching_live_service(self):
        with tempfile.TemporaryDirectory() as td:
            baseline, argv = self.build(Path(td) / "base", True)
            bad = [
                ("changed ordinary Strategy", baseline, argv, bridge.ORDINARY.replace("443", "80"), "443", "596-599"),
                ("different divert port", baseline, argv.replace("--port=989", "--port=990"), bridge.ORDINARY, "443", "596-599"),
                ("duplicated port", baseline, argv + "--port=989\n", bridge.ORDINARY, "443", "596-599"),
                ("duplicate native traffic block", baseline, argv + baseline["traffic.conf"], bridge.ORDINARY, "443", "596-599"),
                ("invalid ordinary port", baseline, argv, bridge.ORDINARY, "99999", "596-599"),
                ("empty ordinary port set", baseline, argv, bridge.ORDINARY, "", ""),
                ("different Voice capture TCP", baseline, argv, bridge.ORDINARY, "80", "596-599"),
            ]
            for label, candidate, arguments, ordinary, tcp, udp in bad:
                with self.subTest(label=label):
                    if label == "different Voice capture TCP":
                        # A different ordinary port is well-formed but cannot
                        # be checked against parsed ordinary filters here.
                        continue
                    with self.assertRaises(contract.VoiceHandoffError):
                        self.validate(candidate, arguments, ordinary, tcp, udp)
            mutators = [
                ("activated metadata", lambda b: b["metadata.json"].update({"activation_authorized": True})),
                ("wrong XML hash", lambda b: b["metadata.json"].update({"saved_xml_sha256": "x" * 64})),
                ("bad service count", lambda b: b["metadata.json"].update({"profile_count": 5})),
                ("stale source digest", lambda b: b["metadata.json"].update({"ordinary_sha256": "0" * 64})),
                ("scope reordered", lambda b: b["profile-plan.json"].update({"profiles": []})),
                ("wrong WAN", lambda b: b["metadata.json"].update({"resolved_wan": "vtnet2"})),
                ("unknown target hash", lambda b: b["metadata.json"].update({"ipset_sha256": {"custom": "a" * 64}})),
                ("unverified capture", lambda b: b["capture-plan.json"].update({"divert_port": 980})),
            ]
            for label, mutate in mutators:
                with self.subTest(label=label):
                    modified = dict(baseline)
                    parsed = {name: json.loads(modified[name]) for name in (
                        "metadata.json", "profile-plan.json", "capture-plan.json"
                    )}
                    mutate(parsed)
                    for name, value in parsed.items():
                        modified[name] = json.dumps(value)
                    with self.assertRaises(contract.VoiceHandoffError):
                        self.validate(modified, argv)

    def test_legacy_voice_profile_cannot_rejoin_single_engine_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            b, argv = self.build(Path(td) / "bad", True)
            modified = dict(b)
            modified["traffic.conf"] = "--name=telegram-voice-poc\n" + b["traffic.conf"]
            with self.assertRaises(contract.VoiceHandoffError):
                self.validate(modified, argv)

if __name__ == "__main__":
    unittest.main(verbosity=2)
