#!/usr/bin/env python3
"""No OPNsense device required: exercise actual Git HEAD and cache-only reads."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_inventory_cache import (
    InventoryCacheError, generate, publish, read_cached, refresh,
)


class TestInventoryCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "zapret2"
        self.state = base / "state"
        self.root.mkdir()
        self.state.mkdir()
        (self.root / "lua").mkdir()
        (self.root / "files/fake").mkdir(parents=True)
        def git(*args):
            subprocess.run(["git", "-C", str(self.root), *args],
                           capture_output=True, check=True)
        self.git = git
        git("init", "-q")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.invalid")
        (self.root / "lua/zapret-lib.lua").write_text("native library\n")
        (self.root / "files/fake/original.bin").write_bytes(b"native blob")
        git("add", "lua", "files")
        git("commit", "-qm", "native")
        (self.root / "lua/extra.lua").write_text("external Lua\n")
        (self.root / "files/fake/extra.bin").write_bytes(b"extra blob")

    def test_actual_head_classifies_all_files_and_reads_cache_only(self):
        data = refresh(self.root, self.state)
        self.assertFalse(data["installed"])
        self.assertEqual(data["lua"], [
            {"name": "extra.lua", "origin": "other"},
            {"name": "zapret-lib.lua", "origin": "upstream"},
        ])
        self.assertEqual(data["bin"], [
            {"name": "extra.bin", "origin": "other"},
            {"name": "original.bin", "origin": "upstream"},
        ])
        (self.state / "installed.json").write_text(json.dumps({
            "schema": 1, "source_commit": "a" * 40, "files": {
                "lua/extra.lua": self._digest(self.root / "lua/extra.lua"),
                "files/fake/extra.bin": self._digest(self.root / "files/fake/extra.bin"),
            },
        }))
        refresh(self.root, self.state)
        # The cached read must not invoke Git or inspect directories.
        saved = self.root.rename(self.root.with_name("renamed"))
        self.assertTrue(read_cached(self.state)["installed"])
        self.assertEqual(len(read_cached(self.state)["lua"]), 2)
        saved.rename(self.root)

    @staticmethod
    def _digest(path):
        import hashlib
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_new_upstream_head_and_dynamic_remove(self):
        data = refresh(self.root, self.state)
        self.assertEqual(data["lua"][0]["origin"], "other")
        self.git("add", "lua/extra.lua")
        self.git("commit", "-qm", "upstream adoption")
        data = refresh(self.root, self.state)
        self.assertEqual(data["lua"][0]["origin"], "upstream")
        (self.root / "files/fake/extra.bin").unlink()
        data = refresh(self.root, self.state)
        self.assertEqual([x["name"] for x in data["bin"]], ["original.bin"])

    def test_modified_tracked_files_and_drift_fail_closed(self):
        refresh(self.root, self.state)
        (self.root / "lua/zapret-lib.lua").write_text("changed tracked file")
        with self.assertRaises(Exception):
            refresh(self.root, self.state)
        self.assertTrue(read_cached(self.state)["lua"])  # previous atomic cache unharmed
        self.git("checkout", "--", "lua/zapret-lib.lua")
        (self.state / "installed.json").write_text(json.dumps({
            "schema": 1, "files": {"lua/extra.lua": "a" * 64},
        }))
        with self.assertRaises(InventoryCacheError):
            generate(self.root, self.state)

    def test_untrusted_cache_refused(self):
        with self.assertRaises(InventoryCacheError):
            read_cached(self.state)
        bad = {"schema": 1, "installed": True,
               "lua": [{"name": "<img src=x>", "origin": "upstream"}], "bin": []}
        publish(bad, self.state)
        with self.assertRaises(InventoryCacheError):
            read_cached(self.state)
        (self.state / "inventory-cache.json").unlink()
        (self.state / "inventory-cache.json").symlink_to(self.root / "lua/extra.lua")
        with self.assertRaises(InventoryCacheError):
            read_cached(self.state)
        with self.assertRaises(InventoryCacheError):
            publish({"schema": 1, "installed": False, "lua": [], "bin": []}, self.state)


if __name__ == "__main__":
    unittest.main()
