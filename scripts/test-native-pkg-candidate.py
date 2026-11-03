#!/usr/bin/env python3
"""Pure fail-closed tests for the packaged read-only native archive contract."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch
import sys

HERE=Path(__file__).resolve().parent
PRODUCT=HERE.parent/'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0,str(PRODUCT))
spec=importlib.util.spec_from_file_location('native_pkg_candidate',PRODUCT/'native_pkg_candidate.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
VERSION='0.6.2_102'


class CandidateTests(unittest.TestCase):
    def build(self, folder, data=b'authentic fixture bytes'):
        path=folder/f'os-zapret2-restyle-{VERSION}.pkg'
        path.write_bytes(data)
        return path,hashlib.sha256(data).hexdigest()

    def inspect(self, path, sha, version=VERSION):
        # GitHub's Ubuntu runner is not root; mock ONLY st_uid, retaining
        # actual file bytes, modes, inode, links and revalidation.
        orig_fstat=os.fstat
        orig_lstat=Path.lstat
        def root_stat(st):
            fields=list(st)
            fields[4]=0
            return os.stat_result(fields)
        def fake_lstat(p,*args,**kwargs):
            return root_stat(orig_lstat(p,*args,**kwargs))
        with patch.object(m.os,'geteuid',return_value=0),\
             patch.object(m.os,'fstat',side_effect=lambda fd:root_stat(orig_fstat(fd))),\
             patch.object(Path,'lstat',fake_lstat):
            return m.inspect_archive(path,version,sha)

    def test_positive_exact_opened_inode_digest(self):
        with tempfile.TemporaryDirectory() as d:
            path,sha=self.build(Path(d))
            evidence=self.inspect(path,sha)
            self.assertEqual(evidence['sha256'],sha)
            self.assertEqual(evidence['inode'],path.stat().st_ino)
            self.assertFalse(evidence['lh08_ac11_accepted'])

    def test_reject_wrong_version_sha_and_request_type(self):
        with tempfile.TemporaryDirectory() as d:
            path,sha=self.build(Path(d))
            for ver,digest in [('0.6.2_103',sha),(VERSION,'0'*64),
                               ('../102',sha),('0.6.2_0',sha),
                               (VERSION,'x'*64)]:
                with self.subTest(ver=ver,digest=digest),self.assertRaises(m.CandidateRefusal):
                    self.inspect(path,digest,ver)
            with self.assertRaisesRegex(m.CandidateRefusal,'PACKAGE_REQUEST_IDENTITY_INVALID'):
                self.inspect(Path('relative.pkg'),sha)

    def test_reject_symlink_and_hardlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            target=root/'target'
            target.write_bytes(b'authentic fixture bytes')
            path=root/f'os-zapret2-restyle-{VERSION}.pkg'
            path.symlink_to(target)
            with self.assertRaisesRegex(m.CandidateRefusal,'ARCHIVE_UNQUALIFIED'):
                self.inspect(path,hashlib.sha256(target.read_bytes()).hexdigest())
            path.unlink()
            os.link(target,path)
            with self.assertRaisesRegex(m.CandidateRefusal,'ARCHIVE_UNQUALIFIED'):
                self.inspect(path,hashlib.sha256(target.read_bytes()).hexdigest())

    def test_reject_world_writable_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            path,sha=self.build(Path(d))
            path.chmod(0o666)
            with self.assertRaisesRegex(m.CandidateRefusal,'ARCHIVE_UNQUALIFIED'):
                self.inspect(path,sha)

    def test_reject_nonroot(self):
        with tempfile.TemporaryDirectory() as d:
            path,sha=self.build(Path(d))
            with patch.object(m.os,'geteuid',return_value=1000),self.assertRaisesRegex(
                    m.CandidateRefusal,'ROOT_PACKAGE_REQUEST_REQUIRED'):
                m.inspect_archive(path,VERSION,sha)

    def test_reject_missing_or_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path,sha=self.build(Path(d),b'')
            with self.assertRaisesRegex(m.CandidateRefusal,'ARCHIVE_UNQUALIFIED'):
                self.inspect(path,sha)
            path.unlink()
            with self.assertRaisesRegex(m.CandidateRefusal,'ARCHIVE_UNQUALIFIED'):
                self.inspect(path,sha)

    def test_original_fd9_required_for_attested_inspect(self):
        with patch.object(m.native_pkg_handoff,'verify_original_lock',side_effect=
                          m.native_pkg_handoff.HandoffRefusal('bad')) as fd9,\
             self.assertRaisesRegex(m.CandidateRefusal,'ORIGINAL_FD9_UNQUALIFIED'):
            m.inspect_with_original_fd9(Path('/tmp/no-such.pkg'),VERSION,'a'*64,1)
        fd9.assert_called_once_with(9,1)
        with self.assertRaisesRegex(m.CandidateRefusal,'ORIGINAL_FD9_REQUEST_INODE_INVALID'):
            m.inspect_with_original_fd9(Path('/tmp/no-such.pkg'),VERSION,'a'*64,True)

    def test_refuse_changed_lock_after_archive_check(self):
        with patch.object(m.native_pkg_handoff,'verify_original_lock',side_effect=
                          [None,m.native_pkg_handoff.HandoffRefusal('changed')]) as fd9,\
             patch.object(m,'inspect_archive',return_value={'sha256':'a'*64}),\
             self.assertRaisesRegex(m.CandidateRefusal,'ORIGINAL_FD9_CHANGED'):
            m.inspect_with_original_fd9(Path('/tmp/absent'),VERSION,'a'*64,12)
        self.assertEqual(fd9.call_count,2)

    def test_transport_contains_no_pkg_dispatch(self):
        src=(PRODUCT/'native_pkg_candidate.py').read_text()
        for forbidden in ('import subprocess', 'pkg add', 'pkg upgrade', 'os.system(',
                          'os.kill(', 'os.unlink(', 'os.rename(', 'os.exec'):
            self.assertNotIn(forbidden,src)


if __name__=='__main__':
    unittest.main()
