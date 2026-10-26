#!/usr/bin/env python3
"""Targeted offline resource-transaction checks; no FreeBSD services invoked."""
from __future__ import annotations

import importlib.util
import json
import os
import stat
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

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


class TestNativeRecoveryReceipt(unittest.TestCase):
    def test_cold_prepared_native_recovery_receipt_is_exact(self):
        from extra_resources_operation import NativeLifecycle
        from extra_resources_transaction import TransactionError as NativeTransactionError
        lifecycle = NativeLifecycle.__new__(NativeLifecycle)
        lifecycle.script = Path("/fake-native-service")
        owner = {"id":"a"*32,"page":"voice","candidate":"b"*64}
        for message,expected in (
            ("native-remove-prepared=not-needed\n",False),
            ("native-remove-prepared-restored="+"a"*32+"\n",True),
        ):
            with patch("extra_resources_operation.subprocess.run",
                       return_value=SimpleNamespace(returncode=0,stdout=message,
                                                     stderr="")) as runner:
                self.assertIs(lifecycle.recover_prepared_native_common_apply(owner), expected)
                self.assertEqual(runner.call_args.kwargs["pass_fds"], (9,))
                self.assertEqual(runner.call_args.kwargs["env"][
                    "EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE"],"1")
        for returncode,stdout in ((70,""),(0,""),(0,"fake-success\n"),
                                  (0,"native-remove-prepared-restored="+"c"*32+"\n")):
            with patch("extra_resources_operation.subprocess.run",
                       return_value=SimpleNamespace(returncode=returncode,
                                                     stdout=stdout,stderr="")):
                with self.assertRaisesRegex(NativeTransactionError,"RESTORE_FAILED"):
                    lifecycle.recover_prepared_native_common_apply(owner)

    def test_fresh_native_remove_trial_requires_full_success_receipt(self):
        from extra_resources_operation import NativeLifecycle
        from extra_resources_transaction import TransactionError as NativeTransactionError
        lifecycle = NativeLifecycle.__new__(NativeLifecycle)
        lifecycle.script = Path("/fake-native-service")
        with patch("extra_resources_operation.subprocess.run",
                   return_value=SimpleNamespace(returncode=0,
                       stdout="native-remove-applied=" + "a"*32 + "\n",
                       stderr="")) as runner:
            lifecycle.start_trial_native_common_apply()
            self.assertEqual(runner.call_args.args[0][1], "extra-resources-native-trial")
            self.assertEqual(runner.call_args.kwargs["env"][
                "EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL"], "1")
            self.assertEqual(runner.call_args.kwargs["pass_fds"], (9,))
        for status, stdout in (
            (70, "native-remove-applied=" + "a"*32 + "\n"),
            (0, "prepared-id=" + "a"*32 + "\n"),
            (0, "native-remove-applied=" + "b"*31 + "\n"),
            (0, ""),
        ):
            with patch("extra_resources_operation.subprocess.run",
                       return_value=SimpleNamespace(returncode=status,
                                                     stdout=stdout, stderr="")):
                with self.assertRaisesRegex(NativeTransactionError, "not attested"):
                    lifecycle.start_trial_native_common_apply()

    def test_exact_native_owner_restore_accepts_normal_common_boot_receipt(self):
        from extra_resources_operation import NativeLifecycle
        from extra_resources_transaction import TransactionError as NativeTransactionError
        lifecycle = NativeLifecycle.__new__(NativeLifecycle)
        lifecycle.script = Path("/fake-native-service")
        owner = {"id": "a"*32, "page": "voice", "candidate": "b"*64}
        for prefix in ("native-common-boot=" + owner["id"] + "\n",
                       "remove-owner-restored\n"):
            output = prefix + "native-owner-restored=" + owner["id"] + "\n"
            with patch("extra_resources_operation.subprocess.run",
                       return_value=SimpleNamespace(returncode=0, stdout=output,
                                                     stderr="")) as runner:
                lifecycle.restore_previous_native_common_apply(owner)
                self.assertEqual(runner.call_args.args[0][-3:],
                                 [owner["id"], owner["page"], owner["candidate"]])
                self.assertEqual(runner.call_args.kwargs["env"][
                    "EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE"], "1")
        for output, code in (("", 0), ("native-common-boot=" + owner["id"] + "\n", 0),
                             ("native-owner-restored=" + "c"*32 + "\n", 0),
                             ("native-owner-restored=" + owner["id"] + "\n", 70)):
            with patch("extra_resources_operation.subprocess.run",
                       return_value=SimpleNamespace(returncode=code, stdout=output,
                                                     stderr="")):
                with self.assertRaisesRegex(NativeTransactionError, "RESTORE_FAILED"):
                    lifecycle.restore_previous_native_common_apply(owner)


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
        old_owner = {"id": "a"*32, "page": "voice", "candidate": "b"*64}
        new_owner = {"id": "c"*32, "page": "voice", "candidate": "b"*64}
        self.lifecycle.current_common_owner = dict(old_owner)
        self.lifecycle.capture_previous_native_common_apply = (
            lambda: dict(self.lifecycle.current_common_owner))
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
            self.lifecycle.current_common_owner = dict(new_owner)
        self.lifecycle.start_trial_native_common_apply = actual_native_gui_compiler_and_start

        def restore_original_native_common_owner(witness):
            self.assertEqual(witness, old_owner)
            # This is a mock of the future original-owner restoration route,
            # not a production common Apply executor. Resource bytes must
            # already be back before that route is allowed to restart.
            self.assertEqual((self.root / "lua/orphan.lua").read_bytes(),
                             b"orphaned bytes")
            self.assertEqual((self.root / "files/fake/user_dynamic.bin").read_bytes(),
                             b"unmanaged existing bytes")
            self.lifecycle.native_restore_calls = (
                getattr(self.lifecycle, "native_restore_calls", 0) + 1
            )
            self.lifecycle.current_common_owner = dict(old_owner)
            self.lifecycle.start()
        self.lifecycle.restore_previous_native_common_apply = restore_original_native_common_owner

    def interrupted_pre_stop_trial(self):
        """Simulate power loss after PREPARED durability, before any Stop."""
        plan, config = self.removal_plan()
        self.trial_route()
        old_capture = self.lifecycle.capture_previous_native_common_apply
        calls = 0
        def crash_at_recheck():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt("power loss before original Stop")
            return old_capture()
        self.lifecycle.capture_previous_native_common_apply = crash_at_recheck
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertEqual(self.lifecycle.stops, 0)
        journal = self.state / "transaction/journal.json"
        self.assertEqual(json.loads(journal.read_text())["phase"], "prepared")
        return journal

    def test_remove_prepared_cold_recovery_proves_unmodified_live_owner(self):
        journal = self.interrupted_pre_stop_trial()
        original = self.inode_metadata(self.root / "lua/orphan.lua")
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "RESTORED")
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertEqual(self.lifecycle.starts, 0)
        self.assertEqual(self.inode_metadata(self.root / "lua/orphan.lua"), original)
        self.assertFalse(journal.exists())

    def test_remove_prepared_cold_recovery_refuses_stopped_owner(self):
        journal = self.interrupted_pre_stop_trial()
        self.lifecycle.running = False
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue(journal.exists())
        self.assertEqual(self.lifecycle.stops, 0)

    def test_remove_prepared_cold_recovery_refuses_foreign_native_owner(self):
        journal = self.interrupted_pre_stop_trial()
        self.lifecycle.capture_previous_native_common_apply = lambda: {
            "id": "c"*32, "page": "voice", "candidate": "b"*64}
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue(journal.exists())
        self.assertEqual(self.lifecycle.stops, 0)

    def test_remove_prepared_cold_recovery_refuses_same_byte_foreign_inode(self):
        journal = self.interrupted_pre_stop_trial()
        original = self.root / "lua/orphan.lua"
        replacement = original.with_name("replacement.tmp")
        replacement.write_bytes(original.read_bytes())
        os.replace(replacement, original)
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue(journal.exists())
        self.assertEqual(self.lifecycle.stops, 0)

    def test_remove_prepared_cold_recovery_refuses_metadata_drift(self):
        self.state.mkdir(parents=True, exist_ok=True)
        installed = self.state / "installed.json"
        installed.write_text(json.dumps({
            "schema": 1, "files": {
                "lua/orphan.lua": tx.sha256(b"orphaned bytes"),
            }
        }))
        journal = self.interrupted_pre_stop_trial()
        installed.write_text(json.dumps({"schema": 1, "files": {}}))
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue(journal.exists())
        self.assertEqual(self.lifecycle.stops, 0)

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

    def test_remove_refuses_missing_original_owner_rollback_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route()
        del self.lifecycle.restore_previous_native_common_apply
        with self.assertRaisesRegex(tx.TransactionError, "native common Apply rollback route"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertTrue((self.root / "lua/orphan.lua").exists())
        self.assertFalse((self.state / "transaction").exists())

    def test_remove_requires_previous_owner_witness_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route()
        del self.lifecycle.capture_previous_native_common_apply
        with self.assertRaisesRegex(tx.TransactionError, "previous-owner witness route"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertFalse((self.state / "transaction").exists())

    def test_remove_rejects_changed_previous_owner_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route()
        calls = 0
        def changed_owner():
            nonlocal calls
            calls += 1
            return {"id": ("a" if calls == 1 else "c")*32,
                    "page": "voice", "candidate": "b"*64}
        self.lifecycle.capture_previous_native_common_apply = changed_owner
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertTrue((self.root / "lua/orphan.lua").exists())
        self.assertTrue((self.state / "transaction/journal.json").exists())

    def test_remove_invalid_previous_owner_fails_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route()
        self.lifecycle.capture_previous_native_common_apply = lambda: {
            "id": "invalid", "page": "voice", "candidate": "b"*64}
        with self.assertRaisesRegex(tx.TransactionError, "invalid previous native common owner"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertEqual(self.lifecycle.stops, 0)
        self.assertFalse((self.state / "transaction").exists())

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

    def test_remove_forced_live_failure_returns_old_native_owner(self):
        self.set_distinct_resource_metadata()
        plan, config = self.removal_plan()
        self.trial_route()
        original = {name: self.inode_metadata(self.root / name) for name
                    in ("lua/orphan.lua", "files/fake/user_dynamic.bin")}
        with self.assertRaisesRegex(tx.TransactionError, "REMOVE_FAILED_RESTORED"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root, self.state,
                self.lifecycle, config=config,
                acceptance_fault="fail-after-quarantine")
        self.assertEqual(self.lifecycle.native_restore_calls, 1)
        self.assertEqual(self.lifecycle.current_common_owner["id"], "a"*32)
        for name, identity in original.items():
            self.assertEqual(self.inode_metadata(self.root / name), identity)
        self.assertFalse((self.state / "transaction").exists())

    def test_remove_owner_interrupt_uses_same_cold_recovery(self):
        plan, config = self.removal_plan()
        self.trial_route()
        with self.assertRaisesRegex(KeyboardInterrupt, "INTERRUPTED"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root, self.state,
                self.lifecycle, config=config,
                acceptance_fault="interrupt-after-quarantine")
        journal = self.state / "transaction/journal.json"
        self.assertEqual(json.loads(journal.read_text())["phase"], "restarting")
        self.assertFalse(self.lifecycle.running)
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "RESTORED")
        self.assertEqual(self.lifecycle.current_common_owner["id"], "a"*32)
        self.assertTrue(self.lifecycle.running)
        self.assertFalse(journal.exists())

    def test_remove_owner_commit_interrupt_after_real_inode_unlink(self):
        """R4 uses a real first committed unlink, not patched cleanup."""
        plan, config = self.removal_plan()
        self.trial_route()
        with self.assertRaisesRegex(KeyboardInterrupt, "AFTER_FIRST_COMMITTED_INODE"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root, self.state,
                self.lifecycle, config=config,
                acceptance_fault="interrupt-after-first-committed-inode")
        journal = self.state / "transaction/journal.json"
        receipt = json.loads(journal.read_text())
        self.assertEqual(receipt["phase"], "committing")
        self.assertEqual(receipt["new_native_owner"]["id"], "c"*32)
        q = self.root / tx.QUARANTINE_NAME
        self.assertFalse((q / "files/fake/user_dynamic.bin").exists())
        self.assertTrue((q / "lua/orphan.lua").is_file())
        self.assertFalse((self.state / "installed.json").exists())
        self.assertTrue(self.lifecycle.running)
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "REMOVED")
        self.assertEqual(self.lifecycle.current_common_owner["id"], "c"*32)
        self.assertFalse(journal.exists())
        self.assertFalse(q.exists())
        self.assertEqual(getattr(self.lifecycle, "native_restore_calls", 0), 0)

    def committed_remove_cut(self):
        """Run real fixture through new-owner commit, crash during inode deletion."""
        plan, config = self.removal_plan()
        self.trial_route()
        def cut_mid_cleanup(root, previous):
            q = root / tx.QUARANTINE_NAME
            (q / "lua/orphan.lua").unlink()
            raise KeyboardInterrupt("power cut after first inode unlinked")
        with patch.object(tx, "_clear_quarantine", cut_mid_cleanup):
            with self.assertRaises(KeyboardInterrupt):
                tx.remove_with_native_trial(
                    plan["witness"]["inventory_sha256"], self.root, self.state,
                    self.lifecycle, config=config)
        journal = self.state / "transaction/journal.json"
        data = json.loads(journal.read_text())
        self.assertEqual(data["phase"], "committing")
        self.assertEqual(data["new_native_owner"]["id"], "c"*32)
        self.assertFalse((self.root / "lua/orphan.lua").exists())
        return journal

    def test_remove_cold_commit_after_partial_deletion_finishes_forward(self):
        journal = self.committed_remove_cut()
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "REMOVED")
        self.assertEqual(self.lifecycle.current_common_owner["id"], "c"*32)
        self.assertFalse(journal.exists())
        self.assertFalse((self.root / tx.QUARANTINE_NAME).exists())
        self.assertFalse((self.root / "files/fake/user_dynamic.bin").exists())

    def test_remove_cold_commit_reboots_only_original_committed_new_owner(self):
        journal = self.committed_remove_cut()
        self.lifecycle.running = False
        original_starts = self.lifecycle.starts
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "REMOVED")
        self.assertEqual(self.lifecycle.starts, original_starts + 1)
        self.assertTrue(self.lifecycle.running)
        self.assertEqual(self.lifecycle.current_common_owner["id"], "c"*32)
        self.assertFalse(journal.exists())

    def test_remove_committing_refuses_foreign_owner_without_destroying_evidence(self):
        journal = self.committed_remove_cut()
        self.lifecycle.current_common_owner = {
            "id": "d"*32, "page": "voice", "candidate": "b"*64}
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue(journal.exists())
        self.assertTrue((self.root / tx.QUARANTINE_NAME /
                         "files/fake/user_dynamic.bin").is_file())

    def test_remove_rejects_illegal_acceptance_fault_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route()
        with self.assertRaisesRegex(tx.TransactionError, "invalid owner-acceptance"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root, self.state,
                self.lifecycle, config=config, acceptance_fault="skip-checks")
        self.assertEqual(self.lifecycle.stops, 0)

    @staticmethod
    def inode_metadata(path):
        observed = path.lstat()
        return (observed.st_dev, observed.st_ino, observed.st_uid,
                observed.st_gid, stat.S_IMODE(observed.st_mode),
                observed.st_mtime_ns)

    def set_distinct_resource_metadata(self):
        for name, mode, timestamp in (
            ("lua/orphan.lua", 0o640, 1680000000123456789),
            ("files/fake/user_dynamic.bin", 0o600, 1690000000234567890),
        ):
            path = self.root / name
            os.chmod(path, mode)
            os.utime(path, ns=(timestamp, timestamp))

    def test_remove_native_gui_apply_failure_restores_every_byte(self):
        self.set_distinct_resource_metadata()
        plan, config = self.removal_plan()
        self.trial_route(fail=True)
        previous = {name: ((self.root / name).read_bytes(),
                           self.inode_metadata(self.root / name))
                    for name in ("lua/orphan.lua", "files/fake/user_dynamic.bin")}
        with self.assertRaisesRegex(tx.TransactionError, "REMOVE_FAILED_RESTORED"):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        self.assertTrue(self.lifecycle.running)
        self.assertEqual(self.lifecycle.stops, 1)
        self.assertEqual(self.lifecycle.starts, 1)
        self.assertEqual(self.lifecycle.native_restore_calls, 1)
        for name, (data, metadata) in previous.items():
            self.assertEqual((self.root / name).read_bytes(), data)
            self.assertEqual(self.inode_metadata(self.root / name), metadata)
        self.assertFalse((self.state / "transaction").exists())
        self.assertFalse((self.root / tx.QUARANTINE_NAME).exists())

    def test_remove_cold_prepared_recovery_skips_legacy_stop(self):
        plan,config=self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"],self.root,
                self.state,self.lifecycle,config=config)
        self.assertFalse(self.lifecycle.running)
        stops=self.lifecycle.stops
        observed=[]
        def prepared(owner):
            observed.append(owner)
            return True
        self.lifecycle.recover_prepared_native_common_apply=prepared
        self.assertEqual(tx.recover(self.root,self.state,self.lifecycle),"RESTORED")
        self.assertEqual(self.lifecycle.stops,stops)
        self.assertEqual(observed,[{"id":"a"*32,"page":"voice","candidate":"b"*64}])
        self.assertTrue(self.lifecycle.running)
        self.assertFalse((self.state/"transaction").exists())

    def test_remove_cold_prepared_refusal_keeps_original_journal(self):
        plan,config=self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"],self.root,
                self.state,self.lifecycle,config=config)
        before=self.lifecycle.stops
        def refuse(owner):
            raise tx.TransactionError("foreign prepared common journal")
        self.lifecycle.recover_prepared_native_common_apply=refuse
        with self.assertRaisesRegex(tx.TransactionError,"RESTORE_FAILED"):
            tx.recover(self.root,self.state,self.lifecycle)
        self.assertEqual(self.lifecycle.stops,before)
        self.assertTrue((self.state/"transaction/journal.json").exists())
        self.assertFalse((self.root/"lua/orphan.lua").exists())

    def test_remove_hard_interrupt_retains_recoverable_journal(self):
        self.set_distinct_resource_metadata()
        plan, config = self.removal_plan()
        self.trial_route(crash=True)
        original = {name: self.inode_metadata(self.root / name)
                    for name in ("lua/orphan.lua", "files/fake/user_dynamic.bin")}
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        journal = self.state / "transaction/journal.json"
        self.assertTrue(journal.is_file())
        state = json.loads(journal.read_text())
        self.assertEqual(state["native_owner"], {
            "id": "a"*32, "page": "voice", "candidate": "b"*64})
        self.assertEqual(set(state["original_inodes"]), set(original))
        self.assertTrue((self.root / tx.QUARANTINE_NAME).is_dir())
        self.assertFalse((self.root / "lua/orphan.lua").exists())
        self.assertEqual(tx.recover(self.root, self.state, self.lifecycle), "RESTORED")
        self.assertEqual(self.lifecycle.stops, 1)
        self.assertTrue((self.root / "lua/orphan.lua").is_file())
        self.assertTrue((self.root / "files/fake/user_dynamic.bin").is_file())
        for name, metadata in original.items():
            self.assertEqual(self.inode_metadata(self.root / name), metadata)
        self.assertFalse((self.root / tx.QUARANTINE_NAME).exists())
        self.assertTrue(self.lifecycle.running)

    def test_remove_missing_quarantined_inode_refuses_fake_byte_rollback(self):
        plan, config = self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        original = self.root / tx.QUARANTINE_NAME / "lua/orphan.lua"
        original.unlink()  # backup bytes remain, but metadata/inode are lost
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue((self.state / "transaction/journal.json").exists())
        self.assertTrue((self.state / "transaction/backup/lua/orphan.lua").is_file())
        self.assertFalse(self.lifecycle.running)

    def test_remove_replaced_identical_bytes_inode_fails_closed(self):
        plan, config = self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        original = self.root / tx.QUARANTINE_NAME / "lua/orphan.lua"
        body = original.read_bytes()
        replacement = original.with_name("replacement.tmp")
        replacement.write_bytes(body)
        os.replace(replacement, original)  # same SHA256, guaranteed different inode
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertTrue((self.state / "transaction/journal.json").exists())
        self.assertFalse(self.lifecycle.running)

    def test_remove_missing_original_inode_witness_refuses_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        journal = self.state / "transaction/journal.json"
        record = json.loads(journal.read_text())
        record.pop("original_inodes")
        journal.write_text(json.dumps(record))
        stops = self.lifecycle.stops
        with self.assertRaisesRegex(tx.TransactionError, "original Remove inode witnesses"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertEqual(self.lifecycle.stops, stops)
        self.assertTrue(journal.exists())

    def test_interrupted_remove_refuses_unqualified_recovery_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        # Once native common Apply is possible, it is not safe to fall back
        # to a general Start, even if extra files are recoverable.
        del self.lifecycle.restore_previous_native_common_apply
        stopped_before = self.lifecycle.stops
        with self.assertRaisesRegex(tx.TransactionError, "RESTORE_FAILED"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertEqual(self.lifecycle.stops, stopped_before)
        self.assertTrue((self.state / "transaction/journal.json").is_file())
        self.assertFalse((self.root / "lua/orphan.lua").exists())

    def test_remove_tampered_owner_blocks_recovery_before_stop(self):
        plan, config = self.removal_plan()
        self.trial_route(crash=True)
        with self.assertRaises(KeyboardInterrupt):
            tx.remove_with_native_trial(
                plan["witness"]["inventory_sha256"], self.root,
                self.state, self.lifecycle, config=config)
        journal = self.state / "transaction/journal.json"
        record = json.loads(journal.read_text())
        record["native_owner"]["candidate"] = "invalid"
        journal.write_text(json.dumps(record))
        stopped = self.lifecycle.stops
        with self.assertRaisesRegex(tx.TransactionError, "invalid previous native common owner"):
            tx.recover(self.root, self.state, self.lifecycle)
        self.assertEqual(stopped, self.lifecycle.stops)
        self.assertTrue(journal.exists())

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
        # No-resource no-op needs no trial/rollback callback and no Stop.
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
