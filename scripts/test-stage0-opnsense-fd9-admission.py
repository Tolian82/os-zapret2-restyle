#!/usr/bin/env python3
"""Stage 0 FD9 refusal is before any private pkg callback."""
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

SRC = Path(__file__).with_name('stage0-opnsense-fd9-admission.py')
spec = importlib.util.spec_from_file_location('fd9_admission', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
GOOD = {'status': 'PASS_COLD_READ_ONLY_SNAPSHOT_ONLY',
        'old_package': 'os-zapret2-restyle-0.6.2_1',
        'real_old_status': 'STOPPED',
        'safe_pkg_transaction_authorized': False}


class AdmissionTests(unittest.TestCase):
    def test_busy_fd9_blocks_pkg(self):
        fn = mock.Mock()
        with self.assertRaisesRegex(m.Refusal, 'FD9_BUSY_OR_UNQUALIFIED'):
            m.admit(lambda: False, lambda: GOOD, fn)
        fn.assert_not_called()

    def test_busy_does_not_probe_owner(self):
        owner = mock.Mock()
        with self.assertRaises(m.Refusal):
            m.admit(lambda: False, owner, lambda: None)
        owner.assert_not_called()

    def test_unknown_fd9_refused(self):
        with self.assertRaises(m.Refusal):
            m.admit(lambda: None, lambda: GOOD, lambda: None)

    def test_truthy_integer_fd9_refused(self):
        with self.assertRaises(m.Refusal):
            m.admit(lambda: 1, lambda: GOOD, lambda: None)

    def test_fd9_busy_after_owner_readback(self):
        fn = mock.Mock()
        seq = iter([True, False])
        with self.assertRaisesRegex(m.Refusal, 'FD9_CHANGED_BEFORE_PRIVATE_PKG'):
            m.admit(lambda: next(seq), lambda: GOOD, fn)
        fn.assert_not_called()

    def test_unknown_owner_refused(self):
        fn = mock.Mock()
        with self.assertRaises(m.Refusal):
            m.admit(lambda: True, lambda: {}, fn)
        fn.assert_not_called()

    def test_running_owner_refused(self):
        fn = mock.Mock()
        with self.assertRaises(m.Refusal):
            m.admit(lambda: True,
                    lambda: dict(GOOD, real_old_status='RUNNING'), fn)
        fn.assert_not_called()

    def test_wrong_old_pkg_refused(self):
        fn = mock.Mock()
        with self.assertRaises(m.Refusal):
            m.admit(lambda: True,
                    lambda: dict(GOOD, old_package='unknown'), fn)
        fn.assert_not_called()

    def test_claimed_pkg_authorization_refused(self):
        fn = mock.Mock()
        with self.assertRaises(m.Refusal):
            m.admit(lambda: True,
                    lambda: dict(GOOD, safe_pkg_transaction_authorized=True), fn)
        fn.assert_not_called()

    def test_private_action_once(self):
        fn = mock.Mock(return_value='private')
        self.assertEqual(m.admit(lambda: True, lambda: GOOD, fn), 'private')
        fn.assert_called_once_with()

    def test_pkg_is_private_and_product_safety_false(self):
        source = SRC.read_text()
        self.assertIn('PKG_DBDIR=str(db)', source)
        self.assertNotIn("pkg + ['delete'", source)
        self.assertIn("'product_safety_acceptance_passed': False", source)

    def test_holder_process_cleanup_on_failure(self):
        source = SRC.read_text()
        self.assertIn('finally:', source)
        self.assertIn('child.terminate()', source)
        self.assertIn('child.kill()', source)


if __name__ == '__main__':
    unittest.main()
