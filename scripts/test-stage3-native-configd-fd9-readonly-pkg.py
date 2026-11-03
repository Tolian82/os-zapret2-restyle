#!/usr/bin/env python3
"""Fail-closed configd/SCM_RIGHTS native pkg read-query boundary contracts.

The Linux unit test mocks only the platform-specific pkg syscall; the real
FreeBSD OPNsense CI job must invoke the installed native /usr/sbin/pkg itself.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
FILE=HERE/'stage3-native-configd-fd9-handoff.py'
spec=importlib.util.spec_from_file_location('stage3_readonly_pkg',FILE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SHA='a'*40
FIELDS={'head':SHA,'inode':4123,'nonce':'b'*32,'created':False}


class GenuineReadOnlyPkgContracts(unittest.TestCase):
    def env(self,**changes):
        return patch.dict(os.environ, {
            'ZAPRET2_STAGE3_HANDOFF_FAULT':'',
            'ZAPRET2_STAGE3_HANDOFF_NEGATIVE':'',
            'ZAPRET2_STAGE3_READONLY_PKG':'1',
            'ZAPRET2_STAGE3_READONLY_PKG_CI':'1',
            **changes},clear=False)

    def test_exact_native_query_while_same_fd9_held(self):
        calls=[]
        created=[]
        def record_create(path,content):
            created.append((path,json.loads(content)))
        def record_run(argv,**kwargs):
            calls.append((argv,kwargs))
            return subprocess.CompletedProcess(argv,0,'os-zapret2-restyle|0.6.2_1\n','')
        with self.env(),\
             patch.object(m.os,'fstat',return_value=SimpleNamespace(st_ino=4123)),\
             patch.object(m.base,'cold_owner_held') as held,\
             patch.object(m.base,'create_owned',side_effect=record_create),\
             patch.object(m.subprocess,'run',side_effect=record_run):
            result=m.readonly_pkg_query(SHA,FIELDS)
        self.assertEqual(calls[0][0],['/usr/sbin/pkg','-o','REPO_AUTOUPDATE=false',
                                      'query','%n|%v','os-zapret2-restyle'])
        self.assertEqual(calls[0][1]['timeout'],8)
        self.assertEqual(calls[0][1]['check'],False)
        self.assertEqual(held.call_count,2)
        self.assertEqual(created[0][0],m.QUERY)
        self.assertEqual(result['status'],'NATIVE_PKG_QUERY_UNDER_TRANSFERRED_FD9')
        self.assertEqual(result['original_fd9_inode'],FIELDS['inode'])
        self.assertEqual(result['nonce_sha256'],hashlib.sha256(FIELDS['nonce'].encode()).hexdigest())
        self.assertIs(result['native_mutating_pkg_invoked'],False)

    def test_wrong_installed_package_version_refused(self):
        for stdout in ('os-zapret2-restyle|0.6.2_97\n','other|0.6.2_1\n',''):
            with self.subTest(stdout=stdout),self.env(),\
                 patch.object(m.os,'fstat',return_value=SimpleNamespace(st_ino=4123)),\
                 patch.object(m.base,'cold_owner_held'),\
                 patch.object(m.base,'create_owned') as created,\
                 patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout,'')):
                with self.assertRaisesRegex(m.base.Refusal,'READ_ONLY_PKG_QUERY_NOT_AUTHENTIC_OLD'):
                    m.readonly_pkg_query(SHA,FIELDS)
                created.assert_not_called()

    def test_query_nonzero_refused(self):
        with self.env(),patch.object(m.os,'fstat',return_value=SimpleNamespace(st_ino=4123)),\
             patch.object(m.base,'cold_owner_held'),\
             patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','error')):
            with self.assertRaisesRegex(m.base.Refusal,'READ_ONLY_PKG_QUERY_NOT_AUTHENTIC_OLD'):
                m.readonly_pkg_query(SHA,FIELDS)

    def test_missing_original_fd9_before_query_denies_pkg(self):
        with self.env(),patch.object(m.os,'fstat',return_value=SimpleNamespace(st_ino=999)),\
             patch.object(m.subprocess,'run') as pkg:
            with self.assertRaisesRegex(m.base.Refusal,'READ_ONLY_PKG_LOST_ORIGINAL_FD9_BEFORE_QUERY'):
                m.readonly_pkg_query(SHA,FIELDS)
            pkg.assert_not_called()

    def test_missing_original_fd9_after_query_denies_attestation(self):
        st=[SimpleNamespace(st_ino=4123),SimpleNamespace(st_ino=999)]
        with self.env(),patch.object(m.os,'fstat',side_effect=st),\
             patch.object(m.base,'cold_owner_held'),\
             patch.object(m.base,'create_owned') as created,\
             patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'os-zapret2-restyle|0.6.2_1','')):
            with self.assertRaisesRegex(m.base.Refusal,'READ_ONLY_PKG_LOST_ORIGINAL_FD9_AFTER_QUERY'):
                m.readonly_pkg_query(SHA,FIELDS)
            created.assert_not_called()

    def test_native_query_mode_requires_qualified_explicit_optin(self):
        with self.env(ZAPRET2_STAGE3_READONLY_PKG_CI='0'):
            with self.assertRaisesRegex(m.base.Refusal,'READ_ONLY_PKG_MODE_UNQUALIFIED'):
                m.readonly_query_mode()
        with self.env(ZAPRET2_STAGE3_READONLY_PKG='2'):
            with self.assertRaisesRegex(m.base.Refusal,'READ_ONLY_PKG_MODE_INVALID'):
                m.readonly_query_mode()

    def test_mixing_dead_worker_injection_and_pkg_query_refused(self):
        with self.env(ZAPRET2_STAGE3_HANDOFF_NEGATIVE='1',
                      ZAPRET2_STAGE3_HANDOFF_FAULT='drop_ack'):
            with self.assertRaisesRegex(m.base.Refusal,'READ_ONLY_PKG_MODE_UNQUALIFIED'):
                m.readonly_query_mode()

    def test_fixed_root_action_and_original_mode_unchanged(self):
        with self.env():
            action=m.action_bytes(SHA).decode()
            self.assertIn('ZAPRET2_STAGE3_READONLY_PKG=1',action)
            self.assertIn('ZAPRET2_STAGE3_READONLY_PKG_CI=1',action)
            self.assertNotIn('%s',action)
        with self.env(ZAPRET2_STAGE3_READONLY_PKG=''):
            self.assertNotIn('ZAPRET2_STAGE3_READONLY_PKG=1',m.action_bytes(SHA).decode())
            self.assertFalse(m.readonly_query_mode())

    def test_source_keeps_old_true_scm_rights_and_fail_closed_gate(self):
        text=FILE.read_text()
        self.assertIn('readonly_pkg_query(head,fields)',text)
        self.assertIn('NATIVE_PKG_QUERY_FD9_ATTESTATION_UNQUALIFIED',text)
        self.assertIn('PASS_TEST_ONLY_CONFIGD_SCM_RIGHTS_CONTINUOUS_FD9',text)
        self.assertIn('PASS_TEST_ONLY_CONFIGD_FD9_NATIVE_PKG_READ_ONLY_QUERY',text)
        self.assertIn('native_mutating_pkg_invoked',text)
        self.assertNotIn('pkg add -f',text)
        self.assertNotIn('pkg upgrade',text)

    def test_mandatory_native_job_and_previous_jobs_preserved(self):
        workflow=HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml'
        if not workflow.exists():
            self.skipTest('full project checkout needed for workflow contract')
        body=workflow.read_text()
        for item in ('  configd-detached-fd9:', '  configd-atomic-handoff:',
                     '  configd-atomic-handoff-faults:', '  configd-readonly-pkg:',
                     'test-stage3-native-configd-fd9-readonly-pkg.py -v',
                     'ZAPRET2_STAGE3_READONLY_PKG=1'):
            self.assertIn(item,body)


if __name__=='__main__':
    unittest.main()
