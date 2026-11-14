#!/usr/bin/env python3
"""#1052 P2k8m: dormant one-generation original raw → pending → P2k2a intent.

The same original P2a queue flock covers rotation and immutable intent.
This does NOT create an epoch, start an observer, choose P1 effects, commit a
destination, ACK pending or run a minute worker. The original FD9 lifecycle
must first create a genuine empty, bound debug epoch. Old generations and
second intents are retained without silent reassignment.
"""
from __future__ import annotations

import os
from pathlib import Path
import pwd
import re
import stat
import sys
from typing import Callable

from auto_detect_debug_window import (Cursor, DebugWindowRefused, MAX_RAW,
                                      propose_window)
from auto_detect_epoch_receipts import (EMPTY_HASH, EpochReceipts,
                                        ReceiptRefused)
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_owner import (GenerationProof, GenerationRefused,
                               attest_running_generation)
from auto_detect_queue import (DurableInbox, MAX_SEGMENT, QueueSafetyError,
                               _identity, _stat_regular)
from auto_detect_storage import ENGINE_USER
from auto_detect_original_lock_handoff import QUEUE_ROOT

PENDING_NAME = re.compile(r"[a-f0-9]{32}-[a-f0-9]{32}\.txt\Z")


class RotationStageRefused(RuntimeError):
    """Retain every original pending/raw byte if provenance is ambiguous."""


def _original(proof: object, queue: DurableInbox) -> GenerationProof:
    if (not isinstance(proof, GenerationProof) or
            proof.generation != proof.operation_id or
            not re.fullmatch(r"[a-f0-9]{32}", proof.generation) or
            proof.owner.pid <= 1 or
            proof.raw_path != str(queue.inbox) or
            proof.debug_path != str(queue.root / "debug.log") or
            (proof.observer_native_number, "observer", None) not in proof.profiles):
        raise RotationStageRefused("no_live_original_generation")
    return proof


