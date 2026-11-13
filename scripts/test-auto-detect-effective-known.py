#!/usr/bin/env python3
"""#1052: real staged YouTube/User hostlist + protected known auto-owned rows."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_effective_known import compose_stage, EffectiveKnownRefused
from auto_detect_owned_sources import bootstrap_empty, OwnedSourcesRefused
from auto_detect_destination_commit import DestinationRefused


class EffectiveKnownTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='p2k8c-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.base.chmod(0o700)
        self.root = self.base / 'auto-detect-owned'
        self.lock = self.base / '.auto-domains.lock'
        self.uid = os.geteuid()
        self.youtube = self.base / 'hostlist-youtube.out'
        self.user = self.base / 'hostlist-user.out'
        self.youtube.write_text('!blocked.example\n^exact.example\nmanual.example\n')
        self.user.write_text('user.example\n')
        self.youtube.chmod(0o644)
        self.user.chmod(0o644)

    def seed(self):
        bootstrap_empty(self.root, original_config_sha256='a' * 64,
                        owner_uid=self.uid, authorized_clean_start=True)

    def compose(self):
        return compose_stage(self.youtube, self.user, root=self.root,
                             lock=self.lock, owner_uid=self.uid)

    def test_absent_source_preserves_manual_files(self):
        before = (self.youtube.read_bytes(), self.user.read_bytes())
        self.assertEqual(self.compose(), {'status': 'uninitialized', 'changed': []})
        self.assertEqual(before, (self.youtube.read_bytes(), self.user.read_bytes()))
        self.assertFalse(self.root.exists())
        self.assertFalse(self.lock.exists())

    def test_real_normalizer_and_owned_rows(self):
        self.seed()
        raw = self.base / 'raw.txt'
        raw.write_text('https://WWW.Example.COM/path\n!blocked.example\n')
        proc = subprocess.run([sys.executable, str(BACKEND / 'domain_policy.py'),
                               'single', 'youtube', str(raw), str(self.youtube)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        (self.root / 'youtube.txt').write_text('video.example\nwww.example.com\n')
        (self.root / 'user.txt').write_text('login.example\nsub.blocked.example\n')
        self.assertEqual(self.compose()['changed'], ['youtube', 'user'])
        self.assertEqual(self.youtube.read_text(),
                         'www.example.com\n!blocked.example\nvideo.example\n')
        self.assertEqual(self.user.read_text(), 'user.example\nlogin.example\n')
        self.assertEqual(self.compose()['changed'], [])
        self.assertEqual((self.root / 'youtube.txt').read_text(),
                         'video.example\nwww.example.com\n')

    def test_corrupted_source_refuses_before_any_change(self):
        self.seed()
        (self.root / 'user.txt').write_text('Upper.example\n')
        before = (self.youtube.read_bytes(), self.user.read_bytes())
        with self.assertRaises(OwnedSourcesRefused):
            self.compose()
        self.assertEqual(before, (self.youtube.read_bytes(), self.user.read_bytes()))

    def test_shared_gui_lock_prevents_read_during_gui_save(self):
        self.seed()
        (self.root / 'user.txt').write_text('new.example\n')
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(DestinationRefused):
                self.compose()
        finally:
            os.close(fd)
        self.assertEqual(self.user.read_text(), 'user.example\n')

    def test_noncanonical_and_symlink_stage_refuse(self):
        self.seed()
        self.youtube.write_text('UPPER.example\n')
        with self.assertRaisesRegex(EffectiveKnownRefused, 'noncanonical_managed'):
            self.compose()
        self.youtube.write_text('manual.example\n')
        self.user.unlink()
        self.user.symlink_to(self.youtube)
        with self.assertRaises(DestinationRefused):
            self.compose()

    def test_original_builder_is_wired_before_staging_publication(self):
        shell = (BACKEND / 'targets.sh').read_text()
        self.assertIn('auto_detect_effective_known.py" compose', shell)
        self.assertLess(shell.index('auto_detect_effective_known.py" compose'),
                        shell.index('mv -f "' + chr(36) + '{input_root}/hostlist-youtube.out"'))


if __name__ == '__main__':
    unittest.main()
