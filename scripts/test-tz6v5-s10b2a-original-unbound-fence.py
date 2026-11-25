#!/usr/bin/env python3
"""S10b2a read-only exact journal/root bound preactivation source checks.

The physical original legacy executor shell fault matrix is run separately by
scripts/test-shared-apply-execute.sh. This module has NO activation code.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from neutral_root_bound_preflight import (
    _attest_bound_candidate, attest_bound_under_fd9, BoundRootRefused,
)
import neutral_root_bound_preflight as guard

spec = importlib.util.spec_from_file_location(
    "s10b2a_existing_b1_fixture",
    ROOT / "scripts/test-tz6v5-s10b1-original-journal-binding.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_S10B1_FIXTURE_MISSING")
b1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b1)


class OriginalBoundPreactivation(unittest.TestCase):
    def setUp(self):
        self.case = b1.OriginalDurableRootBinding("runTest")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.bound = self.case.bind()
        self.owner = self.case.owner
        self.detail = self.case.case.detail

    def kw(self, **changes):
        params = dict(
            generation=self.detail["id"], effective=self.case.case.fx.effective,
            native=self.case.case.fx.native, mode="list", enabled=False,
            parent=self.case.case.fx.parent,
            journal_root=self.case.case.journal_root,
            owner_uid=self.case.case.fx.work.stat().st_uid)
        params.update(changes)
        return params

    def attest(self, **changes):
        return _attest_bound_candidate(**self.kw(**changes))

    def test_bound_original_prepared_readonly_has_no_transition_rights(self):
        root = self.case.case.fx.work
        observed = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob("*") if p.is_file()}
        prior = self.owner.read()
        result = self.attest()
        self.assertEqual(result.generation, self.detail["id"])
        self.assertEqual(result.root_sha256, self.bound["manifest"]["root_sha256"])
        self.assertEqual(result.original_seal_sha256, self.bound["manifest"]["seal_sha256"])
        self.assertEqual(result.original_candidate_sha256, self.detail["candidate"])
        self.assertEqual(result.authorization, "NONE")
        self.assertFalse(result.physical_transition_allowed)
        self.assertFalse(result.promotion_allowed)
        self.assertTrue(result.reattest_under_original_fd9)
        self.assertTrue(result.native_owner_preflight_required)
        self.assertEqual(self.attest(), result)
        self.assertEqual(self.owner.read(), prior)
        self.assertEqual(observed, {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()})

    def test_wrong_bound_root_or_seal_sha_refused(self):
        for field in ("root_sha256", "seal_sha256", "candidate_sha256"):
            with self.subTest(field=field):
                forged = {**self.bound, "manifest": {
                    **self.bound["manifest"], field: "f" * 64}}
                if field == "candidate_sha256":
                    # The journal rejects a detached PHP candidate identity
                    # mismatch even before physical source validation.
                    with self.assertRaises(Exception):
                        self.owner._persist_record(forged)
                else:
                    self.owner._persist_record(forged)
                    with self.assertRaises(BoundRootRefused):
                        self.attest()
                    self.owner._persist_record(self.bound)

    def test_original_root_incomplete_or_changed_is_not_accepted(self):
        root = self.case.case.fx.work / "manifest.json"
        root.write_bytes(root.read_bytes() + b" ")
        with self.assertRaises(BoundRootRefused):
            self.attest()

    def test_unsealed_original_release_mutation_refused(self):
        args = self.case.case.fx.release / "dvtws.args"
        args.write_bytes(args.read_bytes() + b"--foreign\n")
        with self.assertRaises(BoundRootRefused):
            self.attest()

    def test_pending_root_or_release_second_root_refused(self):
        sibling = self.case.case.fx.work / ".manifest.json.pending"
        sibling.write_bytes(b"incomplete")
        sibling.chmod(0o600)
        with self.assertRaises(BoundRootRefused):
            self.attest()
        sibling.unlink()
        second = self.case.case.fx.release / "manifest.json"
        second.write_bytes(b"untrusted")
        second.chmod(0o600)
        with self.assertRaises(BoundRootRefused):
            self.attest()

    def test_wrong_generation_native_mode_and_enablement_refused(self):
        for change in (
            dict(generation="f" * 32),
            dict(mode="auto"),
            dict(enabled=True),
            dict(native=replace(self.case.case.fx.native,
                                original_args_sha256="f" * 64)),
        ):
            with self.subTest(change=change), self.assertRaises(BoundRootRefused):
                self.attest(**change)

    def test_terminal_phase_cannot_be_misread_as_prepared(self):
        self.owner.recover_prepared(self.detail["id"], lambda: True,
                                    shared_work_parent=self.case.case.fx.parent)
        with self.assertRaises(BoundRootRefused):
            self.attest()

    def test_after_first_physical_read_journal_race_refused(self):
        original = guard.attest_staged_candidate
        count = []
        def race(**kwargs):
            proof = original(**kwargs)
            count.append(True)
            if len(count) == 1:
                # Deliberate external journal race, not a valid recovery call.
                self.owner._persist_record({**self.owner.read(), "phase": "restored"})
            return proof
        with patch.object(guard, "attest_staged_candidate", side_effect=race):
            with self.assertRaises(BoundRootRefused):
                self.attest()
        self.assertEqual(count, [True])
        self.assertEqual(self.owner.read()["phase"], "restored")

    def test_public_fd9_gate_refuses_absent_original_lock(self):
        with patch.object(guard, "require_lifecycle_lock",
                          side_effect=RuntimeError("missing original FD9")):
            with self.assertRaisesRegex(BoundRootRefused, "ORIGINAL_FD9_REQUIRED"):
                attest_bound_under_fd9(
                    generation=self.detail["id"],
                    effective=self.case.case.fx.effective,
                    native=self.case.case.fx.native,
                    mode="list", enabled=False)
        self.assertEqual(self.owner.read(), self.bound)


if __name__ == "__main__":
    unittest.main()
