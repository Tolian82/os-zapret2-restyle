#!/usr/bin/env python3
"""TZ6v5 S10b2b2b2 genuine original staged/bound schema3 root (NO activation).

Reuse the accepted actual P2e/S08c/S08d/Voice final schema3 promoter and the
one original S10a sibling writer / S10b1 durable operation.json writer.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

import neutral_root_stage as stage
from neutral_root_manifest import RootCandidate
from neutral_root_stage import RootStageRefused
from neutral_root_bound_preflight import BoundRootRefused, _attest_bound_candidate
from neutral_schema3_physical_refs import _attest_physical_schema3
from shared_apply_operation import SharedOperationError, _validate_record

spec = importlib.util.spec_from_file_location(
    "original_s10b2b1_real_fixture",
    ROOT / "scripts/test-tz6v5-s10b2b1-original-schema3-preimage.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_PROMOTED_P2E_FIXTURE_UNAVAILABLE")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


class GenuineOriginalSchema3StagingAndBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.GenuineNativePromotedS10b2b1.setUpClass()

    @classmethod
    def tearDownClass(cls):
        prior.GenuineNativePromotedS10b2b1.tearDownClass()

    def setUp(self):
        self.f = prior.GenuineNativePromotedS10b2b1("runTest")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.native = self.f.native
        self.effective = self.f.effective
        self.original = self.f.original
        self.raw_before = {str(p.relative_to(self.f.release)):
                           hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in self.f.release.rglob("*") if p.is_file()}
        self.journal_before = self.original.read()

    def source(self, **changes):
        f = self.f
        args = dict(generation=f.generation, native=self.native,
                    effective=self.effective, enabled=True,
                    parent=f.parent, journal_root=f.journal_root,
                    owner_uid=os.geteuid())
        args.update(changes)
        return _attest_physical_schema3(**args)

    def staging(self, candidate=None, **changes):
        f = self.f
        if candidate is None:
            candidate = self.source().candidate
        args = dict(generation=f.generation, candidate=candidate,
                    native=self.native, effective=self.effective,
                    mode="auto", enabled=True, parent=f.parent,
                    journal_root=f.journal_root, owner_uid=os.geteuid(),
                    schema3=True)
        args.update(changes)
        return stage._stage_candidate(**args)

    def attest_staged(self, **changes):
        f = self.f
        args = dict(generation=f.generation, effective=self.effective,
                    native=self.native, enabled=True,
                    parent=f.parent, journal_root=f.journal_root,
                    owner_uid=os.geteuid())
        args.update(changes)
        return stage.attest_staged_schema3_candidate(**args)

    def bind(self, **changes):
        f = self.f
        args = dict(generation=f.generation, native=self.native,
                    effective=self.effective, mode="auto", enabled=True,
                    shared_work_parent=f.parent, schema3=True)
        args.update(changes)
        with patch("voice_ipfw_adapter.require_lifecycle_lock",
                   return_value=None):
            return self.original.bind_prepared_manifest(**args)

    def bound(self, **changes):
        f = self.f
        args = dict(generation=f.generation, native=self.native,
                    effective=self.effective, mode="auto", enabled=True,
                    parent=f.parent, journal_root=f.journal_root,
                    owner_uid=os.geteuid(), schema3=True)
        args.update(changes)
        return _attest_bound_candidate(**args)

    def test_genuine_final_schema3_one_sibling_one_original_writer(self):
        candidate = self.source().candidate
        staged = self.staging(candidate)
        bound = self.bind()
        ready = self.bound()
        self.assertEqual(staged, self.attest_staged(allow_bound_schema3=True))
        self.assertEqual(staged.root_sha256, candidate.sha256)
        self.assertEqual(ready.root_sha256, candidate.sha256)
        self.assertEqual(bound["manifest"]["schema"], 2)
        self.assertEqual(bound["manifest"]["root_sha256"], candidate.sha256)
        self.assertEqual(bound["manifest"]["seal_sha256"],
                         staged.original_seal_sha256)
        self.assertEqual(bound["manifest"]["candidate_sha256"], self.f.candidate)
        self.assertEqual(bound["detail"], self.f.detail)
        self.assertEqual(bound["phase"], "prepared")
        self.assertEqual(self.original.read(), bound)
        self.assertEqual((self.f.work / "manifest.json").read_bytes(),
                         candidate.json_bytes)
        self.assertEqual(stat.S_IMODE(
            (self.f.work / "manifest.json").stat().st_mode), 0o600)
        self.assertFalse((self.f.work / ".manifest.json.pending").exists())
        self.assertFalse((self.f.release / "manifest.json").exists())
        self.assertEqual(self.raw_before, {
            str(p.relative_to(self.f.release)):
                hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.f.release.rglob("*") if p.is_file()})
        self.assertEqual(ready.authorization, "NONE")
        self.assertFalse(ready.physical_transition_allowed)
        self.assertFalse(ready.promotion_allowed)
        self.assertTrue(ready.native_owner_preflight_required)

    def test_unbound_staging_and_journal_never_authorize_activation(self):
        self.staging()
        with self.assertRaises(SharedOperationError):
            self.original.advance("activating", self.f.detail)
        bound = self.bind()
        with self.assertRaisesRegex(SharedOperationError, "preactivation gate"):
            self.original.advance("activating", self.f.detail)
        self.assertEqual(self.original.read(), bound)
        restored = self.original.advance("restored", self.f.detail)
        self.assertEqual(restored["manifest"], bound["manifest"])
        with self.assertRaises(BoundRootRefused):
            self.bound()

    def test_existing_s09_schema1_path_cannot_claim_schema2(self):
        self.staging()
        with self.assertRaises(SharedOperationError):
            self.bind(schema3=False)
        with self.assertRaises(RootStageRefused):
            stage.attest_staged_candidate(
                generation=self.f.generation, effective=self.effective,
                native=self.native, mode="auto", enabled=True,
                parent=self.f.parent, journal_root=self.f.journal_root,
                owner_uid=os.geteuid())
        self.assertEqual(self.original.read(), self.journal_before)

    def test_public_stage_and_binding_need_original_fd9(self):
        candidate = self.source().candidate
        with patch.object(stage, "require_lifecycle_lock",
                          side_effect=RuntimeError("FD9 absent")):
            with self.assertRaisesRegex(RootStageRefused, "FD9"):
                stage.stage_schema3_manifest(
                    generation=self.f.generation, candidate=candidate,
                    effective=self.effective, native=self.native, enabled=True)
        self.assertFalse((self.f.work / "manifest.json").exists())
        self.staging()
        with patch("voice_ipfw_adapter.require_lifecycle_lock",
                   side_effect=RuntimeError("FD9 absent")):
            with self.assertRaisesRegex(SharedOperationError, "FD9"):
                self.original.bind_prepared_manifest(
                    self.f.generation, effective=self.effective,
                    native=self.native, mode="auto", enabled=True,
                    shared_work_parent=self.f.parent, schema3=True)
        self.assertEqual(self.original.read(), self.journal_before)

    def test_no_schema_mixing_forged_status_or_new_authority(self):
        source = self.source()
        for candidate in (
            replace(source.candidate, authorization="ACTIVATE"),
            replace(source.candidate, physical_transition_allowed=True),
            replace(source.candidate, json_bytes=source.candidate.json_bytes+b" "),
        ):
            with self.subTest(candidate=candidate), self.assertRaises(RootStageRefused):
                self.staging(candidate)
            self.assertFalse((self.f.work / "manifest.json").exists())
        with self.assertRaises(RootStageRefused):
            self.staging(source.candidate, mode="list")
        self.assertEqual(self.original.read(), self.journal_before)

    def test_physical_ref_mode_or_content_drift_refused_before_stage(self):
        cached = self.source().candidate
        path = self.f.release / "dvtws.args"
        current = path.read_bytes()
        try:
            path.chmod(0o600)
            with self.assertRaises(RootStageRefused):
                self.staging(cached)
        finally:
            path.chmod(0o644)
        path = self.f.release / "auto-detect-generation.json"
        original = path.read_bytes()
        try:
            path.write_bytes(original+b" ")
            with self.assertRaises(RootStageRefused):
                self.staging(cached)
        finally:
            path.write_bytes(original)
        self.assertFalse((self.f.work / "manifest.json").exists())

    def test_collision_and_interrupted_stage_cannot_overwrite(self):
        candidate = self.source().candidate
        pending = self.f.work / ".manifest.json.pending"
        pending.write_bytes(b"crash-before-atomic-link")
        with self.assertRaises(RootStageRefused):
            self.staging(candidate)
        pending.unlink()
        staged = self.staging(candidate)
        with self.assertRaises(RootStageRefused):
            self.staging(candidate)
        self.assertEqual(staged.root_sha256, candidate.sha256)
        self.assertEqual(self.original.read(), self.journal_before)

    def test_bound_seal_and_original_native_ref_tamper_refused(self):
        self.staging()
        self.bind()
        for file in (self.f.work / "manifest.json",
                     self.f.release / "dvtws.args",
                     self.f.release / "auto-detect-generation.json"):
            saved = file.read_bytes()
            with self.subTest(file=file):
                try:
                    file.write_bytes(saved+b" ")
                    with self.assertRaises(BoundRootRefused):
                        self.bound()
                finally:
                    file.write_bytes(saved)
        self.assertEqual(self.bound().authorization, "NONE")

    def test_forged_schema2_manifest_sha_refused_not_activated(self):
        self.staging()
        bound = self.bind()
        for key, value in (("root_sha256", "f"*64),
                           ("seal_sha256", "f"*64),
                           ("candidate_sha256", "f"*64)):
            forged = dict(bound)
            forged["manifest"] = {**bound["manifest"], key: value}
            with self.subTest(key=key):
                if key == "candidate_sha256":
                    with self.assertRaises(SharedOperationError):
                        _validate_record(forged)
                else:
                    _validate_record(forged)
                    self.original._persist_record(forged)
                    with self.assertRaises(BoundRootRefused):
                        self.bound()
                    self.original._persist_record(bound)

    def test_stale_or_finished_journal_blocks_staging_and_binding(self):
        candidate = self.source().candidate
        self.original.advance("restored", self.f.detail)
        with self.assertRaises(RootStageRefused):
            self.staging(candidate)
        self.assertFalse((self.f.work / "manifest.json").exists())

    def test_post_fsync_recheck_failure_leaves_one_bound_prepared(self):
        self.staging()
        real = stage.attest_staged_schema3_candidate
        checks = []
        def fail_second(**kwargs):
            witness = real(**kwargs)
            checks.append(kwargs.get("allow_bound_schema3", False))
            if len(checks) == 2:
                raise RootStageRefused("fault-after-original-journal-fsync")
            return witness
        with patch("voice_ipfw_adapter.require_lifecycle_lock",
                   return_value=None), patch.object(
                       stage, "attest_staged_schema3_candidate",
                       side_effect=fail_second):
            with self.assertRaisesRegex(SharedOperationError, "post-bind"):
                self.original.bind_prepared_manifest(
                    self.f.generation, effective=self.effective,
                    native=self.native, mode="auto", enabled=True,
                    shared_work_parent=self.f.parent, schema3=True)
        self.assertEqual(checks, [False, True])
        self.assertEqual(self.original.read()["phase"], "prepared")
        self.assertEqual(self.original.read()["manifest"]["schema"], 2)
        with self.assertRaises(SharedOperationError):
            self.original.advance("activating", self.f.detail)
        self.assertEqual(self.bound().authorization, "NONE")

    def test_source_bridge_default_still_refuses_bound_root(self):
        self.staging()
        self.bind()
        from neutral_schema3_source_bridge import (
            OriginalSchema3Refused, _attest_original_schema3)
        with self.assertRaises(OriginalSchema3Refused):
            _attest_original_schema3(
                generation=self.f.generation, native=self.native,
                effective=self.effective, parent=self.f.parent,
                journal_root=self.f.journal_root, owner_uid=os.geteuid())
        self.assertEqual(self.bound().authorization, "NONE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
