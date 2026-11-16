#!/usr/bin/env python3
"""#1052 P2: protected native raw/debug producer layout, not a collector.

Only the existing original shared-FD9 launch path invokes prepare_native()
before the ONE native engine starts; the existing post-drop worker verifies
its exact original inodes. The unprivileged engine may open the two files
but may not create/unlink root-owned queue entries or access pending.
No reset, Config mutation, alternate daemon or second worker is permitted.
"""
from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import sys

ROOT = Path("/var/db/zapret2-auto-detect")
RAW_PATH = ROOT / "inbox.txt"
DEBUG_PATH = ROOT / "debug.log"
ROOT_MODE = 0o710
FILE_MODE = 0o660
PENDING_MODE = 0o700
ENGINE_USER = "nobody"


class StorageRefused(RuntimeError):
    """A missing, unsafe or partially provisioned producer layout."""


def _secure(path: Path, *, directory: bool, uid: int, gid: int,
            mode: int, links: int | None = None) -> os.stat_result:
    info = path.lstat()
    correct = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (not correct or info.st_uid != uid or info.st_gid != gid
            or stat.S_IMODE(info.st_mode) != mode
            or (links is not None and info.st_nlink != links)):
        raise StorageRefused("unsafe_native_producer_artifact")
    return info


def _sync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW |
                 getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _parent(root: Path, uid: int) -> None:
    info = root.parent.lstat()
    # Traversable but never writable by the dropped engine or other users.
    # This MUST NOT be the original private /var/db/zapret2 parent (0700).
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid
            or info.st_mode & 0o022 or not info.st_mode & 0o001):
        raise StorageRefused("producer_parent_not_safe_and_traversable")


def _entry(root: Path, name: str, *, directory: bool, uid: int,
           gid: int, mode: int) -> None:
    path = root / name
    try:
        if directory:
            path.mkdir(mode=0o700)
        else:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                         os.O_NOFOLLOW, 0o600)
            try:
                os.fchown(fd, uid, gid)
                os.fchmod(fd, mode)
                os.fsync(fd)
            finally:
                os.close(fd)
    except FileExistsError:
        pass  # Never repair an untrusted existing object by chmod/chown.
    else:
        if directory:
            os.chown(path, uid, gid, follow_symlinks=False)
            path.chmod(mode)
        _sync(root)
    _secure(path, directory=directory, uid=uid, gid=gid, mode=mode,
            links=None if directory else 1)


def _prepare(root: Path, *, uid: int, engine_gid: int) -> None:
    """Internal testable primitive. The only production root is ROOT."""
    if (root == root.parent or not root.is_absolute()
            or not isinstance(engine_gid, int) or engine_gid < 0):
        raise StorageRefused("invalid_producer_location_or_group")
    _parent(root, uid)
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        pass
    else:
        # A newly created 0700 directory must get the engine's group before
        # granting group execute; no broad directory listing or group write.
        os.chown(root, uid, engine_gid, follow_symlinks=False)
        root.chmod(ROOT_MODE)
        _sync(root.parent)
    _secure(root, directory=True, uid=uid, gid=engine_gid, mode=ROOT_MODE)
    _entry(root, "pending", directory=True, uid=uid,
           gid=uid, mode=PENDING_MODE)
    for name in ("inbox.txt", "debug.log"):
        _entry(root, name, directory=False, uid=uid,
               gid=engine_gid, mode=FILE_MODE)
    # Unknown objects are preserved, but never silently accepted.
    # pending contents are owned by the future durable queue.
    allowed = {"pending", "inbox.txt", "debug.log", "worker.lock"}
    if set(os.listdir(root)) - allowed:
        raise StorageRefused("foreign_native_producer_entry")
    lock = root / "worker.lock"
    if lock.exists() or lock.is_symlink():
        _secure(lock, directory=False, uid=uid, gid=uid,
                mode=0o600, links=1)
    _sync(root)


def prepare_native() -> None:
    """Original-FD9 launcher-only primitive, never a standalone CLI."""
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise StorageRefused("native_root_freebsd_only")
    # NEVER use the generic nobody account as a separate process owner.
    # This group is only for existing dvtws2 open(2) access to exact files.
    identity = pwd.getpwnam(ENGINE_USER)
    if identity.pw_gid <= 0:
        raise StorageRefused("native_engine_group_unqualified")
    _prepare(ROOT, uid=0, engine_gid=identity.pw_gid)


def main() -> None:
    raise SystemExit("P2g is an import-only storage primitive; no native CLI enabled")


if __name__ == "__main__":
    main()
