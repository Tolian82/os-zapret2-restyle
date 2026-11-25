#!/usr/bin/env python3
"""S10c2b1: genuine original P2e shared-build source -> managed parity.

Linux test runner exercises import-only read-only projection; installed
FreeBSD root+original FD9 alone can call the production stdin CLI. No
second runtime builder, mutable manifest, engine action or platform bypass.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from neutral_shared_apply_source_gate import (
    FIELDS, MARKER, decode_pipe, qualify_source_to_managed,
    OriginalSourceGateRefused)
from neutral_resource_compiler import ResourceCompileError
from neutral_native_parity import NativeParityRefused
from shared_apply_seal import create_seal, verify_seal
import auto_detect_origin_map as origin
import hashlib

BUILDER = ROOT / "scripts/test-p2e-original-shared-build.py"
STRATEGY = (
    "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
    "--new\n--filter-udp=443\n<IPSET:telegram>\n--lua-desync=fake\n"
    "--new\n--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n"
    "--new\n--filter-tcp=80\n<HOSTLIST:youtube>\n--lua-desync=fake\n"
    "--new\n--filter-udp=3478\n<IPSET:telegram>\n--lua-desync=fake\n"
)


def original_builder():
    spec = importlib.util.spec_from_file_location("s10c2b1_original", BUILDER)
    if spec is None or spec.loader is None:
        raise AssertionError("ORIGINAL_P2E_FIXTURE_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def original_input(strategy: str, *, mode: str, exclude: str,
                   exclude_ipset: str) -> dict[str, bytes]:
    values = {
        "strategy": strategy, "youtube": "youtube.com", "user": "example.org",
        "telegram": "91.108.13.10", "discord": "", "x": "", "sip": "",
        "custom": "", "exclude_domains": exclude,
        "exclude_ipset": exclude_ipset,
        "mode": mode, "port": "19899", "wan": "lo0",
    }
    assert set(values) == set(FIELDS)
    return {name: value.encode("utf-8") for name, value in values.items()}


class OriginalFd9SourceGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p2e = original_builder()

    def original(self, *, mode="auto", voice=False, exclude="", exclude_ipset=""):
        fixture = self.p2e.OriginalSharedGeneration("runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.build(STRATEGY, mode=mode, voice_on=voice,
                      exclude_domains=exclude, exclude_ipset=exclude_ipset,
                      rule_max="19099")
        inputs = original_input(STRATEGY, mode=mode, exclude=exclude,
                                exclude_ipset=exclude_ipset)
        keyword = {"work": fixture.work, "sources": BACKEND,
                   "inputs": inputs, "owned_known": None,
                   "owner_uid": os.geteuid(),
                   "active_managed": fixture.active / "managed",
                   # The source-only P2e fixture has no protected PHP
                   # preflight; native production MUST supply that actual SHA.
                   "candidate_sha256": "d" * 64 if mode == "auto" else None}
        return fixture, keyword

    def original_plan(self, fixture):
        # Genuine original P2e builder produces candidate.xml and release;
        # shared_apply_request.php normally owns this sibling plan on FD9.
        (fixture.work / "plan.json").write_text(
            __import__("json").dumps({
                "result": "prepared", "page": "strategies",
                "candidate": {"general": {"enabled": "1"}},
                "changed_fields": [], "dependencies": "a" * 64,
            }, sort_keys=True, separators=(",", ":")) + "\n")

    def test_stdin_original_scalars_are_bounded_and_lossless(self):
        inputs = original_input(STRATEGY, mode="list", exclude="",
                                exclude_ipset="")
        input_bytes = MARKER + b"\0" + b"\0".join(inputs[name] for name in FIELDS) + b"\0"
        self.assertEqual(decode_pipe(input_bytes), inputs)
        for bad in (b"", input_bytes[:-1], b"UNKNOWN\0" + input_bytes,
                    input_bytes + b"extra\0"):
            with self.subTest(bad=bad[:20]), self.assertRaises(OriginalSourceGateRefused):
                decode_pipe(bad)

    def test_real_original_all_list_auto_and_voice_with_five_ordered_profiles(self):
        for mode in ("all", "list", "auto"):
            for voice in (False, True):
                with self.subTest(mode=mode, voice=voice):
                    fixture, kw = self.original(
                        mode=mode, voice=voice, exclude="ads.example.org",
                        exclude_ipset="203.0.113.0/24")
                    before = (fixture.release / "dvtws.args").read_bytes()
                    proof = qualify_source_to_managed(**kw)
                    self.assertEqual(proof.status,
                                     "ORIGINAL_NONACTIVATING_SOURCE_MANAGED_PARITY")
                    self.assertEqual(proof.mode, mode)
                    self.assertEqual(proof.authorization, "NONE")
                    self.assertFalse(proof.physical_transition_allowed)
                    self.assertEqual(len(proof.managed_locators), 9)
                    self.assertEqual(proof.original_args_sha256,
                                     __import__("hashlib").sha256(before).hexdigest())
                    self.assertGreaterEqual(proof.native_profile_count, 5)
                    self.assertIn(proof.native_source_map_status,
                                  ("ORIGINAL_NONAUTO_NO_SOURCE_MAP",
                                   "ORIGINAL_NONACTIVATING_MAP_AND_OWNER_INDEPENDENT_PROPOSAL"))
                    if mode != "auto":
                        self.assertEqual(proof.known_learning_count, 0)
                    self.assertEqual(before, (fixture.release / "dvtws.args").read_bytes())
                    self.assertFalse((fixture.release / "auto-detect-generation.json").exists())

    def test_real_original_changed_source_and_generated_bytes_refuse(self):
        fixture, kw = self.original(mode="list", exclude="ads.example.org",
                                    exclude_ipset="203.0.113.0/24")
        self.assertTrue(qualify_source_to_managed(**kw).managed_locators)
        data = dict(kw["inputs"], youtube=b"not-the-original.example.org")
        with self.assertRaises(ResourceCompileError):
            qualify_source_to_managed(**dict(kw, inputs=data))
        data = dict(kw["inputs"], mode=b"all")
        with self.assertRaises(OriginalSourceGateRefused):
            qualify_source_to_managed(**dict(kw, inputs=data))
        file = fixture.release / "managed" / "ipset-telegram.txt"
        file.write_bytes(file.read_bytes() + b"203.0.113.3\n")
        with self.assertRaises(ResourceCompileError):
            qualify_source_to_managed(**kw)

    def test_auto_requires_php_digest_and_exact_original_map(self):
        fixture, kw = self.original(mode="auto", voice=True,
                                    exclude="ads.example.org",
                                    exclude_ipset="198.51.100.0/24")
        self.assertTrue(qualify_source_to_managed(**kw).original_args_sha256)
        for digest in (None, "", "g" * 64, "a" * 63):
            with self.subTest(digest=digest), self.assertRaises(
                    OriginalSourceGateRefused):
                qualify_source_to_managed(**dict(kw, candidate_sha256=digest))
        src = fixture.release / "auto-detect-source-map.json"
        original = src.read_bytes()
        record = __import__("json").loads(original)
        record["final_args_sha256"] = "0" * 64
        src.write_text(__import__("json").dumps(record))
        with self.assertRaises(NativeParityRefused):
            qualify_source_to_managed(**kw)

    def test_original_argv_voice_ipfw_and_nonautos_tamper_refused(self):
        for mode in ("auto", "list", "all"):
            with self.subTest(mode=mode):
                fixture, kw = self.original(
                    mode=mode, voice=True, exclude="ads.example.org",
                    exclude_ipset="203.0.113.0/24")
                result = qualify_source_to_managed(**kw)
                self.assertGreater(result.native_profile_count, 0)
                file = fixture.release / "voice-plan.json"
                original = file.read_bytes()
                plan = __import__("json").loads(original)
                plan["capture"]["ordinary_rule_base"] = 19099
                file.write_text(__import__("json").dumps(plan))
                with self.assertRaises(NativeParityRefused):
                    qualify_source_to_managed(**kw)
                file.write_bytes(original)
                args = fixture.release / "dvtws.args"
                args.write_bytes(args.read_bytes().replace(b"--port=19899\n", b"--port=19900\n", 1))
                with self.assertRaises(NativeParityRefused):
                    qualify_source_to_managed(**kw)

    def test_nonautos_forbid_map_or_auto_digest(self):
        fixture, kw = self.original(mode="list")
        with self.assertRaises(OriginalSourceGateRefused):
            qualify_source_to_managed(
                **dict(kw, candidate_sha256="d" * 64))
        (fixture.release / "auto-detect-source-map.json").write_text("{}")
        with self.assertRaises(OriginalSourceGateRefused):
            qualify_source_to_managed(**kw)

    def test_real_original_final_seal_all_list_and_promoted_auto(self):
        for mode in ("all", "list", "auto"):
            for voice in (False, True):
                with self.subTest(mode=mode, voice=voice):
                    fixture, kw = self.original(
                        mode=mode, voice=voice, exclude="ads.example.org",
                        exclude_ipset="203.0.113.0/24")
                    before = qualify_source_to_managed(**kw)
                    self.original_plan(fixture)
                    if mode == "auto":
                        candidate = kw["candidate_sha256"]
                        original = origin.preflight_learning_tier(fixture.work, candidate)
                        self.assertGreater(len(original["learning_native_numbers"]), 0)
                        origin.promote_learning_release(fixture.work, candidate)
                        self.assertEqual(
                            origin.verify_learning_promotion(fixture.work, candidate)["schema"], 3)
                    create_seal(fixture.work, owner=os.geteuid())
                    sealed = qualify_source_to_managed(**dict(kw, sealed=True))
                    self.assertEqual(sealed.status, "ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY")
                    self.assertEqual(sealed.authorization, "NONE")
                    self.assertFalse(sealed.physical_transition_allowed)
                    self.assertEqual(sealed.original_args_sha256, before.original_args_sha256)
                    self.assertEqual(
                        sealed.final_args_sha256,
                        hashlib.sha256((fixture.release / "dvtws.args").read_bytes()).hexdigest())
                    self.assertEqual(
                        sealed.original_seal_sha256,
                        hashlib.sha256((fixture.work / "bundle-seal.json").read_bytes()).hexdigest())
                    self.assertEqual(verify_seal(fixture.work, owner=os.geteuid())["id"],
                                     fixture.work.name)
                    if mode == "auto":
                        self.assertNotEqual(sealed.final_args_sha256, before.original_args_sha256)
                    else:
                        self.assertEqual(sealed.final_args_sha256, before.original_args_sha256)

    def test_final_seal_ref_and_native_drift_refuse_without_action(self):
        fixture, kw = self.original(mode="auto", voice=True)
        self.assertEqual(qualify_source_to_managed(**kw).mode, "auto")
        self.original_plan(fixture)
        origin.promote_learning_release(fixture.work, kw["candidate_sha256"])
        create_seal(fixture.work, owner=os.geteuid())
        self.assertTrue(qualify_source_to_managed(**dict(kw, sealed=True)).original_seal_sha256)
        with self.assertRaises((ValueError, RuntimeError)):
            qualify_source_to_managed(
                **dict(kw, sealed=True, candidate_sha256="c" * 64))
        target = fixture.release / "auto-detect-generation.json"
        original = target.read_bytes()
        target.write_bytes(original + b" ")
        with self.assertRaises((ValueError, RuntimeError)):
            qualify_source_to_managed(**dict(kw, sealed=True))
        target.write_bytes(original)
        self.assertTrue(qualify_source_to_managed(**dict(kw, sealed=True)).original_seal_sha256)

    def test_sealed_root_collision_and_unsealed_refuse(self):
        fixture, kw = self.original(mode="list")
        with self.assertRaises((ValueError, RuntimeError, OSError)):
            qualify_source_to_managed(**dict(kw, sealed=True))
        self.original_plan(fixture)
        create_seal(fixture.work, owner=os.geteuid())
        self.assertTrue(qualify_source_to_managed(**dict(kw, sealed=True)).original_seal_sha256)
        extra = fixture.work / "manifest.json"
        extra.write_text("{}")
        with self.assertRaises((ValueError, RuntimeError)):
            qualify_source_to_managed(**dict(kw, sealed=True))
        extra.unlink()
        (fixture.release / "dvtws.original.args").write_bytes(b"forged")
        with self.assertRaises((ValueError, RuntimeError)):
            qualify_source_to_managed(**dict(kw, sealed=True))

    def test_original_registry_and_source_map_are_not_reconstructed(self):
        fixture, kw = self.original(mode="auto")
        path = fixture.work / "storage-catalog.tsv"
        saved = path.read_bytes()
        path.write_bytes(saved + b"ipset.foreign\tmanaged\tforeign.txt\n")
        with self.assertRaises(OriginalSourceGateRefused):
            qualify_source_to_managed(**kw)
        # A failed read-only witness never changes the original native argv.
        self.assertIn(b"--port=19899", (fixture.release / "dvtws.args").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
