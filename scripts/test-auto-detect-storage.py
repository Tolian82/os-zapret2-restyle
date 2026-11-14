#!/usr/bin/env python3
"""P2g protected raw/debug layout and dormant queue, with optional FreeBSD UID proof.

The real engine/FD9/Config/IPFW/cron is never touched. Native mode only
operates on a clean disposable CI VM using the exact future producer root.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import pwd
import shutil
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from auto_detect_storage import _prepare, StorageRefused, ROOT as PRODUCER
from auto_detect_queue import DurableInbox, QueueSafetyError


def need(condition, message):
    if not condition:
        raise RuntimeError("P2G_" + message)


def scenario(parent: Path, uid: int, gid: int):
    work = parent / "zapret2-auto-detect"
    _prepare(work, uid=uid, engine_gid=gid)
    _prepare(work, uid=uid, engine_gid=gid)  # idempotent; no truncate.
    need(stat.S_IMODE(work.stat().st_mode) == 0o710, "ROOT_MODE")
    need(stat.S_IMODE((work / "pending").stat().st_mode) == 0o700, "PENDING_MODE")
    for file in ("inbox.txt", "debug.log"):
        need(stat.S_IMODE((work / file).stat().st_mode) == 0o660,
             "WRITER_FILE_MODE:" + file)
    (work / "inbox.txt").write_bytes(b"first.example\n")
    _prepare(work, uid=uid, engine_gid=gid)
    need((work / "inbox.txt").read_bytes() == b"first.example\n", "NO_TRUNCATE")
    with DurableInbox(work, owner_uid=uid, writer_gid=gid).exclusive() as queue:
        pending = queue.rotate()
        need(pending is not None and pending.read_bytes() == b"first.example\n",
             "DURABLE_HARDLINK_SEGMENT")
        need(pending.stat().st_ino != (work / "inbox.txt").stat().st_ino,
             "ATOMIC_REPLACEMENT")
        need(stat.S_IMODE((work / "inbox.txt").stat().st_mode) == 0o660,
             "REPLACEMENT_ENGINE_WRITE_MODE")
        need(queue.acknowledge(pending, drained=lambda *x: False,
                               committed=lambda x: True) is False,
             "PENDING_ACK_WITHOUT_FD_PROOF")
    need(pending.is_file(), "PENDING_RETAINED")
    (work / "debug.log").write_bytes(b"do not erase\n")
    _prepare(work, uid=uid, engine_gid=gid)
    need((work / "debug.log").read_bytes() == b"do not erase\n",
         "DEBUG_PRESERVED")
    (work / "foreign").touch()
    try:
        _prepare(work, uid=uid, engine_gid=gid)
    except StorageRefused:
        pass
    else:
        raise RuntimeError("P2G_FOREIGN_ENTRY_ACCEPTED")
    (work / "foreign").unlink()
    (work / "debug.log").chmod(0o666)
    try:
        _prepare(work, uid=uid, engine_gid=gid)
    except StorageRefused:
        pass
    else:
        raise RuntimeError("P2G_WORLD_WRITE_ACCEPTED")
    (work / "debug.log").chmod(0o660)
    try:
        DurableInbox(work, owner_uid=uid).exclusive().__enter__()
    except QueueSafetyError:
        pass
    else:
        raise RuntimeError("P2G_UNQUALIFIED_PRIVATE_QUEUE_ACCEPTED")
    return work


def native_nobody_access(root: Path, nobody):
    # Never switch UID in the parent; child can only open known names.
    pid = os.fork()
    if pid == 0:
        try:
            os.setgroups([])
            os.setgid(nobody.pw_gid)
            os.setuid(nobody.pw_uid)
            for name in ("inbox.txt", "debug.log"):
                fd = os.open(root / name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
                os.close(fd)
            for denied in ("pending", "worker.lock"):
                try:
                    (root / denied).open("rb")
                except OSError:
                    pass
                else:
                    os._exit(10)
            try:
                os.listdir(root)
            except OSError:
                pass
            else:
                os._exit(11)
            try:
                os.open(root / "foreign", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except OSError:
                pass
            else:
                os._exit(12)
            os._exit(0)
        except BaseException:
            os._exit(13)
    _, code = os.waitpid(pid, 0)
    need(os.WIFEXITED(code) and os.WEXITSTATUS(code) == 0,
         "NATIVE_NOBODY_CREDENTIAL_ACCESS:" + str(code))


def portable():
    uid, gid = os.geteuid(), os.getegid()
    if gid <= 0:
        print("P2G_PORTABLE=NOT_TESTED_GROUP_0")  # Native FreeBSD proves nobody.
        return
    with tempfile.TemporaryDirectory(prefix="p2g-layout-") as tmp:
        parent = Path(tmp)
        parent.chmod(0o755)
        scenario(parent, uid, gid)
    print("P2G_PORTABLE=PASS_PROTECTED_PRODUCER_AND_PENDING_NO_ACK")


def native():
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
         "NATIVE_ROOT_FREEBSD_REQUIRED")
    need(os.environ.get("GITHUB_ACTIONS") == "true"
         and os.environ.get("ZAPRET2_P2G_DISPOSABLE_NATIVE") == "1",
         "DISPOSABLE_OPT_IN_REQUIRED")
    nobody = pwd.getpwnam("nobody")
    need(nobody.pw_uid > 0 and nobody.pw_gid > 0,
         "NOBODY_ACCOUNT_UNQUALIFIED")
    need(not PRODUCER.exists() and not PRODUCER.is_symlink(),
         "PRODUCTION_ROOT_ALREADY_EXISTS")
    # FreeBSD's /var/db is root-owned and traversable by the dropped user.
    parent = PRODUCER.parent
    try:
        _prepare(PRODUCER, uid=0, engine_gid=nobody.pw_gid)
        # The original P2a owner, never this test, creates worker.lock.
        # A FreeBSD touch() here inherits nobody-group and correctly fails.
        with DurableInbox(PRODUCER, writer_gid=nobody.pw_gid).exclusive() as queue:
            need(queue.segments() == [], "NATIVE_PENDING_NOT_EMPTY")
        original = (PRODUCER / "worker.lock").lstat()
        need(original.st_uid == 0 and original.st_gid == 0 and
             original.st_nlink == 1 and stat.S_IMODE(original.st_mode) == 0o600,
             "NATIVE_ORIGINAL_QUEUE_LOCK_OWNER")
        native_nobody_access(PRODUCER, nobody)
        with DurableInbox(PRODUCER, writer_gid=nobody.pw_gid).exclusive() as queue:
            need(queue.segments() == [], "NATIVE_PENDING_NOT_EMPTY")
        need((PRODUCER / "worker.lock").lstat().st_ino == original.st_ino,
             "NATIVE_ORIGINAL_QUEUE_LOCK_REPLACED")
        print("P2G_NATIVE=PASS_FREEBSD_NOBODY_READ_APPEND_NO_CREATE_NO_PENDING")
    finally:
        # Only the explicitly created disposable root, never its parent.
        if PRODUCER.is_dir() and not PRODUCER.is_symlink():
            shutil.rmtree(PRODUCER)
        need(not PRODUCER.exists(), "NATIVE_CLEANUP_RESIDUE")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    native() if args.native else portable()
