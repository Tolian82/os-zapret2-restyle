#!/usr/bin/env python3
"""Offline negative controls for real native clean-install acceptance."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "native_installed", HERE / "stage2-opnsense-real-native-clean-install.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RealInstallContracts(unittest.TestCase):
    def test_bound_to_real_source_revision(self):
        self.assertEqual(mod.REVISION, "75")
        self.assertEqual(mod.VERSION, "0.6.2_75")
        self.assertEqual(mod.native.REVISION, "75")

    def test_explicit_cold_install_optin_required(self):
        with patch.dict(os.environ, {mod.OPTIN: "", "GITHUB_ACTIONS": "true",
                                      "ZAPRET2_NATIVE_BUILD_CI": "1"}):
            with self.assertRaisesRegex(mod.Refusal, "OPTIN_REQUIRED"):
                mod.preflight()

    def test_prior_pkgdb_present_refused(self):
        with patch.object(mod, "run") as run:
            run.return_value.returncode = 0
            with self.assertRaisesRegex(mod.Refusal, "NONEMPTY_PLUGIN_PKGDB"):
                mod.plugin_absent()

    def test_nonzero_pkg_add_refused(self):
        with patch.object(mod, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stdout = ""
            run.return_value.stderr = "genuine hook failure"
            with self.assertRaisesRegex(mod.Refusal, "CLEAN_PKG_ADD_FAILED"):
                mod.pkg_add(Path("/tmp/never-used.pkg"))

    def test_success_without_real_postinstall_message_refused(self):
        with patch.object(mod, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "installed without hook"
            run.return_value.stderr = ""
            with self.assertRaisesRegex(mod.Refusal, "ORIGINAL_POST_INSTALL_MESSAGE_NOT_OBSERVED"):
                mod.pkg_add(Path("/tmp/not-a-real-pkg"))

    def test_real_pkg_add_is_not_force_or_no_script(self):
        with patch.object(mod, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "os-zapret2-restyle was installed."
            run.return_value.stderr = ""
            mod.pkg_add(Path("/tmp/fixture.pkg"))
            args = run.call_args.args[0]
        self.assertEqual(args, ["pkg", "-o", "REPO_AUTOUPDATE=false", "add",
                                "/tmp/fixture.pkg"])
        self.assertNotIn("-f", args)
        self.assertNotIn("-I", args)

    def test_discard_foreign_install_manifest(self):
        example = {"name": mod.NAME, "version": mod.VERSION,
                   "origin": "opnsense/" + mod.NAME, "arch": "freebsd:15:x86:64",
                   "abi": mod.native.validated_policy()["supported_platforms"][0]["freebsd_pkg_abi"],
                   "deps": {"python313":{"origin":"lang/python313","version":"3.13.14"}},
                   "scripts": {x:"#!/bin/sh\nexit 0\n"
                               for x in mod.native.HOOKS.values()}}
        with patch.object(mod, "required") as req, patch.object(
                mod.prior, "installed_manifest_from_json",
                return_value=dict(example, origin="foreign/repository")):
            req.side_effect = [json.dumps(example), json.dumps(example)]
            with self.assertRaisesRegex(mod.Refusal, "PKGDB_FIELD_CHANGED"):
                mod.installed_pkg_manifest(Path("/tmp/never-used.pkg"))

    def test_discard_modified_postinstall_hook(self):
        scripts = {x:"#!/bin/sh\nexit 0\n"
                   for x in mod.native.HOOKS.values()}
        a = {"name": mod.NAME, "version": mod.VERSION,
             "origin": "opnsense/"+mod.NAME, "arch": "freebsd:15:x86:64",
             "abi": mod.native.validated_policy()["supported_platforms"][0]["freebsd_pkg_abi"], "deps":{}, "scripts":scripts}
        changed = {**a, "scripts":{**scripts, "post-install":"#!/bin/sh\nexit 71\n"}}
        with patch.object(mod, "required") as req, patch.object(
                mod.prior, "installed_manifest_from_json",return_value=changed):
            req.side_effect=[json.dumps(a),json.dumps(changed)]
            with self.assertRaisesRegex(mod.Refusal, "HOOKS_MISMATCH"):
                mod.installed_pkg_manifest(Path("/tmp/never-used.pkg"))

    def test_cold_service_requires_real_stopped(self):
        p = type("Result", (), {"returncode":2, "stdout":"", "stderr":""})()
        with patch.object(mod, "run",return_value=p):
            with self.assertRaisesRegex(mod.Refusal, "NOT_STOPPED"):
                mod.cold_status()

    def test_config_diagnostic_reports_only_safe_section_names(self):
        old = (b"<opnsense><OPNsense><Zapret><password>secret-one</password>"
               b"</Zapret></OPNsense></opnsense>")
        new = (b"<opnsense><OPNsense><Zapret><password>secret-two</password>"
               b"</Zapret></OPNsense></opnsense>")
        record = mod.config_structure_diagnostic(old, new)
        self.assertEqual(record["changed_sections"],
                         [{"section":"OPNsense", "changed_children":["Zapret"],
                           "child_count":1}])
        self.assertNotIn("secret", json.dumps(record))
        unknown = mod.config_structure_diagnostic(
            b"<opnsense><unknown><mytoken>a</mytoken></unknown></opnsense>",
            b"<opnsense><unknown><mytoken>b</mytoken></unknown></opnsense>")
        self.assertEqual(unknown["changed_sections"], [{"section":"other"}])

    def test_genuine_first_install_firmware_registry_only(self):
        old = (b'<opnsense><system><hostname>test</hostname><firmware>'
               b'<plugins>other</plugins><type>community</type>'
               b'</firmware></system><revision><time>1</time></revision>'
               b'<OPNsense><secret>unchanged</secret></OPNsense></opnsense>')
        new = old.replace(b'<plugins>other</plugins>',
                          b'<plugins>os-zapret2-restyle,other</plugins>').replace(
                              b'<time>1</time>',b'<time>2</time>')
        observed = mod.verify_official_first_install_registration(old,new)
        self.assertEqual(observed["status"],"PASS_OFFICIAL_FIRMWARE_REGISTER_ONLY")
        self.assertTrue(observed["all_other_config_sections_unchanged"])
        self.assertEqual(observed["prior_plugin_count"],1)

    def test_fresh_registration_creates_initial_firmware_section(self):
        old = b'<opnsense><system><hostname>test</hostname></system></opnsense>'
        new = (b'<opnsense><system><hostname>test</hostname><firmware>'
               b'<plugins>os-zapret2-restyle</plugins><type>community</type>'
               b'</firmware></system><revision><time>2</time></revision></opnsense>')
        self.assertTrue(mod.verify_official_first_install_registration(
            old,new)["allowed_new_firmware_type"])

    def test_unrelated_system_config_change_is_rejected(self):
        old = (b'<opnsense><system><hostname>test</hostname></system></opnsense>')
        new = (b'<opnsense><system><hostname>compromised</hostname>'
               b'<firmware><plugins>os-zapret2-restyle</plugins></firmware>'
               b'</system><revision><time>2</time></revision></opnsense>')
        with self.assertRaisesRegex(mod.Refusal, "UNAUTHORIZED_CONFIG_MUTATION"):
            mod.verify_official_first_install_registration(old,new)

    def test_missing_or_foreign_registry_entry_rejected(self):
        old = b'<opnsense><system><firmware><plugins>other</plugins></firmware></system></opnsense>'
        for plugins in (b'other',b'other,foreign,os-zapret2-restyle'):
            new=(b'<opnsense><system><firmware><plugins>'+plugins+
                 b'</plugins></firmware></system><revision/></opnsense>')
            with self.subTest(plugins=plugins), self.assertRaisesRegex(
                    mod.Refusal, "INSTALL_PLUGIN_REGISTRY"):
                mod.verify_official_first_install_registration(old,new)

    def test_existing_firmware_type_must_not_change(self):
        old=(b'<opnsense><system><firmware><type>community</type>'
             b'</firmware></system></opnsense>')
        new=(b'<opnsense><system><firmware><type>business</type>'
             b'<plugins>os-zapret2-restyle</plugins></firmware>'
             b'</system><revision/></opnsense>')
        with self.assertRaisesRegex(mod.Refusal, "FIRMWARE_TYPE_WAS_CHANGED"):
            mod.verify_official_first_install_registration(old,new)

    def test_full_installed_source_witness_and_no_false_claim(self):
        source = (HERE / "stage2-opnsense-real-native-clean-install.py").read_text()
        for phrase in ('native.gate()', 'native.build()',
                       'pkg_add(path)', 'installed_pkg_manifest(path)',
                       'verify_installed_files(path, manifest)',
                       'cold_status()', 'verify_official_first_install_registration(config_before,',
                       '"old_predecessor_replacement_tested": False',
                       '"configctl_start_stop_tested": False',
                       '"rollback_and_failure_recovery_tested": False',
                       '"publication_approved": False',
                       '"stage0_closed": False', '"stage1_admitted": False'):
            self.assertIn(phrase,source)

    def test_no_stable_package_or_owner_gateway_touch(self):
        source=(HERE / "stage2-opnsense-real-native-clean-install.py").read_text()
        self.assertNotIn('pkg", "add", "-f"',source)
        self.assertNotIn("pkg-static create",source)
        self.assertNotIn('pkg", "delete"',source)
        self.assertNotIn("gh release",source)


if __name__ == "__main__":
    unittest.main()
