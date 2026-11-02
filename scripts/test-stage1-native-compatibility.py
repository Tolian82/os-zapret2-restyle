#!/usr/bin/env python3
"""Offline focused Stage 1.05-1.09 native integration and refusal contracts."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "native_compatibility_candidate", HERE / "native-opnsense-package.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
guard_spec = importlib.util.spec_from_file_location(
    "stage1_static_compatibility", HERE / "stage1-native-policy-static.py")
guard = importlib.util.module_from_spec(guard_spec)
guard_spec.loader.exec_module(guard)
POLICY = native.validated_policy()
TARGET = POLICY["supported_platforms"][0]


class Stage1NativePolicyTests(unittest.TestCase):
    def test_qualified_platform_and_python_origin_use_real_probes(self):
        observed = {"python_runtime": "Python 3.13.16",
                    "native_plugin_python": "313",
                    "generic_python_link_owner": "opnsense-26.7",
                    "installed_python_provider": "python313|lang/python313|3.13.16"}
        with patch.object(native.provider, "command",
                          side_effect=lambda *args: {
                              ("opnsense-version", "-a"): "26.7",
                              ("pkg", "config", "ABI"): "FreeBSD:15:amd64",
                          }[args]), patch.object(native.os, "uname",
                          return_value=type("FakeOS", (), {"machine":"amd64"})()):
            self.assertEqual(native.qualified_target(observed), TARGET)
        # Actual provider is independently verified in official native CI;
        # the unit-level probe mock is not an installed-provider witness.

    def test_freebsd16_negative_even_with_python313(self):
        observed = {"python_runtime": "Python 3.13.16"}
        with patch.object(native.provider, "command",
                          side_effect=lambda *args: {
                              ("opnsense-version", "-a"): "26.7",
                              ("pkg", "config", "ABI"): "FreeBSD:16:amd64",
                          }[args]), patch.object(native.os, "uname",
                          return_value=type("FakeOS", (), {"machine":"amd64"})()):
            with self.assertRaisesRegex(native.compat.Refusal,
                                        "UNSUPPORTED_FREEBSD_ABI"):
                native.qualified_target(observed)

    def test_upstream_product_fallback_not_accepted(self):
        observed = {"python_runtime": "Python 3.13.16"}
        with patch.object(native.provider, "command",
                          side_effect=lambda *args: {
                              ("opnsense-version", "-a"): "27.1",
                              ("pkg", "config", "ABI"): "FreeBSD:15:amd64",
                          }[args]), patch.object(native.os, "uname",
                          return_value=type("FakeOS", (), {"machine":"amd64"})()):
            with self.assertRaisesRegex(native.compat.Refusal,
                                        "UNSUPPORTED_OPNSENSE_PRODUCT_ABI"):
                native.qualified_target(observed)

    def test_exact_staged_source_bytes_no_second_policy(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            with patch.object(native, "validated_policy", return_value=POLICY):
                digest = native.stage_policy(root)
            path = root / "src" / native.POLICY_DEST
            source = native.ROOT / "compatibility.json"
            self.assertEqual(path.read_bytes(), source.read_bytes())
            self.assertEqual(digest, hashlib.sha256(source.read_bytes()).hexdigest())
            path.write_bytes(b"{}")
            self.assertNotEqual(path.read_bytes(), source.read_bytes())
            with self.assertRaisesRegex(native.Refusal, "POLICY_STAGING_COLLISION"):
                native.stage_policy(root)

    def test_native_mk_product_identity_from_matrix(self):
        vars = {"PLUGIN_PKGNAME": native.NAME, "PLUGIN_PKGVERSION": "0.6.2_77",
                "PLUGIN_ABI": TARGET["opnsense_product_abi"],
                "PLUGIN_HASH": "f"*40, "PLUGIN_WWW": native.PROJECT_URL,
                "PLUGIN_PYTHON": "313",
                "PLUGIN_DEPENDS": "python313 gmake pkgconf luajit git jq ca_root_nss",
                "PLUGIN_DEVEL": ""}
        deps = {n: {} for n in vars["PLUGIN_DEPENDS"].split()}
        with patch.object(native.private.old, "mkvar",
                          side_effect=lambda p,s,k: vars[k]):
            self.assertEqual(native.native_make_variables(
                Path("/tmp"), "f"*40, {"native_plugin_python":"313"}, deps, TARGET),
                vars)
            vars["PLUGIN_ABI"] = "27.1"
            with self.assertRaisesRegex(native.Refusal, "VARS_OR_REAL_DEPS_MISMATCH"):
                native.native_make_variables(
                    Path("/tmp"), "f"*40, {"native_plugin_python":"313"}, deps, TARGET)

    def test_no_competing_native_prod_abi_or_python_table(self):
        build = (HERE / "native-opnsense-package.py").read_text()
        make = (HERE.parent / "Makefile").read_text()
        self.assertNotIn('ABI = "FreeBSD:15:amd64"', build)
        self.assertFalse(any(isinstance(node, ast.Name) and node.id == "ABI"
                             for node in ast.walk(ast.parse(build))),
                         "stale unbound ABI result reference in native builder")
        self.assertNotIn('result["PLUGIN_ABI"] == "26.7"', build)
        self.assertNotIn('manifest.get("arch") == "freebsd:15:x86:64"', build)
        self.assertNotIn("python313", make)
        self.assertIn("compat.check_target(policy, product, abi, cpu", build)
        self.assertIn('result["PLUGIN_ABI"] == platform["opnsense_product_abi"]', build)
        self.assertIn('platform["freebsd_pkg_abi"]', build)
        self.assertIn('"pkg", "config", "ABI"', build)
        self.assertIn('"opnsense-version", "-a"', build)

    def test_static_guard_rejects_new_competing_production_abi(self):
        sources = {p: (native.ROOT / p).read_text()
                   for p in guard.PRODUCTION}
        self.assertEqual(guard.scan(sources)["status"],
                         "PASS_SCOPED_NATIVE_POLICY_SINGLE_SOURCE")
        for code, snippet in [
            ("DUPLICATE_FREEBSD_ABI", 'ABI = "FreeBSD:16:amd64"'),
            ("VERSIONED_PYTHON_EXECUTABLE", '/usr/local/bin/python3.14'),
            ("INDEPENDENT_PRODUCT_ABI_ASSIGNMENT", 'PRODUCT_ABI = "27.1"'),
            ("INDEPENDENT_MK_PRODUCT_ABI_MATCH",
             'result["PLUGIN_ABI"] == "26.7"'),
        ]:
            changed = dict(sources)
            changed["scripts/native-opnsense-package.py"] += "\n" + snippet + "\n"
            with self.subTest(code=code), self.assertRaisesRegex(
                    guard.Refusal, code):
                guard.scan(changed)

    def test_python_independent_probe_no_missing_installed_manifest(self):
        sh = (HERE / "compatibility-bootstrap.sh").read_text()
        self.assertTrue(sh.startswith("#!/bin/sh"))
        self.assertIn("[ ! -x /usr/local/bin/python3 ]", sh)
        for forbidden in ("python3 --version", "python3 -c", "compatibility.json",
                          "pkg add", "pkg delete", "sed ", "awk ", "eval "):
            self.assertNotIn(forbidden, sh)
        self.assertIn("NOT_PLATFORM_ADMISSION", sh)
        # Deliberate no platform/FreeBSD16 claim from the bootstrap check.

    def test_source_to_archive_to_installed_integrity_is_enforced(self):
        builder = (HERE / "native-opnsense-package.py").read_text()
        installer = (HERE / "stage2-opnsense-real-native-clean-install.py").read_text()
        self.assertIn('"POLICY_ARCHIVED_BYTES_MISMATCH"', builder)
        self.assertIn('"POLICY_MISSING_FROM_MANIFEST"', builder)
        self.assertIn('"POLICY_INSTALLED_BYTES_MISMATCH"', installer)
        self.assertIn('native.POLICY_DEST', installer)


if __name__ == "__main__":
    unittest.main()
