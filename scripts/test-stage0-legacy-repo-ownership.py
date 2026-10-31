#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'legacy', Path(__file__).with_name('stage0-legacy-repo-ownership.py'))
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


class LegacyRepo(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.repo = self.path / 'FreeBSD.conf'
        self.backup = self.path / 'FreeBSD.conf.backup'

    def report(self):
        return legacy.evaluate(self.repo, self.backup)

    def assert_refuses(self, expected):
        result = self.report()
        self.assertEqual(result['classification'], expected)
        self.assertFalse(result['automatic_restore_allowed'])
        self.assertFalse(result['ownership_verified'])
        self.assertFalse(result['foreign_edits_excluded'])
        self.assertNotIn('FreeBSD:', str(result))  # no user repo text

    def test_absent_and_orphan(self):
        self.assert_refuses('no-residue')
        self.backup.write_text('FreeBSD: { enabled: no }\n')
        self.assert_refuses('ambiguous-refuse')

    def test_matching_legacy_requires_external_provenance(self):
        self.repo.write_bytes(legacy.OVERRIDE)
        self.backup.write_text('FreeBSD: { enabled: no }\n')
        self.assert_refuses('legacy-shape-candidate-requires-independent-ownership-proof')
        self.assertEqual(self.repo.read_bytes(), legacy.OVERRIDE)
        self.assertEqual(self.backup.read_text(), 'FreeBSD: { enabled: no }\n')

    def test_foreign_edit_refuses_even_with_backup(self):
        self.repo.write_bytes(legacy.OVERRIDE + b'# foreign edit\n')
        self.backup.write_text('FreeBSD: { enabled: no }\n')
        self.assert_refuses('foreign-or-edited-repo-refuse')
        self.repo.write_text('FreeBSD: { enabled: no }\n')
        self.assert_refuses('foreign-or-edited-repo-refuse')

    def test_invalid_backup_refuses(self):
        self.repo.write_bytes(legacy.OVERRIDE)
        self.backup.write_bytes(b'')
        self.assert_refuses('invalid-or-ambiguous-backup-refuse')
        self.backup.write_bytes(legacy.OVERRIDE)
        self.assert_refuses('invalid-or-ambiguous-backup-refuse')
        self.backup.write_text('FreeBSD: { enabled: yes }\n')
        self.assert_refuses('invalid-or-ambiguous-backup-refuse')

    def test_symlink_and_nonregular_refuse(self):
        self.repo.symlink_to('elsewhere')
        self.backup.write_text('FreeBSD: { enabled: no }\n')
        self.assert_refuses('unsafe-filesystem-object-refuse')
        self.repo.unlink()
        self.repo.write_bytes(legacy.OVERRIDE)
        self.backup.unlink()
        self.backup.symlink_to('elsewhere')
        self.assert_refuses('unsafe-filesystem-object-refuse')
        self.backup.unlink()
        self.backup.mkdir()
        self.assert_refuses('unsafe-filesystem-object-refuse')

    def test_oversize_refuse(self):
        self.repo.write_bytes(legacy.OVERRIDE)
        self.backup.write_bytes(b'x' * (legacy.LIMIT + 1))
        self.assert_refuses('unsafe-filesystem-object-refuse')


if __name__ == '__main__':
    unittest.main()
