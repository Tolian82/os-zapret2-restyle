#!/usr/bin/env python3
"""STEP 15b3d: source-only STOPPED schema3 / historical WAL / OLD guard join.

Never reuse the RUNNING three-slot inspector for STOPPED generations: after
the original operator Stop the NEW native paths and debug.log may be gone.
Only sealed root-private receipts, surviving OLD archive inodes and the
original independent STOPPED process attester are consulted. This does not
prove current Found/managed physical postimages or an unprocessed live tail;
therefore it cannot authorize unlink, ACK, recovery writes or retirement.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from auto_detect_epoch_receipts import (
    _canonical, _directory, _read, ReceiptRefused,
)
from auto_detect_original_history import (
    _held, _digest, _history_root, _read_history_once, _archive_paths,
)
from auto_detect_original_history_release_guard import (
    _expected_guard, _scan_original_archive, GUARD,
)
from auto_detect_original_history_postimages import _postimage_receipt
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, _original_learning_forward_progress_record,
    _original_learning_third_progress_record,
)
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_owner import (
    LearningGenerationProof, GenerationRefused,
    attest_learning_stopped_generation,
)
from auto_detect_destination_commit import (
    DestinationRefused, qualified_destination_plan,
)
from auto_detect_debug_window import DebugWindowRefused
from auto_detect_queue import QueueSafetyError
from auto_detect_fd import probe_pending_fd
import auto_detect_original_v2_model as original_model


def _stopped_historical_wal(writer, proof, mirror_sha):
    """Bind all original committed checkpoints to the saved final postimages.

    Read-only historical receipts only. No current NEW/debug/Found/managed,
    no physical OLD, and no source-independent *mutating* replay.
    """
    uid = writer.receipts.uid
    root = writer.receipts.root / proof.generation / "cursor-chain-v2"
    receipts, plans, checkpoint_shas = [], [], []
    _directory(root, uid)
    for seq in (0, 1, 2):
        folder = root / f"{seq:08d}"
        _directory(folder, uid)
        intent_raw = _read(folder / "intent.json", uid)
        intent = json.loads(intent_raw)
        if (intent_raw != _canonical(intent) or
                intent.get("schema") != 3 or
                intent.get("sequence") != seq or
                intent.get("generation") != proof.generation or
                intent.get("operation_id") != proof.operation_id or
                intent.get("native_map_sha256") != proof.native_map_sha256 or
                intent.get("owner_pid") != proof.owner.pid or
                intent.get("owner_start") != proof.owner.started or
                intent.get("ack_authorized") is not False):
            raise V2OriginalConfigRefused("stopped_history_wal_source_unqualified")
        plan, plan_raw = qualified_destination_plan(
            folder, intent, uid, targets=writer.targets)
        cp_raw = _read(folder / "destination" / "checkpoint.json", uid)
        cp = json.loads(cp_raw)
        debug_end = (intent["debug_end_offset"] if seq == 0
                     else intent["debug"]["end"])
        debug_sha = (intent["debug_end_sha256"] if seq == 0
                     else intent["debug"]["end_sha256"])
        expected = {
            "schema": 1, "kind": "destination-and-cursor-committed",
            "generation": proof.generation,
            "pending_name": f"learning-{seq:08d}",
            "plan_sha256": _digest(plan_raw),
            "evidence": "learning-native-debug",
            "committed_cursor_offset": debug_end,
            "committed_cursor_sha256": debug_sha,
            "ack_authorized": False,
        }
        if (cp_raw != _canonical(cp) or cp != expected or
                plan.get("schema") != 3 or
                "live" not in plan or
                plan.get("source_intent_sha256") != _digest(intent_raw)):
            raise V2OriginalConfigRefused(
                "stopped_history_original_checkpoint_not_committed")
        receipts.append((intent, intent_raw, cp, cp_raw))
        plans.append(plan)
        checkpoint_shas.append(_digest(cp_raw))
    second = receipts[1]
    second_raw = _read(root / "00000001" / "cursor-progress.json", uid)
    if second_raw != _canonical(
            _original_learning_forward_progress_record(
                second[0], second[1], second[3], second[2])):
        raise V2OriginalConfigRefused("stopped_history_second_cursor_unqualified")
    third = receipts[2]
    third_raw = _read(root / "00000002" / "cursor-progress.json", uid)
    progress = json.loads(third_raw)
    pinned = progress.get("destination_postimages")
    if (type(pinned) is not dict or set(pinned) != {"writes", "live"} or
            any(type(pinned[k]) is not dict or
                set(pinned[k]) != set(plans[2][k]) for k in ("writes", "live")) or
            third_raw != _canonical(
                _original_learning_third_progress_record(
                    third[0], third[1], third[3], third[2], pinned))):
        raise V2OriginalConfigRefused("stopped_history_third_cursor_unqualified")
    latest = {}
    for seq, plan in enumerate(plans):
        for kind in ("writes", "live"):
            for name, row in plan[kind].items():
                latest[(kind, name)] = (seq, row)
    receipt_raw = _read(_history_root(writer, proof) / "postimages.json", uid)
    receipt = json.loads(receipt_raw)
    witnesses = {}
    if (type(receipt) is not dict or
            type(receipt.get("destinations")) is not list or
            len(receipt["destinations"]) != len(latest)):
        raise V2OriginalConfigRefused("stopped_history_final_postimages_missing")
    for row in receipt["destinations"]:
        if type(row) is not dict:
            raise V2OriginalConfigRefused("stopped_history_postimage_invalid")
        key = row.get("target")
        if type(key) is not str or ":" not in key:
            raise V2OriginalConfigRefused("stopped_history_postimage_foreign_key")
        kind, name = key.split(":", 1)
        if ((kind, name) not in latest or key in witnesses):
            raise V2OriginalConfigRefused("stopped_history_postimage_foreign_target")
        seq, plan = latest[(kind, name)]
        expected_path = (writer.targets[name] if kind == "writes" else
                         original_model.COMMON_ACTIVE / "managed" /
                         f"hostlist-{name}.txt")
        if (row.get("path") != str(expected_path) or
                plan.get("path") != str(expected_path) or
                row.get("sha256") != plan.get("after") or
                row.get("last_writer_sequence") != seq):
            raise V2OriginalConfigRefused("stopped_history_postimage_not_original_wal")
        identity = tuple(row.get(k) for k in (
            "device", "inode", "ctime_ns", "mtime_ns", "size"))
        if seq == 2:
            pin = pinned[kind][name]
            if pin != {
                    "path": str(expected_path), "sha256": row["sha256"],
                    "device": identity[0], "inode": identity[1],
                    "ctime_ns": identity[2], "mtime_ns": identity[3],
                    "size": identity[4]}:
                raise V2OriginalConfigRefused("stopped_history_third_postimage_not_pinned")
        witnesses[key] = (
            row["path"], row["sha256"], identity, seq)
    expected_receipt = _canonical(_postimage_receipt(proof, mirror_sha, {
        "destination_witnesses": witnesses,
        "checkpoint_sha256": checkpoint_shas,
        "third_progress_sha256": _digest(third_raw),
    }))
    if receipt_raw != expected_receipt:
        raise V2OriginalConfigRefused("stopped_history_final_postimages_not_sealed")
    return (_digest(receipt_raw), tuple(checkpoint_shas),
            _digest(third_raw), len(witnesses))


def _stopped_snapshot_once(writer, proof, inspect):
    # Immutable mirror+original pending/archive manifests are checked
    # without opening any missing OLD inode or live producer file.
    old, mirror = _read_history_once(writer, proof)
    post_sha, checkpoint_shas, progress_sha, count = _stopped_historical_wal(
        writer, proof, mirror)
    guard_expected = _canonical(_expected_guard(
        writer, proof, old, mirror, post_sha))
    root = _history_root(writer, proof)
    raw = _read(root / GUARD, writer.receipts.uid)
    if raw != guard_expected:
        raise V2OriginalConfigRefused("stopped_history_original_release_guard_changed")
    _, prepared, _ = _archive_paths(writer, proof)
    if set(os.listdir(prepared)) != {
            "manifest.json", *(f"{n:03d}.json" for n, _, _ in proof.learning)}:
        raise V2OriginalConfigRefused("stopped_history_foreign_prepared_N")
    rows = json.loads(guard_expected)["profiles"]
    retained, missing = _scan_original_archive(
        writer, proof, rows, inspect)
    return (_digest(raw), mirror, post_sha, checkpoint_shas,
            progress_sha, count, retained, missing)


def preview_original_learning_stopped_guard_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Original FD9 read-only STOPPED historical proof; NO cleanup/ACK.

    Real independent native stopped-owner attestation is REQUIRED twice,
    outside the internal replay of immutable WAL. A caller-provided FD9
    callback can never impersonate a stopped dvtws2 process census.
    """
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (not isinstance(proof, LearningGenerationProof) or
                not callable(inspect)):
            raise V2OriginalConfigRefused("stopped_history_p2b_and_schema3_required")
        before_owner = attest_learning_stopped_generation()
        if before_owner != proof:
            raise V2OriginalConfigRefused("stopped_history_not_original_owner")
        first = _stopped_snapshot_once(writer, proof, inspect)
        second = _stopped_snapshot_once(writer, proof, inspect)
        after_owner = attest_learning_stopped_generation()
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (before_owner != after_owner or
                before_owner != proof or first != second):
            raise V2OriginalConfigRefused("stopped_history_raced_after_owner")
        guard_sha, mirror_sha, post_sha, cp_sha, progress_sha, count, kept, missing = second
        return {
            "generation": proof.generation, "sequence": 2,
            "stopped_original_owner_freshly_reattested": True,
            "release_guard_sha256": guard_sha,
            "old_mirror_manifest_sha256": mirror_sha,
            "historical_final_postimages_sha256": post_sha,
            "historical_original_wal_checkpoint_sha256": list(cp_sha),
            "historical_third_cursor_progress_sha256": progress_sha,
            "historical_final_destinations_count": count,
            "old_archive_state": (
                "all-retained" if not missing else
                "all-missing" if not kept else "partially-missing"),
            "retained_old_native_numbers": list(kept),
            "missing_old_native_numbers": list(missing),
            "all_three_original_historical_wal_checkpoints_verified": True,
            "current_new_native_and_debug_verified": False,
            "current_final_destinations_inode_pinned": False,
            "new_positive_debug_attribution_verified": False,
            "source_independent_transaction_replay_available": False,
            "owner_lifecycle_mutation_authorized": False,
            "physical_old_archive_cleanup_authorized": False,
            "archive_unlink_authorized": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            GenerationRefused, OriginalLockRefused, QueueSafetyError,
            DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "stopped_history_independent_original_proof_refused") from exc


def main():
    raise SystemExit("Original stopped OLD release guard is not a worker")


if __name__ == "__main__":
    main()
