#!/usr/bin/env python3
"""S10c2b1: genuine original P2e shared-build source -> managed parity.

Linux test runner exercises import-only read-only projection; installed
FreeBSD root+original FD9 alone can call the production stdin CLI. No
second runtime builder, mutable manifest, engine action or platform bypass.
"""
from __future__ import annotations

import importlib.util
from dataclasses import replace
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

import neutral_shared_apply_source_gate as gate
from neutral_shared_apply_source_gate import (
    FIELDS, MARKER, decode_pipe, qualify_source_to_managed,
    OriginalSourceGateRefused, _fixed_unclassified_reason, _owned_under_original_p2)
from neutral_resource_compiler import ResourceCompileError
from neutral_native_parity import NativeParityRefused
from shared_apply_seal import create_seal, verify_seal
from neutral_root_stage import attest_prepared_source_root, _stage_candidate, RootStageRefused
from neutral_root_bound_preflight import _attest_bound_candidate
from shared_apply_operation import SharedApplyOperation, SharedOperationError
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

    def test_fixed_native_refusal_reason_redaction(self):
        from config_projection_opnsense import NativeProjectionError
        from auto_detect_owned_sources import OwnedSourcesRefused
        from shared_apply_seal import SharedBundleError
        self.assertEqual(_fixed_unclassified_reason(NativeProjectionError("INVALID_MODEL_ATTRIBUTES")),
                         "INVALID_MODEL_ATTRIBUTES")
        self.assertEqual(_fixed_unclassified_reason(OwnedSourcesRefused("unsafe_ownership_directory")),
                         "P1_UNSAFE_OWNERSHIP_DIRECTORY")
        for error in (ValueError("private-secret.example"),
                      NativeProjectionError("private-secret.example"),
                      OwnedSourcesRefused("private-secret.example"),
                      SharedBundleError("private-secret.example")):
            code = _fixed_unclassified_reason(error)
            self.assertRegex(code, r"^[A-Z0-9_]{4,64}$")
            self.assertNotIn("private", code)

    def test_missing_file_role_is_fixed_and_no_path_leaks(self):
        missing = FileNotFoundError(2, "private-host.example",
                                    "/var/db/zapret2/shared-work/private/traffic.input")
        self.assertEqual(_fixed_unclassified_reason(missing), "MISSING_STRATEGY_INPUT")
        unknown = FileNotFoundError(2, "private-host.example",
                                    "/tmp/private-host.example")
        self.assertEqual(_fixed_unclassified_reason(unknown), "ORIGINAL_FILE_MISSING")

    def test_missing_auto_directory_requires_proven_absent_p1_for_all_list(self):
        import tempfile
        from auto_detect_owned_sources import OwnedSourcesRefused
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            work = base / "work"
            work.mkdir(mode=0o700)
            (work / "plan.json").write_text('{"page":"voice","result":"prepared"}\n')
            owned = base / "auto-detect-owned"
            auto_lock = base / "missing-auto-directory" / ".auto-domains.lock"
            with patch("auto_detect_owned_sources.OWNED_ROOT", owned), \
                 patch("auto_detect_gui_hostlist.AUTO_LOCK", auto_lock):
                for mode in (b"all", b"list"):
                    self.assertIsNone(_owned_under_original_p2(
                        work, os.geteuid(), mode=mode))
                with self.assertRaises(FileNotFoundError):
                    _owned_under_original_p2(work, os.geteuid(), mode=b"auto")
                owned.mkdir(mode=0o700)
                with self.assertRaisesRegex(
                    OriginalSourceGateRefused, "P1_OWNER_PRESENT_BUT_GUI_LOCK_ABSENT"):
                    _owned_under_original_p2(work, os.geteuid(), mode=b"all")

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

    def test_same_original_source_to_prepared_and_bound_root(self):
        for mode in ("all", "list", "auto"):
            with self.subTest(mode=mode):
                fixture, kw = self.original(mode=mode, voice=True)
                self.original_plan(fixture)
                digest = "d" * 64
                if mode == "auto":
                    origin.promote_learning_release(fixture.work, digest)
                create_seal(fixture.work, owner=os.geteuid())
                source = qualify_source_to_managed(
                    **dict(kw, sealed=True, engine_version="v1.0.7"))
                self.assertEqual(source.effective.argv_sha256, source.original_args_sha256)
                self.assertEqual(source.native.original_args_sha256, source.original_args_sha256)
                journal_root = fixture.work.parent / "journal"
                journal = SharedApplyOperation(journal_root, owner=os.geteuid())
                detail = {"id": fixture.work.name, "page": "strategies",
                          "base": "a" * 64, "candidate": digest, "changed_fields": []}
                journal.advance("prepared", detail)
                before = journal.read()
                args = dict(source=source, candidate_sha256=digest, enabled=True,
                            parent=fixture.work.parent, journal_root=journal_root,
                            owner_uid=os.geteuid())
                with self.assertRaises(RootStageRefused):
                    attest_prepared_source_root(**dict(args, candidate_sha256="c" * 64))
                for altered in (replace(source, original_seal_sha256="0" * 64),
                                replace(source, final_args_sha256="0" * 64),
                                replace(source, candidate_input_sha256="0" * 64)):
                    with self.assertRaises(RootStageRefused):
                        attest_prepared_source_root(**dict(args, source=altered))
                candidate = attest_prepared_source_root(**args)
                self.assertEqual(journal.read(), before)
                self.assertFalse((fixture.work / "manifest.json").exists())
                self.assertFalse(candidate.physical_transition_allowed)
                common = dict(generation=fixture.work.name, native=source.native,
                              effective=source.effective, mode=mode, enabled=True,
                              parent=fixture.work.parent, journal_root=journal_root,
                              owner_uid=os.geteuid(), schema3=mode == "auto")
                staged = _stage_candidate(candidate=candidate, **common)
                with patch("voice_ipfw_adapter.require_lifecycle_lock", return_value=None):
                    bound = journal.bind_prepared_manifest(
                        generation=fixture.work.name, effective=source.effective,
                        native=source.native, mode=mode, enabled=True,
                        shared_work_parent=fixture.work.parent, schema3=mode == "auto")
                recheck = _attest_bound_candidate(**common)
                self.assertEqual(staged.root_sha256, candidate.sha256)
                self.assertEqual(bound["manifest"]["root_sha256"], candidate.sha256)
                self.assertEqual(recheck.root_sha256, candidate.sha256)
                self.assertEqual(journal.read()["phase"], "prepared")
                # Original source can be re-read only with its exact pinned
                # sibling. The normal unbound source path still refuses it.
                with self.assertRaises(OriginalSourceGateRefused):
                    qualify_source_to_managed(
                        **dict(kw, sealed=True, engine_version="v1.0.7"))
                self.assertEqual(qualify_source_to_managed(
                    **dict(kw, sealed=True, engine_version="v1.0.7",
                           bound_root_sha256=bound["manifest"]["root_sha256"])), source)
                with self.assertRaises(OriginalSourceGateRefused):
                    qualify_source_to_managed(
                        **dict(kw, sealed=True, engine_version="v1.0.7",
                               bound_root_sha256="0" * 64))
                with self.assertRaises(SharedOperationError):
                    journal.advance("activating", detail)


    def test_s10_bound_original_fd9_to_real_sealed_s08d_for_all_list_auto(self):
        """Genuine original source with simulated native owner; NEVER a Start."""
        from unittest.mock import patch
        for mode in ("all", "list", "auto"):
            with self.subTest(mode=mode):
                fixture, kw = self.original(mode=mode, voice=True)
                self.original_plan(fixture)
                if mode == "auto":
                    origin.promote_learning_release(fixture.work,
                                                    kw["candidate_sha256"])
                create_seal(fixture.work, owner=os.geteuid())
                expected = qualify_source_to_managed(
                    **dict(kw, sealed=True, engine_version="v1.0.7"))
                wire = MARKER + b"\0" + b"\0".join(
                    kw["inputs"][name] for name in FIELDS) + b"\0"
                bound = {
                    "engine_version": "v1.0.7", "source_commit": "a" * 40,
                    "engine_sha256": "b" * 64,
                    "status": "S10_ORIGINAL_BOUND_ENGINE_VERSION_READ_ONLY",
                    "authorization": "NONE",
                    "physical_transition_allowed": False,
                    "build_provenance_verified": False,
                }
                calls = []

                def original(operation, payload, digest=None, *,
                             sealed=False, engine_version=None):
                    calls.append((operation, payload, digest,
                                  sealed, engine_version))
                    # The outer native-entry check must see synthetic
                    # FreeBSD uid=0. This disposable P2e tree is actually
                    # owned by the CI user: restore THAT real owner while
                    # the genuine Auto promoter reattests its file inodes.
                    with patch.object(gate.os, "geteuid",
                                      return_value=kw["owner_uid"]):
                        return qualify_source_to_managed(**dict(
                            kw, sealed=sealed, engine_version=engine_version))

                args = (fixture.work.name, wire,
                        kw["candidate_sha256"] if mode == "auto" else None)
                original_bytes = ((fixture.release / "dvtws.args").read_bytes(),
                                  (fixture.work / "bundle-seal.json").read_bytes())
                with patch.object(gate.sys, "platform", "freebsd15"), \
                     patch.object(gate.os, "geteuid", return_value=0), \
                     patch("voice_ipfw_adapter.require_lifecycle_lock"), \
                     patch.object(gate, "_s10_native_bound_engine_readback",
                                  side_effect=[bound, bound]), \
                     patch.object(gate, "native_original_fd9",
                                  side_effect=original):
                    observed = gate.native_original_bound_effective_fd9(*args)
                self.assertEqual(observed, expected)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0],
                                 (args[0], wire, args[2], True, "v1.0.7"))
                self.assertEqual(observed.effective.argv_sha256,
                                 observed.native.original_args_sha256)
                self.assertEqual(observed.effective.authorization, "NONE")
                self.assertFalse(observed.effective.physical_transition_allowed)
                self.assertEqual(
                    original_bytes,
                    ((fixture.release / "dvtws.args").read_bytes(),
                     (fixture.work / "bundle-seal.json").read_bytes()))

    def test_s10_native_engine_recheck_and_refusal_do_not_activate(self):
        from types import SimpleNamespace
        id = "a" * 32
        wire = MARKER + b"\0" + b"mock\0"
        identity = {
            "engine_version": "v1.0.7", "source_commit": "a" * 40,
            "engine_sha256": "b" * 64,
            "status": "S10_ORIGINAL_BOUND_ENGINE_VERSION_READ_ONLY",
            "authorization": "NONE", "physical_transition_allowed": False,
            "build_provenance_verified": False,
        }
        model = SimpleNamespace(
            generation=id, status="ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY",
            authorization="NONE", physical_transition_allowed=False,
            native=SimpleNamespace(original_args_sha256="c" * 64),
            effective=SimpleNamespace(argv_sha256="c" * 64),
            original_args_sha256="c" * 64,
            original_seal_sha256="d" * 64)
        with patch.object(gate.sys, "platform", "linux"), \
             patch.object(gate, "_s10_native_bound_engine_readback") as rd:
            with self.assertRaisesRegex(OriginalSourceGateRefused,
                                        "NATIVE_ORIGINAL_FD9_REQUIRED"):
                gate.native_original_bound_effective_fd9(id, wire)
            rd.assert_not_called()
        with patch.object(gate.sys, "platform", "freebsd15"), \
             patch.object(gate.os, "geteuid", return_value=0), \
             patch("voice_ipfw_adapter.require_lifecycle_lock",
                   side_effect=RuntimeError("no inherited FD9")), \
             patch.object(gate, "_s10_native_bound_engine_readback") as rd:
            with self.assertRaises(RuntimeError):
                gate.native_original_bound_effective_fd9(id, wire)
            rd.assert_not_called()
        for altered in (
                {"authorization": "START"},
                {"physical_transition_allowed": True},
                {"build_provenance_verified": True},
                {"status": "legacy-display-only"},
                {"engine_version": "forged=bad"},
                {"engine_sha256": "not-a-digest"},
                {"foreign": "unowned"},
        ):
            with self.subTest(altered=altered), \
                 patch.object(gate.sys, "platform", "freebsd15"), \
                 patch.object(gate.os, "geteuid", return_value=0), \
                 patch("voice_ipfw_adapter.require_lifecycle_lock"), \
                 patch.object(gate, "_s10_native_bound_engine_readback",
                              return_value={**identity, **altered}), \
                 patch.object(gate, "native_original_fd9") as original:
                with self.assertRaisesRegex(OriginalSourceGateRefused,
                                            "S10_BOUND_ENGINE_UNQUALIFIED"):
                    gate.native_original_bound_effective_fd9(id, wire)
                original.assert_not_called()
        # An apparently valid original bundle is NOT a backdoor to an
        # activating receipt; fake/wrong typed source is always rejected.
        with patch.object(gate.sys, "platform", "freebsd15"), \
             patch.object(gate.os, "geteuid", return_value=0), \
             patch("voice_ipfw_adapter.require_lifecycle_lock"), \
             patch.object(gate, "_s10_native_bound_engine_readback",
                          return_value=identity), \
             patch.object(gate, "native_original_fd9", return_value=model):
            with self.assertRaisesRegex(OriginalSourceGateRefused,
                                        "S10_EFFECTIVE_SOURCE_UNQUALIFIED"):
                gate.native_original_bound_effective_fd9(id, wire)
        # Even an authentic typed source cannot pass if the original
        # setup-bound ELF changes during the independent source recheck.
        fixture, kw = self.original(mode="list", voice=True)
        self.original_plan(fixture)
        create_seal(fixture.work, owner=os.geteuid())
        qualified = qualify_source_to_managed(
            **dict(kw, sealed=True, engine_version="v1.0.7"))
        changed = {**identity, "engine_sha256": "f" * 64}
        with patch.object(gate.sys, "platform", "freebsd15"), \
             patch.object(gate.os, "geteuid", return_value=0), \
             patch("voice_ipfw_adapter.require_lifecycle_lock"), \
             patch.object(gate, "_s10_native_bound_engine_readback",
                          side_effect=[identity, changed]), \
             patch.object(gate, "native_original_fd9",
                          return_value=qualified):
            with self.assertRaisesRegex(OriginalSourceGateRefused,
                                        "S10_BOUND_ENGINE_CHANGED"):
                gate.native_original_bound_effective_fd9(fixture.work.name, wire)

    def test_s10_cli_only_accepts_explicit_sealed_original_protocol(self):
        import contextlib
        import io
        from types import SimpleNamespace
        id = "a" * 32
        digest = "d" * 64
        stdout = io.StringIO()
        receipt = SimpleNamespace(
            effective=SimpleNamespace(structural_sha256="e" * 64))
        for argv, expected_digest in (
                ([id, "--sealed", "--s10-effective"], None),
                ([id, digest, "--sealed", "--s10-effective"], digest)):
            with self.subTest(argv=argv), \
                 patch.object(gate.sys, "stdin",
                              SimpleNamespace(buffer=io.BytesIO(b"input"))), \
                 patch.object(gate, "native_original_bound_effective_fd9",
                              return_value=receipt) as native, \
                 contextlib.redirect_stdout(stdout):
                self.assertEqual(gate.main(argv), 0)
                native.assert_called_once_with(id, b"input", expected_digest)
        self.assertEqual(stdout.getvalue(),
                         ("S10_ORIGINAL_EFFECTIVE_INPUT_READ_ONLY=" +
                          "e" * 64 + "\n") * 2)
        for invalid in (
                [id, "--s10-effective"],
                [id, digest, "--s10-effective"],
                [id, "--sealed", "--s10-effective", "foreign"],
                [id, "--s10-effective", "--sealed"],
                [id, digest, "--s10-effective", "--sealed"],
                [id, "--sealed", digest, "--s10-effective"],
        ):
            with self.subTest(invalid=invalid), \
                 patch.object(gate, "native_original_bound_effective_fd9") as native:
                self.assertEqual(gate.main(invalid), 64)
                native.assert_not_called()



    def test_one_original_prepared_source_binding_all_list_auto(self):
        """Same original P2e tree, root writer and WAL; no activator."""
        import xml.etree.ElementTree as ET
        from neutral_schema3_saved_wan_preimage import SavedWanPreimageRefused
        for mode in ("all", "list", "auto"):
            with self.subTest(mode=mode):
                fixture, kw = self.original(mode=mode, voice=True)
                # This existing portable P2e fixture omits general.enabled
                # from XML, although its original rendered shell uses "1".
                # Supply the corresponding model scalar before sealing.
                xml = fixture.work / "candidate.xml"
                tree = ET.parse(xml)
                ET.SubElement(tree.find("./OPNsense/Zapret/general"),
                              "enabled").text = "1"
                strategy = ET.SubElement(tree.find("./OPNsense/Zapret"), "strategy")
                ET.SubElement(strategy, "trafficargs").text = STRATEGY
                tree.write(xml, encoding="utf-8")
                self.original_plan(fixture)
                digest = "d" * 64
                if mode == "auto":
                    origin.promote_learning_release(fixture.work, digest)
                create_seal(fixture.work, owner=os.geteuid())
                source = qualify_source_to_managed(
                    **dict(kw, sealed=True, engine_version="v1.0.7"))
                self.assertIs(source.requested_enabled, True)
                store = SharedApplyOperation(fixture.work.parent / "journal",
                                             owner=os.geteuid())
                detail = {"id": fixture.work.name, "page": "strategies",
                          "base": "a" * 64, "candidate": digest, "changed_fields": []}
                before = store.advance("prepared", detail)
                config = {"result": "prepared", "base": detail["base"],
                          "snapshot": digest, "candidate": digest,
                          "enabled": "1", "changes": 0, "fields": []}
                root = fixture.work / "manifest.json"
                args = dict(store=store, parent=fixture.work.parent,
                            before=before, source=source,
                            read_config=lambda: config, config_receipt=config)
                with patch("voice_ipfw_adapter.require_lifecycle_lock"):
                    with self.assertRaises(SavedWanPreimageRefused):
                        gate._bind_original_prepared_source(
                            **dict(args, config_receipt={**config, "enabled": "0"}))
                    self.assertFalse(root.exists())
                    with self.assertRaises(SavedWanPreimageRefused):
                        gate._bind_original_prepared_source(
                            **dict(args, read_config=lambda: {**config, "base": "b" * 64}))
                    self.assertEqual(store.read(), before)
                    self.assertFalse(root.exists())
                    receipt = gate._bind_original_prepared_source(**args)
                    bound = store.read()
                    self.assertEqual(bound["phase"], "prepared")
                    self.assertEqual(bound["manifest"]["schema"],
                                     2 if mode == "auto" else 1)
                    self.assertEqual(bound["manifest"]["root_sha256"],
                                     hashlib.sha256(root.read_bytes()).hexdigest())
                    self.assertEqual(bound["manifest"]["root_sha256"],
                                     receipt.root_sha256)
                    pinned = dict(detail=detail, binding=bound["manifest"],
                                  parent=fixture.work.parent, sources=BACKEND,
                                  owner_uid=os.geteuid(), engine_version="v1.0.7")
                    old = gate._read_pinned_effective(**pinned)
                    self.assertEqual(old, (source.effective, True))
                    self.assertEqual(gate.plan(old[0], source.effective).kind,
                                     "NO_CHANGE")
                    with self.assertRaises(OriginalSourceGateRefused):
                        gate._read_pinned_effective(**dict(
                            pinned, engine_version="v99.0.1"))
                    # traffic.input is outside the original seal; the
                    # old semantic read must still reject source drift.
                    traffic = fixture.work / "traffic.input"
                    original_traffic = traffic.read_bytes()
                    try:
                        traffic.write_bytes(b"--filter-tcp=1234\n")
                        with self.assertRaisesRegex(OriginalSourceGateRefused,
                                                    "PINNED_STRATEGY_MISMATCH"):
                            gate._read_pinned_effective(**pinned)
                    finally:
                        traffic.write_bytes(original_traffic)
                    self.assertEqual(gate._read_pinned_effective(**pinned), old)
                    # Original producer inputs are needed at creation,
                    # not a durable second configuration for the old root.
                    traffic.unlink()
                    self.assertEqual(gate._read_pinned_effective(**pinned), old)
                    self.assertEqual(receipt.authorization, "NONE")
                    self.assertFalse(receipt.physical_transition_allowed)
                    with self.assertRaises(OriginalSourceGateRefused):
                        gate._bind_original_prepared_source(**args)
                    self.assertEqual(store.read(), bound)
                    with self.assertRaises(SharedOperationError):
                        store.advance("activating", detail)
                    self.assertEqual(store.read(), bound)
                    recovered = store.recover_prepared(
                        fixture.work.name, lambda: bool(verify_seal(
                            fixture.work, owner=os.geteuid())),
                        shared_work_parent=fixture.work.parent)
                    self.assertEqual(recovered["phase"], "restored")
                    self.assertEqual(recovered["manifest"], bound["manifest"])
                    self.assertTrue(root.is_file())

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


    def test_s10_ordinary_reload_fences_unproven_multi_list_changes(self):
        from neutral_effective_diff import EffectiveSnapshot, plan
        links = (("hostlist-youtube.txt", "1" * 64),
                 ("hostlist-user.txt", "2" * 64))
        draft = (("hostlist-exclude.txt", "3" * 64),)
        old = EffectiveSnapshot("4" * 64, "5" * 64, links, draft, 0)
        single = replace(old, linked=((links[0][0], "6" * 64), links[1]))
        multi = replace(single, linked=(single.linked[0], (links[1][0], "7" * 64)))
        mixed = replace(single, unlinked=((draft[0][0], "8" * 64),))
        inactive = replace(old, unlinked=mixed.unlinked)
        self.assertEqual(plan(old, multi).kind, "RELOAD_SAFE_CANDIDATE")
        for after, expected in ((old, "NO_CHANGE"), (single, "RELOAD_SAFE_CANDIDATE"),
                                (multi, "RESTART_REQUIRED"), (mixed, "RESTART_REQUIRED"),
                                (inactive, "SAVE_ONLY"),
                                (replace(single, structural_sha256="9" * 64), "RESTART_REQUIRED")):
            with self.subTest(expected=expected):
                decision = gate._ordinary_effective_decision((old, True), (after, True))
                self.assertEqual(decision.kind, expected)
                self.assertEqual(decision.changed_active, plan(old, after).changed_active)
                self.assertEqual(decision.changed_inactive, plan(old, after).changed_inactive)
                self.assertFalse(decision.physical_transition_allowed)
                self.assertEqual(gate._running_lifecycle_proposal(False, decision), "STOP")
        self.assertEqual(gate._ordinary_effective_decision(None, (single, True)).kind,
                         "RESTART_REQUIRED")

    def test_s10_locked_running_recheck_uses_same_original_source_and_decision(self):
        from contextlib import ExitStack
        from unittest.mock import Mock
        from neutral_effective_diff import EffectiveSnapshot
        from neutral_schema3_previous_physical import (
            CompletePriorPreimage, LockedRunningPredecessor, PriorRunningToken)
        op, old_id = "a" * 32, "b" * 32
        base, candidate, seal, root, old_root = (c * 64 for c in "cdef1")
        old = EffectiveSnapshot("2" * 64, "3" * 64,
                                (("hostlist-youtube.txt", "4" * 64),), (), 0)
        new = replace(old, linked=(("hostlist-youtube.txt", "5" * 64),))
        source = gate.SourceGateReceipt("list", "6" * 64, (),
            generation=op, original_seal_sha256=seal, effective=new,
            requested_enabled=True)
        preimage = CompletePriorPreimage(op, root, old_id, "7" * 64, "7" * 64,
            base, "tun0", 5432, "birth", 6543, "monitor-birth", "8" * 64)
        semantic = gate.OriginalSemanticReceipt(op, old_id, root, old_root,
            gate._ordinary_effective_decision((old, True), (new, True)), preimage,
            lifecycle_proposal="RELOAD")
        record = {"phase": "prepared", "detail": {"id": op, "base": base,
                  "candidate": candidate}, "previous": {"id": old_id, "candidate": base},
                  "manifest": {"root_sha256": root, "seal_sha256": seal},
                  "previous_manifest": {"root_sha256": old_root}}
        physical = LockedRunningPredecessor(op, old_id, old_root, base, "7" * 64,
            PriorRunningToken(5432, "birth", 6543, "monitor-birth", "8" * 64), None)
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate.sys, "platform", "freebsd15"))
            stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
            stack.enter_context(patch("voice_ipfw_adapter.require_lifecycle_lock"))
            stack.enter_context(patch("auto_detect_original_lock_handoff.assert_inherited_config_fd"))
            store = stack.enter_context(patch("shared_apply_operation.SharedApplyOperation",
                return_value=Mock(read=Mock(return_value=record))))
            stack.enter_context(patch.object(gate, "decode_pipe", return_value={"mode": b"list"}))
            stack.enter_context(patch.object(gate, "_s10_native_bound_engine_readback",
                return_value={"engine_version": "v1.0.7", "engine_sha256": "a" * 64}))
            fresh = stack.enter_context(patch.object(gate, "native_original_bound_effective_fd9",
                return_value=source))
            stack.enter_context(patch.object(gate, "_read_pinned_effective", side_effect=
                lambda *, detail, **kw: (new if detail["id"] == op else old, True)))
            attested = stack.enter_context(patch(
                "neutral_schema3_previous_physical.attest_bound_running_predecessor_under_fd9",
                return_value=physical))
            nested = stack.enter_context(patch.object(gate, "native_plan_original_prepared_fd9"))
            exe = stack.enter_context(patch(
                "neutral_schema3_previous_physical._running_executable_identity",
                return_value=(1, 2, "a" * 64)))
            running = stack.enter_context(patch(
                "neutral_schema3_previous_physical._running_native", return_value=physical.running))

            def run(**kw):
                args = dict(source=source, semantic=semantic, config_fd=4, config_digest=base)
                args.update(kw)
                return gate.native_recheck_running_prepared_fd9(op, b"original", **args)

            self.assertEqual(run(), replace(physical, executable_identity=(1, 2, "a" * 64)))
            self.assertEqual(exe.call_count, 2)
            self.assertEqual(running.call_count, 2)
            exe.side_effect = ((1, 2, "a" * 64), (1, 3, "a" * 64))
            with self.assertRaises(gate.OriginalSourceGateRefused):
                run()
            exe.side_effect = None
            self.assertEqual(fresh.call_count, 4)
            fresh.assert_called_with(op, b"original", None, bound_record=record)
            self.assertEqual(attested.call_count, 4)
            nested.assert_not_called()
            for bad in (dict(config_fd=9), dict(config_digest=candidate),
                        dict(semantic=replace(semantic, lifecycle_proposal="RESTART")),
                        dict(semantic=replace(semantic, promotion_allowed=True))):
                with self.assertRaises(gate.OriginalSourceGateRefused):
                    run(**bad)
            fresh.side_effect = (source, replace(source, candidate_input_sha256="9" * 64))
            with self.assertRaises(gate.OriginalSourceGateRefused):
                run()
            fresh.side_effect = None
            attested.side_effect = (physical, replace(physical, epoch_sha256="a" * 64))
            with self.assertRaises(gate.OriginalSourceGateRefused):
                run()
            attested.side_effect = None
            store.return_value.read.return_value = {**record, "phase": "activating"}
            with self.assertRaises(gate.OriginalSourceGateRefused):
                run()
            store.return_value._persist_record.assert_not_called()
            store.return_value._advance_bound_ordinary.assert_not_called()
            nested.assert_not_called()

    def test_s10_running_enabled_off_stop_overrides_legacy_restart_and_pinned_no_change(self):
        """Injected old running process: identical S08d can NEVER suppress STOP.

        Actual P2e source/native/effective data is used, but the disabled
        bound candidate, previous pinned snapshot and physical old-owner
        observation are injected: this is NOT installed FreeBSD proof.
        """
        from contextlib import ExitStack
        from unittest.mock import Mock
        from neutral_schema3_previous_physical import CompletePriorPreimage
        from neutral_schema3_previous_preimage import PreviousRuntimeReceipt

        fixture, kw = self.original(mode="list", voice=True)
        import xml.etree.ElementTree as ET
        xml = fixture.work / "candidate.xml"
        tree = ET.parse(xml)
        ET.SubElement(tree.find("./OPNsense/Zapret/general"), "enabled").text = "1"
        strategy = ET.SubElement(tree.find("./OPNsense/Zapret"), "strategy")
        ET.SubElement(strategy, "trafficargs").text = STRATEGY
        tree.write(xml, encoding="utf-8")
        self.original_plan(fixture)
        create_seal(fixture.work, owner=os.geteuid())
        genuine = qualify_source_to_managed(
            **dict(kw, sealed=True, engine_version="v1.0.7"))
        self.assertEqual(genuine.status, "ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY")
        self.assertIs(genuine.requested_enabled, True)
        disabled = replace(genuine, requested_enabled=False)
        old_id = "e" * 32 if genuine.generation != "e" * 32 else "f" * 32
        old = {"id": old_id, "candidate": "a" * 64}
        detail = {"id": genuine.generation, "base": old["candidate"]}
        manifest = {"root_sha256": "4" * 64,
                    "seal_sha256": genuine.original_seal_sha256}
        physical = CompletePriorPreimage(
            genuine.generation, manifest["root_sha256"], old_id,
            "5" * 64, "5" * 64, old["candidate"], None,
            5432, "native-child-birth", 6543, "native-monitor-birth",
            "6" * 64)
        original_files = {
            file.name: file.read_bytes()
            for file in (fixture.work / "candidate.xml",
                         fixture.work / "bundle-seal.json")}
        for pinned in (False, True):
            with self.subTest(old_pinned=pinned), ExitStack() as stack:
                before = {"phase": "prepared", "detail": detail,
                          "previous": old, "manifest": manifest}
                if pinned:
                    before["previous_manifest"] = {"root_sha256": "8" * 64}
                store = Mock(read=Mock(return_value=before))
                stack.enter_context(patch(
                    "shared_apply_operation.SharedApplyOperation",
                    return_value=store))
                stack.enter_context(patch(
                    "voice_ipfw_adapter.require_lifecycle_lock"))
                stack.enter_context(patch.object(gate.sys, "platform", "freebsd"))
                stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
                engine = stack.enter_context(patch.object(
                    gate, "_s10_native_bound_engine_readback",
                    return_value={"engine_version": "v1.0.7"}))
                def pinned_read(*, detail, **unused):
                    return genuine.effective, detail["id"] != genuine.generation
                read = stack.enter_context(patch.object(
                    gate, "_read_pinned_effective", side_effect=pinned_read))
                state = PreviousRuntimeReceipt(
                    genuine.generation, manifest["root_sha256"],
                    old_id, old["candidate"], "ready", 5, 2)
                previous_read = stack.enter_context(patch(
                    "neutral_schema3_previous_preimage.attest_prepared_previous_under_fd9",
                    return_value=state))
                native = stack.enter_context(patch(
                    "neutral_schema3_previous_physical.attest_previous_physical_under_fd9",
                    return_value=physical))
                result = gate.native_plan_original_prepared_fd9(disabled)
                self.assertEqual(result.lifecycle_proposal, "STOP")
                self.assertEqual(result.decision.kind,
                                 "NO_CHANGE" if pinned else "RESTART_REQUIRED")
                self.assertEqual(result.previous_generation, old_id)
                self.assertEqual(result.candidate_root_sha256,
                                 manifest["root_sha256"])
                self.assertIs(result.previous_physical, physical)
                self.assertEqual(result.authorization, "NONE")
                self.assertFalse(result.physical_transition_allowed)
                self.assertFalse(result.promotion_allowed)
                self.assertTrue(result.final_original_fd9_reattest_required)
                self.assertGreaterEqual(read.call_count, 2)
                self.assertEqual(engine.call_count, 2)
                previous_read.assert_called_once_with(
                    generation=genuine.generation,
                    native=genuine.native,
                    effective=genuine.effective, enabled=False)
                native.assert_called_once_with(
                    generation=genuine.generation,
                    native=genuine.native,
                    effective=genuine.effective, enabled=False)
                self.assertEqual(store.read(), before)
        self.assertEqual({
            file.name: file.read_bytes()
            for file in (fixture.work / "candidate.xml",
                         fixture.work / "bundle-seal.json")}, original_files)

    def test_s10_running_off_refuses_incomplete_owner_and_active_wan_forgery(self):
        """Synthetic seams refuse before any lifecycle dispatcher/action."""
        from contextlib import ExitStack
        from unittest.mock import Mock
        from neutral_schema3_previous_physical import (
            CompletePriorPreimage, PreviousPhysicalRefused)
        from neutral_schema3_previous_preimage import PreviousRuntimeReceipt
        from neutral_effective_diff import EffectiveSnapshot
        from neutral_native_parity import NativeParity
        # Strict exact-type check runs before any filesystem or physical probe.
        malformed = gate.SourceGateReceipt(
            mode="list", candidate_input_sha256="a" * 64,
            managed_locators=(),
            status="ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY",
            generation="d" * 32, original_seal_sha256="e" * 64,
            native=NativeParity(
                "list", "a" * 64, "a" * 64, "ORIGINAL_NONAUTO_NO_SOURCE_MAP",
                0, 1, 0, (), (), "a" * 64, 19000, 19099),
            effective=EffectiveSnapshot("a" * 64, "a" * 64, (), (), 0),
            requested_enabled="0")
        with patch("voice_ipfw_adapter.require_lifecycle_lock"), \
             patch.object(gate.sys, "platform", "freebsd"), \
             patch.object(gate.os, "geteuid", return_value=0), \
             patch.object(gate, "_s10_native_bound_engine_readback") as engine, \
             self.assertRaises(OriginalSourceGateRefused):
            gate.native_plan_original_prepared_fd9(malformed)
        engine.assert_not_called()

        # No running-owner physical proof means no STOP proposal. The
        # original stopped/cold reader is NOT a fallback for this route.
        genuine = gate.SourceGateReceipt(
            mode="list", candidate_input_sha256="a" * 64,
            managed_locators=(),
            status="ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY",
            generation="d" * 32, original_seal_sha256="e" * 64,
            native=NativeParity(
                "list", "a" * 64, "a" * 64, "ORIGINAL_NONAUTO_NO_SOURCE_MAP",
                0, 1, 0, (), (), "a" * 64, 19000, 19099),
            effective=EffectiveSnapshot("a" * 64, "a" * 64, (), (), 0),
            requested_enabled=False)
        previous = {"id": "f" * 32, "candidate": "b" * 64}
        before = {"phase": "prepared",
                  "detail": {"id": genuine.generation, "base": "b" * 64},
                  "previous": previous,
                  "manifest": {"root_sha256": "c" * 64,
                               "seal_sha256": genuine.original_seal_sha256}}
        def pinned_read(*, detail, **unused):
            return genuine.effective, False
        for case in ("old-owner-failed", "unexpected-wan", "journal-raced"):
            with self.subTest(case=case), ExitStack() as stack:
                store = Mock(read=Mock(return_value=before))
                if case == "journal-raced":
                    store.read.side_effect = [before, {**before, "phase": "restored"}]
                stack.enter_context(patch(
                    "shared_apply_operation.SharedApplyOperation", return_value=store))
                stack.enter_context(patch(
                    "voice_ipfw_adapter.require_lifecycle_lock"))
                stack.enter_context(patch.object(gate.sys, "platform", "freebsd"))
                stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
                stack.enter_context(patch.object(
                    gate, "_s10_native_bound_engine_readback",
                    return_value={"engine_version": "v1.0.7"}))
                stack.enter_context(patch.object(
                    gate, "_read_pinned_effective", side_effect=pinned_read))
                witness = CompletePriorPreimage(
                    genuine.generation, "c" * 64, previous["id"],
                    "d" * 64, "d" * 64, previous["candidate"],
                    "tun0", 1, "birth", 2, "birth", "e" * 64)
                state = PreviousRuntimeReceipt(
                    genuine.generation, "c" * 64, previous["id"],
                    previous["candidate"], "ready", 5, 2)
                stack.enter_context(patch(
                    "neutral_schema3_previous_preimage.attest_prepared_previous_under_fd9",
                    return_value=state))
                native = stack.enter_context(patch(
                    "neutral_schema3_previous_physical.attest_previous_physical_under_fd9",
                    side_effect=(PreviousPhysicalRefused("unsafe")
                                 if case == "old-owner-failed" else None),
                    return_value=witness))
                with self.assertRaises(OriginalSourceGateRefused):
                    gate.native_plan_original_prepared_fd9(genuine)
                if case == "journal-raced":
                    native.assert_called_once()


    def test_s10_stopped_and_strict_cold_proposals_never_authorize_action(self):
        """Synthetic owner/FD9 result seams; original physical proofs stay unmodified.

        This test intentionally does NOT claim an installed stopped owner.
        The other S10 tests attest the actual P2e root in isolation.
        """
        from contextlib import ExitStack
        from unittest.mock import Mock
        from neutral_effective_diff import EffectiveSnapshot
        from neutral_native_parity import NativeParity
        from neutral_schema3_previous_preimage import PreviousRuntimeReceipt
        from neutral_schema3_quiescent_preimage import QuiescentPreimage

        effective = EffectiveSnapshot("a" * 64, "a" * 64, (), (), 0)
        native = NativeParity(
            "list", "a" * 64, "a" * 64, "ORIGINAL_NONAUTO_NO_SOURCE_MAP",
            0, 1, 0, (), (), "a" * 64, 19000, 19099)
        source = gate.SourceGateReceipt(
            mode="list", candidate_input_sha256="a" * 64,
            managed_locators=(), status="ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY",
            generation="d" * 32, original_seal_sha256="e" * 64,
            native=native, effective=effective, requested_enabled=True)
        detail = {"id": source.generation, "base": "b" * 64,
                  "candidate": "c" * 64}
        pin = {"root_sha256": "4" * 64,
               "seal_sha256": source.original_seal_sha256}
        former = {"id": "f" * 32, "candidate": detail["base"]}
        cases = (
            ("stopped-off", True, False, False, "SAVE_ONLY"),
            ("stopped-on", True, True, False, "START"),
            ("stopped-pinned-off", True, False, True, "SAVE_ONLY"),
            ("stopped-pinned-on", True, True, True, "START"),
            ("stopped-pinned-idle", True, True, True, "START"),
            ("cold-off", False, False, False, "SAVE_ONLY"),
            ("cold-on", False, True, False, "START"),
        )
        for name, has_prior, enabled, pinned, action in cases:
            with self.subTest(name=name), ExitStack() as stack:
                candidate = replace(source, requested_enabled=enabled)
                record = {"phase": "prepared", "detail": detail,
                          "manifest": pin}
                if has_prior:
                    record["previous"] = former
                if pinned:
                    record["previous_manifest"] = {"root_sha256": "5" * 64}
                store = Mock(read=Mock(return_value=record))
                stack.enter_context(patch(
                    "shared_apply_operation.SharedApplyOperation", return_value=store))
                lock = stack.enter_context(patch(
                    "voice_ipfw_adapter.require_lifecycle_lock"))
                stack.enter_context(patch.object(gate.sys, "platform", "freebsd"))
                stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
                engine = stack.enter_context(patch.object(
                    gate, "_s10_native_bound_engine_readback",
                    return_value={"engine_version": "v1.0.7"}))
                old_enabled = False  # prior STOPPED can be saved as OFF
                def pinned_effective(*, detail, **unused):
                    return (effective,
                            enabled if detail["id"] == source.generation
                            else old_enabled)
                read = stack.enter_context(patch.object(
                    gate, "_read_pinned_effective", side_effect=pinned_effective))
                observed = PreviousRuntimeReceipt(
                    candidate.generation, pin["root_sha256"],
                    former["id"], former["candidate"], "stopped", 0, 0)
                previous_read = stack.enter_context(patch(
                    "neutral_schema3_previous_preimage.attest_prepared_previous_under_fd9",
                    return_value=observed))
                proof = QuiescentPreimage(
                    candidate.generation, pin["root_sha256"],
                    former["id"] if has_prior else None,
                    "6" * 64 if has_prior else None,
                    detail["base"], detail["candidate"],
                    "tun0" if enabled else None,
                    "committed-stopped" if has_prior else "first-install-empty",
                    "native-managed-kernel-empty",
                    ("inert-idle-producer" if name == "stopped-pinned-idle" else
                     "inert-no-producer-data" if has_prior else "no-prior-data"),
                    idle_producer=((1, 2, 0, "a" * 64), (1, 3, 0, "a" * 64))
                    if name == "stopped-pinned-idle" else None)
                quiescent = stack.enter_context(patch(
                    "neutral_schema3_quiescent_preimage.attest_quiescent_under_fd9",
                    return_value=proof))
                running = stack.enter_context(patch(
                    "neutral_schema3_previous_physical.attest_previous_physical_under_fd9"))
                result = gate.native_plan_original_prepared_fd9(candidate)
                self.assertEqual(result.lifecycle_proposal, action)
                self.assertEqual(result.decision.kind,
                                 "NO_CHANGE" if pinned else "RESTART_REQUIRED")
                self.assertEqual(result.previous_generation,
                                 former["id"] if has_prior else None)
                self.assertEqual(result.previous_root_sha256,
                                 "5" * 64 if pinned else None)
                self.assertIs(result.previous_physical, proof)
                self.assertEqual(result.authorization, "NONE")
                self.assertFalse(result.physical_transition_allowed)
                self.assertFalse(result.promotion_allowed)
                self.assertTrue(result.final_original_fd9_reattest_required)
                self.assertEqual(engine.call_count, 2)
                self.assertEqual(read.call_count, 4 if pinned else 2)
                self.assertGreaterEqual(lock.call_count, 2)
                if has_prior:
                    previous_read.assert_called_once()
                else:
                    previous_read.assert_not_called()
                quiescent.assert_called_once_with(
                    generation=candidate.generation, native=native,
                    effective=effective, enabled=enabled)
                running.assert_not_called()
                self.assertEqual(store.read(), record)
                if name == "stopped-pinned-idle":
                    for idle in (None, (), ((1, 2), (1, 3))):
                        quiescent.return_value = replace(proof, idle_producer=idle)
                        with self.assertRaises(gate.OriginalSourceGateRefused):
                            gate.native_plan_original_prepared_fd9(candidate)

    def test_s10_wrong_state_incomplete_owner_cannot_fall_through(self):
        """A READY failure never becomes STOPPED; bad cold cannot become START."""
        from contextlib import ExitStack
        from unittest.mock import Mock
        from neutral_effective_diff import EffectiveSnapshot
        from neutral_native_parity import NativeParity
        from neutral_schema3_previous_preimage import PreviousRuntimeReceipt
        from neutral_schema3_previous_physical import PreviousPhysicalRefused
        from neutral_schema3_quiescent_preimage import (
            QuiescentPreimage, QuiescentPreimageRefused)

        effective = EffectiveSnapshot("a" * 64, "a" * 64, (), (), 0)
        native = NativeParity(
            "list", "a" * 64, "a" * 64, "ORIGINAL_NONAUTO_NO_SOURCE_MAP",
            0, 1, 0, (), (), "a" * 64, 19000, 19099)
        source = gate.SourceGateReceipt(
            "list", "a" * 64, (),
            status="ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY",
            generation="d" * 32, original_seal_sha256="e" * 64,
            native=native, effective=effective, requested_enabled=True)
        former = {"id": "f" * 32, "candidate": "b" * 64}
        detail = {"id": source.generation, "base": former["candidate"],
                  "candidate": "c" * 64}
        pin = {"root_sha256": "4" * 64, "seal_sha256": source.original_seal_sha256}
        for case in ("ready-old-owner-failed", "stopped-retirement-failed",
                     "cold-foreign-active", "stopped-wan-forged",
                     "stopped-unknown", "cold-has-prior-pin"):
            with self.subTest(case=case), ExitStack() as stack:
                cold = case.startswith("cold-")
                record = {"phase": "prepared", "detail": detail, "manifest": pin}
                if not cold:
                    record["previous"] = former
                if case == "cold-has-prior-pin":
                    record["previous_manifest"] = {"root_sha256": "5" * 64}
                store = Mock(read=Mock(return_value=record))
                stack.enter_context(patch(
                    "shared_apply_operation.SharedApplyOperation", return_value=store))
                stack.enter_context(patch(
                    "voice_ipfw_adapter.require_lifecycle_lock"))
                stack.enter_context(patch.object(gate.sys, "platform", "freebsd"))
                stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
                engine = stack.enter_context(patch.object(
                    gate, "_s10_native_bound_engine_readback",
                    return_value={"engine_version": "v1.0.7"}))
                candidate = (replace(source, requested_enabled=False)
                             if case == "stopped-wan-forged" else source)
                stack.enter_context(patch.object(
                    gate, "_read_pinned_effective",
                    return_value=(effective, candidate.requested_enabled)))
                state = ("ready" if case == "ready-old-owner-failed"
                         else "foreign" if case == "stopped-unknown"
                         else "stopped")
                previous = stack.enter_context(patch(
                    "neutral_schema3_previous_preimage.attest_prepared_previous_under_fd9",
                    return_value=PreviousRuntimeReceipt(
                        source.generation, pin["root_sha256"],
                        former["id"], former["candidate"], state, 0, 0)))
                running = stack.enter_context(patch(
                    "neutral_schema3_previous_physical.attest_previous_physical_under_fd9",
                    side_effect=PreviousPhysicalRefused("native-owner-missing")))
                proof = QuiescentPreimage(
                    source.generation, pin["root_sha256"],
                    former["id"] if not cold else None,
                    "6" * 64 if not cold else None,
                    detail["base"], detail["candidate"],
                    "tun0", "committed-stopped" if not cold else "first-install-empty",
                    "native-managed-kernel-empty",
                    "inert-no-producer-data" if not cold else "no-prior-data")
                if case == "cold-foreign-active":
                    proof = replace(proof, old_state="committed-stopped",
                                    previous_generation=former["id"])
                # An OFF candidate must refuse a fabricated active WAN.
                quiescent = stack.enter_context(patch(
                    "neutral_schema3_quiescent_preimage.attest_quiescent_under_fd9",
                    side_effect=(QuiescentPreimageRefused("retirement-incomplete")
                                 if case == "stopped-retirement-failed" else None),
                    return_value=proof))
                with self.assertRaises(OriginalSourceGateRefused):
                    gate.native_plan_original_prepared_fd9(candidate)
                if case == "ready-old-owner-failed":
                    running.assert_called_once()
                    quiescent.assert_not_called()
                elif case in ("stopped-retirement-failed", "stopped-wan-forged"):
                    running.assert_not_called()
                    quiescent.assert_called_once()
                else:
                    running.assert_not_called()
                if case == "cold-has-prior-pin":
                    engine.assert_not_called()
                    previous.assert_not_called()
                    quiescent.assert_not_called()
                self.assertEqual(store.read(), record)


    def test_s10_found_prepared_source_cas_readonly(self):
        """Injected native lock/CAS seams, never a physical Found qualification."""
        from contextlib import ExitStack, contextmanager
        from unittest.mock import Mock
        from neutral_effective_diff import EffectiveSnapshot
        from neutral_native_parity import NativeParity
        from auto_detect_destination_commit import DestinationRefused

        raw = b'{"sealed":"original-found-plan"}'
        seal = b'{"sealed":"original-bundle"}'
        operation = "d" * 32
        detail = {"id": operation, "base": "b" * 64, "candidate": "c" * 64}
        expected = gate.SourceGateReceipt(
            "list", "a" * 64, (),
            status="ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY",
            generation=operation, original_seal_sha256=hashlib.sha256(seal).hexdigest(),
            native=NativeParity("list", "a" * 64, "a" * 64,
                                "ORIGINAL_NONAUTO_NO_SOURCE_MAP",
                                0, 1, 0, (), (), "a" * 64, 19000, 19099),
            effective=EffectiveSnapshot("a" * 64, "a" * 64, (), (), 0),
            requested_enabled=True)
        inputs = original_input(STRATEGY, mode="list", exclude="", exclude_ipset="")
        wire = MARKER + b"\0" + b"\0".join(inputs[k] for k in FIELDS) + b"\0"
        for case in ("ok", "wrong-phase", "wrong-plan", "prior-pin",
                     "old-config-drift", "first-cas", "late-cas",
                     "wrong-seal", "journal-drift", "plan-drift",
                     "config-fd-lost"):
            with self.subTest(case=case), ExitStack() as stack:
                record = {"phase": "prepared", "detail": detail,
                          "found": {"plan_sha256": hashlib.sha256(raw).hexdigest()}}
                if case == "wrong-phase":
                    record["phase"] = "found-files-writing"
                if case == "wrong-plan":
                    record["found"]["plan_sha256"] = "0" * 64
                if case == "prior-pin":
                    record["previous_manifest"] = {}
                if case == "old-config-drift":
                    record["previous"] = {"candidate": "0" * 64}
                store = Mock()
                store.read.return_value = record
                rows = {"original": "rows"}
                targets = {"original": "targets"}
                verified = {"validated": "rows"}
                held = [False]
                @contextmanager
                def p2(*args):
                    self.assertFalse(held[0], "recursive P2")
                    held[0] = True
                    try:
                        yield
                    finally:
                        held[0] = False

                def attest():
                    self.assertTrue(held[0])
                    if case == "config-fd-lost" and cas.call_count:
                        raise DestinationRefused("config_fd_changed")
                    return True

                def observe(*args, **kwargs):
                    self.assertTrue(held[0])
                    if case == "first-cas" or (case == "late-cas" and cas.call_count == 2):
                        raise DestinationRefused("planned_preimage_drift")

                def source(*args):
                    self.assertFalse(held[0], "source reader needs same P2")
                    if case == "journal-drift":
                        store.read.return_value = {**record, "phase": "restored"}
                    return (replace(expected, original_seal_sha256="0" * 64)
                            if case == "wrong-seal" else expected)

                stack.enter_context(patch.object(gate.sys, "platform", "freebsd"))
                stack.enter_context(patch.object(gate.os, "geteuid", return_value=0))
                stack.enter_context(patch("voice_ipfw_adapter.require_lifecycle_lock"))
                context = stack.enter_context(patch(
                    "auto_detect_destination_commit._native_found_wal_context",
                    return_value=(store, record, raw, rows, targets, attest)))
                stack.enter_context(patch(
                    "auto_detect_destination_commit._qualified_shared_found_batch",
                    return_value=verified))
                stack.enter_context(patch(
                    "auto_detect_destination_commit.exclusive_destination_lock",
                    side_effect=p2))
                cas = stack.enter_context(patch(
                    "auto_detect_effective_known._verify_planned_preimages_locked",
                    side_effect=observe))
                stack.enter_context(patch.object(
                    gate, "_read", side_effect=lambda path, *args:
                        seal if path.name == "bundle-seal.json" else
                        (b"changed" if case == "plan-drift" else raw)))
                bridge = stack.enter_context(patch.object(
                    gate, "native_original_bound_effective_fd9", side_effect=source))
                if case == "ok":
                    receipt = gate.native_attest_found_prepared_fd9(operation, wire, 4)
                    self.assertIs(receipt.source, expected)
                    self.assertEqual(receipt.plan_sha256, hashlib.sha256(raw).hexdigest())
                    self.assertEqual(receipt.config_base_sha256, detail["base"])
                    self.assertEqual(receipt.config_candidate_sha256, detail["candidate"])
                    self.assertEqual(receipt.authorization, "NONE")
                    self.assertFalse(receipt.physical_transition_allowed)
                    self.assertFalse(receipt.promotion_allowed)
                    self.assertTrue(receipt.final_original_fd9_reattest_required)
                    self.assertEqual(cas.call_count, 2)
                    bridge.assert_called_once_with(operation, wire, None)
                else:
                    with self.assertRaises(OriginalSourceGateRefused):
                        gate.native_attest_found_prepared_fd9(operation, wire, 4)
                context.assert_called_once_with(operation, 4)
                store._persist_record.assert_not_called()
                store.advance.assert_not_called()
                store.bind_prepared_manifest.assert_not_called()
                self.assertFalse(held[0])


    def test_found_root_binding_preserves_original_source_fence_and_p2(self):
        from contextlib import ExitStack, contextmanager
        from unittest.mock import Mock
        from neutral_root_stage import PreparedRootReceipt

        operation = "d" * 32
        base = "b" * 64
        candidate_sha = "c" * 64
        plan = b'{"sealed":"original-found-plan"}'
        seal = b'{"sealed":"original-bundle"}'
        plan_sha = hashlib.sha256(plan).hexdigest()
        seal_sha = hashlib.sha256(seal).hexdigest()
        old = {"id": "e" * 32, "candidate": base}
        old_pin = {"generation": old["id"], "root_sha256": "a" * 64}
        pending = {"phase": "prepared", "detail": {
            "id": operation, "base": base, "candidate": candidate_sha},
            "found": {"plan_sha256": plan_sha}, "previous": old,
            "previous_manifest": old_pin}
        source = gate.SourceGateReceipt(
            "list", "f" * 64, (), generation=operation,
            original_args_sha256="a" * 64, final_args_sha256="a" * 64,
            original_seal_sha256=seal_sha, requested_enabled=False)
        first = gate.FoundPreparedSourceReceipt(source, plan_sha, base, candidate_sha)
        staged = PreparedRootReceipt(operation, "1" * 64, seal_sha, candidate_sha)
        bound = dict(pending, manifest={
            "schema": 1, "generation": operation, "root_sha256": staged.root_sha256,
            "seal_sha256": seal_sha, "candidate_sha256": candidate_sha})

        for drift in ("none", "base", "prebind", "postbind"):
            with self.subTest(drift=drift), ExitStack() as stack:
                held = [False]
                state = [pending]
                store = Mock()
                store.read.side_effect = lambda: state[0]
                store.root = Path("/disposable/journal")
                @contextmanager
                def p2(*args):
                    self.assertFalse(held[0], "nested original P2")
                    held[0] = True
                    try:
                        yield
                    finally:
                        held[0] = False
                def original_source(*args, **kwargs):
                    self.assertFalse(held[0], "original source reader needs P2")
                    self.assertEqual(state[0], pending)
                    return first
                def stage(**kwargs):
                    self.assertTrue(held[0])
                    self.assertEqual(kwargs["found_plan_sha256"], plan_sha)
                    return staged
                def bind(**kwargs):
                    self.assertTrue(held[0])
                    self.assertEqual(kwargs["found_plan_sha256"], plan_sha)
                    state[0] = bound
                    return bound
                def cas(*args, **kwargs):
                    self.assertTrue(held[0])
                    if ((drift == "prebind" and check.call_count == 2) or
                            (drift == "postbind" and check.call_count == 3)):
                        raise ValueError("simulated CAS drift")

                store.bind_prepared_manifest.side_effect = bind
                stack.enter_context(patch("voice_ipfw_adapter.require_lifecycle_lock"))
                stack.enter_context(patch.object(gate, "_s10_native_bound_engine_readback",
                                                 return_value={"engine": "same"}))
                stack.enter_context(patch(
                    "auto_detect_destination_commit._native_found_wal_context",
                    return_value=(store, pending, plan, {}, {}, lambda: True)))
                stack.enter_context(patch(
                    "auto_detect_destination_commit._qualified_shared_found_batch",
                    return_value={}))
                stack.enter_context(patch(
                    "auto_detect_destination_commit.exclusive_destination_lock",
                    side_effect=p2))
                check = stack.enter_context(patch(
                    "auto_detect_effective_known._verify_planned_preimages_locked",
                    side_effect=cas))
                reader = stack.enter_context(patch.object(
                    gate, "native_attest_found_prepared_fd9", side_effect=original_source))
                candidate = Mock(sha256=staged.root_sha256)
                stack.enter_context(patch("neutral_root_stage.attest_prepared_source_root",
                                          return_value=candidate))
                writer = stack.enter_context(patch("neutral_root_stage._stage_candidate",
                                                   side_effect=stage))
                stack.enter_context(patch("neutral_root_stage._verify_original_pinned_root"))
                stack.enter_context(patch.object(
                    gate, "_read", side_effect=lambda path, *args:
                    seal if path.name == "bundle-seal.json" else plan))
                if drift == "none":
                    self.assertEqual(gate.native_bind_found_prepared_fd9(
                        operation, b"native-wire", 4, config_digest=base), (first, staged))
                    self.assertEqual(state[0], bound)
                    self.assertEqual(check.call_count, 3)
                else:
                    with self.assertRaises(OriginalSourceGateRefused):
                        gate.native_bind_found_prepared_fd9(
                            operation, b"native-wire", 4,
                            config_digest="0" * 64 if drift == "base" else base)
                    self.assertEqual(state[0], bound if drift == "postbind" else pending)
                if drift == "base":
                    reader.assert_not_called()
                    writer.assert_not_called()
                else:
                    reader.assert_called_once_with(
                        operation, b"native-wire", 4, _expected_record=pending)
                self.assertFalse(held[0])


    def test_found_bound_semantic_uses_existing_diff_and_original_p2(self):
        from contextlib import ExitStack, contextmanager
        from unittest.mock import Mock
        from neutral_effective_diff import EffectiveSnapshot
        from neutral_native_parity import NativeParity
        from neutral_root_bound_preflight import BoundRootReceipt

        op, old_id = "d" * 32, "e" * 32
        base, digest, seal, root_sha = "a" * 64, "b" * 64, "c" * 64, "d" * 64
        raw = b"original sealed found plan"
        plan_sha = hashlib.sha256(raw).hexdigest()
        prior = {"id": old_id, "candidate": base}
        pin = {"schema": 1, "root_sha256": root_sha,
               "seal_sha256": seal, "candidate_sha256": digest}
        old_pin = {"schema": 1, "root_sha256": "e" * 64}
        links = (("hostlist-youtube.txt", "1" * 64),
                 ("hostlist-user.txt", "2" * 64))
        old_effective = EffectiveSnapshot("3" * 64, "4" * 64, links, (), 0)
        changed = (("hostlist-youtube.txt", "5" * 64), links[1])
        candidate = replace(old_effective, linked=changed)
        native = NativeParity("list", "4" * 64, "4" * 64, "absent",
                              0, 1, 0, (), (), "6" * 64, 19000, 19001)
        for case in ("legacy", "single", "multiple-active", "multiple-source",
                     "stopped", "disabled", "bad-base", "cas-drift", "pid-drift",
                     "epoch", "epoch-drift", "epoch-refusal"):
            with self.subTest(case=case), ExitStack() as stack:
                effective = (replace(candidate, linked=(changed[0],
                    ("hostlist-user.txt", "7" * 64)))
                    if case == "multiple-active" else candidate)
                enabled = case != "disabled"
                source = gate.SourceGateReceipt(
                    "list", "8" * 64, (),
                    status="ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY",
                    generation=op, original_seal_sha256=seal,
                    native=native, effective=effective, requested_enabled=enabled)
                witness = gate.FoundPreparedSourceReceipt(
                    source, plan_sha, base, digest)
                before = {"phase": "prepared", "detail": {
                    "id": op, "base": base, "candidate": digest},
                    "found": {"plan_sha256": plan_sha}, "previous": prior,
                    "manifest": pin}
                if case != "legacy":
                    before["previous_manifest"] = {
                        **old_pin, "schema": 2 if case.startswith("epoch") else 1}
                store = Mock(read=Mock(return_value=before))
                store.root = Path("/disposable/journal")
                verified = {"youtube": (b"old", b"new"), "auto": (
                    b"old", b"new" if case == "multiple-source" else b"old")}
                held = [False]

                @contextmanager
                def p2(*args):
                    self.assertFalse(held[0])
                    held[0] = True
                    try:
                        yield
                    finally:
                        held[0] = False

                def check(*args, **kwargs):
                    self.assertTrue(held[0])
                    if case == "cas-drift" and cas.call_count == 2:
                        raise ValueError("changed original preimage")

                def read_pinned(*, detail, **kwargs):
                    self.assertTrue(held[0])
                    return (effective, enabled) if detail["id"] == op else (
                        old_effective, True)

                stack.enter_context(patch("voice_ipfw_adapter.require_lifecycle_lock"))
                stack.enter_context(patch(
                    "auto_detect_destination_commit._native_found_wal_context",
                    return_value=(store, before, raw, {}, {}, lambda: True)))
                stack.enter_context(patch(
                    "auto_detect_destination_commit._qualified_shared_found_batch",
                    return_value=verified))
                stack.enter_context(patch(
                    "auto_detect_destination_commit.exclusive_destination_lock", side_effect=p2))
                cas = stack.enter_context(patch(
                    "auto_detect_effective_known._verify_planned_preimages_locked", side_effect=check))
                stack.enter_context(patch.object(gate, "_s10_native_bound_engine_readback",
                                                 return_value={"engine_version": "v1.0.7"}))
                stack.enter_context(patch.object(gate, "_read_pinned_effective",
                                                 side_effect=read_pinned))
                bound = stack.enter_context(patch(
                    "neutral_root_bound_preflight._attest_bound_candidate",
                    return_value=BoundRootReceipt(op, root_sha, seal, digest)))
                stack.enter_context(patch(
                    "voice_live_inspect.examine_pending_found_previous",
                    return_value={"id": old_id,
                                  "state": "stopped" if case == "stopped" else "ready"}))
                stack.enter_context(patch(
                    "neutral_schema3_previous_physical._full_prior_tree",
                    return_value="9" * 64))
                from types import SimpleNamespace
                runtime = SimpleNamespace(pid=1733, started="birth")
                running = stack.enter_context(patch(
                    "neutral_schema3_previous_physical._running_native",
                    side_effect=[runtime, SimpleNamespace(pid=1733, started="other-birth")
                                 if case == "pid-drift" else runtime]))
                learning = SimpleNamespace(operation_id=old_id, generation=old_id,
                    owner_candidate_sha256=base, owner=runtime)
                epoch = stack.enter_context(patch(
                    "auto_detect_owner.attest_prepared_found_learning_predecessor",
                    side_effect=(ValueError("epoch absent") if case == "epoch-refusal"
                                 else [(learning, "1" * 64),
                                       (learning, ("2" if case == "epoch-drift" else "1") * 64)])))
                if case in ("bad-base", "cas-drift", "pid-drift",
                            "epoch-drift", "epoch-refusal"):
                    with self.assertRaises(OriginalSourceGateRefused):
                        gate.native_plan_found_prepared_fd9(
                            witness, 4, config_digest="0" * 64 if case == "bad-base" else base)
                else:
                    receipt = gate.native_plan_found_prepared_fd9(witness, 4, config_digest=base)
                    self.assertEqual(receipt.decision.kind,
                        "RELOAD_SAFE_CANDIDATE" if case in ("single", "stopped", "epoch")
                        else "RESTART_REQUIRED")
                    self.assertEqual(receipt.reload_candidate, case in ("single", "epoch"))
                    self.assertEqual(receipt.previous_running_epoch_sha256,
                                     "1" * 64 if case == "epoch" else None)
                    self.assertEqual(epoch.call_count, 2 if case == "epoch" else 0)
                    self.assertEqual(receipt.authorization, "NONE")
                    self.assertFalse(receipt.physical_transition_allowed)
                    self.assertFalse(receipt.promotion_allowed)
                    self.assertEqual(receipt.plan_sha256, plan_sha)
                    self.assertEqual(receipt.previous_root_sha256,
                                     None if case == "legacy" else old_pin["root_sha256"])
                    self.assertEqual(bound.call_count, 2)
                    self.assertEqual(bound.call_args.kwargs["found_plan_sha256"], plan_sha)
                    self.assertEqual(cas.call_count, 2)
                    self.assertEqual(running.call_count, 0 if case == "stopped" else 2)
                store._persist_record.assert_not_called()
                store.advance.assert_not_called()
                store.bind_prepared_manifest.assert_not_called()
                self.assertFalse(held[0])

if __name__ == "__main__":
    unittest.main(verbosity=2)
