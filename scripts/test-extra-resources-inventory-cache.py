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
from contextlib import ExitStack
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret"))
from extra_resources_inventory_cache import (
    InventoryCacheError, generate, invalidate, publish, read_cached, refresh,
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


    def _faulty_worker(self, mode, actor):
        """Actual dispatch, injected *native* actor and failed Help refresh."""
        import extra_resources_operation as worker
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                "EXTRA_RESOURCES_SETUP_LOCK_OWNER": "1",
                "EXTRA_RESOURCES_OPERATION_ID": "a" * 32,
                "EXTRA_RESOURCES_REMOVE_CONFIRMED": "1"}))
            stack.enter_context(patch.object(worker, "STATE", self.state))
            stack.enter_context(patch.object(worker, "RUNTIME", self.root))
            stack.enter_context(patch.object(worker, "NativeLifecycle", return_value=type(
                "StartedLifecycle", (), {"assert_started": lambda self: "1:2"})()))
            stack.enter_context(patch.object(worker.os, "geteuid", return_value=0))
            stack.enter_context(patch.object(
                worker, "refresh_inventory_cache",
                side_effect=InventoryCacheError("injected failed refresh")))
            if mode == "remove":
                stack.enter_context(patch.object(
                    worker, "remove_with_native_trial", side_effect=actor))
                code = worker.main(["worker", "remove", "f" * 64])
            elif mode == "install":
                stack.enter_context(patch.object(worker, "obtain_revision", return_value="b" * 40))
                stack.enter_context(patch.object(worker, "obtain_archive", return_value=b"archive"))
                stack.enter_context(patch.object(worker, "unpack_verified_archive",
                    return_value={"inventory/capabilities.json":
                                  b'{"schema":1,"resources":[]}'}))
                stack.enter_context(patch.object(worker, "verified_resources",
                    return_value=({"lua/extra.lua": b"external Lua"}, 0)))
                stack.enter_context(patch.object(worker, "make_plan", return_value={}))
                stack.enter_context(patch.object(worker, "install", side_effect=actor))
                code = worker.main(["worker", "install"])
            else:
                stack.enter_context(patch.object(worker, "recover", side_effect=actor))
                code = worker.main(["worker", "recover"])
        self.assertEqual(code, 0)
        with self.assertRaises(InventoryCacheError):
            read_cached(self.state)
        self.assertFalse((self.state / "inventory-cache.json").exists())

    def test_real_remove_dispatch_refresh_failure_retires_stale_installed_cache(self):
        manifest = self.state / "installed.json"
        manifest.write_text(json.dumps({"schema": 1, "source_commit": "a" * 40,
            "files": {"lua/extra.lua": self._digest(self.root / "lua/extra.lua"),
                      "files/fake/extra.bin": self._digest(
                          self.root / "files/fake/extra.bin")}}))
        refresh(self.root, self.state)
        self.assertTrue(read_cached(self.state)["installed"])
        def remove(witness, root, state, lifecycle, *, acceptance_fault):
            (root / "lua/extra.lua").unlink()
            (root / "files/fake/extra.bin").unlink()
            manifest.unlink()
            return {"status": "REMOVED", "lua": 0, "bin": 0, "removed": 2}
        self._faulty_worker("remove", remove)
        self.assertFalse(refresh(self.root, self.state)["installed"])
        self.assertEqual([x["name"] for x in read_cached(self.state)["lua"]],
                         ["zapret-lib.lua"])

    def test_real_install_dispatch_refresh_failure_retires_stale_absent_cache(self):
        refresh(self.root, self.state)
        self.assertFalse(read_cached(self.state)["installed"])
        def install(payloads, revision, root, state, lifecycle, **kwargs):
            (state / "installed.json").write_text(json.dumps({
                "schema": 1, "source_commit": revision,
                "files": {"lua/extra.lua": self._digest(root / "lua/extra.lua")}}))
            return {"status": "INSTALLED", "revision": revision,
                    "lua": 1, "bin": 0, "restarted": True}
        self._faulty_worker("install", install)
        self.assertTrue(refresh(self.root, self.state)["installed"])

    def test_real_recovery_dispatch_refresh_failure_retires_stale_cache(self):
        refresh(self.root, self.state)
        def recover(root, state, lifecycle):
            (root / "files/fake/extra.bin").unlink()
            return "REMOVED"
        self._faulty_worker("recover", recover)

    def test_unsafe_cache_symlink_refuses_before_remove_actor(self):
        import extra_resources_operation as worker
        cache = self.state / "inventory-cache.json"
        cache.symlink_to(self.root / "lua/extra.lua")
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                "EXTRA_RESOURCES_SETUP_LOCK_OWNER": "1",
                "EXTRA_RESOURCES_OPERATION_ID": "a" * 32,
                "EXTRA_RESOURCES_REMOVE_CONFIRMED": "1"}))
            stack.enter_context(patch.object(worker, "STATE", self.state))
            stack.enter_context(patch.object(worker, "RUNTIME", self.root))
            stack.enter_context(patch.object(worker, "NativeLifecycle", return_value=type(
                "StartedLifecycle", (), {"assert_started": lambda self: "1:2"})()))
            stack.enter_context(patch.object(worker.os, "geteuid", return_value=0))
            actor = stack.enter_context(patch.object(worker, "remove_with_native_trial"))
            self.assertEqual(worker.main(["worker", "remove", "f" * 64]), 1)
            actor.assert_not_called()
        self.assertTrue(cache.is_symlink())
        self.assertEqual((self.root / "lua/extra.lua").read_text(), "external Lua\n")

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
