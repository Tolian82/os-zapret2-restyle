#!/usr/bin/env python3
"""Native Voice journal gate: verify no boot/lifecycle mutation on pending intent.

All filesystem writes are private temporary CI fixtures; no live firewall,
OPNsense Config, process control or outside network operations are performed.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
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
            owned = guard.check_pending(whole, ipfw)
            self.assertFalse(owned["safe_to_mutate"])
            self.assertEqual("native-ipfw-owned", owned["reason"])
            self.assertIsNone(VoiceOwnershipStore(ipfw).pending())

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

    def test_bound_v2_journal_still_blocks_legacy_before_all_ipfw_reads(self):
        desired = fixture.fixture(("telegram", "91.108.0.0/16"))
        for phase in ("prepared", "mutating", "committed"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                whole, ipfw = self.paths(Path(tmp))
                whole.mkdir(mode=0o700)
                journal = VoiceCutoverJournal(whole)
                journal.begin_bound(OLD, NEW, desired)
                if phase in ("mutating", "committed"):
                    journal.mark_mutating()
                if phase == "committed":
                    journal.commit()
                original = journal._target().read_bytes()
                observed = guard.check_pending(whole, ipfw)
                self.assertEqual("blocked", observed["state"])
                self.assertEqual("whole-runtime-intent", observed["reason"])
                self.assertEqual(phase, journal.read()["phase"])
                self.assertFalse(observed["safe_to_mutate"])
                self.assertEqual(original, journal._target().read_bytes())
                self.assertFalse(ipfw.exists())

    def test_existing_native_ownership_blocks_legacy_even_if_all_journals_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            whole, ipfw = self.paths(Path(tmp))
            whole.mkdir(mode=0o700)
            ipfw.mkdir(mode=0o700)
            ledger = VoiceOwnershipStore(ipfw)
            ledger.seed(fixture.fixture())
            result = guard.check_pending(whole, ipfw)
            self.assertEqual("native-ipfw-owned", result["reason"])
            self.assertFalse(result["safe_to_mutate"])
            self.assertFalse((whole / "intent.json").exists())

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

    def test_service_shell_guard_has_ci_interpreter_without_a_production_bypass(self):
        service=(ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        self.assertIn("_voice_cutover_guard_python=/usr/local/bin/python3.13",service)
        self.assertIn("case \"${BACKEND_DIR}\" in",service)
        self.assertIn("/usr/local/opnsense/scripts/OPNsense/Zapret/backend)",service)
        self.assertIn("command -v python3.13",service)
        body=service.split("preflight_voice_cutover_journals()\n{",1)[1].split("\n}\n",1)[0]
        snippet="preflight_voice_cutover_journals()\n{" + body + "\n}\npreflight_voice_cutover_journals\n"
        with tempfile.TemporaryDirectory() as temp:
            backend=Path(temp)/"backend"
            backend.mkdir()
            script=backend/"voice_cutover_guard.py"
            for status in (0, 69):
                with self.subTest(status=status):
                    script.write_text("raise SystemExit("+str(status)+")\n")
                    env=os.environ.copy()
                    env["BACKEND_DIR"]=str(backend)
                    result=subprocess.run(
                        ["/bin/sh","-c",snippet],env=env,
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                        check=False,
                    )
                    self.assertEqual(status,result.returncode,result.stderr)

    def test_inherited_strategy_lab_owner_cannot_bypass_voice_crash_guard(self):
        service=(ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
        owner=service.split("strategy_lab_internal_dispatch()\n{",1)[1].split("\n}\n",1)[0]
        self.assertIn("strategy_lab_lock_owner_valid",owner)
        self.assertEqual(2,owner.count("preflight_voice_cutover_journals || return 69"))
        for action in ("strategy-lab-stop", "strategy-lab-start"):
            block=owner.split(action+")",1)[1].split(";;",1)[0]
            self.assertLess(block.index("preflight_voice_cutover_journals || return 69"),
                            block.index("stop_service" if action.endswith("stop") else "start_service"))
        for action in ("strategy-lab-status", "strategy-lab-evidence"):
            block=owner.split(action+")",1)[1].split(";;",1)[0]
            self.assertNotIn("preflight_voice_cutover_journals",block,
                             "read-only Strategy Lab status must remain available for recovery")

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
