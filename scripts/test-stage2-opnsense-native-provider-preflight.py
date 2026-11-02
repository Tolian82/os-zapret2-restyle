#!/usr/bin/env python3
"""Positive/negative offline contracts for genuine OPNsense provider preflight."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "stage2_native_providers", HERE / "stage2-opnsense-native-provider-preflight.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    rows = {f"dummy{i}": {"name": f"dummy{i}",
                         "origin": f"bench/dummy{i}", "version": "1.2.3"}
            for i in range(700)}
    rows.update({n: {"name": n, "origin": "target/" + n, "version": "9.3_1"}
                 for n in ("python313", "gmake", "pkgconf", "luajit",
                           "git-lite", "git", "jq", "ca_root_nss")})
    return rows


class ProviderContracts(unittest.TestCase):
    def test_expected_revision_and_pin(self):
        self.assertEqual(mod.REVISION, "60")
        self.assertEqual(mod.mk.REVISION, "60")
        self.assertEqual(mod.UPSTREAM_SHA,
                         "79a5f88b7b27a706c10511ea5587c9d0e0dbdced")

    def test_true_catalog_parser(self):
        data = fixture()
        raw = "\n".join("|".join((x["name"], x["origin"], x["version"]))
                        for x in data.values())
        self.assertEqual(mod.parse_catalog(raw), data)

    def test_tiny_catalog_fails_closed(self):
        with self.assertRaisesRegex(mod.Refusal, "CATALOG_NOT_QUALIFIED"):
            mod.parse_catalog("python313|lang/python313|3.13.16")

    def test_duplicate_package_name_refused(self):
        raw = "x|foo/bar|1\n" * 701
        with self.assertRaisesRegex(mod.Refusal, "DUPLICATE_PROVIDER"):
            mod.parse_catalog(raw)

    def test_malformed_catalog_refused(self):
        for raw in ("x|a|1|stray", "x|../bad|2", "x|a|1\x00p",
                    "bad package|foo/bar|2"):
            with self.subTest(raw=raw), self.assertRaisesRegex(
                    mod.Refusal, "ROW_MALFORMED"):
                mod.parse_catalog(raw)

    def test_all_targets_present_are_accepted(self):
        providers = mod.resolve(fixture(), "python313")
        self.assertEqual(set(providers), {*mod.REQUIRED, "python-runtime"})
        self.assertEqual(providers["setup-git"]["selected"]["name"], "git-lite")
        self.assertEqual(providers["setup-git"]["alternatives"][0]["name"], "git")

    def test_fallback_to_git_if_lite_not_found(self):
        catalog = fixture()
        catalog.pop("git-lite")
        self.assertEqual(mod.resolve(catalog, "python313")["setup-git"]
                         ["selected"]["name"], "git")

    def test_missing_provider_refused(self):
        for name in ("luajit", "gmake", "jq", "python313", "ca_root_nss"):
            catalog = fixture()
            catalog.pop(name)
            with self.subTest(name=name), self.assertRaisesRegex(
                    mod.Refusal, "TARGET_PROVIDER_MISSING"):
                mod.resolve(catalog, "python313")

    def test_no_foreign_python_origin_equivalence(self):
        providers = mod.resolve(fixture(), "python313")
        valid = {"installed_python_provider": "python313|target/python313|3.13.14"}
        self.assertEqual(mod.installed_python_crosscheck(providers, valid)
                         ["installed"], valid["installed_python_provider"])
        invalid = {"installed_python_provider": "python313|lang/python313|3.13.14"}
        with self.assertRaisesRegex(mod.Refusal, "NOT_MATCHED_TO_TARGET"):
            mod.installed_python_crosscheck(providers, invalid)

    def test_invalid_python_name_refused(self):
        with self.assertRaisesRegex(mod.Refusal, "PYTHON_PROVIDER_NAME"):
            mod.resolve(fixture(), "python313;echo pwned")

    def test_actual_source_legacy_pipeline_assertions(self):
        actual = mod.inventory_legacy_contracts()
        self.assertEqual(len(actual), 8)
        self.assertTrue(all(actual.values()))

    def test_genuine_guest_is_required(self):
        source = (HERE / "stage2-opnsense-native-provider-preflight.py").read_text()
        for marker in ("mk.guest_gate()", 'mk.source_identity()',
                       'mk.qualify_python_provider()',
                       '"pkg", "rquery", "-r", REPOSITORY',
                       "mk.clone_official(Path(td))",
                       "mk.native_variables(plugin, source_sha, installed_python)"):
            self.assertIn(marker, source)

    def test_cannot_claim_published_or_installed(self):
        source = (HERE / "stage2-opnsense-native-provider-preflight.py").read_text()
        for marker in ('"production_builder_replaced": False',
                       '"new_package_installed": False',
                       '"product_package_published": False',
                       '"foreign_FreeBSD_system_pkg_installed": False',
                       '"stage0_closed": False', '"stage1_admitted": False'):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
