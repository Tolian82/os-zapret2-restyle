#!/usr/bin/env python3
"""S10 original journal pins, file CAS and recovery with disposable data.

Portable S0 may use local stubs for native-only modules. GitHub Actions
runs this unchanged test with the actual original SharedApplyOperation and
S09/S10a modules, plus the existing real P2e/S08c source tests.
"""
from __future__ import annotations

from dataclasses import replace
import importlib.util
import hashlib
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

    def test_ordinary_config_save_requires_exact_activated_journal_and_seal(self):
        import auto_detect_effective_known as source

        work = self.case.fx.work
        root = work / "manifest.json"
        root.unlink()
        detail = self.case.detail
        plan = work / "plan.json"
        plan_bytes = plan.read_bytes()
        parts = [detail["page"], detail["base"], detail["candidate"],
                 hashlib.sha256(plan_bytes).hexdigest(), ",".join(detail["changed_fields"])]
        witness = lambda values: hashlib.sha256("\0".join(values).encode("ascii")).hexdigest()
        token = witness(parts)

        def attest(sha=token):
            self.owner.attest_unbound_config_save(detail["id"], sha,
                                                   shared_work_parent=work.parent)

        with self.assertRaisesRegex(SharedOperationError, "unbound activated owner"):
            attest()
        self.owner.advance("activating", detail)
        with self.assertRaisesRegex(SharedOperationError, "unbound activated owner"):
            attest()
        activated = self.owner.advance("activated", detail)
        attest()
        self.assertEqual(self.owner.read(), activated)

        for idx, value in enumerate(("voice", "8" * 64, "9" * 64, "a" * 64, "voice.telegram.enabled")):
            with self.subTest(field=idx):
                changed = parts.copy()
                changed[idx] = value
                with self.assertRaisesRegex(SharedOperationError, "differs from original activation"):
                    attest(witness(changed))

        for path in (root, work / "release" / ".manifest.json.pending"):
            path.symlink_to(work / "missing-root")
            with self.assertRaisesRegex(SharedOperationError, "unbound root artifacts"):
                attest()
            path.unlink()
        from shared_apply_seal import SharedBundleError
        plan.write_bytes(plan_bytes + b" ")
        with self.assertRaises(SharedBundleError):
            attest()
        plan.write_bytes(plan_bytes)

        with patch.object(source.sys, "platform", "freebsd15"), \
             patch.object(source.os, "geteuid", return_value=0), \
             patch("voice_ipfw_adapter.require_lifecycle_lock") as fd9, \
             patch("auto_detect_original_lock_handoff.assert_inherited_config_fd") as fd4, \
             patch("shared_apply_operation.SharedApplyOperation", return_value=self.owner), \
             patch("shared_apply_seal.WORK", work.parent), \
             patch("sys.stdout") as output, patch("sys.stderr"):
            args = ["attest-ordinary-save-locked", detail["id"], token]
            self.assertEqual(source.main(args), 0)
            receipt = json.loads(output.write.call_args_list[0].args[0])
            self.assertEqual(receipt, {"result": "original-ordinary-save-verified", "id": detail["id"]})
            self.assertEqual(fd9.call_count, 2)
            self.assertEqual(fd4.call_count, 2)
            fd4.side_effect = RuntimeError("lost inherited Config lock")
            self.assertEqual(source.main(args), 69)
        self.assertEqual(self.owner.read(), activated)
        self.owner.advance("config-saved", detail)
        with self.assertRaisesRegex(SharedOperationError, "unbound activated owner"):
            attest()


    def test_bound_ordinary_transition_preserves_pins_and_requires_fresh_native_proof(self):
        bound = self.bind()
        root = self.case.fx.work / "manifest.json"
        original = root.read_bytes()
        def advance(phase, expected, attest):
            return self.owner._advance_bound_ordinary(
                phase, expected, attest, shared_work_parent=self.case.fx.parent)

        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            # An exact bound PREPARED record is still not a legacy CLI permit.
            with self.assertRaises(SharedOperationError):
                self.owner.advance("activating", self.case.detail)
            with self.assertRaises(SharedOperationError):
                advance("activating", bound, lambda: False)
            self.assertEqual(self.owner.read(), bound)

            def drift():
                root.write_bytes(original + b" ")
                return True

            with self.assertRaises(SharedOperationError):
                advance("activating", bound, drift)
            self.assertEqual(self.owner.read(), bound)
            root.write_bytes(original)
            # Portable journal evidence only. This callback deliberately
            # substitutes native physical proof; no runtime is started.
            activating = advance("activating", bound, lambda: True)
            self.assertEqual(activating, {**bound, "phase": "activating"})
            with self.assertRaises(SharedOperationError):
                self.owner.advance("activated", self.case.detail)
            with self.assertRaises(SharedOperationError):
                advance("committed", activating, lambda: True)
            with self.assertRaises(SharedOperationError):
                advance("activated", bound, lambda: True)
            activated = advance("activated", activating, lambda: True)
            saved = advance("config-saved", activated, lambda: True)
            with self.assertRaises(SharedOperationError):
                self.owner.finish_saved(self.case.detail["id"], lambda: True)
            # A pre-save restore is allowed by the phase table only with
            # independent proof; a Config-saved rollback is not.
            with self.assertRaises(SharedOperationError):
                advance("restored", saved, lambda: True)
            committed = advance("committed", saved, lambda: True)
            self.assertEqual(committed_manifest(committed), bound["manifest"])
            self.assertEqual(self.owner.read(), committed)
            self.assertFalse(native_lifecycle_gate("common-apply",
                             root=self.owner.root)["safe_to_mutate"])

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

    def _pinned_found_fixture(self, rows=None):
        bound = self.bind()
        old = self.owner._persist_record({**bound, "phase": "committed"})
        fresh = {**self.case.detail, "id": "e" * 32,
                 "base": old["detail"]["candidate"]}
        plan = json.dumps({
            "result": "prepared", "page": "strategies",
            "dependencies": fresh["base"],
            "changed_fields": fresh["changed_fields"], "candidate": {},
            "found_intent": {"config_revision": fresh["base"],
                             "commit_authorized": False},
            "found_batch": ({name: {} for name in ("youtube", "user", "auto")}
                            if rows is None else rows)
        }).encode()
        return bound, old, fresh, plan

    def test_pinned_found_prepared_retains_old_root_but_no_file_action(self):
        bound, old, fresh, plan = self._pinned_found_fixture()
        root = self.case.fx.work / "manifest.json"
        original = root.read_bytes()
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            pending = self.owner.prepare_found(
                fresh, plan, lambda _: True, runtime_mode="1",
                shared_work_parent=self.case.fx.parent)
            self.assertEqual(pending["phase"], "prepared")
            self.assertEqual(pending["previous"], old["detail"])
            self.assertEqual(pending["previous_manifest"], bound["manifest"])
            self.assertNotIn("manifest", pending)
            self.assertEqual(root.read_bytes(), original)
            with self.assertRaises(SharedOperationError):
                self.owner.advance_found_files(
                    "found-files-writing", fresh, plan, lambda *_: True)
            self.assertEqual(self.owner.read(), pending)
            recovered = self.owner.finish_found_prepared_pristine(
                fresh["id"], plan, lambda raw, previous:
                raw == plan and previous == old["detail"],
                shared_work_parent=self.case.fx.parent)
            self.assertEqual(recovered["phase"], "restored")
            self.assertNotIn("found", recovered)
            self.assertEqual(committed_manifest(recovered), bound["manifest"])
            self.assertEqual(root.read_bytes(), original)

    def test_pinned_found_prep_refuses_without_fd9_wrong_base_or_tamper(self):
        _, old, fresh, plan = self._pinned_found_fixture()
        first = self.owner.read()
        with patch("voice_ipfw_adapter.require_lifecycle_lock",
                   side_effect=RuntimeError("no original FD9")):
            with self.assertRaisesRegex(SharedOperationError, "predecessor proof"):
                self.owner.prepare_found(
                    fresh, plan, lambda _: True,
                    shared_work_parent=self.case.fx.parent)
        self.assertEqual(self.owner.read(), first)
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            with self.assertRaisesRegex(SharedOperationError, "previous Config mismatch"):
                wrong = {**fresh, "base": "f" * 64}
                wrong_plan = plan.replace(fresh["base"].encode(), b"f" * 64)
                self.owner.prepare_found(
                    wrong, wrong_plan, lambda _: True,
                    shared_work_parent=self.case.fx.parent)
        self.assertEqual(self.owner.read(), first)
        root = self.case.fx.work / "manifest.json"
        original = root.read_bytes()
        root.write_bytes(original + b"foreign")
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            with self.assertRaisesRegex(SharedOperationError, "predecessor proof"):
                self.owner.prepare_found(
                    fresh, plan, lambda _: True,
                    shared_work_parent=self.case.fx.parent)
        self.assertEqual(self.owner.read(), first)
        root.write_bytes(original)

    def test_pinned_found_recovery_refuses_changed_root_and_mixed_phases(self):
        bound, _, fresh, plan = self._pinned_found_fixture()
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            pending = self.owner.prepare_found(
                fresh, plan, lambda _: True,
                shared_work_parent=self.case.fx.parent)
            root = self.case.fx.work / "manifest.json"
            original = root.read_bytes()
            root.write_bytes(original + b"drift")
            with self.assertRaisesRegex(SharedOperationError, "predecessor pin"):
                self.owner.finish_found_prepared_pristine(
                    fresh["id"], plan, lambda *_: True,
                    shared_work_parent=self.case.fx.parent)
            self.assertEqual(self.owner.read(), pending)
            root.write_bytes(original)
            # Structurally valid wrong hashes pass JSON shape checks, but
            # NEVER pass the independent physical pinned-root recovery.
            substituted = {**pending, "previous_manifest": {
                **bound["manifest"], "root_sha256": "f" * 64}}
            self.owner._persist_record(substituted)
            with self.assertRaisesRegex(SharedOperationError, "predecessor pin"):
                self.owner.finish_found_prepared_pristine(
                    fresh["id"], plan, lambda *_: True,
                    shared_work_parent=self.case.fx.parent)
            self.assertEqual(self.owner.read(), substituted)
            self.owner._persist_record(pending)
            recovered = self.owner.finish_found_prepared_pristine(
                fresh["id"], plan, lambda *_: True,
                shared_work_parent=self.case.fx.parent)
            self.assertEqual(committed_manifest(recovered), bound["manifest"])
            for forged in (
                {**pending, "phase": "found-files-writing"},
                {**pending, "phase": "found-files-written"},
                {**pending, "phase": "found-config-saving"},
                {**pending, "manifest": bound["manifest"]},
                {**pending, "previous_manifest": {
                    **bound["manifest"], "root_sha256": "f"}},
            ):
                with self.subTest(phase=forged.get("phase")):
                    with self.assertRaises(SharedOperationError):
                        _validate_record(forged)

    def _staged_pinned_found_fixture(self, rows=None):
        import hashlib
        import shutil
        from neutral_root_manifest import compile_candidate
        from neutral_root_stage import _stage_candidate
        from shared_apply_seal import create_seal

        old_bound, old, fresh, plan = self._pinned_found_fixture(rows)
        parent = self.case.fx.parent
        work = parent / fresh["id"]
        work.mkdir(mode=0o700)
        shutil.copytree(self.case.fx.release, work / "release")
        shutil.copyfile(self.case.fx.work / "candidate.xml", work / "candidate.xml")
        (work / "plan.json").write_bytes(plan)
        (work / "plan.json").chmod(0o600)
        create_seal(work, owner=self.owner.owner)
        seal_sha = hashlib.sha256((work / "bundle-seal.json").read_bytes()).hexdigest()
        plan_sha = hashlib.sha256(plan).hexdigest()
        candidate = compile_candidate(
            effective=self.case.fx.effective, generation=fresh["id"],
            target_mode="list", enabled=False, original_args=self.case.fx.args,
            original_source_map=None, seal_sha256=seal_sha, owner_uid=self.owner.owner)
        pending = self.owner.prepare_found(
            fresh, plan, lambda _: True, shared_work_parent=parent)
        args = self.case.kw(generation=fresh["id"])
        # Ordinary staging must refuse even the genuine original Found seal.
        with self.assertRaises(RootStageRefused):
            _stage_candidate(candidate=candidate, **args)
        with self.assertRaises(RootStageRefused):
            _stage_candidate(candidate=candidate, **args, found_plan_sha256="0" * 64)
        self.assertEqual(self.owner.read(), pending)
        staged = _stage_candidate(candidate=candidate, **args, found_plan_sha256=plan_sha)
        self.assertEqual(staged.root_sha256, candidate.sha256)
        self.assertEqual(self.owner.read(), pending)
        return old_bound, old, fresh, plan, pending, work, staged, plan_sha

    def test_dual_found_root_binding_and_exact_pristine_recovery(self):
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            old_bound, old, fresh, plan, pending, work, staged, plan_sha = (
                self._staged_pinned_found_fixture())
            with self.assertRaises(SharedOperationError):
                self.bind(generation=fresh["id"])
            with self.assertRaises(SharedOperationError):
                self.bind(generation=fresh["id"], found_plan_sha256="0" * 64)
            self.assertEqual(self.owner.read(), pending)
            bound = self.bind(generation=fresh["id"], found_plan_sha256=plan_sha)
            self.assertEqual(bound["phase"], "prepared")
            self.assertEqual(bound["found"], pending["found"])
            self.assertEqual(bound["previous_manifest"], old_bound["manifest"])
            self.assertEqual(bound["manifest"]["root_sha256"], staged.root_sha256)
            self.assertEqual(bound["manifest"]["generation"], fresh["id"])
            self.assertIsNone(committed_manifest(bound))
            self.assertFalse(native_lifecycle_gate("common-apply",
                            root=self.owner.root)["safe_to_mutate"])
            with self.assertRaises(SharedOperationError):
                self.owner.advance_found_files("found-files-writing",
                                               fresh, plan, lambda *_: True)
            self.assertEqual(self.owner.read(), bound)

            # Reopen the single WAL after an interrupted caller; either
            # physical pin drifting must leave its exact PREPARED intact.
            reopened = SharedApplyOperation(self.owner.root, owner=self.owner.owner)
            for root in (work / "manifest.json", self.case.fx.work / "manifest.json"):
                original = root.read_bytes()
                root.write_bytes(original + b"changed")
                with self.assertRaises(SharedOperationError):
                    reopened.finish_found_prepared_pristine(
                        fresh["id"], plan, lambda *_: True,
                        shared_work_parent=self.case.fx.parent)
                self.assertEqual(reopened.read(), bound)
                root.write_bytes(original)
            restored = reopened.finish_found_prepared_pristine(
                fresh["id"], plan, lambda raw, prior: raw == plan and prior == old["detail"],
                shared_work_parent=self.case.fx.parent)
            self.assertEqual(restored["phase"], "restored")
            self.assertNotIn("found", restored)
            self.assertEqual(restored["manifest"], bound["manifest"])
            self.assertEqual(committed_manifest(restored), old_bound["manifest"])

    def test_bound_found_real_cas_and_rollback_preserve_both_immutable_pins(self):
        import hashlib
        from auto_detect_destination_commit import (
            _locked_shared_found_apply_journal, _recover_found_preimages_locked,
            _bound_found_native_witness)
        root = self.case.fx.parent / "physical-found"
        root.mkdir(mode=0o700)
        targets, rows = {}, {}
        originals = {"youtube": "example.com\n", "user": "example.org\n", "auto": ""}
        after = {"youtube": "example.com\nfresh.com\n", "user": "", "auto": "shared.org\n"}
        for name, old_text in originals.items():
            path = root / (name + ".txt")
            path.write_text(old_text)
            path.chmod(0o600)
            st = path.lstat()
            targets[name] = path
            rows[name] = dict(before=old_text, after=after[name], before_status="present",
                before_revision=hashlib.sha256(b"present\0" + old_text.encode()).hexdigest(),
                before_device=st.st_dev, before_inode=st.st_ino,
                before_ctime_ns=st.st_ctime_ns, before_mtime_ns=st.st_mtime_ns,
                before_size=st.st_size)
        # Test fixture deliberately supplies disposable native lock witnesses;
        # actual manifest/seal verification and file CAS are NOT mocked.
        with patch("voice_ipfw_adapter.require_lifecycle_lock"), \
             patch("shared_apply_seal.WORK", self.case.fx.parent):
            old_bound, _, fresh, raw, _, work, _, plan_sha = (
                self._staged_pinned_found_fixture(rows))
            bound = self.bind(generation=fresh["id"], found_plan_sha256=plan_sha)
            qualified = _bound_found_native_witness(self.owner, bound, lambda: True)

            def apply(witness):
                return _locked_shared_found_apply_journal(
                    rows, targets, store=self.owner, detail=fresh, plan_bytes=raw,
                    uid=self.owner.owner, attest=lambda *_: True, bound_attest=witness)

            with self.assertRaises(SharedOperationError):
                apply(None)
            self.assertEqual(self.owner.read(), bound)
            self.assertEqual({n: p.read_text() for n, p in targets.items()}, originals)

            # A tampered root must fail before the first physical rename.
            sibling = work / "manifest.json"
            original = sibling.read_bytes()
            sibling.write_bytes(original + b"drift")
            with self.assertRaises(SharedOperationError):
                apply(qualified)
            self.assertEqual(self.owner.read(), bound)
            self.assertEqual({n: p.read_text() for n, p in targets.items()}, originals)
            sibling.write_bytes(original)

            self.assertEqual(apply(qualified)["journal_phase"], "found-files-written")
            written = self.owner.read()
            self.assertEqual(written["manifest"], bound["manifest"])
            self.assertEqual(written["previous_manifest"], old_bound["manifest"])
            self.assertEqual({n: p.read_text() for n, p in targets.items()}, after)
            with self.assertRaises(SharedOperationError):
                self.owner.advance_found_config("found-config-saving", fresh, raw,
                                                lambda *_: True)
            saving = self.owner.advance_found_config("found-config-saving", fresh, raw,
                lambda *_: True, bound_attest=qualified)
            self.assertEqual(saving["phase"], "found-config-saving")
            self.assertEqual(saving["manifest"], bound["manifest"])
            # No Config write in this portable test: simulate a proven base
            # from native Config and use the exact same physical rollback.
            reopened = SharedApplyOperation(self.owner.root, owner=self.owner.owner)
            rollback = _bound_found_native_witness(reopened, saving, lambda: True)
            def recover():
                return _recover_found_preimages_locked(
                    rows, targets, store=reopened, record=reopened.read(),
                    plan_bytes=raw, uid=reopened.owner, attest=lambda: True,
                    bound_attest=rollback)
            sibling.write_bytes(original + b"foreign")
            with self.assertRaises(SharedOperationError):
                recover()
            self.assertEqual(reopened.read(), saving)
            self.assertEqual({n: p.read_text() for n, p in targets.items()}, after)
            sibling.write_bytes(original)
            # A crash after the first actual rollback rename leaves the
            # original restore inode pin and both immutable root pins.
            # Reopen the same WAL and resume without adopting foreign bytes.
            rename = os.replace
            def interrupted(temp, target):
                rename(temp, target)
                if Path(target) == targets["auto"]:
                    raise OSError("bound rollback interrupted after rename")
            with patch("auto_detect_destination_commit.os.replace", side_effect=interrupted):
                with self.assertRaisesRegex(OSError, "bound rollback interrupted"):
                    recover()
            interrupted_record = reopened.read()
            self.assertEqual(interrupted_record["phase"], "found-restoring")
            self.assertEqual(interrupted_record["manifest"], bound["manifest"])
            self.assertEqual(interrupted_record["previous_manifest"], old_bound["manifest"])
            restored = recover()
            self.assertEqual(restored["phase"], "restored")
            self.assertNotIn("found", restored)
            self.assertEqual(restored["manifest"], bound["manifest"])
            self.assertEqual(committed_manifest(restored), old_bound["manifest"])
            self.assertEqual({n: p.read_text() for n, p in targets.items()}, originals)

    def test_dual_found_root_interrupted_post_fsync_retains_both_pins(self):
        import neutral_root_stage as stage
        with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
            old_bound, _, fresh, plan, _, work, staged, plan_sha = (
                self._staged_pinned_found_fixture())
            original = stage.attest_staged_candidate
            calls = []
            def interrupted(**kwargs):
                receipt = original(**kwargs)
                calls.append(receipt)
                if len(calls) == 2:
                    raise RootStageRefused("simulated post-fsync failure")
                return receipt
            with patch.object(stage, "attest_staged_candidate", side_effect=interrupted):
                with self.assertRaisesRegex(SharedOperationError, "post-bind"):
                    self.bind(generation=fresh["id"], found_plan_sha256=plan_sha)
            reopened = SharedApplyOperation(self.owner.root, owner=self.owner.owner)
            pending = reopened.read()
            self.assertEqual(len(calls), 2)
            self.assertEqual(pending["phase"], "prepared")
            self.assertEqual(pending["manifest"]["root_sha256"], staged.root_sha256)
            self.assertEqual(pending["previous_manifest"], old_bound["manifest"])
            with self.assertRaises(SharedOperationError):
                reopened.advance_found_files("found-files-writing",
                                             fresh, plan, lambda *_: True)
            restored = reopened.finish_found_prepared_pristine(
                fresh["id"], plan, lambda *_: True,
                shared_work_parent=self.case.fx.parent)
            self.assertEqual(committed_manifest(restored), old_bound["manifest"])

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

    def test_first_running_pin_is_only_first_inert_activated_history(self):
        bound = self.bind()
        first = {k: v for k, v in bound.items() if k not in ("previous", "previous_manifest")}
        pin = "a" * 64
        for phase in ("activated", "config-saved", "committed", "restored"):
            _validate_record({**first, "phase": phase, "first_running_sha256": pin})
        for phase in ("prepared", "activating"):
            with self.assertRaises(SharedOperationError):
                _validate_record({**first, "phase": phase, "first_running_sha256": pin})
        for invalid in ("x", True, None):
            with self.assertRaises(SharedOperationError):
                _validate_record({**first, "phase": "activated", "first_running_sha256": invalid})
        if "previous" in bound:
            with self.assertRaises(SharedOperationError):
                _validate_record({**bound, "phase": "activated", "first_running_sha256": pin})

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


