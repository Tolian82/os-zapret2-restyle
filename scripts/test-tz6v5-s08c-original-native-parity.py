#!/usr/bin/env python3
"""S08c exact native argv/Voice/IPFW/source-map and first-match producer parity.

Runs the actual existing P2e orchestrator_build_release on a disposable
workspace; all candidate evidence is read from its original staged files.
No engine, network, live Config, PID, FD9, IPFW command or Apply.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))

from config_projection_opnsense import registered_ids
from neutral_config_model import project
from neutral_target_compiler import parse_original_policy, compile_target_profiles
from neutral_resource_compiler import (parse_original_storage, compile_resources,
                                       compare_original_managed_bytes, ResourceCompileError)
from neutral_native_parity import inspect_original, NativeParityRefused
from voice_profile_compiler import SERVICES
from global_exclusions import segments

BUILDER = ROOT / "scripts/test-p2e-original-shared-build.py"
REGISTRY = BACKEND / "registry.sh"
STORAGE = BACKEND / "storage.sh"
MODE = BACKEND / "target_mode.sh"
ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
VOICE_ARGS = (
    "--filter-udp=3478\n--filter-l7=stun\n--payload=stun\n"
    "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2"
)
TWO = ("--filter-tcp=443\n--filter-l7=tls\n<HOSTLIST:youtube>\n"
       "--lua-desync=fake\n--new\n"
       "--filter-tcp=443\n<HOSTLIST:user>\n--lua-desync=fake\n")
DEFAULT = "--filter-tcp=443\n--lua-desync=fake\n"
MIXED = ("--filter-tcp=443\n<HOSTLIST:user>\n<IPSET:telegram>\n"
         "--lua-desync=fake\n")
EXCLUDE = "ads.example.org\n"


def load_p2e():
    spec = importlib.util.spec_from_file_location("s08c_original_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise AssertionError("ORIGINAL_GENERATOR_FIXTURE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_request(mode, on, port):
    return project(
        {"general": {"enabled": "0", "waninterface": "lo0",
                     "divertport": str(port)},
         "hostlist": {"mode": mode, "youtubedomains": "IGNORED_XML_DATA"},
         "strategy": {}, "strategylab": {},
         "voice": {name: ({"enabled": "1" if name == "telegram" and on else "0",
                           "args": VOICE_ARGS if name == "telegram" and on else ""}
                          ) for name in SERVICES}},
        registered_ids(REGISTRY.read_bytes()))


class RealNativeSourceParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p2e = load_p2e()
        cls.storage = parse_original_storage(STORAGE.read_bytes())
        cls.policy = parse_original_policy(MODE.read_bytes())

    def real(self, strategy=TWO, *, mode="auto", voice_on=False,
             exclude_domains="", exclude_ipset=""):
        fixture = self.p2e.OriginalSharedGeneration("runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        path, args = fixture.build(
            strategy, mode=mode, voice_on=voice_on,
            exclude_domains=exclude_domains, exclude_ipset=exclude_ipset,
            divert_port="19899", rule_max="19099")
        emitted = args.read_bytes()
        captured_strategy = (fixture.work / "traffic.input").read_bytes()
        model = build_request(mode, voice_on, 19899)
        targets = compile_target_profiles(model, captured_strategy, self.policy)
        raw = {
            "hostlist.youtube": b"youtube.com\n",
            "hostlist.user": b"example.org\n",
            "ipset.telegram": b"91.108.13.10\n",
            "ipset.discord": b"", "ipset.x": b"", "ipset.sip": b"",
            "ipset.custom": b"",
            "hostlist.exclude": exclude_domains.encode(),
            "ipset.exclude": exclude_ipset.encode(),
        }
        resources = compile_resources(
            model, targets, self.storage, raw, None,
            voice_managed_root=ACTIVE / "managed")
        mapping = fixture.check_nonactivating(path, args) if mode == "auto" else None
        if mode != "auto":
            self.assertFalse(path.exists(), "original non-Auto emitted a source map")
        voice_conf = (fixture.release / "voice.conf").read_bytes()
        voice_plan = json.loads((fixture.release / "voice-plan.json").read_bytes())
        kw = {"requested": model, "targets": targets, "resources": resources,
              "strategy": captured_strategy, "original_args": emitted,
              "voice_conf": voice_conf, "voice_plan": voice_plan,
              "source_map": mapping,
              "generation": fixture.work.name if mode == "auto" else None,
              "candidate_sha256": "d" * 64 if mode == "auto" else None,
              "rule_base": 19000, "rule_max": 19099}
        return fixture, kw, inspect_original(**kw)

    def test_original_auto_youtube_user_working_first_learning_last(self):
        fixture, kw, proof = self.real()
        self.assertEqual(proof.mode, "auto")
        self.assertEqual(proof.status, "ORIGINAL_SOURCE_PARITY_ONLY")
        self.assertEqual(proof.authorization, "NONE")
        self.assertFalse(proof.physical_transition_allowed)
        self.assertEqual(proof.voice_profile_count, 0)
        self.assertEqual(proof.ordinary_native_count, 2)
        self.assertEqual(proof.learning_native_count, 2)
        self.assertEqual([r.hostlist for r in proof.working_profiles
                          if r.status == "known-hostlist"], ["youtube", "user"])
        self.assertEqual([r.hostlist for r in proof.learning_profiles],
                         ["youtube", "user"])
        self.assertEqual([r.native_number for r in proof.learning_profiles], [3, 4])
        self.assertEqual([r.source_number for r in proof.working_profiles], [1, 2])
        self.assertEqual(kw["original_args"], (fixture.release / "dvtws.args").read_bytes())
        self.assertNotEqual(proof.proposed_args_sha256, proof.original_args_sha256)
        with self.assertRaises(FrozenInstanceError):
            proof.authorization = "ROOT"

    def test_real_voice_first_and_capture_rules_with_exact_final_numbers(self):
        fixture, kw, proof = self.real(voice_on=True)
        self.assertEqual(proof.voice_profile_count, 1)
        self.assertEqual(proof.ordinary_native_count, 3)
        self.assertEqual(proof.learning_native_count, 2)
        self.assertEqual(proof.working_profiles[0].role, "voice")
        self.assertEqual([r.native_number for r in proof.working_profiles],
                         [1, 2, 3])
        self.assertEqual([r.native_number for r in proof.learning_profiles], [4, 5])
        self.assertEqual([r.hostlist for r in proof.learning_profiles],
                         ["youtube", "user"])
        self.assertEqual((proof.ordinary_rule_start, proof.ordinary_rule_end),
                         (19001, 19099))
        cap = kw["voice_plan"]["capture"]
        self.assertEqual(cap["voice"][0]["rule"], 19000)
        self.assertEqual(cap["ordinary_rule_base"], 19001)
        self.assertEqual(cap["rule_max"], 19099)
        self.assertEqual(cap["divert_port"], 19899)
        self.assertEqual(cap["wan"], "lo0")
        self.assertIn("--name=voice-telegram", kw["original_args"].decode())

    def test_real_default_auto_does_not_learn_implicit_selectors(self):
        _, kw, proof = self.real(DEFAULT)
        self.assertEqual(proof.learning_native_count, 0)
        self.assertEqual(proof.proposed_args_sha256, proof.original_args_sha256)
        self.assertEqual(proof.ordinary_native_count, 3)
        # Original Target Mode appends HOSTLIST youtube + IPSET telegram +
        # HOSTLIST user in ONE sourced profile, so source_has_ipset is true
        # for every normalized native copy. The source-map owner refuses to
        # infer known HOSTLIST attribution from a mixed default expansion.
        self.assertEqual([r.status for r in proof.working_profiles],
                         ["excluded-ipset"] * 3)
        self.assertEqual([r.hostlist for r in proof.working_profiles],
                         [None] * 3)
        self.assertEqual([r.source_number for r in proof.working_profiles], [1, 1, 1])
        self.assertEqual(proof.learning_profiles, ())

    def test_explicit_mixed_hostlist_ipset_never_becomes_learner(self):
        _, _, proof = self.real(MIXED)
        self.assertEqual(proof.learning_native_count, 0)
        self.assertEqual(proof.ordinary_native_count, 2)
        self.assertEqual([r.status for r in proof.working_profiles],
                         ["excluded-ipset", "excluded-ipset"])
        self.assertEqual([r.hostlist for r in proof.working_profiles], [None, None])

    def test_original_list_and_all_have_no_map_or_hidden_observer(self):
        for mode in ("list", "all"):
            with self.subTest(mode=mode):
                _, kw, proof = self.real(TWO, mode=mode)
                self.assertEqual(proof.source_map_status,
                                 "ORIGINAL_NONAUTO_NO_SOURCE_MAP")
                self.assertEqual(proof.learning_native_count, 0)
                self.assertEqual(proof.working_profiles, ())
                self.assertEqual(proof.original_args_sha256,
                                 proof.proposed_args_sha256)
                self.assertNotIn(b"--hostlist-auto=", kw["original_args"])

    def test_original_global_exclusions_preserve_working_and_learner_tail(self):
        fixture, kw, proof = self.real(
            exclude_domains=EXCLUDE, exclude_ipset="198.51.100.0/24\n")
        self.assertEqual(proof.learning_native_count, 2)
        self.assertEqual(proof.ordinary_native_count, 2)
        from auto_detect_origin_map import plan_learning_tier, _original_global_policy_paths
        from global_exclusions import audit
        pre = kw["original_args"]
        proposed, _ = plan_learning_tier(
            kw["source_map"], pre, owner_id=kw["generation"],
            owner_candidate_sha256=kw["candidate_sha256"])
        expected_paths = _original_global_policy_paths(fixture.release)
        audit(pre.decode(), *expected_paths)
        audit(proposed.decode(), *expected_paths)
        rows = segments(proposed.decode())
        d = "--hostlist-exclude=" + expected_paths[1]
        ip = "--ipset-exclude=" + expected_paths[3]
        for row in rows:
            self.assertEqual(row[-2:], [d, ip])
        self.assertFalse((fixture.release / "auto-detect-observer-preview.args").exists())

    def test_invalid_pinned_source_and_voice_capture_fail_closed(self):
        import copy
        _, kw, proof = self.real(voice_on=True)
        self.assertEqual(proof.learning_native_count, 2)
        bads = [
            dict(kw, original_args=kw["original_args"] + b"\n--filter-tcp=9\n"),
            dict(kw, source_map=None),
            dict(kw, source_map={**kw["source_map"], "mode": "list"}),
            dict(kw, source_map={**kw["source_map"], "generation": "f" * 32}),
            dict(kw, candidate_sha256="not-hex"),
            dict(kw, rule_max=19131),
            dict(kw, rule_base=19100),
            dict(kw, voice_conf=b"forged\n"),
            dict(kw, requested=replace(kw["requested"], target_mode="list")),
        ]
        changed = copy.deepcopy(kw["source_map"])
        changed["profiles"][1]["source_sha256"] = "a" * 64
        bads.append(dict(kw, source_map=changed))
        forged = copy.deepcopy(kw["voice_plan"])
        forged["capture"]["voice"][0]["rule"] += 1
        bads.append(dict(kw, voice_plan=forged))
        for index, item in enumerate(bads):
            with self.subTest(case=index), self.assertRaises(NativeParityRefused):
                inspect_original(**item)
        self.assertEqual(kw["original_args"],
                         kw["original_args"])  # witness input never written

    def test_nonautos_cannot_accept_forged_map_even_if_argv_same(self):
        _, kw, result = self.real(TWO, mode="list")
        self.assertEqual(result.source_map_status,
                         "ORIGINAL_NONAUTO_NO_SOURCE_MAP")
        with self.assertRaisesRegex(NativeParityRefused,
                                    "UNEXPECTED_NONAUTO_SOURCE_MAP"):
            inspect_original(**dict(kw, source_map={"schema": 1}))

    def test_original_managed_bytes_are_checked_without_second_generator(self):
        for mode in ("all", "list", "auto"):
            with self.subTest(mode=mode):
                fixture, kw, _ = self.real(TWO, mode=mode)
                catalog = self.storage
                observed = {x.locator: (fixture.release / "managed" / x.locator).read_bytes()
                            for x in catalog.entries if x.provider == "managed"}
                for name in ("hostlist-exclude.txt", "ipset-exclude.txt"):
                    observed[name] = (fixture.release / "managed" / name).read_bytes()
                matched = compare_original_managed_bytes(
                    kw["resources"], catalog, observed)
                self.assertEqual(len(matched), len(kw["resources"].resources) - 1 + 2)
                key = "ipset-telegram.txt"
                with self.assertRaisesRegex(ResourceCompileError,
                                            "ORIGINAL_MANAGED_BYTES_MISMATCH"):
                    compare_original_managed_bytes(
                        kw["resources"], catalog,
                        dict(observed, **{key: observed[key] + b"198.51.100.9\n"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
