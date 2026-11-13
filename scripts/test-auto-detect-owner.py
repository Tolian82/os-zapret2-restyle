#!/usr/bin/env python3
"""#1052 P2c focused read-only common owner and generation gate (portable S0).

A synthetic *sealed* fixture checks the verification protocol; a fixture does
not prove the actual source generator writes a map or that a real dvtws2 owns it.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
import auto_detect_owner as owner_mod
from shared_apply_seal import SharedBundleError, create_seal
from shared_apply_operation import SharedOperationError

EXE = owner_mod.CHILD_EXEC
MONITOR = owner_mod.MONITOR_EXEC
START = "Fri Nov 13 07:00:00 2026"
UID = os.geteuid()
OP_ID = "0123456789abcdef0123456789abcdef"
CANDIDATE = "b" * 64
BASE = "a" * 64
RAW = "/var/db/zapret2-restyle/auto-detect/inbox.txt"
DEBUG = "/var/db/zapret2-restyle/auto-detect/debug.log"
PID = 1733
MONITOR_PID = 1833


class FakePS:
    def __init__(self, args: str):
        self.args = args
        self.birth = START
        self.monitor_exe = MONITOR
        self.extra = False
        self.commands: list[list[str]] = []
        self.fail = False

    def __call__(self, argv, **_):
        self.commands.append(argv)
        if self.fail:
            return subprocess.CompletedProcess(argv, 1, "", "")
        if "-A" in argv:
            lines = [f"{PID} {EXE} {self.args} --sockarg=0x200 --user=nobody"]
            if self.extra:
                lines.append(f"9999 {EXE} --port=9999")
            return subprocess.CompletedProcess(argv, 0, "\n".join(lines) + "\n", "")
        if str(PID) in argv:
            data = f"{self.birth} {EXE} {self.args} --sockarg=0x200 --user=nobody\n"
        elif str(MONITOR_PID) in argv:
            data = f"{self.birth} {self.monitor_exe} /var/run/dvtws2.pid\n"
        else:
            return subprocess.CompletedProcess(argv, 1, "", "")
        return subprocess.CompletedProcess(argv, 0, data, "")


class OwnerGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.journal = root / "journal"
        self.journal.mkdir(mode=0o700)
        self.work_root = root / "work"
        self.work_root.mkdir(mode=0o700)
        self.work = self.work_root / OP_ID
        self.work.mkdir(mode=0o700)
        self.release = self.work / "release"
        self.release.mkdir(mode=0o700)
        self.active = root / "active"
        self.active.mkdir(mode=0o700)
        self.run = root / "run"
        self.run.mkdir(mode=0o700)
        self.child = self.run / "dvtws2.pid"
        self.monitor = self.run / "monitor.pid"
        self._write(self.child, f"{PID}\n")
        self._write(self.monitor, f"{MONITOR_PID}\n")
        self.argv = ("--port=989\n--lua-init=@/usr/local/etc/zapret2/lua/zapret-lib.lua\n"
                     "--filter-tcp=443\n--hostlist=/usr/local/etc/zapret2/ipset/youtube.txt\n"
                     "--new\n--filter-tcp=443\n"
                     f"--hostlist-auto={RAW}\n"
                     f"--hostlist-auto-debug={DEBUG}\n"
                     "--hostlist-auto-retrans-reset=0\n")
        self.map = {
            "schema": 2, "generation": OP_ID,
            "evidence": "ORIGINAL_SHARED_GENERATOR_CAPTURE",
            "owner_operation_id": OP_ID, "owner_candidate_sha256": CANDIDATE,
            "final_args_sha256": __import__("hashlib").sha256(self.argv.encode()).hexdigest(),
            "mode": "auto", "raw_path": RAW, "debug_path": DEBUG,
            "observer_native_number": 2,
            "profiles": [
                {"native_number": 1, "status": "known-hostlist", "hostlist": "youtube"},
                {"native_number": 2, "status": "observer", "hostlist": None},
                {"native_number": 0, "status": "unknown-native-default", "hostlist": None},
            ],
        }
        self.record = {
            "schema": 1, "phase": "committed",
            "detail": {"id": OP_ID, "page": "strategies", "base": BASE,
                       "candidate": CANDIDATE, "changed_fields": []},
        }
        self._write(self.journal / "operation.json", json.dumps(self.record) + "\n")
        self._write(self.work / "candidate.xml", "<root/>\n")
        self._write(self.work / "plan.json",
                    json.dumps({"page": "strategies", "dependencies": BASE,
                                "changed_fields": []}) + "\n")
        self.ps = FakePS(" ".join(self.argv.split()))
        self.refresh()

    @staticmethod
    def _write(path, data):
        path.write_text(data, encoding="utf-8")
        path.chmod(0o600)

    def refresh(self):
        self._write(self.release / "dvtws.args", self.argv)
        self._write(self.release / owner_mod.MAP_NAME, json.dumps(self.map) + "\n")
        for name in ("dvtws.args", owner_mod.MAP_NAME):
            shutil.copyfile(self.release / name, self.active / name)
            (self.active / name).chmod(0o600)
        seal = self.work / "bundle-seal.json"
        if seal.exists():
            seal.unlink()
        create_seal(self.work, owner=UID)
        self.ps.args = " ".join(self.argv.split())

    def witness(self):
        return owner_mod._attest_core(
            journal=self.journal, work_root=self.work_root, active=self.active,
            child_pidfile=self.child, monitor_pidfile=self.monitor,
            runner=self.ps, owner_uid=UID,
        )

    def refuses(self):
        with self.assertRaises((owner_mod.GenerationRefused, SharedBundleError,
                                SharedOperationError, ValueError, OSError)):
            self.witness()

    def test_qualified_synthetic_owner_and_source_profiles(self):
        proof = self.witness()
        self.assertEqual(proof.owner.pid, PID)
        self.assertEqual(proof.owner.started, START)
        self.assertEqual(proof.generation, OP_ID)
        self.assertEqual(proof.observer_native_number, 2)
        self.assertEqual(proof.profiles[0], (1, "known-hostlist", "youtube"))
        self.assertTrue(any("-A" in cmd for cmd in self.ps.commands))

    def test_uncommitted_journal_or_owner_change_refused(self):
        self.record["phase"] = "activated"
        self._write(self.journal / "operation.json", json.dumps(self.record))
        self.refuses()
        self.record["phase"] = "committed"
        self.record["detail"]["candidate"] = "c" * 64
        self._write(self.journal / "operation.json", json.dumps(self.record))
        self.refuses()

    def test_seal_tampering_and_active_copy_refused(self):
        with (self.release / owner_mod.MAP_NAME).open("a") as file:
            file.write(" ")
        self.refuses()
        self.refresh()
        self._write(self.active / "dvtws.args", "--port=other\n")
        self.refuses()

    def test_pid_reuse_or_wrong_argv_refused(self):
        self.ps.birth = "Fri Nov 13 07:01:00 2026"
        # An internally consistent newer birth can only be accepted if the
        # original launch record pinned it; P2c currently cannot know it.
        self.ps.args += " --unknown"
        self.refuses()
        self.ps.args = "--port=989"
        self.refuses()

    def test_foreign_engine_and_lost_monitor_refused(self):
        self.ps.extra = True
        self.refuses()
        self.ps.extra = False
        self.ps.monitor_exe = "/tmp/foreign-monitor"
        self.refuses()

    def test_missing_map_or_map_from_other_generation_refused(self):
        (self.active / owner_mod.MAP_NAME).unlink()
        self.refuses()
        self.map["generation"] = "f" * 32
        self.refresh()
        self.refuses()

    def test_ambiguous_profiles_or_import_refused(self):
        self.map["profiles"][0]["status"] = "excluded-ipset"
        self.refresh()
        self.refuses()
        self.map["profiles"][0]["status"] = "known-hostlist"
        self.map["profiles"].insert(1, {"native_number": 1, "status": "known-hostlist", "hostlist": "user"})
        self.refresh()
        self.refuses()

    def test_mismatched_auto_paths_and_unsafe_observer_refused(self):
        self.map["raw_path"] += ".changed"
        self.refresh()
        self.refuses()
        self.map["raw_path"] = RAW
        self.argv += "--lua-desync=fake\n"
        self.map["final_args_sha256"] = __import__("hashlib").sha256(self.argv.encode()).hexdigest()
        self.refresh()
        self.refuses()

    def test_corrupt_or_unrecognized_producer_metadata_refused(self):
        self.map["evidence"] = "P0_DETACHED_GENERATOR_ONLY"
        self.refresh()
        self.refuses()
        self.map["evidence"] = "ORIGINAL_SHARED_GENERATOR_CAPTURE"
        self.map["observer_native_number"] = 1
        self.refresh()
        self.refuses()

    def test_nonroot_or_offtarget_public_api_refuses(self):
        # The public path is strict; these positive synthetic fixture checks
        # do not imply permission to run on a user appliance.
        with self.assertRaises(owner_mod.GenerationRefused):
            owner_mod.attest_running_generation(journal=self.journal, work_root=self.work_root,
                   active=self.active, child_pidfile=self.child, monitor_pidfile=self.monitor,
                   runner=self.ps)


if __name__ == "__main__":
    unittest.main(verbosity=2)
