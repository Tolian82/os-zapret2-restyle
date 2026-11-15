#!/usr/bin/env python3
"""#1052: one short original configd minute, using the existing P2a/P2k8p owner.

Ordinary release: inert. Qualified native schema-2 RUNNING generation:
one original queue -> locked OPNsense Config/P1 -> durable v2 checkpoint/ACK.
Neither this entry nor its source tests install cron or launch/stop dvtws2.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys

from auto_detect_owner import (
    MAP_NAME, MAX_ARGS, GenerationProof, GenerationRefused,
    _secure_bytes, attest_running_generation,
)
from auto_detect_storage import RAW_PATH, DEBUG_PATH
from auto_detect_original_lock_handoff import (
    run_native_original_v2_cycle_once, OriginalLockRefused,
)
from voice_live_inspect import COMMON_ACTIVE
from voice_ipfw_adapter import require_lifecycle_lock


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
    # A native auto argv is NOT a sufficient authority. Callers must next
    # obtain a real terminal original P2c owner and the same P2a/Config path.
    # This inspector is deliberately *only* the unchanged inert classifier.
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
        # No native queue, Config/P1 or engine process evidence may be
        # accessed by configd outside the sole original held FD9. The
        # service wrapper owns it; no second lock is taken here.
        require_lifecycle_lock()
        # Reuse the original P2k8j read-only refusal for malformed release,
        # dangling generation, foreign auto knob and normal inactive start.
        try:
            state = inspect_inert_release(COMMON_ACTIVE, owner_uid=0)
        except MinuteRefused as exc:
            if str(exc) != 'native_observer_worker_ack_not_authorized':
                raise
            # Only the canonical committed shared owner and exact running
            # native argv can turn the refusal into a qualified worker.
            # A forged map, a stale process, and preview-only generation
            # all fail BEFORE P2a queue/Config/target access.
            proof = attest_running_generation()
            if (not isinstance(proof, GenerationProof) or
                    proof.operation_id != proof.generation or
                    proof.raw_path != str(RAW_PATH) or
                    proof.debug_path != str(DEBUG_PATH) or
                    proof.owner.pid <= 1):
                raise MinuteRefused('unqualified_original_running_generation')
            # This is the already established ONE queue -> PHP Config-held
            # model/P1 -> v2 checkpoint -> durable P2a ACK. No alternative
            # parser, Config writer, worker, delay or process action.
            changed = run_native_original_v2_cycle_once()
            if type(changed) is not bool:
                raise MinuteRefused('original_v2_completion_not_boolean')
            print('auto-detect-minute=' + ('processed' if changed else 'idle'))
            return 0
        if state != 'inactive':
            raise MinuteRefused('unqualified_worker_state')
    except (MinuteRefused, OriginalLockRefused, GenerationRefused,
            OSError, ValueError, TypeError, RuntimeError) as exc:
        # No private argv/Config/hostname/FD gets logged. Fail closed:
        # the original pending and queue are left to their durable owner.
        print('auto-detect-minute-refused=' + type(exc).__name__, file=sys.stderr)
        return 69
    print('auto-detect-minute=inactive')
    return 0


if __name__ == '__main__':
    raise SystemExit(native_minute_once(sys.argv[1:]))
