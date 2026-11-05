#!/usr/bin/env python3
"""Stage 3.45 original FD9 CI-only witness interruption contracts, no local pkg."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def module(name):
    spec = importlib.util.spec_from_file_location(
        name.replace('-', '_').replace('.', '_'), HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


handoff = module('stage3-native-configd-fd9-handoff.py')


class NativeLiveWitnessRestartContracts(unittest.TestCase):
    def test_invalid_mode_refused(self):
        with mock.patch.dict(os.environ,
                             {'ZAPRET2_STAGE3_NATIVE_LIVE_RESTART': 'other'},
                             clear=True):
            with self.assertRaisesRegex(handoff.base.Refusal,
                                        'CI_LIVE_RESTART_MODE_INVALID'):
                handoff.live_witness_restart_mode()

    def test_mode_cannot_enable_without_explicit_disposable_ci_flag(self):
        with mock.patch.dict(os.environ, {
            'GITHUB_ACTIONS': 'true',
            'ZAPRET2_STAGE3_NATIVE_LIVE_RESTART': 'resume'
        }, clear=True), mock.patch.object(handoff, 'live_witness_mode',
                                           return_value=True):
            with self.assertRaisesRegex(handoff.base.Refusal,
                                        'CI_LIVE_RESTART_DISPOSABLE_LIVE_FD9_REQUIRED'):
                handoff.live_witness_restart_mode()

    def test_mode_cannot_enable_without_live_witness(self):
        with mock.patch.dict(os.environ, {
            'GITHUB_ACTIONS': 'true',
            'ZAPRET2_STAGE3_NATIVE_LIVE_RESTART': 'outage',
            'ZAPRET2_STAGE3_NATIVE_LIVE_RESTART_CI': '1'
        }, clear=True), mock.patch.object(handoff, 'live_witness_mode',
                                           return_value=False):
            with self.assertRaisesRegex(handoff.base.Refusal,
                                        'CI_LIVE_RESTART_DISPOSABLE_LIVE_FD9_REQUIRED'):
                handoff.live_witness_restart_mode()

    def test_only_two_ci_interruption_modes_admitted(self):
        for mode in ('resume', 'outage'):
            with self.subTest(mode=mode), mock.patch.dict(os.environ, {
                'GITHUB_ACTIONS': 'true',
                'ZAPRET2_STAGE3_NATIVE_LIVE_RESTART': mode,
                'ZAPRET2_STAGE3_NATIVE_LIVE_RESTART_CI': '1'
            }, clear=True), mock.patch.object(handoff, 'live_witness_mode',
                                               return_value=True), mock.patch.object(
                                                   handoff, 'fault_mode', return_value=''):
                self.assertEqual(handoff.live_witness_restart_mode(), mode)

    def test_native_worker_pauses_after_real_consume_before_final_status(self):
        worker = (HERE / 'stage3-native-configd-mutating-pkg.py').read_text()
        self.assertLess(worker.index('approval=grant_guard.verify('),
                        worker.index('ci_live_consumed_before_status'))
        self.assertLess(worker.index('ci_live_consumed_before_status'),
                        worker.index('second=grant_guard.verify('))
        self.assertLess(worker.index('second=grant_guard.verify('),
                        worker.index('delegate.admitted_pkg_dispatch(\n'
                                     '                archive,candidate,env,'
                                     'dispatch=verified_stdin_dispatch)'))
        self.assertIn('locked.check_fd9()\n            base.create_owned(handoff.PREPKG_READY', worker)
        self.assertIn('CI_NATIVE_LIVE_RESTART_BARRIER_NOT_AUTHORIZED', worker)

    def test_controller_proves_real_sqlite_commit_and_fd9_across_restart(self):
        source = (HERE / 'stage3-native-configd-fd9-handoff.py').read_text()
        self.assertIn('ci_live_consumed_before_status', source)
        self.assertIn('checkpoint=live.confirm(ROOT,ci_grant,head,nonce,', source)
        self.assertIn('expected_challenges=(2,)', source)
        self.assertIn('live_process=live.restart(ROOT,ci_grant,head,base.OLD,', source)
        self.assertIn('live_process.pid!=old_witness_pid', source)
        self.assertLess(source.index('checkpoint=live.confirm('),
                        source.index('live_process=live.restart('))
        restart_index = source.index('live_process=live.restart(')
        self.assertLess(restart_index,
                        source.index('base.create_owned(\n                PREPKG_RESUME,',
                                     restart_index))
        self.assertIn('base.check_original_fd9_busy()', source)

    def test_offline_status_must_refuse_no_pkg_preserve_original_owner(self):
        source = (HERE / 'stage3-native-configd-fd9-handoff.py').read_text()
        self.assertIn("if live_restart=='outage':\n            try:", source)
        self.assertIn("'ConnectionRefusedError' in reason", source)
        self.assertIn("'CI_LIVE_OUTAGE_PKG_OR_SQLITE_STATE_CHANGED'", source)
        self.assertIn("live_restart=='outage' or", source)
        self.assertIn("managed.owner_snapshot(old,guard,base.OLD)==before", source)
        self.assertIn("'PASS_TEST_ONLY_LIVE_STATUS_OUTAGE_NO_PKG'", source)

    def test_no_production_admission_claim_in_restart_receipt(self):
        source = (HERE / 'stage3-native-configd-fd9-handoff.py').read_text()
        self.assertIn("'ci_operator_grant_is_owner_approved':False", source)
        self.assertIn("'stock_web_firmware_or_direct_root_pkg_protected':False", source)
        self.assertIn("'lh08_ac11_accepted':False", source)
        self.assertIn("'ci_live_witness_status_outage_refused_pkg':", source)

    def test_ci_matrix_requires_distinct_actual_opnsense_guests(self):
        workflow = (ROOT / '.github/workflows/stage2-native-delegated-fd9-handoff.yml').read_text()
        self.assertIn('configd-native-live-mtls-sqlite-restart-fd9:', workflow)
        self.assertIn('mode: [resume, outage]', workflow)
        self.assertIn('ZAPRET2_STAGE3_NATIVE_LIVE_RESTART="${{ matrix.mode }}"', workflow)
        self.assertIn('uses: vmactions/opnsense-vm@', workflow)


if __name__ == '__main__':
    unittest.main()
