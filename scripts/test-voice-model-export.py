#!/usr/bin/env python3
"""Native config.xml → Voice JSON → dvtws2/IPFW candidate chain."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"


def module(name):
    spec = importlib.util.spec_from_file_location(name, BACKEND / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


exporter = module("voice_model_export")
compiler = module("voice_profile_compiler")
planner = module("voice_capture_plan")
MANAGED = Path("/usr/local/etc/zapret2/runtime-v2/managed")
STUN = "--filter-udp=*\n--filter-l7=stun\n--payload=stun"


def fixture(enable_telegram=True):
    root = ET.Element("opnsense")
    settings = ET.SubElement(ET.SubElement(root, "OPNsense"), "Zapret")
    general = ET.SubElement(settings, "general")
    ET.SubElement(general, "waninterface").text = "WAN"
    voice = ET.SubElement(settings, "voice")
    ET.SubElement(voice, "waninterface").text = ""
    telegram = ET.SubElement(voice, "telegram")
    ET.SubElement(telegram, "enabled").text = "1" if enable_telegram else "0"
    ET.SubElement(telegram, "args").text = STUN
    hostlist = ET.SubElement(settings, "hostlist")
    ET.SubElement(hostlist, "telegramips").text = "91.108.0.0/16\n91.108.13.10"
    ET.SubElement(hostlist, "discordips").text = "203.0.113.0/24"
    unrelated = ET.SubElement(root, "squid")
    ET.SubElement(unrelated, "password").text = "NEVER_EXPORT_SECRET"
    return root


class NativeModelBridgeTests(unittest.TestCase):
    def test_native_model_to_one_engine_profile_and_scoped_ipfw_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"config.xml"
            ET.ElementTree(fixture()).write(source, encoding="utf-8")
            state = exporter.read_voice_model(source)
            self.assertEqual("WAN", state["strategy_wan"])
            self.assertEqual("91.108.0.0/16\n91.108.13.10",
                             state["services"]["telegram"]["ips"])
            self.assertFalse(state["services"]["discord"]["enabled"])
            self.assertFalse(state["services"]["custom"]["enabled"])
            self.assertNotIn("squid", json.dumps(state))
            self.assertNotIn("NEVER_EXPORT_SECRET", json.dumps(state))
            text, profile_plan = compiler.compile_candidate(state, MANAGED)
            self.assertIn("--name=voice-telegram", text)
            self.assertNotIn("--name=voice-discord", text)
            capture = planner.compile_capture_plan(profile_plan, 19000, 19010, 989)
            self.assertEqual(1, len(capture["voice"]))
            self.assertEqual(19001, capture["ordinary_rule_base"])
            self.assertEqual("table(zapret2_voice_telegram)", capture["voice"][0]["argv"][6])

    def test_absent_voice_section_is_all_off_and_preserves_strategies(self):
        root = fixture()
        settings = root.find("./OPNsense/Zapret")
        settings.remove(settings.find("voice"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"config.xml"
            ET.ElementTree(root).write(source, encoding="utf-8")
            state = exporter.read_voice_model(source)
            self.assertEqual("WAN", state["strategy_wan"])
            self.assertTrue(all(not item["enabled"] for item in state["services"].values()))
            strategy, plan = compiler.compile_candidate(state, MANAGED)
            self.assertEqual("", strategy)
            self.assertEqual([], plan["profiles"])

    def test_rejects_corrupt_enable_and_does_not_clobber_previous_export(self):
        root = fixture()
        root.find("./OPNsense/Zapret/voice/telegram/enabled").text = "yes; execute"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"config.xml"
            out = Path(tmp)/"state.json"
            out.write_text("previous", encoding="utf-8")
            ET.ElementTree(root).write(path, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(BACKEND/"voice_model_export.py"),
                 str(path), str(out)],
                capture_output=True, text=True
            )
            self.assertNotEqual(0, proc.returncode)
            self.assertIn("voice.telegram.enabled", proc.stderr)
            self.assertEqual("previous", out.read_text())

    def test_cli_writes_private_json_without_squids_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"config.xml"
            out = Path(tmp)/"state.json"
            ET.ElementTree(fixture()).write(path, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(BACKEND/"voice_model_export.py"),
                 str(path), str(out)],
                capture_output=True, text=True
            )
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual(0o600, out.stat().st_mode & 0o777)
            contents = out.read_text()
            self.assertNotIn("NEVER_EXPORT_SECRET", contents)
            self.assertTrue(json.loads(contents)["services"]["telegram"]["enabled"])

    def test_malformed_xml_fails_without_creating_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"config.xml"
            out = Path(tmp)/"state.json"
            path.write_text("<opnsense><OPNsense>", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable,str(BACKEND/"voice_model_export.py"),
                 str(path),str(out)],
                capture_output=True,text=True
            )
            self.assertNotEqual(0, proc.returncode)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
