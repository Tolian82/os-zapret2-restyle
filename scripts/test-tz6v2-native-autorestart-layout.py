#!/usr/bin/env python3
"""TZ6v2 portable native form/GUI source contract, NOT installed UI proof."""
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/forms/general.xml"
MODEL = ROOT / "src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml"
VIEW = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"


class AutoRestartNativeForm(unittest.TestCase):
    def test_separate_enabled_and_schedule(self):
        form = ET.parse(FORM).getroot()
        by_id = {f.findtext("id"): f for f in form.findall("./field")
                 if f.find("id") is not None}
        enabled = by_id["zapret.general.enabled"]
        restart = by_id["zapret.general.autorestart"]
        self.assertEqual((enabled.findtext("type"), enabled.findtext("label")),
                         ("checkbox", "Enable"))
        self.assertEqual((restart.findtext("type"), restart.findtext("label")),
                         ("dropdown", "Auto Restart"))
        self.assertEqual(restart.findtext("advanced"), "true")
        self.assertIsNot(enabled, restart)

    def test_model_options_unchanged(self):
        control = ET.parse(MODEL).getroot().find("./items/general/autorestart")
        self.assertEqual(control.get("type"), "OptionField")
        self.assertEqual(control.findtext("Default"), "off")
        self.assertEqual([o.tag for o in control.findall("./OptionValues/*")],
                         ["off", "hourly", "daily", "weekly", "monthly"])

    def test_original_native_row_is_not_moved_by_javascript(self):
        page = VIEW.read_text()
        self.assertNotIn("mountAdvancedAutoRestart()", page)
        self.assertNotIn("zapretAutoRestartInline", page)
        self.assertNotIn("actual.detach()", page)
        self.assertIn("localizeAutoRestartOptions();", page)
        self.assertEqual(page.count('id="reconfigureAct"'), 1)

    def test_native_browser_expects_new_separate_schedule_row(self):
        browser = (ROOT / "scripts/p3-browser-i18n.py").read_text()
        self.assertIn("P4_RESTART_NOT_SEPARATE_NATIVE_ROW", browser)
        self.assertIn("row_zapret.general.autorestart", browser)
        self.assertNotIn("zapretAutoRestartInline", browser)
        self.assertNotIn("P4_RESTART_NOT_INLINE_RIGHT_OF_ENABLED", browser)


if __name__ == "__main__":
    unittest.main()
