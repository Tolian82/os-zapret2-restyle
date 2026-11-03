#!/usr/bin/env python3
"""Fast checks of the real source-bound same-version pkg driver and refusal."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).with_name("stage2-opnsense-real-native-force-reinstall.py")
spec = importlib.util.spec_from_file_location("native_force_reinstall", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RealForceReinstallTest(unittest.TestCase):
    def test_revision(self):
        self.assertEqual(m.REVISION, "80")

    def test_refuse_without_disposable_gates_before_guest(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            m.clean, "preflight", side_effect=AssertionError("unsafe")) as gate:
            with self.assertRaisesRegex(m.Refusal, "OPTIN_REQUIRED"):
                m.preflight()
            gate.assert_not_called()

    def test_native_source_revision_mismatch_refuses(self):
        flags = {k: "1" for k in
                 (m.OPTIN, "ZAPRET2_STAGE2_REAL_CLEAN_INSTALL",
                  "ZAPRET2_NATIVE_BUILD_CI", "GITHUB_ACTIONS")}
        flags["GITHUB_ACTIONS"] = "true"
        with patch.dict(os.environ, flags), patch.object(
            m.clean, "preflight", return_value=b"xml"), patch.object(
            m.native, "REVISION", "unqualified"):
            with self.assertRaisesRegex(m.Refusal, "REVISIONS_MISMATCH"):
                m.preflight()

    def test_invokes_real_force_with_scripts_and_exact_archive(self):
        with patch.object(m.clean, "run", return_value=SimpleNamespace(
                returncode=0, stdout="Reinstalling os-zapret2-restyle...\nos-zapret2-restyle was installed.\n",
                stderr="")) as run:
            result = m.force_same_version(Path("/tmp/actual-same-version.pkg"))
            self.assertTrue(result["genuine_pkg_add_force"])
            run.assert_called_once_with(
                ["pkg", "-o", "REPO_AUTOUPDATE=false", "add", "-f",
                 "/tmp/actual-same-version.pkg"], timeout=240)

    def test_nonzero_pkg_must_refuse(self):
        with patch.object(m.clean, "run", return_value=SimpleNamespace(
                returncode=3, stdout="", stderr="hook failed")):
            with self.assertRaisesRegex(m.Refusal, "NONZERO"):
                m.force_same_version(Path("/tmp/archive.pkg"))

    def test_no_hook_success_message_must_refuse(self):
        with patch.object(m.clean, "run", return_value=SimpleNamespace(
                returncode=0, stdout="Reinstalling os-zapret2-restyle...", stderr="")):
            with self.assertRaisesRegex(m.Refusal, "POSTINSTALL"):
                m.force_same_version(Path("/tmp/archive.pkg"))

    def test_no_pkg_operation_signature_must_refuse(self):
        with patch.object(m.clean, "run", return_value=SimpleNamespace(
                returncode=0, stdout="os-zapret2-restyle was installed.", stderr="")):
            with self.assertRaisesRegex(m.Refusal, "OPERATION_NOT_OBSERVED"):
                m.force_same_version(Path("/tmp/archive.pkg"))

    def test_foreign_process_or_rule_failure_propagates(self):
        with patch.object(m.clean, "cold_status", return_value={
                "direct_service_status_exit": 1, "installed_runtime_started": False}), patch.object(
                m.stopped, "verify_cold_runtime", return_value={
                    "no_plugin_processes_or_markers": False,
                    "no_ipfw_or_ipdivert_kernel_ownership": True}):
            with self.assertRaisesRegex(m.Refusal, "NOT_COLD"):
                m.assert_cold()

    def test_real_source_calls_strict_payload_and_config_guards(self):
        text = SOURCE.read_text(encoding="utf-8")
        for fragment in ("clean.verify_installed_files(path, manifest)",
                         "clean.verify_installed_files(path, same_manifest)",
                         "clean.verify_official_first_install_registration(",
                         "stopped.prove_preserved_config(",
                         "assert_cold()", "force_same_version(path)"):
            self.assertIn(fragment, text)
        self.assertNotIn("--script-no-exec", text)
        self.assertNotIn("pkg add -I", text)


if __name__ == "__main__":
    unittest.main()
