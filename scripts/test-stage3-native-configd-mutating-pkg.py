#!/usr/bin/env python3
"""Offline fail-closed contracts for one-use configd-transferred native pkg.

All pure negative checks are runnable off-target; only disposable OPNsense
CI may invoke the genuine mutating pkg, real historical hooks, or original FD9.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'stage3-native-configd-mutating-pkg.py'
spec=importlib.util.spec_from_file_location('configd_native_mutating',SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativePkgContract(unittest.TestCase):
    def test_official_candidate_exact_version_and_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'os-zapret2-restyle-0.6.2_99.pkg'
            p.write_bytes(b'one-use-fake-candidate-for-offline-pure-tests')
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            with patch.object(m,'load_product_candidate') as load:
                load.return_value.inspect_archive.return_value={
                    'status':'READ_ONLY_NATIVE_PKG_ARCHIVE_BOUND','sha256':digest}
                result=m.validate_candidate(p,digest,'99')
                self.assertEqual(result['sha256'],digest)
                load.return_value.inspect_archive.assert_called_once_with(
                    p,'0.6.2_99',digest)

    def test_candidate_refuses_wrong_sha_and_revision(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'os-zapret2-restyle-0.6.2_99.pkg'
            p.write_bytes(b'test-candidate')
            good=hashlib.sha256(p.read_bytes()).hexdigest()
            for sha,rev in [('0'*64,'99'),(good,'98'),('invalid','99'),
                            (good,'../99')]:
                with self.subTest(sha=sha,rev=rev),self.assertRaises(m.Refusal):
                    m.validate_candidate(p,sha,rev)

    def test_package_selection_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            actual=Path(d)/'genuine.pkg'
            actual.write_bytes(b'x')
            p=Path(d)/'os-zapret2-restyle-0.6.2_99.pkg'
            p.symlink_to(actual)
            product=m.load_product_candidate()
            with patch.object(product.os,'geteuid',return_value=0),\
                 patch.object(m,'load_product_candidate',return_value=product),\
                 self.assertRaisesRegex(m.Refusal,'ARCHIVE_UNQUALIFIED'):
                m.validate_candidate(p,hashlib.sha256(b'x').hexdigest(),'99')

    def test_success_requires_hook_invocation_not_only_pkg_rc(self):
        with self.assertRaisesRegex(m.Refusal,'HOOK_FD9_DELEGATION'):
            m.accept_pkg_effect(0,'os-zapret2-restyle was installed.','',
                                'os-zapret2-restyle|0.6.2_99',
                                'os-zapret2-restyle|0.6.2_99',0)

    def test_genuine_native_historical_hook_acceptance(self):
        self.assertTrue(m.accept_pkg_effect(
            0,'os-zapret2-restyle was installed.','',
            'os-zapret2-restyle|0.6.2_99',
            'os-zapret2-restyle|0.6.2_99',2))

    def test_native_pkg_failure_refuses_despite_hook_calls(self):
        for rc in (1,2,75):
            with self.subTest(rc=rc),self.assertRaisesRegex(
                    m.Refusal,'INSTALL_OR_OLD_HOOKS_UNQUALIFIED'):
                m.accept_pkg_effect(rc,'os-zapret2-restyle was installed.','',
                    'os-zapret2-restyle|0.6.2_99',
                    'os-zapret2-restyle|0.6.2_99',2)

    def test_native_wrong_installed_version_refuses(self):
        with self.assertRaisesRegex(m.Refusal,'INSTALL_OR_OLD_HOOKS_UNQUALIFIED'):
            m.accept_pkg_effect(0,'os-zapret2-restyle was installed.','',
                'os-zapret2-restyle|0.6.2_1',
                'os-zapret2-restyle|0.6.2_99',1)

    def test_refusing_real_hooks_cannot_be_mistaken_for_success(self):
        for diagnostic in ('incomplete zapret lifecycle',
                           'cannot determine zapret service state',
                           'could not be stopped'):
            with self.subTest(diagnostic=diagnostic),self.assertRaisesRegex(
                    m.Refusal,'INSTALL_OR_OLD_HOOKS_UNQUALIFIED'):
                m.accept_pkg_effect(0,'os-zapret2-restyle was installed.',diagnostic,
                    'os-zapret2-restyle|0.6.2_99',
                    'os-zapret2-restyle|0.6.2_99',1)

    def test_late_refusal_specific_not_any_error(self):
        class Refusal(Exception):
            pass
        self.assertTrue(m.qualify_late_native_refusal(
            Refusal('UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:bad'),False))
        for err,reached in (
                (Refusal('different error'),False),
                (Exception('UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:bad'),False),
                (Refusal('UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:bad'),True)):
            with self.subTest(err=str(err),reached=reached),self.assertRaisesRegex(
                    m.Refusal,'LATE_REAL_PKG_DISPATCH_VETO_UNQUALIFIED'):
                m.qualify_late_native_refusal(err,reached)

    def test_late_dispatch_barrier_and_tripwire_wired(self):
        code=SOURCE.read_text()
        for fragment in ('late_journal_fault=False',
                         'dispatch=forbidden_dispatch',
                         'NATIVE_PKG_LATE_JOURNAL_BARRIER_NOT_RELEASED',
                         'REFUSED_TEST_ONLY_REAL_NATIVE_DISPATCH_LATE_JOURNAL'):
            self.assertIn(fragment,code)

    def test_no_mutating_pkg_without_explicit_dual_optin(self):
        with patch.dict(os.environ,{
                'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG':'',
                'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI':''}):
            with self.assertRaisesRegex(m.Refusal,'OPTIN_REQUIRED'):
                m.native_transaction(None,'0'*64,'99',1)

    def test_product_archive_gate_rechecked_under_original_fd9(self):
        code=SOURCE.read_text()
        self.assertIn('product.inspect_archive(',code)
        self.assertIn('product.inspect_with_original_fd9(',code)
        self.assertIn('attest_candidate_fd9(product,candidate,selected_sha,revision,expected_inode)',code)
        self.assertIn("'product_candidate_fd9_rechecked':True",code)
        self.assertNotIn('path.stat().st_uid',code)

    def test_source_uses_shared_final_gate_and_original_historical_fd9(self):
        text=SOURCE.read_text()
        for x in ('delegate.admitted_pkg_dispatch(archive,candidate,env)',
                  'locked.check_fd9()', 'pass_fds=(9,)',
                  "'LOCKF_BIN':str(script)", 'native_mutating_pkg_invoked',
                  'clean.verify_installed_files(candidate,manifest)',
                  'stopped.prove_preserved_config(',
                  'GENUINE_HISTORICAL_HOOK_FD9_DELEGATION_NOT_OBSERVED'):
            self.assertIn(x,text)

    def test_core_configd_worker_and_ci_job_connect_exact_mode(self):
        core=HERE/'stage3-native-configd-fd9-handoff.py'
        workflow=HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml'
        if not core.exists() or not workflow.exists():
            self.skipTest('full repository checkout mandatory for CI')
        code=core.read_text()
        yml=workflow.read_text()
        for x in ('def native_pkg_mode():', 'transaction.native_transaction(',
                  'native.build()', 'PASS_TEST_ONLY_CONFIGD_NATIVE_PKG_UNDER_ORIGINAL_FD9',
                  'NATIVE_CONFIGD_PKG_OR_OWNERSHIP_ATTESTATION_UNQUALIFIED',
                  'native_mutating_pkg_under_detached_fd9',
                   'def native_late_journal_mode():',
                   'NATIVE_PKG_PRE_DISPATCH_BARRIER_NOT_AUTHENTIC'):
            self.assertIn(x,code)
        for x in ('  configd-native-mutating-pkg:',
                  '  configd-readonly-pkg:', '  configd-late-owner-veto:',
                  '  configd-atomic-handoff-faults:',
                  'scripts/test-stage3-native-configd-mutating-pkg.py -v',
                  'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG=1',
                   '  configd-native-late-journal-dispatch:',
                   'ZAPRET2_STAGE3_NATIVE_LATE_JOURNAL=1'):
            self.assertIn(x,yml)


if __name__=='__main__':
    unittest.main()
