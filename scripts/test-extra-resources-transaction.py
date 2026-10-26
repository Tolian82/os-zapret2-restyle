#!/usr/bin/env python3
"""Targeted offline resource-transaction checks; no FreeBSD services invoked."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location("extra_resources_transaction", SRC / "extra_resources_transaction.py")
assert spec and spec.loader
tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tx)

REV = "a" * 40
LUA = b"function user_dynamic(ctx, d) return true end\n"
BIN = b"\x16\x03\x03\x00\x07\x01\x00\x00\x03yes"


class Lifecycle:
    def __init__(self):
        self.running = True
        self.pid = 41
        self.stops = 0
        self.starts = 0
        self.fail_once = False
        self.crash_once = False

    def assert_started(self):
        if not self.running:
            raise RuntimeError("not running")
        return str(self.pid)

    def assert_stopped(self):
        if self.running:
            raise RuntimeError("not stopped")

    def stop(self):
        self.stops += 1
        self.running = False

    def start(self):
        self.starts += 1
        if self.crash_once:
            self.crash_once = False
            raise KeyboardInterrupt()
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("start failure")
        self.running = True
        self.pid += 1


class TestResourceTransaction(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "zapret2"
        self.state = Path(self.temp.name) / "state"
        (self.root / "lua").mkdir(parents=True)
        (self.root / "files/fake").mkdir(parents=True)
        self.lifecycle = Lifecycle()
        self.payloads = {"lua/user_dynamic.lua": LUA,
                         "files/fake/user_dynamic.bin": BIN}

    def install(self, payloads=None):
        return tx.install(payloads if payloads is not None else self.payloads,
                          REV, self.root, self.state, self.lifecycle,
                          capabilities={"schema": 1, "resources": []})

    def test_first_install_and_restart(self):
        result = self.install()
        self.assertEqual(result["status"], "INSTALLED")
        self.assertTrue(result["restarted"])
        self.assertEqual(self.lifecycle.stops, 1)
        self.assertEqual(self.lifecycle.starts, 1)
        self.assertEqual((self.root / "lua/user_dynamic.lua").read_bytes(), LUA)
        self.assertEqual(json.loads((self.state / "installed.json").read_text())["source_commit"], REV)
        self.assertFalse((self.state / "transaction").exists())

    def test_identical_second_click_still_restarts(self):
        self.install()
        first = self.lifecycle.pid
        self.install()
        self.assertNotEqual(first, self.lifecycle.pid)
        self.assertEqual((self.lifecycle.starts, self.lifecycle.stops), (2, 2))
        self.assertEqual(list((self.root / "lua").glob("*.lua")),
                         [self.root / "lua/user_dynamic.lua"])

    def test_dynamic_add_remove_and_update(self):
        self.install()
        next_set = {"lua/next_dynamic.lua": b"function next_dynamic() end\n",
                    "files/fake/user_dynamic.bin": b"new-payload"}
        result = self.install(next_set)
        self.assertEqual((result["lua"], result["bin"]), (1, 1))
        self.assertFalse((self.root / "lua/user_dynamic.lua").exists())
        self.assertEqual((self.root / "lua/next_dynamic.lua").read_bytes(),
                         b"function next_dynamic() end\n")
        self.assertEqual((self.root / "files/fake/user_dynamic.bin").read_bytes(),
                         b"new-payload")

    def test_upstream_filename_collision_rejected_before_stop(self):
        (self.root / "lua/user_dynamic.lua").write_bytes(LUA)
        with self.assertRaisesRegex(tx.TransactionError, "upstream/user"):
            self.install()
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertFalse(self.state.joinpath("transaction").exists())

    def test_initial_stopped_service_rejected_without_write(self):
        self.lifecycle.running = False
        with self.assertRaisesRegex(RuntimeError, "not running"):
            self.install()
        self.assertFalse((self.root / "lua/user_dynamic.lua").exists())

    def test_start_failure_rolls_back_previous_managed_files(self):
        self.install()
        old_metadata = (self.state / "installed.json").read_bytes()
        self.lifecycle.fail_once = True
        with self.assertRaisesRegex(tx.TransactionError, "INSTALL_FAILED_RESTORED"):
            self.install({"lua/user_dynamic.lua": b"modified", "files/fake/user_dynamic.bin": BIN})
        self.assertEqual((self.root / "lua/user_dynamic.lua").read_bytes(), LUA)
        self.assertEqual((self.state / "installed.json").read_bytes(), old_metadata)
        self.assertTrue(self.lifecycle.running)
        self.assertFalse((self.state / "transaction").exists())

    def test_crash_keeps_backups_and_recovery_restores(self):
        self.install()
        self.lifecycle.crash_once = True
        with self.assertRaises(KeyboardInterrupt):
            self.install({"lua/user_dynamic.lua": b"updated", "files/fake/user_dynamic.bin": BIN})
        self.assertTrue((self.state / "transaction/journal.json").exists())
        with self.assertRaisesRegex(tx.TransactionError, "RECOVERY_REQUIRED"):
            self.install()
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "RESTORED")
        self.assertEqual((self.root / "lua/user_dynamic.lua").read_bytes(), LUA)
        self.assertTrue(self.lifecycle.running)

    def test_recovery_rejects_unexpected_user_modifications(self):
        self.install()
        self.lifecycle.crash_once = True
        with self.assertRaises(KeyboardInterrupt):
            self.install({"lua/user_dynamic.lua": b"updated", "files/fake/user_dynamic.bin": BIN})
        (self.root / "lua/user_dynamic.lua").write_bytes(b"not from either revision")
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue((self.state / "transaction/journal.json").exists())

    def test_invalid_paths_and_revision_are_refused(self):
        with self.assertRaisesRegex(tx.TransactionError, "immutable Git SHA"):
            tx.install(self.payloads, "main", self.root, self.state, self.lifecycle)
        with self.assertRaisesRegex(tx.TransactionError, "unsafe"):
            self.install({"../escape.lua": b"bad"})
        self.assertEqual(self.lifecycle.stops, 0)

    def test_managed_file_drift_fails_without_stop(self):
        self.install()
        (self.root / "lua/user_dynamic.lua").write_bytes(b"modified outside ownership")
        old_stops = self.lifecycle.stops
        with self.assertRaisesRegex(tx.TransactionError, "changed or missing"):
            self.install()
        self.assertEqual(self.lifecycle.stops, old_stops)



class TestExactReconciliation(unittest.TestCase):
    """A real local Git checkout; no network or OPNsense service invoked."""

    def setUp(self):
        TestResourceTransaction.setUp(self)
        import subprocess
        self.subprocess = subprocess
        self.git("init", "-q")
        self.git("config", "user.name", "Resource Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "lua/native.lua").write_bytes(b"function native() end\n")
        (self.root / "files/fake/native.bin").write_bytes(b"native")
        self.git("add", "lua/native.lua", "files/fake/native.bin")
        self.git("commit", "-qm", "upstream fixture")
        (self.root / "lua/orphan.lua").write_bytes(b"orphaned bytes")
        (self.root / "files/fake/user_dynamic.bin").write_bytes(b"unmanaged existing bytes")

    def git(self, *args):
        self.subprocess.run(["git", "-C", str(self.root), *args],
                            check=True, capture_output=True)

    def install(self, payloads=None):
        return tx.install(payloads if payloads is not None else self.payloads,
                          REV, self.root, self.state, self.lifecycle,
                          capabilities={"schema": 1, "resources": []},
                          reconcile=True)

    def test_replaces_preexisting_and_prunes_orphans(self):
        result = self.install()
        self.assertEqual(result["removed"], 1)
        self.assertFalse((self.root / "lua/orphan.lua").exists())
        self.assertEqual((self.root / "files/fake/user_dynamic.bin").read_bytes(), BIN)
        self.assertEqual((self.root / "files/fake/native.bin").read_bytes(), b"native")
        self.assertEqual((self.root / "lua/native.lua").read_bytes(), b"function native() end\n")
        self.assertEqual(self.lifecycle.stops, 1)
        self.assertEqual(self.lifecycle.starts, 1)

    def test_restart_failure_restores_every_unmanaged_file(self):
        self.lifecycle.fail_once = True
        with self.assertRaisesRegex(tx.TransactionError, "INSTALL_FAILED_RESTORED"):
            self.install()
        self.assertTrue(self.lifecycle.running)
        self.assertEqual((self.root / "lua/orphan.lua").read_bytes(), b"orphaned bytes")
        self.assertEqual((self.root / "files/fake/user_dynamic.bin").read_bytes(),
                         b"unmanaged existing bytes")
        self.assertFalse((self.root / "lua/user_dynamic.lua").exists())
        self.assertFalse((self.state / "transaction").exists())

    def test_recover_after_interrupted_restart(self):
        self.lifecycle.crash_once = True
        with self.assertRaises(KeyboardInterrupt):
            self.install()
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "RESTORED")
        self.assertEqual((self.root / "lua/orphan.lua").read_bytes(), b"orphaned bytes")
        self.assertEqual((self.root / "files/fake/user_dynamic.bin").read_bytes(),
                         b"unmanaged existing bytes")

    def test_upstream_tracked_file_change_refuses_before_stop(self):
        (self.root / "lua/native.lua").write_bytes(b"changed")
        with self.assertRaisesRegex(tx.TransactionError, "Git-tracked resource changed"):
            self.install()
        self.assertEqual(self.lifecycle.stops, 0)

    def test_conflicting_upstream_filename_refuses(self):
        with self.assertRaisesRegex(tx.TransactionError, "upstream/additional resource collision"):
            self.install({"lua/native.lua": b"foreign"})
        self.assertEqual(self.lifecycle.stops, 0)

    def test_symlinked_orphan_refuses_before_stop(self):
        (self.root / "lua/orphan.lua").unlink()
        (self.root / "lua/orphan.lua").symlink_to(self.root / "lua/native.lua")
        with self.assertRaisesRegex(tx.TransactionError, "unsafe current runtime resource"):
            self.install()
        self.assertEqual(self.lifecycle.stops, 0)

    def removal_plan(self):
        from extra_resources_reconcile import make_remove_plan
        config = Path(self.temp.name) / "config.xml"
        config.write_text("<opnsense><saved/></opnsense>\n")
        plan = make_remove_plan(self.root, self.state / "installed.json", config)
        return plan, config

    def trial_route(self, *, fail=False, crash=False):
        def actual_native_gui_compiler_and_start():
            # A new, future production adapter must use shared GUI Apply;
            # this fixture only models its required file-visibility boundary.
            self.assertFalse((self.root / "lua/orphan.lua").exists())
            self.assertFalse((self.root / "files/fake/user_dynamic.bin").exists())
            self.assertEqual((self.root / "lua/native.lua").read_bytes(),
                             b"function native() end\n")
            self.assertEqual((self.root / "files/fake/native.bin").read_bytes(), b"native")
            if crash:
                raise KeyboardInterrupt("simulated abrupt interruption")
            if fail:
                raise RuntimeError("existing GUI Apply candidate failed")
            self.lifecycle.start()
        self.lifecycle.start_trial_native_common_apply = actual_native_gui_compiler_and_start

    def test_remove_requires_exact_native_gui_apply_before_any_stop(self):
        plan, config = self.removal_plan()
        with self.assertRaisesRegex(tx.TransactionError, "native common Apply trial route"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertTrue((self.root / "lua/orphan.lua").exists())
        self.assertFalse((self.state / "transaction").exists())
        self.assertFalse((self.root / tx.QUARANTINE_NAME).exists())

    def test_remove_native_trial_exact_upstream_success(self):
        plan, config = self.removal_plan()
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "installed.json").write_text(json.dumps({
            "schema": 1, "files": {
                "files/fake/user_dynamic.bin": tx.sha256(b"unmanaged existing bytes")
            }
        }))
        plan, config = self.removal_plan()
        self.trial_route()
        result = tx.remove_with_native_trial(
            plan["witness"]["inventory_sha256"], self.root,
            self.state, self.lifecycle, config=config)
        self.assertEqual(result["status"], "REMOVED")
        self.assertEqual(result["removed"], 2)
        self.assertEqual(self.lifecycle.stops, 1)
        self.assertEqual(self.lifecycle.starts, 1)
        self.assertFalse((self.state / "installed.json").exists())
        self.assertFalse((self.root / tx.QUARANTINE_NAME).exists())
        self.assertFalse((self.state / "transaction").exists())
        self.assertFalse((self.root / "lua/orphan.lua").exists())
        self.assertFalse((self.root / "files/fake/user_dynamic.bin").exists())

    def test_remove_native_gui_apply_failure_restores_every_byte(self):
        plan, config = self.removal_plan()
        self.trial_route(fail=True)
        previous = {name: (self.root / name).read_bytes()
                    for name in ("lua/orphan.lua", "files/fake/user_dynamic.bin")}
        with self.assertRaisesRegex(tx.TransactionError, "REMOVE_FAILED_RESTORED"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertTrue(self.lifecycle.running)
        self.assertEqual(self.lifecycle.stops, 2)
        self.assertEqual(self.lifecycle.starts, 1)
        for name, data in previous.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        self.assertFalse((self.state / "transaction").exists())
        self.assertFalse((self.root / tx.QUARANTINE_NAME).exists())

    def test_remove_hard_interrupt_retains_recoverable_journal(self):
        plan, config = self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertTrue((self.state / "transaction/journal.json").is_file())
        self.assertTrue((self.root / tx.QUARANTINE_NAME).is_dir())
        self.assertFalse((self.root / "lua/orphan.lua").exists())
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "RESTORED")
        self.assertTrue((self.root / "lua/orphan.lua").is_file())
        self.assertTrue((self.root / "files/fake/user_dynamic.bin").is_file())
        self.assertFalse((self.root / tx.QUARANTINE_NAME).exists())
        self.assertTrue(self.lifecycle.running)

    def test_remove_stale_confirm_refuses_without_mutation(self):
        plan, config = self.removal_plan()
        self.trial_route()
        config.write_text("<opnsense><changed/></opnsense>\n")
        with self.assertRaisesRegex(tx.TransactionError, "stale"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertTrue((self.root / "lua/orphan.lua").exists())
        self.assertFalse((self.state / "transaction").exists())

    def test_remove_no_extras_does_not_restart(self):
        (self.root / "lua/orphan.lua").unlink()
        (self.root / "files/fake/user_dynamic.bin").unlink()
        plan, config = self.removal_plan()
        self.trial_route()
        result = tx.remove_with_native_trial(
            plan["witness"]["inventory_sha256"], self.root,
            self.state, self.lifecycle, config=config)
        self.assertEqual(result["status"], "NO_EXTRA_RESOURCES")
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertEqual(self.lifecycle.starts, 0)
        self.assertFalse((self.state / "transaction").exists())

    def test_second_install_still_restarts_with_exact_files(self):
        self.install()
        old_pid = self.lifecycle.pid
        second = self.install()
        self.assertEqual(second["removed"], 0)
        self.assertNotEqual(self.lifecycle.pid, old_pid)
        self.assertFalse((self.root / "lua/orphan.lua").exists())

if __name__ == "__main__":
    unittest.main()
