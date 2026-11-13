#!/usr/bin/env python3
"""#1052 P2k3: dormant authenticated pending -> canonical P1 decision.

This adapter is deliberately read-only. It does not authorize acknowledgment or
make an installed P2c generation map. The default native attester + FD inspector
are fail-closed; injected adapters are usable only by disposable source tests.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from typing import Callable

from auto_detect_debug_window import Cursor, DebugWindowRefused, propose_window
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused, EMPTY_HASH, MAX_SEGMENT
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_owner import GenerationProof, attest_running_generation
from auto_detect_queue import DurableInbox
from domain_policy import AutoDomainPolicyError, PublicSuffixList, plan_auto_additions


class BatchRefused(RuntimeError):
    """Untrusted batch: preserve the original pending and any prior receipts."""


@dataclass(frozen=True)
class VerifiedBatch:
    """Transient proof of policy planning, NOT a durable commit or FD9 seal."""
    generation: str
    pending_name: str
    pending_sha256: str
    debug_end_offset: int
    debug_end_sha256: str
    policy: dict
    ack_authorized: bool = False


def _pending_bytes(pending: Path, queue: DurableInbox, intent: dict) -> bytes:
    """Use the existing protected old-inode protocol without deleting source."""
    if (pending.parent != queue.pending or pending not in queue.segments() or
            intent.get("pending_name") != pending.name or
            type(intent.get("pending_size")) is not int or
            not 0 < intent["pending_size"] <= MAX_SEGMENT):
        raise BatchRefused("pending_not_in_original_locked_queue")
    try:
        before = pending.lstat()
        fd = os.open(pending, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            opened = os.fstat(fd)
            raw = os.read(fd, MAX_SEGMENT + 1)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        current = pending.lstat()
    except OSError as exc:
        raise BatchRefused("original_pending_unreadable") from exc
    identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
    if (identity(before) != identity(opened) or identity(after) != identity(before) or
            identity(current) != identity(before) or not stat.S_ISREG(before.st_mode) or
            before.st_uid != queue.uid or before.st_nlink != 1 or
            stat.S_IMODE(before.st_mode) != (0o600 if queue.writer_gid is None else 0o660) or
            (queue.writer_gid is not None and before.st_gid != queue.writer_gid) or
            len(raw) != before.st_size or
            (before.st_dev, before.st_ino, before.st_size, hashlib.sha256(raw).hexdigest()) !=
            (intent.get("pending_device"), intent.get("pending_inode"),
             intent["pending_size"], intent.get("pending_sha256")) or
            not raw.endswith(b"\n")):
        raise BatchRefused("original_pending_inode_or_hash_changed")
    return raw


def prepare_verified_batch(queue: DurableInbox, receipts: EpochReceipts,
                           pending: Path, hostlists: dict[str, str],
                           automatic: dict[str, str], global_exclude: str = "", *,
                           attest: Callable = attest_running_generation,
                           inspect: Callable = probe_pending_fd,
                           psl: PublicSuffixList | None = None,
                           allow_owned_relocation: bool = False) -> VerifiedBatch:
    """Read current original P2c/P2b + P2k1/P2k2a; invoke P1 exactly once.

    The caller must hold `queue.exclusive()` across this procedure. Historical
    receipts alone cannot impersonate an exited original native engine. The
    default `attest` and `inspect` are the real FreeBSD read-side gates; tests
    may inject bounded synthetic proofs without producing live authority.
    """
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(receipts, EpochReceipts) or
            not callable(attest) or not callable(inspect) or
            type(allow_owned_relocation) is not bool):
        raise BatchRefused("original_queue_lock_and_native_evidence_required")
    try:
        proof = attest()
        if (not isinstance(proof, GenerationProof) or
                proof.raw_path != str(queue.inbox) or
                proof.debug_path != str(queue.root / "debug.log") or
                proof.generation != proof.operation_id or
                (proof.observer_native_number, "observer", None) not in proof.profiles):
            raise BatchRefused("no_authentic_original_native_observer")
        _, epoch = receipts._epoch(proof)
        h = receipts.historical(proof.generation)
        intent = h.intent
        if (not isinstance(intent, dict) or
                intent.get("generation") != proof.generation or
                intent.get("debug_start_offset") != 0 or
                intent.get("debug_start_sha256") != EMPTY_HASH or
                intent.get("debug_device") != epoch["debug_device"] or
                intent.get("debug_inode") != epoch["debug_inode"]):
            raise BatchRefused("missing_original_prepared_intent")
        pending = Path(pending)
        raw = _pending_bytes(pending, queue, intent)
        info = pending.stat()
        if inspect(pending, info.st_dev, info.st_ino,
                   owner=proof.owner, writer_gid=queue.writer_gid) is not FDState.DRAINED:
            raise BatchRefused("original_native_writer_fd_not_drained")
        cursor = Cursor(proof.generation, epoch["debug_device"],
                        epoch["debug_inode"], 0, EMPTY_HASH)
        window = propose_window(proof, cursor, raw, owner_uid=receipts.uid,
                                writer_gid=queue.writer_gid)
        if (not window.candidates or
                any(c.native_number != proof.observer_native_number for c in window.candidates) or
                len(window.candidates) != intent.get("candidate_count") or
                window.proposed_cursor.offset != intent.get("debug_end_offset") or
                window.proposed_cursor.prefix_sha256 != intent.get("debug_end_sha256")):
            raise BatchRefused("native_debug_does_not_match_original_intent")
        # The genuine trailing native observer has NO known-list selector.
        # Never map it to YouTube/User by domain spelling or earlier profiles.
        discoveries = [{"hostname": c.host, "hostlist": None}
                       for c in window.candidates]
        plan = plan_auto_additions(discoveries, hostlists, automatic,
                                   global_exclude, psl=psl)
        if (plan["result"] != "ok" or plan["unprocessed"] or
                (plan["removals"] and not allow_owned_relocation) or
                (allow_owned_relocation and
                 set(plan["removals"]) - {"youtube", "user"}) or
                any(name != "auto" for name in plan["additions"]) or
                any(row["destination"] != "auto" for row in plan["routes"])):
            # Even with an opted-in known-owned relocation transaction, the
            # genuine trailing observer NEVER gains known-list attribution.
            # Old owned rows move only via a separately authenticated sink.
            raise BatchRefused("policy_requires_unimplemented_owned_relocation")
        if attest() != proof:
            raise BatchRefused("original_common_generation_changed_during_plan")
        return VerifiedBatch(proof.generation, intent["pending_name"],
                             intent["pending_sha256"],
                             intent["debug_end_offset"],
                             intent["debug_end_sha256"], plan)
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            ReceiptRefused, DebugWindowRefused, AutoDomainPolicyError) as exc:
        raise BatchRefused("original_pending_policy_evidence_unavailable") from exc


def run_native_verified_batch_worker() -> None:
    raise BatchRefused("native_owner_gui_and_destination_writer_not_connected")


if __name__ == "__main__":
    run_native_verified_batch_worker()