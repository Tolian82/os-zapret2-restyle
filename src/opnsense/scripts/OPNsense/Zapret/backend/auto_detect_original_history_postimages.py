#!/usr/bin/env python3
"""STEP 15b2a: final physical Found/managed postimage evidence, import ONLY.

The original archive is created only after the third destination checkpoint.
Before possible OLD inode disposal, bind ALL final destination identities
(including last writes from slots zero and one) in ONE original root-private
write-once receipt. Read that receipt later WITHOUT opening any OLD inode.

This is not a partial-CAS recovery writer, a permission to ACK/unlink, or a
substitute for positive NEW-native/debug and owner-live evidence.
"""
from __future__ import annotations

import os
import json
from pathlib import Path

from auto_detect_epoch_receipts import _canonical, _read, _write_once, ReceiptRefused
from auto_detect_original_history import (
    _held, _digest, _history_root, _read_history_once,
)
from auto_detect_original_history_wal import _read_original_wal_once
from auto_detect_original_native_archive import (
    _read_archive_plan, preview_original_learning_archive_release_locked,
)
from auto_detect_original_v2_model import V2OriginalConfigRefused
from auto_detect_destination_commit import DestinationRefused
from auto_detect_debug_window import DebugWindowRefused
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError
from auto_detect_fd import probe_pending_fd


def _snapshot(writer, proof, workspace, config_fd, config_path, attest, inspect):
    """Double-reread old mirror, original WAL, all final files and NEW tails."""
    _held(writer, proof, workspace, config_fd, config_path, attest)
    if not callable(inspect):
        raise V2OriginalConfigRefused("native_postimages_P2b_missing")
    old_images, mirror_sha = _read_history_once(writer, proof)
    before = _read_original_wal_once(writer, proof, old_images, inspect)
    newer_old, newer_sha = _read_history_once(writer, proof)
    after = _read_original_wal_once(writer, proof, newer_old, inspect)
    _held(writer, proof, workspace, config_fd, config_path, attest)
    if (old_images != newer_old or mirror_sha != newer_sha or
            before != after or
            before["all_three_original_wal_checkpoints_verified"] is not True):
        raise V2OriginalConfigRefused("native_postimages_snapshot_raced")
    return mirror_sha, before


def _postimage_receipt(proof, mirror_sha, evidence):
    """Original WAL-bound immutable physical identities; NEVER a new plan."""
    rows = []
    for key, value in sorted(evidence["destination_witnesses"].items()):
        if (type(key) is not str or ":" not in key or
                type(value) is not tuple or len(value) != 4):
            raise V2OriginalConfigRefused("native_postimages_foreign_witness")
        kind, name = key.split(":", 1)
        path, digest, identity, last_writer = value
        if (kind not in ("writes", "live") or
                not name or type(identity) is not tuple or
                len(identity) != 5 or
                type(last_writer) is not int or
                last_writer not in (0, 1, 2) or
                type(path) is not str or not Path(path).is_absolute() or
                type(digest) is not str or len(digest) != 64 or
                any(type(x) is not int or x < 0 for x in identity) or
                identity[1] == 0):
            raise V2OriginalConfigRefused("native_postimages_invalid_witness")
        rows.append({
            "target": key, "path": path, "sha256": digest,
            "device": identity[0], "inode": identity[1],
            "ctime_ns": identity[2], "mtime_ns": identity[3],
            "size": identity[4], "last_writer_sequence": last_writer,
        })
    if not rows or len(rows) > 18:
        raise V2OriginalConfigRefused("native_postimages_unbounded_destinations")
    return {
        "schema": 3,
        "kind": "original-learning-independent-final-postimages",
        "generation": proof.generation, "sequence": 2,
        "owner_pid": proof.owner.pid,
        "owner_start": proof.owner.started,
        "operation_id": proof.operation_id,
        "native_map_sha256": proof.native_map_sha256,
        "old_mirror_manifest_sha256": mirror_sha,
        "original_wal_checkpoints_sha256": list(evidence["checkpoint_sha256"]),
        "third_cursor_progress_sha256": evidence["third_progress_sha256"],
        "destinations": rows,
        "new_positive_debug_attribution_verified": False,
        "source_independent_transaction_replay_available": False,
        "archive_unlink_authorized": False,
        "native_pending_ack_authorized": False,
        "generation_retired": False,
    }


