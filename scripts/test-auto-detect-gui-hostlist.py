#!/usr/bin/env python3
"""#1052 P2k5: physical shared HOSTLIST reads and original link-once creation."""
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
    AutoHostlistRefused, read_current, _create,
)
from auto_detect_destination_commit import DestinationRefused

class AutoHostlistGuiTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(prefix='p2k5-gui-')
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.root.chmod(0o700)
        self.path = self.root / 'auto-domains.txt'
        self.retired = self.root / 'zapret-hosts-auto.txt'  # adversarial old artifact
        self.lock = self.root / '.auto-domains.lock'
        self.uid = os.geteuid()

    def read(self):
        return read_current(self.path, self.lock, owner_uid=self.uid)

    def test_missing_and_empty_are_distinct_revisions(self):
        initial = self.read()
        self.assertEqual(initial['status'], 'missing')
        self.assertFalse(self.path.exists())
        _create(self.path, b'', self.uid)
        self.assertEqual(self.read()['status'], 'empty')
        self.assertNotEqual(initial['revision'], self.read()['revision'])
        with self.assertRaises(FileExistsError):
            _create(self.path, b'example.com\n', self.uid)
        self.assertEqual(self.path.read_bytes(), b'')

    def test_retired_file_never_imported_or_inspected(self):
        # A malicious or unreadable obsolete path must not initialize the NEW
        # final file, or block a fresh read.
        self.retired.symlink_to(self.root / 'nonexistent-old-target')
        initial = self.read()
        self.assertEqual(initial['status'], 'missing')
        self.assertEqual(initial['content'], '')
        self.assertFalse(self.path.exists())
        _create(self.path, b'new.example\n', self.uid)
        self.assertEqual(self.path.read_bytes(), b'new.example\n')
        self.assertEqual(self.read()['content'], 'new.example\n')
        self.assertTrue(self.retired.is_symlink())
        self.assertFalse((self.root / '.auto-domains-legacy-migration').exists())

    def test_retired_file_cannot_override_populated_or_empty_new_list(self):
        self.retired.write_text('old.example\n')
        self.retired.chmod(0o600)
        self.path.write_text('new.example\n')
        self.path.chmod(0o600)
        first = self.read()
        self.assertEqual(first['content'], 'new.example\n')
        self.path.write_bytes(b'')
        self.assertEqual(self.read()['status'], 'empty')
        self.assertEqual(self.path.read_bytes(), b'')
        self.assertEqual(self.retired.read_text(), 'old.example\n')

    def test_busy_shared_worker_lock_rejects_read(self):
        self.read()
        fd = os.open(self.lock, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(DestinationRefused, 'gui_writer_busy'):
                self.read()
        finally:
            os.close(fd)
        self.assertFalse(self.path.exists())

    def test_symlink_and_broken_content_refuse_without_writing(self):
        unrelated = self.root / 'unrelated-hostlist.txt'
        unrelated.write_text('original.example\n')
        unrelated.chmod(0o600)
        self.path.symlink_to(unrelated)
        with self.assertRaises(AutoHostlistRefused):
            self.read()
        self.path.unlink()
        self.path.write_bytes(b'\xff')
        with self.assertRaises(AutoHostlistRefused):
            self.read()
        self.assertEqual(unrelated.read_text(), 'original.example\n')

    def test_no_retired_api_or_gui_import_paths(self):
        # Regression for the owner's corrected #1052 contract: inspect only
        # active product sources, not retained historical docs/test fixtures.
        repo = Path(__file__).resolve().parents[1]
        active = [
            BACKEND / 'auto_detect_gui_hostlist.py',
            repo / 'src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt',
            repo / 'src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php',
            repo / 'src/opnsense/service/conf/actions.d/actions_zapret.conf',
        ]
        for path in active:
            source = path.read_text(encoding='utf-8')
            with self.subTest(path=str(path.relative_to(repo))):
                self.assertNotIn('zapret-hosts-auto.txt', source)
                self.assertNotIn('auto_hostlist_migrate', source)
                self.assertNotIn('autoHostlistMigrate', source)
                self.assertNotIn('autoHostlistSave', source)
                self.assertNotIn('auto_hostlist_save', source)
                self.assertNotIn('autoHostlistLegacyState', source)
                self.assertNotIn('auto-domains-legacy-migration', source)
        import inspect
        import auto_detect_gui_hostlist as module
        self.assertNotIn('legacy', inspect.signature(module.read_current).parameters)
        self.assertFalse(hasattr(module, 'save_current'))

    def test_no_auto_service_runtime_or_config_touch(self):
        import auto_detect_gui_hostlist as module
        self.assertEqual(module.AUTO_HOSTLIST.name, 'auto-domains.txt')
        self.assertEqual(module.AUTO_LOCK.name, '.auto-domains.lock')
        self.assertEqual(module.main([]), 0)  # native entry refuses on Linux
        self.assertEqual(module.main(['migrate', 'a', 'b']), 0)
        self.assertFalse(hasattr(module, 'migrate_current'))

if __name__ == '__main__':
    unittest.main()