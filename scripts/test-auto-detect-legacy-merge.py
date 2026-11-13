#!/usr/bin/env python3
"""#1052 P2k6 protected real-file two-populated legacy migration tests."""
from __future__ import annotations
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / 'src/opnsense/scripts/OPNsense/Zapret/backend'
sys.path.insert(0, str(BACKEND))
from auto_detect_gui_hostlist import (read_current, save_current,
                                     migrate_current, _revision,
                                     AutoHostlistRefused, MIGRATION_DIR)
from auto_detect_destination_commit import DestinationRefused

class NativeLegacyMerge(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(prefix='p2k6-legacy-')
        self.addCleanup(d.cleanup)
        self.base = Path(d.name)
        self.base.chmod(0o700)
        self.path = self.base / 'auto-domains.txt'
        self.legacy = self.base / 'zapret-hosts-auto.txt'
        self.lock = self.base / '.auto-domains.lock'
        self.uid = os.geteuid()

    def put(self, new: str, old: str):
        self.path.write_text(new)
        self.legacy.write_text(old)
        self.path.chmod(0o600)
        self.legacy.chmod(0o600)

    def read(self):
        return read_current(self.path, self.lock, legacy=self.legacy,
                            owner_uid=self.uid)

    def migrate(self, snap):
        return migrate_current(snap['revision'], snap['legacy']['digest'],
                               self.path, self.lock, legacy=self.legacy,
                               owner_uid=self.uid)

    def test_two_populated_approved_merge_and_no_reimport_after_delete(self):
        self.put('new.example\n!^blocked.example\n',
                 'old.example\nnew.example\n!^blocked.example\n')
        before = self.read()
        self.assertEqual(before['legacy']['status'], 'available')
        self.assertEqual(before['legacy']['added'], 1)
        result = self.migrate(before)
        self.assertEqual(result['result'], 'migrated')
        self.assertEqual(result['added'], 1)
        self.assertEqual(self.path.read_text(),
                         'new.example\n!^blocked.example\nold.example\n')
        self.assertEqual(self.legacy.read_text(),
                         'old.example\nnew.example\n!^blocked.example\n')
        self.assertEqual(self.read()['legacy']['status'], 'already_imported')
        self.assertEqual(self.migrate(before)['result'], 'conflict')
        saved = save_current(result['revision'], 'new.example\n', self.path,
                             self.lock, legacy=self.legacy, owner_uid=self.uid)
        self.assertEqual(saved['result'], 'saved')
        self.assertEqual(self.read()['legacy']['status'], 'already_imported')
        self.assertEqual(self.path.read_text(), 'new.example\n')

    def test_two_populated_revisions_and_writer_flock(self):
        self.put('new.example\n', 'old.example\n')
        before = self.read()
        self.path.write_text('other.example\n')
        self.assertEqual(self.migrate(before)['result'], 'conflict')
        self.assertFalse((self.base / MIGRATION_DIR).exists())
        changed = self.read()
        self.legacy.write_text('changed.example\n')
        self.assertEqual(self.migrate(changed)['result'], 'conflict')
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(DestinationRefused, 'gui_writer_busy'):
                self.migrate(self.read_without_lock_reentry())
        finally:
            os.close(fd)

    def read_without_lock_reentry(self):
        return {'revision': _revision(self.path.read_bytes()),
                'legacy': {'digest': _revision(self.legacy.read_bytes())}}

    def test_existing_modifiers_and_negative_overlap_fail_closed(self):
        for new, old in [('example.com\n', '!example.com\n'),
                         ('a.example.com\n', '!example.com\n'),
                         ('!example.com\n', 'a.example.com\n'),
                         ('^example.com\n', 'example.com\n')]:
            with self.subTest(new=new, old=old):
                self.put(new, old)
                result = self.read()
                self.assertEqual(result['legacy']['status'], 'review_required')
                with self.assertRaises(AutoHostlistRefused):
                    self.migrate(self.read_without_lock_reentry())
                self.assertEqual(self.path.read_text(), new)
                self.assertEqual(self.legacy.read_text(), old)

    def test_auto_first_copy_marked_complete_before_any_deletion(self):
        self.legacy.write_text('old.example\n')
        self.legacy.chmod(0o600)
        first = self.read()
        self.assertEqual(first['legacy']['status'], 'already_imported')
        self.assertEqual(self.path.read_text(), 'old.example\n')
        self.assertTrue((self.base / MIGRATION_DIR / 'done.json').is_file())
        saved = save_current(first['revision'], '', self.path, self.lock,
                             legacy=self.legacy, owner_uid=self.uid)
        self.assertEqual(saved['result'], 'saved')
        self.assertEqual(self.read()['legacy']['status'], 'already_imported')
        self.assertEqual(self.path.read_text(), '')

    def test_after_physical_write_before_done_recovers_once(self):
        self.put('new.example\n', 'old.example\n')
        before = self.read()
        import auto_detect_gui_hostlist as mod
        real = mod._write_done
        with patch.object(mod, '_write_done', side_effect=OSError('crash after replace')):
            with self.assertRaises(OSError):
                self.migrate(before)
        self.assertEqual(self.path.read_text(), 'new.example\nold.example\n')
        self.assertFalse((self.base / MIGRATION_DIR / 'done.json').exists())
        incomplete = self.read()
        self.assertEqual(incomplete['legacy']['status'], 'resume_available')
        done = self.migrate(incomplete)
        self.assertEqual(done['result'], 'migrated')
        self.assertEqual(self.path.read_text(), 'new.example\nold.example\n')
        self.assertEqual(self.read()['legacy']['status'], 'already_imported')

    def test_incomplete_journal_conflict_does_not_restore_manual_deletion(self):
        self.put('new.example\n', 'old.example\n')
        before = self.read()
        import auto_detect_gui_hostlist as mod
        with patch.object(mod, '_write_done', side_effect=OSError('crash')):
            with self.assertRaises(OSError): self.migrate(before)
        self.path.write_text('manual.example\n')
        self.assertEqual(self.read()['legacy']['status'], 'review_required')
        self.assertEqual(self.migrate(self.read_without_lock_reentry())['result'], 'conflict')
        self.assertEqual(self.path.read_text(), 'manual.example\n')

    def test_unsafe_legacy_and_changed_source_no_mutation(self):
        self.put('new.example\n', 'old.example\n')
        self.legacy.unlink()
        self.legacy.symlink_to(self.path)
        self.assertEqual(self.read()['legacy']['status'], 'review_required')
        with self.assertRaises(AutoHostlistRefused):
            self.migrate(self.read_without_lock_reentry())
        self.assertEqual(self.path.read_text(), 'new.example\n')

    def test_overlimit_merge_refuses_before_creating_journal(self):
        self.put('new.example\n', 'one.example\ntwo.example\nthree.example\n')
        import auto_detect_gui_hostlist as mod
        with patch.object(mod, 'MAX_MERGE_ADDITIONS', 2):
            self.assertEqual(self.read()['legacy']['status'], 'review_required')
            with self.assertRaisesRegex(AutoHostlistRefused, 'legacy_merge_row_limit'):
                self.migrate(self.read_without_lock_reentry())
        self.assertFalse((self.base / MIGRATION_DIR).exists())
        self.assertEqual(self.path.read_text(), 'new.example\n')

    def test_native_entry_does_not_serve_non_freebsd(self):
        import auto_detect_gui_hostlist as mod
        self.assertEqual(mod.main(['migrate', 'a'*64, 'b'*64]), 0)
        self.assertFalse(self.path.is_symlink())

if __name__ == '__main__':
    unittest.main()