#!/usr/bin/env python3
"""#1052 P2c focused read-only common owner and generation gate (portable S0).

A synthetic *sealed* fixture checks the verification protocol; a fixture does
not prove the actual source generator writes a map or that a real dvtws2 owns it.
"""
from __future__ import annotations

import importlib.util
import ctypes
import errno
import hashlib
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
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_queue import DurableInbox

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
    def __init__(self, args: str, child_pidfile: Path):
        self.args = args
        self.child_pidfile = child_pidfile
        self.birth = START
        self.monitor_exe = MONITOR
        self.extra = False
        self.stopped = False
        self.stopped_rows = "0 [kernel]\\n1 /sbin/init\\n77 /bin/ps\\n".replace("\\n", "\n")
        self.commands: list[list[str]] = []
        self.fail = False
        self.truncate_child_at = 0

    def __call__(self, argv, **_):
        self.commands.append(argv)
        if self.fail:
            return subprocess.CompletedProcess(argv, 1, "", "")
        if "-A" in argv:
            if self.stopped:
                return subprocess.CompletedProcess(argv, 0, self.stopped_rows, "")
            lines = [f"{PID} {EXE} {self.args} --sockarg=0x200 --user=nobody"]
            if self.extra:
                lines.append(f"9999 {EXE} --port=9999")
            return subprocess.CompletedProcess(argv, 0, "\n".join(lines) + "\n", "")
        if str(PID) in argv:
            data = f"{self.birth} {EXE} {self.args} --sockarg=0x200 --user=nobody\n"
            if self.truncate_child_at:
                data = data[:self.truncate_child_at].rstrip("\n") + "\n"
        elif str(MONITOR_PID) in argv:
            data = (f"{self.birth} {self.monitor_exe} {self.child_pidfile} "
                    f"{Path(MONITOR).with_name('zapret_service.sh')} {EXE}\n")
        else:
            return subprocess.CompletedProcess(argv, 1, "", "")
        return subprocess.CompletedProcess(argv, 0, data, "")


