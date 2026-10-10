#!/usr/bin/env python3
"""Offline integration: staged Voice + actual production shell argv generator.

No dvtws2, IPFW or OPNsense instance is executed. This test exercises the
actual generator.sh assembly order against a staged single-engine Voice +
ordinary Strategies candidate and compiles the matching guarded IPFW plan.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
def load(name):
    spec = importlib.util.spec_from_file_location(name, BACKEND / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
stage = load("voice_release_stage")
firewall = load("voice_firewall_transaction")
fixtures_spec = importlib.util.spec_from_file_location(
    "voice_release_stage_fixture", ROOT / "scripts/test-voice-release-stage.py"
)
fixtures = importlib.util.module_from_spec(fixtures_spec)
fixtures_spec.loader.exec_module(fixtures)

ACTIVE_ROOT = Path("/usr/local/etc/zapret2/runtime-v2")
ORDINARY = (
    "--filter-tcp=443\n--filter-l7=tls\n--new\n"
    "--filter-udp=596-599\n--filter-l7=unknown\n--payload=unknown\n"
)

def generate_native_argv(folder: Path, traffic: str) -> str:
    """Invoke repository's real generator.sh via POSIX sh, no shell arguments from users."""
    folder.mkdir(parents=True, exist_ok=True)
    trafficfile = folder / "traffic.conf"
    extrafile = folder / "extra.conf"
    blobsfile = folder / "blob-args.conf"
    excludefile = folder / "exclude.conf"
    outputfile = folder / "dvtws.args"
    trafficfile.write_text(traffic, encoding="utf-8")
    for f in (extrafile, blobsfile, excludefile):
        f.write_text("", encoding="utf-8")
    luas = []
    for i in range(3):
        p = folder / f"lib-{i}.lua"
        p.write_text("-- fake initializer for argv assembly test\n", encoding="utf-8")
        luas.append(str(p))
    cmd = [
        "/bin/sh", "-c",
        '. "$1"; . "$2"; shift 2; generator_build_args "$@"',
        "native-generator-test",
        str(BACKEND / "common.sh"), str(BACKEND / "generator.sh"),
        str(outputfile), "989", str(trafficfile),
        str(extrafile), str(blobsfile), str(excludefile), *luas,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError("real generator.sh rejected candidate: " + result.stderr)
    return outputfile.read_text(encoding="utf-8")


def extract_real_ordinary_ports(folder: Path, ordinary: str) -> tuple[str, str]:
    """Use production ports.sh, never infer ports from merged Voice filters."""
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "ordinary.conf"
    tcp = folder / "ordinary.tcp"
    udp = folder / "ordinary.udp"
    source.write_text(ordinary, encoding="utf-8")
    command = [
        "/bin/sh", "-c",
        '. "$1"; . "$2"; shift 2; ports_extract_file "$@"',
        "native-ports-test", str(BACKEND / "common.sh"),
        str(BACKEND / "ports.sh"), str(source), str(tcp), str(udp),
    ]
    response = subprocess.run(command, capture_output=True, text=True, check=False)
    if response.returncode:
        raise AssertionError("production ordinary ports extractor failed: " + response.stderr)
    return tcp.read_text(encoding="utf-8").strip(), udp.read_text(encoding="utf-8").strip()


class GeneratorInteropTests(unittest.TestCase):
    def compile(self, root: Path, *, enabled: bool, ordinary: str = ORDINARY) -> dict:
        xml, managed = fixtures.write_fixture(root, fixtures.fixture(enabled))
        traffic = root / "ordinary.resolved.conf"
        traffic.write_text(ordinary, encoding="utf-8")
        return stage.compile_bundle(
            xml, managed, ACTIVE_ROOT, "vtnet1",
            19000, 19010, 989, traffic,
        )

    def test_voice_enabled_and_ordinary_preserve_single_dvtws2_argv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self.compile(root, enabled=True)
            full = generate_native_argv(root / "builder", bundle["traffic.conf"])
            self.assertEqual(1, full.count("--port=989\n"))
            self.assertEqual(3, full.count("--lua-init=@"))
            self.assertEqual(1, full.count("--name=voice-telegram\n"))
            self.assertLess(full.index("--name=voice-telegram"), full.index("--filter-tcp=443"))
            self.assertIn(ORDINARY, full)
            self.assertEqual(ORDINARY, bundle["traffic.conf"][-len(ORDINARY):])
            self.assertNotIn("--name=telegram-voice-poc", full)
            meta = json.loads(bundle["metadata.json"])
            self.assertFalse(meta["activation_authorized"])
            self.assertEqual(1, meta["profile_count"])
            plan = json.loads(bundle["capture-plan.json"])
            tcp, udp = extract_real_ordinary_ports(root / "port-extractor", ORDINARY)
            self.assertEqual(("443", "596-599"), (tcp, udp))
            desired = firewall.prepare_desired(plan, tcp, udp)
            self.assertEqual([19000, 19001, 19002], sorted(desired["rules"]))
            self.assertEqual("table(zapret2_voice_telegram)", desired["rules"][19000][6])
            self.assertEqual("tcp", desired["rules"][19001][2])
            self.assertEqual("udp", desired["rules"][19002][2])
            self.assertEqual({"zapret2_voice_telegram": ["91.108.0.0/16", "91.108.13.10"]},
                             desired["tables"])

    def test_all_voice_off_preserves_ordinary_bytes_and_engine_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self.compile(root, enabled=False)
            self.assertEqual(ORDINARY, bundle["traffic.conf"])
            full = generate_native_argv(root / "builder", bundle["traffic.conf"])
            self.assertNotIn("--name=voice-", full)
            self.assertIn(ORDINARY, full)
            self.assertEqual(1, full.count("--port=989\n"))
            plan = json.loads(bundle["capture-plan.json"])
            tcp, udp = extract_real_ordinary_ports(root / "port-extractor", ORDINARY)
            self.assertEqual(("443", "596-599"), (tcp, udp))
            desired = firewall.prepare_desired(plan, tcp, udp)
            self.assertEqual([19000, 19001], sorted(desired["rules"]))
            self.assertEqual({}, desired["tables"])

    def test_old_poc_or_ordinary_stun_conflict_fails_before_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            for number, bad in enumerate((
                "--name=telegram-voice-poc\n" + ORDINARY,
                "--filter-udp=*\n--filter-l7=stun\n--payload=stun\n",
            )):
                root = Path(tmp) / str(number)
                root.mkdir()
                with self.subTest(bad=bad):
                    with self.assertRaises(ValueError):
                        self.compile(root, enabled=True, ordinary=bad)
                    self.assertFalse((root / "builder").exists())

if __name__ == "__main__":
    unittest.main(verbosity=2)