def _pending_snapshot(queue: DurableInbox, path: Path) -> bytes:
    """Read ONE detached original inode only; never consume the live alias."""
    if not queue._held or path.parent != queue.pending:
        raise RotationStageRefused("original_queue_owner_required")
    before = _stat_regular(path, queue.uid, max_size=MAX_SEGMENT,
                           writer_gid=queue.writer_gid)
    if (before.st_nlink != 1 or before.st_size <= 0 or
            before.st_size > MAX_RAW or
            _identity(queue.inbox) == (before.st_dev, before.st_ino)):
        raise RotationStageRefused("pending_not_detached_or_complete")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        held = os.fstat(fd)
        data = bytearray()
        while len(data) <= MAX_SEGMENT:
            block = os.read(fd, min(65536, MAX_SEGMENT + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    current = path.lstat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns,
                          x.st_nlink, stat.S_IMODE(x.st_mode))
    if (identity(before) != identity(held) or
            identity(held) != identity(after) or
            identity(after) != identity(current) or
            len(data) != before.st_size or not data.endswith(b"\n") or
            b"\x00" in data or b"\r" in data):
        raise RotationStageRefused("incomplete_or_modified_original_pending")
    return bytes(data)


def stage_original_current_locked(
    queue: DurableInbox, receipts: EpochReceipts, *,
    attest: Callable[[], GenerationProof] = attest_running_generation,
    inspect: Callable = probe_pending_fd,
) -> Path | None:
    """Stage at most one current-generation pending under ORIGINAL queue FD.

    No creation of the trusted initial epoch here: its actual empty debug
    inode must have been installed by the original FD9 launch lifecycle
    before native recording. A previous pending ALWAYS wins over new inbox
    bytes, and an old-generation pending is an unconditional refusal.
    """
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(receipts, EpochReceipts) or
            receipts.uid != queue.uid or receipts.writer_gid != queue.writer_gid or
            not callable(attest) or not callable(inspect)):
        raise RotationStageRefused("original_locked_queue_and_epoch_required")
    try:
        proof = _original(attest(), queue)
        folder, epoch = receipts._epoch(proof)
        historical = receipts.historical(proof.generation)
        prior = historical.intent
        if (not isinstance(epoch, dict) or epoch.get("generation") != proof.generation or
                not folder.is_dir()):
            raise RotationStageRefused("untrusted_current_debug_epoch")
        pending = queue.segments()
        if (len(pending) > 1 or
                any(not PENDING_NAME.fullmatch(p.name) or
                    not p.name.startswith(proof.generation + "-") for p in pending)):
            raise RotationStageRefused("historical_or_ambiguous_pending_retained")
        if prior is not None and (not pending or
                prior.get("pending_name") != pending[0].name):
            raise RotationStageRefused("older_original_intent_requires_completion")

        if pending:
            segment = pending[0]
            live_alias = _identity(queue.inbox) == _identity(segment)
            if live_alias:
                # Crash after hardlink and before replace; P2a completes that
                # exact original inode. An old generation is never retried
                # under the current owner.
                if attest() != proof:
                    raise RotationStageRefused("owner_changed_before_recovery")
                segment = queue.rotate(generation=proof.generation)
        else:
            if prior is not None:
                raise RotationStageRefused("earlier_intent_not_recyclable")
            if attest() != proof:
                raise RotationStageRefused("owner_changed_before_rotation")
            segment = queue.rotate(generation=proof.generation)
        if segment is None:
            return None
        if attest() != proof:
            raise RotationStageRefused("owner_changed_after_rotation")
        before = segment.lstat()
        if (_identity(queue.inbox) == (before.st_dev, before.st_ino) or
                before.st_nlink != 1):
            raise RotationStageRefused("original_rotation_incomplete")
        state = inspect(segment, before.st_dev, before.st_ino,
                        owner=proof.owner, writer_gid=queue.writer_gid)
        if state is not FDState.DRAINED or attest() != proof:
            raise RotationStageRefused("original_writer_fd_not_drained")
        raw = _pending_snapshot(queue, segment)
        # Epoch and intent are immutable. The earlier cursor must remain 0;
        # at most one pending per generation is supported by this journal.
        cursor = Cursor(proof.generation, epoch["debug_device"],
                        epoch["debug_inode"], 0, EMPTY_HASH)
        window = propose_window(proof, cursor, raw, owner_uid=queue.uid,
                                writer_gid=queue.writer_gid)
        if attest() != proof:
            raise RotationStageRefused("owner_changed_before_intent")
        receipts.stage(proof, cursor, window, segment)
        # A durable intent alone does not authorize a Config commit or ACK.
        if attest() != proof or inspect(
                segment, before.st_dev, before.st_ino,
                owner=proof.owner,
                writer_gid=queue.writer_gid) is not FDState.DRAINED:
            raise RotationStageRefused("owner_or_writer_changed_after_intent")
        return segment
    except (QueueSafetyError, ReceiptRefused, DebugWindowRefused,
            GenerationRefused, OSError, ValueError, TypeError, KeyError,
            AttributeError) as exc:
        raise RotationStageRefused("original_raw_debug_epoch_unavailable") from exc


def run_native_stage_original_current_once() -> Path | None:
    """STRICT import-only native boundary: never registered as CLI/cron."""
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise RotationStageRefused("native_original_root_required")
    try:
        writer_gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if writer_gid <= 0:
            raise RotationStageRefused("native_original_writer_group_missing")
        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=writer_gid)
        receipts = EpochReceipts(owner_uid=0, writer_gid=writer_gid)
        with queue.exclusive():
            return stage_original_current_locked(queue, receipts)
    except (KeyError, OSError, QueueSafetyError, ReceiptRefused) as exc:
        raise RotationStageRefused("native_original_queue_epoch_unavailable") from exc


def main() -> None:
    raise RotationStageRefused("original_fd9_epoch_and_minute_worker_not_enabled")


if __name__ == "__main__":
    main()
