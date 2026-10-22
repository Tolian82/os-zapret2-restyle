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
        self.previous = (guard.RUNTIME, guard.STATE, guard.ROLLBACK, guard.GIT)
        guard.RUNTIME, guard.STATE, guard.ROLLBACK, guard.GIT = (
            self.runtime, self.state, self.backup, str(self.git))
        self.addCleanup(self.restore_globals)

    def restore_globals(self):
        guard.RUNTIME, guard.STATE, guard.ROLLBACK, guard.GIT = self.previous

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
