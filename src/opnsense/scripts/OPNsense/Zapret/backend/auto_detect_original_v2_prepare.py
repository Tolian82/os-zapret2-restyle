#!/usr/bin/env python3
"""#1052 P2k8o: inert original P2a raw rotation -> P2k8n v2 intent.

This is a *current-generation-only* import helper, not a minute worker.
One ORIGINAL queue flock protects preflight, original crash recovery or
rotation, real P2b FD drain, P2k1 debug pairing and durable v2 prepare.
No Config/FD9 child, destination writes, ACK, cron or old-owner migration.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Callable

from auto_detect_debug_window import _read_exact, DebugWindowRefused, MAX_WINDOW, MAX_DEBUG
from auto_detect_cursor_chain import (ChainTip, CursorChain, CursorChainRefused,
                                      MAX_STEPS, PENDING)
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_v2_source import (qualified_current_source, OriginalSourceRefused)
from auto_detect_owner import (GenerationProof, GenerationRefused,
                               attest_running_generation)
from auto_detect_queue import (DurableInbox, QueueSafetyError, MAX_SEGMENT, _stat_regular,
                               _sync_directory)


class OriginalV2PrepareRefused(RuntimeError):
    """Do not rotate or discard another generation's original raw segment."""


# Conservative high-water cuts; one ACK-proven original archive can retire.
# The new retained inode cannot itself retire without a matching durable
# cursor anchor. This is NOT an unbounded debug/journal rollover.
DEBUG_HIGH_WATERMARK = MAX_DEBUG // 2
DEBUG_NEXT = ".original-debug-prepared"
DEBUG_OLD = ".original-debug-retained"


def _retire_debug_archive_once(queue: DurableInbox, receipts: EpochReceipts,
                               proof: GenerationProof, tip: ChainTip,
                               current: os.stat_result, archived: os.stat_result,
                               old_path: Path, attest: Callable,
                               inspect_debug: Callable) -> None:
    """Retire only an ACK-proven first-cut debug inode; raw remains truth."""
    if (tip.open_folder is not None or tip.open_intent is not None or
            not tip.raw_first or tip.next_sequence < 1 or
            (tip.cursor.device, tip.cursor.inode) !=
            (archived.st_dev, archived.st_ino)):
        raise OriginalV2PrepareRefused("retained_debug_ack_not_proven")
    if queue.segments():
        raise OriginalV2PrepareRefused("retained_debug_pending_unacknowledged")
    live_raw = _stat_regular(queue.inbox, receipts.uid,
                             max_size=MAX_SEGMENT, writer_gid=queue.writer_gid)
    if live_raw.st_nlink != 1 or live_raw.st_size != 0:
        raise OriginalV2PrepareRefused("retained_debug_live_raw_unprocessed")
    old_stat, old_bytes = _read_exact(
        old_path, owner_uid=receipts.uid, writer_gid=queue.writer_gid)
    if ((old_stat.st_dev, old_stat.st_ino) !=
            (archived.st_dev, archived.st_ino) or
            tip.cursor.offset > len(old_bytes) or
            hashlib.sha256(old_bytes[:tip.cursor.offset]).hexdigest() !=
            tip.cursor.prefix_sha256 or
            b"\x00" in old_bytes or
            (old_bytes and not old_bytes.endswith(b"\n"))):
        raise OriginalV2PrepareRefused("retained_debug_cursor_or_content_changed")
    if (inspect_debug(old_path, old_stat.st_dev, old_stat.st_ino,
                      owner=proof.owner, writer_gid=queue.writer_gid)
            is not FDState.DRAINED or attest() != proof):
        raise OriginalV2PrepareRefused("retained_debug_writer_fd_not_drained")
    # The native producer does not hold this flock. Refuse any observed
    # change instead of discarding an unprocessed historical event.
    now_old = old_path.lstat()
    now_raw = queue.inbox.lstat()
    now_live = Path(proof.debug_path).lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size,
                          s.st_mtime_ns, s.st_nlink)
    if (identity(now_old) != identity(old_stat) or
            identity(now_raw) != identity(live_raw) or
            identity(now_live) != identity(current) or
            attest() != proof):
        raise OriginalV2PrepareRefused("retained_debug_changed_before_retirement")
    old_path.unlink()
    _sync_directory(queue.root)


