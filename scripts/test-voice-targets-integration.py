#!/usr/bin/env python3
"""Exercise real shared Targets normalizer -> all five Voice managed IPSETs.

Only temporary files and POSIX shell helper functions are used. No configctl,
running dvtws2, IPFW rules, route, tunnel or live OPNsense configuration.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

def load(name):
    spec = importlib.util.spec_from_file_location(name, BACKEND / (name + ".py"))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

stage = load("voice_release_stage")
compiler = load("voice_profile_compiler")
capture = load("voice_capture_plan")

DATA = {
    "telegram": ("91.108.0.0/16\n91.108.13.10\n91.108.13.10", "596-599"),
    "discord": ("203.0.113.0/24\n203.0.113.0/24", "5000"),
    "x": ("198.51.100.0/24\n", "5000"),
    "sip": ("192.0.2.0/24\n192.0.2.10", "6000"),
    "custom": ("100.64.0.0/10\n100.64.0.0/10", "7777"),
}
SERVICES = ("telegram", "discord", "x", "sip", "custom")

def run_real_targets(folder: Path, addresses: dict[str, str]) -> subprocess.CompletedProcess:
    cmd = [
        "/bin/sh", "-c",
        '. "$1"; . "$2"; shift 2; targets_prepare_managed "$@"',
        "voice-targets-interop",
        str(BACKEND / "common.sh"), str(BACKEND / "targets.sh"),
        str(folder), "youtube.com", addresses["telegram"], "example.org",
        addresses["discord"], addresses["x"], addresses["sip"], addresses["custom"],
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def xml_source(path: Path, addresses: dict[str,str]) -> None:
    root = ET.Element("opnsense")
    model = ET.SubElement(ET.SubElement(root, "OPNsense"), "Zapret")
    ET.SubElement(ET.SubElement(model, "general"), "waninterface").text = "WAN"
    voice = ET.SubElement(model, "voice")
    ET.SubElement(voice, "waninterface").text = "WAN"
    hostlist = ET.SubElement(model, "hostlist")
    for service, (original, ports) in DATA.items():
        entry = ET.SubElement(voice, service)
        ET.SubElement(entry, "enabled").text = "1"
        ET.SubElement(entry, "args").text = (
            f"--filter-udp={ports}\n--filter-l7=stun\n--payload=stun\n"
        )
        ET.SubElement(hostlist, service+"ips").text = addresses[service]
    ET.ElementTree(root).write(path, encoding="utf-8")


class RealTargetsBridgeTests(unittest.TestCase):
    def test_all_five_voice_targets_match_real_shared_normalizer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            managed = root / "managed"
            source = root / "config.xml"
            original = {name: DATA[name][0] for name in SERVICES}
            xml_source(source, original)
            result = run_real_targets(managed, original)
            self.assertEqual(result.returncode, 0, result.stderr)
            bundle = stage.compile_bundle(
                source, managed, Path("/usr/local/etc/zapret2/runtime-v2"),
                "vtnet1", 19000, 19010, 989,
            )
            plan = json.loads(bundle["capture-plan.json"])
            meta = json.loads(bundle["metadata.json"])
            self.assertEqual(SERVICES, tuple(row["service"] for row in plan["voice"]))
            self.assertEqual(5, meta["profile_count"])
            self.assertEqual(set(SERVICES), set(meta["ipset_sha256"]))
            self.assertFalse(meta["activation_authorized"])
            for name in SERVICES:
                expected, _ = compiler.normalize_targets(original[name], name)
                self.assertEqual(
                    expected, (managed / f"ipset-{name}.txt").read_text().splitlines(),
                    name + " normalization differs between shared Targets and Voice compiler",
                )
                self.assertIn(f"--name=voice-{name}", bundle["voice.conf"])
                self.assertIn(f"table(zapret2_voice_{name})",
                              str(next(r for r in plan["voice"] if r["service"]==name)["argv"]))
            self.assertNotIn("telegram-voice-poc", bundle["voice.conf"])

    def test_host_bits_in_shared_targets_fail_instead_of_entering_voice_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            managed = root / "managed"
            bad = {name: DATA[name][0] for name in SERVICES}
            bad["sip"] = "192.0.2.10/24"
            source = root / "config.xml"
            xml_source(source, bad)
            result = run_real_targets(managed, bad)
            self.assertNotEqual(0, result.returncode, result.stdout)
            with self.assertRaises((ValueError, OSError)):
                stage.compile_bundle(
                    source, managed, Path("/usr/local/etc/zapret2/runtime-v2"),
                    "vtnet1", 19000, 19010, 989,
                )
            self.assertTrue(source.is_file())

if __name__ == "__main__":
    unittest.main(verbosity=2)
