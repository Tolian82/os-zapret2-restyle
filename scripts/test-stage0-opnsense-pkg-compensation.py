#!/usr/bin/env python3
"""Fail-closed independent hook-failure and compensation contracts."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

SRC = Path(__file__).with_name('stage0-opnsense-pkg-compensation.py')
spec = importlib.util.spec_from_file_location('stage0_pkg_compensation', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
EVENTS = m.INITIAL + m.FAULT


class CompensationTests(unittest.TestCase):
    def test_expected_native_hook_success_rc_with_fault_is_hazard(self):
        self.assertEqual(m.classify_mutation(0, m.NEW, EVENTS),
                         'NATIVE_PKG_RETURNED_SUCCESS_AFTER_FAILED_POST_INSTALL')

    def test_wrong_pkg_result_refuses(self):
        with self.assertRaisesRegex(m.Refusal, 'RETURN_BEHAVIOR_DIFFERENT'):
            m.classify_mutation(1, m.NEW, EVENTS)

    def test_unmodified_fixture_does_not_claim_mutation(self):
        with self.assertRaisesRegex(m.Refusal, 'PKG_MUTATION_NOT_PROVEN'):
            m.classify_mutation(0, m.OLD, EVENTS)

    def test_foreign_fixture_refused(self):
        with self.assertRaises(m.Refusal):
            m.classify_mutation(0, ('foreign', b'faulted\n'), EVENTS)

    def test_missing_fault_receipt_refused(self):
        with self.assertRaisesRegex(m.Refusal, 'PHASES_NOT_EXACT'):
            m.classify_mutation(0, m.NEW, m.INITIAL + ('faulted:pre-install',))

    def test_extra_hook_refused(self):
        with self.assertRaises(m.Refusal):
            m.classify_mutation(0, m.NEW, EVENTS + ('old:pre-deinstall',))

    def test_malformed_hook_order_refused(self):
        with self.assertRaises(m.Refusal):
            m.classify_mutation(0, m.NEW, tuple(reversed(EVENTS)))

    def test_exact_compensation_receipt(self):
        self.assertEqual(m.assert_compensated(m.OLD, EVENTS + m.INITIAL),
                         'PRIVATE_FIXTURE_RESTORED_AFTER_DETECTED_HOOK_FAULT')

    def test_old_pkg_not_restored_refused(self):
        with self.assertRaisesRegex(m.Refusal, 'DID_NOT_RESTORE_OLD'):
            m.assert_compensated(m.NEW, EVENTS + m.INITIAL)

    def test_missing_rollback_hook_receipt_refused(self):
        with self.assertRaisesRegex(m.Refusal, 'PHASES_NOT_EXACT'):
            m.assert_compensated(m.OLD, EVENTS + ('old:pre-install',))

    def test_forged_extra_rollback_trace_refused(self):
        with self.assertRaises(m.Refusal):
            m.assert_compensated(m.OLD, EVENTS + m.INITIAL + ('old:post-deinstall',))

    def test_private_archive_identity_requires_known_role(self):
        with self.assertRaisesRegex(m.Refusal, 'UNEXPECTED_SYNTHETIC_ROLE'):
            m.build(Path('/tmp'), 'unknown', Path('/tmp/trace'), Path('/tmp'), Mock())

    def test_product_rollback_is_not_claimed(self):
        text = SRC.read_text()
        self.assertIn("'actual_product_rollback_tested': False", text)
        self.assertIn("'crash_atomicity_proved': False", text)
        self.assertIn('PKG_DBDIR=str(db)', text)


if __name__ == '__main__':
    unittest.main()
