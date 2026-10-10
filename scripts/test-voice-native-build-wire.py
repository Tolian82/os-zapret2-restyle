#!/usr/bin/env python3
"""Exercise the actual orchestrator -> native Voice release compiler path.

The kernel and live OPNsense configuration are NEVER accessed. Tests use
private XML and managed-IPSET files, while verifying the real shell function
that production orchestrator invokes before runtime activation.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
ORCH = BACKEND / "orchestrator.sh"
ACTIVE = "/usr/local/etc/zapret2/runtime-v2"
STUN = "--filter-udp=*\n--filter-l7=stun\n--payload=stun\n--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2"


def prepare(tmp: Path, on: bool) -> tuple[Path, Path, Path]:
    root = ET.Element("opnsense")
    zapret = ET.SubElement(ET.SubElement(root, "OPNsense"), "Zapret")
    general = ET.SubElement(zapret, "general")
    ET.SubElement(general, "waninterface").text = "WAN"
    voice = ET.SubElement(zapret, "voice")
    ET.SubElement(voice, "waninterface").text = ""
    telegram = ET.SubElement(voice, "telegram")
    ET.SubElement(telegram, "enabled").text = "1" if on else "0"
    ET.SubElement(telegram, "args").text = STUN
    hostlist = ET.SubElement(zapret, "hostlist")
    ET.SubElement(hostlist, "telegramips").text = "91.108.13.10\n91.108.0.0/16"
    xml = tmp / "config.xml"
    ET.ElementTree(root).write(xml, encoding="utf-8")
    managed = tmp / "managed"
    managed.mkdir()
    (managed / "ipset-telegram.txt").write_text(
        "91.108.13.10\n91.108.0.0/16\n", encoding="utf-8"
    )
    ordinary = tmp / "traffic-user.conf"
    ordinary.write_text("--filter-tcp=443\n--filter-l7=tls\n", encoding="utf-8")
    return xml, managed, ordinary


def build(xml: Path, managed: Path, ordinary: Path, output: Path, wan: str = "WAN"):
    runner = r"""
set -eu
BACKEND_DIR="$1"
. "$BACKEND_DIR/orchestrator.sh"
common_error() { printf '%s\n' "$*" >&2; }
config_resolve_interface() {
    [ "$1" = "WAN" ] || return 1
    printf 'vtnet1\n'
}
orchestrator_stage_native_voice "$2" "$3" "$4" "$5" \
    19000 19010 989 "$6" "$7"
"""
    return subprocess.run(
        ["/bin/sh", "-c", runner, "voice-native-test", str(BACKEND),
         str(xml), str(managed), ACTIVE, wan, str(ordinary), str(output)],
        capture_output=True, text=True, timeout=30, check=False,
    )


class ActualRuntimeWire(unittest.TestCase):
    def test_normal_build_calls_native_stage_on_real_ordinary_output(self):
        shell = ORCH.read_text(encoding="utf-8")
        source = shell[shell.index("orchestrator_build_release()"):
                       shell.index("orchestrator_cleanup_runtime()")]
        self.assertIn('orchestrator_stage_native_voice \\', source)
        self.assertIn('"/conf/config.xml" \\', source)
        self.assertIn('"${_orchestrator_build_user_traffic}" \\', source)
        self.assertIn('"${_orchestrator_build_managed_source}" \\', source)
        self.assertIn('"${_orchestrator_build_voice_native}"', source)
        self.assertLess(source.index("config_voice_staged_only_guard"),
                        source.index("orchestrator_stage_native_voice"))
        # Old PoC still builds real traffic.conf until full IPFW cutover.
        self.assertLess(source.index("telegram_voice_build_effective_traffic"),
                        source.index("orchestrator_stage_native_voice"))

    def test_native_voice_on_is_built_in_single_engine_traffic_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            xml, managed, ordinary = prepare(tmp, on=True)
            out = tmp / "voice-native-candidate"
            proc = build(xml, managed, ordinary, out)
            self.assertEqual(0, proc.returncode, proc.stderr)
            metadata = json.loads((out / "metadata.json").read_text())
            self.assertFalse(metadata["activation_authorized"])
            self.assertEqual("staged-only", metadata["mode"])
            self.assertEqual(1, metadata["profile_count"])
            traffic = (out / "traffic.conf").read_text()
            self.assertTrue(traffic.startswith("--name=voice-telegram\n"))
            self.assertIn("\n--new\n--filter-tcp=443", traffic)
            self.assertEqual(1, traffic.count("\n--new\n"))
            plan = json.loads((out / "capture-plan.json").read_text())
            self.assertEqual(["telegram"], [item["service"] for item in plan["voice"]])
            self.assertEqual("vtnet1", plan["wan"])
            self.assertEqual("table(zapret2_voice_telegram)", plan["voice"][0]["argv"][6])
            self.assertEqual(19001, plan["ordinary_rule_base"])
            self.assertFalse((tmp / "dvtws.pid").exists())

    def test_all_off_compiles_without_changing_ordinary_traffic(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            xml, managed, ordinary = prepare(tmp, on=False)
            out = tmp / "voice-native-candidate"
            proc = build(xml, managed, ordinary, out)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual("", (out / "voice.conf").read_text())
            self.assertEqual(ordinary.read_text(), (out / "traffic.conf").read_text())
            self.assertEqual([], json.loads((out / "capture-plan.json").read_text())["voice"])

    def test_invalid_wan_or_managed_targets_cannot_publish(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            xml, managed, ordinary = prepare(tmp, on=True)
            bad_wan = tmp / "invalid-wan"
            result = build(xml, managed, ordinary, bad_wan, wan="WAN2")
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(bad_wan.exists())
            (managed / "ipset-telegram.txt").write_text("8.8.8.8\n", encoding="utf-8")
            bad_ipset = tmp / "invalid-targets"
            result = build(xml, managed, ordinary, bad_ipset)
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(bad_ipset.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
