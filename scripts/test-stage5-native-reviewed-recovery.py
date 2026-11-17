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

    def test_registered_prior_version_requires_real_native_dual_probes(self):
        prior = mock.Mock(returncode=0, stdout="0.6.5_88\n", stderr="")
        info = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(fixture, "cmd", side_effect=[prior, info]) as calls:
            self.assertEqual(fixture.reviewed_pkgdb("0.6.5_88"),
                             "registered-prior")
            self.assertEqual(calls.call_count, 2)
        missing = mock.Mock(returncode=1, stdout="", stderr="No packages matching")
        with mock.patch.object(fixture, "cmd", return_value=missing):
            self.assertEqual(fixture.reviewed_pkgdb("0.6.5_88"), "absent")
        bad = mock.Mock(returncode=1, stdout="", stderr="database is malformed")
        with mock.patch.object(fixture, "cmd", return_value=bad):
            with self.assertRaisesRegex(RuntimeError, "PKGDB_NOT_ELIGIBLE_ABSENT_OR_TRUSTED_PRIOR"):
                fixture.reviewed_pkgdb("0.6.5_88")
        wrong = mock.Mock(returncode=0, stdout="0.6.5_89", stderr="")
        with mock.patch.object(fixture, "cmd", return_value=wrong):
            with self.assertRaisesRegex(RuntimeError, "PKGDB_NOT_ELIGIBLE_ABSENT_OR_TRUSTED_PRIOR"):
                fixture.reviewed_pkgdb("0.6.5_88")

    def test_reinstall_checks_guarded_prior_and_physical_torn_payload_first(self):
        source = SOURCE.read_text()
        scope = source.split("def reinstall():", 1)[1].split("def finish():", 1)[0]
        self.assertLess(scope.index('original_journal('),
                        scope.index('reviewed_pkgdb(prior_version)'))
        self.assertLess(scope.index('fixture.witness_inventory()'),
                        scope.index('reviewed_pkgdb(prior_version)'))
        self.assertLess(scope.index('reviewed_pkgdb(prior_version)'),
                        scope.index('"add", "-f", str(stage)'))
        self.assertIn('protected.VERSION_PATTERN.fullmatch(prior_version)', scope)
        self.assertIn('receipt["witnesses_before"]["restored"] > 0', scope)
        self.assertIn('"REVIEWED_RECOVERY_REQUIRES_REAL_TORN_PAYLOAD"', scope)
        self.assertNotIn('pkg delete', scope)
        self.assertNotIn('sqlite3', scope)

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
