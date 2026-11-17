#!/usr/bin/env python3
"""Portable fast preflight for disposable, explicitly reviewed native recovery."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name("stage5-native-reviewed-recovery.py")
spec = importlib.util.spec_from_file_location("reviewed_test_only", SOURCE)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class ReviewedRecoveryContracts(unittest.TestCase):
    def test_no_implicit_operator_approval(self):
        with mock.patch.dict(fixture.os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "NOT_EXPLICITLY_REVIEWED"):
                fixture.isolation("reinstall")
            with self.assertRaisesRegex(RuntimeError, "NOT_EXPLICITLY_REVIEWED"):
                fixture.isolation("finish")

    def test_unknown_command_refuses_early(self):
        with mock.patch.object(fixture.sys, "argv", ["recovery", "auto-repair"]):
            with self.assertRaisesRegex(RuntimeError, "UNSUPPORTED_REVIEWED"):
                fixture.main()

    def test_dual_pkgdb_must_be_unambiguously_absent(self):
        good = mock.Mock(returncode=1, stdout="", stderr="No packages matching")
        with mock.patch.object(fixture, "cmd", return_value=good) as run:
            self.assertTrue(fixture.absent_pkgdb())
            self.assertEqual(run.call_count, 2)
        bad = mock.Mock(returncode=1, stdout="", stderr="database is malformed")
        with mock.patch.object(fixture, "cmd", return_value=bad):
            with self.assertRaisesRegex(RuntimeError, "PKGDB_NOT_UNAMBIGUOUSLY_ABSENT"):
                fixture.absent_pkgdb()
        installed = mock.Mock(returncode=0, stdout="0.6.5_89", stderr="")
        with mock.patch.object(fixture, "cmd", return_value=installed):
            with self.assertRaisesRegex(RuntimeError, "PKGDB_NOT_UNAMBIGUOUSLY_ABSENT"):
                fixture.absent_pkgdb()

    def test_pkgdb_failure_categories_are_bounded_and_never_override_refusal(self):
        self.assertEqual(fixture.pkgdb_error_categories("No packages matching"), [])
        self.assertEqual(
            fixture.pkgdb_error_categories("pkg: SQL Error; IO ERROR: user-secret"),
            ["sql_error", "io_error"])
        self.assertNotIn("user-secret", str(
            fixture.pkgdb_error_categories("IO ERROR: user-secret")))
        query = mock.Mock(returncode=1, stdout="", stderr="No packages matching")
        info = mock.Mock(returncode=1, stdout="", stderr="database is LOCKED")
        with mock.patch.object(fixture, "cmd", side_effect=[query, info]):
            with self.assertRaisesRegex(RuntimeError, "PKGDB_NOT_UNAMBIGUOUSLY_ABSENT"):
                fixture.absent_pkgdb()
        # A true ambiguity is still a hard refusal, not permission to reinstall.
        self.assertIn("need(query.returncode == 1", SOURCE.read_text())

    def test_postkill_partial_payload_proof_never_calls_installed_service(self):
        contents = SOURCE.read_text()
        scope = contents.split("def interrupt_for_reset(", 1)[1].split("def reinstall():", 1)[0]
        tail = scope.split("witness.interrupt_real_native_pkg_midextract(", 1)[1]
        self.assertIn('"postkill_installed_code_executed": False', tail)
        self.assertIn('["/bin/ps", "-axo", "comm="]', tail)
        self.assertNotIn('native.SERVICE)', tail)
        self.assertNotIn('"start"', tail)
        self.assertNotIn('"pkg-update-finish"', tail)

    def test_only_one_reviewed_native_pkg_call_and_no_other_writer(self):
        s = SOURCE.read_text()
        self.assertIn('"add", "-f", str(stage)', s)
        self.assertIn('"zapret-pkg-postinstall-guarded=1" in combined', s)
        self.assertIn('"postinstall-attested"', s)
        self.assertIn('"pkg-update-finish"', s)
        self.assertIn('fixture.trusted_service()', s)
        self.assertIn('receipt["config_snapshot"]["plugin"]', s)
        self.assertNotIn('rm -f', s)
        self.assertNotIn('pkg delete', s)
        self.assertNotIn('os.unlink(', s)
        self.assertNotIn('os.replace(', s)
        self.assertNotIn('configctl', s)
        self.assertNotIn('service_with_lifecycle_lock', s)
        self.assertNotIn('start_service(', s)


if __name__ == "__main__":
    unittest.main()
