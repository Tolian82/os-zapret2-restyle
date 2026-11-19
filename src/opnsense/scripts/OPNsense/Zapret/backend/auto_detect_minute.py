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
    _secure_bytes, attest_running_generation, attest_stopped_generation,
    attest_retiring_predecessor,
)
from auto_detect_storage import RAW_PATH, DEBUG_PATH
from auto_detect_original_lock_handoff import (
    run_native_original_v2_cycle_once, OriginalLockRefused,
)
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused
from auto_detect_original_v2_source import qualified_current_source
from auto_detect_queue import DurableInbox
from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
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



def native_retire_preflight() -> int:
    """Original FD9's last running-owner epoch proof BEFORE explicit Stop."""
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0:
        return 69
    try:
        require_lifecycle_lock()
        proof = attest_running_generation()
        import pwd
        gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if gid <= 0:
            raise MinuteRefused("invalid_original_engine_gid")
        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        with queue.exclusive():
            qualified_current_source(proof, queue)
            drifted = receipts.verify_stop_only_epoch(
                proof, queue, attest=attest_running_generation)
            if drifted:
                # Stop is an explicit operator action. Do not block stopping
                # a genuinely owned engine on ps wall-time drift. Never
                # change epoch.json or grant minute/ACK from this exception.
                print('auto-detect-retire-warning=owner-birth-clock-drift',
                      file=sys.stderr)
            if attest_running_generation() != proof:
                raise MinuteRefused("old_owner_changed_before_stop")
        print('auto-detect-retire=original-running-attested')
        return 0
    except (MinuteRefused, OriginalLockRefused, GenerationRefused,
            ReceiptRefused, OSError, ValueError, RuntimeError, KeyError) as exc:
        print('auto-detect-retire-refused=' + type(exc).__name__, file=sys.stderr)
        return 69


def native_retire_once() -> int:
    """One old-owner post-Stop Config/P1/ACK, never a cron restart gate.

    Caller must have removed the single old engine and original monitor.
    Existing immutable pretraffic/epoch + journal remain the only old-owner
    identity. No old PID is treated as a new engine or live signal target.
    """
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0:
        return 69
    try:
        require_lifecycle_lock()
        proof = attest_stopped_generation()
        if not isinstance(proof, GenerationProof):
            raise MinuteRefused('missing_old_generation_proof')
        import pwd
        gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if gid <= 0:
            raise MinuteRefused('invalid_stopped_writer_gid')
        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        # A crash AFTER the one durable retirement plan but BEFORE all
        # pathname renames must finish those renames FIRST; never run the
        # original pending preparer over a half-retired source tree.
        with queue.exclusive():
            folder, _ = receipts._epoch(proof)
            retirement_exists = ((folder / 'retired.json').exists() or
                                 (folder / 'retired.json').is_symlink())
            if retirement_exists:
                receipts.retire_stopped(proof, queue,
                                        attest=attest_stopped_generation)
                if not receipts.verify_retired(proof, queue):
                    raise MinuteRefused('old_retirement_incomplete')
                print('auto-detect-retire=idle')
                return 0
        changed = run_native_original_v2_cycle_once(retired=True)
        if type(changed) is not bool or attest_stopped_generation() != proof:
            raise MinuteRefused('old_generation_changed_during_retirement')
        if changed:
            print('auto-detect-retire=processed')
            return 0
        # Native raw is now empty, every original pending was ACKed, and
        # there are no old open cursor intents. Move the exact old inodes
        # into their existing epoch and provision only fresh empty paths.
        with queue.exclusive():
            receipts.retire_stopped(proof, queue,
                                    attest=attest_stopped_generation)
            if not receipts.verify_retired(proof, queue):
                raise MinuteRefused('old_retirement_incomplete')
        print('auto-detect-retire=idle')
        return 0
    except (MinuteRefused, OriginalLockRefused, GenerationRefused,
            ReceiptRefused, OSError, ValueError, RuntimeError, KeyError) as exc:
        print('auto-detect-retire-refused=' + type(exc).__name__, file=sys.stderr)
        return 69



def native_retired_ready() -> int:
    """Pure read-only old-epoch retirement proof before replacing ACTIVE_DIR.

    Both terminal committed and one prepared/activating *predecessor* are
    allowed, but no LIVE old or NEW engine, and no source mutation.
    """
    if not sys.platform.startswith('freebsd') or os.geteuid() != 0:
        return 69
    try:
        require_lifecycle_lock()
        previous = attest_retiring_predecessor()
        import pwd
        gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if gid <= 0:
            raise MinuteRefused('invalid_retired_engine_gid')
        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        with queue.exclusive():
            if (not receipts.verify_retired(previous, queue) or
                    attest_retiring_predecessor() != previous):
                raise MinuteRefused('old_original_retirement_not_complete')
        print('auto-detect-retire=ready')
        return 0
    except (MinuteRefused, OriginalLockRefused, GenerationRefused,
            ReceiptRefused, OSError, ValueError, RuntimeError, KeyError) as exc:
        print('auto-detect-retire-refused=' + type(exc).__name__, file=sys.stderr)
        return 69


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--pre-retire']:
        raise SystemExit(native_retire_preflight())
    if args == ['--retire-once']:
        raise SystemExit(native_retire_once())
    if args == ['--retired-ready']:
        raise SystemExit(native_retired_ready())
    raise SystemExit(native_minute_once(args))
