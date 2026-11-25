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
                   "active_managed": fixture.active / "managed"}
        return fixture, keyword

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
