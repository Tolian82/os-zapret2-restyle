#!/usr/bin/env python3
"""#1052 P2k8h: original-owner pre-IPFW native producer reownership.

Import-only. Only the ORIGINAL shared-FD9 owner may eventually call the native
entry after starting its ONE sealed dvtws2 process and before IPFW divert.
No start, discovery, Config write, worker, ACK, daemon or public CLI.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
from typing import Callable

from auto_detect_fd import OwnerToken, _owner_snapshot
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
    _check_layout(root, root_uid, root_gid, engine_gid)
    identities = tuple(_identity(root / name, uid=(root_uid,), gid=engine_gid)
                       for name in ("inbox.txt", "debug.log"))
    return OriginalProducer(root, root_uid, root_gid, engine_uid, engine_gid, identities)


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
    """Original FD9-only prospective call; no installed caller or CLI yet."""
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


if __name__ == "__main__":
    raise SystemExit("P2k8h is import-only; no independent startup or repair CLI")
