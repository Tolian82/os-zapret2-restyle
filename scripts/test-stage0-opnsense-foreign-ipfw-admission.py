#!/usr/bin/env python3
"""Offline contracts for real-kernel foreign-count-rule negative witness."""
import importlib.util
from pathlib import Path
from unittest import TestCase, main, mock

SOURCE = Path(__file__).with_name('stage0-opnsense-foreign-ipfw-admission.py')
spec = importlib.util.spec_from_file_location('foreign_ipfw', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TestForeignIPFW(TestCase):
    def test_only_default(self):
        self.assertTrue(m.only_default(m.DEFAULT + '\n'))
        self.assertFalse(m.only_default(''))

    def test_native_built_in_orphan_counter_is_not_foreign(self):
        self.assertTrue(m.only_default(m.ORPHAN + '\n' + m.DEFAULT))
        self.assertTrue(m.only_injected_foreign(
            m.ORPHAN + '\n' + m.RULE_TEXT + '\n' + m.DEFAULT))

    def test_duplicate_orphan_counter_refused(self):
        self.assertFalse(m.only_default(m.ORPHAN + '\n' + m.ORPHAN + '\n' + m.DEFAULT))

    def test_lookalike_orphan_counter_refused(self):
        self.assertFalse(m.only_default(
            '65535 count ip from any to any not // foreign dynamic counter\n' + m.DEFAULT))

    def test_foreign_count_exact(self):
        self.assertTrue(m.only_injected_foreign(m.RULE_TEXT + '\n' + m.DEFAULT + '\n'))

    def test_foreign_count_reverse(self):
        self.assertTrue(m.only_injected_foreign(m.DEFAULT + '\n' + m.RULE_TEXT))

    def test_delete_refuses_other_rules(self):
        self.assertFalse(m.only_injected_foreign(m.RULE_TEXT + '\n123 allow ip from any to any\n'+m.DEFAULT))

    def test_delete_refuses_other_number(self):
        self.assertFalse(m.only_injected_foreign('63036 count ip from any to any\n' + m.DEFAULT))

    def test_delete_refuses_divert(self):
        self.assertFalse(m.only_injected_foreign('63037 divert 989 ip from any to any\n' + m.DEFAULT))

    def test_default_check_refuses_other_rule(self):
        self.assertFalse(m.only_default(m.RULE_TEXT + '\n' + m.DEFAULT))

    def test_rejects_kernel_loaded(self):
        guard = mock.Mock()
        class Denied(Exception): pass
        guard.Refusal = Denied
        guard.require_snapshot_before.side_effect = Denied('KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED')
        self.assertEqual(m.refuse_before_private_callback(guard, lambda: None),
                         'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED')

    def test_rejects_unknown_running_old(self):
        guard = mock.Mock()
        class Denied(Exception): pass
        guard.Refusal = Denied
        guard.require_snapshot_before.side_effect = Denied('REAL_OLD_SERVICE_NOT_PROVEN_STOPPED:2')
        self.assertEqual(m.refuse_before_private_callback(guard, lambda: None),
                         'REAL_OLD_SERVICE_NOT_PROVEN_STOPPED:2')

    def test_rejects_wrong_refusal(self):
        guard = mock.Mock()
        class Denied(Exception): pass
        guard.Refusal = Denied
        guard.require_snapshot_before.side_effect = Denied('INVALID_TEST_STATE')
        with self.assertRaisesRegex(m.Refusal, 'UNEXPECTED_OWNER_REFUSAL'):
            m.refuse_before_private_callback(guard, lambda: None)

    def test_gate_acceptance_is_a_failure(self):
        guard = mock.Mock()
        guard.require_snapshot_before.return_value = None
        with self.assertRaisesRegex(m.Refusal, 'UNSAFE_SNAPSHOT_ACCEPTED'):
            m.refuse_before_private_callback(guard, lambda: None)

    def test_real_guest_only(self):
        with mock.patch.object(m.os, 'geteuid', return_value=999):
            with self.assertRaisesRegex(m.Refusal, 'ONLY_DISPOSABLE'):
                m.run(Path('/bogus'))

    def test_no_product_upgrade_claim(self):
        text = SOURCE.read_text()
        for marker in ("'native_pkg_operation_executed': False",
                       "'real_running_engine_tested': False",
                       "'safe_pkg_transaction_proved': False",
                       "'uncoordinated_root_pkg_excluded': False",
                       "'stage0_closed': False"):
            self.assertIn(marker,text)


if __name__ == '__main__':
    main()