class OriginalManagedFileCAS(unittest.TestCase):
    def fixture(self, *, extra_change=False, equal_config=False):
        import shutil
        from auto_detect_destination_commit import _sha, _target_identity
        from neutral_root_manifest import compile_candidate
        from neutral_root_stage import _stage_candidate
        from shared_apply_seal import create_seal

        case = _prior.OriginalPreparedS10a("runTest")
        case.setUp()
        self.addCleanup(case.doCleanups)
        store, parent = case.original_journal, case.fx.parent
        name = "hostlist-youtube.txt"
        before, after = b"old.example\n", b"new.example\n"
        (case.fx.release / "managed").mkdir()
        old_file = case.fx.release / "managed" / name
        old_file.write_bytes(before)
        case.stage(case.candidate())
        bound = store.bind_prepared_manifest(generation=case.detail["id"],
            effective=case.fx.effective, native=case.fx.native, mode="list",
            enabled=False, shared_work_parent=parent)
        for phase in ("activating", "activated", "config-saved", "committed"):
            bound = store._advance_bound_ordinary(phase, bound, lambda: True,
                                                   shared_work_parent=parent)
        detail = {**case.detail, "id": "e" * 32, "base": case.detail["candidate"],
                  "candidate": case.detail["candidate"] if equal_config else "9" * 64}
        work = parent / detail["id"]
        work.mkdir(mode=0o700)
        shutil.copytree(case.fx.release, work / "release")
        shutil.copyfile(case.fx.work / "candidate.xml", work / "candidate.xml")
        (work / "plan.json").write_text(json.dumps({"result": "prepared",
            "page": detail["page"], "dependencies": detail["base"],
            "changed_fields": [], "candidate": {"general": {"enabled": "0"}}}))
        new_file = work / "release" / "managed" / name
        new_file.write_bytes(after)
        if extra_change:
            (work / "release" / "unrelated.txt").write_text("different tree\n")
        create_seal(work, owner=store.owner)
        candidate = compile_candidate(effective=case.fx.effective, generation=detail["id"],
            target_mode="list", enabled=False, original_args=case.fx.args,
            original_source_map=None, seal_sha256=_sha((work / "bundle-seal.json").read_bytes()),
            owner_uid=store.owner)
        store.advance("prepared", detail)
        _stage_candidate(candidate=candidate, **case.kw(generation=detail["id"]))
        prepared = store.bind_prepared_manifest(generation=detail["id"],
            effective=case.fx.effective, native=case.fx.native, mode="list",
            enabled=False, shared_work_parent=parent)
        active = parent / "runtime-v2"
        shutil.copytree(case.fx.release, active)
        target = active / "managed" / name
        row = (name, _sha(before), _sha(after), *(_target_identity(path.lstat())
                for path in (old_file, new_file, target)))
        return store, prepared, row, parent, active, target, before, after

    def test_original_managed_file_cas_and_interrupted_restore(self):
        from auto_detect_destination_commit import (
            _write_bound_managed_file_locked, _restore_bound_managed_file_locked,
            _target_identity)

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            for interrupted in (False, True):
                with self.subTest(interrupted=interrupted):
                    store, prepared, row, parent, active, target, before, after = self.fixture()
                    kw = dict(parent=parent, active=active, attest=lambda: True)
                    real_replace = os.replace
                    seen = []

                    def replace_file(source, dest, **kwargs):
                        if Path(dest) == target:
                            intent = store.read()
                            self.assertEqual(intent["phase"], "managed-writing")
                            pin = intent["managed"].get("restore", intent["managed"]["ready"])
                            self.assertEqual(Path(source).stat().st_ino, pin["inode"])
                            seen.append(pin["sha256"])
                        result = real_replace(source, dest, **kwargs)
                        if interrupted and Path(dest) == target:
                            raise OSError("interrupted after file rename")
                        return result

                    with patch("os.replace", side_effect=replace_file):
                        if interrupted:
                            with self.assertRaisesRegex(OSError, "interrupted after file rename"):
                                _write_bound_managed_file_locked(store, prepared, row, **kw)
                        else:
                            _write_bound_managed_file_locked(store, prepared, row, **kw)
                    pending = store.read()
                    self.assertEqual(target.read_bytes(), after)
                    self.assertEqual("installed" in pending["managed"], not interrupted)
                    self.assertIn("barrier", pending["managed"])
                    if not interrupted:
                        # Genuine post-WAL full inode proof; reproduces UFS
                        # deferred ctime drift in the original uncorrected writer.
                        self.assertEqual(list(_target_identity(target.lstat())),
                                         pending["managed"]["installed"])
                    token = pending["managed"]["ready"]["temp"][13:-4]
                    self.assertEqual((active.parent / (".s10-managed-barrier-" + token)).exists(), interrupted)
                    self.assertFalse(native_lifecycle_gate("common-recover-activating",
                        root=store.root)["safe_to_mutate"])
                    with self.assertRaises(SharedOperationError):
                        store.advance("activated", prepared["detail"])
                    with self.assertRaises(SharedOperationError):
                        store.attest_unbound_config_save(prepared["detail"]["id"], "d" * 64,
                                                        shared_work_parent=parent)
                    if interrupted:
                        with patch("os.replace", side_effect=replace_file):
                            with self.assertRaisesRegex(OSError, "interrupted after file rename"):
                                _restore_bound_managed_file_locked(store, pending, **kw)
                        pending = store.read()
                        self.assertEqual(target.read_bytes(), before)
                        self.assertIn("restore", pending["managed"])
                    restored = _restore_bound_managed_file_locked(store, pending, **kw)
                    self.assertFalse((active.parent / (".s10-managed-barrier-" + token)).exists())
                    self.assertEqual(restored["phase"], "restored")
                    self.assertEqual(committed_manifest(restored), prepared["previous_manifest"])
                    self.assertEqual(target.read_bytes(), before)
                    self.assertEqual(seen, [row[2], row[1]] if interrupted else [row[2]])

    def test_original_managed_cas_crash_after_ready_before_rename(self):
        from auto_detect_destination_commit import (
            _write_bound_managed_file_locked, _restore_bound_managed_file_locked)

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            store, prepared, row, parent, active, target, before, _ = self.fixture()
            kw = dict(parent=parent, active=active, attest=lambda: True)
            original = target.stat()
            real_replace = os.replace

            def stop_at_rename(source, dest, **kwargs):
                if Path(dest) == target:
                    os._exit(85)
                return real_replace(source, dest, **kwargs)

            pid = os.fork()
            if pid == 0:
                with patch("os.replace", side_effect=stop_at_rename):
                    try:
                        _write_bound_managed_file_locked(store, prepared, row, **kw)
                    except Exception:
                        os._exit(86)
                    os._exit(87)
            _, status = os.waitpid(pid, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 85)
            pending = store.read()
            temp = target.with_name(pending["managed"]["ready"]["temp"])
            self.assertEqual(temp.stat().st_ino, pending["managed"]["ready"]["inode"])
            self.assertIn("barrier", pending["managed"])
            token = pending["managed"]["ready"]["temp"][13:-4]
            scratch = active.parent / (".s10-managed-barrier-" + token)
            self.assertTrue(scratch.is_dir())
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(_restore_bound_managed_file_locked(store, pending, **kw)["phase"], "restored")
            self.assertFalse(temp.exists())
            self.assertFalse(scratch.exists())
            self.assertTrue(os.path.samestat(target.stat(), original))

    def test_original_managed_barrier_seed_without_wal_pin_refuses_recovery(self):
        """Crash between scratch seed and its durable WAL pin cannot delete by name."""
        from auto_detect_destination_commit import (
            DestinationRefused, _write_bound_managed_file_locked,
            _restore_bound_managed_file_locked)
        from managed_inode_barrier import seed as real_seed

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            store, prepared, row, parent, active, target, before, _ = self.fixture()
            kw = dict(parent=parent, active=active, attest=lambda: True)

            def crash_after_seed(*args):
                real_seed(*args)
                raise OSError("power-loss-window-after-scratch-seed")

            with patch("managed_inode_barrier.seed", side_effect=crash_after_seed):
                with self.assertRaisesRegex(DestinationRefused, "barrier_seed_refused"):
                    _write_bound_managed_file_locked(store, prepared, row, **kw)
            pending = store.read()
            self.assertEqual(pending["phase"], "managed-writing")
            self.assertIn("ready", pending["managed"])
            self.assertNotIn("barrier", pending["managed"])
            token = pending["managed"]["ready"]["temp"][13:-4]
            scratch = active.parent / (".s10-managed-barrier-" + token)
            self.assertTrue(scratch.is_dir())
            with self.assertRaisesRegex(DestinationRefused, "barrier_recovery_refused"):
                _restore_bound_managed_file_locked(store, pending, **kw)
            self.assertEqual(store.read(), pending)
            self.assertEqual(target.read_bytes(), before)
            self.assertTrue(scratch.exists())

    def test_original_managed_barrier_foreign_identical_bytes_inode_refused(self):
        """A same-length/same-content scratch substitution is never recovery authority."""
        from auto_detect_destination_commit import (
            DestinationRefused, _write_bound_managed_file_locked,
            _restore_bound_managed_file_locked)
        from managed_inode_barrier import _payload

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            store, prepared, row, parent, active, target, _, after = self.fixture()
            kw = dict(parent=parent, active=active, attest=lambda: True)
            real_replace = os.replace

            def crash_after_rename(source, dest, **kwargs):
                result = real_replace(source, dest, **kwargs)
                if Path(dest) == target:
                    raise OSError("crash-after-target-rename")
                return result

            with patch("os.replace", side_effect=crash_after_rename):
                with self.assertRaisesRegex(OSError, "crash-after-target-rename"):
                    _write_bound_managed_file_locked(store, prepared, row, **kw)
            pending = store.read()
            self.assertIn("barrier", pending["managed"])
            self.assertNotIn("installed", pending["managed"])
            token = pending["managed"]["ready"]["temp"]
            scratch = active.parent / (".s10-managed-barrier-" + token[13:-4])
            original = scratch / "record"
            original.rename(scratch / "original")
            original.write_bytes(_payload(token))
            original.chmod(0o600)
            (scratch / "original").unlink()
            with self.assertRaisesRegex(DestinationRefused, "barrier_recovery_refused"):
                _restore_bound_managed_file_locked(store, pending, **kw)
            self.assertEqual(store.read(), pending)
            self.assertEqual(target.read_bytes(), after)


    def test_native_managed_write_restores_a_synchronous_interruption(self):
        from contextlib import ExitStack
        from auto_detect_destination_commit import exclusive_destination_lock
        from neutral_effective_diff import EffectiveDecision
        from neutral_schema3_previous_physical import LockedRunningPredecessor, PriorRunningToken
        import neutral_shared_apply_source_gate as gate

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            store, prepared, row, parent, active, target, before, _ = self.fixture()
            detail, prior = prepared["detail"], prepared["previous"]
            root = prepared["manifest"]["root_sha256"]
            old_root = prepared["previous_manifest"]["root_sha256"]
            running = PriorRunningToken(123, "birth", 456, "monitor-birth", "f" * 64)
            executable = (1, 2, "f" * 64)
            physical = LockedRunningPredecessor(detail["id"], prior["id"], old_root,
                detail["base"], "3" * 64, running, None, executable_identity=executable,
                managed_preimages=(row,))
            semantic = gate.OriginalSemanticReceipt(detail["id"], prior["id"], root, old_root,
                EffectiveDecision("RELOAD_SAFE_CANDIDATE", (row[0],), ()), None,
                lifecycle_proposal="RELOAD")
            real_replace = os.replace
            attempts = []

            def fail_first_live_rename(source, dest, **kwargs):
                result = real_replace(source, dest, **kwargs)
                if Path(dest) == target:
                    attempts.append(target.read_bytes())
                    if len(attempts) == 1:
                        raise OSError("interrupted after file rename")
                return result

            with ExitStack() as stack:
                stack.enter_context(patch.object(gate, "native_recheck_running_prepared_fd9", return_value=physical))
                stack.enter_context(patch.object(gate, "_s10_native_bound_engine_readback",
                                                return_value={"engine_sha256": executable[2]}))
                stack.enter_context(patch("shared_apply_operation.SharedApplyOperation", return_value=store))
                stack.enter_context(patch("shared_apply_seal.WORK", parent))
                stack.enter_context(patch("neutral_schema3_previous_physical.COMMON_ACTIVE", active))
                stack.enter_context(patch("neutral_schema3_previous_physical._running_native", return_value=running))
                stack.enter_context(patch("neutral_schema3_previous_physical._running_executable_identity",
                                          return_value=executable))
                stack.enter_context(patch("voice_ipfw_adapter.shared_release_manifest",
                    return_value={"rule_base": 19000, "rule_max": 19099}))
                kernel = stack.enter_context(patch("voice_firewall_transaction.verify_prior_state"))
                config = stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
                stack.enter_context(patch("auto_detect_destination_commit.exclusive_destination_lock",
                    side_effect=lambda *_: exclusive_destination_lock(parent / "p2.lock", store.owner)))
                stack.enter_context(patch("os.replace", side_effect=fail_first_live_rename))
                with self.assertRaisesRegex(OSError, "interrupted after file rename"):
                    gate.native_write_running_managed_file_fd9(detail["id"], b"fixture",
                        source=None, semantic=semantic, config_fd=4, config_digest=detail["base"])
            self.assertGreaterEqual(config.call_count, 4)
            self.assertEqual(config.call_count, 2 * kernel.call_count)
            self.assertEqual(len(attempts), 2)
            self.assertEqual(attempts[1], before)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(store.read()["phase"], "restored")

    def test_original_managed_file_cas_refuses_drift_before_any_write(self):
        from auto_detect_destination_commit import (
            DestinationRefused, _write_bound_managed_file_locked, _restore_bound_managed_file_locked)

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            for kind in ("another release entry", "same bytes new inode", "foreign postimage"):
                with self.subTest(kind=kind):
                    store, prepared, row, parent, active, target, before, after = self.fixture(
                        extra_change=kind == "another release entry")
                    kw = dict(parent=parent, active=active, attest=lambda: True)
                    sibling = target.with_name("substitute")
                    if kind == "foreign postimage":
                        pending = _write_bound_managed_file_locked(store, prepared, row, **kw)
                        sibling.write_bytes(after)
                        sibling.replace(target)
                        with self.assertRaisesRegex(DestinationRefused, "foreign_image"):
                            _restore_bound_managed_file_locked(store, pending, **kw)
                        self.assertEqual(store.read(), pending)
                        self.assertEqual(target.read_bytes(), after)
                    else:
                        if kind == "same bytes new inode":
                            sibling.write_bytes(before)
                            sibling.replace(target)
                        with self.assertRaises(DestinationRefused):
                            _write_bound_managed_file_locked(store, prepared, row, **kw)
                        self.assertEqual(store.read(), prepared)
                        self.assertEqual(target.read_bytes(), before)

    def test_managed_cold_recovery_reuses_original_boot_and_config_transport(self):
        from contextlib import ExitStack, redirect_stdout, redirect_stderr
        import io
        import subprocess
        from auto_detect_destination_commit import (
            _write_bound_managed_file_locked, exclusive_destination_lock,
        )
        from auto_detect_minute import inspect_inert_release
        from shared_apply_seal import _stat
        import neutral_schema3_quiescent_preimage as gate
        import shared_apply_operation as journal

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            store, prepared, row, parent, active, target, before, after = self.fixture()
            pending = _write_bound_managed_file_locked(store, prepared, row,
                parent=parent, active=active, attest=lambda: True)
            op, old = pending["detail"], pending["previous"]
            self.assertEqual(target.read_bytes(), after)
            cli = ["shared_apply_operation.py", "recover-managed", op["id"], old["id"]]

            def php(command, *, pass_fds, budget, capture_output):
                self.assertEqual(command[-3:], ["ordinary-restore-finish", op["id"], "strategies"])
                self.assertEqual(pass_fds, (9,))
                self.assertEqual(budget, 90)
                self.assertTrue(capture_output)
                receipt = gate.finish_bound_cold_restore_locked(op["id"], op["base"], config_fd=4)
                return subprocess.CompletedProcess(command, 0, (json.dumps(receipt) + "\n").encode())

            with ExitStack() as stack:
                stack.enter_context(patch.object(sys, "platform", "freebsd15"))
                stack.enter_context(patch.object(os, "geteuid", return_value=0))
                stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
                stack.enter_context(patch.object(journal, "SharedApplyOperation", return_value=store))
                stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
                stack.enter_context(patch.object(gate, "WORK", parent))
                stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
                stack.enter_context(patch.object(gate, "PRODUCER_ROOT", parent / "absent-producer"))
                stack.enter_context(patch("shared_apply_seal._stat", side_effect=
                    lambda path, uid, **kw: _stat(path, store.owner, **kw)))
                stack.enter_context(patch.object(gate, "inspect_inert_release", side_effect=
                    lambda path, **kw: inspect_inert_release(path, owner_uid=store.owner)))
                stack.enter_context(patch("auto_detect_destination_commit.exclusive_destination_lock",
                    side_effect=lambda *_: exclusive_destination_lock(parent / "p2.lock", store.owner)))
                config = stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
                processes = stack.enter_context(patch.object(gate, "_zero_processes"))
                kernel = stack.enter_context(patch.object(gate, "_empty_kernel",
                                                        return_value="native-managed-kernel-empty"))
                transport = stack.enter_context(patch.object(gate, "_run_bound_restore_joined", side_effect=php))
                stdout = stack.enter_context(redirect_stdout(io.StringIO()))
                stack.enter_context(redirect_stderr(io.StringIO()))

                self.assertEqual(journal.main([cli[0], "inspect"]), 0)
                self.assertEqual(stdout.getvalue(),
                    f"managed-writing {op['id']} strategies {old['id']} {old['page']}\n")
                self.assertEqual(journal.main([*cli[:-1], "7" * 32]), 69)
                transport.assert_not_called()
                with self.assertRaises(gate.QuiescentPreimageRefused):
                    gate.finish_bound_cold_restore_locked(op["id"], op["candidate"], config_fd=4)
                processes.side_effect = gate.QuiescentPreimageRefused("live process")
                self.assertEqual(journal.main(cli), 69)
                processes.side_effect = None
                kernel.side_effect = gate.QuiescentPreimageRefused("managed kernel is not empty")
                self.assertEqual(journal.main(cli), 69)
                kernel.side_effect = None
                residue = parent / f".{active.name}.stage.{op['id']}"
                residue.mkdir()
                self.assertEqual(journal.main(cli), 69)
                residue.rmdir()
                self.assertEqual(store.read(), pending)
                self.assertEqual(target.read_bytes(), after)

                self.assertEqual(journal.main(cli), 0)
                self.assertTrue(stdout.getvalue().endswith(f"managed-restored={op['id']}\n"))
                self.assertEqual(journal.main([cli[0], "inspect"]), 0)
                self.assertTrue(stdout.getvalue().endswith(f"committed {old['id']} {old['page']}\n"))
                self.assertEqual(journal.main(cli), 69)
                config.assert_called_with(4, Path("/conf/config.xml"), owner_uid=None)

            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(committed_manifest(store.read()), prepared["previous_manifest"])

    def test_interrupted_managed_save_reconciles_exact_observed_image(self):
        from contextlib import ExitStack, redirect_stdout
        import io
        import subprocess
        from auto_detect_destination_commit import (
            _write_bound_managed_file_locked, exclusive_destination_lock,
        )
        from shared_apply_operation import _config_observation_witness
        from shared_apply_seal import _stat, verify_seal
        import auto_detect_effective_known as worker
        import neutral_schema3_quiescent_preimage as gate

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            for mode in ("base", "candidate", "running", "foreign-inode", "equal",
                         "pre-save-running", "pre-save-unpinned"):
                with self.subTest(mode=mode):
                    store, prepared, row, parent, active, target, before, after = self.fixture(
                        equal_config=mode == "equal")
                    detail = prepared["detail"]
                    observed = detail["base" if mode == "base" else "candidate"]
                    owner = "3" * 64
                    pending = _write_bound_managed_file_locked(store, prepared, row,
                        running_sha256=None if mode == "pre-save-unpinned" else owner,
                        parent=parent, active=active, attest=lambda: True)
                    saving = (pending if mode.startswith("pre-save-") else
                              store._checkpoint_managed_config(pending, saved=False, attest=lambda: True,
                                                               shared_work_parent=parent))
                    plan_sha = verify_seal(parent / detail["id"], owner=store.owner)["sha256"]["plan.json"]

                    def witness(image):
                        return _config_observation_witness(detail, plan_sha, image)

                    with ExitStack() as stack:
                        config = stack.enter_context((parent / "config.xml").open("w+b"))
                        config.write(b"<opnsense/>\n")
                        config.flush()
                        stack.enter_context(patch.object(sys, "platform", "freebsd15"))
                        stack.enter_context(patch.object(os, "geteuid", return_value=0))
                        stack.enter_context(patch.object(gate, "require_lifecycle_lock"))
                        stack.enter_context(patch.object(gate, "SharedApplyOperation", return_value=store))
                        stack.enter_context(patch.object(gate, "WORK", parent))
                        stack.enter_context(patch.object(gate, "COMMON_ACTIVE", active))
                        stack.enter_context(patch.object(gate, "PRODUCER_ROOT", parent / "absent-producer"))
                        pidfile = parent / "child.pid"
                        stack.enter_context(patch.object(gate, "CHILD_PID", pidfile))
                        stack.enter_context(patch.object(gate, "MONITOR_PID", parent / "monitor.pid"))
                        stack.enter_context(patch.object(gate, "DAEMON_PID", parent / "daemon.pid"))
                        stack.enter_context(patch("shared_apply_seal._stat", side_effect=
                            lambda path, uid, **kw: _stat(path, store.owner, **kw)))
                        stack.enter_context(patch("shared_apply_seal.verify_seal", side_effect=
                            lambda work, **kw: verify_seal(work, owner=store.owner)))
                        stack.enter_context(patch.object(gate, "inspect_inert_release", return_value="inactive"))
                        stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
                        stack.enter_context(patch("auto_detect_destination_commit.exclusive_destination_lock",
                            side_effect=lambda *_: exclusive_destination_lock(parent / "p2.lock", store.owner)))
                        processes = stack.enter_context(patch.object(gate, "_zero_processes"))
                        empty = stack.enter_context(patch.object(gate, "_empty_kernel",
                                                               return_value="native-managed-kernel-empty"))
                        running = stack.enter_context(patch(
                            "neutral_shared_apply_source_gate._native_managed_running_digest", return_value=owner))

                        if mode.startswith("pre-save-"):
                            pidfile.touch()
                            processes.side_effect = gate.QuiescentPreimageRefused("live process")
                            finish = gate.finish_bound_cold_restore_locked
                            running.return_value = "5" * 64
                            reason = ("RUNNING_OWNER_REQUIRED" if mode == "pre-save-unpinned"
                                      else "RUNNING_OWNER_CHANGED")
                            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, reason):
                                finish(detail["id"], detail["base"], config_fd=config.fileno())
                            self.assertEqual(store.read(), pending)
                            self.assertEqual(target.read_bytes(), after)
                            if mode == "pre-save-unpinned":
                                running.assert_not_called()
                            else:
                                # Change the witnessed process after the initial observation,
                                # before the original writer can restore the attributed inode.
                                running.side_effect = [owner, "5" * 64]
                                with self.assertRaisesRegex(gate.QuiescentPreimageRefused,
                                                            "RUNNING_OWNER_CHANGED"):
                                    finish(detail["id"], detail["base"], config_fd=config.fileno())
                                self.assertEqual(store.read(), pending)
                                self.assertEqual(target.read_bytes(), after)
                                running.side_effect = None
                                running.return_value = owner
                                self.assertEqual(finish(detail["id"], detail["base"],
                                                       config_fd=config.fileno()),
                                    {"result": "original-bound-cold-restored", "id": detail["id"]})
                                self.assertEqual((store.read()["phase"], target.read_bytes()),
                                                 ("restored", before))
                                self.assertEqual(committed_manifest(store.read()),
                                                 prepared["previous_manifest"])
                            empty.assert_not_called()
                            processes.assert_not_called()
                            continue

                        finish = gate.finish_managed_config_recovery_locked
                        if mode == "running":
                            pidfile.touch()
                        if mode == "equal":
                            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "AMBIGUOUS_IMAGE"):
                                finish(detail["id"], witness(observed), config_fd=config.fileno())
                            self.assertEqual(store.read(), saving)
                            continue

                        with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "IMAGE_REFUSED"):
                            finish(detail["id"], witness("8" * 64), config_fd=config.fileno())
                        self.assertEqual(store.read(), saving)
                        if mode == "foreign-inode":
                            from auto_detect_destination_commit import DestinationRefused
                            sibling = target.with_name("substitute")
                            sibling.write_bytes(after)
                            sibling.replace(target)
                            with self.assertRaisesRegex(DestinationRefused, "installed_image_changed"):
                                finish(detail["id"], witness(observed), config_fd=config.fileno())
                            self.assertEqual(store.read(), saving)
                            continue
                        if mode == "running":
                            running.return_value = "5" * 64
                            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "RUNNING_OWNER_CHANGED"):
                                finish(detail["id"], witness(observed), config_fd=config.fileno())
                            running.return_value = owner
                            empty.assert_not_called()
                        if mode == "base":
                            real_replace = os.replace

                            def interrupted(source, dest, **kw):
                                real_replace(source, dest, **kw)
                                if Path(dest) == target:
                                    raise OSError("interrupted restoring saved base")

                            with patch("os.replace", side_effect=interrupted):
                                with self.assertRaisesRegex(OSError, "interrupted restoring saved base"):
                                    finish(detail["id"], witness(observed), config_fd=config.fileno())
                            saving = store.read()
                            self.assertIn("restore", saving["managed"])
                            with self.assertRaisesRegex(gate.QuiescentPreimageRefused, "IMAGE_REFUSED"):
                                finish(detail["id"], witness(detail["candidate"]), config_fd=config.fileno())

                        def inherited(operation, proof, *, config_fd, queue_fd):
                            self.assertEqual((operation, config_fd, queue_fd), (detail["id"], 4, None))
                            return finish(operation, proof, config_fd=config.fileno())

                        def php(command, *, pass_fds, budget, capture_output):
                            self.assertEqual(command[-3:], ["managed-save-recover", detail["id"], "strategies"])
                            self.assertEqual((pass_fds, budget, capture_output), ((9,), 90, True))
                            with redirect_stdout(io.StringIO()) as output:
                                rc = worker.main(["recover-managed-config-locked", detail["id"], witness(observed)])
                            return subprocess.CompletedProcess(command, rc, output.getvalue().encode())

                        stack.enter_context(patch.object(gate, "finish_managed_config_recovery_locked",
                                                        side_effect=inherited))
                        stack.enter_context(patch.object(gate, "_run_bound_restore_joined", side_effect=php))
                        terminal = gate.native_finish_bound_cold_restore(saving)
                        self.assertEqual(store.read(), terminal)
                        self.assertNotIn("managed", terminal)
                        if mode == "base":
                            self.assertEqual((terminal["phase"], target.read_bytes()), ("restored", before))
                            self.assertEqual(committed_manifest(terminal), prepared["previous_manifest"])
                        else:
                            self.assertEqual((terminal["phase"], target.read_bytes()), ("committed", after))
                            self.assertEqual(committed_manifest(terminal), prepared["manifest"])

    def test_managed_config_requires_installed_file_and_same_running_owner_through_commit(self):
        from contextlib import ExitStack, redirect_stdout
        import io
        import auto_detect_effective_known as transport
        from auto_detect_destination_commit import (
            DestinationRefused, _restore_bound_managed_file_locked,
            _write_bound_managed_file_locked, exclusive_destination_lock,
        )
        from shared_apply_operation import _config_save_witness
        from shared_apply_seal import verify_seal
        import neutral_shared_apply_source_gate as gate

        with patch("voice_ipfw_adapter.require_lifecycle_lock"):
            for foreign_file in (False, True):
                with self.subTest(foreign_file=foreign_file):
                    store, prepared, row, parent, active, target, _, after = self.fixture()
                    detail = prepared["detail"]
                    running = "3" * 64
                    witness = _config_save_witness(detail,
                        verify_seal(parent / detail["id"], owner=store.owner)["sha256"]["plan.json"])
                    kw = dict(parent=parent, active=active, attest=lambda: True)
                    pending = _write_bound_managed_file_locked(store, prepared, row,
                                                              running_sha256=running, **kw)
                    with ExitStack() as stack:
                        config = stack.enter_context((parent / "config.xml").open("w+b"))
                        config.write(b"<opnsense/>\n")
                        config.flush()
                        stack.enter_context(patch.object(sys, "platform", "freebsd15"))
                        stack.enter_context(patch.object(os, "geteuid", return_value=0))
                        stack.enter_context(patch("shared_apply_operation.SharedApplyOperation", return_value=store))
                        stack.enter_context(patch("shared_apply_seal.WORK", parent))
                        stack.enter_context(patch("shared_apply_seal.verify_seal", side_effect=
                            lambda work, **_: verify_seal(work, owner=store.owner)))
                        stack.enter_context(patch("neutral_schema3_previous_physical.COMMON_ACTIVE", active))
                        stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
                        stack.enter_context(patch("auto_detect_destination_commit.exclusive_destination_lock",
                            side_effect=lambda *_: exclusive_destination_lock(parent / "p2.lock", store.owner)))
                        owner = stack.enter_context(patch.object(gate, "_native_managed_running_digest",
                                                               return_value=running))

                        native_checkpoint = gate.native_checkpoint_managed_config_fd9

                        def checkpoint(*, saved=False, digest=witness):
                            return native_checkpoint(detail["id"], digest,
                                config_fd=config.fileno(), saved=saved)

                        def request(mode, phase):
                            def inherited(operation, digest, *, config_fd, saved):
                                self.assertEqual(operation, detail["id"])
                                self.assertEqual(config_fd, 4)
                                return checkpoint(saved=saved, digest=digest)

                            with patch.object(gate, "native_checkpoint_managed_config_fd9", side_effect=inherited), \
                                 redirect_stdout(io.StringIO()) as output:
                                self.assertEqual(transport.main([mode, detail["id"], witness]), 0)
                            self.assertEqual(json.loads(output.getvalue()), {"result": phase, "id": detail["id"]})
                            return store.read()

                        with self.assertRaises(gate.OriginalSourceGateRefused):
                            checkpoint(saved=True)
                        with self.assertRaisesRegex(gate.OriginalSourceGateRefused, "MANAGED_CONFIG_PLAN_CHANGED"):
                            checkpoint(digest="4" * 64)
                        self.assertEqual(store.read(), pending)
                        saving = request("begin-managed-config-save-locked", "managed-config-saving")
                        self.assertEqual(saving, {**pending, "phase": "managed-config-saving"})
                        self.assertEqual(store.read(), saving)
                        with self.assertRaises(DestinationRefused):
                            _restore_bound_managed_file_locked(store, saving, **kw)
                        self.assertFalse(native_lifecycle_gate("common-recover-activating",
                            root=store.root)["safe_to_mutate"])
                        with self.assertRaises(gate.OriginalSourceGateRefused):
                            checkpoint()
                        with self.assertRaisesRegex(gate.OriginalSourceGateRefused, "MANAGED_CONFIG_PLAN_CHANGED"):
                            checkpoint(saved=True, digest="4" * 64)
                        owner.return_value = "5" * 64
                        with self.assertRaises(SharedOperationError):
                            checkpoint(saved=True)
                        self.assertEqual(store.read(), saving)
                        owner.return_value = running
                        if foreign_file:
                            sibling = target.with_name("substitute")
                            sibling.write_bytes(after)
                            sibling.replace(target)
                            with self.assertRaisesRegex(DestinationRefused, "installed_image_changed"):
                                checkpoint(saved=True)
                            self.assertEqual(store.read(), saving)
                        else:
                            committed = request("confirm-managed-config-save-locked", "committed")
                            self.assertEqual(committed, store.read())
                            self.assertEqual(committed["phase"], "committed")
                            self.assertEqual(committed_manifest(committed), prepared["manifest"])
                            self.assertNotIn("managed", committed)
                        self.assertEqual(target.read_bytes(), after)


if __name__ == "__main__":
    unittest.main()
