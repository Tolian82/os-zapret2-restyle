#!/usr/bin/env python3
"""STEP 15b3g: original STOPPED post-OLD NEW/debug tail preflight, READ ONLY.

After a completed original FD9 OLD-only retirement, independently attest
the still-physical NEW native files and debug against the sealed third cut.
A positive pair remains UNCONSUMED until a later original P1/destination
checkpoint; it is never ACKed merely because an OLD archive was deleted.
Missing/rotated NEW or debug cannot be inferred from historical WAL.
This optional inspector is not wired to Stop/Restart/Apply/Boot/cron.
"""
from __future__ import annotations

import os

from auto_detect_epoch_receipts import (
    _canonical, _directory, _read, ReceiptRefused,
)
from auto_detect_original_history import _held, _digest
from auto_detect_original_history_positive import _positive_snapshot_once
from auto_detect_original_history_stopped import (
    preview_original_learning_stopped_guard_locked,
    preview_original_learning_stopped_destination_reconciliation_locked,
)
from auto_detect_original_history_stop_retirement import (
    _retirement_paths, _original_retirement_plan, _retired_complete_record,
    INTENT, COMPLETE,
)
from auto_detect_original_v2_model import V2OriginalConfigRefused
from auto_detect_owner import (
    LearningGenerationProof, GenerationRefused,
    attest_learning_stopped_generation,
)
from auto_detect_fd import probe_pending_fd
from auto_detect_destination_commit import DestinationRefused
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError
from auto_detect_debug_window import DebugWindowRefused


def _completed_old_retirement(writer, proof, historical):
    """Never infer OLD completion from absent files without exact receipts."""
    slot, folder, _archive = _retirement_paths(writer, proof)
    uid = writer.receipts.uid
    _directory(slot, uid)
    _directory(folder, uid)
    if set(os.listdir(folder)) != {INTENT, COMPLETE}:
        raise V2OriginalConfigRefused("stopped_new_missing_original_retirement_receipts")
    plan = _canonical(_original_retirement_plan(writer, proof, historical))
    if _read(folder / INTENT, uid) != plan:
        raise V2OriginalConfigRefused("stopped_new_original_retirement_intent_changed")
    complete = _canonical(_retired_complete_record(proof, plan))
    if _read(folder / COMPLETE, uid) != complete:
        raise V2OriginalConfigRefused("stopped_new_original_retirement_completion_changed")
    if set(os.listdir(folder)) != {INTENT, COMPLETE}:
        raise V2OriginalConfigRefused("stopped_new_retirement_receipts_raced")
    return _digest(plan), _digest(complete)


def preview_original_learning_stopped_NEW_tail_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Classify exact unread NEW after completed OLD retirement; never ACK.

    Even with all NEW physical paths still present and a genuine stopped
    owner, historical final Found/managed only proves the old third cut.
    Later matched N/debug positives must be committed via the original
    destination transaction before any future native cleanup. A vanished
    NEW file or debug is refused, never interpreted as an empty tail.
    """
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if not isinstance(proof, LearningGenerationProof) or not callable(inspect):
            raise V2OriginalConfigRefused("stopped_new_original_schema3_required")
        previous = preview_original_learning_stopped_destination_reconciliation_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (previous["old_archive_state"] != "all-missing" or
                previous["current_destinations_match_original_physical_postimages"]
                is not True or
                previous["historical_wal_all_destination_commits_complete"]
                is not True or
                previous["native_pending_ack_authorized"] is not False):
            raise V2OriginalConfigRefused("stopped_new_original_wal_or_old_not_complete")
        receipts = _completed_old_retirement(writer, proof, previous)
        # An injected FD9 callback alone is not a kernel STOPPED witness.
        owner_before = attest_learning_stopped_generation()
        if owner_before != proof:
            raise V2OriginalConfigRefused("stopped_new_original_owner_not_stopped")
        first = _positive_snapshot_once(writer, proof, inspect)
        second = _positive_snapshot_once(writer, proof, inspect)
        owner_after = attest_learning_stopped_generation()
        following = preview_original_learning_stopped_destination_reconciliation_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        after_receipts = _completed_old_retirement(writer, proof, following)
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (owner_before != owner_after or owner_before != proof or
                first != second or previous != following or
                receipts != after_receipts):
            raise V2OriginalConfigRefused("stopped_new_source_owner_or_targets_raced")

        # Paired positives are evidence of UNPROCESSED work, not proof of
        # a successful DPI bypass or of an existing Found/managed postimage.
        pending = [
            {"native_number": n, "hostlist": name, "hostname": host}
            for n, name, host in second["positive"]
        ]
        raw_bytes = second["native_bytes_after_third"]
        return {
            "generation": proof.generation, "sequence": 2,
            "original_OLD_archive_physically_retired": True,
            "retirement_intent_sha256": receipts[0],
            "retirement_completion_sha256": receipts[1],
            "current_final_destinations_inode_pinned": True,
            "stopped_owner_freshly_reattested": True,
            "all_NEW_native_and_debug_physically_pinned": True,
            "remaining_new_native_bytes": raw_bytes,
            "remaining_new_debug_bytes": second["debug_bytes_after_third"],
            "remaining_positive_native_observations": pending,
            "remaining_new_state": (
                "unconsumed-native-events" if raw_bytes else
                "no-unread-native-bytes"),
            "remaining_new_events_committed_to_found": False,
            "native_pending_ack_authorized": False,
            "new_native_cleanup_authorized": False,
            "generation_retired": False,
            "operator_stop_may_be_blocked": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            GenerationRefused, OriginalLockRefused, QueueSafetyError,
            DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "stopped_new_original_physical_tail_unavailable") from exc


def main():
    raise SystemExit("STOPPED original NEW tail preflight is not a worker")


if __name__ == "__main__":
    main()
