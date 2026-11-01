#!/usr/bin/env python3
"""Offline safety tests: real target path is executed only in disposable VM."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "negative", Path(__file__).with_name("stage0-opnsense-old-unknown-owner.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class UnknownOwner(unittest.TestCase):
    def test_old_service_unknown_only_exit_two(self):
        m.prove_unknown_status(SimpleNamespace(returncode=2, stdout=m.UNKNOWN_STATUS))
        for rc, output in ((0, "zapret is running"), (1, "zapret is not running"),
                           (2, "unrecognized"), (75, "busy")):
            with self.subTest(rc=rc), self.assertRaises(m.pre.Refusal):
                m.prove_unknown_status(SimpleNamespace(returncode=rc, stdout=output))

    def test_native_delete_is_exact_named_package_with_original_scripts(self):
        self.assertEqual(m.DELETE[-2:], ("-y", m.pre.NAME))
        for unsupported in ("-f", "-I", "--force", "--script-no-exec",
                            "--no-scripts", "--accept-missing"):
            self.assertNotIn(unsupported, m.DELETE)

    def test_native_pkg_ignores_refusal_and_removes_original_package(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old-service"
            with patch.object(m.pre, "SERVICE", str(path)), patch.object(
                    m.old, "run_command", side_effect=[
                        SimpleNamespace(returncode=0, stdout="removed",
                                        stderr=m.UNKNOWN_HOOK_DIAGNOSTIC),
                        SimpleNamespace(returncode=1, stdout="", stderr="")
                    ]):
                outcome, details = m.measure_native_pkg_delete_outcome()
                self.assertEqual(outcome, "REMOVED_DESPITE_PRE_DEINSTALL_REFUSAL")
                self.assertEqual(details["native_pkg_delete_exit_code"], 0)
                self.assertFalse(details["old_pkgdb_present"])

    def test_native_refusal_with_bytes_kept_and_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old-service"
            path.write_text("immutable original fixture")
            with patch.object(m.pre, "SERVICE", str(path)), patch.object(
                    m.old, "run_command", side_effect=[
                        SimpleNamespace(returncode=1, stdout="",
                                        stderr=m.UNKNOWN_HOOK_DIAGNOSTIC),
                        SimpleNamespace(returncode=0, stdout="", stderr="")
                    ]):
                outcome, details = m.measure_native_pkg_delete_outcome()
                self.assertEqual(outcome, "REFUSED_WITH_PACKAGE_PRESERVED")
                self.assertTrue(details["original_service_path_present"])

    def test_native_hazard_must_not_hide_absent_original_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old-service"
            with patch.object(m.pre, "SERVICE", str(path)), patch.object(
                    m.old, "run_command", side_effect=[
                        SimpleNamespace(returncode=0, stdout="removed", stderr=""),
                        SimpleNamespace(returncode=1, stdout="", stderr="")
                    ]):
                with self.assertRaisesRegex(m.pre.Refusal, "HOOK_REFUSAL_NOT_OBSERVED"):
                    m.measure_native_pkg_delete_outcome()

    def test_original_pre_hook_status_two_refuses_without_stop(self):
        good = "+ /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh status\n" + \
               "+ service_status=2\n+ echo ERROR: incomplete zapret lifecycle\n" + \
               m.UNKNOWN_HOOK_DIAGNOSTIC + "\n"
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            with patch.object(m.old, "run_command", return_value=SimpleNamespace(
                    returncode=1, stdout="", stderr=good)):
                self.assertTrue(m.trace_original_unknown_predeinstall("real hook", directory))
            with patch.object(m.old, "run_command", return_value=SimpleNamespace(
                    returncode=1, stdout="", stderr=good + \
                    "+ /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh stop\n")):
                with self.assertRaisesRegex(m.pre.Refusal, "CALLED_STOP"):
                    m.trace_original_unknown_predeinstall("real hook", directory)

    def test_unqualified_preexisting_journal_refuses_before_mutation(self):
        with patch.object(m, "ensure_no_journal", side_effect=m.pre.Refusal(
                "UNQUALIFIED_PREEXISTING_JOURNAL")), \
             patch.object(m.JOURNAL.__class__, "mkdir",
                          side_effect=AssertionError("must never create journal")):
            with self.assertRaisesRegex(m.pre.Refusal, "UNQUALIFIED_PREEXISTING"):
                m.create_owned_corrupt_journal()

    def test_absent_disposable_parent_created_only_under_trusted_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder) / "zapret2"
            journal = parent / "shared-apply"
            with patch.object(m, "JOURNAL", journal):
                self.assertTrue(m.create_disposable_root_if_absent())
                self.assertFalse(m.create_disposable_root_if_absent())
                self.assertTrue(parent.is_dir())
                parent.rmdir()
                parent.symlink_to(Path(folder), target_is_directory=True)
                with self.assertRaisesRegex(m.pre.Refusal, "PARENT_SYMLINK"):
                    m.create_disposable_root_if_absent()

    def test_unproven_package_refuses_before_injection_or_deletion(self):
        with patch.object(m.pre, "run", return_value=b"guest"), \
             patch.object(m.pre, "run_guest",
                          side_effect=m.pre.Refusal("PUBLISHED_PACKAGE_SHA256_MISMATCH")), \
             patch.object(m, "create_owned_corrupt_journal",
                          side_effect=AssertionError("must not inject")), \
             patch.object(m, "measure_native_pkg_delete_outcome",
                          side_effect=AssertionError("must not delete")):
            with self.assertRaisesRegex(m.pre.Refusal, "SHA256_MISMATCH"):
                m.run_negative(Path("/tmp/irrelevant.pkg"))


if __name__ == "__main__":
    unittest.main()
