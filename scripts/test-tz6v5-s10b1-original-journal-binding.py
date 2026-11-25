#!/usr/bin/env python3
"""S10b1: exact original PREPARED journal pins S10a root, never activates.

Portable S0 may use local stubs for native-only modules. GitHub Actions
runs this unchanged test with the actual original SharedApplyOperation and
S09/S10a modules, plus the existing real P2e/S08c source tests.
"""
from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from shared_apply_operation import (SharedApplyOperation, SharedOperationError,
                                    _validate_manifest_binding, _validate_record,
                                    committed_manifest, native_lifecycle_gate)
from neutral_root_stage import (PreparedRootReceipt, RootStageRefused)

_spec = importlib.util.spec_from_file_location(
    "s10b1_s10a_original_fixture", ROOT / "scripts/test-tz6v5-s10a-root-stage.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("ORIGINAL_S10A_FIXTURE_MISSING")
_prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_prior)


class OriginalDurableRootBinding(unittest.TestCase):
    def setUp(self):
        self.case = _prior.OriginalPreparedS10a("runTest")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.candidate = self.case.candidate()
        self.case.stage(self.candidate)
        self.owner = self.case.original_journal
        self.before = self.owner.read()
        self.assertEqual(self.before["phase"], "prepared")
        self.assertNotIn("manifest", self.before)

    def bind(self, **changes):
        args = dict(generation=self.case.detail["id"],
                    effective=self.case.fx.effective,
                    native=self.case.fx.native,
                    mode=self.case.fx.mode,
                    enabled=False,
                    shared_work_parent=self.case.fx.parent)
        args.update(changes)
        # The public method is FD9-only; the disposable unit substitutes
        # the original adapter's FreeBSD FD9 proof, not a lock/writer.
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            return self.owner.bind_prepared_manifest(**args)

    def test_exact_seal_root_and_original_candidate_single_journal_bind(self):
        files = {str(path.relative_to(self.case.fx.parent)): path.read_bytes()
                 for path in self.case.fx.parent.rglob("*") if path.is_file()}
        result = self.bind()
        metadata = result["manifest"]
        self.assertEqual(metadata["generation"], self.case.detail["id"])
        self.assertEqual(metadata["root_sha256"], self.candidate.sha256)
        self.assertEqual(metadata["candidate_sha256"], self.case.detail["candidate"])
        self.assertEqual(metadata["seal_sha256"], self.case.attest().original_seal_sha256)
        self.assertEqual(result["phase"], "prepared")
        self.assertEqual(result["detail"], self.case.detail)
        self.assertEqual(self.owner.read(), result)
        for name, before in files.items():
            if not name.startswith("journal/"):
                self.assertEqual((self.case.fx.parent / name).read_bytes(), before)
        self.assertNotIn("found", result)
        self.assertFalse((self.case.fx.release / "manifest.json").exists())

    def test_replay_cannot_rebind_or_overwrite(self):
        bound = self.bind()
        with self.assertRaisesRegex(SharedOperationError, "PREPARED unbound"):
            self.bind()
        self.assertEqual(bound, self.owner.read())

    def test_no_fd9_refuses_before_durable_write(self):
        with patch("voice_ipfw_adapter.require_lifecycle_lock",
                   side_effect=RuntimeError("test no FD9")):
            with self.assertRaisesRegex(SharedOperationError, "original FD9"):
                self.owner.bind_prepared_manifest(
                    generation=self.case.detail["id"],
                    effective=self.case.fx.effective,
                    native=self.case.fx.native,
                    mode="list", enabled=False,
                    shared_work_parent=self.case.fx.parent)
        self.assertEqual(self.owner.read(), self.before)

    def test_wrong_generation_mode_enabled_native_refuse(self):
        from dataclasses import replace as dc_replace
        for delta in (dict(generation="f" * 32), dict(mode="auto"),
                      dict(enabled=True),
                      dict(native=dc_replace(self.case.fx.native,
                                             original_args_sha256="f" * 64))):
            with self.subTest(delta=delta):
                with self.assertRaises(SharedOperationError):
                    self.bind(**delta)
                self.assertEqual(self.owner.read(), self.before)

    def test_modified_root_refuses_without_journal_mutation(self):
        root = self.case.fx.work / "manifest.json"
        root.write_bytes(self.candidate.json_bytes + b" ")
        with self.assertRaisesRegex(SharedOperationError, "staged root"):
            self.bind()
        self.assertEqual(self.owner.read(), self.before)

    def test_modified_original_release_refuses_before_bind(self):
        (self.case.fx.release / "dvtws.args").write_bytes(self.case.fx.args + b"tampered")
        with self.assertRaises(SharedOperationError):
            self.bind()
        self.assertEqual(self.owner.read(), self.before)

    def test_unbound_original_prepared_can_move_as_before_no_new_owner(self):
        unchanged = self.owner.advance("activating", self.case.detail)
        self.assertNotIn("manifest", unchanged)
        with self.assertRaisesRegex(SharedOperationError, "PREPARED unbound"):
            self.bind()

    def test_bound_prepared_cannot_enter_activating_and_can_restore(self):
        bound = self.bind()
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.owner.advance("activating", self.case.detail)
        self.assertEqual(self.owner.read(), bound)
        restored = self.owner.recover_prepared(
            self.case.detail["id"], lambda: True,
            shared_work_parent=self.case.fx.parent)
        self.assertEqual(restored["phase"], "restored")
        self.assertEqual(restored["manifest"], bound["manifest"])
        self.assertEqual(self.owner.read(), restored)
        with self.assertRaises(SharedOperationError):
            self.bind()


    def test_restored_candidate_pin_is_not_active_owner_pin(self):
        bound = self.bind()
        restored = self.owner.recover_prepared(
            self.case.detail["id"], lambda: True,
            shared_work_parent=self.case.fx.parent)
        self.assertIsNone(committed_manifest(restored))
        fresh = {**self.case.detail, "id": "e" * 32}
        self.assertNotEqual(fresh["id"], self.case.detail["id"])
        prepared = self.owner.advance("prepared", fresh)
        self.assertNotIn("previous_manifest", prepared)
        self.assertNotIn("manifest", prepared)

    def test_future_committed_pin_survives_successor_and_exact_abort(self):
        bound = self.bind()
        # Simulate the future accepted terminal owner only in the disposable
        # original WAL fixture. Production bound activation remains fenced.
        committed = self.owner._persist_record({**bound, "phase": "committed"})
        self.assertEqual(committed_manifest(committed), bound["manifest"])
        self.assertFalse(native_lifecycle_gate("common-apply",
                         root=self.owner.root)["safe_to_mutate"])
        self.assertFalse(native_lifecycle_gate("strategy-lab-native",
                         root=self.owner.root)["safe_to_mutate"])
        fresh = {**self.case.detail, "id": "e" * 32,
                 "base": self.case.detail["candidate"]}
        prepared = self.owner.advance("prepared", fresh)
        self.assertEqual(prepared["previous"], committed["detail"])
        self.assertEqual(prepared["previous_manifest"], bound["manifest"])
        self.assertIsNone(committed_manifest(prepared))
        with self.assertRaises(SharedOperationError):
            self.owner.advance("activating", fresh)
        with self.assertRaises(SharedOperationError):
            self.owner.advance("restored", fresh)
        path = self.case.fx.work / "manifest.json"
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(SharedOperationError, "recovery pin"):
            self.owner.recover_prepared(fresh["id"], lambda: True,
                                       shared_work_parent=self.case.fx.parent)
        self.assertEqual(self.owner.read(), prepared)
        path.write_bytes(original)
        restored = self.owner.recover_prepared(
            fresh["id"], lambda: True, shared_work_parent=self.case.fx.parent)
        self.assertEqual(restored["phase"], "restored")
        self.assertEqual(committed_manifest(restored), bound["manifest"])
        self.assertEqual(restored["previous_manifest"], bound["manifest"])
        self.assertFalse(native_lifecycle_gate("common-apply",
                         root=self.owner.root)["safe_to_mutate"])
        third = self.owner.advance("prepared", {**fresh, "id": "f" * 32})
        self.assertEqual(third["previous"], committed["detail"])
        self.assertEqual(third["previous_manifest"], bound["manifest"])

    def test_predecessor_pin_is_bound_to_exact_previous_detail(self):
        bound = self.bind()
        prior = self.owner._persist_record({**bound, "phase": "committed"})
        fresh = {**self.case.detail, "id": "e" * 32}
        prepared = self.owner.advance("prepared", fresh)
        for bad in (
                {k: v for k, v in prepared.items() if k != "previous"},
                {**prepared, "previous_manifest": {**bound["manifest"],
                                                  "generation": fresh["id"]}},
                {**prepared, "previous_manifest": {**bound["manifest"],
                                                  "candidate_sha256": "f" * 64}},
                {**prepared, "phase": "activating"},
                {**prepared, "found": {}},
        ):
            with self.assertRaises(SharedOperationError):
                _validate_record(bad)
        self.assertEqual(self.owner.read(), prepared)

    def test_bound_predecessor_cannot_enter_legacy_found_writer(self):
        bound = self.bind()
        previous = self.owner._persist_record({**bound, "phase": "committed"})
        fresh = {**self.case.detail, "id": "e" * 32,
                 "base": self.case.detail["candidate"]}
        plan = json.dumps({
            "result": "prepared", "page": "strategies",
            "dependencies": fresh["base"],
            "found_intent": {"config_revision": fresh["base"],
                             "commit_authorized": False},
            "found_batch": {name: {} for name in ("youtube", "user", "auto")}
        }).encode()
        def forbidden(_):
            self.fail("legacy Found attestation called for immutable predecessor")
        with self.assertRaisesRegex(SharedOperationError, "bound Found preflight"):
            self.owner.prepare_found(fresh, plan, forbidden, runtime_mode="1")
        self.assertEqual(self.owner.read(), previous)

    def test_terminal_selector_distinguishes_two_generation_pins(self):
        bound = self.bind()
        old = self.owner._persist_record({**bound, "phase": "committed"})
        fresh = {**self.case.detail, "id": "e" * 32,
                 "candidate": "c" * 64}
        pending = self.owner.advance("prepared", fresh)
        # Synthetic metadata for selection only, not a second physical proof.
        new_pin = {**bound["manifest"], "generation": fresh["id"],
                   "candidate_sha256": fresh["candidate"], "root_sha256": "b" * 64}
        both = {**pending, "manifest": new_pin}
        self.assertIsNone(committed_manifest(both))
        self.assertEqual(committed_manifest({**both, "phase": "committed"}), new_pin)
        self.assertEqual(committed_manifest({**both, "phase": "restored"}), old["manifest"])


    def test_record_validation_rejects_manifest_forgery_and_found_mix(self):
        bound = self.bind()
        _validate_record(bound)
        for mutation in (dict(root_sha256="f"),
                         dict(generation="f" * 32),
                         dict(candidate_sha256="f" * 64),
                         dict(schema=True),
                         dict(foreign="a")):
            with self.subTest(mutation=mutation):
                record = dict(bound)
                record["manifest"] = {**bound["manifest"], **mutation}
                with self.assertRaises(SharedOperationError):
                    _validate_record(record)
        mixed = dict(bound)
        mixed["found"] = {}
        with self.assertRaises(SharedOperationError):
            _validate_record(mixed)

    def test_post_bind_reattest_failure_keeps_durable_prepared_refusal(self):
        import neutral_root_stage as staged
        real = staged.attest_staged_candidate
        seen = []
        def crash_after_fsync(**kwargs):
            receipt = real(**kwargs)
            seen.append(True)
            if len(seen) == 2:
                raise RootStageRefused("simulated post-fsync power cut")
            return receipt
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None), \
             patch.object(staged, "attest_staged_candidate", side_effect=crash_after_fsync):
            with self.assertRaisesRegex(SharedOperationError, "post-bind"):
                self.owner.bind_prepared_manifest(
                    generation=self.case.detail["id"],
                    effective=self.case.fx.effective,
                    native=self.case.fx.native,
                    mode="list", enabled=False,
                    shared_work_parent=self.case.fx.parent)
        self.assertEqual(seen, [True, True])
        pending = self.owner.read()
        self.assertEqual(pending["phase"], "prepared")
        self.assertEqual(pending["manifest"]["root_sha256"], self.candidate.sha256)
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.owner.advance("activating", self.case.detail)

    def test_wrong_source_receipt_non_authorizing_only(self):
        receipt = PreparedRootReceipt(self.case.detail["id"],
                                      self.candidate.sha256,
                                      "a" * 64,
                                      self.case.detail["candidate"])
        for wrong in (replace(receipt, authorization="ACTIVATE"),
                      replace(receipt, physical_transition_allowed=True),
                      replace(receipt, promotion_allowed=True),
                      replace(receipt, reattest_under_original_fd9=False),
                      replace(receipt, original_candidate_sha256="f" * 64)):
            with self.subTest(wrong=wrong):
                with patch("voice_ipfw_adapter.require_lifecycle_lock",
                           return_value=None), patch(
                        "neutral_root_stage.attest_staged_candidate", return_value=wrong):
                    with self.assertRaises(SharedOperationError):
                        self.owner.bind_prepared_manifest(
                            generation=self.case.detail["id"],
                            effective=self.case.fx.effective,
                            native=self.case.fx.native,
                            mode="list", enabled=False,
                            shared_work_parent=self.case.fx.parent)
                self.assertEqual(self.owner.read(), self.before)


if __name__ == "__main__":
    unittest.main()
