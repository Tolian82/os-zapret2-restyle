#!/usr/bin/env python3
"""Offline proof of the bounded read-only FreeBSD Voice packet trial."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from voice_live_trial import VoiceTrialError, compare, count_owned, snapshot


class TrialTests(unittest.TestCase):
    def test_ipfw_counter_parser_restricts_numbers_and_fails_closed(self):
        listing = (
            "00001 18 1242 allow ip from any to any\n"
            "19000 3 216 divert 989 udp from any to table(zapret2_voice_telegram) out xmit vtnet1\n"
            "19001 10 800 divert 989 tcp from any to any 443 out xmit vtnet1\n"
            "65535 25 1200 deny ip from any to any\n"
        )
        self.assertEqual({19000: {"packets": 3, "bytes": 216}},
                         count_owned(listing, {19000}))
        with self.assertRaisesRegex(VoiceTrialError, "missing"):
            count_owned(listing, {19000, 19002})
        with self.assertRaisesRegex(VoiceTrialError, "duplicate"):
            count_owned(listing + listing.splitlines()[1] + "\n", {19000})
        with self.assertRaisesRegex(VoiceTrialError, "untrusted"):
            count_owned(listing, {65535})

    def test_comparison_never_claims_successful_call_or_media(self):
        first = {
            "schema": 1, "state": "ready", "owner": "a" * 32,
            "time_unix": 100,
            "rules": {"telegram": {"number": 19000, "packets": 20, "bytes": 1800}},
        }
        last = json.loads(json.dumps(first))
        last["time_unix"] = 123
        last["rules"]["telegram"]["packets"] = 45
        last["rules"]["telegram"]["bytes"] = 3500
        result = compare(first, last)
        self.assertEqual(25, result["services"]["telegram"]["packet_delta"])
        self.assertEqual(1700, result["services"]["telegram"]["byte_delta"])
        self.assertEqual(23, result["elapsed_seconds"])
        self.assertTrue(result["ipfw_packets_observed"])
        self.assertFalse(result["stun_verified"])
        self.assertFalse(result["media_verified"])
        self.assertFalse(result["call_verified"])
        with self.assertRaisesRegex(VoiceTrialError, "owner changed"):
            compare(first, dict(last, owner="b" * 32))
        reset = json.loads(json.dumps(last))
        reset["rules"]["telegram"]["packets"] = 1
        with self.assertRaisesRegex(VoiceTrialError, "counters reset"):
            compare(first, reset)
        with self.assertRaisesRegex(VoiceTrialError, "rules changed"):
            compare(first, dict(last, rules={"discord": last["rules"]["telegram"]}))

    def test_snapshot_uses_exact_existing_common_owner_and_read_only_ipfw(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            identity = "a" * 32
            release = work / identity / "release"
            release.mkdir(parents=True)
            (release / "voice-plan.json").write_text(json.dumps({
                "capture": {"voice": [
                    {"service": "telegram", "rule": 19000}
                ]}
            }), encoding="utf-8")
            record = {"phase": "committed", "id": identity, "page": "voice"}
            manifest = {
                "rule_base": 19000, "rule_max": 19010,
                "rules": {19000: ["divert", "989"]}, "tables": {},
            }
            calls = []
            def inspect(owner):
                self.assertEqual(record, owner)
                return {"state": "ready"}
            def ipfw(argv, **kwargs):
                calls.append(argv)
                self.assertEqual(["/sbin/ipfw", "-a", "list"], argv)
                self.assertFalse(kwargs["check"])
                return subprocess.CompletedProcess(
                    argv, 0,
                    "19000 42 4096 divert 989 udp from any to table(zapret2_voice_telegram)\n",
                    "",
                )
            class Operation:
                def read(self):
                    return record
            trial = sys.modules[snapshot.__module__]
            with patch.object(trial.sys, "platform", "freebsd"), \
                 patch.object(trial.os, "geteuid", return_value=0), \
                 patch.object(trial, "WORK", work), \
                 patch.object(trial, "SharedApplyOperation", Operation), \
                 patch.object(trial, "committed_owner", return_value={"id": identity}), \
                 patch.object(trial, "examine_shared", side_effect=inspect), \
                 patch.object(trial, "shared_release_manifest", return_value=manifest), \
                 patch.object(trial.subprocess, "run", side_effect=ipfw):
                result = snapshot()
            self.assertEqual([["/sbin/ipfw", "-a", "list"]], calls)
            self.assertEqual(42, result["rules"]["telegram"]["packets"])
            self.assertEqual(identity, result["owner"])
            self.assertFalse(result["call_verified"])

    def test_no_local_or_uncommitted_owner_fabricates_live_evidence(self):
        trial = sys.modules[snapshot.__module__]
        with patch.object(trial.os, "geteuid", return_value=1):
            with self.assertRaisesRegex(VoiceTrialError, "FreeBSD"):
                snapshot()


if __name__ == "__main__":
    unittest.main(verbosity=2)
