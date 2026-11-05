#!/usr/bin/env python3
"""Offline refusal and config-retention tests for real native firmware remove."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "native_removal", HERE / "stage2-opnsense-real-native-remove.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def xml(plugin_names="os-zapret2-restyle,other", saved="<Zapret><enabled>0</enabled>"
            "<custom>sentinel-sensitive-value</custom></Zapret>",
        other="<hostname>opnsense</hostname>"):
    return (f"<opnsense><system>{other}<firmware><type>community</type>"
            f"<plugins>{plugin_names}</plugins></firmware></system>"
            f"<OPNsense>{saved}</OPNsense><revision><time>1</time></revision>"
            "</opnsense>").encode()


class RealNativeFirmwareRemovalTests(unittest.TestCase):
    def test_current_revision_comes_from_makefile(self):
        self.assertEqual(mod.VERSION, "0.6.2_" +
                         mod.revision_from_makefile())

    def test_optin_refuses_before_any_pkg_or_config(self):
        with patch.dict(mod.os.environ, {mod.OPTIN: "",
                                         "GITHUB_ACTIONS": "true",
                                         "ZAPRET2_NATIVE_BUILD_CI": "1"}), \
             patch.object(mod.native, "gate") as guest:
            with self.assertRaisesRegex(mod.Refusal, "OPTIN_REQUIRED"):
                mod.preflight()
            guest.assert_not_called()

    def test_qualifies_registration_removal_and_saved_config(self):
        before = xml()
        after = xml("other").replace(b"<time>1</time>", b"<time>2</time>")
        result = mod.check_official_unregistration(before, after)
        self.assertTrue(result["plugin_removed_from_firmware_registry"])
        self.assertTrue(result["saved_zapret_config_present"])
        self.assertTrue(result["saved_zapret_config_retained_when_present"])
        self.assertTrue(result["other_config_preserved_semantically"])

    def test_disposable_saved_config_seeds_without_overwriting_user_state(self):
        with patch.object(mod.CONFIG.__class__, "read_bytes", return_value=xml()), \
             patch.object(mod.clean, "run") as command:
            with self.assertRaisesRegex(
                    mod.Refusal, "ZAPRET_CONFIG_ALREADY_PRESENT"):
                mod.seed_saved_config_for_disposable_guest()
            command.assert_not_called()

    def test_disposable_saved_config_uses_opnsense_php_config_api(self):
        fixture = ("<Zapret><enabled>0</enabled>"
                   "<nativeRemovalRetention>" + mod.SAVED_CONFIG_SENTINEL +
                   "</nativeRemovalRetention></Zapret>")
        before = xml(saved="")
        after = xml(saved=fixture)
        result = type("Result", (), {"returncode": 0, "stderr": ""})()
        with patch.object(mod.CONFIG.__class__, "read_bytes",
                          side_effect=[before, after]), \
             patch.object(mod.clean, "run", return_value=result) as command:
            self.assertTrue(mod.seed_saved_config_for_disposable_guest())
        args = command.call_args.args[0]
        self.assertEqual(args[:2], ["/usr/local/bin/php", "-r"])
        self.assertIn("Config::getInstance()->save()", args[2])
        self.assertIn(mod.SAVED_CONFIG_SENTINEL, args[2])

    def test_rejects_unregistered_or_foreign_plugin_change(self):
        for after in (xml(), xml(""), xml("other,foreign"),
                      xml("os-zapret2-restyle,other,foreign")):
            with self.subTest(after=after), self.assertRaises(mod.Refusal):
                mod.check_official_unregistration(xml(), after)

    def test_rejects_mutated_zapret_settings_on_removal(self):
        after = xml("other", "<Zapret><enabled>1</enabled>"
                    "<custom>sentinel-sensitive-value</custom></Zapret>")
        with self.assertRaisesRegex(mod.Refusal, "SAVED_CONFIG_MODIFIED"):
            mod.check_official_unregistration(xml(), after)

    def test_rejects_changed_unrelated_system_config(self):
        with self.assertRaisesRegex(mod.Refusal, "UNRELATED_CONFIG"):
            mod.check_official_unregistration(
                xml(), xml("other", other="<hostname>changed</hostname>"))

    def test_rejects_plugin_list_duplicates_and_bad_xml(self):
        for before in (xml("other,other,os-zapret2-restyle"),
                       b"<opnsense><system>"):
            with self.subTest(before=before), self.assertRaises(mod.Refusal):
                mod.check_official_unregistration(before, xml("other"))

    def test_does_not_claim_saved_config_when_not_present(self):
        before = xml(saved="")
        after = xml("other", saved="")
        result = mod.check_official_unregistration(before, after)
        self.assertFalse(result["saved_zapret_config_present"])

    def test_source_uses_real_native_pkg_remove_and_official_registry(self):
        source = (HERE / "stage2-opnsense-real-native-remove.py").read_text()
        self.assertIn('["pkg", "-o", "REPO_AUTOUPDATE=false", "delete", "-y", NAME]', source)
        self.assertIn('clean.installed_pkg_manifest(archive)', source)
        self.assertIn('REGISTRATION, "remove", NAME', source)
        self.assertIn("PKG_DELETE_CHANGED_CONFIG_BEFORE_OFFICIAL_UNREGISTER", source)
        self.assertIn("NATIVE_REMOVAL_DID_NOT_PROVE_POPULATED_CONFIG_RETENTION", source)
        self.assertNotIn('"pkg", "delete", "-f"', source)
        self.assertNotIn('"pkg", "delete", "-I"', source)
        self.assertNotIn('"pkg", "autoremove"', source)
        self.assertNotIn('register.php install', source)
        self.assertIn('"post_deinstall_independently_traced": False', source)


if __name__ == "__main__":
    unittest.main()
