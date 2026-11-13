#!/usr/bin/env python3
"""#1052 P2k5: physical GUI read/save root flock and stale-page protection."""
from __future__ import annotations
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_gui_hostlist import (
    AutoHostlistRefused, read_current, save_current, _revision,
)
from auto_detect_destination_commit import DestinationRefused

class AutoHostlistGuiTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(prefix='p2k5-gui-')
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.root.chmod(0o700)
        self.path = self.root / 'auto-domains.txt'
        self.legacy = self.root / 'zapret-hosts-auto.txt'
        self.lock = self.root / '.auto-domains.lock'
        self.uid = os.geteuid()

    def read(self):
        return read_current(self.path, self.lock, legacy=self.legacy, owner_uid=self.uid)

    def save(self, token, value):
        return save_current(token, value, self.path, self.lock,
                            legacy=self.legacy, owner_uid=self.uid)

    def test_missing_create_empty_then_populated_with_modifiers(self):
        initial = self.read()
        self.assertEqual(initial['status'], 'missing')
        self.assertFalse(self.path.exists())
        saved = self.save(initial['revision'], '')
        self.assertEqual(saved['result'], 'saved')
        self.assertEqual(self.read()['status'], 'empty')
        self.assertNotEqual(initial['revision'], saved['revision'])
        populated = self.save(saved['revision'], 'Example.COM\n!^test.invalid\n')
        self.assertEqual(populated['result'], 'saved')
        self.assertEqual(self.path.read_text(), 'example.com\n!^test.invalid\n')
        self.assertEqual(self.read()['status'], 'populated')

    def test_two_tabs_reject_stale_save_and_preserve_user_deletion(self):
        token = self.read()['revision']
        first = self.save(token, 'alpha.example\n')
        self.assertEqual(self.save(token, 'beta.example\n')['result'], 'conflict')
        self.assertEqual(self.path.read_text(), 'alpha.example\n')
        second = self.save(first['revision'], '')
        self.assertEqual(second['status'], 'empty')
        self.assertEqual(self.path.read_bytes(), b'')
        self.assertEqual(self.save(first['revision'], 'alpha.example\n')['result'], 'conflict')
        self.assertEqual(self.path.read_bytes(), b'')

    def test_legacy_first_read_copy_without_overwrite_or_reimport(self):
        self.legacy.write_bytes(b'legacy.example\n!exact.invalid\n')
        self.legacy.chmod(0o600)
        result = self.read()
        self.assertEqual(result['content'], 'legacy.example\n!exact.invalid\n')
        self.assertEqual(self.legacy.read_bytes(), self.path.read_bytes())
        cleared = self.save(result['revision'], '')
        self.assertEqual(cleared['status'], 'empty')
        # Legacy source survives, but a later GUI read must NOT restore deletion.
        self.assertEqual(self.read()['status'], 'empty')
        self.assertEqual(self.path.read_bytes(), b'')
        self.assertTrue(self.legacy.exists())

    def test_preexisting_new_list_is_never_overwritten_from_legacy(self):
        self.legacy.write_text('old.example\n')
        self.legacy.chmod(0o600)
        self.path.write_text('new.example\n')
        self.path.chmod(0o600)
        self.assertEqual(self.read()['content'], 'new.example\n')
        self.assertEqual(self.legacy.read_text(), 'old.example\n')

    def test_busy_shared_worker_lock_rejects_both_read_and_save(self):
        token = self.read()['revision']
        fd = os.open(self.lock, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(DestinationRefused, 'gui_writer_busy'):
                self.read()
            with self.assertRaisesRegex(DestinationRefused, 'gui_writer_busy'):
                self.save(token, 'example.com\n')
        finally:
            os.close(fd)
        self.assertFalse(self.path.exists())

    def test_symlink_and_broken_content_refuse_without_writing(self):
        self.legacy.write_text('original.example\n')
        self.legacy.chmod(0o600)
        self.path.symlink_to(self.legacy)
        with self.assertRaises(AutoHostlistRefused):
            self.read()
        self.path.unlink()
        snapshot = self.read()
        with self.assertRaises(AutoHostlistRefused):
            self.save(snapshot['revision'], '!bad.example\nbad.example\n')
        self.assertEqual(self.path.read_text(), 'original.example\n')

    def test_no_auto_service_runtime_or_config_touch(self):
        import auto_detect_gui_hostlist as module
        self.assertEqual(module.AUTO_HOSTLIST.name, 'auto-domains.txt')
        self.assertEqual(module.AUTO_LOCK.name, '.auto-domains.lock')
        self.assertEqual(module.main([]), 0)  # native entry refuses on Linux

if __name__ == '__main__':
    unittest.main()