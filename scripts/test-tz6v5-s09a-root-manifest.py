#!/usr/bin/env python3
"""S09a detached root grammar/structural proof, not filesystem attestation."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import sys
import unittest

# Works from scripts/ and in an isolated copy of this fixture.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from neutral_effective_diff import EffectiveSnapshot
from neutral_root_manifest import RootManifestRefused, compile_candidate, validate_candidate

GEN = "0123456789abcdef0123456789abcdef"
SEAL = "e" * 64
ARGS = b"--port=989\n--filter-tcp=443\n--hostlist=/usr/local/etc/zapret2/runtime-v2/managed/hostlist-user.txt\n"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def effective():
    return EffectiveSnapshot("b" * 64, sha(ARGS),
                             (("hostlist-user.txt", sha(b"content-is-NOT-in-root")),), (), 0)


def source_map():
    # S09a checks only original-generator identity fields. S08c is the owner
    # of full native profile/order and source-map parity, not this fixture.
    return json.dumps({"schema": 1, "generation": GEN, "mode": "auto",
                       "final_args_sha256": sha(ARGS),
                       "activation_authorized": False,
                       "observer_attached": False}).encode()


def params(**updates):
    data = dict(effective=effective(), generation=GEN, target_mode="list",
                enabled=True, original_args=ARGS, original_source_map=None,
                seal_sha256=SEAL, owner_uid=0)
    data.update(updates)
    return data


def validate_args(candidate, **changes):
    p = params(**changes)
    return dict(raw=candidate.json_bytes, effective=p["effective"],
                expected_generation=p["generation"], expected_mode=p["target_mode"],
                expected_enabled=p["enabled"], original_args=p["original_args"],
                original_source_map=p["original_source_map"],
                expected_seal_sha256=p["seal_sha256"], expected_uid=p["owner_uid"])


def modified(raw, change):
    data = json.loads(raw)
    change(data)
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()


class RootContract(unittest.TestCase):
    def test_canonical_list_root_is_bounded_and_never_authorizes(self):
        p = params()
        c = compile_candidate(**p)
        self.assertEqual(c, validate_candidate(**validate_args(c)))
        self.assertEqual(c.sha256, sha(c.json_bytes))
        self.assertFalse(c.physical_transition_allowed)
        self.assertEqual(c.authorization, "NONE")
        with self.assertRaises(FrozenInstanceError):
            c.authorization = "APPLY"
        root = json.loads(c.json_bytes)
        self.assertEqual(set(root), {"schema", "generation", "service", "resources", "refs"})
        self.assertEqual(len(root["refs"]), 1)
        self.assertEqual(root["refs"][0]["path"], "dvtws.args")
        self.assertNotIn("content-is-NOT-in-root", c.json_bytes.decode())
        self.assertNotIn(sha(b"content-is-NOT-in-root"), c.json_bytes.decode())

    def test_auto_requires_original_generation_bound_map(self):
        m = source_map()
        c = compile_candidate(**params(target_mode="auto", original_source_map=m))
        self.assertEqual(c, validate_candidate(**validate_args(c, target_mode="auto", original_source_map=m)))
        self.assertEqual(len(json.loads(c.json_bytes)["refs"]), 2)
        for change in (None, m.replace(GEN.encode(), b"f" * 32),
                       m.replace(sha(ARGS).encode(), b"a" * 64),
                       m.replace(b'"observer_attached": false', b'"observer_attached": true')):
            with self.subTest(change=change is None):
                with self.assertRaises(RootManifestRefused):
                    compile_candidate(**params(target_mode="auto", original_source_map=change))
        with self.assertRaises(RootManifestRefused):
            compile_candidate(**params(original_source_map=m))

    def test_wrong_effective_or_unowned_input_fails_closed(self):
        invalid = (replace(effective(), authorization="APPLY"),
                   replace(effective(), external_ref_count=1),
                   replace(effective(), argv_sha256="0" * 64),
                   replace(effective(), linked=(("../escape", "c" * 64),)),
                   replace(effective(), linked=(("hostlist-user.txt", "c" * 64),) * 2),
                   replace(effective(), linked=(("ipset-user.txt", "a" * 64),
                                                        ("hostlist-user.txt", "c" * 64))))
        for proof in invalid:
            with self.subTest(proof=proof):
                with self.assertRaises(RootManifestRefused):
                    compile_candidate(**params(effective=proof))

    def test_tampered_root_ref_paths_modes_owner_hash_and_generation(self):
        c = compile_candidate(**params())
        mutations = (
            lambda d: d["refs"][0].update(path="../dvtws.args"),
            lambda d: d["refs"][0].update(path="/tmp/dvtws.args"),
            lambda d: d["refs"][0].update(path="manifest.json"),
            lambda d: d["refs"][0].update(mode=0o666),
            lambda d: d["refs"][0].update(uid=1001),
            lambda d: d["refs"][0].update(size=9999999),
            lambda d: d["refs"][0].update(sha256="a" * 64),
            lambda d: d["refs"][0].update(seal_sha256="a" * 64),
            lambda d: d["refs"][0].update(generation="f" * 32),
            lambda d: d.update(generation="f" * 32),
            lambda d: d["service"].update(target_mode="auto"),
            lambda d: d["service"].update(structural_sha256="a" * 64),
            lambda d: d["resources"].update(mutable_refs=[]),
            lambda d: d["resources"]["mutable_refs"][0].update(owner="external"),
            lambda d: d["refs"].append(dict(d["refs"][0])),
            lambda d: d.update(strategies=["raw-rule"]),
            lambda d: d["service"].update(enabled="true"),
        )
        for change in mutations:
            with self.subTest(change=change):
                with self.assertRaises(RootManifestRefused):
                    validate_candidate(**{**validate_args(c), "raw": modified(c.json_bytes, change)})

    def test_noncanonical_duplicate_overflow_and_wrong_input_refuse(self):
        c = compile_candidate(**params())
        rejects = (c.json_bytes + b" ", c.json_bytes.replace(b'"schema":1', b'"schema":1,"schema":1'),
                   c.json_bytes.replace(b'"schema":1', b'"schema":true'),
                   b"[1]", b"{" + b" " * 16384 + b"}", b"{", b"\xff")
        for raw in rejects:
            with self.subTest(raw=raw[:12]):
                with self.assertRaises(RootManifestRefused):
                    validate_candidate(**{**validate_args(c), "raw": raw})

    def test_external_witness_change_without_root_update_fails(self):
        c = compile_candidate(**params())
        changed = (dict(original_args=ARGS + b"x"), dict(generation="1" * 32),
                   dict(seal_sha256="a" * 64), dict(owner_uid=1001),
                   dict(enabled=False), dict(target_mode="all"))
        for delta in changed:
            with self.subTest(delta=delta):
                with self.assertRaises(RootManifestRefused):
                    validate_candidate(**validate_args(c, **delta))


if __name__ == "__main__":
    unittest.main()