def _debug_cut_once(queue: DurableInbox, receipts: EpochReceipts,
                    proof: GenerationProof, cursor, raw_first: bool,
                    attest: Callable, inspect_debug: Callable, *,
                    retirement_tip: ChainTip | None = None) -> bool:
    """Original P2a-lock debug cut; never pause the native engine.

    The already sealed original FD9/P2c owner and all-PID P2b FD inspector
    are required on both sides. A torn prepared inode or two-link alias
    is safely rolled back without dropping ANY original debug bytes.
    One old inode retires only after same-cursor original raw-first ACK,
    empty pending/live raw, all-PID drained FD and exact owner recheck.
    A newer unanchored archive remains protected; no arbitrary pruning.
    """
    if not queue._held:
        raise OriginalV2PrepareRefused("original_debug_cut_queue_lock_required")
    live = Path(proof.debug_path)
    if live != queue.root / "debug.log":
        raise OriginalV2PrepareRefused("original_debug_cut_path_changed")
    old_path, fresh_path = queue.root / DEBUG_OLD, queue.root / DEBUG_NEXT
    uid, gid = receipts.uid, queue.writer_gid
    mode = 0o660 if gid is not None else 0o600
    # Recover exactly the torn state after hardlink/dir-fsync but before
    # atomic replace. The live inode still has TWO names and every byte:
    # unlink only its EXTRA original alias; never truncate/swap it here.
    # _read_exact requires a single link, so inspect these two names first.
    live_stat = _stat_regular(live, uid, max_size=MAX_DEBUG, writer_gid=gid)
    # The normal original P2a stage already checked owner before calling
    # this optional helper. When safely BELOW high-water with no unfinished
    # cut, do NOT introduce an additional owner snapshot before raw rotate:
    # it would change the established original after-rotation FD9/P2c
    # TOCTOU gate and falsely reject its precise historical regression.
    # Any actual cut/recovery still requires its OWN new owner proof.
    needs_cut_or_recovery = (
        live_stat.st_nlink != 1 or
        live_stat.st_size >= DEBUG_HIGH_WATERMARK or
        old_path.exists() or old_path.is_symlink() or
        fresh_path.exists() or fresh_path.is_symlink()
    )
    if needs_cut_or_recovery and attest() != proof:
        raise OriginalV2PrepareRefused("original_debug_cut_owner_required")
    if live_stat.st_nlink != 1:
        alias = _stat_regular(old_path, uid, max_size=MAX_DEBUG,
                              writer_gid=gid)
        if (live_stat.st_nlink != 2 or alias.st_nlink != 2 or
                (live_stat.st_dev, live_stat.st_ino) !=
                (alias.st_dev, alias.st_ino)):
            raise OriginalV2PrepareRefused("original_debug_live_links_not_one")
        if fresh_path.exists() or fresh_path.is_symlink():
            prepared = _stat_regular(fresh_path, uid, max_size=0,
                                     writer_gid=gid)
            if (prepared.st_dev != live_stat.st_dev or
                    prepared.st_nlink != 1 or
                    stat.S_IMODE(prepared.st_mode) != mode):
                raise OriginalV2PrepareRefused("unsafe_torn_original_debug_temp")
            fresh_path.unlink()
        old_path.unlink()
        _sync_directory(queue.root)
    current, _ = _read_exact(live, owner_uid=uid, writer_gid=gid)

    # Crash between preparing an empty inode and linking the old debug.
    # The new inode was never published; only remove that exact safe temp.
    if (fresh_path.exists() or fresh_path.is_symlink()) and not (
            old_path.exists() or old_path.is_symlink()):
        fresh = _stat_regular(fresh_path, uid, max_size=0, writer_gid=gid)
        if (fresh.st_nlink != 1 or stat.S_IMODE(fresh.st_mode) != mode or
                fresh.st_dev != current.st_dev):
            raise OriginalV2PrepareRefused("unsafe_prepared_original_debug")
        fresh_path.unlink()
        _sync_directory(queue.root)

    if old_path.exists() or old_path.is_symlink():
        archived = _stat_regular(old_path, uid, max_size=MAX_DEBUG,
                                 writer_gid=gid)
        if archived.st_dev != current.st_dev:
            raise OriginalV2PrepareRefused("foreign_retained_debug_device")
        if archived.st_ino != current.st_ino:
            if archived.st_nlink != 1 or (
                    fresh_path.exists() or fresh_path.is_symlink()):
                raise OriginalV2PrepareRefused("unsafe_completed_debug_cut")
            if (inspect_debug(old_path, archived.st_dev, archived.st_ino,
                              owner=proof.owner, writer_gid=gid)
                    is not FDState.DRAINED or attest() != proof):
                raise OriginalV2PrepareRefused("retained_debug_writer_fd_not_drained")
            if current.st_size < DEBUG_HIGH_WATERMARK:
                return False
            if (not isinstance(retirement_tip, ChainTip) or
                    retirement_tip.cursor != cursor or
                    retirement_tip.raw_first != raw_first):
                raise OriginalV2PrepareRefused("second_debug_cut_needs_retirement")
            _retire_debug_archive_once(
                queue, receipts, proof, retirement_tip, current, archived,
                old_path, attest, inspect_debug)
            # The archived inode was unlink-safe only because the original
            # v2 checkpoint/ACK chain already processed its raw discoveries.
            # Continue with the SAME protected live inode below and create
            # a second retained alias atomically, without any engine signal.
        else:
            # An archived hardlink to the SAME live inode would have nlink=2,
            # which the initial torn-alias recovery handles. If the kernel
            # observation contradicts it, never infer a completed cut.
            raise OriginalV2PrepareRefused("unqualified_same_inode_debug_archive")
    if current.st_size < DEBUG_HIGH_WATERMARK:
        return False
    # Do not hide a corrupted original SAME-inode native prefix by cutting
    # to a new filename and switching to raw-first without inspection.
    _require_debug_window_before_raw_cut(
        proof, cursor, receipts, raw_first=raw_first)
    if (inspect_debug(live, current.st_dev, current.st_ino,
                      owner=proof.owner, writer_gid=gid)
            is not FDState.DRAINED or attest() != proof):
        raise OriginalV2PrepareRefused("original_debug_old_fd_not_drained")

    fd = os.open(fresh_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW, mode)
    try:
        os.fchown(fd, uid, gid if gid is not None else current.st_gid)
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)
    _sync_directory(queue.root)
    # The native producer does NOT hold P2a's root-only flock. Recheck the
    # exact old inode, SHA/size/mtime before hardlink/replace; never silently
    # pretend that a changed debug was a clean cut.
    before, old_bytes = _read_exact(live, owner_uid=uid, writer_gid=gid)
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
            (current.st_dev, current.st_ino, current.st_size,
             current.st_mtime_ns) or attest() != proof):
        raise OriginalV2PrepareRefused("original_debug_changed_before_cut")
    os.link(live, old_path, follow_symlinks=False)
    linked = old_path.lstat()
    if ((linked.st_dev, linked.st_ino, linked.st_size,
         linked.st_mtime_ns, linked.st_nlink) !=
            (before.st_dev, before.st_ino, len(old_bytes),
             before.st_mtime_ns, 2)):
        raise OriginalV2PrepareRefused("original_debug_link_modified")
    _sync_directory(queue.root)
    os.replace(fresh_path, live)
    _sync_directory(queue.root)
    retained = _stat_regular(old_path, uid, max_size=MAX_DEBUG,
                             writer_gid=gid)
    active, payload = _read_exact(live, owner_uid=uid, writer_gid=gid)
    if (retained.st_nlink != 1 or
            (retained.st_dev, retained.st_ino) !=
            (before.st_dev, before.st_ino) or
            (active.st_dev, active.st_ino) ==
            (before.st_dev, before.st_ino) or payload or
            inspect_debug(old_path, retained.st_dev, retained.st_ino,
                          owner=proof.owner, writer_gid=gid)
            is not FDState.DRAINED or attest() != proof):
        # Atomic cut already happened. Do not attempt to rename the old
        # file back under a RUNNING engine; keep both authentic inodes.
        raise OriginalV2PrepareRefused("original_debug_retained_cut_unqualified")
    return True


