#!/usr/bin/env python3
"""Offline negative contract tests for real versioned disposable native pkg gate."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "stage0_versioned", HERE / "stage0-opnsense-versioned-native-pkg.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HOOKS = {"pre-install": "#!/bin/sh\nexit 0\n",
         "post-install": "#!/bin/sh\nexit 0\n",
         "pre-deinstall": "#!/bin/sh\nexit 0\n",
         "post-deinstall": "#!/bin/sh\nexit 0\n"}


def manifest(version):
    return {"name": mod.NAME, "version": version, "origin": "opnsense/" + mod.NAME,
            "arch": "freebsd:15:x86:64", "abi": "FreeBSD:15:amd64",
            "prefix": "/usr/local", "scripts": dict(HOOKS),
            "files": {"/usr/local/f" + str(i): "abc" for i in range(20)},
            "deps": {"python313": {"origin": "lang/python313", "version": "0"}}}


class VersionedTests(unittest.TestCase):
    def test_optin_refuses_non_ci_without_guest_probe(self):
        with mock.patch.dict(os.environ, {mod.OPTIN: "0", "GITHUB_ACTIONS": "true"}):
            with mock.patch.object(mod, "load") as loaded:
                with self.assertRaisesRegex(mod.Refusal, "OPTIN"):
                    mod.qualify()
                loaded.assert_not_called()

    def test_real_old_package_is_not_same_version(self):
        self.assertNotEqual(mod.OLD_VERSION, mod.TEST_VERSION)
        self.assertEqual(mod.NAME, "os-zapret2-restyle")
        self.assertEqual(mod.TEST_VERSION, "0.6.2_56")

    def test_valid_candidate_preserves_all_old_fields(self):
        mod.compare_manifest(manifest(mod.OLD_VERSION), manifest(mod.TEST_VERSION))

    def test_manifest_refuses_different_hook(self):
        new = manifest(mod.TEST_VERSION)
        new["scripts"]["post-install"] = "#!/bin/sh\nexit 2\n"
        with self.assertRaisesRegex(mod.Refusal, "HOOKS_CHANGED"):
            mod.compare_manifest(manifest(mod.OLD_VERSION), new)

    def test_manifest_refuses_missing_post_deinstall(self):
        old = manifest(mod.OLD_VERSION)
        del old["scripts"]["post-deinstall"]
        with self.assertRaisesRegex(mod.Refusal, "HOOKS_CHANGED"):
            mod.compare_manifest(old, manifest(mod.TEST_VERSION))

    def test_manifest_refuses_modified_files(self):
        candidate = manifest(mod.TEST_VERSION)
        candidate["files"]["/usr/local/foreign"] = "abc"
        with self.assertRaisesRegex(mod.Refusal, "FILE_MANIFEST_CHANGED"):
            mod.compare_manifest(manifest(mod.OLD_VERSION), candidate)

    def test_manifest_refuses_unexpected_origin_and_abi(self):
        for field in ("origin", "arch", "abi", "prefix"):
            candidate = manifest(mod.TEST_VERSION)
            candidate[field] = "foreign"
            with self.subTest(field=field), self.assertRaisesRegex(
                    mod.Refusal, "PROVENANCE_CHANGED"):
                mod.compare_manifest(manifest(mod.OLD_VERSION), candidate)

    def test_native_resolved_dependency_requires_exact_installed_provider(self):
        old = manifest(mod.OLD_VERSION)
        created = manifest(mod.TEST_VERSION)
        created["deps"]["python313"]["version"] = "3.13.14"
        provider = {"python313": {"origin": "lang/python313", "version": "3.13.14"}}
        mod.compare_manifest(old, created, provider)
        with self.assertRaisesRegex(mod.Refusal, "DEPENDENCIES_CHANGED"):
            mod.compare_manifest(old, created)
        with self.assertRaisesRegex(mod.Refusal, "DEPENDENCIES_CHANGED"):
            mod.compare_manifest(old, created, {"python313": {
                "origin": "lang/python313", "version": "3.13.13"}})
        created["deps"]["python313"]["origin"] = "foreign/python313"
        with self.assertRaisesRegex(mod.Refusal, "DEPENDENCIES_CHANGED"):
            mod.compare_manifest(old, created, provider)

    def test_actual_pkg_dependency_provider_rejects_mismatched_origin(self):
        old = manifest(mod.OLD_VERSION)
        with mock.patch.object(mod, "command", return_value=subprocess.CompletedProcess(
                ["pkg"], 0, "python313|foreign/python313|3.13.14\n", "")):
            with self.assertRaisesRegex(mod.Refusal, "PROVIDER_MISMATCH"):
                mod.provider_versions(old)

    def test_actual_pkg_dependency_provider_matches_exact_name_origin_and_version(self):
        old = manifest(mod.OLD_VERSION)
        with mock.patch.object(mod, "command", return_value=subprocess.CompletedProcess(
                ["pkg"], 0, "python313|lang/python313|3.13.14\n", "")) as caller:
            self.assertEqual(mod.provider_versions(old), {
                "python313": {"origin": "lang/python313", "version": "3.13.14"}})
            caller.assert_called_once_with(
                ["pkg", "query", "%n|%o|%v", "python313"], timeout=20)

    def test_manifest_refuses_wrong_version_and_dependencies(self):
        new = manifest(mod.OLD_VERSION)
        with self.assertRaisesRegex(mod.Refusal, "IDENTITY_MISMATCH"):
            mod.compare_manifest(manifest(mod.OLD_VERSION), new)
        new["version"] = mod.TEST_VERSION
        new["deps"] = {}
        with self.assertRaisesRegex(mod.Refusal, "DEPENDENCIES_CHANGED"):
            mod.compare_manifest(manifest(mod.OLD_VERSION), new)

    def test_native_command_failure_closes_gate(self):
        with mock.patch.object(mod.subprocess, "run", side_effect=OSError):
            with self.assertRaisesRegex(mod.Refusal, "NATIVE_COMMAND"):
                mod.command(["pkg", "info"])

    def test_install_state_requires_exact_successor_and_owner(self):
        old = mock.Mock()
        old.installed_manifest_from_json.side_effect = lambda s: json.loads(s)
        old.SERVICE = "/tmp/stage0-test-service-absent"
        inspector = mock.Mock()
        with tempfile.TemporaryDirectory() as d:
            package = Path(d) / "new.pkg"
            package.write_bytes(b"known")
            sha = __import__("hashlib").sha256(b"known").hexdigest()
            with mock.patch.object(mod, "command",
                    return_value=subprocess.CompletedProcess(
                        ["pkg"], 0, json.dumps(manifest(mod.OLD_VERSION)), "")):
                with self.assertRaisesRegex(mod.Refusal, "IDENTITY_MISMATCH"):
                    mod.installed_successor(package, sha, b"x",
                        manifest(mod.OLD_VERSION), None, old, inspector)

    def test_refuse_changed_candidate_before_pkgdb_inspection(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "package.pkg"
            path.write_bytes(b"unexpected")
            with mock.patch.object(mod, "command") as run:
                with self.assertRaisesRegex(mod.Refusal, "ARCHIVE_CHANGED"):
                    mod.installed_successor(path, "0"*64, b"x",
                        manifest(mod.OLD_VERSION), None, mock.Mock(), mock.Mock())
                run.assert_not_called()

    def test_success_report_cannot_claim_official_production_atomicity(self):
        source = (HERE / "stage0-opnsense-versioned-native-pkg.py").read_text()
        for token in ('"official_native_opnsense_build_tested": False',
                      '"production_new_code_successor_tested": False',
                      '"running_replacement_tested": False',
                      '"crash_atomicity_proved": False',
                      '"direct_root_pkg_bypass_excluded": False',
                      '"stage0_closed": False'):
            self.assertIn(token, source)

    def test_transaction_requires_succeeded_then_faulted_then_old(self):
        source = (HERE / "stage0-opnsense-versioned-native-pkg.py").read_text()
        self.assertLess(source.index("normal = pkg.real_pkg_add(successor)"),
                        source.index("failed = pkg.faulted_real_pkg_add(successor)"))
        self.assertIn("old.run_guest(archive, hostname) == initial", source)
        self.assertIn("pkg.snapshot(archive, inspector)", source)
        self.assertIn("pkg.same_config(original_config)", source)


if __name__ == "__main__":
    unittest.main()
