#!/usr/bin/env python3
"""No-pkg, fixed-owner, FD9 and process-lifetime contracts for native daemon."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
FILE=HERE/'stage3-native-configd-detached-fd9.py'
sp=importlib.util.spec_from_file_location('test_stage3_detached_fd9',FILE)
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)
HEAD='a'*40


class DetachedFD9Contracts(unittest.TestCase):
    def test_configd_action_is_fixed_root_only_and_has_no_pkg(self):
        value=m.action_bytes(HEAD).decode()
        self.assertIn('[launch]\n',value)
        self.assertIn('type:script_output',value)
        self.assertIn('ZAPRET2_STAGE3_DETACHED_FD9=1',value)
        self.assertIn('--launch '+HEAD,value)
        self.assertNotIn('%s',value)
        self.assertNotIn('pkg add -f',value)
        self.assertNotIn('pkg upgrade',value)

    def test_daemon_invocation_uses_pid_supervisor_and_never_mutating_pkg(self):
        with patch.object(m,'qualify'),\
             patch.object(m,'trusted',return_value=m.action_bytes(HEAD)),\
             patch.object(m,'PIDFILE',Path('/tmp/nothing-stage3.pid')),\
             patch.object(m,'READY',Path('/tmp/nothing-stage3.ready')),\
             patch.object(m,'RELEASE',Path('/tmp/nothing-stage3.release')),\
             patch.object(m,'DONE',Path('/tmp/nothing-stage3.done')),\
             patch.object(m.subprocess,'run',
                          return_value=SimpleNamespace(returncode=0,
                                                       stdout='',stderr='')) as call:
            report=m.launch(HEAD)
        self.assertEqual(report['status'],'DETACHED_DAEMON_LAUNCH_RETURNED')
        args=call.call_args.args[0]
        self.assertEqual(args[:3],['/usr/sbin/daemon','-f','-P'])
        self.assertIn('--worker',args)
        self.assertNotIn('pkg',args)

    def test_no_false_ready_acceptance_for_unqualified_or_forged_fd9(self):
        good={'status':'HELD_AUTHENTIC_FD9_IN_DETACHED_WORKER',
              'pid':701,'ppid':702,'original_fd9_held':True,
              'cold_old_owner':True,'created_original_lock_inode':True,
              'original_fd9_inode':772901,
              'native_pkg_mutation_invoked':False,
              'schema':1,'sha':HEAD}
        self.assertEqual(m.inspect_ready(json.dumps(good).encode(),HEAD),good)
        for bad in (
            {'pid':-1},{'ppid':0},{'original_fd9_held':False},
            {'cold_old_owner':False},{'native_pkg_mutation_invoked':True},
            {'status':'RUNNING'},{'sha':'b'*40},
            {'original_fd9_inode':0},
            {'created_original_lock_inode':'TRUE'},
        ):
            with self.subTest(bad=bad),\
                 self.assertRaisesRegex(m.Refusal,
                                        'DETACHED_OLD_FD9_READY_NOT_QUALIFIED'):
                m.inspect_ready(json.dumps(good|bad).encode(),HEAD)

    def test_disposable_result_file_requires_root_only_mode_and_inode(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'result'
            m.create_owned(path,b'TEST_ONLY')
            if path.stat().st_uid==0:
                self.assertEqual(m.trusted(path),b'TEST_ONLY')
            else:
                with self.assertRaisesRegex(m.Refusal,'INODE_UNTRUSTED'):
                    m.trusted(path)
            with self.assertRaises(FileExistsError):
                m.create_owned(path,b'ATTEMPT_OVERWRITE')
            path.chmod(0o644)
            with self.assertRaises(m.Refusal):
                m.trusted(path)
            path.unlink()
            path.symlink_to(Path(d)/'foreign')
            with self.assertRaises(m.Refusal):
                m.trusted(path)

    def test_detached_worker_failure_marker_makes_missing_ready_fail_fast(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            ready=root/'ready'
            failed=root/'failed'
            failed.write_text('ORIGINAL_FD9_BUSY_NO_WORKER_ADMISSION')
            with patch.object(m,'READY',ready),\
                 patch.object(m,'FAILED',failed),\
                 patch.object(m,'trusted',
                              return_value=b'ORIGINAL_FD9_BUSY_NO_WORKER_ADMISSION'):
                with self.assertRaisesRegex(
                        m.Refusal,
                        'DETACHED_WORKER_DID_NOT_REACH_READY:ORIGINAL_FD9_BUSY'):
                    m.wait_file(ready,.5)

    def test_unknown_or_busy_original_fd9_is_not_admitted(self):
        with patch.object(m,'load',return_value=SimpleNamespace(
                LOCK=m.LOCK,CHALLENGER='true')),\
             patch.object(m.subprocess,'run',
                          return_value=SimpleNamespace(returncode=0,
                                                       stdout='',stderr='')):
            with self.assertRaisesRegex(m.Refusal,
                                        'INDEPENDENT_ORIGINAL_FD9_NOT_BUSY'):
                m.check_original_fd9_busy()

    def test_missing_historical_original_fd9_creation_is_exclusive(self):
        source=FILE.read_text()
        self.assertIn("fd=os.open(LOCK,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)",source)
        self.assertIn("except FileExistsError:",source)
        self.assertIn("created_original_lock_inode",source)
        self.assertIn("if not lock_preexisting:",source)
        self.assertIn("CREATED_TEST_ORIGINAL_LOCK_INODE_CHANGED",source)
        self.assertIn("CREATED_TEST_LOCK_STILL_BUSY_NO_UNLINK",source)
        self.assertIn("ORIGINAL_LOCK_INITIAL_ABSENCE_NOT_RESTORED",source)

    def test_native_supervisor_requires_explicit_head_optin_and_real_archive(self):
        with patch.object(m.os,'geteuid',return_value=1001):
            with self.assertRaisesRegex(m.Refusal,
                                        'DISPOSABLE_OPNSENSE_ROOT_CI_REQUIRED'):
                m.qualify(HEAD)
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m.os,'uname',return_value=SimpleNamespace(
                 sysname='FreeBSD',machine='amd64')),\
             patch.dict(m.os.environ,{
                'GITHUB_ACTIONS':'true',
                'ZAPRET2_STAGE3_DETACHED_FD9':'1',
                'ZAPRET2_NATIVE_PROJECT_SHA':HEAD}):
            with self.assertRaisesRegex(m.Refusal,
                                        'EXACT_NATIVE_PROJECT_HEAD_REQUIRED'):
                m.qualify('b'*40)

    def test_source_proves_two_independent_busy_checks_across_real_reload(self):
        s=FILE.read_text()
        idx=s.index('def execute(head):')
        body=s[idx:s.index('def main():')]
        first=body.index('check_original_fd9_busy()')
        reload=body.index("run(['/usr/sbin/service','configd','restart'],45)",first)
        second=body.index('check_original_fd9_busy()',reload)
        self.assertLess(first,reload)
        self.assertLess(reload,second)
        self.assertIn('managed.owner_snapshot(old,guard,OLD)==baseline',body)
        self.assertIn("create_owned(RELEASE,b'RELEASE_TEST_ONLY')",body)
        self.assertIn('ACTION.unlink()',body)
        self.assertIn("'unbroken_configd_to_fd9_handoff_proven':False",body)
        self.assertIn("'lh08_ac11_accepted':False",body)
        self.assertNotIn('pkg add -f',s)
        self.assertNotIn('pkg unlock',s)

    def test_required_existing_native_workflow_has_new_job_and_keeps_old(self):
        workflow=(HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml').read_text()
        for part in ('  delegated-old-hook:','  late-owner-negatives:',
                     '  configd-inprocess-veto:','  configd-detached-fd9:',
                     'scripts/stage3-native-configd-detached-fd9.py',
                     'test-stage3-native-configd-detached-fd9.py -v',
                     'vmactions/opnsense-vm@abaa977e3dbc77a0d1eeed4d82c8d9914b018235',
                     'release: "26.7"'):
            self.assertIn(part,workflow)
        self.assertNotIn('pkg unlock',workflow)


if __name__=='__main__':
    unittest.main()
