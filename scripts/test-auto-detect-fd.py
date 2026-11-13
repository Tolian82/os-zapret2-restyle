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
        self.devid = f"{os.major(self.stat.st_dev)},{os.minor(self.stat.st_dev)}"

    def probe(self, runner, **kwargs):
        return mod.probe_pending_fd(self.segment, self.stat.st_dev, self.stat.st_ino,
                                    owner=self.owner, runner=runner,
                                    platform="freebsd15", **kwargs)

    def test_closed_inode_with_exact_owner_and_header(self):
        r = FakeRunner()
        self.assertEqual(self.probe(r), mod.FDState.DRAINED)
        self.assertEqual(len(r.commands), 3)
        self.assertIn("-p", r.commands[1])
        self.assertEqual(r.commands[1][-1], str(self.segment))

    def test_open_writer_blocks_acknowledgement(self):
        body = f"root dvtws2 123 4 {self.devid} {self.stat.st_ino} 100600 8 w {self.segment}\n"
        self.assertEqual(self.probe(FakeRunner(fstat=HEADER + body)), mod.FDState.BUSY)

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
        for dev, inode in ((self.devid, self.stat.st_ino + 1), ("99,77", self.stat.st_ino)):
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
            if probe() != mod.FDState.BUSY:
                raise RuntimeError("NATIVE_HELD_WRITER_WAS_NOT_DETECTED")
            process.stdin.write("close\n")
            process.stdin.flush()
            if process.stdout.readline().strip() != "CLOSED":
                raise RuntimeError("NATIVE_CHILD_DID_NOT_CLOSE")
            if probe() != mod.FDState.DRAINED:
                raise RuntimeError("NATIVE_CLOSED_WRITER_NOT_DETECTED")
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
    print("P2B_NATIVE_FSTAT=PASS_FREEBSD_HELD_AND_CLOSED_FD_ONLY", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--native"]:
        native()
    elif sys.argv[1:] in ([], ["--self-test"]):
        unittest.main(argv=[sys.argv[0]], verbosity=2)
    else:
        raise SystemExit("usage: --self-test | --native")
