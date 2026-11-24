#!/usr/bin/env python3
"""TZ6v5 S09b: real original sealed file refs + deterministic tamper negatives.

No engine, service, config writer, original FD9 or IPFW is touched. The
actual native-builder cases use the existing S08c/P2e original generator.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from neutral_effective_diff import EffectiveSnapshot, snapshot
from neutral_native_parity import NativeParity
from neutral_root_manifest import compile_candidate
from neutral_root_refs import attest_sealed_original, SealedRefsRefused
from shared_apply_seal import create_seal

GEN = "0123456789abcdef0123456789abcdef"
ARGS = (b"--port=989\n--filter-tcp=443\n--hostlist="
        b"/usr/local/etc/zapret2/runtime-v2/managed/hostlist-user.txt\n")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_map(generation: str, args: bytes) -> bytes:
    return (json.dumps({"schema": 1, "generation": generation, "mode": "auto",
                        "final_args_sha256": sha(args),
                        "activation_authorized": False,
                        "observer_attached": False},
                       sort_keys=True, separators=(",", ":")) + "\n").encode()


def proof(mode: str, args: bytes) -> NativeParity:
    return NativeParity(mode, sha(args), sha(args),
                        ("ORIGINAL_NONACTIVATING_MAP_AND_OWNER_INDEPENDENT_PROPOSAL"
                         if mode == "auto" else "ORIGINAL_NONAUTO_NO_SOURCE_MAP"),
                        0, 1, 0, (), (), sha(b"original-capture"), 19000, 19099)


def effective(args: bytes) -> EffectiveSnapshot:
    names = sorted(set(re.findall(r"(?:hostlist|ipset)-[a-z][a-z0-9-]*\.txt",
                                  args.decode("utf-8"))))
    return EffectiveSnapshot("b" * 64, sha(args),
                             tuple((name, sha(name.encode())) for name in names), (), 0)


class SealedFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="s09b-root-")
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.work = self.parent / GEN
        self.work.mkdir(mode=0o700)
        self.release = self.work / "release"
        self.release.mkdir(mode=0o700)
        (self.work / "plan.json").write_bytes(b"{}\n")
        (self.work / "candidate.xml").write_bytes(b"<opnsense/>\n")
        self.mode = "list"
        self.args = ARGS
        self.map = None
        self.native = proof(self.mode, self.args)
        self.effective = effective(self.args)
        (self.release / "dvtws.args").write_bytes(self.args)
        (self.release / "dvtws.args").chmod(0o600)

    def seal(self):
        create_seal(self.work, owner=os.geteuid())
        digest = sha((self.work / "bundle-seal.json").read_bytes())
        return compile_candidate(effective=self.effective, generation=GEN,
                                 target_mode=self.mode, enabled=False,
                                 original_args=self.args,
                                 original_source_map=self.map,
                                 seal_sha256=digest, owner_uid=os.geteuid())

    def attest(self, candidate, **changes):
        values = dict(shared_work_parent=self.parent, generation=GEN,
                      root_bytes=candidate.json_bytes, effective=self.effective,
                      native=self.native, mode=self.mode, enabled=False,
                      owner_uid=os.geteuid())
        values.update(changes)
        return attest_sealed_original(**values)

    def test_list_original_seal_and_refs_read_only(self):
        c = self.seal()
        before = sorted((str(p.relative_to(self.parent)), sha(p.read_bytes()))
                        for p in self.parent.rglob("*") if p.is_file())
        r = self.attest(c)
        after = sorted((str(p.relative_to(self.parent)), sha(p.read_bytes()))
                       for p in self.parent.rglob("*") if p.is_file())
        self.assertEqual(before, after)
        self.assertEqual(r.root_sha256, c.sha256)
        self.assertEqual(r.authorization, "NONE")
        self.assertFalse(r.physical_transition_allowed)
        self.assertTrue(r.reattest_under_original_fd9)
        self.assertEqual(r.ref_sha256, (("dvtws.args", sha(self.args)),))

    def test_auto_original_source_map_generation_and_exact_ref(self):
        self.mode = "auto"
        self.map = source_map(GEN, self.args)
        self.native = proof(self.mode, self.args)
        (self.release / "auto-detect-source-map.json").write_bytes(self.map)
        (self.release / "auto-detect-source-map.json").chmod(0o600)
        c = self.seal()
        self.assertEqual(len(self.attest(c).ref_sha256), 2)
        with self.assertRaises(SealedRefsRefused):
            self.attest(c, mode="list")
        with self.assertRaises(SealedRefsRefused):
            self.attest(c, generation="f" * 32)
        with self.assertRaises(SealedRefsRefused):
            self.attest(c, root_bytes=c.json_bytes.replace(sha(self.args).encode(), b"f" * 64))

    def test_missing_modified_oversized_or_bad_mode_refused(self):
        for mutation in ("missing", "modified", "oversized", "mode"):
            with self.subTest(mutation=mutation):
                # Every subcase starts from the same immutable sealed bytes.
                if self.work.joinpath("bundle-seal.json").exists():
                    self.work.joinpath("bundle-seal.json").unlink()
                (self.release / "dvtws.args").write_bytes(self.args)
                (self.release / "dvtws.args").chmod(0o600)
                c = self.seal()
                p = self.release / "dvtws.args"
                if mutation == "missing":
                    p.unlink()
                elif mutation == "modified":
                    p.write_bytes(self.args + b"x")
                elif mutation == "oversized":
                    p.write_bytes(b"a" * 262145)
                else:
                    p.chmod(0o644)
                with self.assertRaises(SealedRefsRefused):
                    self.attest(c)

    def test_symlink_hardlink_foreign_and_release_alias_refused(self):
        for mutation in ("symlink", "hardlink", "owner", "release_symlink"):
            with self.subTest(mutation=mutation):
                if (self.work / "bundle-seal.json").exists():
                    (self.work / "bundle-seal.json").unlink()
                a = self.release / "dvtws.args"
                if self.release.is_symlink():
                    self.release.unlink()
                    self.release.mkdir(mode=0o700)
                if a.is_symlink():
                    a.unlink()
                alias = self.release / "alias.args"
                if alias.exists():
                    alias.unlink()
                a.write_bytes(self.args)
                a.chmod(0o600)
                c = self.seal()
                if mutation == "symlink":
                    a.unlink()
                    a.symlink_to("dvtws.args")  # cycle
                elif mutation == "hardlink":
                    os.link(a, self.release / "alias.args")
                elif mutation == "owner":
                    with self.assertRaises(SealedRefsRefused):
                        self.attest(c, owner_uid=os.geteuid() + 1)
                    continue
                else:
                    old = self.work / "original-release"
                    self.release.rename(old)
                    self.release.symlink_to(old.name)
                with self.assertRaises(SealedRefsRefused):
                    self.attest(c)

    def test_race_after_first_pinned_read_is_detected(self):
        c = self.seal()
        import neutral_root_refs as refs
        original_read = refs._read_file
        called = []
        def racing(fd, name, owner):
            data = original_read(fd, name, owner)
            if name == "dvtws.args" and not called:
                called.append(True)
                target = self.release / name
                replacement = self.release / ".replacement"
                replacement.write_bytes(self.args + b"altered")
                replacement.chmod(0o600)
                os.replace(replacement, target)
            return data
        with patch.object(refs, "_read_file", side_effect=racing):
            with self.assertRaises(SealedRefsRefused):
                self.attest(c)
        self.assertEqual(called, [True])

    def test_stale_and_mutated_root_and_native_proof_refused(self):
        c = self.seal()
        for wrong in ({"native": replace(self.native, original_args_sha256="f" * 64)},
                      {"native": replace(self.native, authorization="APPLY")},
                      {"root_bytes": c.json_bytes + b"\n"},
                      {"mode": "auto"},
                      {"enabled": True},
                      {"owner_uid": os.geteuid() + 1}):
            with self.subTest(wrong=wrong):
                with self.assertRaises(SealedRefsRefused):
                    self.attest(c, **wrong)


class GenuineOriginalBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "scripts/test-tz6v5-s08c-original-native-parity.py"
        spec = importlib.util.spec_from_file_location("s09b_existing_s08c", path)
        if spec is None or spec.loader is None:
            raise AssertionError("S08C_ORIGINAL_BUILDER_MISSING")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.original = module.RealNativeSourceParity
        cls.original.setUpClass()

    def test_real_generator_modes_and_exact_physical_seal(self):
        for mode in ("list", "auto"):
            with self.subTest(mode=mode):
                runner = self.original("runTest")
                self.addCleanup(runner.doCleanups)
                fixture, kw, native = runner.real(mode=mode)
                args = kw["original_args"]
                path = fixture.release / "dvtws.args"
                self.assertEqual(path.read_bytes(), args)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                if mode == "auto":
                    mapping = (fixture.release / "auto-detect-source-map.json").read_bytes()
                else:
                    mapping = None
                # Take the S08d fingerprint from the SAME real original
                # source inputs; a synthetic dataclass would not establish
                # genuine cross-attestation of structural identity.
                managed = fixture.release / "managed"
                managed_hashes = {
                    p.name: sha(p.read_bytes()) for p in managed.iterdir()
                    if p.is_file() and re.fullmatch(
                        r"(?:hostlist|ipset)-[a-z][a-z0-9-]{0,63}[.]txt", p.name)
                }
                original_map_rows = None if kw["source_map"] is None else [
                    [r["role"], r["status"], r.get("selector"),
                     r.get("hostlist"), r.get("native_number")]
                    for r in kw["source_map"]["profiles"]
                ]
                eff = snapshot(
                    original_native_args=args, target_mode=mode,
                    original_source_rows=original_map_rows,
                    authored_selectors=tuple(
                        tuple(f"<{kind}:{key}>" for kind, key in p.authored)
                        for p in kw["targets"].profiles),
                    saved_wan=kw["requested"].saved_wan,
                    resolved_wan=kw["voice_plan"]["capture"]["wan"],
                    engine_version="v1.0.7",
                    original_capture=kw["voice_plan"]["capture"],
                    original_tcp=(fixture.release / "tcp-ports.txt").read_bytes(),
                    original_udp=(fixture.release / "udp-ports.txt").read_bytes(),
                    managed_sha256=managed_hashes)
                self.assertEqual(eff.external_ref_count, 0)

                (fixture.work / "plan.json").write_bytes(b"{}\n")
                create_seal(fixture.work, owner=os.geteuid())
                seal_digest = sha((fixture.work / "bundle-seal.json").read_bytes())
                c = compile_candidate(effective=eff, generation=fixture.work.name,
                                      target_mode=mode, enabled=False,
                                      original_args=args, original_source_map=mapping,
                                      seal_sha256=seal_digest, owner_uid=os.geteuid())
                receipt = attest_sealed_original(
                    shared_work_parent=fixture.root, generation=fixture.work.name,
                    root_bytes=c.json_bytes, effective=eff, native=native,
                    mode=mode, enabled=False, owner_uid=os.geteuid())
                self.assertEqual(receipt.ref_sha256[0], ("dvtws.args", sha(args)))
                self.assertEqual(len(receipt.ref_sha256), 2 if mode == "auto" else 1)
                self.assertTrue(receipt.reattest_under_original_fd9)


if __name__ == "__main__":
    unittest.main()