class FakeArgvSysctl:
    """Fixture preserves kernel NUL boundaries past ps text truncation."""

    def __init__(self, argv):
        self.raw = b"\x00".join(x.encode("utf-8") for x in argv) + b"\x00"

    def __call__(self, mib, miblen, pointer, length_ptr, new_ptr, new_len):
        assert miblen == 4 and list(mib) == [1, 14, 7, PID]
        n = ctypes.cast(length_ptr, ctypes.POINTER(ctypes.c_size_t))
        if pointer is None:
            n[0] = len(self.raw)
        else:
            if n[0] < len(self.raw):
                ctypes.set_errno(errno.ENOMEM)
                return -1
            ctypes.memmove(pointer, self.raw, len(self.raw))
            n[0] = len(self.raw)
        return 0


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
        self.ps = FakePS(" ".join(self.argv.split()), self.child)
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

    def witness(self, *, epoch_finalizing_operation=None, reviewed_operation=None):
        return owner_mod._attest_core(
            journal=self.journal, work_root=self.work_root, active=self.active,
            child_pidfile=self.child, monitor_pidfile=self.monitor,
            runner=self.ps, owner_uid=UID,
            epoch_finalizing_operation=epoch_finalizing_operation,
            reviewed_operation=reviewed_operation,
            argv_reader=lambda pid: [EXE, *self.ps.args.split(),
                                     "--sockarg=0x200", "--user=nobody"],
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

    def test_exact_native_freebsd_shebang_monitor_and_foreign_argv_refusal(self):
        # The real OPNsense monitor is a #!/bin/sh script started via
        # /usr/sbin/daemon -f. Its ps(1) argv can start with /bin/sh.
        self.ps.monitor_exe = "/bin/sh " + MONITOR
        self.assertEqual(self.witness().operation_id, OP_ID)
        # Exact executable, callback, child PIDfile and child binary still
        # matter. No shell -c, alternate interpreter, or trailing tokens.
        for foreign in (
            "/bin/sh -c " + MONITOR,
            "/usr/bin/env sh " + MONITOR,
            "/bin/sh " + MONITOR + " --foreign",
            "/bin/sh /tmp/foreign-monitor",
        ):
            self.ps.monitor_exe = foreign
            self.refuses()
        self.ps.monitor_exe = "/bin/sh " + MONITOR
        self.ps.child_pidfile = self.run / "other-child.pid"
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

    def test_epoch_finalizing_is_not_a_public_current_owner(self):
        self.record["phase"] = "epoch-finalizing"
        self._write(self.journal / "operation.json", json.dumps(self.record))
        self.refuses()  # ordinary P2c / minute worker cannot accept it
        proof = self.witness(epoch_finalizing_operation=OP_ID)
        self.assertEqual(proof.generation, OP_ID)
        self.assertEqual(proof.owner.pid, PID)
        with self.assertRaises(owner_mod.GenerationRefused):
            self.witness(epoch_finalizing_operation="f" * 32)
        self.record["phase"] = "activated"
        self._write(self.journal / "operation.json", json.dumps(self.record))
        with self.assertRaises(owner_mod.GenerationRefused):
            self.witness(epoch_finalizing_operation=OP_ID)
        self.record["phase"] = "committed"
        self._write(self.journal / "operation.json", json.dumps(self.record))
        with self.assertRaises(owner_mod.GenerationRefused):
            self.witness(epoch_finalizing_operation=OP_ID)
        self.assertEqual(self.witness().generation, OP_ID)

    def test_freebsd_kernel_argv_above_ps_limit_and_malformed_refusal(self):
        long_argv = [EXE, "--port=989", "--lua-init=@" + "x" * 2200,
                     "--sockarg=0x200", "--user=nobody"]
        kernel = FakeArgvSysctl(long_argv)
        self.assertGreater(len(kernel.raw), 2048)
        self.assertEqual(owner_mod._freebsd_argv(PID, sysctl_call=kernel), long_argv)
        for bad in (b"\x00", b"/bin/foo", b"/bin/foo\x00\x00",
                    b"/bin/foo\xff\x00"):
            malformed = FakeArgvSysctl([EXE])
            malformed.raw = bad
            with self.assertRaises(owner_mod.GenerationRefused):
                owner_mod._freebsd_argv(PID, sysctl_call=malformed)
        with self.assertRaises(owner_mod.GenerationRefused):
            owner_mod._freebsd_argv(PID, sysctl_call=lambda *args: -1)

    def test_realistic_long_ps_display_is_not_kernel_argv(self):
        # Owner FreeBSD: ps -ww 2049 bytes; sealed args 2410;
        # procstat -c 2582 bytes, including both mandatory suffix flags.
        self.argv = self.argv.replace(
            "--filter-tcp=443\n",
            "--lua-init=@" + "x" * 2200 + "\n--filter-tcp=443\n", 1)
        self.map["final_args_sha256"] = hashlib.sha256(self.argv.encode()).hexdigest()
        self.refresh()
        self.ps.truncate_child_at = 2048
        self.assertEqual(self.witness().generation, OP_ID)
        self.ps.args += " --foreign-hidden-after-2048"
        self.refuses()

    def test_reviewed_native_is_never_public_minute_owner(self):
        # Owner _70 auto-mode failure: one previous committed owner, the new
        # sealed process/monitor present, but no terminal shared journal.
        prior = {"id": "a" * 32, "page": "strategies",
                 "base": "c" * 64, "candidate": BASE, "changed_fields": []}
        self.record["phase"] = "requires-review"
        self.record["previous"] = prior
        self.record["detail"]["page"] = "strategies"
        self.record["detail"]["changed_fields"] = ["hostlist.mode"]
        self._write(self.journal / "operation.json", json.dumps(self.record))
        self._write(self.work / "plan.json",
                    json.dumps({"page": "strategies", "dependencies": BASE,
                                "changed_fields": ["hostlist.mode"]}) + "\n")
        self.refresh()
        self.refuses()
        reviewed = self.witness(reviewed_operation=OP_ID)
        self.assertEqual(reviewed.operation_id, OP_ID)
        for bad in ("activated", "epoch-finalizing", "committed", "restored"):
            self.record["phase"] = bad
            self._write(self.journal / "operation.json", json.dumps(self.record))
            with self.assertRaises(owner_mod.GenerationRefused):
                self.witness(reviewed_operation=OP_ID)
        self.record["phase"] = "requires-review"
        self.record["detail"]["changed_fields"] = ["voice.telegram.enabled"]
        self._write(self.journal / "operation.json", json.dumps(self.record))
        with self.assertRaises((owner_mod.GenerationRefused, SharedOperationError)):
            self.witness(reviewed_operation=OP_ID)
        self.record["detail"]["changed_fields"] = ["hostlist.mode"]
        self._write(self.journal / "operation.json", json.dumps(self.record))
        self.ps.args += " --foreign-after-verified-tail"
        with self.assertRaises(owner_mod.GenerationRefused):
            self.witness(reviewed_operation=OP_ID)
        self.ps.args = " ".join(self.argv.split())
        self.assertEqual(self.witness(reviewed_operation=OP_ID), reviewed)
        with self.assertRaises(owner_mod.GenerationRefused):
            self.witness(reviewed_operation="f" * 32)

    def test_reviewed_native_service_uses_real_fd9_and_postcommit_proof(self):
        service = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
        shell = service.read_text(encoding="utf-8")
        prefix = "shared_apply_recover_reviewed_native_service()\n{\n"
        start = shell.index(prefix)
        end = shell.index("\n}\n", start) + 3
        recovery = shell[start:end]
        syntax = subprocess.run(["/bin/sh", "-n", str(service)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        required = (
            'ZAPRET_OWNER_REVIEW_RECOVERY',
            'preflight_shared_apply_journal common-recover-reviewed-native',
            'shared_apply_native_config saved',
            'atomic_verify_tree',
            'apply_runtime_probe',
            'firewall_shared_runtime verify - "$ACTIVE_DIR"',
            'finish-reviewed-epoch',
            'finish-reviewed-native',
            'shared_apply_status_observe_service',
        )
        for token in required:
            self.assertIn(token, recovery)
        self.assertLess(recovery.index('wan_first_service require'),
                        recovery.index('finish-reviewed-epoch'))
        self.assertLess(recovery.index('firewall_shared_runtime verify - "$ACTIVE_DIR"'),
                        recovery.index('finish-reviewed-epoch'))
        self.assertLess(recovery.index('finish-reviewed-epoch'),
                        recovery.index('finish-reviewed-native'))
        for forbidden in ("supervisor_stop", "launcher_stop", "ipfw delete",
                          "rm -f", "SIGSTOP", "SIGCONT", "configctl"):
            self.assertNotIn(forbidden, recovery)
        self.assertIn('shared-apply-recover-reviewed-native)', shell)

    def stopped_fixture(self):
        # Physically persist the same original root-private pretraffic/epoch
        # receipt that binds the old PID/birth to a real sealed release.
        self.producer = self.work_root.parent / "producer"
        self.producer.mkdir(mode=0o700)
        (self.producer / "pending").mkdir(mode=0o700)
        raw = self.producer / "inbox.txt"
        debug = self.producer / "debug.log"
        self._write(raw, "")
        self._write(debug, "")
        self.queue = DurableInbox(self.producer, owner_uid=UID)
        self.epochs = self.work_root.parent / "epochs"
        self.receipts = EpochReceipts(self.epochs, owner_uid=UID)
        # The original test map must reference exactly those native inodes.
        self.argv = self.argv.replace(RAW, str(raw)).replace(DEBUG, str(debug))
        self.map["raw_path"], self.map["debug_path"] = str(raw), str(debug)
        self.map["final_args_sha256"] = __import__("hashlib").sha256(
            self.argv.encode()).hexdigest()
        self.refresh()
        current = self.witness()
        with self.queue.exclusive():
            self.receipts.seal_pretraffic(
                self.queue, workspace=self.work, candidate_sha256=CANDIDATE)
            self.receipts.finish_running(
                current, self.queue, attest=lambda: current)
        self.child.unlink()
        self.monitor.unlink()
        self.ps.stopped = True
        return current

    def stopped_witness(self):
        return owner_mod._attest_stopped_core(
            journal=self.journal, work_root=self.work_root, active=self.active,
            child_pidfile=self.child, monitor_pidfile=self.monitor,
            epoch_root=self.epochs, runner=self.ps, owner_uid=UID)

    def test_stopped_exact_prior_epoch_is_not_new_engine_owner(self):
        previous = self.stopped_fixture()
        stopped = self.stopped_witness()
        self.assertEqual(stopped, previous)
        # The same proof cannot be used as a new running process.
        # _attest_core is the raw fixture primitive: absent pidfiles cause
        # its underlying protected read to raise OSError. The public native
        # attester wraps that as GenerationRefused.
        with self.assertRaises((owner_mod.GenerationRefused, OSError)):
            self.witness()
        self.assertTrue(any("-A" in cmd for cmd in self.ps.commands))

    def test_stopped_native_ps_includes_kernel_init_but_refuses_owners(self):
        previous = self.stopped_fixture()
        # Actual FreeBSD ps -A lists PID 0/1 as well as user processes.
        self.assertEqual(self.stopped_witness(), previous)
        for rows in (
            "0 " + EXE + "\\n",
            "1 " + MONITOR + "\\n",
            "82 /bin/sh " + MONITOR + " /var/run/dvtws2.pid\\n",
            "82 " + EXE + " --port=989\\n",
            "82\\n",
            "invalid /bin/ps\\n",
        ):
            self.ps.stopped_rows = rows.replace("\\n", "\n")
            with self.assertRaises(owner_mod.GenerationRefused):
                self.stopped_witness()

    def test_stopped_refuses_old_engine_or_pidfile_or_changed_journal(self):
        self.stopped_fixture()
        self.ps.stopped = False
        with self.assertRaises(owner_mod.GenerationRefused):
            self.stopped_witness()
        self.ps.stopped = True
        self._write(self.child, f"{PID}\\n".replace("\\n", "\n"))
        with self.assertRaises(owner_mod.GenerationRefused):
            self.stopped_witness()
        self.child.unlink()
        self.record["phase"] = "prepared"
        self._write(self.journal / "operation.json", json.dumps(self.record))
        with self.assertRaises(owner_mod.GenerationRefused):
            self.stopped_witness()

    def test_stopped_refuses_invalid_prior_birth_or_active_release(self):
        self.stopped_fixture()
        epoch = self.epochs / OP_ID / "epoch.json"
        recorded = json.loads(epoch.read_text())
        recorded["owner_start"] = "not-a-native-process-start"
        self._write(epoch, json.dumps(recorded))
        with self.assertRaises(owner_mod.GenerationRefused):
            self.stopped_witness()
        self._write(epoch, json.dumps({**recorded, "owner_start": START}))
        self.assertEqual(self.stopped_witness().owner.started, START)
        self._write(self.active / "dvtws.args", "--port=999\n")
        with self.assertRaises(owner_mod.GenerationRefused):
            self.stopped_witness()

    def test_nonroot_or_offtarget_public_api_refuses(self):
        # The public path is strict; these positive synthetic fixture checks
        # do not imply permission to run on a user appliance.
        with self.assertRaises(owner_mod.GenerationRefused):
            owner_mod.attest_running_generation(journal=self.journal, work_root=self.work_root,
                   active=self.active, child_pidfile=self.child, monitor_pidfile=self.monitor,
                   runner=self.ps)


if __name__ == "__main__":
    unittest.main(verbosity=2)
