#!/usr/bin/env python3
"""Portable CI-only tests for verified bytes -> pkg stdin without path reopen."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stdin_probe', HERE / 'stage3-native-pkg-stdin-ci.py')
m = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = m
spec.loader.exec_module(m)
FLAGS = {'GITHUB_ACTIONS':'true', 'ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI':'1',
         'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK':'1',
         'ZAPRET2_NATIVE_BUILD_CI':'1',
         'ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI':'1',
         'ZAPRET2_STAGE2_DELEGATED_FD9_HANDOFF':'1'}

class StdinCI(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'os-zapret2-restyle-0.6.2_130.pkg'
        self.payload = b'native one-use sealed-byte fixture' * 11
        self.path.write_bytes(self.payload); self.path.chmod(0o600)
        self.sha = hashlib.sha256(self.payload).hexdigest()
        self.calls = 0
    def fd9(self):
        self.calls += 1
    def freeze(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            return m.freeze_exact_candidate(self.path, self.sha, '130', self.fd9)

    def test_actual_byte_snapshot_identical_and_owned(self):
        value = self.freeze()
        self.assertEqual(value.data, self.payload)
        self.assertEqual(value.sha256, self.sha)
        self.assertEqual(value.inode, self.path.stat().st_ino)
        self.assertEqual(self.calls, 2)

    def test_after_snapshot_path_replacement_cannot_change_stdin_bytes(self):
        value = self.freeze()
        self.path.unlink()
        self.path.write_bytes(b'ATTACKER_REPLACED_FILE')
        class Fake:
            def __init__(self, argv, **kwargs):
                self.argv=argv; self.kwargs=kwargs; self.returncode=0; self.payload=None
            def communicate(self, input=None, timeout=None):
                self.payload=input
                self.__class__.seen=self
                return b'os-zapret2-restyle was installed.', b''
        with patch.dict(os.environ, FLAGS, clear=True):
            rc, out, err=m.install_frozen_stdin(value, {}, self.fd9, popen=Fake)
        self.assertEqual(rc,0)
        self.assertIn('was installed',out)
        self.assertEqual(Fake.seen.payload,self.payload)
        self.assertEqual(Fake.seen.argv[-1],'-')
        self.assertNotIn(str(self.path), Fake.seen.argv)
        self.assertEqual(Fake.seen.kwargs['pass_fds'],(9,))
        self.assertEqual(Fake.seen.kwargs['text'],False)
        self.assertTrue(Fake.seen.kwargs['start_new_session'])

    def test_missing_ci_optin_refuses_before_file_read_or_dispatch(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(m.Refusal,'DISPOSABLE_GATE_REQUIRED'):
                m.freeze_exact_candidate(self.path, self.sha, '130', self.fd9)
        self.assertEqual(self.calls,0)

    def test_wrong_sha_refuses_without_pkg(self):
        with patch.dict(os.environ,FLAGS,clear=True), self.assertRaisesRegex(m.Refusal,'SNAPSHOT_SHA_MISMATCH'):
            m.freeze_exact_candidate(self.path, '0'*64, '130', self.fd9)

    def test_symlink_and_hardlink_denied(self):
        link = self.path.parent/'os-zapret2-restyle-0.6.2_131.pkg'
        link.symlink_to(self.path)
        with patch.dict(os.environ,FLAGS,clear=True), self.assertRaisesRegex(m.Refusal,'OPEN_REFUSED'):
            m.freeze_exact_candidate(link, self.sha,'131',self.fd9)
        link.unlink(); os.link(self.path,link)
        with patch.dict(os.environ,FLAGS,clear=True), self.assertRaisesRegex(m.Refusal,'INODE_UNTRUSTED'):
            m.freeze_exact_candidate(self.path, self.sha,'130',self.fd9)

    def test_wrong_revision_refuses(self):
        with patch.dict(os.environ,FLAGS,clear=True), self.assertRaisesRegex(m.Refusal,'CANDIDATE_IDENTITY_INVALID'):
            m.freeze_exact_candidate(self.path,self.sha,'129',self.fd9)

    def test_changed_snapshot_bytes_cannot_be_dispatched(self):
        value=self.freeze()
        forged=m.VerifiedBytes(data=value.data+b'!', sha256=value.sha256,
                               archive_name=value.archive_name,revision=value.revision,
                               inode=value.inode,dev=value.dev)
        with patch.dict(os.environ,FLAGS,clear=True), self.assertRaisesRegex(m.Refusal,'NOT_EXACTLY_SIGNED'):
            m.install_frozen_stdin(forged, {}, self.fd9)

    def test_stdin_dispatch_requires_mode_optin(self):
        value=self.freeze()
        with patch.dict(os.environ,{},clear=True), self.assertRaisesRegex(m.Refusal,'DISPOSABLE_GATE_REQUIRED'):
            m.install_frozen_stdin(value,{},self.fd9)

    def test_fd9_checker_failure_propagates_before_pkg(self):
        value=self.freeze()
        def veto():raise m.Refusal('FD9_NOT_HELD')
        with patch.dict(os.environ,FLAGS,clear=True), self.assertRaisesRegex(m.Refusal,'FD9_NOT_HELD'):
            m.install_frozen_stdin(value,{},veto)

    def test_archive_is_never_passed_as_pkg_path(self):
        value=self.freeze()
        class Fake:
            def __init__(self, argv, **kwargs):
                self.args=argv; self.returncode=4
                self.__class__.argv=argv
            def communicate(self, input=None, timeout=None):
                self.__class__.payload=input
                return b'', b'missing real OPNsense dependency'
        with patch.dict(os.environ,FLAGS,clear=True):
            rc,out,err=m.install_frozen_stdin(value,{},self.fd9,popen=Fake)
        self.assertEqual(rc,4)
        self.assertIn('missing',err)
        self.assertEqual(Fake.argv,['/usr/sbin/pkg','-o','REPO_AUTOUPDATE=false','add','-f','-'])
        self.assertEqual(Fake.payload,self.payload)

if __name__=='__main__':unittest.main()
