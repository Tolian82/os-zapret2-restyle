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




class ExactReleaseSwitch(unittest.TestCase):
    """Two real immutable local Git commits; no network or service mutation."""

    def setUp(self):
        import subprocess
        self.sp = subprocess
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.runtime = self.base / "upstream"
        (self.runtime / "lua").mkdir(parents=True)
        (self.runtime / "files/fake").mkdir(parents=True)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.native = self.runtime / "lua/native.lua"
        self.native.write_bytes(b"function native_old() end\n")
        (self.runtime / "files/fake/legacy.bin").write_bytes(b"legacy")
        self.git("add", "lua", "files")
        self.git("commit", "-qm", "upstream v1")
        self.old = self.git_out("rev-parse", "HEAD")
        (self.runtime / "files/fake/legacy.bin").unlink()
        (self.runtime / "files/fake/next.bin").write_bytes(b"new native")
        self.native.write_bytes(b"function native_new() end\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "upstream v2")
        self.new = self.git_out("rev-parse", "HEAD")
        self.git("checkout", "-q", "--detach", self.old)
        self.extra = self.runtime / "lua/managed.lua"
        self.extra.write_bytes(b"function managed() end\n")
        self.state = self.base / "state/extra-resources"
        self.state.mkdir(parents=True)
        self.manifest = self.state / "installed.json"
        self.manifest.write_text(json.dumps({
            "schema": 1, "files": {"lua/managed.lua": guard.sha256(self.extra.read_bytes())},
            "source_commit": "f" * 40,
        }))
        self.before = (guard.RUNTIME, guard.STATE, guard.ROLLBACK,
                       guard.GIT, guard.BACKUP_ROOT, guard.ATTESTATION)
        guard.RUNTIME = self.runtime
        guard.STATE = self.state
        guard.GIT = self.sp.run(["which", "git"], capture_output=True,
                                text=True, check=True).stdout.strip()
        guard.ROLLBACK = self.base / "rollback/extra-managed"
        guard.BACKUP_ROOT = guard.ROLLBACK.parent
        guard.ATTESTATION = guard.BACKUP_ROOT / "backup-attestation.json"
        self.addCleanup(self.restore_globals)

    def restore_globals(self):
        (guard.RUNTIME, guard.STATE, guard.ROLLBACK,
         guard.GIT, guard.BACKUP_ROOT, guard.ATTESTATION) = self.before

    def git(self, *args):
        self.sp.run(["git", "-C", str(self.runtime), *args], check=True,
                    capture_output=True)

    def git_out(self, *args):
        return self.sp.run(["git", "-C", str(self.runtime), *args],
                           check=True, capture_output=True, text=True).stdout.strip()

    def test_exact_old_and_target_reconcile_by_git_checkout(self):
        guard.preflight_exact(self.old)
        guard.preflight_exact(self.new)
        self.git("checkout", "-q", "--detach", self.new)
        guard.verify_exact()
        self.assertFalse((self.runtime / "files/fake/legacy.bin").exists())
        self.assertTrue((self.runtime / "files/fake/next.bin").exists())
        self.assertTrue(self.extra.exists())

    def test_orphan_refuses_before_snapshot_and_checkout(self):
        (self.runtime / "lua/orphan.lua").write_bytes(b"foreign")
        with self.assertRaisesRegex(guard.TransactionError, "exact upstream/extras"):
            guard.preflight_exact(self.new)
        self.assertEqual(self.git_out("rev-parse", "HEAD"), self.old)

    def test_target_new_conflict_with_extra_refuses_without_checkout(self):
        self.git("checkout", "-q", "--detach", self.new)
        (self.runtime / "lua/managed.lua").write_bytes(b"new upstream content")
        self.git("add", "lua/managed.lua")
        self.git("commit", "-qm", "target collision")
        conflicted = self.git_out("rev-parse", "HEAD")
        self.git("checkout", "-q", "--detach", self.old)
        # Checkout removes the tracked target-only file; restore the original
        # untracked managed copy before old-HEAD resource validation.
        self.extra.write_bytes(b"function managed() end\n")
        with self.assertRaisesRegex(guard.TransactionError, "target upstream conflicts"):
            guard.preflight_exact(conflicted)
        self.assertEqual(self.git_out("rev-parse", "HEAD"), self.old)

    def test_upstream_modified_bytes_refused_pre_mutation(self):
        self.native.write_bytes(b"corrupt tracked")
        with self.assertRaisesRegex(Exception, "Git-tracked resource changed"):
            guard.preflight_exact(self.new)

    def test_post_checkout_untracked_drift_refused(self):
        guard.preflight_exact(self.new)
        self.git("checkout", "-q", "--detach", self.new)
        (self.runtime / "files/fake/orphan.bin").write_bytes(b"unexpected")
        with self.assertRaisesRegex(guard.TransactionError, "exact upstream/extras"):
            guard.verify_exact()

    def test_post_checkout_missing_extra_refused(self):
        self.git("checkout", "-q", "--detach", self.new)
        self.extra.unlink()
        with self.assertRaisesRegex(guard.TransactionError, "missing or changed"):
            guard.verify_exact()


    def test_untracked_snapshot_restores_lost_managed_lua(self):
        guard.snapshot()
        guard.snapshot_untracked()
        guard.create_backup_attestation(False)
        record = json.loads(guard.ATTESTATION.read_text())
        self.assertEqual(record["schema"], 2)
        self.assertIn("lua/managed.lua", record["untracked"])
        self.extra.unlink()
        guard.verify_backup_attestation(False)
        with self.assertRaisesRegex(guard.TransactionError, "live untracked"):
            guard.verify_live_untracked()
        guard.restore_untracked()
        self.assertEqual(self.extra.read_bytes(), b"function managed() end\n")
        guard.verify_live_untracked()

    def test_untracked_snapshot_tampering_refuses_recovery(self):
        guard.snapshot()
        guard.snapshot_untracked()
        guard.create_backup_attestation(False)
        self.extra.unlink()
        saved = guard.BACKUP_ROOT / "untracked-resources/lua/managed.lua"
        saved.write_bytes(b"corrupted")
        with self.assertRaisesRegex(guard.TransactionError, "untracked snapshot bytes changed"):
            guard.verify_backup_attestation(False)
        with self.assertRaisesRegex(guard.TransactionError, "untracked snapshot bytes changed"):
            guard.restore_untracked()
        self.assertFalse(self.extra.exists())

    def test_untracked_snapshot_rejects_foreign_backup_entry(self):
        guard.snapshot()
        guard.snapshot_untracked()
        guard.create_backup_attestation(False)
        (guard.BACKUP_ROOT / "untracked-resources/lua/foreign.lua").write_bytes(b"foreign")
        with self.assertRaisesRegex(guard.TransactionError, "untracked snapshot bytes changed"):
            guard.verify_backup_attestation(False)

    def test_untracked_snapshot_rejects_symlink(self):
        guard.snapshot()
        guard.snapshot_untracked()
        guard.create_backup_attestation(False)
        saved = guard.BACKUP_ROOT / "untracked-resources/lua/managed.lua"
        saved.unlink()
        saved.symlink_to(self.extra)
        with self.assertRaisesRegex(guard.TransactionError, "untracked backup symlink"):
            guard.verify_backup_attestation(False)

    def test_untracked_snapshot_preserves_orphan_without_deletion(self):
        orphan = self.runtime / "files/fake/old-unowned.bin"
        orphan.write_bytes(b"owner orphan content")
        guard.snapshot()
        guard.snapshot_untracked()
        guard.create_backup_attestation(False)
        self.assertEqual(orphan.read_bytes(), b"owner orphan content")
        self.assertEqual(
            (guard.BACKUP_ROOT / "untracked-resources/files/fake/old-unowned.bin").read_bytes(),
            b"owner orphan content",
        )
        guard.verify_backup_attestation(False)

    def test_untracked_snapshot_rejects_live_conflict(self):
        guard.snapshot()
        guard.snapshot_untracked()
        guard.create_backup_attestation(False)
        self.extra.write_bytes(b"user changed after snapshot")
        with self.assertRaisesRegex(guard.TransactionError, "live untracked conflict"):
            guard.restore_untracked()
        self.assertEqual(self.extra.read_bytes(), b"user changed after snapshot")

    def test_untracked_snapshot_rejects_corrupt_git_blob(self):
        self.native.write_bytes(b"corrupted upstream file")
        with self.assertRaisesRegex(Exception, "Git-tracked resource changed"):
            guard.snapshot_untracked()
        self.assertFalse((guard.BACKUP_ROOT / "untracked-resources").exists())

    def test_preflight_symlinked_extra_refused(self):
        self.extra.unlink()
        self.extra.symlink_to(self.native)
        with self.assertRaisesRegex(Exception, "symlink"):
            guard.preflight_exact(self.new)

if __name__ == "__main__":
    unittest.main()
