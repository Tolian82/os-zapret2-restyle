#!/usr/bin/env python3
"""Real bound schema3 root + stopped/cold source contracts, no native install."""
from contextlib import ExitStack
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import neutral_schema3_quiescent_preimage as gate
from shared_apply_operation import SharedOperationError
from voice_firewall_transaction import VoiceFirewallError

spec = importlib.util.spec_from_file_location(
    "original_full_prior", ROOT / "scripts/test-tz6v5-s10b2b2b3b2a-original-prior-full-tree-pid.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_PRIOR_FIXTURE_REQUIRED")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OriginalQuiescentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.FullPreviousOwnerReadOnly.setUpClass()

    @classmethod
    def tearDownClass(cls):
        m.FullPreviousOwnerReadOnly.tearDownClass()

    def setUp(self):
        self.fixture = m.FullPreviousOwnerReadOnly("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture.f.f.f
        self.active = self.fixture.active
        self.root = Path(self.f.tmp.name)
        self.backups = self.root / "backups"
        self.producer = self.root / "producer"
        self.epochs = self.root / "epochs"
        self.pidfiles = (self.fixture.pidfile, self.fixture.monitorfile,
                         self.root / "daemon.pid")
        self.saved = replace(self.fixture.saved, previous_state="stopped")
        self.config = self.fixture.f.config(self.f.generation, self.f.detail["page"])
        self.runner = Mock(return_value=Mock(
            returncode=0, stderr="", stdout="0 [kernel]\n1 /sbin/init\n123 /bin/sh\n"))
        self.adapter = Mock(spec=["rule_base", "rule_max", "list_rules", "get_table"])
        self.adapter.rule_base = 19000
        self.adapter.rule_max = 19099
        self.adapter.list_rules.return_value = {}
        self.adapter.get_table.return_value = None

    def call(self):
        return gate._attest_quiescent(
            generation=self.f.generation, native=self.f.native,
            effective=self.f.effective, enabled=True, parent=self.f.parent,
            journal_root=self.f.journal_root, owner_uid=os.geteuid(),
            active=self.active, backups=self.backups, producer=self.producer,
            epochs=self.epochs, pidfiles=self.pidfiles, runner=self.runner)

    def native_seams(self, stack, *, cold_kernel=False):
        stack.enter_context(patch.object(gate, "_native_preflight", return_value=self.config))
        stack.enter_context(patch.object(gate, "_native_wan", return_value="tun0"))
        stack.enter_context(patch.object(gate, "_attest_saved_wan", return_value=self.saved))
        stack.enter_context(patch.object(gate, "_ipfw_kernel_confirmed_absent",
                                         return_value=cold_kernel))
        stack.enter_context(patch.object(gate, "FreeBSDIPFWAdapter",
                                         return_value=self.adapter))
        return stack.enter_context(patch.object(gate, "_native_call",
                                  return_value=b"auto-detect-retire=ready\n"))

    def cold(self):
        shutil.rmtree(self.active)
        shutil.rmtree(self.fixture.old_work)
        record = self.f.original.read()
        record.pop("previous")
        self.f.original._persist_record(record)

    def lock(self):
        self.producer.mkdir(mode=0o700)
        lock = self.producer / "worker.lock"
        lock.touch(mode=0o600)
        if os.geteuid() == 0:
            os.chown(lock, 0, 0)
        lock.chmod(0o600)

    def test_real_bound_cold_root_with_actual_empty_manifest_check(self):
        self.cold()
        record = self.f.original.read()
        with ExitStack() as stack:
            retired = self.native_seams(stack)
            receipt = self.call()
            retired.assert_not_called()
        self.assertEqual(receipt.old_state, "first-install-empty")
        self.assertEqual(receipt.kernel_state, "native-managed-kernel-empty")
        self.assertEqual(receipt.retirement_state, "no-prior-data")
        self.assertEqual(receipt.root_sha256, record["manifest"]["root_sha256"])
        self.assertIsNone(receipt.previous_generation)
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertEqual(receipt.authorization, "NONE")
        self.adapter.list_rules.assert_called_with(19000, 19099)
        self.assertEqual(self.f.original.read(), record)
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.f.original.advance("activating", self.f.detail)

    def test_cold_native_absent_kernel_never_loads_adapter(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            receipt = self.call()
        self.assertEqual(receipt.kernel_state, "native-kernel-absent")
        self.adapter.list_rules.assert_not_called()

    def test_cold_orphan_rule_or_managed_stage_table_refused(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            self.adapter.list_rules.return_value = {19095: ["foreign"]}
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            self.adapter.list_rules.return_value = {}
            self.adapter.get_table.side_effect = lambda name: (
                ["192.0.2.1"] if name.endswith("_stage") else None)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_no_previous_with_active_tree_is_not_cold(self):
        record = self.f.original.read()
        record.pop("previous")
        self.f.original._persist_record(record)
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_cold_pidfile_foreign_process_and_malformed_census(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            for path in self.pidfiles:
                path.write_text("5432\n")
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
                path.unlink()
            for line in (f"999 {gate.CHILD_EXEC}", f"999 /bin/sh {gate.MONITOR_EXEC}",
                         "999 daemon: supervisor_loop.sh[123] (daemon)",
                         "999 daemon: dvtws2[123] (daemon)", "malformed", "999"):
                self.runner.return_value.stdout = "1 /sbin/init\n" + line + "\n"
                with self.subTest(line=line), self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_cold_residual_producer_epoch_backup_atomic_stage_and_old_work(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack, cold_kernel=True)
            for path in (self.producer, self.epochs, self.backups, self.active,
                         self.f.parent / ("0" * 32)):
                path.mkdir()
                (path / "evidence").touch()
                with self.subTest(path=path.name), self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
                shutil.rmtree(path)
            stage = self.active.parent / (f".{self.active.name}.stage." + "0" * 32)
            stage.mkdir()
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()

    def test_stopped_old_tree_plus_existing_retired_ready_command(self):
        self.lock()
        record = self.f.original.read()
        with ExitStack() as stack:
            cmd = self.native_seams(stack)
            receipt = self.call()
        self.assertEqual(receipt.old_state, "committed-stopped")
        self.assertEqual(receipt.previous_generation, record["previous"]["id"])
        self.assertEqual(receipt.retirement_state, "original-epoch-ack-retired")
        self.assertEqual(cmd.call_count, 2)
        cmd.assert_called_with((str(gate.SCRIPT / "python_runtime.sh"),
            str(gate.SCRIPT / "backend/auto_detect_minute.py"), "--retired-ready"))
        self.assertEqual(record, self.f.original.read())
        self.assertEqual(receipt.authorization, "NONE")

    def test_stopped_native_retirement_must_be_complete_no_lock_creation(self):
        with ExitStack() as stack:
            cmd = self.native_seams(stack)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            cmd.assert_not_called()
            self.assertFalse(self.producer.exists())
            self.lock()
            for response in (b"auto-detect-retire=processed\n",
                             b"auto-detect-retire=idle\n", b"", b"foreign\n"):
                cmd.return_value = response
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_stopped_old_tree_mutation_and_running_refused(self):
        self.lock()
        with ExitStack() as stack:
            self.native_seams(stack)
            (self.active / "tcp-ports.txt").write_bytes(b"tampered\n")
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
        with ExitStack() as stack:
            self.saved = replace(self.saved, previous_state="ready")
            cmd = self.native_seams(stack)
            with self.assertRaises(gate.QuiescentPreimageRefused):
                self.call()
            cmd.assert_not_called()

    def test_second_observation_wan_or_kernel_changed_refused(self):
        self.cold()
        with ExitStack() as stack:
            self.native_seams(stack)
            with patch.object(gate, "_native_wan", side_effect=("tun0", "tun1")):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()
            with patch.object(gate, "_ipfw_kernel_confirmed_absent",
                              side_effect=(True, False)):
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    self.call()

    def test_retired_readonly_native_source_still_uses_repair_false(self):
        minute = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/auto_detect_minute.py"
        text = minute.read_text().split("def native_retired_ready()", 1)[1]
        self.assertIn("repair=False", text)
        self.assertIn("verify_retired(previous, queue)", text)
        self.assertNotIn("retire_stopped(", text)

    def test_public_wrapper_refuses_absent_original_fd9(self):
        with patch.object(gate, "require_lifecycle_lock",
                          side_effect=RuntimeError("no FD9")), \
             patch.object(gate, "_attest_quiescent") as read:
            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "FD9"):
                gate.attest_quiescent_under_fd9(
                    generation=self.f.generation, native=self.f.native,
                    effective=self.f.effective, enabled=True)
            read.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
