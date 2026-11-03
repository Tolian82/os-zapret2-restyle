#!/usr/bin/env python3
"""Fail-closed, no-pkg original FD9 SCM_RIGHTS handoff contracts."""
import array
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
FILE=HERE/'stage3-native-configd-fd9-handoff.py'
s=importlib.util.spec_from_file_location('stage3_atomic_fd9',FILE)
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)
HEAD='a'*40
NONCE='b'*32


class HandoffContracts(unittest.TestCase):
    def test_fixed_configd_action_does_not_accept_arguments_or_pkg(self):
        src=m.action_bytes(HEAD).decode()
        self.assertIn('--launch '+HEAD,src)
        self.assertIn('ZAPRET2_STAGE3_ATOMIC_HANDOFF=1',src)
        self.assertIn('type:script_output',src)
        self.assertNotIn('%s',src)
        self.assertNotIn('pkg add',src)
        self.assertNotIn('pkg upgrade',src)

    def test_not_admitted_without_disposable_explicit_optin(self):
        with patch.object(m.base,'qualify'),patch.dict(os.environ,
                {'ZAPRET2_STAGE3_ATOMIC_HANDOFF':'0'}):
            with self.assertRaisesRegex(m.base.Refusal,
                                        'ONE_USE_ATOMIC_HANDOFF_OPTIN_REQUIRED'):
                m.qualify(HEAD)

    def test_socket_receiver_requires_exact_one_original_fd9(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'original.lock'
            path.write_text('test')
            fd=os.open(path,os.O_RDWR)
            try:
                old9=os.dup(9)
            except OSError:
                old9=None
            a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
            try:
                original_fstat=os.fstat
                def root_owned_fstat(value):
                    st=original_fstat(value)
                    return SimpleNamespace(st_uid=0,st_nlink=st.st_nlink,
                                           st_mode=st.st_mode,st_dev=st.st_dev,
                                           st_ino=st.st_ino)
                # The Linux offline runner is not root; simulate only uid
                # while preserving the real SCM_RIGHTS descriptor/inode.
                with patch.object(m,'ticket',return_value=NONCE),\
                     patch.object(m.base,'LOCK',path),\
                     patch.object(m.base,'cold_owner_held'),\
                     patch.object(m.os,'fstat',side_effect=root_owned_fstat):
                    msg=json.dumps({'head':HEAD,'nonce':NONCE,
                                    'created':False,'inode':path.stat().st_ino}).encode()
                    a.sendmsg([msg],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,
                                       array.array('i',[fd]))])
                    result=m.accept_rights(b,HEAD)
                    self.assertEqual(result['inode'],os.fstat(9).st_ino)
                    self.assertEqual(os.fstat(9).st_ino,path.stat().st_ino)
            finally:
                a.close(); b.close(); os.close(fd)
                if old9 is None:
                    try: os.close(9)
                    except OSError: pass
                else:
                    os.dup2(old9,9);os.close(old9)

    def test_missing_rights_must_fail_before_any_worker_admission(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            a.sendall(json.dumps({'head':HEAD,'nonce':NONCE,
                                  'created':False,'inode':44}).encode())
            with self.assertRaisesRegex(m.base.Refusal,
                                        'MISSING_OR_EXTRA_FD9_RIGHTS'):
                m.accept_rights(b,HEAD)
        finally:
            a.close(); b.close()

    def test_wrong_nonce_refused_despite_attached_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'original.lock'
            path.write_text('t')
            fd=os.open(path,os.O_RDWR)
            a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
            try:
                msg=json.dumps({'head':HEAD,'nonce':'c'*32,
                                'created':False,'inode':path.stat().st_ino}).encode()
                a.sendmsg([msg],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,
                                   array.array('i',[fd]))])
                with patch.object(m,'ticket',return_value=NONCE):
                    with self.assertRaisesRegex(m.base.Refusal,
                                                'TRANSFER_TICKET_OR_OWNER_UNTRUSTED'):
                        m.accept_rights(b,HEAD)
            finally:
                a.close();b.close();os.close(fd)

    def test_invalid_ready_nonce_and_pid_fail_closed(self):
        good={'status':'HANDOFF_WORKER_HOLDS_ORIGINAL_FD9',
              'sha':HEAD,'native_pkg_mutation_invoked':False,
              'pid':32,'original_fd9_inode':123,
              'created_original_lock_inode':True,
              'nonce_sha256':m.hashlib.sha256(NONCE.encode()).hexdigest()}
        with tempfile.TemporaryDirectory() as tmp:
            ready=Path(tmp)/'ready'
            with patch.object(m,'READY',ready),\
                 patch.object(m,'FAILED',Path(tmp)/'failed'),\
                 patch.object(m.base,'trusted',side_effect=lambda p,*_:p.read_bytes()):
                ready.write_text(json.dumps(good))
                self.assertEqual(m.wait_ready(HEAD,NONCE),good)
                for item in ({'nonce_sha256':'x'}, {'pid':0},
                             {'native_pkg_mutation_invoked':True}, {'sha':'f'*40},
                             {'created_original_lock_inode':'true'}):
                    ready.write_text(json.dumps(good|item))
                    with self.subTest(item=item),\
                         self.assertRaisesRegex(m.base.Refusal,
                                                'FD9_HANDOFF_READY_UNQUALIFIED'):
                        m.wait_ready(HEAD,NONCE)

    def test_source_requires_pre_transfer_lock_and_post_transfer_busy_checks(self):
        source=FILE.read_text()
        a=source.index('def launch(head):')
        b=source.index('def wait_ready(',a)
        block=source[a:b]
        self.assertLess(block.index('open_original_fd9()'),block.index('sendmsg('))
        self.assertLess(block.index('sendmsg('),block.index('ack=conn.recv('))
        self.assertLess(block.index('ack=conn.recv('),block.index('os.close(9)'))
        self.assertIn('base.check_original_fd9_busy()',block)
        self.assertIn('base.cold_owner_held()',source)
        self.assertIn('native_mutating_pkg_invoked\':False',source)
        self.assertIn('lh08_ac11_accepted\':False',source)
        self.assertNotIn('pkg add -f',source)

    def test_native_workflow_retains_all_prior_regressions(self):
        p=HERE.parent/'.github/workflows/stage2-native-delegated-fd9-handoff.yml'
        if not p.exists():
            self.skipTest('workflow not available in local isolated unit directory')
        s=p.read_text()
        for k in ('  delegated-old-hook:', '  late-owner-negatives:',
                  '  configd-inprocess-veto:', '  configd-detached-fd9:',
                  '  configd-atomic-handoff:',
                  'scripts/stage3-native-configd-fd9-handoff.py',
                  'test-stage3-native-configd-fd9-handoff.py -v'):
            self.assertIn(k,s)


if __name__=='__main__':
    unittest.main()
