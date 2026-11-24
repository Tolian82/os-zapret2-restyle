#!/usr/bin/env python3
"""S10a original PREPARED root staging, no physical activation or second seal."""
from __future__ import annotations

import hashlib
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
from neutral_root_manifest import compile_candidate
from shared_apply_seal import create_seal
from neutral_root_stage import (stage_manifest, _stage_candidate,
                                attest_staged_candidate, RootStageRefused)
from shared_apply_seal import verify_seal
from shared_apply_operation import SharedApplyOperation

_spec = importlib.util.spec_from_file_location(
    "s10a_existing_s09b", ROOT / "scripts/test-tz6v5-s09b-sealed-root-refs.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("ORIGINAL_S09B_FIXTURE_MISSING")
_previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_previous)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class OriginalPreparedS10a(unittest.TestCase):
    def setUp(self):
        # Retain exact S09b original seal/argv/source-map fixture; only the
        # original shared Apply journal is new, never a second root writer.
        self.fx = _previous.SealedFixture("runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.journal_root = self.fx.parent / "journal"
        plan = {"result": "prepared", "page": "strategies",
                "dependencies": "f" * 64, "changed_fields": [],
                "candidate": {"general": {"enabled": "0"}}}
        (self.fx.work / "plan.json").write_text(
            json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
        self.detail = {
            "id": _previous.GEN, "page": "strategies", "base": "f" * 64,
            # ORIGINAL PHP preflight produces a logical candidate digest;
            # it is emphatically not the sha256 of candidate.xml bytes.
            "candidate": sha(b"original logical VoiceSettingsSnapshot::digest witness"),
            "changed_fields": [],
        }
        self.original_journal = SharedApplyOperation(self.journal_root,
                                                    owner=os.geteuid())
        self.original_journal.advance("prepared", self.detail)

    def candidate(self, mode="list"):
        if mode == "auto":
            self.fx.mode = "auto"
            self.fx.map = _previous.source_map(_previous.GEN, self.fx.args)
            self.fx.native = _previous.proof("auto", self.fx.args)
            path = self.fx.release / "auto-detect-source-map.json"
            path.write_bytes(self.fx.map)
            path.chmod(0o600)
        return self.fx.seal()

    def kw(self, **changes):
        params = {
            "generation": _previous.GEN, "effective": self.fx.effective,
            "native": self.fx.native, "mode": self.fx.mode,
            "enabled": False, "parent": self.fx.parent,
            "journal_root": self.journal_root, "owner_uid": os.geteuid(),
        }
        params.update(changes)
        return params

    def stage(self, candidate, **changes):
        return _stage_candidate(candidate=candidate, **self.kw(**changes))

    def attest(self, **changes):
        return attest_staged_candidate(**self.kw(**changes))

    def test_list_prepared_root_sibling_nonactivating_and_original_seal_unchanged(self):
        c = self.candidate()
        before = verify_seal(self.fx.work, owner=os.geteuid())
        before_journal = self.original_journal.read()
        receipt = self.stage(c)
        after = verify_seal(self.fx.work, owner=os.geteuid())
        self.assertEqual(before, after)
        self.assertEqual(before_journal, self.original_journal.read())
        self.assertEqual(receipt.root_sha256, sha(c.json_bytes))
        self.assertEqual(receipt.original_candidate_sha256, self.detail["candidate"])
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertFalse(receipt.promotion_allowed)
        self.assertEqual(receipt.authorization, "NONE")
        self.assertTrue(receipt.reattest_under_original_fd9)
        self.assertEqual(self.attest(), receipt)
        root = self.fx.work / "manifest.json"
        self.assertEqual(root.read_bytes(), c.json_bytes)
        self.assertEqual(root.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.fx.release / "manifest.json").exists())
        self.assertFalse((self.fx.work / ".manifest.json.pending").exists())
        with self.assertRaises(RootStageRefused):
            self.stage(c)  # same-generation replay must never overwrite
        self.assertEqual(root.read_bytes(), c.json_bytes)

    def test_auto_original_map_with_same_seal_and_pending_owner(self):
        c = self.candidate("auto")
        receipt = self.stage(c)
        self.assertEqual(self.attest(), receipt)
        self.assertEqual(len(json.loads((self.fx.work / "manifest.json").read_bytes())["refs"]), 2)
        self.assertEqual(self.fx.mode, "auto")

    def test_no_fd9_means_public_writer_rejected_before_work(self):
        c = self.candidate()
        # On non-native OS the original FreeBSD-root FD9 is absent. In CI
        # even if FD9 belongs to an unrelated test it MUST be refused.
        with patch("neutral_root_stage.require_lifecycle_lock",
                   side_effect=RuntimeError("no original FD9")):
            with self.assertRaisesRegex(RootStageRefused, "ORIGINAL_FD9_REQUIRED"):
                stage_manifest(generation=_previous.GEN, candidate=c,
                               effective=self.fx.effective, native=self.fx.native,
                               mode="list", enabled=False)
        self.assertFalse((self.fx.work / "manifest.json").exists())

    def test_wrong_original_journal_and_candidate_seal_refuse_prewrite(self):
        c = self.candidate()
        for delta in (dict(generation="f" * 32), dict(mode="auto"),
                      dict(enabled=True), dict(native=_previous.proof("auto", self.fx.args))):
            with self.subTest(delta=delta):
                with self.assertRaises(RootStageRefused):
                    self.stage(c, **delta)
        # The only original journal field allowed is a proven digest of the
        # same candidate.xml covered by the existing seal.
        self.original_journal.advance("activating", self.detail)
        with self.assertRaises(RootStageRefused):
            self.stage(c)
        self.assertFalse((self.fx.work / "manifest.json").exists())

    def test_second_root_inside_original_sealed_release_refused(self):
        foreign = self.fx.release / "manifest.json"
        foreign.write_bytes(b"second-manifest-owner\n")
        foreign.chmod(0o600)
        c = self.candidate()
        with self.assertRaisesRegex(RootStageRefused, "SECOND_RELEASE_ROOT_FORBIDDEN"):
            self.stage(c)
        self.assertFalse((self.fx.work / "manifest.json").exists())
        self.assertTrue(foreign.exists())  # no untrusted cleanup/write

    def test_original_plan_dependency_or_page_mismatch_refused(self):
        # Original immutable plan and prepared journal MUST identify same
        # page, source snapshot, owned changes, but we do not recompute
        # VoiceSettingsSnapshot::digest in a second Python serializer.
        c = self.candidate()
        before = self.original_journal.read()
        modified = dict(before)
        modified["detail"] = {**before["detail"], "base": "c" * 64}
        (self.journal_root / "operation.json").write_text(json.dumps(modified))
        with self.assertRaises(RootStageRefused):
            self.stage(c)
        self.assertFalse((self.fx.work / "manifest.json").exists())

    def test_corrupt_release_or_seal_refuses_without_staging(self):
        c = self.candidate()
        (self.fx.release / "dvtws.args").write_bytes(self.fx.args + b"--unexpected\n")
        with self.assertRaises(RootStageRefused):
            self.stage(c)
        self.assertFalse((self.fx.work / "manifest.json").exists())

    def test_collision_pending_symlink_and_root_alias_refused(self):
        for collision in ("pending", "root", "symlink"):
            with self.subTest(collision=collision):
                if (self.fx.work / "bundle-seal.json").exists():
                    (self.fx.work / "bundle-seal.json").unlink()
                c = self.fx.seal()
                target = self.fx.work / (".manifest.json.pending" if collision == "pending" else "manifest.json")
                if collision == "symlink":
                    target.symlink_to("bundle-seal.json")
                else:
                    target.write_bytes(b"old-original-byte-snapshot\n")
                with self.assertRaises(RootStageRefused):
                    self.stage(c)
                self.assertEqual(target.is_symlink(), collision == "symlink")
                target.unlink()

    def test_crash_or_tamper_after_original_staging_blocks_read(self):
        c = self.candidate()
        self.stage(c)
        root = self.fx.work / "manifest.json"
        root.write_bytes(c.json_bytes.replace(b'"enabled":false', b'"enabled":true'))
        with self.assertRaises(RootStageRefused):
            self.attest()
        root.write_bytes(c.json_bytes)
        pending = self.fx.work / ".manifest.json.pending"
        pending.write_bytes(c.json_bytes)
        pending.chmod(0o600)
        with self.assertRaises(RootStageRefused):
            self.attest()

    def test_changed_original_journal_after_stage_blocks_read(self):
        c = self.candidate()
        self.stage(c)
        self.original_journal.advance("activating", self.detail)
        with self.assertRaises(RootStageRefused):
            self.attest()
        self.assertTrue((self.fx.work / "manifest.json").exists())


@unittest.skipUnless(
    (ROOT / "scripts/test-tz6v5-s08c-original-native-parity.py").is_file(),
    "genuine original S08c/P2e shell builder is CI-only; not mounted in local S0")
class GenuineOriginalProducerS10a(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "scripts/test-tz6v5-s08c-original-native-parity.py"
        spec = importlib.util.spec_from_file_location("s10a_original_s08c", path)
        if spec is None or spec.loader is None:
            raise AssertionError("ORIGINAL_NATIVE_SOURCE_FIXTURE_MISSING")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.original = module.RealNativeSourceParity
        cls.original.setUpClass()

    def test_original_p2e_builder_list_auto_prepared_sibling_unchanged_seal(self):
        # Genuine original argv/source-map production is delegated to the
        # existing S08c→P2e builder, never repeated or approximated here.
        for mode in ("list", "auto"):
            with self.subTest(mode=mode):
                runner = self.original("runTest")
                self.addCleanup(runner.doCleanups)
                fixture, kw, native = runner.real(mode=mode)
                args = kw["original_args"]
                mapping = ((fixture.release / "auto-detect-source-map.json").read_bytes()
                           if mode == "auto" else None)
                # Independent real S08d snapshot parity is tested in the
                # existing S09b integration on exactly these original inputs.
                eff = _previous.effective(args)
                plan = {"result": "prepared", "page": "strategies",
                        "dependencies": "f" * 64, "changed_fields": [],
                        "candidate": {"general": {"enabled": "0"}}}
                (fixture.work / "plan.json").write_text(
                    json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
                original = create_seal(fixture.work, owner=os.geteuid())
                digest = sha((fixture.work / "bundle-seal.json").read_bytes())
                candidate = compile_candidate(
                    effective=eff, generation=fixture.work.name, target_mode=mode,
                    enabled=False, original_args=args, original_source_map=mapping,
                    seal_sha256=digest, owner_uid=os.geteuid())
                journal_root = fixture.root / "s10a-original-journal"
                detail = {"id": fixture.work.name, "page": "strategies",
                          "base": "f" * 64, "candidate": sha(b"original logical digest"),
                          "changed_fields": []}
                journal = SharedApplyOperation(journal_root, owner=os.geteuid())
                journal.advance("prepared", detail)
                params = dict(generation=fixture.work.name,
                              effective=eff, native=native, mode=mode,
                              enabled=False, parent=fixture.root,
                              journal_root=journal_root, owner_uid=os.geteuid())
                r = _stage_candidate(candidate=candidate, **params)
                self.assertEqual(r, attest_staged_candidate(**params))
                self.assertEqual(verify_seal(fixture.work, owner=os.geteuid()), original)
                self.assertEqual(journal.read()["phase"], "prepared")
                self.assertFalse((fixture.release / "manifest.json").exists())
                self.assertEqual((fixture.work / "manifest.json").read_bytes(),
                                 candidate.json_bytes)
                self.assertFalse(r.physical_transition_allowed)


if __name__ == "__main__":
    unittest.main()
