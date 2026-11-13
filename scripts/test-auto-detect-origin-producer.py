#!/usr/bin/env python3
"""#1052 P2d: actual P0 generator fixture → original-release source map.

No appliance/daemon/Config access. This runs the existing canonical P0 full
parser/Target Mode/normalizer/targets/blobs/Voice/Extra/final-policy fixture,
then passes its exact captured stage bytes through the installed P2d writer.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
import auto_detect_origin_map as api

P0_FIXTURE = ROOT / "docs/verification/test_p0_profile_attribution.py"
spec = importlib.util.spec_from_file_location("p0_real_fixture", P0_FIXTURE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class OriginalProducerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = mod.AttributionTests(methodName="test_mixed_source_stays_excluded_after_real_expansion")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.tmp = tempfile.TemporaryDirectory(prefix="p2d-origin-")
        self.addCleanup(self.tmp.cleanup)

    def candidate(self, strategy: str, *, voice: str = "", extra: str = ""):
        evidence, expected = self.fixture.generate(strategy, mode="auto", voice=voice, extra=extra)
        work = Path(self.tmp.name) / uuid.uuid4().hex
        work.mkdir(mode=0o700)
        trace = work / api.CAPTURE
        trace.mkdir()
        release = work / "release"
        release.mkdir()
        (work / "traffic.input").write_bytes(evidence["strategy"])
        for stage in ("effective", "normalized", "resolved"):
            directory = trace / stage
            directory.mkdir()
            for idx, value in enumerate(evidence[stage], 1):
                (directory / str(idx)).write_bytes(value)
        for name in ("bindings", "preamble", "assembled"):
            (trace / name).write_bytes(evidence[name])
        (trace / "overlays").write_text("\n".join(evidence["overlays"]) + "\n", encoding="utf-8")
        for name, value in (("traffic-user.conf", evidence["ordinary"]),
                            ("voice.conf", evidence["voice"]),
                            ("extra.conf", evidence["extra"]),
                            ("dvtws.args", evidence["final"])):
            (release / name).write_bytes(value)
        before = (release / "dvtws.args").read_bytes()
        return work, release, trace, before, expected

    def test_explicit_hostlist_from_real_pipeline_is_source_scoped(self):
        work, release, _, original_args, expected = self.candidate(
            "--filter-tcp=443\n<HOSTLIST:youtube>\n--lua-desync=fake\n")
        result = api.publish_origin_map(work, release, "auto")
        stored = json.loads((release / api.ORIGIN_FILE).read_text())
        self.assertEqual(result, stored)
        self.assertEqual(stored["profiles"], expected["profiles"])
        self.assertEqual(stored["evidence"], api.NONACTIVATING)
        self.assertFalse(stored["observer_attached"])
        self.assertFalse(stored["activation_authorized"])
        self.assertFalse((release / "auto-detect-generation.json").exists())
        self.assertEqual((release / "dvtws.args").read_bytes(), original_args)
        self.assertEqual((release / api.ORIGIN_FILE).stat().st_mode & 0o777, 0o600)

    def test_mixed_source_and_voice_cannot_become_known_hostlist(self):
        strategy = ("--filter-tcp=443\n<HOSTLIST:youtube>\n<IPSET:telegram>\n"
                    "--lua-desync=fake\n")
        voice = "--name=voice-telegram-stun\n--filter-udp=3478\n--filter-l7=stun\n"
        work, release, _, _, _ = self.candidate(strategy, voice=voice)
        result = api.publish_origin_map(work, release, "auto")
        self.assertEqual(result["profiles"][0]["status"], "excluded-voice")
        self.assertEqual(result["profiles"][0]["hostlist"], None)
        mixed = [r for r in result["profiles"] if r["role"] == "strategy"]
        self.assertTrue(mixed and all(r["status"] == "excluded-ipset" for r in mixed))
        self.assertTrue(all(r["hostlist"] is None for r in mixed))

    def test_stale_resolved_bytes_refuse_without_creating_map(self):
        work, release, trace, _, _ = self.candidate("--filter-tcp=443\n<HOSTLIST:user>\n")
        path = trace / "resolved" / "1"
        path.write_bytes(path.read_bytes().replace(b"hostlist-user.txt", b"hostlist-youtube.txt"))
        with self.assertRaises(api.AttributionError):
            api.publish_origin_map(work, release, "auto")
        self.assertFalse((release / api.ORIGIN_FILE).exists())

    def test_missing_or_symlinked_native_stage_refuses_without_map(self):
        work, release, trace, _, _ = self.candidate("--filter-tcp=443\n<HOSTLIST:user>\n")
        path = trace / "assembled"
        path.rename(trace / "assembled.orig")
        path.symlink_to(trace / "assembled.orig")
        with self.assertRaises(api.AttributionError):
            api.publish_origin_map(work, release, "auto")
        self.assertFalse((release / api.ORIGIN_FILE).exists())

    def test_refuse_republish_and_wrong_generation_or_mode(self):
        work, release, _, _, _ = self.candidate("--filter-tcp=443\n<HOSTLIST:user>\n")
        with self.assertRaises(api.AttributionError):
            api.publish_origin_map(work, release, "list")
        api.publish_origin_map(work, release, "auto")
        with self.assertRaises(FileExistsError):
            api.publish_origin_map(work, release, "auto")
        self.assertFalse((release / "auto-detect-generation.json").exists())


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    if result.wasSuccessful():
        print("P2D_ORIGINAL_GENERATOR_ORIGIN_PRODUCER=PASS_NONACTIVATING")
    raise SystemExit(0 if result.wasSuccessful() else 1)
