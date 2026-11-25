#!/usr/bin/env python3
"""TZ6v5 S10b2b2b3a: genuine schema3 bound PREPARED + old runtime inspection.

Current new candidate and one journal are genuine original P2e/S08c/S08d/
Voice/schema3 fixtures. Old native physical reader is the UNMODIFIED original
examine_shared() in production; here its returned read-only states are injected
to exercise the boundary, NEVER claimed as installed old process/IPFW proof.
"""
from __future__ import annotations

from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from shared_apply_operation import SharedApplyOperation, SharedOperationError
from neutral_root_stage import _stage_candidate
from neutral_schema3_physical_refs import _attest_physical_schema3
import neutral_schema3_previous_preimage as previous
from neutral_schema3_previous_preimage import OriginalPredecessorRefused

spec = importlib.util.spec_from_file_location(
    "original_s10b2b1_predecessor_fixture",
    ROOT / "scripts/test-tz6v5-s10b2b1-original-schema3-preimage.py")
if spec is None or spec.loader is None:
    raise RuntimeError("GENUINE_ORIGINAL_P2E_FIXTURE_MISSING")
src = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src)


class OriginalSchema3PreviousReadOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src.GenuineNativePromotedS10b2b1.setUpClass()

    @classmethod
    def tearDownClass(cls):
        src.GenuineNativePromotedS10b2b1.tearDownClass()

    def setUp(self):
        self.f = src.GenuineNativePromotedS10b2b1("runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.old = {
            "id": "f" * 32 if self.f.generation != "f" * 32 else "e" * 32,
            "page": "strategies", "base": "9" * 64,
            "candidate": self.f.detail["base"], "changed_fields": [],
        }

    def prepare_with_previous(self):
        # Seed ONE original journal's former committed phase, then invoke
        # its original protected PREPARED transition. No external witness.
        self.f.original._persist_record({
            "schema": 1, "phase": "committed", "detail": self.old})
        self.f.original.advance("prepared", self.f.detail)
        self.assertEqual(self.f.original.read()["previous"], self.old)

    def stage_and_bind(self):
        f = self.f
        native = _attest_physical_schema3(
            generation=f.generation, native=f.native,
            effective=f.effective, enabled=True,
            parent=f.parent, journal_root=f.journal_root,
            owner_uid=os.geteuid())
        _stage_candidate(
            generation=f.generation, candidate=native.candidate,
            effective=f.effective, native=f.native,
            mode="auto", enabled=True, parent=f.parent,
            journal_root=f.journal_root, owner_uid=os.geteuid(),
            schema3=True)
        with patch("voice_ipfw_adapter.require_lifecycle_lock",
                   return_value=None):
            f.original.bind_prepared_manifest(
                f.generation, effective=f.effective, native=f.native,
                mode="auto", enabled=True,
                shared_work_parent=f.parent, schema3=True)
        return native.candidate

    def attest(self):
        f = self.f
        return previous._attest_prepared_previous(
            generation=f.generation, native=f.native,
            effective=f.effective, enabled=True,
            parent=f.parent, journal_root=f.journal_root,
            owner_uid=os.geteuid())

    def observed(self, state="ready", **changes):
        running = state == "ready"
        old = self.old
        base = {
            "source": "native-common", "can_activate": False,
            "state": state, "config_digest": old["candidate"],
            "condition": ("common-runtime-and-ipfw-verified" if running
                          else "common-runtime-stopped"),
            "rule_count": 5 if running else 0,
            "table_count": 2 if running else 0,
            "runtime": {
                "state": "running" if running else "stopped",
                "source_verified": True,
                "engine_verified": running,
                "supervisor_verified": running,
            },
        }
        base.update(changes)
        return base

    def test_genuine_current_root_and_old_original_ready_double_readonly(self):
        self.prepare_with_previous()
        candidate = self.stage_and_bind()
        pinned = self.f.original.read()
        hits = []
        def witness(record, *, work_root):
            hits.append((record, work_root))
            return self.observed()
        with patch.object(previous, "examine_shared", side_effect=witness):
            receipt = self.attest()
        self.assertEqual(len(hits), 2)
        for record, parent in hits:
            self.assertEqual(record, {
                "schema": 1, "phase": "committed", "detail": self.old})
            self.assertEqual(parent, self.f.parent)
        self.assertEqual(receipt.root_sha256, candidate.sha256)
        self.assertEqual(receipt.previous_generation, self.old["id"])
        self.assertEqual(receipt.previous_candidate_sha256, self.old["candidate"])
        self.assertEqual(receipt.observed_previous_state, "ready")
        self.assertEqual((receipt.previous_rule_count, receipt.previous_table_count),
                         (5, 2))
        self.assertEqual(receipt.authorization, "NONE")
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertFalse(receipt.promotion_allowed)
        self.assertTrue(receipt.saved_config_required)
        self.assertTrue(receipt.saved_wan_required)
        self.assertTrue(receipt.complete_active_root_required)
        self.assertTrue(receipt.original_pid_birth_epoch_required)
        self.assertEqual(self.f.original.read(), pinned)
        self.assertEqual(self.f.original.read()["phase"], "prepared")
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.f.original.advance("activating", self.f.detail)

    def test_existing_original_inspector_stopped_state_only_if_empty_ipfw(self):
        self.prepare_with_previous()
        self.stage_and_bind()
        with patch.object(previous, "examine_shared",
                          return_value=self.observed("stopped")) as obs:
            receipt = self.attest()
        self.assertEqual(receipt.observed_previous_state, "stopped")
        self.assertEqual(receipt.previous_rule_count, 0)
        self.assertEqual(obs.call_count, 2)
        with patch.object(previous, "examine_shared", return_value=self.observed(
                "stopped", rule_count=1)):
            with self.assertRaises(OriginalPredecessorRefused):
                self.attest()

    def test_no_previous_committed_owner_never_implies_empty_kernel(self):
        self.stage_and_bind()
        with patch.object(previous, "examine_shared") as inspector:
            with self.assertRaises(OriginalPredecessorRefused):
                self.attest()
            inspector.assert_not_called()

    def test_unbound_and_wrong_schema_and_finished_phase_refuse(self):
        self.prepare_with_previous()
        with self.assertRaises(OriginalPredecessorRefused):
            self.attest()
        self.stage_and_bind()
        self.f.original.recover_prepared(
            self.f.generation, lambda: True, shared_work_parent=self.f.parent)
        with self.assertRaises(OriginalPredecessorRefused):
            self.attest()

    def test_base_mismatch_or_foreign_previous_refused(self):
        self.prepare_with_previous()
        self.stage_and_bind()
        saved = self.f.original.read()
        for bad in (
            {**self.old, "candidate": "8" * 64},
            {**self.old, "id": self.f.generation},
        ):
            with self.subTest(bad=bad):
                record = {**saved, "previous": bad}
                if bad["id"] == self.f.generation:
                    with self.assertRaises(SharedOperationError):
                        self.f.original._persist_record(record)
                else:
                    self.f.original._persist_record(record)
                    with self.assertRaises(OriginalPredecessorRefused):
                        self.attest()
                    self.f.original._persist_record(saved)

    def test_foreign_partial_drifted_original_inspector_never_ready(self):
        self.prepare_with_previous()
        self.stage_and_bind()
        negatives = (
            self.observed(state="interrupted"),
            self.observed(can_activate=True),
            self.observed(config_digest="7" * 64),
            self.observed(source="foreign"),
            self.observed(runtime={
                "state": "running", "source_verified": False,
                "engine_verified": True, "supervisor_verified": True}),
            self.observed(runtime={
                "state": "running", "source_verified": True,
                "engine_verified": True, "supervisor_verified": False}),
            self.observed(rule_count=True),
            self.observed(condition="common-runtime-stopped"),
            self.observed("stopped", table_count=1),
        )
        for entry in negatives:
            with self.subTest(entry=entry):
                with patch.object(previous, "examine_shared", return_value=entry):
                    with self.assertRaises(OriginalPredecessorRefused):
                        self.attest()

    def test_old_kernel_changes_between_both_readonly_observations(self):
        self.prepare_with_previous()
        self.stage_and_bind()
        with patch.object(previous, "examine_shared", side_effect=(
                self.observed(), self.observed(rule_count=4))):
            with self.assertRaises(OriginalPredecessorRefused):
                self.attest()

    def test_pending_journal_changed_during_old_process_inspection(self):
        self.prepare_with_previous()
        self.stage_and_bind()
        def injected_old(record, *, work_root):
            # Simulated external writer/race, never an allowed recovery.
            self.f.original._persist_record({**self.f.original.read(), "phase": "restored"})
            return self.observed()
        with patch.object(previous, "examine_shared", side_effect=injected_old):
            with self.assertRaises(OriginalPredecessorRefused):
                self.attest()
        self.assertEqual(self.f.original.read()["phase"], "restored")

    def test_staged_final_args_tampered_old_inspector_not_called(self):
        self.prepare_with_previous()
        self.stage_and_bind()
        argv = self.f.release / "dvtws.args"
        original = argv.read_bytes()
        try:
            argv.write_bytes(original + b" ")
            with patch.object(previous, "examine_shared") as inspector:
                with self.assertRaises(OriginalPredecessorRefused):
                    self.attest()
                inspector.assert_not_called()
        finally:
            argv.write_bytes(original)

    def test_original_fd9_public_wrapper_missing_never_reads_kernel(self):
        self.prepare_with_previous()
        self.stage_and_bind()
        with patch.object(previous, "require_lifecycle_lock",
                          side_effect=RuntimeError("not root FD9")), \
             patch.object(previous, "examine_shared") as inspector:
            with self.assertRaisesRegex(OriginalPredecessorRefused, "FD9"):
                previous.attest_prepared_previous_under_fd9(
                    generation=self.f.generation, native=self.f.native,
                    effective=self.f.effective, enabled=True)
            inspector.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
