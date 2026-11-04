#!/usr/bin/env python3
"""Offline fail-closed proof of atomic pathname rebind and safe restoration."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stdin_path_swap_ci', HERE / 'stage3-native-stdin-path-swap-ci.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
FLAGS = {'GITHUB_ACTIONS': 'true', 'ZAPRET2_STAGE3_NATIVE_STDIN_PKG': '1',
         'ZAPRET2_STAGE3_NATIVE_STDIN_PKG_CI': '1',
         'ZAPRET2_STAGE3_NATIVE_STDIN_PATH_SWAP_CI': '1',
         'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK': '1',
         'ZAPRET2_NATIVE_BUILD_CI': '1'}


class RealPathRebindFixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'os-zapret2-restyle-0.6.2_131.pkg'
        self.payload = (b'official-Mk-simulated-archive-' * 32) + b'end'
        self.sha = hashlib.sha256(self.payload).hexdigest()
        self.path.write_bytes(self.payload)
        self.path.chmod(0o600)
        self.inode = self.path.stat().st_ino

    def attack(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            return m.atomic_rebind(self.path, self.sha, '131')

    def restore(self, report):
        with patch.dict(os.environ, FLAGS, clear=True):
            return m.restore_original_after_verified_pkg(report)

    def test_rebind_is_true_inode_swap_not_in_place_byte_tamper(self):
        result = self.attack()
        self.assertEqual(result['status'], 'CI_STDIN_PATH_REBOUND_TO_DIFFERENT_INODE')
        self.assertEqual(result['original_sha256'], self.sha)
        self.assertEqual(result['original_inode'], self.inode)
        self.assertNotEqual(result['replacement_inode'], self.inode)
        self.assertEqual(self.path.stat().st_ino, result['replacement_inode'])
        self.assertNotEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), self.sha)
        self.assertEqual(result['backup'].read_bytes(), self.payload)
        self.assertFalse(result['original_fd9_touched'])
        self.assertFalse(result['native_pkg_invoked'])

    def test_byte_snapshot_unaffected_and_original_path_restored(self):
        frozen = bytes(self.path.read_bytes())
        result = self.attack()
        self.assertEqual(hashlib.sha256(frozen).hexdigest(), self.sha)
        self.assertNotEqual(self.path.read_bytes(), frozen)
        self.assertTrue(self.restore(result)['status'].endswith('_RESTORED'))
        self.assertEqual(self.path.read_bytes(), frozen)
        self.assertEqual(self.path.stat().st_ino, self.inode)
        self.assertFalse(result['backup'].exists())

    def test_attack_bytes_are_one_byte_different_same_length(self):
        result = self.attack()
        altered = self.path.read_bytes()
        self.assertEqual(len(altered), len(self.payload))
        self.assertNotEqual(altered[0], self.payload[0])
        self.assertEqual(altered[1:], self.payload[1:])
        self.assertTrue(m.sha_bytes(altered) == result['replacement_sha256'])

    def test_disposable_flag_missing_fails_without_touching_file(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'DISPOSABLE_OPTIN_REQUIRED'):
                m.atomic_rebind(self.path, self.sha, '131')
        self.assertEqual(self.path.stat().st_ino, self.inode)
        self.assertEqual(self.path.read_bytes(), self.payload)

    def test_wrong_digest_rejected_before_replacement(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'OLD_SOURCE_MISMATCH'):
                m.atomic_rebind(self.path, '0' * 64, '131')
        self.assertEqual(self.path.read_bytes(), self.payload)

    def test_wrong_revision_rejected(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'CANDIDATE_IDENTITY_INVALID'):
                m.atomic_rebind(self.path, self.sha, '130')

    def test_symlink_source_rejected(self):
        symlink = self.path.with_name('os-zapret2-restyle-0.6.2_132.pkg')
        symlink.symlink_to(self.path)
        with patch.dict(os.environ, FLAGS, clear=True), self.assertRaises(OSError):
            m.atomic_rebind(symlink, self.sha, '132')
        self.assertEqual(self.path.read_bytes(), self.payload)

    def test_hardlink_source_rejected(self):
        other = self.path.with_name('existing-second-link')
        os.link(self.path, other)
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'ORIGINAL_NOT_EXCLUSIVE'):
                m.atomic_rebind(self.path, self.sha, '131')

    def test_world_writable_source_refused(self):
        self.path.chmod(0o666)
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'ORIGINAL_NOT_EXCLUSIVE'):
                m.atomic_rebind(self.path, self.sha, '131')

    def test_restore_requires_exact_attacker_inode_and_digest(self):
        report = self.attack()
        self.path.write_bytes(b'FOREIGN CHANGED AGAIN')
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'ACTIVE_IDENTITY_CHANGED'):
                m.restore_original_after_verified_pkg(report)
        self.assertTrue(report['backup'].exists())

    def test_restore_cannot_accept_forged_backup(self):
        report = self.attack()
        report['backup'].write_bytes(b'BAD BACKUP')
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'ACTIVE_IDENTITY_CHANGED'):
                m.restore_original_after_verified_pkg(report)
        self.assertEqual(self.path.stat().st_ino, report['replacement_inode'])

    def test_replay_restore_is_rejected(self):
        report = self.attack()
        self.restore(report)
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaises((m.Refusal, FileNotFoundError)):
                m.restore_original_after_verified_pkg(report)

    def test_forged_report_without_status_is_rejected(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(m.Refusal, 'REPORT_INVALID'):
                m.restore_original_after_verified_pkg({'status': 'PASS'})

    def test_no_pkg_invocation_in_fixture(self):
        s = (HERE / 'stage3-native-stdin-path-swap-ci.py').read_text()
        for word in ('subprocess.', 'os.system(', 'os.exec', 'pkg add', 'pkg -o'):
            self.assertNotIn(word, s)


if __name__ == '__main__':
    unittest.main()
