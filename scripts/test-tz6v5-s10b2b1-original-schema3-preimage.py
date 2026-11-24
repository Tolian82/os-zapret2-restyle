#!/usr/bin/env python3
"""TZ6v5 S10b2b1 genuine P2e original -> schema3 promoted/SEALED FD9 source.

No engine, live Config, physical FD9, IPFW or process; exact production
promoter, full original seal and real original S08c/S08d typed witnesses.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

import auto_detect_origin_map as origin
import neutral_schema3_source_bridge as bridge
from neutral_effective_diff import snapshot
from shared_apply_seal import create_seal, verify_seal
from shared_apply_operation import SharedApplyOperation
from neutral_schema3_source_bridge import (
    _attest_original_schema3, attest_schema3_under_fd9, OriginalSchema3Refused,
)

spec = importlib.util.spec_from_file_location(
    "s10b2b1_original_s08c", ROOT / "scripts/test-tz6v5-s08c-original-native-parity.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_S08C_P2E_FIXTURE_MISSING")
s08c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s08c)


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class GenuineNativePromotedS10b2b1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owner_case = s08c.RealNativeSourceParity("runTest")
        cls.owner_case.setUpClass()
        fixture, kwargs, cls.native = cls.owner_case.real(mode="auto", voice_on=True)
        cls.generation = fixture.work.name
        cls.candidate = kwargs["candidate_sha256"]
        cls.base = "a" * 64
        cls.detail = {
            "id": cls.generation, "page": "strategies", "base": cls.base,
            "candidate": cls.candidate, "changed_fields": [],
        }
        assert cls.candidate == "d" * 64
        original = kwargs["original_args"]
        source = kwargs["source_map"]
        assert source["generation"] == cls.generation
        managed = fixture.release / "managed"
        hashes = {
            p.name: sha(p.read_bytes()) for p in managed.iterdir()
            if p.is_file() and re.fullmatch(
                r"(?:hostlist|ipset)-[a-z][a-z0-9-]{0,63}[.]txt", p.name)
        }
        cls.effective = snapshot(
            original_native_args=original, target_mode="auto",
            original_source_rows=[
                [row["role"], row["status"], row.get("selector"),
                 row.get("hostlist"), row.get("native_number")]
                for row in source["profiles"]],
            authored_selectors=tuple(
                tuple(f"<{kind}:{key}>" for kind, key in row.authored)
                for row in kwargs["targets"].profiles),
            saved_wan=kwargs["requested"].saved_wan,
            resolved_wan=kwargs["voice_plan"]["capture"]["wan"],
            engine_version="v1.0.7",
            original_capture=kwargs["voice_plan"]["capture"],
            original_tcp=(fixture.release / "tcp-ports.txt").read_bytes(),
            original_udp=(fixture.release / "udp-ports.txt").read_bytes(),
            managed_sha256=hashes)
        assert cls.effective.argv_sha256 == sha(original)
        assert cls.native.original_args_sha256 == sha(original)
        # Genuine original FD9 promoter, BEFORE the only original seal.
        plan = {"result": "prepared", "page": "strategies",
                "candidate": {"general": {"enabled": "1"}},
                "changed_fields": [], "dependencies": cls.base}
        (fixture.work / "plan.json").write_text(
            json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n")
        original_result = origin.preflight_learning_tier(
            fixture.work, cls.candidate)
        assert len(original_result["learning_native_numbers"]) == 2
        promoted = origin.promote_learning_release(fixture.work, cls.candidate)
        assert promoted["schema"] == 3
        assert origin.verify_learning_promotion(fixture.work, cls.candidate) == promoted
        assert sha((fixture.release / "dvtws.args").read_bytes()) == cls.native.proposed_args_sha256
        assert sha((fixture.release / "dvtws.original.args").read_bytes()) == cls.native.original_args_sha256
        create_seal(fixture.work, owner=os.geteuid())
        cls.original_work = fixture.work

    @classmethod
    def tearDownClass(cls):
        cls.owner_case.doCleanups()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="s10b2b1-genuine-")
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name) / "shared-work"
        self.parent.mkdir(mode=0o700)
        self.work = self.parent / self.generation
        shutil.copytree(self.original_work, self.work, copy_function=shutil.copy2)
        self.release = self.work / "release"
        self.journal_root = Path(self.tmp.name) / "journal"
        self.original = SharedApplyOperation(self.journal_root, owner=os.geteuid())
        self.original.advance("prepared", self.detail)

    def attest(self, **changes):
        args = dict(
            generation=self.generation, native=self.native, effective=self.effective,
            parent=self.parent, journal_root=self.journal_root, owner_uid=os.geteuid())
        args.update(changes)
        return _attest_original_schema3(**args)

    def test_genuine_promoted_preimage_and_final_are_distinct_and_sealed(self):
        prior = verify_seal(self.work, owner=os.geteuid())
        journal = self.original.read()
        before = {
            str(path.relative_to(self.parent)): sha(path.read_bytes())
            for path in self.parent.rglob("*") if path.is_file()}
        receipt = self.attest()
        self.assertEqual(receipt, self.attest())
        self.assertEqual(receipt.candidate_sha256, self.detail["candidate"])
        self.assertEqual(receipt.generation, self.generation)
        self.assertEqual(receipt.old_args_sha256, self.native.original_args_sha256)
        self.assertEqual(receipt.final_args_sha256, self.native.proposed_args_sha256)
        self.assertNotEqual(receipt.old_args_sha256, receipt.final_args_sha256)
        self.assertEqual(receipt.learning_native_count, 2)
        self.assertEqual(receipt.authorization, "NONE")
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertFalse(receipt.promotion_allowed)
        self.assertTrue(receipt.original_fd9_recheck_required)
        self.assertEqual(prior, verify_seal(self.work, owner=os.geteuid()))
        self.assertEqual(journal, self.original.read())
        self.assertEqual(before, {
            str(path.relative_to(self.parent)): sha(path.read_bytes())
            for path in self.parent.rglob("*") if path.is_file()})

    def test_wrong_native_sha_numbers_or_trust_authorization_refused(self):
        for change in (
            dict(original_args_sha256="f"*64),
            dict(proposed_args_sha256="f"*64),
            dict(ordinary_native_count=self.native.ordinary_native_count + 1),
            dict(learning_native_count=1),
            dict(authorization="APPLY"),
            dict(physical_transition_allowed=True),
            dict(source_map_status="ORIGINAL_NONAUTO_NO_SOURCE_MAP"),
            dict(mode="list"),
        ):
            with self.subTest(change=change):
                with self.assertRaises(OriginalSchema3Refused):
                    self.attest(native=replace(self.native, **change))

    def test_wrong_effective_original_preimage_and_mode_refused(self):
        for change in (
            dict(argv_sha256="f"*64), dict(authorization="APPLY"),
            dict(external_ref_count=1), dict(physical_transition_allowed=True),
        ):
            with self.subTest(change=change), self.assertRaises(OriginalSchema3Refused):
                self.attest(effective=replace(self.effective, **change))

    def test_tampered_original_or_promoted_argv_refused(self):
        for name in ("dvtws.original.args", "dvtws.args"):
            with self.subTest(name=name):
                target = self.release / name
                before = target.read_bytes()
                target.write_bytes(before + b"\n--filter-tcp=5\n")
                with self.assertRaises(OriginalSchema3Refused):
                    self.attest()
                target.write_bytes(before)

    def test_modified_original_and_active_maps_refused(self):
        for name in ("auto-detect-source-map.json", "auto-detect-generation.json"):
            with self.subTest(name=name):
                target = self.release / name
                before = target.read_bytes()
                target.write_bytes(before + b" ")
                with self.assertRaises(OriginalSchema3Refused):
                    self.attest()
                target.write_bytes(before)

    def test_missing_old_arg_and_second_or_torn_pending_promotion_refused(self):
        (self.release / "dvtws.original.args").unlink()
        with self.assertRaises(OriginalSchema3Refused):
            self.attest()

    def test_pending_promotion_refused(self):
        (self.release / ".dvtws.original.args.learning.pending").write_bytes(b"pending")
        with self.assertRaises(OriginalSchema3Refused):
            self.attest()

    def test_foreign_symlink_original_release_refused(self):
        original = self.release / "dvtws.original.args"
        original.unlink()
        original.symlink_to("dvtws.args")
        with self.assertRaises(OriginalSchema3Refused):
            self.attest()

    def test_wrong_journal_candidate_and_finished_phase_refused(self):
        after = {**self.detail, "candidate": "f"*64}
        bad = {**self.original.read(), "detail": after}
        self.original._persist_record(bad)
        with self.assertRaises(OriginalSchema3Refused):
            self.attest()

    def test_advance_restored_before_attestation_refused(self):
        self.original.advance("restored", self.detail)
        with self.assertRaises(OriginalSchema3Refused):
            self.attest()

    def test_wrong_generation_or_parent_refused(self):
        with self.assertRaises(OriginalSchema3Refused):
            self.attest(generation="f"*32)
        with self.assertRaises(OriginalSchema3Refused):
            self.attest(parent=self.parent / "missing")

    def test_journal_race_after_original_promoter_verification_refused(self):
        original = bridge.origin.verify_learning_promotion
        calls = []
        def race(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(True)
            self.original.advance("restored", self.detail)
            return result
        with patch.object(bridge.origin, "verify_learning_promotion", side_effect=race):
            with self.assertRaises(OriginalSchema3Refused):
                self.attest()
        self.assertEqual(calls, [True])
        self.assertEqual(self.original.read()["phase"], "restored")

    def test_original_root_fd9_absent_never_fabricates_authorization(self):
        with patch.object(bridge, "require_lifecycle_lock",
                          side_effect=RuntimeError("no original FD9")):
            with self.assertRaisesRegex(OriginalSchema3Refused, "ORIGINAL_FD9_REQUIRED"):
                attest_schema3_under_fd9(
                    generation=self.generation, native=self.native, effective=self.effective)
        self.assertEqual(self.original.read()["phase"], "prepared")


if __name__ == "__main__":
    unittest.main(verbosity=2)
