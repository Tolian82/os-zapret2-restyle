#!/usr/bin/env python3
"""S08d fail-closed pure semantic fingerprint and no-action planner negatives.

Only controlled detached inputs; the exact original old-generator 10-case
evidence is executed separately in the existing S03b native P2e fixture.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from neutral_effective_diff import snapshot, plan, EffectiveDiffRefused

MANAGED = "/usr/local/etc/zapret2/runtime-v2/managed/"
ARGS = (b"--port=989\n--lua-init=@/usr/local/zapret2/lua/zapret-lib.lua\n"
        b"--filter-tcp=443\n--hostlist=" + MANAGED.encode()
        + b"hostlist-user.txt\n--lua-desync=fake\n")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def case(**changes):
    item = {
        "original_native_args": ARGS,
        "target_mode": "list",
        "original_source_rows": None,
        "authored_selectors": (("<HOSTLIST:user>",),),
        "saved_wan": "opt0",
        "resolved_wan": "vtnet1",
        "engine_version": "v1.0.7",
        "original_capture": {
            "schema": 1, "logical_wan": "opt0", "wan": "vtnet1",
            "divert_port": 989, "rule_base": 19000, "rule_max": 19099,
            "ordinary_rule_base": 19000, "voice": [],
        },
        "original_tcp": b"443\n",
        "original_udp": b"",
        "managed_sha256": {
            "hostlist-user.txt": sha(b"user.example.org\n"),
            "hostlist-youtube.txt": sha(b"youtube.com\n"),
        },
    }
    item.update(changes)
    return item


class DetachedEffectiveDiff(unittest.TestCase):
    def test_unchanged_snapshots_are_stable_and_never_authorize(self):
        first = snapshot(**case())
        second = snapshot(**case())
        self.assertEqual(first, second)
        res = plan(first, second)
        self.assertEqual(res.kind, "NO_CHANGE")
        self.assertEqual(res.changed_active, ())
        self.assertEqual(res.authorization, "NONE")
        self.assertIs(res.physical_transition_allowed, False)
        with self.assertRaises(FrozenInstanceError):
            res.authorization = "APPLY"

    def test_only_exact_linked_managed_contents_can_be_reload_candidate(self):
        before = snapshot(**case())
        data = case()
        data["managed_sha256"]["hostlist-user.txt"] = sha(b"other.example.org\n")
        after = snapshot(**data)
        res = plan(before, after)
        self.assertEqual(res.kind, "RELOAD_SAFE_CANDIDATE")
        self.assertEqual(res.changed_active, ("hostlist-user.txt",))
        self.assertEqual(res.changed_inactive, ())
        self.assertEqual(before.structural_sha256, after.structural_sha256)
        self.assertFalse(res.physical_transition_allowed)

    def test_unlinked_editor_changes_do_not_imply_runtime_reload(self):
        before = snapshot(**case())
        data = case()
        data["managed_sha256"]["hostlist-youtube.txt"] = sha(b"changed.example.net\n")
        after = snapshot(**data)
        res = plan(before, after)
        self.assertEqual(res.kind, "SAVE_ONLY")
        self.assertEqual(res.changed_active, ())
        self.assertEqual(res.changed_inactive, ("hostlist-youtube.txt",))

    def test_mixed_active_unlinked_only_shares_same_structural_candidate(self):
        before = snapshot(**case())
        data = case()
        data["managed_sha256"]["hostlist-user.txt"] = sha(b"changed.example.net\n")
        data["managed_sha256"]["hostlist-youtube.txt"] = sha(b"changed.example.org\n")
        result = plan(before, snapshot(**data))
        self.assertEqual(result.kind, "RELOAD_SAFE_CANDIDATE")
        self.assertEqual(result.changed_active, ("hostlist-user.txt",))
        self.assertEqual(result.changed_inactive, ("hostlist-youtube.txt",))

    def test_mode_change_even_identical_native_argv_requires_restart(self):
        old = snapshot(**case())
        new = snapshot(**case(target_mode="all"))
        self.assertEqual(old.argv_sha256, new.argv_sha256)
        self.assertNotEqual(old.structural_sha256, new.structural_sha256)
        self.assertEqual(plan(old, new).kind, "RESTART_REQUIRED")

    def test_wan_engine_source_order_and_native_args_are_structural(self):
        old = snapshot(**case())
        args = ARGS.replace(b"--lua-desync=fake", b"--lua-desync=multisplit")
        for diff in (
            {"engine_version": "v1.0.8"},
            {"saved_wan": "opt1", "original_capture": {
                **case()["original_capture"], "logical_wan": "opt1"}},
            {"resolved_wan": "tun2", "original_capture": {
                **case()["original_capture"], "wan": "tun2"}},
            {"authored_selectors": (("<HOSTLIST:youtube>",),)},
            {"original_native_args": args},
            {"original_tcp": b"80,443\n"},
        ):
            with self.subTest(diff=tuple(diff)):
                changed = snapshot(**case(**diff))
                self.assertEqual(plan(old, changed).kind, "RESTART_REQUIRED")

    def test_voice_ipfw_rule_structural_even_if_args_unchanged(self):
        old = snapshot(**case())
        capture = case()["original_capture"]
        changed = {
            **capture, "ordinary_rule_base": 19001,
            "voice": [{"service": "telegram", "rule": 19000}],
        }
        after = snapshot(**case(original_capture=changed))
        self.assertEqual(old.argv_sha256, after.argv_sha256)
        self.assertEqual(plan(old, after).kind, "RESTART_REQUIRED")

    def test_existing_external_ref_prevents_unverified_managed_reload(self):
        extra = ARGS + b"--ipset=/upstream/foreign.txt\n"
        old = snapshot(**case(original_native_args=extra))
        data = case(original_native_args=extra)
        data["managed_sha256"]["hostlist-user.txt"] = sha(b"other.example.org\n")
        changed = snapshot(**data)
        self.assertEqual(plan(old, changed).kind, "RESTART_REQUIRED")

    def test_auto_requires_qualified_original_map_never_fabricates_one(self):
        with self.assertRaisesRegex(EffectiveDiffRefused, "AUTO_SOURCE_MAP"):
            snapshot(**case(target_mode="auto"))
        rows = [
            ["strategy", "known-hostlist", "<HOSTLIST:user>", "user", 1],
            ["native-default", "unknown-native-default", None, None, 0],
        ]
        auto = snapshot(**case(target_mode="auto", original_source_rows=rows))
        self.assertEqual(plan(auto, auto).kind, "NO_CHANGE")
        with self.assertRaisesRegex(EffectiveDiffRefused, "NONAUTO_SOURCE_MAP"):
            snapshot(**case(original_source_rows=rows))
        with self.assertRaises(EffectiveDiffRefused):
            snapshot(**case(target_mode="auto", original_source_rows=rows[:-1]))

    def test_unsafe_or_stale_links_and_unqualified_bounds_fail_closed(self):
        variations = (
            {"original_native_args": ARGS.replace(b"hostlist-user.txt",
                                                   b"hostlist-missing.txt")},
            {"managed_sha256": {"hostlist-user.txt": "not-a-sha"}},
            {"original_native_args": ARGS + b"\x00"},
            {"original_capture": {**case()["original_capture"], "rule_max": 19131}},
            {"original_capture": {**case()["original_capture"], "rule_base": 19100}},
            {"original_capture": {**case()["original_capture"],
                                  "ordinary_rule_base": 19099}},
            {"authored_selectors": (("<HOSTLIST:user>", "<HOSTLIST:user>"),)},
            {"engine_version": "../untrusted-engine"},
            {"saved_wan": ""},
            {"resolved_wan": ""},
        )
        for change in variations:
            with self.subTest(fields=tuple(change)), self.assertRaises(EffectiveDiffRefused):
                snapshot(**case(**change))

    def test_tampered_snapshot_cannot_authorize_an_action(self):
        genuine = snapshot(**case())
        with self.assertRaisesRegex(EffectiveDiffRefused, "UNQUALIFIED_EFFECTIVE_SNAPSHOT"):
            plan(replace(genuine, physical_transition_allowed=True), genuine)
        with self.assertRaisesRegex(EffectiveDiffRefused, "UNQUALIFIED_RESOURCE_FINGERPRINT"):
            plan(replace(genuine, linked=(("hostlist-user.txt", "badsha"),)), genuine)


if __name__ == "__main__":
    unittest.main(verbosity=2)
