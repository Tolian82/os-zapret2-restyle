#!/usr/bin/env python3
"""#1052 P2k8k: dormant same-generation durable checkpoint -> pending ACK.

This import-only bridge cannot establish FD9, produce a native epoch, run the
Config-held transaction or authorize a collector. Its caller must hold the
original queue lock and obtain the *actual* Config-child completion response.
Old-generation replay is deliberately not inferred from a historical receipt.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

from auto_detect_destination_commit import DestinationCommit, DestinationRefused
from auto_detect_epoch_receipts import _read, ReceiptRefused
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_owner import GenerationProof, attest_running_generation


class PostCommitRefused(RuntimeError):
    """Preserve unacknowledged bytes on any ambiguous commit or provenance."""


def acknowledge_current_checkpoint(writer: DestinationCommit, pending: Path,
                                   completion: dict, *,
                                   attest: Callable = attest_running_generation,
                                   inspect: Callable = probe_pending_fd) -> bool:
    """Remove one ORIGINAL pending only after durable original-child result.

    The caller must be the *same* queue owner that invoked original OPNsense
    Config::lock() -> P1 -> P2k2b, with a real completion from that child.
    Persistent receipts are not by themselves owner authorization. The native
    defaults re-attest the live original dvtws2 and its old writer FD before
    and after the queue's own final inode-safe unlink protocol.
    """
    if (not isinstance(writer, DestinationCommit) or not writer.queue._held or
            not isinstance(pending, Path) or not isinstance(completion, dict) or
            not callable(attest) or not callable(inspect)):
        raise PostCommitRefused('original_locked_owner_and_completion_required')
    queue = writer.queue
    try:
        proof = attest()
        if (not isinstance(proof, GenerationProof) or
                proof.generation != proof.operation_id or
                proof.raw_path != str(queue.inbox) or
                proof.debug_path != str(queue.root / 'debug.log') or
                (proof.observer_native_number, 'observer', None) not in proof.profiles):
            raise PostCommitRefused('current_original_observer_not_attested')
        # Reads original immutable epoch and exactly this hashed, rotated inode.
        folder, intent, original = writer._source(proof, pending)
        plan_raw = _read(folder / 'destination' / 'plan.json', writer.receipts.uid)
        checkpoint_raw = _read(folder / 'destination' / 'checkpoint.json', writer.receipts.uid)
        plan, checkpoint = json.loads(plan_raw), json.loads(checkpoint_raw)
        expected_plan = {
            'schema': 1, 'kind': 'durable-destination-plan',
            'generation': proof.generation, 'pending_name': pending.name,
            'pending_sha256': intent['pending_sha256'],
            'debug_end_offset': intent['debug_end_offset'],
            'debug_end_sha256': intent['debug_end_sha256'],
        }
        if (not isinstance(plan, dict) or
                set(plan) != set(expected_plan) | {'writes'} or
                any(plan.get(key) != val for key, val in expected_plan.items()) or
                not isinstance(plan['writes'], dict) or
                set(plan['writes']) - set(writer.targets)):
            raise PostCommitRefused('destination_plan_not_original_intent')
        expected_checkpoint = {
            'schema': 1, 'kind': 'destination-and-cursor-committed',
            'generation': proof.generation, 'pending_name': pending.name,
            'plan_sha256': hashlib.sha256(plan_raw).hexdigest(),
            'committed_cursor_offset': intent['debug_end_offset'],
            'committed_cursor_sha256': intent['debug_end_sha256'],
            'ack_authorized': False,
        }
        if (not isinstance(checkpoint, dict) or
                checkpoint != expected_checkpoint or completion != checkpoint):
            raise PostCommitRefused('original_child_checkpoint_mismatch')

        def still_original() -> bool:
            return attest() == proof

        def drained(path: Path, device: int, inode: int) -> bool:
            if (path != pending or
                    (device, inode) != (intent['pending_device'], intent['pending_inode']) or
                    not still_original()):
                return False
            answer = inspect(path, device, inode, owner=proof.owner,
                             writer_gid=queue.writer_gid)
            return answer is FDState.DRAINED and still_original()

        def persisted(data: bytes) -> bool:
            if data != original or not still_original():
                return False
            # Re-read durable protected receipts after Config child exits;
            # a mere successful subprocess or a forged JSON string is not ACK.
            if (_read(folder / 'destination' / 'plan.json', writer.receipts.uid) != plan_raw or
                    _read(folder / 'destination' / 'checkpoint.json',
                          writer.receipts.uid) != checkpoint_raw):
                return False
            return still_original()

        # Queue owns the separate fresh FD read, final stat, unlink and fsync.
        return queue.acknowledge(pending, drained=drained, committed=persisted)
    except (DestinationRefused, ReceiptRefused, OSError, ValueError, KeyError,
            TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise PostCommitRefused('original_durable_ack_evidence_unavailable') from exc


def main() -> None:
    raise PostCommitRefused('original_fd9_generation_and_minute_worker_not_enabled')


if __name__ == '__main__':
    main()
