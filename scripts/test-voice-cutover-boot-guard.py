#!/usr/bin/env python3
"""Native Voice journal gate: verify no boot/lifecycle mutation on pending intent.

All filesystem writes are private temporary CI fixtures; no live firewall,
OPNsense Config, process control or outside network operations are performed.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
import voice_cutover_guard as guard
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore

fixture_spec=importlib.util.spec_from_file_location(
    "voice_fw_fixture", ROOT / "scripts/test-voice-firewall-transaction.py"
)
fixture=importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixture)

OLD = {name: str(i) * 64 for i, name in
       enumerate(("config", "runtime", "engine", "firewall", "supervisor"))}
NEW = {"saved_xml_sha256": "a" * 64, "merged_sha256": "b" * 64,
       "native_argv_sha256": "c" * 64}


class BootGateTests(unittest.TestCase):
    def paths(self, root: Path):
        return root / "whole", root / "ipfw"

    def test_missing_journals_allow_normal_legacy_service_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            whole, ipfw = self.paths(Path(tmp))
            self.assertEqual({"state": "clear", "safe_to_mutate": True},
                             guard.check_pending(whole, ipfw))
            self.assertEqual(64, guard.main(["voice_cutover_guard.py", "unexpected"]))

    def test_empty_private_journals_allow_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            whole, ipfw = self.paths(Path(tmp))
            whole.mkdir(mode=0o700)
            ipfw.mkdir(mode=0o700)
            self.assertTrue(guard.check_pending(whole, ipfw)["safe_to_mutate"])
            current = fixture.fixture()
            VoiceOwnershipStore(ipfw).seed(current)
            self.assertTrue(guard.check_pending(whole, ipfw)["safe_to_mutate"])

    def test_each_whole_cutover_phase_preempts_any_other_state(self):
        for phase in ("prepared", "mutating", "committed"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                whole, ipfw = self.paths(Path(tmp))
                whole.mkdir(mode=0o700)
                journal = VoiceCutoverJournal(whole)
                journal.begin(OLD, NEW)
                if phase in ("mutating", "committed"):
                    journal.mark_mutating()
                if phase == "committed":
                    journal.commit()
                before = (whole / "intent.json").read_bytes()
                state = guard.check_pending(whole, ipfw)
                self.assertEqual("blocked", state["state"])
                self.assertEqual("whole-runtime-intent", state["reason"])
                self.assertFalse(state["safe_to_mutate"])
                self.assertEqual(before, (whole / "intent.json").read_bytes())
                self.assertFalse(ipfw.exists(),
                                 "journal guard must never initialize any directory")

    def test_ipfw_pending_blocks_even_without_whole_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            whole, ipfw = self.paths(Path(tmp))
            ipfw.mkdir(mode=0o700)
            store = VoiceOwnershipStore(ipfw)
            prev = fixture.fixture()
            next_ = fixture.fixture(("telegram", "91.108.0.0/16"))
            store.seed(prev)
            store.begin(prev, next_)
            original = (ipfw / "intent.json").read_bytes()
            result = guard.check_pending(whole, ipfw)
            self.assertEqual("ipfw-intent", result["reason"])
            self.assertEqual("prepared", result["phase"])
            self.assertFalse(result["safe_to_mutate"])
            self.assertEqual(original, (ipfw / "intent.json").read_bytes())

    def test_untrusted_paths_or_corrupt_records_fail_closed(self):
        for case in ("symlink-whole", "symlink-ipfw", "bad-mode",
                     "bad-whole-json", "bad-ipfw-json"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                whole, ipfw = self.paths(Path(tmp))
                other = Path(tmp) / "foreign"
                other.mkdir(mode=0o700)
                if case == "symlink-whole":
                    whole.symlink_to(other)
                elif case == "symlink-ipfw":
                    ipfw.symlink_to(other)
                elif case == "bad-mode":
                    whole.mkdir(mode=0o700)
                    whole.chmod(0o755)
                elif case == "bad-whole-json":
                    whole.mkdir(mode=0o700)
                    (whole / "intent.json").write_text("{broken")
                else:
                    ipfw.mkdir(mode=0o700)
                    (ipfw / "intent.json").write_text("{broken")
                result = guard.check_pending(whole, ipfw)
                self.assertEqual("blocked", result["state"])
                self.assertEqual("invalid-or-untrusted-journal", result["reason"])
                self.assertFalse(result["safe_to_mutate"])

    def test_real_service_lock_wrapper_probes_before_any_dispatch(self):
        service = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        method = service.split("service_with_lifecycle_lock()\n{", 1)[1]
        method = method.split("\n}\n", 1)[0]
        self.assertLess(method.index('"${LOCKF_BIN}" -s'), method.index(
            "preflight_voice_cutover_journals || return 69"
        ))
        self.assertLess(method.index("preflight_voice_cutover_journals || return 69"),
                        method.index('service_dispatch "$@"'))
        for action in ("start", "stop", "restart", "reconfigure",
                       "telegram-voice-enable", "telegram-voice-disable",
                       "runtime-failure", "strategy-lab", "strategy-lab-recover"):
            self.assertIn(action, method)
        self.assertIn("voice_cutover_guard.py", service)
        self.assertIn("/usr/local/bin/python3.13", service)


if __name__ == "__main__":
    unittest.main(verbosity=2)
