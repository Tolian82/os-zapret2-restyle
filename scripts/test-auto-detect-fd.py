#!/usr/bin/env python3
"""P2b FreeBSD native fstat parser and read-only FD lifecycle witness.

Portable cases are pure/injected. Native test is a disposable OPNsense guest
with a real kernel writer FD, NOT a production dvtws2 owner/map proof.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

MODULE = (Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/"
          "Zapret/backend/auto_detect_fd.py")
# Running this script standalone outside a repo is also useful for S0.
if not MODULE.is_file():
    MODULE = Path(__file__).with_name("auto_detect_fd.py")
spec = importlib.util.spec_from_file_location("p2b_fd", MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

STAMP = "Fri Nov 13 07:00:00 2026"
EXE = "/usr/local/bin/dvtws2"
HEADER = "USER CMD PID FD DEV INUM MODE SZ|DV R/W NAME\n"


class FakeRunner:
    def __init__(self, ps=None, fstat=None, rc=0, stderr=""):
        self.ps = ps or f"{STAMP} {EXE} --port=19899\n"
        self.fstat = HEADER if fstat is None else fstat
        self.rc = rc
        self.stderr = stderr
        self.commands = []

    def __call__(self, args, **_):
        self.commands.append(args)
        if args[0].endswith("/ps"):
            return subprocess.CompletedProcess(args, 0, self.ps, "")
        return subprocess.CompletedProcess(args, self.rc, self.fstat, self.stderr)


class FDPortable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.segment = Path(self.tmp.name) / "pending.txt"
        self.segment.write_bytes(b"ok.test\n")
        self.segment.chmod(0o600)
        self.stat = self.segment.stat()
        self.owner = mod.OwnerToken(123, STAMP, EXE)
        self.devid = hex(self.stat.st_dev)

    def probe(self, runner, **kwargs):
        # Portable Linux CI runs unprivileged. Preserve production root-only
        # semantics while injecting a synthetic root-owned inode for parsing.
        original_fstat = os.fstat
        def as_root(fd):
            st = original_fstat(fd)
            return SimpleNamespace(st_uid=0, st_gid=st.st_gid, st_mode=st.st_mode, st_dev=st.st_dev,
                                   st_ino=st.st_ino, st_nlink=st.st_nlink,
                                   st_size=st.st_size, st_mtime_ns=st.st_mtime_ns)
        with mock.patch.object(mod.os, "geteuid", return_value=0), \
             mock.patch.object(mod.os, "fstat", side_effect=as_root):
            return mod.probe_pending_fd(self.segment, self.stat.st_dev, self.stat.st_ino,
                                        owner=self.owner, runner=runner,
                                        platform="freebsd15", **kwargs)

    def stopped_probe(self, runner, attest, *, learning=False, retiring=False, **kwargs):
        # The original FD9 epoch witness is injected only in this portable
        # parser fixture; the real method always imports the native one.
        original_fstat = os.fstat

        def as_root(fd):
            st = original_fstat(fd)
            return SimpleNamespace(st_uid=0, st_gid=st.st_gid,
                                   st_mode=st.st_mode, st_dev=st.st_dev,
                                   st_ino=st.st_ino, st_nlink=st.st_nlink,
                                   st_size=st.st_size, st_mtime_ns=st.st_mtime_ns)

        with mock.patch.object(mod.os, "geteuid", return_value=0), \
             mock.patch.object(mod.os, "fstat", side_effect=as_root), \
             mock.patch.dict(sys.modules, {
                 "auto_detect_owner": SimpleNamespace(
                     attest_stopped_generation=(
                         attest if not learning else
                         mock.Mock(side_effect=AssertionError("schema2_stop_called"))),
                     attest_learning_stopped_generation=(
                         attest if learning and not retiring else
                         mock.Mock(side_effect=AssertionError("schema3_stop_called"))),
                     attest_retiring_learning_predecessor=(
                         attest if retiring else
                         mock.Mock(side_effect=AssertionError("predecessor_called"))))
             }):
            probe = (mod.probe_retiring_learning_pending_fd if retiring
                     else mod.probe_stopped_learning_pending_fd if learning
                     else mod.probe_stopped_pending_fd)
            return probe(
                self.segment, self.stat.st_dev, self.stat.st_ino,
                owner=self.owner, runner=runner, platform="freebsd15", **kwargs)

    def test_stopped_old_epoch_uses_same_global_kernel_fd_scan(self):
        from unittest.mock import Mock
        attest = Mock(return_value=SimpleNamespace(owner=self.owner))
        runner = FakeRunner()
        self.assertEqual(self.stopped_probe(runner, attest), mod.FDState.DRAINED)
        self.assertEqual(attest.call_count, 2)
        self.assertEqual([x[0] for x in runner.commands], ["/usr/bin/fstat"])

    def test_stopped_old_owner_with_foreign_open_writer_remains_busy(self):
        from unittest.mock import Mock
        attest = Mock(return_value=SimpleNamespace(owner=self.owner))
        row = (f"root previous 991 7 {self.devid} {self.stat.st_ino} "
               f"100600 8 w {self.segment}\n")
        self.assertEqual(self.stopped_probe(FakeRunner(fstat=HEADER + row),
                                            attest), mod.FDState.BUSY)

    def test_stopped_refuses_changed_or_missing_epoch_owner(self):
        from unittest.mock import Mock
        stale = SimpleNamespace(owner=mod.OwnerToken(
            self.owner.pid + 1, self.owner.started, self.owner.executable))
        runner = FakeRunner()
        self.assertEqual(self.stopped_probe(runner, Mock(return_value=stale)),
                         mod.FDState.UNKNOWN)
        self.assertEqual(runner.commands, [])  # no FD access until proof
        runner = FakeRunner()
        attest = Mock(side_effect=[SimpleNamespace(owner=self.owner), stale])
        self.assertEqual(self.stopped_probe(runner, attest), mod.FDState.UNKNOWN)
        self.assertEqual(len(runner.commands), 1)

    def test_stopped_learning_uses_exact_schema3_attester_not_legacy(self):
        from unittest.mock import Mock
        attest = Mock(return_value=SimpleNamespace(owner=self.owner))
        runner = FakeRunner()
        self.assertEqual(
            self.stopped_probe(runner, attest, learning=True), mod.FDState.DRAINED)
        self.assertEqual(attest.call_count, 2)
        self.assertEqual([x[0] for x in runner.commands], ["/usr/bin/fstat"])

    def test_schema3_prepared_predecessor_uses_same_global_fd_scan(self):
        from unittest.mock import Mock
        attest = Mock(return_value=SimpleNamespace(owner=self.owner))
        runner = FakeRunner()
        self.assertEqual(
            self.stopped_probe(runner, attest, learning=True, retiring=True),
            mod.FDState.DRAINED)
        self.assertEqual(attest.call_count, 2)
        self.assertEqual([x[0] for x in runner.commands], ["/usr/bin/fstat"])
        old = self.owner
        self.owner = mod.OwnerToken(old.pid + 3, old.started, old.executable)
        self.assertEqual(
            self.stopped_probe(FakeRunner(), attest,
                               learning=True, retiring=True), mod.FDState.UNKNOWN)

    def test_schema3_prepared_predecessor_preserves_foreign_open_fd(self):
        from unittest.mock import Mock
        attest = Mock(return_value=SimpleNamespace(owner=self.owner))
        row = (f"root previous 991 7 {self.devid} {self.stat.st_ino} "
               f"100600 8 w {self.segment}\n")
        self.assertEqual(
            self.stopped_probe(FakeRunner(fstat=HEADER + row), attest,
                               learning=True, retiring=True), mod.FDState.BUSY)

    def test_stopped_learning_preserves_foreign_open_inode(self):
        from unittest.mock import Mock
        attest = Mock(return_value=SimpleNamespace(owner=self.owner))
        row = (f"root previous 991 7 {self.devid} {self.stat.st_ino} "
               f"100600 8 w {self.segment}\n")
        self.assertEqual(
            self.stopped_probe(FakeRunner(fstat=HEADER + row), attest,
                               learning=True), mod.FDState.BUSY)

    def test_stopped_learning_refuses_changed_owner_during_census(self):
        from unittest.mock import Mock
        stale = SimpleNamespace(owner=mod.OwnerToken(
            self.owner.pid + 1, self.owner.started, self.owner.executable))
        runner = FakeRunner()
        attest = Mock(side_effect=[SimpleNamespace(owner=self.owner), stale])
        self.assertEqual(
            self.stopped_probe(runner, attest, learning=True), mod.FDState.UNKNOWN)
        self.assertEqual(len(runner.commands), 1)

    def test_closed_inode_with_exact_owner_and_header(self):
        r = FakeRunner()
        self.assertEqual(self.probe(r), mod.FDState.DRAINED)
        self.assertEqual(len(r.commands), 3)
        self.assertNotIn("-p", r.commands[1])
        self.assertIn("-m", r.commands[1])
        self.assertEqual(r.commands[1][-1], str(self.segment))

    def test_qualified_group_writer_requires_explicit_engine_group(self):
        self.segment.chmod(0o660)
        self.stat = self.segment.stat()
        self.assertEqual(self.probe(FakeRunner()), mod.FDState.UNKNOWN)
        if self.stat.st_gid > 0:
            self.assertEqual(self.probe(FakeRunner(), writer_gid=self.stat.st_gid),
                             mod.FDState.DRAINED)
            self.assertEqual(self.probe(FakeRunner(), writer_gid=self.stat.st_gid + 1),
                             mod.FDState.UNKNOWN)
        self.segment.chmod(0o666)
        self.assertEqual(self.probe(FakeRunner(), writer_gid=max(self.stat.st_gid, 1)),
                         mod.FDState.UNKNOWN)

    def test_open_writer_blocks_acknowledgement(self):
        body = f"root dvtws2 123 4 {self.devid} {self.stat.st_ino} 100600 8 w {self.segment}\n"
        self.assertEqual(self.probe(FakeRunner(fstat=HEADER + body)), mod.FDState.BUSY)

    def test_historical_pid_writer_blocks_when_current_pid_has_no_fd(self):
        # PRE-FIX reproducer: -p 123 sees no current engine writer, but
        # the previous process PID 991 still holds this original inode.
        row = (f"root previous 991 7 {self.devid} {self.stat.st_ino} "
               f"100600 8 w {self.segment}\n")
        self.assertEqual(self.probe(FakeRunner(fstat=HEADER + row)),
                         mod.FDState.BUSY)

    def test_unrelated_pid_reader_also_conservatively_blocks(self):
        row = (f"root reader 992 6 {self.devid} {self.stat.st_ino} "
               f"100600 8 r {self.segment}\n")
        self.assertEqual(self.probe(FakeRunner(fstat=HEADER + row)),
                         mod.FDState.BUSY)

    def test_only_own_pinned_read_fd_may_be_skipped(self):
        own_pid, pinned_fd = 1333, 17
        own = (f"root inspector {own_pid} {pinned_fd} {self.devid} "
               f"{self.stat.st_ino} 100600 8 r {self.segment}\n")
        old = (f"root oldengine 991 7 {self.devid} {self.stat.st_ino} "
               f"100600 8 rw {self.segment}\n")
        scan = lambda rows: mod._all_rows(HEADER + rows, self.stat.st_dev,
                                         self.stat.st_ino,
                                         inspector_pid=own_pid,
                                         inspector_fd=pinned_fd)
        self.assertEqual(scan(own), mod.FDState.DRAINED)
        self.assertEqual(scan(own + old), mod.FDState.BUSY)
        self.assertEqual(scan(own.replace(" 8 r ", " 8 w ")), mod.FDState.BUSY)
        self.assertEqual(scan(own.replace(f" {pinned_fd} ", " 18 ")),
                         mod.FDState.BUSY)
        self.assertEqual(scan(own.replace(" 1333 ", " 1334 ")),
                         mod.FDState.BUSY)

    def test_kernel_scan_corruption_never_grants_drain(self):
        old = (f"root oldengine 991 7 {self.devid} {self.stat.st_ino} "
               f"100600 8 w {self.segment}\n")
        for invalid in ("root bad 0 7 " + old.split(" 7 ", 1)[1],
                        old.replace(" 991 ", " x "),
                        old.replace(" 7 ", " mmap "),
                        old.replace(" 100600 ", " badmode "),
                        old.replace(f" {self.devid} ", " 0xdead "),
                        old + "unparsed remainder\n"):
            with self.subTest(row=invalid[:70]):
                self.assertEqual(self.probe(FakeRunner(fstat=HEADER + invalid)),
                                 mod.FDState.UNKNOWN)

    def test_open_reader_is_conservatively_busy(self):
        body = f"root dvtws2 123 5 {self.devid} {self.stat.st_ino} 100600 8 r {self.segment}\n"
        self.assertEqual(self.probe(FakeRunner(fstat=HEADER + body)), mod.FDState.BUSY)

    def test_bad_owner_birth_or_executable_is_unknown(self):
        self.assertEqual(self.probe(FakeRunner(ps=f"{STAMP} /tmp/dvtws2 --port=19899\n")), mod.FDState.UNKNOWN)
        self.owner = mod.OwnerToken(123, "Fri Nov 13 07:00:01 2026", EXE)
        self.assertEqual(self.probe(FakeRunner()), mod.FDState.UNKNOWN)

    def test_missing_or_truncated_native_header_is_unknown(self):
        for text in ("", "wrong header\n", HEADER + "broken line\n"):
            with self.subTest(text=text):
                self.assertEqual(self.probe(FakeRunner(fstat=text)), mod.FDState.UNKNOWN)

    def test_foreign_inode_or_dev_in_filtered_rows_is_unknown(self):
        for dev, inode in ((self.devid, self.stat.st_ino + 1), ("0xdeadbeef", self.stat.st_ino)):
            row = f"root dvtws2 123 4 {dev} {inode} 100600 8 rw {self.segment}\n"
            self.assertEqual(self.probe(FakeRunner(fstat=HEADER + row)), mod.FDState.UNKNOWN)

    def test_fstat_error_or_verbose_warning_is_unknown(self):
        self.assertEqual(self.probe(FakeRunner(rc=1)), mod.FDState.UNKNOWN)
        self.assertEqual(self.probe(FakeRunner(stderr="incomplete vnode\n")), mod.FDState.UNKNOWN)

    def test_platform_and_bad_owner_refuse(self):
        r = FakeRunner()
        self.assertEqual(mod.probe_pending_fd(self.segment, self.stat.st_dev, self.stat.st_ino,
                         owner=self.owner, runner=r, platform="linux"), mod.FDState.UNKNOWN)
        self.assertEqual(r.commands, [])
        self.owner = mod.OwnerToken(0, STAMP, EXE)
        self.assertEqual(self.probe(r), mod.FDState.UNKNOWN)

    def test_symlink_or_modified_inode_refuses(self):
        target = self.segment.with_name("renamed.txt")
        self.segment.rename(target)
        self.segment.symlink_to(target)
        self.assertEqual(self.probe(FakeRunner()), mod.FDState.UNKNOWN)
        self.segment.unlink()
        self.segment.write_bytes(b"new inode\n")
        self.segment.chmod(0o600)
        self.assertEqual(self.probe(FakeRunner()), mod.FDState.UNKNOWN)


def native() -> None:
    if not (sys.platform.startswith("freebsd") and os.geteuid() == 0 and
            os.environ.get("GITHUB_ACTIONS") == "true" and
            os.environ.get("ZAPRET_P2B_DISPOSABLE") == "1" and
            Path("/usr/local/opnsense").is_dir()):
        raise RuntimeError("P2B_DISPOSABLE_OPNSENSE_GUEST_REQUIRED")
    code = """import sys
