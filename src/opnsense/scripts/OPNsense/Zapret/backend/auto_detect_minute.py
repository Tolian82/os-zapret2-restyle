#!/usr/bin/env python3
"""#1052 P2k8j: registered but unscheduled original configd minute ingress.

No cron entry, raw reader, process restart, FD9 owner, Config writer, target
writer or ACK is enabled here. A normal pre-observer runtime is inert. Any
active/forged native observer refuses instead of silently consuming a queue.
The real one-minute cron schedule MUST be installed only together with the
qualified original generation/FD/debug/durable destination/ACK worker.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys

from auto_detect_owner import MAP_NAME, MAX_ARGS, _secure_bytes
from voice_live_inspect import COMMON_ACTIVE


class MinuteRefused(RuntimeError):
    """Do not modify/acknowledge any raw or durable pending event."""


def _entry_present(path: Path) -> bool:
    """Include dangling symlinks, which Path.exists() alone would miss."""
    return path.exists() or path.is_symlink()


def _safe_directory(path: Path, uid: int) -> None:
    try:
        parent = path.parent.lstat()
        entry = path.lstat()
    except OSError as exc:
        raise MinuteRefused('native_release_directory_unavailable') from exc
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid or
            parent.st_mode & 0o022 or not stat.S_ISDIR(entry.st_mode) or
            entry.st_uid != uid or entry.st_mode & 0o022):
        raise MinuteRefused('unsafe_original_release_directory')


def inspect_inert_release(active: Path, *, owner_uid: int) -> str:
    """Read the original release; never create a root, lock or inbox.

    This result is only permission to do NOTHING; it is not a worker owner,
    schema-2 approval or a readiness signal for native recording.
    """
    if (not isinstance(active, Path) or not active.is_absolute() or
            type(owner_uid) is not int or owner_uid < 0):
        raise MinuteRefused('invalid_original_release_reference')
    if not _entry_present(active):
        return 'inactive'
    _safe_directory(active, owner_uid)
    args = active / 'dvtws.args'
    generation = active / MAP_NAME
    if not _entry_present(args):
        if _entry_present(generation):
            raise MinuteRefused('orphan_native_generation')
        return 'inactive'
    try:
        raw = _secure_bytes(args, MAX_ARGS, owner_uid)
        tokens = raw.decode('utf-8').split()
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        raise MinuteRefused('untrusted_original_native_argv') from exc
    if not tokens or not tokens[0].startswith('--port=') or '\x00' in raw.decode('utf-8'):
        raise MinuteRefused('invalid_original_native_argv')
    # A trailing raw/debug observer or any unknown native-auto knob is NOT
    # authorized by the existence of argv, a JSON file or a cron request.
    # Strictly reject before an attempt to rotate/access raw or pending.
    if any(token.startswith('--hostlist-auto') for token in tokens):
        raise MinuteRefused('native_observer_worker_ack_not_authorized')
    if _entry_present(generation):
        raise MinuteRefused('unexpected_native_generation_without_observer')
    return 'inactive'


def native_minute_once(args: list[str]) -> int:
    """The only exposed configd entry, never an ad-hoc standalone worker."""
    if args:
        return 64
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0:
        print('auto-detect-minute-refused=native-root-only', file=sys.stderr)
        return 69
    try:
        state = inspect_inert_release(COMMON_ACTIVE, owner_uid=0)
        if state != 'inactive':
            raise MinuteRefused('unqualified_worker_state')
    except (MinuteRefused, OSError, ValueError, TypeError) as exc:
        # Do not print any native argv, domain, private inode, path or Config.
        print('auto-detect-minute-refused=' + type(exc).__name__, file=sys.stderr)
        return 69
    print('auto-detect-minute=inactive')
    return 0


if __name__ == '__main__':
    raise SystemExit(native_minute_once(sys.argv[1:]))
