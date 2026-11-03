#!/usr/bin/env python3
"""Fast offline failure-adjudication tests for same original FD9 process."""
import importlib.util
import pathlib
import os
from unittest.mock import patch
import unittest

S=pathlib.Path(__file__).with_name('stage3-native-configd-fd9-faults.py')
sp=importlib.util.spec_from_file_location('stage3_fd9_faults',S)
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)


class FaultMatrixContracts(unittest.TestCase):
    def test_drop_ack_must_be_refused(self):
        d=m.classify('drop_ack',2,'','REFUSED:FD9_HANDOFF_ACK_NOT_QUALIFIED',True)
        self.assertEqual(d['status'],'REFUSED_MISSING_OR_TIMED_OUT_WORKER_ACK')
        self.assertFalse(d['observed_provisional_ack'])

    def test_timeout_must_be_refused(self):
        d=m.classify('stall_ack',2,'','REFUSED:timed_out',True)
        self.assertEqual(d['status'],'REFUSED_MISSING_OR_TIMED_OUT_WORKER_ACK')

    def test_post_ack_death_not_success_even_if_configctl_returns_zero(self):
        d=m.classify('post_ack_exit',0,'ACKED_CONTINUOUS_FD9_TRANSFER','',True)
        self.assertEqual(d['status'],'REFUSED_ACKED_WORKER_EXITED_BEFORE_DURABLE_OWNERSHIP')
        self.assertTrue(d['observed_provisional_ack'])

    def test_post_ack_exit_without_prior_ack_is_not_proven(self):
        with self.assertRaisesRegex(ValueError,'POST_ACK_CRASH_WAS_NOT_PROVEN_AFTER_ACK'):
            m.classify('post_ack_exit',0,'','',True)

    def test_no_ack_case_with_ack_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'NON_ACK_CASE_WAS_ACCIDENTALLY_ADMITTED'):
            m.classify('drop_ack',0,'ACKED_CONTINUOUS_FD9_TRANSFER','',True)

    def test_lock_still_held_after_any_failure_is_unqualified(self):
        for case,stdout in [('drop_ack',''),('stall_ack',''),
                            ('post_ack_exit','ACKED_CONTINUOUS_FD9_TRANSFER')]:
            with self.subTest(case=case),self.assertRaisesRegex(
                ValueError,'ORIGINAL_FD9_STILL_HELD_AFTER_FAULT'):
                m.classify(case,0,stdout,'',False)

    def test_unknown_case_or_malformed_exit_rejected(self):
        with self.assertRaisesRegex(ValueError,'INVALID_FAULT_OBSERVATION'):
            m.classify('bypass_pkg',0,'','',True)
        with self.assertRaisesRegex(ValueError,'INVALID_FAULT_OBSERVATION'):
            m.classify('drop_ack',None,'','',True)

    def test_test_only_fault_action_is_fixed_and_not_user_parameterized(self):
        ref=pathlib.Path(__file__).with_name('stage3-native-configd-fd9-handoff.py')
        if not ref.exists():
            self.skipTest('full source checkout required for existing _95 module')
        h=m.load('stage3-native-configd-fd9-handoff.py')
        with patch.dict(os.environ,{'ZAPRET2_STAGE3_HANDOFF_NEGATIVE':'1',
                                    'ZAPRET2_STAGE3_HANDOFF_FAULT':'drop_ack'}):
            action=h.action_bytes('a'*40).decode()
            self.assertIn('ZAPRET2_STAGE3_HANDOFF_FAULT=drop_ack',action)
            self.assertIn('ZAPRET2_STAGE3_HANDOFF_NEGATIVE=1',action)
            self.assertNotIn('%s',action)
        with patch.dict(os.environ,{'ZAPRET2_STAGE3_HANDOFF_NEGATIVE':'0',
                                    'ZAPRET2_STAGE3_HANDOFF_FAULT':'drop_ack'}):
            with self.assertRaises(h.base.Refusal):
                h.action_bytes('a'*40)
        with patch.dict(os.environ,{'ZAPRET2_STAGE3_HANDOFF_NEGATIVE':'1',
                                    'ZAPRET2_STAGE3_HANDOFF_FAULT':'pkg_add'}):
            with self.assertRaises(h.base.Refusal):
                h.action_bytes('a'*40)

    def test_real_path_and_single_file_ownership_are_required(self):
        src=S.read_text()
        for fragment in ('installer.install_and_verify(m.base.OLD)',
                         'guard.snapshot(m.base.OLD)',
                         'managed.owner_snapshot(old,guard,m.base.OLD)==baseline',
                         "m.ACTION.unlink()",'m.ROOT.rmdir()',
                         'm.base.LOCK','fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)'):
            self.assertIn(fragment,src)
        self.assertNotIn('pkg add -f',src)
        self.assertNotIn('pkg upgrade',src)


if __name__=='__main__':
    unittest.main()
