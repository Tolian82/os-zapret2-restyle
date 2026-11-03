#!/usr/bin/env python3
"""Fail-closed tests for the installed shared original-FD9 transport."""
import array
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
import fcntl

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'src/opnsense/scripts/OPNsense/Zapret/backend/native_pkg_handoff.py'
spec=importlib.util.spec_from_file_location('native_pkg_handoff', SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
HEAD='a'*40
NONCE='b'*32

class Transport(unittest.TestCase):
    def test_exact_envelope(self):
        expected={'head':HEAD,'nonce':NONCE,'created':False,'inode':32}
        self.assertEqual(m.validate_envelope(expected,HEAD,NONCE),expected)
        for wrong in ({**expected,'inode':True},{**expected,'created':1},
                      {**expected,'nonce':'x'*32},{**expected,'extra':1},
                      {**expected,'inode':0}):
            with self.subTest(wrong=wrong),self.assertRaises(m.HandoffRefusal):
                m.validate_envelope(wrong,HEAD,NONCE)

    def transport(self, *, lock=True, data=None, send_fd=True):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'original.lock'
            p.touch(mode=0o600)
            fd=os.open(p,os.O_RDWR|os.O_NOFOLLOW)
            if lock:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
            try:
                raw=data or {'head':HEAD,'nonce':NONCE,'created':False,
                             'inode':os.fstat(fd).st_ino}
                ancillary=[(socket.SOL_SOCKET,socket.SCM_RIGHTS,
                            array.array('i',[fd]))] if send_fd else []
                a.sendmsg([json.dumps(raw).encode()],ancillary)
                real_fstat=os.fstat
                real_lstat=Path.lstat
                def root_stat(st):
                    values=list(st)
                    values[4]=0  # st_uid only; preserve real inode/mode/link count
                    return os.stat_result(values)
                def root_fstat(value):
                    return root_stat(real_fstat(value))
                def root_lstat(path,*args,**kwargs):
                    st=real_lstat(path,*args,**kwargs)
                    return root_stat(st) if path == p else st
                with patch.object(m,'LOCK',p),patch.object(m.os,'geteuid',return_value=0),\
                        patch.object(m.os,'fstat',side_effect=root_fstat) as check,\
                        patch.object(Path,'lstat',root_lstat):
                    if lock and send_fd and data is None:
                        received,fields=m.receive_original_fd9(b,head=HEAD,nonce=NONCE)
                        try:
                            self.assertEqual(fields['inode'],os.fstat(fd).st_ino)
                            self.assertTrue(check.called)
                        finally:
                            os.close(received)
                    else:
                        with self.assertRaises(m.HandoffRefusal):
                            m.receive_original_fd9(b,head=HEAD,nonce=NONCE)
            finally:
                a.close()
                b.close()
                os.close(fd)

    def test_transferred_original_lock(self):
        self.transport()

    def test_unlocked_fd_refused(self):
        self.transport(lock=False)

    def test_missing_rights_refused(self):
        self.transport(send_fd=False)

    def test_other_inode_refused(self):
        self.transport(data={'head':HEAD,'nonce':NONCE,'created':False,'inode':55})

    def test_nonroot_receiver_refused(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            with patch.object(m.os,'geteuid',return_value=1000),self.assertRaisesRegex(
                    m.HandoffRefusal,'ROOT_HANDOFF_REQUIRED'):
                m.receive_original_fd9(b,head=HEAD,nonce=NONCE)
        finally:
            a.close()
            b.close()

    def test_symlink_lock_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            real=Path(tmp)/'real'
            real.touch()
            symlink=Path(tmp)/'link'
            symlink.symlink_to(real)
            fd=os.open(real,os.O_RDONLY)
            try:
                with patch.object(m,'LOCK',symlink),patch.object(m.os,'geteuid',return_value=0),self.assertRaisesRegex(
                        m.HandoffRefusal,'ORIGINAL_LOCK_PATH_UNTRUSTED'):
                    m.verify_original_lock(fd,real.stat().st_ino)
            finally:
                os.close(fd)

    def test_no_mutating_package_operations_in_transport(self):
        text=SOURCE.read_text()
        for forbidden in ('import subprocess', 'subprocess.run(', 'pkg add', 'pkg install', 'pkg delete',
                          'unlink(', 'os.system(', 'os.exec', 'os.kill('):
            self.assertNotIn(forbidden,text)

if __name__=='__main__':
    unittest.main()