def _require_debug_window_before_raw_cut(proof: GenerationProof, cursor,
                                         receipts: EpochReceipts, *,
                                         raw_first: bool = False) -> None:
    """Refuse a known-bad native debug before changing original raw inode.

    This remains a finite snapshot, not an atomic native-writer barrier.
    Reuse only the existing original P2k1 protected debug reader.
    """
    info, data = _read_exact(Path(proof.debug_path),
                             owner_uid=receipts.uid,
                             writer_gid=receipts.writer_gid)
    # Debug is diagnostic, not raw source truth. An original FD9/epoch-
    # authenticated new debug inode selects the one-way raw-first path.
    # Same-inode modification still refuses instead of hiding corruption.
    if (raw_first or
            (info.st_dev, info.st_ino) != (cursor.device, cursor.inode)):
        return
    if (cursor.offset > len(data) or
            hashlib.sha256(data[:cursor.offset]).hexdigest() !=
            cursor.prefix_sha256):
        raise OriginalV2PrepareRefused("debug_cursor_invalid_before_raw_cut")
    tail = data[cursor.offset:]
    if (len(tail) > MAX_WINDOW or
            (tail and not tail.endswith(b"\n")) or
            b"\x00" in tail):
        raise OriginalV2PrepareRefused("debug_window_invalid_before_raw_cut")


