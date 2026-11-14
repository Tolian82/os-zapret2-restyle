#!/usr/bin/env python3
"""#1052 P2k8h: original-owner pre-IPFW native producer reownership.

Import-only. Only the ORIGINAL shared-FD9 owner may eventually call the native
entry after starting its ONE sealed dvtws2 process and before IPFW divert.
No start, discovery, Config write, worker, ACK, daemon or public CLI.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from pathlib import Path
import pwd
import stat
import subprocess
import sys
from typing import Callable

from auto_detect_fd import OwnerToken, _owner_snapshot
from auto_detect_debug_window import _read_exact, DebugWindowRefused
from auto_detect_queue import DurableInbox, QueueSafetyError
from auto_detect_storage import (
    ROOT, RAW_PATH, DEBUG_PATH, ENGINE_USER,
    ROOT_MODE, FILE_MODE, PENDING_MODE, _parent,
)

class PostDropRefused(RuntimeError):
    """A changed original inode/process prevents IPFW activation."""


@dataclass(frozen=True)
class OriginalProducer:
    root: Path
    root_uid: int
    root_gid: int
    engine_uid: int
    engine_gid: int
    # One ordered identity per actual original producer file, never raw data.
    identities: tuple[tuple[int, int, int], tuple[int, int, int]]


def _check_layout(root: Path, root_uid: int, root_gid: int, engine_gid: int) -> None:
    try:
        info = root.lstat()
        pending = (root / "pending").lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != root_uid or
                info.st_gid != engine_gid or
                stat.S_IMODE(info.st_mode) != ROOT_MODE or
                not stat.S_ISDIR(pending.st_mode) or pending.st_uid != root_uid or
                pending.st_gid != root_gid or
                stat.S_IMODE(pending.st_mode) != PENDING_MODE or
                set(os.listdir(root)) - {"pending", "inbox.txt", "debug.log", "worker.lock"}):
            raise PostDropRefused("unsafe_original_producer_layout")
        lock = root / "worker.lock"
        if lock.exists() or lock.is_symlink():
            st = lock.lstat()
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != root_uid or
                    st.st_gid != root_gid or st.st_nlink != 1 or
                    stat.S_IMODE(st.st_mode) != 0o600):
                raise PostDropRefused("unsafe_original_producer_lock")
    except (OSError, ValueError) as exc:
        raise PostDropRefused("original_producer_layout_unavailable") from exc


def _identity(path: Path, *, uid: tuple[int, ...], gid: int,
              expected: tuple[int, int, int] | None = None) -> tuple[int, int, int]:
    try:
        entry = path.lstat()
    except OSError as exc:
        raise PostDropRefused("original_producer_entry_unavailable") from exc
    inode = (entry.st_dev, entry.st_ino, entry.st_nlink)
    if (not stat.S_ISREG(entry.st_mode) or entry.st_nlink != 1 or
            stat.S_IMODE(entry.st_mode) != FILE_MODE or
            entry.st_uid not in uid or entry.st_gid != gid or
            (expected is not None and inode != expected)):
        raise PostDropRefused("original_producer_inode_drift")
    return inode


def _capture(root: Path, *, root_uid: int, root_gid: int, engine_uid: int,
             engine_gid: int) -> OriginalProducer:
    """Testable scoped precursor. Does not change either producer file."""
    if (not isinstance(root, Path) or not root.is_absolute() or
            type(root_uid) is not int or root_uid < 0 or
            type(root_gid) is not int or root_gid < 0 or
            type(engine_uid) is not int or engine_uid <= 0 or
            type(engine_gid) is not int or engine_gid <= 0 or
            root_uid == engine_uid):
        raise PostDropRefused("unqualified_original_producer_identity")
    # The original P2a queue flock is the ONLY serialization owner for
    # prelaunch raw/old-inode state. The FD9 caller retains its independent
    # common Apply lock; this short nested P2a lock is not a new worker.
    # Neither a nonempty prior native debug history nor foreign-generation
    # pending may be inherited by a new original shared-FD9 observer.
    try:
        _check_layout(root, root_uid, root_gid, engine_gid)
        queue = DurableInbox(root, owner_uid=root_uid, writer_gid=engine_gid)
        with queue.exclusive():
            _check_layout(root, root_uid, root_gid, engine_gid)
            if queue.segments():
                raise PostDropRefused("unprocessed_original_pending_prelaunch")
            identities = []
            for name in ("inbox.txt", "debug.log"):
                path = root / name
                stat_before, bytes_before = _read_exact(
                    path, owner_uid=root_uid, writer_gid=engine_gid)
                identity = _identity(path, uid=(root_uid,), gid=engine_gid)
                if bytes_before or stat_before.st_size or identity != (
                        stat_before.st_dev, stat_before.st_ino, stat_before.st_nlink):
                    raise PostDropRefused("nonempty_or_changed_original_pretraffic_inode")
                identities.append(identity)
            if identities[0][:2] == identities[1][:2]:
                raise PostDropRefused("aliased_original_raw_and_debug")
            _check_layout(root, root_uid, root_gid, engine_gid)
            return OriginalProducer(root, root_uid, root_gid,
                                    engine_uid, engine_gid, tuple(identities))
    except (QueueSafetyError, DebugWindowRefused, OSError) as exc:
        raise PostDropRefused("original_pretraffic_queue_or_inode_unavailable") from exc


def _reattest(witness: OriginalProducer, owner_alive: Callable[[], bool]) -> tuple[str, ...]:
    """Repair only original *open inodes* after real engine credential drop.

    Both paths are verified before the first fchown, so an unsafe debug file
    cannot cause a partial 'successful' repair of the raw inbox. FDs use
    O_NOFOLLOW and are never created/replaced. Abort before IPFW on any drift.
    """
    if not isinstance(witness, OriginalProducer) or not callable(owner_alive):
        raise PostDropRefused("missing_original_fd9_witness")
    root = witness.root
    _check_layout(root, witness.root_uid, witness.root_gid, witness.engine_gid)
    paths = (root / "inbox.txt", root / "debug.log")
    for path, prior in zip(paths, witness.identities):
        _identity(path, uid=(witness.root_uid, witness.engine_uid),
                  gid=witness.engine_gid, expected=prior)
    if owner_alive() is not True:
        raise PostDropRefused("original_engine_owner_changed")
    changed = []
    for path, prior in zip(paths, witness.identities):
        if owner_alive() is not True:
            raise PostDropRefused("original_engine_owner_changed")
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as exc:
            raise PostDropRefused("original_producer_fd_unavailable") from exc
        try:
            before = os.fstat(fd)
            if ((before.st_dev, before.st_ino, before.st_nlink) != prior or
                    not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                    stat.S_IMODE(before.st_mode) != FILE_MODE or
                    before.st_gid != witness.engine_gid or
                    before.st_uid not in (witness.root_uid, witness.engine_uid)):
                raise PostDropRefused("original_producer_open_inode_drift")
            # Upstream dvtws2 --user=nobody may chown its hostlist on startup.
            # Repair the very same open inode, never pathname-following chown.
            if before.st_uid == witness.engine_uid:
                os.fchown(fd, witness.root_uid, witness.engine_gid)
                changed.append(path.name)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_nlink) != prior or
                    after.st_uid != witness.root_uid or
                    after.st_gid != witness.engine_gid or
                    stat.S_IMODE(after.st_mode) != FILE_MODE):
                raise PostDropRefused("original_producer_reownership_failed")
        except OSError as exc:
            raise PostDropRefused("original_producer_reownership_failed") from exc
        finally:
            os.close(fd)
        _identity(path, uid=(witness.root_uid,), gid=witness.engine_gid,
                  expected=prior)
    _check_layout(root, witness.root_uid, witness.root_gid, witness.engine_gid)
    for path, prior in zip(paths, witness.identities):
        _identity(path, uid=(witness.root_uid,), gid=witness.engine_gid,
                  expected=prior)
    if owner_alive() is not True:
        raise PostDropRefused("original_engine_owner_changed")
    return tuple(changed)


def native_capture_before_launch() -> OriginalProducer:
    """Original FD9-only pretraffic proof; live producer still disabled."""
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise PostDropRefused("native_root_fd9_only")
    try:
        nobody = pwd.getpwnam(ENGINE_USER)
        if nobody.pw_uid <= 0 or nobody.pw_gid <= 0:
            raise PostDropRefused("unqualified_original_engine_user")
        _parent(ROOT, 0)
        return _capture(ROOT, root_uid=0, root_gid=0, engine_uid=nobody.pw_uid,
                        engine_gid=nobody.pw_gid)
    except (OSError, KeyError, ValueError) as exc:
        raise PostDropRefused("original_producer_native_identity_unavailable") from exc


def native_restore_before_ipfw(witness: OriginalProducer, owner: OwnerToken,
                               *, runner=subprocess.run) -> tuple[str, ...]:
    """Original FD9-only post-drop call. Requires exact original PID/birth/exe.

    Passing an arbitrary alive=True flag cannot invoke the native entry.
    Never call outside the original single-process shared Apply under FD9.
    """
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(owner, OwnerToken) or not isinstance(witness, OriginalProducer) or
            witness.root != ROOT or witness.root_uid != 0 or witness.root_gid != 0 or
            not owner.executable.startswith("/") or owner.pid <= 1):
        raise PostDropRefused("native_original_fd9_owner_required")
    try:
        return _reattest(witness, lambda: _owner_snapshot(owner, runner))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise PostDropRefused("native_original_process_unavailable") from exc


# P2k8q3a: route the sole original FD9 through the existing immutable
# pretraffic -> committed process epoch. These commands are not authorizers:
# normal original Apply still refuses active native recording until the
# existing worker/FD/rollover gates are qualified.
def _original_epoch_queue():
    from auto_detect_epoch_receipts import EpochReceipts
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise PostDropRefused("native_root_fd9_epoch_only")
    _parent(ROOT, 0)
    native_user = pwd.getpwnam(ENGINE_USER)
    if native_user.pw_uid <= 0 or native_user.pw_gid <= 0:
        raise PostDropRefused("unqualified_original_epoch_engine")
    _check_layout(ROOT, 0, 0, native_user.pw_gid)
    return (DurableInbox(ROOT, owner_uid=0, writer_gid=native_user.pw_gid),
            EpochReceipts(writer_gid=native_user.pw_gid))


def native_seal_original_epoch(generation: str, candidate: str) -> None:
    from auto_detect_epoch_receipts import HEX32, HEX64
    from shared_apply_seal import WORK
    if (not isinstance(generation, str) or not HEX32.fullmatch(generation)
            or not isinstance(candidate, str) or not HEX64.fullmatch(candidate)):
        raise PostDropRefused("invalid_original_epoch_candidate")
    queue, receipts = _original_epoch_queue()
    with queue.exclusive():
        receipts.seal_pretraffic(
            queue, workspace=WORK / generation, candidate_sha256=candidate)


def native_finish_original_epoch(generation: str) -> None:
    from auto_detect_epoch_receipts import HEX32
    from auto_detect_owner import attest_running_generation
    if not isinstance(generation, str) or not HEX32.fullmatch(generation):
        raise PostDropRefused("invalid_original_epoch_generation")
    # P2c requires the ORIGINAL terminal common journal, live supervisor,
    # matching active+sealed argv/map and exact PID/birth. Do not call this
    # before native Config save and the terminal shared Apply record.
    proof = attest_running_generation()
    if proof.generation != generation or proof.operation_id != generation:
        raise PostDropRefused("completed_original_owner_differs")
    queue, receipts = _original_epoch_queue()
    with queue.exclusive():
        receipts.finish_running(proof, queue)


# P2k8i: the two half-calls are a *single* original-FD9 shell operation.
# No new lock, Config parser, queue owner or on-disk witness is introduced.
# The compact witness crosses launcher_start_once as an exact positional
# argument, never through a detached daemon or a public worker.
_WITNESS = re.compile(r"^p2k8i:([0-9]+):([0-9]+):([0-9]+):([0-9]+):([0-9]+):([0-9]+)$")


def _witness_line(witness: OriginalProducer) -> str:
    a, b = witness.identities
    return "p2k8i:" + ":".join(str(v) for v in (*a, *b))


def _witness_read(line: str) -> OriginalProducer:
    if not isinstance(line, str) or len(line) > 192:
        raise PostDropRefused("invalid_original_fd9_prelaunch_witness")
    found = _WITNESS.fullmatch(line)
    if found is None:
        raise PostDropRefused("invalid_original_fd9_prelaunch_witness")
    values = tuple(int(x) for x in found.groups())
    if any(n > (1 << 64) - 1 for n in values) or values[2] != 1 or values[5] != 1:
        raise PostDropRefused("invalid_original_fd9_prelaunch_witness")
    # Do not call native_capture_before_launch() again here: the verified
    # upstream credential drop legitimately chowns inbox.txt to nobody.
    # _reattest() immediately checks both protected named/open inodes against
    # this original prelaunch witness and rejects every other UID.
    _parent(ROOT, 0)
    native_user = pwd.getpwnam(ENGINE_USER)
    if native_user.pw_uid <= 0 or native_user.pw_gid <= 0:
        raise PostDropRefused("unqualified_original_engine_user")
    return OriginalProducer(
        ROOT, 0, 0, native_user.pw_uid, native_user.pw_gid,
        (values[:3], values[3:]),
    )


def _original_owner_from_pid(pid_text: str, executable: str) -> OwnerToken:
    if (not isinstance(pid_text, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", pid_text)
            or not isinstance(executable, str) or not executable.startswith("/")
            or not executable.endswith("/dvtws2") or "\x00" in executable or
            any(c.isspace() for c in executable)):
        raise PostDropRefused("invalid_original_launcher_identity")
    pid = int(pid_text)
    try:
        reply = subprocess.run(
            ["/bin/ps", "-ww", "-p", str(pid), "-o", "lstart=", "-o", "command="],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PostDropRefused("original_launcher_process_unavailable") from exc
    if reply.returncode or reply.stderr or len(reply.stdout) > 131072:
        raise PostDropRefused("original_launcher_process_unavailable")
    lines = reply.stdout.strip().splitlines()
    if len(lines) != 1:
        raise PostDropRefused("original_launcher_process_unavailable")
    fields = lines[0].split(maxsplit=5)
    if len(fields) != 6:
        raise PostDropRefused("original_launcher_process_unavailable")
    started = " ".join(fields[:5])
    token = OwnerToken(pid, started, executable)
    if not _owner_snapshot(token, subprocess.run):
        raise PostDropRefused("original_launcher_owner_changed")
    return token


def original_fd9_command(args: list[str]) -> int:
    """Restricted internal CLI, only from inherited original held FD9.

    A normal release with P2h's inert preview never invokes this command.
    Activation is deliberately a separate original-builder/worker gate.
    """
    shapes = {"capture": 1, "restore": 4, "seal-epoch": 3,
              "finish-epoch": 2}
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not args or len(args) != shapes.get(args[0], -1)):
        return 64
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()  # REAL original same-OFD held FD9, no new lock.
        if args[0] == "capture":
            print(_witness_line(native_capture_before_launch()))
        elif args[0] == "restore":
            # Caller already started the single original engine. A false
            # witness, missing original FD9 or replaced process refuses.
            witness = _witness_read(args[1])
            owner = _original_owner_from_pid(args[2], args[3])
            native_restore_before_ipfw(witness, owner)
            print("original-fd9-postdrop=attested")
        elif args[0] == "seal-epoch":
            native_seal_original_epoch(args[1], args[2])
            print("original-fd9-pretraffic=sealed")
        else:
            native_finish_original_epoch(args[1])
            print("original-fd9-running-epoch=attested")
        return 0
    except Exception as exc:
        # Catch the original FD9 adapter's refusal as well as process errors.
        # Do not print a traceback, raw argv or any private Config/hostlist.
        # No raw domain, process argv or private witness leaks in diagnostics.
        print("original-fd9-postdrop-refused=" + type(exc).__name__,
              file=sys.stderr)
        return 69


if __name__ == "__main__":
    raise SystemExit(original_fd9_command(sys.argv[1:]))
