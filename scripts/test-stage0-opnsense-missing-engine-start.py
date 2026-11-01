#!/usr/bin/env python3
"""Fast source contracts for missing actual engine Start negative."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'stage0-opnsense-missing-engine-start.py'
spec = importlib.util.spec_from_file_location('absent_engine', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
COLD = {'status': 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
        'safe_pkg_transaction_authorized': False}
GOOD = subprocess.CompletedProcess([], 1, '', m.ERROR + '\nERROR: reinstall the plugin')


class Contracts(unittest.TestCase):
    def test_exact_old_start_refusal(self):
        self.assertEqual(m.classify_start(GOOD, COLD, COLD),
                         'REAL_OLD_START_REFUSED_MISSING_RUNTIME_BEFORE_FIREWALL')

    def test_successful_start_refuses_test(self):
        with self.assertRaisesRegex(m.Refusal, 'NOT_REFUSED'):
            m.classify_start(subprocess.CompletedProcess([], 0, '', GOOD.stderr), COLD, COLD)

    def test_unexpected_exit_refuses(self):
        with self.assertRaises(m.Refusal):
            m.classify_start(subprocess.CompletedProcess([], 69, '', GOOD.stderr), COLD, COLD)

    def test_missing_error_refuses(self):
        with self.assertRaisesRegex(m.Refusal, 'DIAGNOSTIC_CHANGED'):
            m.classify_start(subprocess.CompletedProcess([], 1, '', 'another error'), COLD, COLD)

    def test_fake_error_prefix_refuses(self):
        with self.assertRaises(m.Refusal):
            m.classify_start(subprocess.CompletedProcess([], 1, '', 'reinstall the plugin'), COLD, COLD)

    def test_stdout_refuses(self):
        with self.assertRaises(m.Refusal):
            m.classify_start(subprocess.CompletedProcess([], 1, 'unexpected', GOOD.stderr), COLD, COLD)

    def test_unknown_before_refuses(self):
        with self.assertRaisesRegex(m.Refusal, 'COLD_OWNER_NOT_PRESERVED'):
            m.classify_start(GOOD, {'status':'UNKNOWN'}, COLD)

    def test_unknown_after_refuses(self):
        with self.assertRaisesRegex(m.Refusal, 'COLD_OWNER_NOT_PRESERVED'):
            m.classify_start(GOOD, COLD, {'status':'UNKNOWN'})

    def test_unsafe_authorization_refuses(self):
        with self.assertRaisesRegex(m.Refusal, 'UNSAFE_PREPKG'):
            m.classify_start(GOOD, COLD, {**COLD,'safe_pkg_transaction_authorized':True})

    def test_present_runtime_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            engine=Path(t)/'dvtws2';engine.write_bytes(b'ELF')
            with self.assertRaisesRegex(m.Refusal, 'RUNTIME_NOT_ABSENT'):
                m.require_missing_engine(engine)

    def test_symlink_runtime_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            engine=Path(t)/'dvtws2';engine.symlink_to('missing-elsewhere')
            with self.assertRaisesRegex(m.Refusal, 'RUNTIME_NOT_ABSENT'):
                m.require_missing_engine(engine)

    def test_absent_runtime_allowed(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(m.require_missing_engine(Path(t)/'dvtws2'))

    def test_nonroot_refuses_before_install(self):
        with mock.patch.object(m.os,'geteuid',return_value=1001), \
             mock.patch.object(m,'load') as loader:
            with self.assertRaisesRegex(m.Refusal, 'ONLY_DISPOSABLE'):
                m.prove(Path('/not-real'))
            loader.assert_not_called()

    def test_fd9_lock_missing_before_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(m.original_lock_identity(Path(d)/'missing'))
            with self.assertRaisesRegex(m.Refusal, 'DISAPPEARED'):
                m.original_lock_identity(Path(d)/'missing', required=True)

    def test_fd9_lock_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'lock';path.symlink_to('/tmp/no-lock-file')
            with self.assertRaisesRegex(m.Refusal, 'FOREIGN_OR_SYMLINK'):
                m.original_lock_identity(path)

    def test_no_running_or_pkg_safety_claim(self):
        text=SOURCE.read_text()
        for token in ("'real_running_engine_tested': False",
                      "'actual_product_package_replaced': False",
                      "'coordinated_pkg_transaction_proved': False",
                      "'stage0_closed': False"):
            self.assertIn(token,text)


if __name__ == '__main__':
    unittest.main()
