#!/usr/bin/env python3
"""#1052 P2j: dormant single-tick owner/FD/queue coordinator.

No cron/configd or production CLI is registered. This module cannot make a
successful durable destination write: authentic debug and sink callbacks do not
yet exist. Its purpose is to join existing queue + FD + owner primitives while
refusing deletion on any uncertain proof; a caller may exercise the internal
core with injected evidence only in a disposable regression.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable

from auto_detect_fd import FDState
from auto_detect_owner import GenerationProof
from auto_detect_queue import DurableInbox, _identity


class CycleRefused(RuntimeError):
    """Retain the entire unacknowledged source whenever proof is missing."""


@dataclass(frozen=True)
class CycleResult:
    rotated: bool
    acknowledged: int
    retained: int
    blocked: bool


def _qualified(proof: object, queue: DurableInbox,
               expected: GenerationProof | None = None) -> GenerationProof:
    if not isinstance(proof, GenerationProof):
        raise CycleRefused("no_authenticated_common_generation")
    if (proof.raw_path != str(queue.inbox) or
            proof.debug_path != str(queue.root / "debug.log") or
            proof.owner.pid <= 1 or not proof.operation_id or
            proof.generation != proof.operation_id or
            proof.observer_native_number <= 0 or
            (proof.observer_native_number, "observer", None) not in proof.profiles or
            not isinstance(queue, DurableInbox) or
            not re.fullmatch(r"[0-9a-f]{32}", proof.generation) or
            not re.fullmatch(r"[0-9a-f]{32}", proof.operation_id)):
        raise CycleRefused("wrong_queue_or_observer_generation")
    if expected is not None and proof != expected:
        raise CycleRefused("common_generation_changed_during_cycle")
    return proof


def _cycle_once(queue: DurableInbox, *, attest: Callable,
                inspect: Callable, correlate: Callable | None,
                persist: Callable | None) -> CycleResult:
    """The future native wrapper MUST supply real, non-permissive adapters.

    The P3 durable destination sink and debug-cursor correlator are not yet
    implemented. This function intentionally makes no path/ps/fstat spoofing
    shortcuts; even a local test must exercise the actual DurableInbox.
    """
    if not all(callable(x) for x in (attest, inspect, correlate, persist)):
        raise CycleRefused("missing_fd_debug_or_durable_commit_adapter")
    with queue.exclusive():
        start = _qualified(attest(), queue)
        pending = queue.segments()
        # Generation is durable in each pending filename, not inferred from
        # the *current* engine when recovering a previous minute/reboot.
        prefix = start.generation + "-"
        pattern = re.compile(re.escape(prefix) + r"[0-9a-f]{32}\.txt\Z")
        if any(pattern.fullmatch(path.name) is None for path in pending):
            raise CycleRefused("pending_segment_has_no_current_generation_proof")
        rotated = False
        # Crash after hardlink and before replacement: a pending entry still
        # aliases the LIVE inbox inode. Never treat it as a complete segment.
        # Finish that existing rotation first, even if pending is nonempty.
        live = _identity(queue.inbox)
        interrupted = any(_identity(path) == live for path in pending)
        if not pending or interrupted:
            rotated_path = queue.rotate(generation=start.generation)
            rotated = rotated_path is not None
            if rotated:
                # A new Apply/engine could have started while we rotated.
                _qualified(attest(), queue, start)
                pending = queue.segments()
        if any(pattern.fullmatch(path.name) is None for path in pending):
            raise CycleRefused("pending_segment_has_no_current_generation_proof")
        acknowledged = 0
        for segment in pending:
            def drained(path: Path, dev: int, inode: int) -> bool:
                proof = _qualified(attest(), queue, start)
                return inspect(path, dev, inode, owner=proof.owner,
                               writer_gid=queue.writer_gid) is FDState.DRAINED

            def committed(raw: bytes) -> bool:
                # Reattest before both debug binding and side-effecting commit.
                _qualified(attest(), queue, start)
                if correlate(raw, start) is not True:
                    return False
                _qualified(attest(), queue, start)
                if persist(raw, start) is not True:
                    return False
                # Commit may already be durable on failure here: the next
                # tick MUST replay idempotently, never silently unlink.
                _qualified(attest(), queue, start)
                return True

            # The actual queue owns inode/size/last-line/fsync/unlink safety.
            if not queue.acknowledge(segment, drained=drained, committed=committed):
                return CycleResult(rotated, acknowledged,
                                   len(queue.segments()), True)
            acknowledged += 1
        return CycleResult(rotated, acknowledged, len(queue.segments()), False)


def run_native_cycle() -> None:
    """Not enabled: no real debug-cursor and P3 durable destination adapter.

    Never install a timer or invoke the core directly from configd while both
    trustworthy adapters and the authenticated live schema-2 producer are absent.
    """
    raise CycleRefused("native_cycle_not_active_without_debug_and_destination")


if __name__ == "__main__":
    run_native_cycle()
