#!/usr/bin/env python3
"""Original-FD9 read-only legacy Telegram PoC gate shared by GUI preview and Apply.

The old marker presence is authoritative, *even when its contents are empty*.
A runtime enabled state can outlive the marker, including after a failed
restart. No migration, marker cleanup, process or IPFW mutation is performed.
The caller MUST already hold the original FD9 and Config inode flock.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

import voice_ipfw_runtime as native


class NativePrepareRouteError(RuntimeError):
    pass


def _legacy_read(path: Path) -> bytes | None:
    """Read one fixed legacy marker/state without following links or unsafe inode races."""
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        return None
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid()
            or before.st_nlink != 1 or before.st_mode & 0o022
            or before.st_size > 64):
        raise NativePrepareRouteError("legacy Telegram Voice marker/state is untrusted")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_NONBLOCK", 0))
    try:
        opened = os.fstat(fd)
        content = os.read(fd, 65)
        after = os.fstat(fd)
        current = os.lstat(path)
        def identity(info):
            return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
                    info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if (identity(before) != identity(opened)
                or identity(opened) != identity(after)
                or identity(after) != identity(current)
                or len(content) != before.st_size):
            raise NativePrepareRouteError("legacy Telegram Voice state changed during preflight")
        return content
    finally:
        os.close(fd)


def _require_no_legacy_poc() -> None:
    """Fail closed before staging/Apply when the transient PoC still has authority.

    The old shell PoC tests marker *presence*, not its contents. The runtime
    state can outlive the marker, including after a failed/rebooted operation.
    Do not remove either file or infer an explicit new Voice preference.
    """
    if native.ACTIVE_ROOT.is_symlink():
        raise NativePrepareRouteError("native runtime root is a symlink")
    marker = _legacy_read(native.LEGACY_MARKER)
    state = _legacy_read(native.ACTIVE_ROOT / "telegram-voice-poc.state")
    if marker is not None or state == b"enabled\n" or state == b"enabled":
        raise NativePrepareRouteError("legacy Telegram Voice PoC requires reviewed migration")
    if state is not None and state.strip() != b"disabled":
        raise NativePrepareRouteError("unknown legacy Telegram Voice runtime state")


