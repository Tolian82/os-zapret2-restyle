#!/usr/bin/env python3
"""Legacy transient Telegram PoC migration never auto-infers durable ON."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
spec = importlib.util.spec_from_file_location("voice_migration_plan", BACKEND / "voice_migration_plan.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config(path, *, telegram=None, discord=None):
    root=ET.Element("opnsense")
    plugin=ET.SubElement(ET.SubElement(root, "OPNsense"), "Zapret")
    ET.SubElement(ET.SubElement(plugin,"general"),"enabled").text="1"
    if telegram is not None or discord is not None:
        voice=ET.SubElement(plugin, "voice")
        if telegram is not None:
            ET.SubElement(ET.SubElement(voice,"telegram"),"enabled").text=telegram
        if discord is not None:
            ET.SubElement(ET.SubElement(voice,"discord"),"enabled").text=discord
    ET.ElementTree(root).write(path, encoding="utf-8")


class MigrationTests(unittest.TestCase):
    def setup_paths(self, d, **kwargs):
        root=Path(d)
        xml=root/"config.xml"
        config(xml,**kwargs)
        marker=root/"old.enabled"
        runtime=root/"active"
        runtime.mkdir()
        return xml,marker,runtime

    def test_clean_install_defaults_off_without_new_enabled_state(self):
        with tempfile.TemporaryDirectory() as d:
            xml,marker,active=self.setup_paths(d)
            report=module.assess(xml,marker,active)
            self.assertEqual("unselected-default-off",report["condition"])
            self.assertFalse(report["has_persisted_selection"])
            self.assertFalse(any(report["services"].values()))
            self.assertFalse(report["may_activate_without_lifecycle"])

    def test_running_old_marker_requires_owner_selection_not_auto_on(self):
        with tempfile.TemporaryDirectory() as d:
            xml,marker,active=self.setup_paths(d)
            marker.write_text("enabled\n")
            report=module.assess(xml,marker,active)
            self.assertEqual("operator-selection-required",report["condition"])
            self.assertFalse(report["may_stage_candidate"])
            self.assertFalse(report["has_persisted_selection"])

    def test_explicit_persisted_on_and_off_both_require_cutover_if_old_on(self):
        for selected in ("1","0"):
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as d:
                xml,marker,active=self.setup_paths(d,telegram=selected)
                marker.write_text("enabled\n")
                report=module.assess(xml,marker,active)
                self.assertEqual("legacy-atomic-cutover-required",report["condition"])
                self.assertEqual(selected=="1",report["services"]["telegram"])
                self.assertTrue(report["may_stage_candidate"])
                self.assertTrue(report["remove_legacy_only_after_confirmed_cutover"])

    def test_old_running_without_marker_is_an_inconsistent_live_state(self):
        with tempfile.TemporaryDirectory() as d:
            xml,marker,active=self.setup_paths(d,telegram="1")
            (active/"telegram-voice-poc.state").write_text("enabled\n")
            report=module.assess(xml,marker,active)
            self.assertEqual("unresolved-legacy-running",report["condition"])
            self.assertFalse(report["may_stage_candidate"])

    def test_native_selected_discord_does_not_enable_telegram(self):
        with tempfile.TemporaryDirectory() as d:
            xml,marker,active=self.setup_paths(d,discord="1")
            report=module.assess(xml,marker,active)
            self.assertEqual("persisted-voice-preference",report["condition"])
            self.assertFalse(report["services"]["telegram"])
            self.assertTrue(report["services"]["discord"])

    def test_corrupt_marker_and_corrupt_native_preference_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            xml,marker,active=self.setup_paths(d,telegram="true")
            with self.assertRaisesRegex(module.VoiceMigrationError,"invalid persisted"):
                module.assess(xml,marker,active)
            config(xml,telegram="0")
            marker.write_text("anything")
            with self.assertRaisesRegex(module.VoiceMigrationError,"unexpected content"):
                module.assess(xml,marker,active)
            marker.unlink()
            marker.symlink_to(xml)
            with self.assertRaisesRegex(module.VoiceMigrationError,"unsafe"):
                module.assess(xml,marker,active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
