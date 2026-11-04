#!/usr/bin/env python3
"""Isolated, actually executable portable contracts for CI native archive drift."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('late_archive_fixture', HERE / 'stage3-native-late-archive-corruption-ci.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

FLAGS = {'GITHUB_ACTIONS': 'true',
         'ZAPRET2_STAGE3_NATIVE_LATE_ARCHIVE_TAMPER_CI': '1',
         'ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK': '1',
         'ZAPRET2_NATIVE_BUILD_CI': '1'}


class LateNativeArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'os-zapret2-restyle-0.6.2_128.pkg'
        self.payload = b'CI-only-authentic-archive-mock-128' * 3
        self.path.write_bytes(self.payload)
        self.path.chmod(0o600)
        self.sha = hashlib.sha256(self.payload).hexdigest()

    def test_valid_signed_bytes_then_single_byte_corruption(self):
        before = self.path.stat()
        with patch.dict(os.environ, FLAGS, clear=True):
            result = fixture.corrupt_native_archive(self.path, self.sha, '128')
        after = self.path.stat()
        self.assertEqual(result['status'], 'CI_LATE_ARCHIVE_CORRUPTED_BEFORE_FINAL_GRANT')
        self.assertEqual(result['expected_sha256'], self.sha)
        self.assertEqual(result['modified_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual((before.st_ino, before.st_size, before.st_mode),
                         (after.st_ino, after.st_size, after.st_mode))
        self.assertEqual(self.path.read_bytes()[1:], self.payload[1:])
        self.assertEqual(self.path.read_bytes()[0], self.payload[0] ^ 1)
        self.assertFalse(result['native_pkg_invoked'])
        self.assertFalse(result['original_fd9_touched'])

    def test_disposable_guard_denies_before_writes(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(fixture.Refusal, 'CI_LATE_ARCHIVE_TAMPER_NOT_DISPOSABLE'):
                fixture.corrupt_native_archive(self.path, self.sha, '128')
        self.assertEqual(self.path.read_bytes(), self.payload)

    def test_incorrect_digest_denies_before_writes(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(fixture.Refusal, 'CI_LATE_ARCHIVE_ALREADY_DIFFERENT'):
                fixture.corrupt_native_archive(self.path, 'f'*64, '128')
        self.assertEqual(self.path.read_bytes(), self.payload)

    def test_symlink_and_hardlink_denied_without_target_damage(self):
        link = self.path.parent / 'os-zapret2-restyle-0.6.2_129.pkg'
        link.symlink_to(self.path)
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(fixture.Refusal, 'CI_LATE_ARCHIVE_OPEN_REFUSED'):
                fixture.corrupt_native_archive(link, self.sha, '129')
        link.unlink()
        os.link(self.path, link)
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(fixture.Refusal, 'CI_LATE_ARCHIVE_NOT_EXCLUSIVE_OWNED_FILE'):
                fixture.corrupt_native_archive(self.path, self.sha, '128')
        self.assertEqual(self.path.read_bytes(), self.payload)

    def test_after_final_requires_distinct_disposable_phase_and_corrupts_one_byte(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(fixture.Refusal,
                    'CI_LATE_ARCHIVE_TAMPER_NOT_DISPOSABLE'):
                fixture.corrupt_native_archive(
                    self.path,self.sha,'128',after_final=True)
        self.assertEqual(self.path.read_bytes(),self.payload)
        phase=dict(FLAGS)
        phase.pop('ZAPRET2_STAGE3_NATIVE_LATE_ARCHIVE_TAMPER_CI')
        phase['ZAPRET2_STAGE3_NATIVE_POST_FINAL_ARCHIVE_TAMPER_CI']='1'
        with patch.dict(os.environ,phase,clear=True):
            attestation=fixture.corrupt_native_archive(
                self.path,self.sha,'128',after_final=True)
        self.assertEqual(attestation['status'],
                         'CI_ARCHIVE_CORRUPTED_AFTER_FINAL_GRANT')
        self.assertNotEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),
                            self.sha)
        self.assertFalse(attestation['original_fd9_touched'])
        self.assertFalse(attestation['native_pkg_invoked'])

    def test_invalid_phase_type_refused_without_mutation(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(fixture.Refusal,
                    'CI_ARCHIVE_TAMPER_PHASE_INVALID'):
                fixture.corrupt_native_archive(
                    self.path,self.sha,'128',after_final='true')
        self.assertEqual(self.path.read_bytes(),self.payload)

    def test_foreign_name_and_wrong_revision_denied(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            with self.assertRaisesRegex(fixture.Refusal, 'CI_LATE_ARCHIVE_IDENTITY_INVALID'):
                fixture.corrupt_native_archive(self.path, self.sha, '127')
        self.assertEqual(self.path.read_bytes(), self.payload)


if __name__ == '__main__':
    unittest.main()
