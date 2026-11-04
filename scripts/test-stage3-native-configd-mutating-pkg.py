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
                  'clean.verify_installed_files(source_for_manifest,manifest)',
                  'stopped.prove_preserved_config(',
                  'GENUINE_HISTORICAL_HOOK_FD9_DELEGATION_NOT_OBSERVED'):
            self.assertIn(x,text)

    def test_stdin_native_positive_only_with_disposable_ci_flags(self):
        handoff_path=HERE/'stage3-native-configd-fd9-handoff.py'
        spec=importlib.util.spec_from_file_location('stdin_native_handoff',handoff_path)
        handoff=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handoff)
        with patch.dict(os.environ,{'ZAPRET2_STAGE3_NATIVE_STDIN_PKG':'bad'},clear=True):
            with self.assertRaisesRegex(Exception,'NATIVE_STDIN_PKG_MODE_INVALID'):
                handoff.native_stdin_pkg_mode()
        with patch.dict(os.environ,{'ZAPRET2_STAGE3_NATIVE_STDIN_PKG':'1'},clear=True):
            with self.assertRaisesRegex(Exception,'NATIVE_STDIN_PKG_NOT_DISPOSABLE'):
                handoff.native_stdin_pkg_mode()
        env={
          'ZAPRET2_STAGE3_NATIVE_STDIN_PKG':'1',
          'ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI':'1',
          'GITHUB_ACTIONS':'true',
          'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG':'1',
          'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI':'1',
          'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK':'1',
          'ZAPRET2_NATIVE_BUILD_CI':'1',
          'ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF':'1',
          'ZAPRET2_STAGE3_READONLY_PKG':'1',
          'ZAPRET2_STAGE3_READONLY_PKG_CI':'1'}
        with patch.dict(os.environ,env,clear=True):
            self.assertTrue(handoff.native_stdin_pkg_mode())
        with patch.dict(os.environ,{
          **env,'ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER':'1',
          'ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER_CI':'1'},clear=True):
            with self.assertRaisesRegex(Exception,'NATIVE_STDIN_PKG_NOT_DISPOSABLE'):
                handoff.native_stdin_pkg_mode()

    def test_stdin_snapshot_after_final_grant_before_real_pkg(self):
        source=SOURCE.read_text()
        initial=source.index('approval=grant_guard.verify(')
        final=source.index('second=grant_guard.verify(',initial)
        recheck=source.index('attest_candidate_fd9(product,candidate,selected_sha,revision,expected_inode)',final)
        snapshot=source.index('stream.freeze_exact_candidate(',recheck)
        dispatcher=source.index('delegate.admitted_pkg_dispatch(',snapshot)
        self.assertLess(initial,final)
        self.assertLess(final,recheck)
        self.assertLess(recheck,snapshot)
        self.assertLess(snapshot,dispatcher)
        self.assertIn('verified_stdin_dispatch',source)
        self.assertIn('stream.install_frozen_stdin(',source)
        self.assertIn('clean.verify_installed_files(source_for_manifest,manifest)',source)
        self.assertIn('GENUINE_HISTORICAL_HOOK_FD9_DELEGATION_NOT_OBSERVED',source)
        self.assertIn("'ci_pkg_consumed_verified_stdin_bytes':stdin_mode",source)

    def test_stdin_positive_controller_and_native_ci_scoped(self):
        controller=(HERE/'stage3-native-configd-fd9-handoff.py').read_text()
        workflow=(HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml').read_text()
        self.assertIn('native_stdin_pkg_mode()',controller)
        self.assertIn('NATIVE_STDIN_PKG_NOT_DISPOSABLE',controller)
        self.assertIn("done.get('ci_pkg_consumed_verified_stdin_bytes') is stdin_pkg",controller)
        self.assertIn("'ci_native_pkg_verified_stdin_mode':stdin_pkg and pkg_enabled",controller)
        self.assertIn("'final_owner_check_to_pkg_race_closed':False",controller)
        self.assertIn('configd-native-pkg-verified-stdin:',workflow)
        self.assertIn('ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI=1',workflow)

    def test_real_path_swap_mode_requires_stdin_and_disposable_guest(self):
        controller=HERE/'stage3-native-configd-fd9-handoff.py'
        spec=importlib.util.spec_from_file_location('isolated_stdin_path_controller',controller)
        obj=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(obj)
        with patch.dict(os.environ,{'ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP':'invalid'},clear=True):
            with self.assertRaisesRegex(Exception,'CI_STDIN_PATH_SWAP_MODE_INVALID'):
                obj.native_stdin_path_swap_mode()
        with patch.dict(os.environ,{'ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP':'1'},clear=True):
            with self.assertRaisesRegex(Exception,'CI_STDIN_PATH_SWAP_NOT_DISPOSABLE'):
                obj.native_stdin_path_swap_mode()
        env={
            'GITHUB_ACTIONS':'true','ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP':'1',
            'ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP_CI':'1',
            'ZAPRET2_STAGE3_NATIVE_STDIN_PKG':'1',
            'ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI':'1',
            'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG':'1',
            'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI':'1',
            'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK':'1',
            'ZAPRET2_NATIVE_BUILD_CI':'1',
            'ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF':'1',
            'ZAPRET2_STAGE3_READONLY_PKG':'1',
            'ZAPRET2_STAGE3_READONLY_PKG_CI':'1'}
        with patch.dict(os.environ,env,clear=True):
            self.assertTrue(obj.native_stdin_path_swap_mode())
        env['ZAPRET2_STAGE3_NATIVE_STDIN_PKG']=''
        with patch.dict(os.environ,env,clear=True):
            with self.assertRaisesRegex(Exception,'CI_STDIN_PATH_SWAP_NOT_DISPOSABLE'):
                obj.native_stdin_path_swap_mode()

    def test_stdin_path_swap_barrier_requires_frozen_bytes_before_actual_pkg(self):
        source=SOURCE.read_text()
        signed=source.index('second=grant_guard.verify(')
        snapshot=source.index('frozen=stream.freeze_exact_candidate(',signed)
        armed=source.index("'frozen_snapshot_complete':True",snapshot)
        wait=source.index('CI_STDIN_PATH_SWAP_BARRIER_NOT_RELEASED',armed)
        changed=source.index('CI_STDIN_CANDIDATE_PATH_NOT_ACTUALLY_REBOUND',wait)
        pkg=source.index('delegate.admitted_pkg_dispatch(',changed)
        manifest=source.index('clean.installed_pkg_manifest(source_for_manifest)',pkg)
        self.assertLess(signed,snapshot)
        self.assertLess(snapshot,armed)
        self.assertLess(armed,wait)
        self.assertLess(wait,changed)
        self.assertLess(changed,pkg)
        self.assertLess(pkg,manifest)
        self.assertIn("observed_rebound_sha!=selected_sha",source)
        self.assertIn("reference.write(frozen.data)",source)
        self.assertIn("'ci_stdin_frozen_manifest_verified':stdin_path_swap",source)
        self.assertIn("'lh08_ac11_accepted':False",source)

    def test_controller_rebinds_only_after_authentic_frozen_worker_marker(self):
        controller=(HERE/'stage3-native-configd-fd9-handoff.py').read_text()
        workflow=(HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml').read_text()
        armed=controller.index("'frozen_snapshot_complete') is True")
        swapped=controller.index('attack.atomic_rebind(',armed)
        resume=controller.index('RESUME_TEST_ONLY_AFTER_STDIN_SNAPSHOT_PATH_REBIND',swapped)
        final=controller.index("swap_data.get('ci_stdin_rebound_sha256')",resume)
        restore=controller.index('attack.restore_original_after_verified_pkg(',final)
        self.assertLess(armed,swapped)
        self.assertLess(swapped,resume)
        self.assertLess(resume,final)
        self.assertLess(final,restore)
        self.assertIn("swapped_archive['replacement_sha256']!=native_archive_sha",controller)
        self.assertIn("'ci_stdin_original_path_restored':stdin_original_restored",controller)
        self.assertIn("if stdin_path_swap else",controller)
        self.assertIn("configd-native-stdin-post-snapshot-path-swap:",workflow)
        self.assertIn("ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP_CI=1",workflow)

    def test_path_swap_evidence_is_bounded_sidecar_not_historical_done(self):
        controller=(HERE/'stage3-native-configd-fd9-handoff.py').read_text()
        self.assertIn("SWAP_RESULT=ROOT/'stdin-path-swap-result.json'",controller)
        self.assertIn("swap_result={key:verdict.pop(key) for key in swap_keys}",controller)
        self.assertIn('base.create_owned(SWAP_RESULT,json.dumps({',controller)
        self.assertIn("swap_data.get('sha')==head",controller)
        self.assertIn("swap_data.get('pid')==ready['pid']",controller)
        self.assertIn("swap_data.get('original_fd9_inode')==ready['original_fd9_inode']",controller)
        self.assertIn("swap_data.get('nonce_sha256')==ready['nonce_sha256']",controller)
        self.assertIn('base.trusted(SWAP_RESULT,1024)',controller)
        self.assertIn('SWAP_RESULT)\n              if stdin_path_swap else',controller)
        self.assertIn('TEST_RESULT_UNBOUNDED',(
            HERE/'stage3-native-configd-detached-fd9.py').read_text())
        self.assertNotIn("done.get('ci_stdin_rebound_sha256')",controller)

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
