#!/usr/bin/env python3
"""Offline fail-closed contracts for installed inspect-only managed CLI."""
import array
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
PRODUCT=HERE.parent/'src/opnsense/scripts/OPNsense/Zapret/backend'
import sys
sys.path.insert(0,str(PRODUCT))
SRC=PRODUCT/'native_pkg_managed.py'
spec=importlib.util.spec_from_file_location('native_pkg_managed',SRC)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ManagedCLIContracts(unittest.TestCase):
    def test_upgrade_and_unknown_commands_refuse_before_pkg(self):
        with patch.object(m,'inspect_independent') as inspect, patch.object(m.subprocess,'Popen') as popen:
            for args in ([], ['upgrade'],['upgrade','/tmp/x','0.6.2_103','a'*64],
                         ['inspect-candidate'], ['--worker'], ['--help']):
                with self.subTest(args=args):
                    self.assertEqual(m.main(args),78)
            inspect.assert_not_called()
            popen.assert_not_called()

    def test_only_inspect_command_can_reach_supervisor(self):
        verdict={'status':'PASS_MANAGED_READ_ONLY_INSPECTION'}
        with patch.object(m,'inspect_independent',return_value=verdict) as inspect:
            self.assertEqual(m.main(['inspect-candidate','/tmp/candidate.pkg',
                                     '0.6.2_103','a'*64]),0)
            inspect.assert_called_once()

    def test_predecessor_readonly_command_is_distinct_from_updater(self):
        with patch.object(m,'inspect_independent',return_value={'status':'PASS_MANAGED_READ_ONLY_PREDECESSOR_SCREEN'}) as inspect:
            self.assertEqual(m.main(['inspect-predecessor','/tmp/old.pkg','0.6.2_1','a'*64]),0)
            inspect.assert_called_once_with(Path('/tmp/old.pkg'),'0.6.2_1','a'*64,mode='predecessor')
        with patch.object(m,'inspect_independent') as inspect:
            self.assertEqual(m.main(['inspect-predecessor','/tmp/old.pkg']),78)
            inspect.assert_not_called()

    def test_old_owner_negative_worker_attestation_is_not_success(self):
        pid, head, nonce, inode, sha=244, 'a'*40, 'b'*32, 77, 'c'*64
        refusal={'status':'REFUSED_MANAGED_OLD_OWNER','worker_pid':pid,
                 'session_head':head,
                 'nonce_sha256':hashlib.sha256(nonce.encode()).hexdigest(),
                 'original_fd9_inode':inode, 'archive_sha256':sha,
                 'pkg_invoked':False,'old_owner_qualified':False,
                 'lh08_ac11_accepted':False,
                 'reason':'OLD_KERNEL_IPFW_OR_IPDIVERT_NOT_PROVEN_COLD'}
        self.assertTrue(m._attested_old_refusal(refusal,pid,head,nonce,inode,sha))
        for changed in ({'pkg_invoked':True},{'old_owner_qualified':True},
                        {'lh08_ac11_accepted':True},{'session_head':'x'*40},
                        {'nonce_sha256':'0'*64},{'worker_pid':999},
                        {'reason':''},{'reason':'X'*241},
                        {'status':'PASS_MANAGED_READ_ONLY_INSPECTION'}):
            with self.subTest(changed=changed):
                self.assertFalse(m._attested_old_refusal(
                    dict(refusal,**changed),pid,head,nonce,inode,sha))

    def test_nonroot_refused_before_historical_lock_creation(self):
        with patch.object(m.os,'geteuid',return_value=1000),patch.object(m.os,'open') as op:
            with self.assertRaisesRegex(m.ManagedRefusal,'ROOT_FREEBSD_MANAGED_INSPECTION_ONLY'):
                m.original_lock_fd()
            op.assert_not_called()

    def test_bad_target_refused_before_lock_creation(self):
        with patch.object(m.os,'geteuid',return_value=0),patch.object(m.os,'uname',
                         return_value=SimpleNamespace(sysname='Linux',machine='amd64')):
            with self.assertRaisesRegex(m.ManagedRefusal,'ROOT_FREEBSD_MANAGED_INSPECTION_ONLY'):
                m.original_lock_fd()

    def test_live_original_fd9_exclusive_and_busy_negative(self):
        with tempfile.TemporaryDirectory() as d:
            lock=Path(d)/'historical.lock'
            root_stat=os.fstat
            path_lstat=Path.lstat
            def adjusted(st):
                a=list(st);a[4]=0
                return os.stat_result(a)
            def fake_lstat(path,*args,**kwargs):
                st=path_lstat(path,*args,**kwargs)
                return adjusted(st) if path==lock else st
            with patch.object(m,'LOCK',lock),patch.object(m.transport,'LOCK',lock),\
                 patch.object(m.os,'geteuid',return_value=0),\
                 patch.object(m.os,'uname',return_value=SimpleNamespace(sysname='FreeBSD',machine='amd64')),\
                 patch.object(m.os,'fstat',side_effect=lambda fd:adjusted(root_stat(fd))),\
                 patch.object(Path,'lstat',fake_lstat),\
                 patch.object(m.transport,'verify_original_lock') as verify:
                fd,created,inode=m.original_lock_fd()
                try:
                    self.assertTrue(created)
                    self.assertGreater(inode,0)
                    with self.assertRaisesRegex(m.ManagedRefusal,'ORIGINAL_FD9_BUSY_BEFORE_INSPECTION'):
                        m.original_lock_fd()
                finally:
                    os.close(fd)
                fd2,created2,inode2=m.original_lock_fd()
                self.assertFalse(created2)
                self.assertEqual(inode2,inode)
                os.close(fd2)
                self.assertEqual(verify.call_count,2)

    def test_symlink_original_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            target=root/'target';target.touch()
            link=root/'historical.lock';link.symlink_to(target)
            with patch.object(m,'LOCK',link),patch.object(m.transport,'LOCK',link),\
                 patch.object(m.os,'geteuid',return_value=0),\
                 patch.object(m.os,'uname',return_value=SimpleNamespace(sysname='FreeBSD',machine='amd64')):
                with self.assertRaisesRegex(m.ManagedRefusal,'HISTORICAL_LOCK_PATH_UNTRUSTED'):
                    m.original_lock_fd()

    def test_wrong_candidate_identity_never_spawns_worker(self):
        with patch.object(m.candidate,'identity',side_effect=m.candidate.CandidateRefusal('bad')),\
             patch.object(m,'original_lock_fd') as lock,\
             patch.object(m.subprocess,'Popen') as spawn:
            with self.assertRaises(m.candidate.CandidateRefusal):
                m.inspect_independent(Path('/tmp/x.pkg'),'0.6.2_103','a'*64)
            lock.assert_not_called()
            spawn.assert_not_called()

    def test_worker_result_parser_rejects_non_json_and_oversize(self):
        left,right=socket.socketpair()
        try:
            right.sendall(b'garbage')
            right.shutdown(socket.SHUT_WR)
            with self.assertRaisesRegex(m.ManagedRefusal,'NOT_JSON'):
                m._read_response(left)
        finally:
            left.close();right.close()
        left,right=socket.socketpair()
        try:
            right.sendall(b'X'*(m.MAX_MESSAGE+20))
            right.shutdown(socket.SHUT_WR)
            with self.assertRaisesRegex(m.ManagedRefusal,'OVERSIZE'):
                m._read_response(left)
        finally:
            left.close();right.close()

    def test_detached_worker_protocol_passes_only_socket_and_verified_fd9(self):
        with tempfile.TemporaryDirectory() as d:
            archive=Path(d)/'os-zapret2-restyle-0.6.2_103.pkg'
            archive.write_bytes(b'candidate fixture')
            sha=hashlib.sha256(archive.read_bytes()).hexdigest()
            lock=Path(d)/'lock'
            lock.touch()
            fd=os.open(lock,os.O_RDONLY)
            nonce='b'*32;head='a'*40
            thread=[]
            class FakeProcess:
                pid=987654
                def poll(self):return 0
                def wait(self, timeout=None):return 0
                def kill(self):raise AssertionError('unexpected kill')
            def fake_spawn(command,**kw):
                self.assertEqual(command[:3],[m.sys.executable,'-B',str(SRC)])
                self.assertEqual(command[3],'--worker')
                self.assertEqual(kw['pass_fds'],(int(command[4]),))
                self.assertTrue(kw['start_new_session'])
                socket_copy=os.dup(int(command[4]))
                def child():
                    with socket.socket(fileno=socket_copy) as conn:
                        data,anc,flags,_=conn.recvmsg(1024,socket.CMSG_SPACE(16))
                        fields=json.loads(data)
                        self.assertEqual((fields['head'],fields['nonce']),(head,nonce))
                        self.assertEqual(fields['inode'],os.fstat(fd).st_ino)
                        fds=[]
                        for level,typ,raw in anc:
                            if level==socket.SOL_SOCKET and typ==socket.SCM_RIGHTS:
                                a=array.array('i');a.frombytes(raw[:len(raw)//4*4]);fds.extend(a)
                        self.assertEqual(len(fds),1)
                        for received in fds:os.close(received)
                        answer={'status':'PASS_MANAGED_READ_ONLY_INSPECTION',
                                'worker_pid':FakeProcess.pid,'session_head':head,
                                'nonce_sha256':hashlib.sha256(nonce.encode()).hexdigest(),
                                'original_fd9_inode':fields['inode'],
                                'archive_sha256':sha,'pkg_invoked':False,
                                'old_owner_qualified':False,'lh08_ac11_accepted':False}
                        conn.sendall(json.dumps(answer).encode())
                t=threading.Thread(target=child)
                thread.append(t);t.start()
                return FakeProcess()
            try:
                with patch.object(m,'_product_script_identity',return_value=(SRC,'f'*64)),\
                     patch.object(m,'original_lock_fd',return_value=(fd,False,os.fstat(fd).st_ino)),\
                     patch.object(m.transport,'verify_original_lock') as guard,\
                     patch.object(m.subprocess,'Popen',side_effect=fake_spawn),\
                     patch.object(m.secrets,'token_hex',side_effect=[head,nonce]):
                    answer=m.inspect_independent(archive,'0.6.2_103',sha)
                    self.assertEqual(answer['status'],'PASS_MANAGED_READ_ONLY_INSPECTION')
                    guard.assert_called_once()
            finally:
                for t in thread:t.join(timeout=2)
                # m.inspect_independent always closes the transferred original FD.

    def test_no_package_mutation_dispatch_is_reachable(self):
        source=SRC.read_text()
        for forbidden in ('"pkg", "add"',"\'pkg\', \'add\'",'pkg upgrade','pkg install',
                          'pkg delete','os.system(', 'os.execvp(', 'os.rename('):
            self.assertNotIn(forbidden,source)
        self.assertIn("UPGRADE_NOT_IMPLEMENTED_NO_PKG",source)
        self.assertIn("'pkg_invoked': False",source)
        self.assertIn('transport.receive_original_fd9(',source)
        self.assertIn('candidate.inspect_with_original_fd9(',source)

if __name__=='__main__':
    unittest.main()
