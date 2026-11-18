#!/usr/bin/env python3
"""Read the shared final HOSTLIST and create it for the original P2 owner."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys

from auto_detect_destination_commit import (
    DestinationRefused, _target, _sync, exclusive_destination_lock,
)

AUTO_HOSTLIST = Path('/usr/local/etc/zapret2/ipset/auto-domains.txt')
AUTO_LOCK = Path('/usr/local/etc/zapret2/ipset/.auto-domains.lock')
MAX_GUI_BYTES = 40 * 1024


class AutoHostlistRefused(ValueError):
    pass


def _revision(data: bytes | None) -> str:
    return hashlib.sha256(b'missing\0' if data is None else b'present\0' + data).hexdigest()


def _read_current(path: Path, uid: int) -> bytes | None:
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid or
            parent.st_mode & 0o022):
        raise AutoHostlistRefused('unsafe_directory')
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    # The shared destination writer also uses this nofollow/owner/link check.
    try:
        contents, _ = _target(path, uid)
    except DestinationRefused as exc:
        raise AutoHostlistRefused('unsafe_or_unreadable_file') from exc
    if len(contents) > MAX_GUI_BYTES:
        raise AutoHostlistRefused('file_exceeds_gui_transfer_limit')
    return contents


def read_current(path: Path = AUTO_HOSTLIST, lock: Path = AUTO_LOCK, *,
                 owner_uid: int = 0) -> dict:
    """Read the new final HOSTLIST without creating or modifying any file."""
    with exclusive_destination_lock(lock, owner_uid):
        data = _read_current(path, owner_uid)
        return {
            'result': 'ok',
            'status': 'missing' if data is None else ('empty' if not data else 'populated'),
            'revision': _revision(data),
            'content': '' if data is None else data.decode('utf-8'),
        }


def _create(path: Path, data: bytes, uid: int, *, stage_fn=None) -> None:
    """Write a complete temporary inode, then link-once an absent name."""
    temp = path.parent / ('.auto-hostlist-' + secrets.token_hex(16) + '.tmp')
    fd = None
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_NOFOLLOW | os.O_CREAT | os.O_EXCL, 0o600)
        os.fchmod(fd, 0o644)
        os.fchown(fd, uid, 0 if uid == 0 else os.getegid())
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise AutoHostlistRefused('short_write')
            view = view[n:]
        os.fsync(fd)
        os.close(fd)
        fd = None
        if stage_fn is not None:
            stage_fn("ready", temp, data)
        os.link(temp, path, follow_symlinks=False)
        _sync(path.parent)
    finally:
        if fd is not None:
            os.close(fd)
        if temp.exists():
            temp.unlink()
            _sync(path.parent)
    # A temporary link has been removed, so _target() can now validate
    # the single-link final inode and the same WAL pin.
    if stage_fn is not None:
        stage_fn("installed", path, data)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if (not sys.platform.startswith('freebsd') or os.geteuid() != 0 or
            argv != ['read']):
        print(json.dumps({'result': 'error', 'reason': 'native_request_refused'}))
        return 0
    try:
        result = read_current()
    except (AutoHostlistRefused, DestinationRefused, OSError, ValueError,
            UnicodeError, TypeError, KeyError) as exc:
        # Never log user domains or the contents of a failed transport.
        result = {'result': 'error', 'reason': str(exc) if isinstance(exc, AutoHostlistRefused)
                  else 'native_file_unavailable'}
    print(json.dumps(result, ensure_ascii=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())