def _check_seal(writer, proof, workspace, config_fd, config_path, attest,
                inspect):
    mirror_sha, evidence = _snapshot(
        writer, proof, workspace, config_fd, config_path, attest, inspect)
    expected = _canonical(_postimage_receipt(proof, mirror_sha, evidence))
    root = _history_root(writer, proof)
    actual = _read(root / "postimages.json", writer.receipts.uid)
    if actual != expected:
        raise V2OriginalConfigRefused("native_postimages_physical_identity_changed")
    return _digest(actual), evidence


def read_original_learning_independent_postimages_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Read after missing OLD inode; no physical historical OLD reopen."""
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        sha, first = _check_seal(
            writer, proof, workspace, config_fd, config_path, attest, inspect)
        again, second = _check_seal(
            writer, proof, workspace, config_fd, config_path, attest, inspect)
        if sha != again or first != second:
            raise V2OriginalConfigRefused("native_postimages_postseal_raced")
        _held(writer, proof, workspace, config_fd, config_path, attest)
        return {
            "generation": proof.generation, "sequence": 2,
            "postimages_sha256": sha,
            "all_three_original_wal_checkpoints_verified": True,
            "all_final_destinations_inode_pinned": True,
            "final_destination_count": len(first["destination_witnesses"]),
            "unprocessed_new_native_bytes":
                first["unprocessed_new_native_bytes"],
            "unprocessed_new_debug_bytes":
                first["unprocessed_new_debug_bytes"],
            "new_positive_debug_attribution_verified": False,
            "source_independent_transaction_replay_available": False,
            "archive_unlink_authorized": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            DebugWindowRefused, OriginalLockRefused, QueueSafetyError) as exc:
        raise V2OriginalConfigRefused(
            "native_postimages_independent_replay_refused") from exc


def seal_original_learning_independent_postimages_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Original pre-unlink attestation only; one crash-resumable receipt."""
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        before = _read_archive_plan(writer, proof)
        if before is None:
            raise V2OriginalConfigRefused("native_postimages_original_archive_missing")
        gate = preview_original_learning_archive_release_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (gate.get("archive_relocation_qualified") is not True or
                gate.get("archive_unlink_authorized") is not False or
                gate.get("source_independent_replay_available") is not False):
            raise V2OriginalConfigRefused("native_postimages_archive_gate_changed")
        mirror, evidence = _snapshot(
            writer, proof, workspace, config_fd, config_path, attest, inspect)
        expected = _canonical(_postimage_receipt(proof, mirror, evidence))
        root = _history_root(writer, proof)
        if set(os.listdir(root)) - (
                {f"{n:03d}" for n, _, _ in proof.learning} |
                {"manifest.json", "postimages.json", "release-guard.json"}):
            raise V2OriginalConfigRefused("native_postimages_foreign_history_entry")
        _held(writer, proof, workspace, config_fd, config_path, attest)
        _write_once(root, "postimages.json", expected, writer.receipts.uid)
        proved = read_original_learning_independent_postimages_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (_read_archive_plan(writer, proof) != before or
                proved["postimages_sha256"] != _digest(expected)):
            raise V2OriginalConfigRefused("native_postimages_after_seal_raced")
        return proved
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            DebugWindowRefused, OriginalLockRefused, QueueSafetyError) as exc:
        raise V2OriginalConfigRefused("native_postimages_seal_refused") from exc


def main():
    raise SystemExit("Original independent destination postimages are not a worker")


if __name__ == "__main__":
    main()
