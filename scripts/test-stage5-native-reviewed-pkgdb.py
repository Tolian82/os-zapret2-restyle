#!/usr/bin/env python3
"""S0 native pkgdb source-policy contract; all tests offline."""
import importlib.util
from pathlib import Path
from subprocess import CompletedProcess
import unittest

SOURCE = Path(__file__).with_name('stage5-native-reviewed-pkgdb.py')
spec = importlib.util.spec_from_file_location('reviewed_pkgdb', SOURCE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def outcome(rc, stdout='', stderr=''):
    return CompletedProcess(['pkg'], rc, stdout, stderr)


class PkgdbEligibility(unittest.TestCase):
    def test_original_absent_status_still_allowed(self):
        state, report = policy.classify_pkgdb(
            outcome(1, stderr='No packages matching'), outcome(1), '0.6.5_88')
        self.assertEqual(state, 'absent')
        self.assertTrue(report['no_write'])

    def test_prior_registered_is_allowed_only_from_exact_dual_probes(self):
        state, report = policy.classify_pkgdb(
            outcome(0, '0.6.5_88\n'), outcome(0, 'os-zapret2-restyle-0.6.5_88\n'),
            '0.6.5_88')
        self.assertEqual(state, 'registered-prior')
        self.assertTrue(report['prior_version_matches'])
        self.assertEqual(policy.classify_pkgdb(
            outcome(0, '0.6.5_89\n'), outcome(0), '0.6.5_88')[0], 'refused')
        self.assertEqual(policy.classify_pkgdb(
            outcome(0, '0.6.5_88\n0.6.5_89'), outcome(0), '0.6.5_88')[0], 'refused')
        self.assertEqual(policy.classify_pkgdb(
            outcome(0, '0.6.5_88'), outcome(1), '0.6.5_88')[0], 'refused')
        self.assertEqual(policy.classify_pkgdb(
            outcome(0, '0.6.5_88', 'warning: other error'), outcome(0),
            '0.6.5_88')[0], 'refused')
        self.assertEqual(policy.classify_pkgdb(
            outcome(0, '0.6.5_88'), outcome(0, stderr='warning: other error'),
            '0.6.5_88')[0], 'refused')

    def test_corruption_malformed_lock_io_and_inconsistent_probes_refuse(self):
        for message in ('database is malformed', 'database is locked',
                        'database is corrupt', 'SQL Error', 'IO ERROR'):
            with self.subTest(stderr=message):
                s, e = policy.classify_pkgdb(
                    outcome(0, '0.6.5_88', stderr=message), outcome(0), '0.6.5_88')
                self.assertEqual(s, 'refused')
                self.assertTrue(e['possible_db_error'])
                s, e = policy.classify_pkgdb(outcome(1, stderr=message),
                                              outcome(1), '0.6.5_88')
                self.assertEqual(s, 'refused')
        self.assertEqual(policy.classify_pkgdb(outcome(1), outcome(0), '0.6.5_88')[0],
                         'refused')
        self.assertEqual(policy.classify_pkgdb(outcome(0, '0.6.5_88'),
                                                outcome(0), '')[0], 'refused')

    def test_diagnostics_do_not_expose_versions_credentials_or_raw_errors(self):
        s, evidence = policy.classify_pkgdb(outcome(1, stderr='database is malformed: secret'),
                                            outcome(1), 'PRIVATE_TOKEN')
        self.assertEqual(s, 'refused')
        self.assertNotIn('secret', str(evidence))
        self.assertNotIn('PRIVATE_TOKEN', str(evidence))
        self.assertNotIn('malformed: secret', str(evidence))
        self.assertTrue(evidence['no_write'])


if __name__ == '__main__':
    unittest.main()
