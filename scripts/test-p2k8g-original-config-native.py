#!/usr/bin/env python3
"""#1052 P2k8g: actual OPNsense Config flock + original queue FD, one native VM.

One disposable guest, no installed zapret2, Config save or IPFW mutations.
Real 3-process FD/OFD test; synthetic Hostlist Model and inert destination
receipt mean this is NOT actual native dvtws2/ACK/worker acceptance.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
sys.path.insert(0, str(BACKEND))
from auto_detect_original_lock_handoff import run_original_pending_cycle
from auto_detect_queue import DurableInbox

MARK = "P2K8G_ORIGINAL_NATIVE_CONFIG_FD"
CONFIG = Path("/conf/config.xml")
PHP = Path("/usr/local/bin/php")
FIXTURE = HERE / "test-auto-detect-original-lock-handoff.php"
CHILD = HERE / "test-auto-detect-original-lock-handoff.py"
WRAPPER = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret/python_runtime.sh"
POLICY = HERE.parent / "compatibility.json"
SEGMENT = "a" * 32 + "-" + "c" * 32 + ".txt"


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def guest_guard() -> None:
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
         "FREEBSD_ROOT_ONLY")
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_P2K8G_DISPOSABLE_NATIVE") == "1",
         "DISPOSABLE_NATIVE_OPT_IN_REQUIRED")
    need(PHP.is_file() and os.access(PHP, os.X_OK) and FIXTURE.is_file() and
         CHILD.is_file() and WRAPPER.is_file() and os.access(WRAPPER, os.X_OK) and
         POLICY.is_file() and CONFIG.is_file() and not CONFIG.is_symlink(),
         "ORIGINAL_NATIVE_CONFIG_OR_PHP_UNAVAILABLE")
    st, parent = CONFIG.lstat(), CONFIG.parent.lstat()
    # Only inode/permission metadata is logged. Never expose XML contents,
    # hostlist names or Config data when a native appliance disagrees.
    metadata = (
        f":file_type={stat.S_IFMT(st.st_mode):o},uid={st.st_uid},"
        f"gid={st.st_gid},mode={stat.S_IMODE(st.st_mode):04o},"
        f"nlink={st.st_nlink};parent_type={stat.S_IFMT(parent.st_mode):o},"
        f"parent_uid={parent.st_uid},parent_gid={parent.st_gid},"
        f"parent_mode={stat.S_IMODE(parent.st_mode):04o}"
    )
    # P2k8f's original fixed Config file may have a native non-root
    # owner; require the same UID for /conf, file and original descriptor,
    # plus root GID and no group/other write. Never accept a guessed UID.
    need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
         stat.S_ISDIR(parent.st_mode) and st.st_uid == parent.st_uid and
         st.st_gid == parent.st_gid == 0 and
         not st.st_mode & 0o022 and not parent.st_mode & 0o022,
         "ORIGINAL_NATIVE_CONFIG_INODE_UNSAFE" + metadata)


def blocked(file: Path) -> bool:
    """Independent *different* open description, not a dup of owned lock."""
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
    finally:
        os.close(fd)


def native() -> None:
    guest_guard()
    original_sha = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    original_stat = CONFIG.stat()
    with tempfile.TemporaryDirectory(prefix="p2k8g-original-", dir="/tmp") as directory:
        root = Path(directory)
        root.chmod(0o700)
        queue_dir = root / "queue"
        queue_dir.mkdir(mode=0o700)
        pending_dir = queue_dir / "pending"
        pending_dir.mkdir(mode=0o700)
        inbox = queue_dir / "inbox.txt"
        inbox.write_bytes(b"")
        inbox.chmod(0o600)
        pending = pending_dir / SEGMENT
        pending.write_bytes(b"youtube.example.co.uk\n")
        pending.chmod(0o600)
        queue = DurableInbox(queue_dir, owner_uid=0)

        env = {**os.environ,
               "P2K8G_USE_NATIVE_CONFIG": "1",
               "P2K8F_PYTHON": str(WRAPPER),
               "ZAPRET_PYTHON_BIN": sys.executable,
               "ZAPRET_PYTHON_POLICY": str(POLICY),
               "P2K8F_TEST_SCRIPT": str(CHILD),
               "P2K8F_QUEUE_PATH": str(queue.lock),
               "P2K8F_QUEUE_ROOT": str(queue_dir),
               "P2K8F_CONFIG_PATH": str(CONFIG),
               "P2K8F_UNLOCKED_CONFIG": "0",
               "PYTHONDONTWRITEBYTECODE": "1"}

        # The shipped Python runtime shim must independently pass the
        # installed OPNsense platform policy before we test its FD path.
        runtime = subprocess.run(
            [str(WRAPPER), "--check"], env=env,
            capture_output=True, text=True, timeout=15)
        need(runtime.returncode == 0 and runtime.stdout == "",
             "ORIGINAL_NATIVE_PYTHON_RUNTIME_PRECHECK_FAILED:"
             + str(runtime.returncode))
        # The unchanged public queue owner suppresses child stderr. For
        # native diagnosis, first invoke the SAME PHP Config callback under
        # the SAME original queue lock, collecting only fixed error classes,
        # stages and the test-grandchild's private content-free refusal.
        diagnosis = root / "child-refusal"
        diagnostic_env = {**env, "P2K8G_CHILD_DIAG": str(diagnosis)}
        with queue.exclusive():
            direct = subprocess.run(
                [str(PHP), str(FIXTURE), "commit-with-fds",
                 str(queue.locked_fd), pending.name],
                pass_fds=(queue.locked_fd,), env=diagnostic_env,
                capture_output=True, text=True, timeout=20)
        if direct.returncode != 0:
            # Accept only fixed test-diagnostic prefixes with safe ASCII
            # punctuation; do not echo arbitrary PHP stderr or raw values.
            allowed = set(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "0123456789_=:;-\\"
            )
            php_marker = next((
                line for line in direct.stderr.splitlines()
                if (line.startswith("P2K8G_NATIVE_GUARD_REFUSED=")
                    or line.startswith("P2K8G_NATIVE_STAGE="))
                and len(line) <= 256 and all(c in allowed for c in line)
            ), None)
            stderr_type = ("fatal" if "Fatal error" in direct.stderr else
                           "present" if direct.stderr else "empty")
            child_marker = (diagnosis.read_text().strip()
                            if diagnosis.is_file() else 'no_child_marker')
            # No actual PHP exception message, Config, user domains or
            # raw native stdout/stderr is ever printed in the CI log.
            raise RuntimeError(
                "ORIGINAL_NATIVE_PHP_DIAGNOSTIC:rc="
                + str(direct.returncode)
                + ":php=" + (php_marker if php_marker else 'no_marker')
                + ":stderr_kind=" + stderr_type
                + ":child=" + child_marker)
        need(pending.is_file(), "DIAGNOSTIC_CONFIG_PROBE_ACKED_PENDING")
        print(MARK + "_DIRECT_ORIGINAL_PHP_CONFIG_HANDLE=PASS", flush=True)

        # Exact original public queue owner callable, with the native PHP
        # Config instance and the real proc_open FDs; no independent lock.
        with _environment(env):
            result = run_original_pending_cycle(
                queue, pending, php_bin=str(PHP), php_script=FIXTURE, timeout=20)
        need(result.get("ack_authorized") is False and pending.is_file(),
             "NATIVE_CONFIG_TO_PYTHON_DID_NOT_RETAIN_PENDING")
        print(MARK + "_ORIGINAL_CONFIG_HANDLE_AND_QUEUE=PASS", flush=True)

        # Simulate original Config::save() releasing the flock, but never
        # invoke save() or write to /conf/config.xml on this guest.
        env_early = {**env, "P2K8G_SIMULATE_CONFIG_UNLOCK": "1"}
        with queue.exclusive():
            bad = subprocess.run(
                [str(PHP), str(FIXTURE), "commit-with-fds",
                 str(queue.locked_fd), pending.name],
                pass_fds=(queue.locked_fd,), env=env_early,
                capture_output=True, text=True, timeout=15)
        need(bad.returncode != 0 and pending.is_file(),
             "PREMATURE_CONFIG_UNLOCK_ACCEPTED_OR_PENDING_LOST")
        print(MARK + "_EARLY_CONFIG_UNLOCK_REFUSED=PASS", flush=True)

        # Independently open both lock inodes; once PHP is SIGKILLed
        # the *grandchild* must keep them blocked until released. This
        # catches lost-original-lock bugs hidden by short happy-path tests.
        ready, release = root / "child-ready", root / "child-release"
        parent = None
        grandchild_pid = None
        try:
            with queue.exclusive():
                hold_env = {**env,
                            "P2K8G_HOLD_READY": str(ready),
                            "P2K8G_HOLD_RELEASE": str(release)}
                parent = subprocess.Popen(
                    [str(PHP), str(FIXTURE), "commit-with-fds",
                     str(queue.locked_fd), pending.name],
                    pass_fds=(queue.locked_fd,), env=hold_env,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
                until = time.monotonic() + 10
                while not ready.is_file() and parent.poll() is None and time.monotonic() < until:
                    time.sleep(0.05)
                need(ready.is_file() and parent.poll() is None,
                     "NATIVE_CHILD_DID_NOT_ACQUIRE_BOTH_FDS")
                raw_pid = ready.read_text().strip()
                need(re.fullmatch(r"[0-9]{1,10}", raw_pid) is not None,
                     "NATIVE_CHILD_PID_INVALID")
                grandchild_pid = int(raw_pid)
                need(blocked(queue.lock) and blocked(CONFIG),
                     "ORIGINAL_LOCK_NOT_HELD_BEFORE_PARENT_DEATH")
                parent.kill()
                parent.wait(timeout=5)
            # The original queue owner exits its context and PHP is dead.
            # Only the Python child has both inherited descriptors now.
            need(blocked(queue.lock) and blocked(CONFIG),
                 "ORIGINAL_LOCK_DROPPED_BY_PHP_PARENT_DEATH")
            print(MARK + "_PHP_PARENT_DEATH_LOCKS_SURVIVE=PASS", flush=True)
            release.write_text("release\n")
            until = time.monotonic() + 10
            while time.monotonic() < until:
                if not blocked(queue.lock) and not blocked(CONFIG):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("ORPHANED_NATIVE_CHILD_LOCK_NOT_RELEASED")
            need(pending.is_file(), "ORIGINAL_PENDING_ACKED_ON_PARENT_DEATH")
            print(MARK + "_CHILD_EXIT_RELEASES_ORIGINAL_LOCKS=PASS", flush=True)
        finally:
            release.write_text("release\n")
            if parent is not None and parent.poll() is None:
                parent.kill()
                parent.wait(timeout=5)
            if grandchild_pid is not None and (blocked(queue.lock) or blocked(CONFIG)):
                try:
                    os.kill(grandchild_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        need(pending.read_bytes() == b"youtube.example.co.uk\n" and
             inbox.read_bytes() == b"",
             "NATIVE_LOCK_TEST_MUTATED_PENDING_OR_INBOX")
    after = CONFIG.stat()
    need(hashlib.sha256(CONFIG.read_bytes()).hexdigest() == original_sha and
         (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
         (original_stat.st_dev, original_stat.st_ino,
          original_stat.st_size, original_stat.st_mtime_ns),
         "TEST_MUTATED_ORIGINAL_CONFIG_XML")
    print(MARK + "_CONFIG_XML_UNTOUCHED=PASS", flush=True)
    print(MARK + "_SCOPE=REAL_OPNSENSE_CONFIG_LOCK_FD_NO_NATIVE_WRITER_OR_ACK",
          flush=True)


class _environment:
    def __init__(self, values: dict):
        self.values = values
        self.previous = {}

    def __enter__(self):
        self.previous = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.values)

    def __exit__(self, *_):
        os.environ.clear()
        os.environ.update(self.previous)


def main(args: list[str]) -> int:
    if args == ["--self-test"]:
        # This test is intentionally not permitted to fake FreeBSD with
        # environment variables; the native branch must really execute.
        if not sys.platform.startswith("freebsd"):
            try:
                guest_guard()
            except RuntimeError as e:
                need("FREEBSD_ROOT_ONLY" in str(e), "OFF_NATIVE_GUARD_CHANGED")
        print(MARK + "_HOST_GUARD=PASS")
        return 0
    if args != ["--native"]:
        return 64
    try:
        native()
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(MARK + "_FAIL=" + str(exc), file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
