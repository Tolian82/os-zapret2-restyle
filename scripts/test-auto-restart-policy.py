#!/usr/bin/env python3
"""#1052: one small source contract for the independent opt-in Auto Restart.

No VM or cron firing. Runtime status/FD9 and native Config are the only
authorities; the 60-second Auto-detect tick is never a restart.
"""
from __future__ import annotations

import configparser
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MODEL = SRC / "opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml"
FORM = SRC / "opnsense/mvc/app/controllers/OPNsense/Zapret/forms/general.xml"
ACTIONS = SRC / "opnsense/service/conf/actions.d/actions_zapret.conf"
CRON = SRC / "etc/cron.d/zapret2-restyle"
SERVICE = SRC / "opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
CONFIG = SRC / "opnsense/scripts/OPNsense/Zapret/shared_apply_config.php"
MINUTE = SRC / "opnsense/scripts/OPNsense/Zapret/backend/auto_detect_minute.py"
ALLOWED = ("off", "hourly", "daily", "weekly", "monthly")


class AutoRestartNativePolicy(unittest.TestCase):
    def test_saved_enum_and_advanced_only_field(self):
        model = ET.parse(MODEL).getroot()
        node = model.find("./items/general/autorestart")
        self.assertIsNotNone(node)
        self.assertEqual(node.attrib.get("type"), "OptionField")
        self.assertEqual(node.findtext("Default"), "off")
        self.assertEqual(tuple(x.tag for x in node.findall("OptionValues/*")), ALLOWED)
        field = ET.parse(FORM).getroot().find(
            ".//field[id='zapret.general.autorestart']")
        self.assertIsNotNone(field)
        self.assertEqual(field.findtext("advanced"), "true")

    def test_one_native_configd_action_and_fixed_system_cron(self):
        cfg = configparser.RawConfigParser(interpolation=None)
        self.assertTrue(cfg.read(ACTIONS))
        self.assertEqual(cfg["auto_restart_tick"]["parameters"], "%s")
        self.assertIn("auto-restart-tick",
                      cfg["auto_restart_tick"]["command"])
        # Restart is the normal common Stop + Boot transaction, which can
        # legitimately exceed the minute worker's timeout on OPNsense.
        self.assertEqual(cfg["auto_restart_tick"]["timeout"], "600")
        self.assertEqual(cfg["auto_detect_minute"]["timeout"], "60")
        self.assertEqual(cfg["auto_detect_minute"]["parameters"], "")
        rows = [x.strip() for x in CRON.read_text().splitlines()
                if x.strip() and not x.startswith("#") and not x.startswith(("SHELL=", "PATH=", "MAILTO="))]
        self.assertEqual(len(rows), 5)
        expected = {
            "auto_detect_minute": "* * * * *",
            "hourly": "0 * * * *", "daily": "0 3 * * *",
            "weekly": "0 3 * * 0", "monthly": "0 3 1 * *",
        }
        for row in rows:
            pieces = row.split()
            self.assertEqual(pieces[5], "root")
            self.assertEqual(pieces[6:8], ["/usr/local/sbin/configctl", "-d"])
            name = pieces[9] if pieces[8] == "zapret" else None
            key = pieces[10] if name == "auto_restart_tick" else name
            self.assertIn(key, expected)
            self.assertEqual(" ".join(pieces[:5]), expected.pop(key))
        self.assertEqual(expected, {})

    def test_original_owner_and_stopped_gate_no_minute_restart(self):
        service = SERVICE.read_text()
        php = CONFIG.read_text()
        minute = MINUTE.read_text()
        self.assertIn("shared_apply_auto_restart_tick_service()", service)
        self.assertIn("shared_apply_status_observe_service", service)
        self.assertIn("stopped:2)", service)
        self.assertIn('shared_apply_stop_service "$_auto_restart_owner"', service)
        self.assertIn('shared_apply_boot_service "$_auto_restart_owner"', service)
        self.assertIn("SharedApplyLifecycleLock::assertHeld();", php)
        self.assertIn("autoRestartPreference", php)
        self.assertIn("run_native_original_v2_cycle_once()", minute)
        self.assertIn("require_lifecycle_lock()", minute)
        self.assertIn("auto-detect-minute",
                      (SRC / "opnsense/service/conf/actions.d/actions_zapret.conf").read_text())
        self.assertNotIn("launcher_stop", minute)
        self.assertNotIn("SIGSTOP", minute)
        self.assertNotIn("SIGCONT", minute)


if __name__ == "__main__":
    unittest.main(verbosity=2)
