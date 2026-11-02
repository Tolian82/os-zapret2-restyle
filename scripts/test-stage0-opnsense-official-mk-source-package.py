#!/usr/bin/env python3
"""Negative offline contracts for the isolated official Mk source-package witness."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "stage0_official_mk", HERE / "stage0-opnsense-official-mk-source-package.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PROVIDER = {
    "python_runtime": "Python 3.13.14",
    "native_plugin_python": "313",
    "generic_python_link_owner": "opnsense-26.7.8",
    "installed_python_provider": "python313|lang/python313|3.13.14",
}
VARS = {
    "PLUGIN_PKGNAME": mod.NAME, "PLUGIN_PKGVERSION": "0.6.2_58",
    "PLUGIN_ABI": "26.7", "PLUGIN_PYTHON": "313",
    "PLUGIN_HASH": "f" * 40,
    "PLUGIN_WWW": "https://github.com/Tolian82/os-zapret2-restyle",
    "PLUGIN_DEPENDS": "python313", "PLUGIN_DEVEL": "",
}


def make_manifest(temp):
    p = Path(temp)
    for file in mod.PHASES:
        (p / file).write_text("#!/bin/sh\nexit 0\n")
    return {
        "name": mod.NAME, "version": "0.6.2_58",
        "origin": "opnsense/" + mod.NAME,
        "www": "https://github.com/Tolian82/os-zapret2-restyle",
        "deps": {"python313": {"origin": "lang/python313", "version": "3.13.14"}},
        "scripts": {phase: (p / file).read_text().replace("%", "%25").removesuffix("\n")
                    for file, phase in mod.PHASES.items()},
        "files": {"/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh": "a",
                  **{"/usr/local/a" + str(n): "b" for n in range(110)}}}


class OfficialMkTests(unittest.TestCase):
    def test_untrusted_environment_refused_before_guest_probe(self):
        with patch.dict(os.environ, {mod.KEY: "0", "GITHUB_ACTIONS": "true"}):
            with patch.object(mod.importlib.util, "spec_from_file_location") as probe:
                with self.assertRaisesRegex(mod.Refusal, "OPTIN"):
                    mod.guest_gate()
                probe.assert_not_called()

    def test_authoritative_upstream_is_sha_pinned(self):
        self.assertEqual(len(mod.UPSTREAM_SHA), 40)
        self.assertEqual(mod.UPSTREAM, "https://github.com/opnsense/plugins.git")
        self.assertEqual(mod.REVISION, "58")

    def test_project_sha_uses_exact_checkout_scoped_git_trust(self):
        sha = "f" * 40
        with patch.dict(os.environ, {"ZAPRET2_STAGE0_PROJECT_SHA": sha}):
            with patch.object(mod, "cmd", return_value=sha) as called:
                self.assertEqual(mod.source_identity(), sha)
                args = called.call_args.args[0]
                self.assertEqual(args, ["git", "-c",
                                        "safe.directory=" + str(mod.ROOT),
                                        "-C", str(mod.ROOT), "rev-parse", "HEAD"])
                self.assertNotIn("*", args)

    def test_native_make_variables_accept_full_exact_provenance(self):
        with patch.object(mod, "mkvar", side_effect=lambda _p, _s, key: VARS[key]):
            self.assertEqual(mod.native_variables(Path("/tmp"), "f" * 40, PROVIDER),
                             VARS)

    def test_native_make_variables_refuse_wrong_origin_and_devel(self):
        for key, value in (("PLUGIN_PKGNAME", "os-zapret2-restyle-devel"),
                           ("PLUGIN_ABI", "26.1"),
                           ("PLUGIN_PYTHON", "312"),
                           ("PLUGIN_HASH", "0" * 40),
                           ("PLUGIN_DEVEL", "yes")):
            bad = dict(VARS)
            bad[key] = value
            with patch.object(mod, "mkvar", side_effect=lambda _p, _s, k: bad[k]):
                with self.subTest(key=key), self.assertRaisesRegex(
                        mod.Refusal, "VARIABLE_EVALUATION"):
                    mod.native_variables(Path("/tmp"), "f" * 40, PROVIDER)

    def test_native_source_dep_is_explicitly_unmigrated(self):
        bad = dict(VARS)
        bad["PLUGIN_DEPENDS"] = "py313"
        with patch.object(mod, "mkvar", side_effect=lambda _p, _s, k: bad[k]):
            with self.assertRaisesRegex(mod.Refusal, "DEPENDENCY_NOT_AS_AUDITED"):
                mod.native_variables(Path("/tmp"), "f" * 40, PROVIDER)

    def test_four_manual_hooks_unchanged_and_source_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            meta = make_manifest(td)
            self.assertEqual(mod.manifest_identity(meta, Path(td), PROVIDER), 111)

    def test_native_manifest_percent25_is_only_allowed_hook_encoding(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = make_manifest(td)
            path = Path(td) / "+PRE_INSTALL"
            path.write_text("#!/bin/sh\nprintf '%s\\n' 'pass'\n")
            source = path.read_text()
            manifest["scripts"]["pre-install"] = source.replace("%", "%25").removesuffix("\n")
            self.assertEqual(mod.manifest_identity(manifest, Path(td), PROVIDER), 111)
            manifest["scripts"]["pre-install"] = source.replace("%", "%26").removesuffix("\n")
            with self.assertRaisesRegex(mod.Refusal, "HOOK_BYTES_CHANGED"):
                mod.manifest_identity(manifest, Path(td), PROVIDER)
            manifest["scripts"]["pre-install"] = source
            with self.assertRaisesRegex(mod.Refusal, "HOOK_BYTES_CHANGED"):
                mod.manifest_identity(manifest, Path(td), PROVIDER)

    def test_native_manifest_extra_newline_or_truncation_refused(self):
        with tempfile.TemporaryDirectory() as td:
            meta = make_manifest(td)
            meta["scripts"]["pre-install"] += "\n"
            with self.assertRaisesRegex(mod.Refusal, "HOOK_BYTES_CHANGED"):
                mod.manifest_identity(meta, Path(td), PROVIDER)
            meta = make_manifest(td)
            meta["scripts"]["pre-install"] = meta["scripts"]["pre-install"][:-1]
            with self.assertRaisesRegex(mod.Refusal, "HOOK_BYTES_CHANGED"):
                mod.manifest_identity(meta, Path(td), PROVIDER)

    def test_manual_hook_rewrite_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            meta = make_manifest(td)
            meta["scripts"]["post-install"] += "echo unsafe\n"
            with self.assertRaisesRegex(mod.Refusal, "HOOK_BYTES_CHANGED"):
                mod.manifest_identity(meta, Path(td), PROVIDER)

    def test_hook_difference_reports_hashes_not_hook_contents(self):
        with tempfile.TemporaryDirectory() as td:
            meta = make_manifest(td)
            meta["scripts"]["pre-install"] += "exit 23\n"
            with self.assertRaises(mod.Refusal) as refusal:
                mod.manifest_identity(meta, Path(td), PROVIDER)
            message = str(refusal.exception)
            self.assertIn("NATIVE_SCRIPTS_MANUAL_HOOK_BYTES_CHANGED:pre-install", message)
            self.assertIn(":source_sha256=", message)
            self.assertIn(":archive_sha256=", message)
            self.assertIn(":first_diff=", message)
            self.assertNotIn("exit 23", message)

    def test_missing_or_extra_hook_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            meta = make_manifest(td)
            meta["scripts"]["pre-deinstall"] = meta["scripts"].pop("post-deinstall")
            with self.assertRaisesRegex(mod.Refusal, "PHASE_SET_CHANGED"):
                mod.manifest_identity(meta, Path(td), PROVIDER)

    def test_wrong_pkg_metadata_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            for key, value in (("name", "os-other"), ("version", "0.6.2_56"),
                               ("origin", "unknown/os-zapret2-restyle"),
                               ("www", "https://opnsense.org/")):
                meta = make_manifest(td)
                meta[key] = value
                with self.subTest(key=key), self.assertRaisesRegex(
                        mod.Refusal, "ORIGIN_OR_VERSION"):
                    mod.manifest_identity(meta, Path(td), PROVIDER)

    def test_wrong_real_python_provider_version_or_origin_refused(self):
        with tempfile.TemporaryDirectory() as td:
            for key, value in (("version", "0"), ("version", "3.12.12"),
                               ("origin", "lang/python312")):
                meta = make_manifest(td)
                meta["deps"]["python313"][key] = value
                with self.subTest(key=key), self.assertRaisesRegex(
                        mod.Refusal, "PROVIDER_DEPENDENCY"):
                    mod.manifest_identity(meta, Path(td), PROVIDER)

    def test_extra_dependency_refused(self):
        with tempfile.TemporaryDirectory() as td:
            meta = make_manifest(td)
            meta["deps"]["git"] = {"origin": "devel/git", "version": "2.0"}
            with self.assertRaisesRegex(mod.Refusal, "PROVIDER_DEPENDENCY"):
                mod.manifest_identity(meta, Path(td), PROVIDER)

    def test_missing_source_service_or_small_inventory_refused(self):
        with tempfile.TemporaryDirectory() as td:
            meta = make_manifest(td)
            meta["files"].pop("/usr/local/" + mod.SERVICE)
            with self.assertRaisesRegex(mod.Refusal, "SERVICE_PATH_MISSING"):
                mod.manifest_identity(meta, Path(td), PROVIDER)
            meta["files"] = {"other": "x"}
            with self.assertRaisesRegex(mod.Refusal, "INVENTORY_TOO_SMALL"):
                mod.manifest_identity(meta, Path(td), PROVIDER)

    def test_tar_member_requires_usr_local_full_path_and_unique_match(self):
        expected = "usr/local/" + mod.SERVICE
        self.assertEqual(mod.exact_installed_tar_member(
            ["+MANIFEST", "./" + expected], mod.SERVICE), "./" + expected)
        for other in ([mod.SERVICE], ["bin/" + mod.SERVICE],
                      [expected, "./" + expected],
                      ["other/" + mod.SERVICE]):
            with self.subTest(members=other), self.assertRaisesRegex(
                    mod.Refusal, "MEMBER_UNQUALIFIED"):
                mod.exact_installed_tar_member(other, mod.SERVICE)
        with self.assertRaisesRegex(mod.Refusal, "INPUT_UNQUALIFIED"):
            mod.exact_installed_tar_member([expected], "../" + mod.SERVICE)

    def test_missing_archived_payload_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(mod.Refusal, "NOT_FOUND"):
                mod.evaluate_archive(Path(td) / "missing.pkg", Path(td),
                                     b"old", PROVIDER)

    def test_source_executable_git_and_archive_mode_are_binding(self):
        source = (HERE / "stage0-opnsense-official-mk-source-package.py").read_text()
        self.assertIn('re.fullmatch(r"100755 blob [a-f0-9]{40}"', source)
        self.assertIn('"SOURCE_SERVICE_BYTES_DIFFER_FROM_EXACT_GIT_TREE"', source)
        self.assertIn('stat.S_IMODE(info.st_mode) == 0o755', source)
        self.assertIn('matching[0].split()[0] == "-rwxr-xr-x"', source)
        self.assertIn('"NATIVE_SOURCE_SERVICE_MODE_NOT_0755"', source)
        self.assertNotIn('"historical_git_mode_100644_preserved": True', source)
        self.assertNotIn('chmod(', source)

    def test_technical_result_cannot_claim_safe_product_or_install(self):
        content = (HERE / "stage0-opnsense-official-mk-source-package.py").read_text()
        for clause in ('"native_service_mode_is_safe": True',
                       '"source_git_mode_100755_proved": True',
                       '"private_curl_assets_bundled": False',
                       '"native_pkg_install_executed": False',
                       '"production_builder_replaced": False',
                       '"official_final_product_package_qualified": False',
                       '"stage0_closed": False'):
            self.assertIn(clause, content)

    def test_upstream_fetch_is_explicit_exact_sha_and_detached(self):
        source = (HERE / "stage0-opnsense-official-mk-source-package.py").read_text()
        self.assertIn('"fetch", "--no-tags", "--depth", "1"', source)
        self.assertIn('"checkout", "--quiet", "--detach", "FETCH_HEAD"', source)
        self.assertIn('UPSTREAM_SHA, "OFFICIAL_OPNSENSE_PLUGIN_FRAMEWORK_SHA_MISMATCH"', source)


if __name__ == "__main__":
    unittest.main()