def prepare_original_v2_locked(
    queue: DurableInbox, receipts: EpochReceipts, *,
    attest: Callable[[], GenerationProof] = attest_running_generation,
    inspect: Callable = probe_pending_fd,
    inspect_debug: Callable = probe_pending_fd,
) -> Path | None:
    """Return one prepared ORIGINAL pending inode, without commit or ACK.

    The same queue.open-file-description must be held by the caller until
    its eventual separate Config-held processing. The exact protected
    *empty debug epoch* must already exist; no unauthenticated bootstrap.

    Preflight precedes any raw mutation:
      - v1/v2 journal mixing, corruption and chain capacity refuse;
      - pending from a different generation or >1 pending refuse;
      - an open v2 slot takes precedence over fresh inbox bytes;
      - an open slot with no original pending requires prior authorized
        ACK recovery, never a guessed new rotation.
    """
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(receipts, EpochReceipts) or
            queue.uid != receipts.uid or
            queue.writer_gid != receipts.writer_gid or
            not callable(attest) or not callable(inspect) or
            not callable(inspect_debug)):
        raise OriginalV2PrepareRefused("original_queue_epoch_lock_required")
    try:
        proof = qualified_current_source(attest(), queue)
        chain = CursorChain(receipts, queue)
        tip = chain.tip(proof)  # actual original P2k2a epoch, not fabricated
        pending = queue.segments()
        if (len(pending) > 1 or any(
                not PENDING.fullmatch(path.name) or
                not path.name.startswith(proof.generation + "-")
                for path in pending)):
            raise OriginalV2PrepareRefused("historical_or_ambiguous_pending_retained")
        if tip.open_intent is not None:
            # A crash after physical unlink but before slot ACK must recover
            # under a separate qualified original checkpoint/Config owner.
            # This source-only staging seam may never guess a completion.
            if not pending:
                raise OriginalV2PrepareRefused("unacknowledged_pending_needs_original_ack")
            if tip.open_intent["pending_name"] != pending[0].name:
                raise OriginalV2PrepareRefused("unacknowledged_pending_identity_mismatch")
        elif tip.next_sequence >= MAX_STEPS:
            raise OriginalV2PrepareRefused("bounded_cursor_chain_capacity")
        # The v2 tip includes its currently OPEN intent in used_pending_names.
        # Retrying that exact unacknowledged inode is necessary for durable
        # crash recovery. Only a name from a previously ACKed slot is reuse.
        if (pending and tip.open_intent is None and
                pending[0].name in tip.used_pending_names):
            raise OriginalV2PrepareRefused("acknowledged_pending_name_reused")
        if attest() != proof:
            raise OriginalV2PrepareRefused("original_owner_changed_before_rotation")
        if tip.open_intent is None:
            # Torn hardlink recovery must precede the normal strict
            # single-link debug reader. The cut itself verifies the
            # original cursor BEFORE changing native diagnostic inodes.
            _debug_cut_once(queue, receipts, proof, tip.cursor,
                            tip.raw_first, attest, inspect_debug,
                            retirement_tip=tip)
        if pending:
            # Reuse a fully rotated pending first, including if a new live
            # inbox already contains later data. For a P2a crash *after*
            # hardlink and before replace, complete only this exact inode.
            segment = pending[0]
            inode = segment.lstat()
            live = queue.inbox.lstat()
            if (inode.st_dev, inode.st_ino) == (live.st_dev, live.st_ino):
                # Crash-link repair still cuts the live raw pathname.
                _require_debug_window_before_raw_cut(proof, tip.cursor, receipts,
                                                     raw_first=tip.raw_first)
                segment = queue.rotate(generation=proof.generation)
        else:
            # Refuse known-bad debug before converting live raw to pending.
            _require_debug_window_before_raw_cut(proof, tip.cursor, receipts,
                                                     raw_first=tip.raw_first)
            segment = queue.rotate(generation=proof.generation)
        if segment is None:
            return None
        if attest() != proof:
            raise OriginalV2PrepareRefused("original_owner_changed_after_rotation")
        # Native P2b FD.DRAINED and P2k1 exact debug/raw proof happen
        # INSIDE this same original queue lock, in the v2 primitive.
        slot = chain.prepare(proof, segment, attest=attest, inspect=inspect)
        if (not isinstance(slot, Path) or not slot.is_dir() or
                attest() != proof):
            raise OriginalV2PrepareRefused("original_owner_changed_after_intent")
        return segment
    except (OriginalSourceRefused, CursorChainRefused, QueueSafetyError,
            ReceiptRefused, DebugWindowRefused, GenerationRefused,
            OSError, ValueError, TypeError,
            AttributeError, KeyError) as exc:
        raise OriginalV2PrepareRefused("original_v2_prepared_intent_unavailable") from exc
