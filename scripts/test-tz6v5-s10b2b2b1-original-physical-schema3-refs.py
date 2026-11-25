#!/usr/bin/env python3
"""Genuine P2e/Voice/schema3 source -> original sealed physical refs; no activation."""
from __future__ import annotations

from dataclasses import replace
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

import neutral_schema3_physical_refs as physical
from neutral_schema3_physical_refs import (
    _attest_physical_schema3, attest_physical_schema3_under_fd9,
    PhysicalSchema3Refused,
)

spec = importlib.util.spec_from_file_location(
    "existing_s10b2b1_fixture", ROOT / "scripts/test-tz6v5-s10b2b1-original-schema3-preimage.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_S10B2B1_GENUINE_FIXTURE_MISSING")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


class OriginalPhysicalSchema3Refs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old.GenuineNativePromotedS10b2b1.setUpClass()

    @classmethod
    def tearDownClass(cls):
        old.GenuineNativePromotedS10b2b1.tearDownClass()

    def setUp(self):
        self.fixture = old.GenuineNativePromotedS10b2b1("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def attest(self, **changes):
        f = self.fixture
        args = dict(generation=f.generation, native=f.native, effective=f.effective,
                    enabled=True, parent=f.parent, journal_root=f.journal_root,
                    owner_uid=os.geteuid())
        args.update(changes)
        return _attest_physical_schema3(**args)

    def test_real_four_original_refs_are_sealed_exact_and_read_only(self):
        f = self.fixture
        before = {str(p.relative_to(f.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in f.parent.rglob("*") if p.is_file()}
        journal = f.original.read()
        receipt = self.attest()
        self.assertEqual(receipt, self.attest())
        self.assertEqual(receipt.generation, f.generation)
        self.assertEqual(receipt.candidate_sha256, f.candidate)
        self.assertNotEqual(receipt.native_ref_sha256[0][1],
                            receipt.native_ref_sha256[1][1])
        self.assertEqual([n for n, _ in receipt.native_ref_sha256],
                         ["dvtws.args", "dvtws.original.args",
                          "auto-detect-source-map.json", "auto-detect-generation.json"])
        root = json.loads(receipt.candidate.json_bytes)
        self.assertEqual(root["schema"], 2)
        self.assertEqual([ref["mode"] for ref in root["refs"]],
                         [0o644, 0o644, 0o600, 0o644])
        self.assertEqual(receipt.authorization, "NONE")
        self.assertFalse(receipt.promotion_allowed)
        self.assertFalse(receipt.physical_transition_allowed)
        self.assertTrue(receipt.original_fd9_reattest_required)
        self.assertTrue(receipt.runtime_preimages_required)
        self.assertEqual(journal, f.original.read())
        self.assertEqual(before, {
            str(p.relative_to(f.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in f.parent.rglob("*") if p.is_file()})
        self.assertFalse((f.work / "manifest.json").exists())

    def test_real_promoter_mode_drift_refused_not_reinterpreted(self):
        for name, mode in (("dvtws.args", 0o600),
                           ("dvtws.original.args", 0o600),
                           ("auto-detect-source-map.json", 0o644),
                           ("auto-detect-generation.json", 0o600)):
            with self.subTest(name=name):
                path = self.fixture.release / name
                old_mode = path.stat().st_mode & 0o777
                try:
                    path.chmod(mode)
                    with self.assertRaises(PhysicalSchema3Refused):
                        self.attest()
                finally:
                    path.chmod(old_mode)

    def test_old_or_final_args_and_active_map_tamper_refused(self):
        for name in ("dvtws.args", "dvtws.original.args",
                     "auto-detect-source-map.json", "auto-detect-generation.json"):
            with self.subTest(name=name):
                path = self.fixture.release / name
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b" ")
                    with self.assertRaises(PhysicalSchema3Refused):
                        self.attest()
                finally:
                    path.write_bytes(original)

    def test_symlink_missing_and_hardlink_native_ref_refused(self):
        path = self.fixture.release / "dvtws.args"
        original = path.read_bytes()
        path.unlink()
        path.symlink_to("dvtws.original.args")
        with self.assertRaises(PhysicalSchema3Refused):
            self.attest()
        path.unlink()
        path.write_bytes(original)
        extra = self.fixture.parent / "untrusted-hardlink"
        os.link(path, extra)
        try:
            with self.assertRaises(PhysicalSchema3Refused):
                self.attest()
        finally:
            extra.unlink()

    def test_stale_original_journal_and_native_source_refused(self):
        f = self.fixture
        f.original.advance("restored", f.detail)
        with self.assertRaises(PhysicalSchema3Refused):
            self.attest()

    def test_wrong_native_old_sha_or_original_effective_refused(self):
        with self.assertRaises(PhysicalSchema3Refused):
            self.attest(native=replace(
                self.fixture.native, proposed_args_sha256="e"*64))
        with self.assertRaises(PhysicalSchema3Refused):
            self.attest(effective=replace(
                self.fixture.effective, argv_sha256="f"*64))

    def test_race_between_original_ref_reads_refused(self):
        f = self.fixture
        original = physical._pinned_ref
        calls = []
        def swap(fd, name, mode, owner_uid):
            raw = original(fd, name, mode, owner_uid)
            if name == "dvtws.args" and not calls:
                calls.append(True)
                (f.release / name).write_bytes(raw + b" ")
            return raw
        with patch.object(physical, "_pinned_ref", side_effect=swap):
            with self.assertRaises(PhysicalSchema3Refused):
                self.attest()
        self.assertEqual(calls, [True])

    def test_absent_fd9_and_false_enabled_or_generation_refused(self):
        with patch.object(physical, "require_lifecycle_lock",
                          side_effect=RuntimeError("missing FD9")):
            with self.assertRaisesRegex(PhysicalSchema3Refused, "ORIGINAL_FD9_REQUIRED"):
                attest_physical_schema3_under_fd9(
                    generation=self.fixture.generation,
                    native=self.fixture.native, effective=self.fixture.effective,
                    enabled=True)
        for update in (dict(enabled=1), dict(generation="f"*32)):
            with self.assertRaises(PhysicalSchema3Refused):
                self.attest(**update)


if __name__ == "__main__":
    unittest.main(verbosity=2)
