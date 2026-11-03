#!/usr/bin/env python3
"""Runnable negative/cold contract for native late-unsafe-owner pkg dispatch."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(
        'test_' + name.replace('-', '_').replace('.', '_'), HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


positive = load('stage2-native-delegated-fd9-handoff.py')
negative = load('stage3-native-late-owner-veto.py')


class SharedNativeDispatchGateTests(unittest.TestCase):
    def test_eligible_real_gate_allows_only_explicit_dispatch(self):
        calls = []
        def safe_fake(*args):
            calls.append(args)
            return (0, 'non-native test result', '')
        with patch.object(positive, 'verify_old_cold_admission',
                          return_value='AUTHENTIC_OLD_COLD_OWNER_UNDER_ORIGINAL_FD9') as guard:
            result = positive.admitted_pkg_dispatch(
                Path('/old.pkg'), Path('/new.pkg'), {'TEST':'1'},
                dispatch=safe_fake)
        self.assertEqual(result, (0, 'non-native test result', ''))
        guard.assert_called_once_with(Path('/old.pkg'))
        self.assertEqual(calls, [(Path('/new.pkg'), {'TEST':'1'})])

    def test_late_owner_refusal_cannot_enter_actual_native_dispatch(self):
        for reason in (
            'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:COMMON_APPLY',
            'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED',
            'INDEPENDENT_FD9_NOT_BUSY:0',
            'GENUINE_INSTALLED_PREDECESSOR_UNVERIFIED',
            'PKGDB_SERVICE_OR_CONFIG_CHANGED_WITHIN_LOCK'
        ):
            with self.subTest(reason=reason), \
                 patch.object(positive, 'verify_old_cold_admission',
                              side_effect=positive.Refusal(reason)), \
                 patch.object(positive, 'run_pkg',
                              side_effect=AssertionError('NATIVE_PKG_REACHED')) as native:
                with self.assertRaisesRegex(positive.Refusal, reason):
                    positive.admitted_pkg_dispatch(
                        Path('/old.pkg'), Path('/new.pkg'), {})
                native.assert_not_called()

    def test_same_final_gate_rejects_actual_native_ipfw_and_journal_reasons(self):
        for reason, expected in (
            ('UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:/var/run/journal',
             'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:'),
            ('KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED',
             'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED')):
            with self.subTest(reason=reason), \
                 patch.object(positive, 'verify_old_cold_admission',
                              side_effect=positive.Refusal(reason)):
                self.assertEqual(
                    negative.latest_gate_verdict(positive, Path('/old.pkg'), expected),
                    'DENIED_BEFORE_DISPATCH')
        with patch.object(positive, 'verify_old_cold_admission',
                          side_effect=positive.Refusal('SOME_OTHER_FAILURE')):
            with self.assertRaisesRegex(negative.Refusal,
                                        'WRONG_FINAL_ADMISSION_REFUSAL'):
                negative.latest_gate_verdict(
                    positive, Path('/old.pkg'),
                    'UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:')

    def test_no_false_negative_when_tripwire_would_reach_pkg(self):
        with patch.object(positive, 'verify_old_cold_admission',
                          return_value='AUTHENTIC_OLD_COLD_OWNER_UNDER_ORIGINAL_FD9'):
            with self.assertRaisesRegex(negative.Refusal,
                                        'NATIVE_MUTATING_PKG_DISPATCH_REACHED'):
                negative.latest_gate_verdict(
                    positive, Path('/old.pkg'),
                    'KERNEL_IPFW_OR_IPDIVERT_LOADED_OR_UNQUALIFIED')

    def test_test_owned_cold_tripwire_proves_dispatch_reachable_without_pkg(self):
        with patch.object(positive, 'verify_old_cold_admission',
                          return_value='AUTHENTIC_OLD_COLD_OWNER_UNDER_ORIGINAL_FD9') as probe, \
             patch.object(positive, 'run_pkg',
                          side_effect=AssertionError('REAL_NATIVE_PKG_WAS_CALLED')) as pkg:
            self.assertEqual(
                negative.clean_tripwire(positive, Path('/old.pkg')),
                'QUALIFIED_COLD_REACHED_NONMUTATING_DISPATCH_TRIPWIRE')
        self.assertEqual(probe.call_count, 2)
        pkg.assert_not_called()

    def test_case_classifier_refuses_forged_success_and_unsafe_rc(self):
        import json
        for case, actual in (
            ('cold', 'PASS_TEST_ONLY_LATE_LATE_JOURNAL_DENIED_BEFORE_PKG'),
            ('late_journal', 'PASS_TEST_ONLY_COLD_GATE_REACHED_TRIPWIRE'),
            ('late_orphan', 'SOMETHING_ELSE')):
            proc = SimpleNamespace(
                returncode=0, stderr='',
                stdout=negative.PREFIX + json.dumps({
                    'status': actual,
                    'real_pkg_mutation_invoked': False,
                    'lh08_ac11_accepted': False}) + '\n')
            with self.subTest(case=case), self.assertRaisesRegex(
                    negative.Refusal, 'FALSE_LATE_NATIVE_PKG_SAFETY_REPORT'):
                negative.classify(proc, case)
        for rc in (2, 75, 1):
            with self.subTest(rc=rc), self.assertRaisesRegex(
                    negative.Refusal, 'LATE_OWNER_NATIVE_WITNESS_REFUSED'):
                negative.classify(
                    SimpleNamespace(returncode=rc, stdout='', stderr='DENIED'), 'cold')

    def test_source_orders_final_owner_revalidation_before_real_pkg(self):
        positive_source = (HERE / 'stage2-native-delegated-fd9-handoff.py').read_text()
        negative_source = (HERE / 'stage3-native-late-owner-veto.py').read_text()
        self.assertIn('rc, out, err = admitted_pkg_dispatch(archive, successor, env)',
                      positive_source)
        idx = positive_source.index('def admitted_pkg_dispatch(')
        body = positive_source[idx:positive_source.index('def inside_lock(', idx)]
        self.assertLess(body.index('verify_old_cold_admission(archive)'),
                        body.index('run_pkg if dispatch is None'))
        self.assertIn("locked.inside_lock(archive)", positive_source)
        self.assertIn("unsafe.add_test_orphan()", negative_source)
        self.assertIn("unknown.create_owned_corrupt_journal()", negative_source)
        self.assertIn("managed.owner_snapshot(old, guard, archive) == injected",
                      negative_source)
        self.assertIn("NATIVE_MUTATING_PKG_DISPATCH_REACHED", negative_source)
        for forbidden in ('pkg add -f', 'ipfw flush', 'configctl zapret stop'):
            self.assertNotIn(forbidden, negative_source)

    def test_native_workflow_target_only_no_package_publication(self):
        workflow=(HERE.parent / '.github/workflows/stage2-native-delegated-fd9-handoff.yml').read_text()
        self.assertIn('vmactions/opnsense-vm@abaa977e3dbc77a0d1eeed4d82c8d9914b018235',
                      workflow)
        self.assertIn('release: "26.7"', workflow)
        self.assertIn('ZAPRET2_STAGE3_LATE_OWNER_VETO=1', workflow)
        self.assertIn('test-stage3-native-late-owner-veto.py -v', workflow)
        self.assertNotIn('pkg add -f', workflow)
        self.assertNotIn('pkg unlock', workflow)

if __name__ == '__main__':
    unittest.main()
