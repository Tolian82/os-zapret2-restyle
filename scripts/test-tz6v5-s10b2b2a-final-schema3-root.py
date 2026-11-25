#!/usr/bin/env python3
"""Genuine original P2e -> promoted schema3 -> detached final root RED/GREEN.

S10b2b2a does NOT enable the original FD9 PREPARED->ACTIVATING gate.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from neutral_root_manifest import RootManifestRefused, validate_candidate
from neutral_schema3_final_root import (
    FinalSchema3Refused, compile_final_schema3, validate_final_schema3,
)

spec = importlib.util.spec_from_file_location(
    "existing_s10b2b1_fixture", ROOT / "scripts/test-tz6v5-s10b2b1-original-schema3-preimage.py")
if spec is None or spec.loader is None:
    raise RuntimeError("ORIGINAL_S10B2B1_GENUINE_FIXTURE_MISSING")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


class GenuineFinalSchema3Root(unittest.TestCase):
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
        fx = self.fixture
        release = fx.release
        self.inputs = dict(
            proof=fx.attest(), native=fx.native,
            original_effective=fx.effective,
            original_args=(release / "dvtws.original.args").read_bytes(),
            final_args=(release / "dvtws.args").read_bytes(),
            original_source_map=(release / "auto-detect-source-map.json").read_bytes(),
            active_generation_map=(release / "auto-detect-generation.json").read_bytes(),
            enabled=True, owner_uid=__import__("os").geteuid(),
        )

    def compile(self, **updates):
        inputs = {**self.inputs, **updates}
        return compile_final_schema3(**inputs)

    def test_real_final_root_has_two_different_sha_and_four_original_refs(self):
        before = {str(p.relative_to(self.fixture.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.fixture.parent.rglob("*") if p.is_file()}
        root = self.compile()
        self.assertEqual(root, self.compile())
        self.assertEqual(root, validate_final_schema3(root.candidate.json_bytes, **self.inputs))
        value = json.loads(root.candidate.json_bytes)
        self.assertEqual(value["schema"], 2)
        self.assertEqual(value["service"]["target_mode"], "auto")
        self.assertEqual(value["service"]["original_structural_sha256"],
                         self.inputs["original_effective"].structural_sha256)
        self.assertNotEqual(root.structural_sha256,
                            self.inputs["original_effective"].structural_sha256)
        self.assertEqual([r["id"] for r in value["refs"]],
                         ["native_args", "original_native_args", "native_source_map",
                          "native_active_map"])
        self.assertEqual([r["mode"] for r in value["refs"]],
                         [0o644, 0o644, 0o600, 0o644])
        self.assertEqual([r["sha256"] for r in value["refs"]][:2],
                         [self.inputs["proof"].final_args_sha256,
                          self.inputs["proof"].old_args_sha256])
        self.assertEqual(value["resources"]["learning_native_numbers"],
                         [row.native_number for row in self.inputs["native"].learning_profiles])
        self.assertEqual(root.authorization, "NONE")
        self.assertFalse(root.physical_transition_allowed)
        self.assertFalse(root.promotion_allowed)
        self.assertTrue(root.original_fd9_reattest_required)
        self.assertEqual(before, {
            str(p.relative_to(self.fixture.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.fixture.parent.rglob("*") if p.is_file()})

    def test_legacy_s09_root_cannot_silently_accept_schema2(self):
        root = self.compile().candidate
        with self.assertRaises(RootManifestRefused):
            validate_candidate(
                root.json_bytes, effective=self.inputs["original_effective"],
                expected_generation=self.inputs["proof"].generation,
                expected_mode="auto", expected_enabled=True,
                original_args=self.inputs["original_args"],
                original_source_map=self.inputs["original_source_map"],
                expected_seal_sha256=self.inputs["proof"].seal_sha256,
                expected_uid=self.inputs["owner_uid"])
        with self.assertRaises(FinalSchema3Refused):
            validate_final_schema3(root.json_bytes + b" ", **self.inputs)

    def test_forged_physical_authority_never_produces_a_root(self):
        proof = self.inputs["proof"]
        for change in (
            dict(status="ORIGINAL_SCHEMA3_ACTIVATED"),
            dict(authorization="START"), dict(promotion_allowed=True),
            dict(physical_transition_allowed=True),
            dict(original_fd9_recheck_required=False),
            dict(learning_native_count=proof.learning_native_count + 1),
            dict(old_args_sha256="f"*64), dict(final_args_sha256="f"*64),
            dict(original_source_map_sha256="f"*64),
            dict(active_generation_sha256="f"*64),
            dict(seal_sha256="f"*63),
        ):
            with self.subTest(change=change), self.assertRaises(FinalSchema3Refused):
                self.compile(proof=replace(proof, **change))

    def test_changed_old_final_map_source_bytes_are_not_relabelled(self):
        for key in ("original_args", "final_args", "original_source_map",
                    "active_generation_map"):
            with self.subTest(key=key), self.assertRaises(FinalSchema3Refused):
                self.compile(**{key: self.inputs[key] + b" "})

    def test_forged_s08d_final_snapshot_or_native_numbers_refused(self):
        orig = self.inputs["original_effective"]
        native = self.inputs["native"]
        with self.assertRaises(FinalSchema3Refused):
            self.compile(original_effective=replace(
                orig, argv_sha256=self.inputs["proof"].final_args_sha256))
        with self.assertRaises(FinalSchema3Refused):
            self.compile(original_effective=replace(orig, external_ref_count=1))
        for change in (dict(mode="list"), dict(learning_native_count=0),
                       dict(proposed_args_sha256="e"*64)):
            with self.subTest(change=change), self.assertRaises(FinalSchema3Refused):
                self.compile(native=replace(native, **change))

    def test_no_root_without_original_prepared_seal(self):
        self.fixture.original.advance("restored", self.fixture.detail)
        with self.assertRaises(old.OriginalSchema3Refused):
            self.fixture.attest()
        # An earlier detached receipt alone is not a live permission: the
        # planned original-FD9 S10b2b2b consumer must reattest at use time.
        self.assertEqual(self.compile().authorization, "NONE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
