#!/usr/bin/env python3
"""Offline positive/negative contracts for the native Mk builder."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "native_production", HERE / "native-opnsense-package.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NativeBuilderTests(unittest.TestCase):
    def test_revision_and_exact_target(self):
        self.assertEqual(mod.REVISION, "71")
        self.assertEqual(mod.private.old.REVISION, "71")
        self.assertEqual(mod.provider.mk.REVISION, "71")
        self.assertEqual(mod.validated_policy()["supported_platforms"][0]["freebsd_pkg_abi"], "FreeBSD:15:amd64")

    def test_missing_optin_refused(self):
        with patch.dict(os.environ, {"ZAPRET2_NATIVE_BUILD_CI": "",
                                      "GITHUB_ACTIONS": "true",
                                      "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK": "1"}):
            with self.assertRaisesRegex(mod.Refusal, "NOT_OPTED_IN"):
                mod.gate()

    def test_unpinned_source_refused(self):
        with patch.dict(os.environ, {"ZAPRET2_NATIVE_PROJECT_SHA": "not-a-sha"}):
            with self.assertRaisesRegex(mod.Refusal, "EXACT_PROJECT_SHA"):
                mod.git_head()

    def test_mk_accepts_derived_python_and_real_dependencies(self):
        vars = {"PLUGIN_PKGNAME":mod.NAME, "PLUGIN_PKGVERSION":"0.6.2_71",
                "PLUGIN_ABI":"26.7", "PLUGIN_HASH":"f"*40,
                "PLUGIN_WWW":mod.PROJECT_URL, "PLUGIN_PYTHON":"313",
                "PLUGIN_DEPENDS":"python313 gmake pkgconf luajit git jq ca_root_nss",
                "PLUGIN_DEVEL":""}
        installed = {n:{} for n in vars["PLUGIN_DEPENDS"].split()}
        with patch.object(mod.private.old, "mkvar",
                          side_effect=lambda p,s,k:vars[k]):
            self.assertEqual(mod.native_make_variables(
                Path("/tmp"), "f"*40, {"native_plugin_python":"313"},installed,
                mod.validated_policy()["supported_platforms"][0]),
                vars)

    def test_mk_refuses_unsafe_dependency_mismatch(self):
        vars = {"PLUGIN_PKGNAME":mod.NAME, "PLUGIN_PKGVERSION":"0.6.2_71",
                "PLUGIN_ABI":"26.7", "PLUGIN_HASH":"f"*40,
                "PLUGIN_WWW":mod.PROJECT_URL, "PLUGIN_PYTHON":"313",
                "PLUGIN_DEPENDS":"python313 gmake", "PLUGIN_DEVEL":""}
        with patch.object(mod.private.old, "mkvar",
                          side_effect=lambda p,s,k:vars[k]):
            with self.assertRaisesRegex(mod.Refusal,"VARS_OR_REAL_DEPS_MISMATCH"):
                mod.native_make_variables(Path("/tmp"), "f"*40,
                                          {"native_plugin_python":"313"},
                                          {"python313":{}, "git":{}},
                                          mod.validated_policy()["supported_platforms"][0])

    def test_archive_verification_requires_exact_manual_hooks_and_modes(self):
        source = (HERE / "native-opnsense-package.py").read_text()
        for snippet in ('src.replace(b"%", b"%25")[:-1]',
                        '["-rwxr-xr-x"]',
                        '"NATIVE_ARCHIVE_PRIVATE_ELF_SHA_CHANGED"',
                        'len(name_to_source) == len(files) - 1'):
            self.assertIn(snippet, source)
        self.assertEqual(set(mod.HOOKS.values()),
                         {"pre-install","post-install","pre-deinstall","post-deinstall"})

    def test_single_official_native_build_and_dist(self):
        source = (HERE / "native-opnsense-package.py").read_text()
        for snippet in ('private.old.clone_official(Path(scratch))',
                        'private.prepare_private(plugin, Path(scratch))',
                        'command(["make", "-C", str(plugin)',
                        'verify_native_package(pkg, plugin, sha, installed, bundle,',
                        'shutil.copyfile(pkg, dest)'):
            self.assertIn(snippet, source)
        for forbidden in ("pkg-static create", "dep_origin()", "chmod("):
            self.assertNotIn(forbidden, source)

    def test_real_signed_catalog_providers_before_make(self):
        source = (HERE / "native-opnsense-package.py").read_text()
        for snippet in ("private.old.guest_gate()", '"pkg", "config", "ABI"',
                        '"pkg", "rquery", "-r", "OPNsense"',
                        'provider.parse_catalog(raw)',
                        'provider.resolve(catalog',
                        'provider.installed_python_crosscheck'):
            self.assertIn(snippet, source)

    def test_native_build_does_not_claim_install_or_release(self):
        source = (HERE / "native-opnsense-package.py").read_text()
        for snippet in ('"actual_product_pkg_installed": False',
                        '"publication_approved": False',
                        '"stage0_closed": False', '"stage1_admitted": False'):
            self.assertIn(snippet, source)
        self.assertIn("native-product-installed-acceptance.json",
                      (HERE.parent / ".github/workflows/release.yml").read_text())

    def test_old_manual_builder_removed_completely(self):
        wrapper = (HERE / "build-pkg.sh").read_text()
        self.assertIn("exec /usr/local/bin/python3", wrapper)
        self.assertIn("ZAPRET2_NATIVE_BUILD_CI", wrapper)
        for forbidden in ("pkg-static create", "dep_origin()", "jq -n",
                          "cp -R src/opnsense", "find "):
            self.assertNotIn(forbidden, wrapper)

    def test_native_python_is_derived_not_hardcoded(self):
        make = (HERE.parent / "Makefile").read_text()
        self.assertIn("python" + chr(36) + "{PLUGIN_PYTHON}", make)
        self.assertNotIn("PLUGIN_DEPENDS=     python313", make)
        self.assertEqual(len(mod.EXPECTED_ROLES), 7)


if __name__ == "__main__":
    unittest.main()
