#!/usr/bin/env python3
"""Offline tests of managed-resource preservation through upstream setup."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(BACKEND))
spec = importlib.util.spec_from_file_location("extra_resources_upstream_guard", BACKEND / "extra_resources_upstream_guard.py")
assert spec and spec.loader
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class UpstreamResources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.runtime = self.base / "zapret2"
        (self.runtime / "lua").mkdir(parents=True)
        (self.runtime / "files/fake").mkdir(parents=True)
        self.state = self.base / "state/extra-resources"
        self.state.mkdir(parents=True)
        self.backup = self.base / "rollback/extra-managed"
        self.lua = self.runtime / "lua/a-dynamic.lua"
        self.lua.write_bytes(b"function extra() end\n")
        self.original = self.lua.read_bytes()
        self.manifest = self.state / "installed.json"
        self.manifest.write_text(json.dumps({
            "schema": 1, "source_commit": "a" * 40,
            "files": {"lua/a-dynamic.lua": guard.sha256(self.original)},
        }))
        self.git = self.base / "git"
        self.git.write_text("#!/bin/sh\necho lua/zapret-lib.lua\n")
        self.git.chmod(0o755)
        self.previous = (guard.RUNTIME, guard.STATE, guard.ROLLBACK, guard.GIT,
                         guard.BACKUP_ROOT, guard.ATTESTATION)
        guard.RUNTIME, guard.STATE, guard.ROLLBACK, guard.GIT = (
            self.runtime, self.state, self.backup, str(self.git))
        guard.BACKUP_ROOT = self.backup.parent
        guard.ATTESTATION = guard.BACKUP_ROOT / "backup-attestation.json"
        self.addCleanup(self.restore_globals)

    def restore_globals(self):
        (guard.RUNTIME, guard.STATE, guard.ROLLBACK, guard.GIT,
         guard.BACKUP_ROOT, guard.ATTESTATION) = self.previous

    def test_unrelated_upstream_file(self):
        guard.preflight()
        guard.verify()

    def test_upstream_collision_fails_before_checkout(self):
        self.git.write_text("#!/bin/sh\necho lua/a-dynamic.lua\n")
        with self.assertRaisesRegex(guard.TransactionError, "conflicts"):
            guard.preflight()

    def test_snapshot_and_restore_preserve_user_file(self):
        guard.snapshot()
        user = self.runtime / "lua/user-file.lua"
        user.write_bytes(b"user file")
        self.lua.unlink()
        guard.restore()
        self.assertEqual(self.lua.read_bytes(), self.original)
        self.assertEqual(user.read_bytes(), b"user file")
        guard.verify()

    def test_modified_owned_resource_blocks_snapshot(self):
        self.lua.write_bytes(b"tampered")
        with self.assertRaisesRegex(guard.TransactionError, "missing or changed"):
            guard.snapshot()
        self.assertFalse(self.backup.exists())

    def test_modified_backup_blocks_restore(self):
        guard.snapshot()
        self.lua.unlink()
        (self.backup / "lua/a-dynamic.lua").write_bytes(b"bad backup")
        with self.assertRaisesRegex(guard.TransactionError, "RESTORE_FAILED"):
            guard.restore()
        self.assertFalse(self.lua.exists())

    def test_snapshot_attestation_after_upstream_deletes_live_resource(self):
        guard.snapshot()
        self.lua.unlink()
        # The original checkout may have removed a managed Lua file during a
        # power cut. The complete saved snapshot is still independently valid.
        guard.verify_snapshot()
        with self.assertRaisesRegex(guard.TransactionError, "missing or changed"):
            guard.verify()
        self.assertEqual((self.backup / "lua/a-dynamic.lua").read_bytes(), self.original)

    def test_snapshot_attestation_after_upstream_modifies_live_resource(self):
        guard.snapshot()
        self.lua.write_bytes(b"candidate checkout")
        guard.verify_snapshot()
        with self.assertRaisesRegex(guard.TransactionError, "missing or changed"):
            guard.verify()
        (self.backup / "lua/a-dynamic.lua").write_bytes(b"corrupt backup")
        with self.assertRaisesRegex(guard.TransactionError, "backup missing or changed"):
            guard.verify_snapshot()

    def test_snapshot_attestation_rejects_pending_transaction_without_live_files(self):
        guard.snapshot()
        self.lua.unlink()
        (self.state / "transaction").mkdir()
        with self.assertRaisesRegex(guard.TransactionError, "unfinished"):
            guard.verify_snapshot()
        self.assertTrue(self.backup.exists())

    def test_snapshot_attestation_before_prepared_cleanup(self):
        guard.snapshot()
        guard.verify_snapshot()
        saved = self.backup / "lua/a-dynamic.lua"
        saved.write_bytes(b"tampered backup")
        with self.assertRaisesRegex(guard.TransactionError, "backup missing or changed"):
            guard.verify_snapshot()

    def test_snapshot_attestation_rejects_symlinked_parent(self):
        guard.snapshot()
        lua_backup = self.backup / "lua"
        saved = self.base / "foreign-backup"
        lua_backup.rename(saved)
        lua_backup.symlink_to(saved, target_is_directory=True)
        with self.assertRaisesRegex(guard.TransactionError, "backup symlink"):
            guard.verify_snapshot()
        self.assertEqual(self.lua.read_bytes(), self.original)

    def test_snapshot_attestation_rejects_extra_file(self):
        guard.snapshot()
        foreign = self.backup / "lua/foreign.lua"
        foreign.write_bytes(b"not part of manifest")
        with self.assertRaisesRegex(guard.TransactionError, "unexpected managed backup"):
            guard.verify_snapshot()
        self.assertEqual(foreign.read_bytes(), b"not part of manifest")

    def test_empty_manifest_rejects_unexpected_backup(self):
        self.manifest.unlink()
        guard.verify_snapshot()
        self.backup.mkdir(parents=True)
        with self.assertRaisesRegex(guard.TransactionError, "unexpected managed backup"):
            guard.verify_snapshot()


    def _compiled_backup(self):
        saved = self.backup.parent / "binaries/my/dvtws2"
        saved.parent.mkdir(parents=True)
        saved.write_bytes(b"compiled binary from original checkout")
        return saved

    def test_sealed_binary_backup_survives_missing_live_managed_lua(self):
        guard.snapshot()
        saved = self._compiled_backup()
        guard.create_backup_attestation(True)
        guard.verify_backup_attestation(True)
        self.lua.unlink()
        guard.verify_backup_attestation(True)
        saved.write_bytes(b"tampered compiled binary")
        with self.assertRaisesRegex(guard.TransactionError, "compiled binary backup changed"):
            guard.verify_backup_attestation(True)
        self.assertTrue(guard.ATTESTATION.exists())

    def test_sealed_manifest_identity_rejects_mutation_and_presence_change(self):
        guard.snapshot()
        self._compiled_backup()
        guard.create_backup_attestation(True)
        self.manifest.write_text(json.dumps({
            "schema": 1, "files": {"lua/a-dynamic.lua": guard.sha256(self.original)},
            "source_commit": "b" * 40,
        }))
        with self.assertRaisesRegex(guard.TransactionError, "managed resource manifest changed"):
            guard.verify_backup_attestation(True)
        self.assertTrue(guard.ATTESTATION.exists())

    def test_sealed_binary_backup_rejects_foreign_entry_and_symlink(self):
        guard.snapshot()
        saved = self._compiled_backup()
        guard.create_backup_attestation(True)
        foreign = saved.parent / "unexpected"
        foreign.write_bytes(b"foreign")
        with self.assertRaisesRegex(guard.TransactionError, "compiled binary backup changed"):
            guard.verify_backup_attestation(True)
        foreign.unlink()
        saved.unlink()
        saved.symlink_to(self.lua)
        with self.assertRaisesRegex(guard.TransactionError, "binary backup symlink"):
            guard.verify_backup_attestation(True)

    def test_sealed_binary_backup_rejects_manifest_absence_change(self):
        self.manifest.unlink()
        # A real setup transaction created runtime-rollback before evidence.
        guard.BACKUP_ROOT.mkdir()
        guard.create_backup_attestation(False)
        guard.verify_backup_attestation(False)
        self.manifest.write_text(json.dumps({"schema": 1, "files": {}}))
        with self.assertRaisesRegex(guard.TransactionError, "managed resource manifest changed"):
            guard.verify_backup_attestation(False)

    def test_sealed_backup_presence_requires_explicit_binary_identity(self):
        guard.snapshot()
        self._compiled_backup()
        with self.assertRaisesRegex(guard.TransactionError, "presence differs"):
            guard.create_backup_attestation(False)
        self.assertFalse(guard.ATTESTATION.exists())
        guard.create_backup_attestation(True)
        with self.assertRaisesRegex(guard.TransactionError, "compiled binary backup changed"):
            guard.verify_backup_attestation(False)

    def test_pending_extra_transaction_refuses_upstream(self):
        (self.state / "transaction").mkdir()
        with self.assertRaisesRegex(guard.TransactionError, "unfinished"):
            guard.preflight()

    def test_unmanaged_files_are_not_assumed_owned(self):
        self.manifest.unlink()
        self.git.write_text("#!/bin/sh\necho lua/a-dynamic.lua\n")
        guard.preflight()
        self.assertEqual(guard._owned(), {})


if __name__ == "__main__":
    unittest.main()