f = open(sys.argv[1], 'ab', buffering=0)
print('OPEN', flush=True)
sys.stdin.readline()
f.close()
print('CLOSED', flush=True)
sys.stdin.readline()
"""
    with tempfile.TemporaryDirectory(prefix="p2b-fstat-") as dirname:
        segment = Path(dirname) / "segment.txt"
        segment.write_bytes(b"example.test\n")
        segment.chmod(0o600)
        process = subprocess.Popen([sys.executable, "-c", code, str(segment)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            if process.stdout.readline().strip() != "OPEN":
                raise RuntimeError("NATIVE_CHILD_NOT_OPEN")
            raw = subprocess.check_output(["/bin/ps", "-ww", "-p", str(process.pid),
                                           "-o", "lstart=", "-o", "command="],
                                          text=True, timeout=5).strip()
            fields = raw.split(maxsplit=5)
            if len(fields) != 6 or fields[5].split()[0] != sys.executable:
                raise RuntimeError("NATIVE_OWNER_STAMP_UNREADABLE")
            token = mod.OwnerToken(process.pid, " ".join(fields[:5]), sys.executable)
            stat_before = segment.stat()
            probe = lambda: mod.probe_pending_fd(segment, stat_before.st_dev,
                                                   stat_before.st_ino, owner=token)
            held = probe()
            if held != mod.FDState.BUSY:
                # This test has only synthetic input and a disposable child.
                # Report the native kernel formatting, not any user traffic.
                inspected = subprocess.run(["/usr/bin/fstat", "-n", "-v", "-m",
                                            str(segment)],
                                           capture_output=True, text=True, timeout=5)
                print(f"P2B_TEST_FSTAT_DIAGNOSTIC={inspected.returncode}:"
                      f"{inspected.stdout[:1024]!r}:{inspected.stderr[:256]!r}",
                      file=sys.stderr, flush=True)
                raise RuntimeError(f"NATIVE_HELD_WRITER_WAS_NOT_DETECTED:{held.value}")
            process.stdin.write("close\n")
            process.stdin.flush()
            if process.stdout.readline().strip() != "CLOSED":
                raise RuntimeError("NATIVE_CHILD_DID_NOT_CLOSE")
            if probe() != mod.FDState.DRAINED:
                raise RuntimeError("NATIVE_CLOSED_WRITER_NOT_DETECTED")
            # With the current P2c owner alive but its FD CLOSED, emulate
            # the old generation still writing the very same raw inode.
            # The old -p owner-only probe returned DRAINED: data-loss gate.
            historical = subprocess.Popen(
                [sys.executable, "-c", code, str(segment)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True)
            try:
                if historical.stdout.readline().strip() != "OPEN":
                    raise RuntimeError("NATIVE_HISTORICAL_WRITER_NOT_OPEN")
                if probe() != mod.FDState.BUSY:
                    raise RuntimeError("NATIVE_OLD_PID_STILL_OPEN_WAS_NOT_DETECTED")
                historical.stdin.write("close\n")
                historical.stdin.flush()
                if historical.stdout.readline().strip() != "CLOSED":
                    raise RuntimeError("NATIVE_OLD_PID_DID_NOT_CLOSE")
                if probe() != mod.FDState.DRAINED:
                    raise RuntimeError("NATIVE_OLD_PID_CLOSE_NOT_DETECTED")
            finally:
                if historical.poll() is None:
                    historical.stdin.write("exit\n")
                    historical.stdin.flush()
                try:
                    historical.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    historical.kill()
                    historical.communicate(timeout=5)
            bad = mod.OwnerToken(process.pid, "Fri Nov 13 00:00:00 2000", sys.executable)
            if mod.probe_pending_fd(segment, stat_before.st_dev, stat_before.st_ino,
                                    owner=bad) != mod.FDState.UNKNOWN:
                raise RuntimeError("NATIVE_WRONG_BIRTH_WAS_ACCEPTED")
        finally:
            if process.poll() is None:
                process.stdin.write("exit\n")
                process.stdin.flush()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
        if probe() != mod.FDState.UNKNOWN:
            raise RuntimeError("NATIVE_REAPED_OWNER_WAS_ACCEPTED")
    print("P2B_NATIVE_FSTAT=PASS_FREEBSD_ALL_PID_HISTORICAL_WRITER_FD_CLOSED", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--native"]:
        native()
    elif sys.argv[1:] in ([], ["--self-test"]):
        unittest.main(argv=[sys.argv[0]], verbosity=2)
    else:
        raise SystemExit("usage: --self-test | --native")
