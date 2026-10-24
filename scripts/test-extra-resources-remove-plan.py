#!/usr/bin/env python3
"""Real-Git, offline Stage-1 removal-plan contract; never mutates the runtime."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_preflight import PreflightError
from extra_resources_reconcile import make_remove_plan

NATIVE_LUA = b"function upstream() return true end\n"
NATIVE_BIN = b"\x16\x03\x03\x00\x02\x01\x00"
EXTRA_LUA = b"function optional_action() return true end\n"
EXTRA_BIN = b"\x00\x01EXTRA"


class TestReadOnlyRemovalPlanner(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.root = base / "installed-zapret2"
        self.root.mkdir()
        (self.root / "lua").mkdir()
        (self.root / "files/fake").mkdir(parents=True)
        self.managed = base / "state" / "installed.json"
        self.managed.parent.mkdir()
        self.config = base / "conf" / "config.xml"
        self.config.parent.mkdir()
        self.config.write_text("<opnsense><saved/></opnsense>\n")

        self.git("init", "-q")
        self.git("config", "user.email", "tests@example.invalid")
        self.git("config", "user.name", "Remove Plan Test")
        (self.root / "lua/native.lua").write_bytes(NATIVE_LUA)
        (self.root / "files/fake/native.bin").write_bytes(NATIVE_BIN)
        self.git("add", "lua", "files/fake")
        self.git("commit", "-qm", "installed upstream v1")
        (self.root / "lua/addon.lua").write_bytes(EXTRA_LUA)
        (self.root / "files/fake/manual.bin").write_bytes(EXTRA_BIN)

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args],
                                check=True, capture_output=True)
        return result.stdout.decode().strip()

    def plan(self):
        return make_remove_plan(self.root, self.managed, self.config)

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest()

    def test_exact_non_upstream_set_includes_managed_and_manual_without_writes(self):
        self.managed.write_text(json.dumps({
            "schema": 1, "files": {"lua/addon.lua": self.digest(EXTRA_LUA)}
        }))
        paths = [self.root / "lua/native.lua", self.root / "files/fake/native.bin",
                 self.root / "lua/addon.lua", self.root / "files/fake/manual.bin",
                 self.config, self.managed]
        original = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        head = self.git("rev-parse", "HEAD")
        result = self.plan()
        self.assertEqual(result["upstream_head"], head)
        self.assertEqual(result["status"], "dry_run_only")
        self.assertEqual(result["compatibility"], "unknown")
        self.assertFalse(result["authorized"])
        self.assertEqual(result["counts"], {"lua": 1, "bin": 1, "total": 2})
        self.assertEqual([p["path"] for p in result["remove"]],
                         ["files/fake/manual.bin", "lua/addon.lua"])
        self.assertEqual(result["remove"][0]["sha256"], self.digest(EXTRA_BIN))
        self.assertEqual(len(result["witness"]["inventory_sha256"]), 64)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual({str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in paths},
                         original)

    def test_new_upstream_head_changes_plan_without_filename_lists(self):
        self.assertEqual(self.plan()["counts"]["total"], 2)
        self.git("add", "lua/addon.lua")
        self.git("commit", "-qm", "adopt addon into installed upstream")
        self.assertEqual(self.plan()["counts"], {"lua": 0, "bin": 1, "total": 1})
        self.assertEqual([e["path"] for e in self.plan()["remove"]],
                         ["files/fake/manual.bin"])

    def test_no_extra_resources_is_true_noop_plan(self):
        (self.root / "lua/addon.lua").unlink()
        (self.root / "files/fake/manual.bin").unlink()
        result = self.plan()
        self.assertEqual(result["counts"]["total"], 0)
        self.assertEqual(result["remove"], [])
        self.assertFalse(result["authorized"])

    def test_modified_upstream_bytes_fail_closed(self):
        (self.root / "lua/native.lua").write_bytes(b"tampered")
        with self.assertRaisesRegex(PreflightError, "Git-tracked resource changed"):
            self.plan()

    def test_extra_symlink_refused_without_following(self):
        (self.root / "lua/addon.lua").unlink()
        (self.root / "lua/addon.lua").symlink_to(self.config)
        with self.assertRaisesRegex(PreflightError, "unsafe current runtime resource"):
            self.plan()
        self.assertTrue(self.config.is_file())

    def test_bad_managed_ownership_refused(self):
        self.managed.write_text(json.dumps({
            "schema": 1, "files": {"lua/addon.lua": "0" * 64}
        }))
        with self.assertRaisesRegex(PreflightError, "ownership differs"):
            self.plan()

    def test_managed_manifest_cannot_claim_current_upstream(self):
        self.managed.write_text(json.dumps({
            "schema": 1, "files": {"lua/native.lua": self.digest(NATIVE_LUA)}
        }))
        with self.assertRaisesRegex(PreflightError, "ownership differs"):
            self.plan()

    def test_config_is_required_and_not_followed(self):
        self.config.unlink()
        with self.assertRaisesRegex(PreflightError, "saved OPNsense configuration"):
            self.plan()
        self.config.symlink_to(self.root / "lua/native.lua")
        with self.assertRaisesRegex(PreflightError, "saved OPNsense configuration"):
            self.plan()

    def test_changed_head_between_attestations_refused(self):
        head = self.git("rev-parse", "HEAD")
        with patch("extra_resources_reconcile._remove_head",
                   side_effect=[head, "b" * 40]):
            with self.assertRaisesRegex(PreflightError, "inventory changed"):
                self.plan()

    def test_invalid_directory_and_manual_non_regular_file_block(self):
        (self.root / "files/fake/manual.bin").unlink()
        (self.root / "files/fake/manual.bin").mkdir()
        with self.assertRaisesRegex(PreflightError, "unsafe current runtime resource"):
            self.plan()


if __name__ == "__main__":
    unittest.main()
