#!/usr/bin/env python3
"""STEP 15b3f: optional original FD9 STOPPED OLD-only archival retirement.

This is NOT a Stop/Restart/Apply hook or a worker. It physically releases
only fully checkpointed, independently mirrored OLD native archive inodes.
A write-once intent is fsynced BEFORE the first unlink; interruption after
any unlink resumes from that original intent and independent immutable WAL.
The NEW native --hostlist-auto inodes and debug.log are never opened for
mutation, truncated, acknowledged or removed here. An explicit operator
Stop may discard transient uncommitted learning under DEV-064; this
optional cleanup must never hold Stop hostage or claim all-native ACK.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from auto_detect_epoch_receipts import (
    _canonical, _directory, _read, _sync, _write_once, ReceiptRefused,
)
from auto_detect_original_history import _held, _history_root, _digest
from auto_detect_original_history_release_guard import GUARD
from auto_detect_original_history_stopped import (
    preview_original_learning_stopped_guard_locked,
    preview_original_learning_stopped_destination_reconciliation_locked,
)
from auto_detect_original_native_archive import _archive_paths
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, _native_rebind_stable_snapshot,
)
from auto_detect_owner import (
    LearningGenerationProof, GenerationRefused,
    attest_learning_stopped_generation,
)
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_destination_commit import DestinationRefused
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError
from auto_detect_debug_window import DebugWindowRefused


FOLDER = "pending-old-retirement"
INTENT = "intent.json"
COMPLETE = "complete.json"


def _retirement_paths(writer, proof):
    slot, _, archive = _archive_paths(writer, proof)
    return slot, slot / FOLDER, archive


def _original_retirement_plan(writer, proof, historical):
    """Only the original immutable archive guard may define names/inodes."""
    uid = writer.receipts.uid
    raw = _read(_history_root(writer, proof) / GUARD, uid)
    guard = json.loads(raw)
    if (_digest(raw) != historical["release_guard_sha256"] or
            raw != _canonical(guard) or
            guard.get("generation") != proof.generation or
            guard.get("native_map_sha256") != proof.native_map_sha256):
        raise V2OriginalConfigRefused("stopped_old_retirement_guard_mismatch")
    rows = guard.get("profiles")
    if (type(rows) is not list or
            len(rows) != len(proof.learning) or
            [r.get("native_number") for r in rows] !=
            [n for n, _, _ in proof.learning] or
            any(type(r) is not dict or
                r.get("hostlist") != hostlist or
                r.get("old_inode", 0) <= 0
                for r, (_, hostlist, _) in zip(rows, proof.learning))):
        raise V2OriginalConfigRefused("stopped_old_retirement_foreign_N")
    return {
        "schema": 3, "kind": "original-fd9-stopped-OLD-archive-retirement-intent",
        "generation": proof.generation, "operation_id": proof.operation_id,
        "sequence": 2, "owner_pid": proof.owner.pid,
        "owner_start": proof.owner.started,
        "native_map_sha256": proof.native_map_sha256,
        "release_guard_sha256": historical["release_guard_sha256"],
        "old_mirror_manifest_sha256": historical["old_mirror_manifest_sha256"],
        "final_postimages_sha256": historical["historical_final_postimages_sha256"],
        "original_wal_checkpoint_sha256": historical[
            "historical_original_wal_checkpoint_sha256"],
        "third_cursor_progress_sha256": historical[
            "historical_third_cursor_progress_sha256"],
        "profiles": rows,
        "only_original_archived_OLD_paths": True,
        "new_live_native_touched": False,
        "new_live_debug_touched": False,
        "native_pending_ack_authorized": False,
        "new_generation_retired": False,
        "operator_stop_may_be_blocked": False,
    }


def _retired_complete_record(proof, plan_raw):
    return {
        "schema": 3, "kind": "original-fd9-stopped-OLD-archive-physically-absent",
        "generation": proof.generation, "sequence": 2,
        "original_retirement_intent_sha256": _digest(plan_raw),
        "original_OLD_paths_absent": True,
        "new_live_native_touched": False,
        "new_live_debug_touched": False,
        "native_pending_ack_authorized": False,
        "generation_retired": False,
        "operator_stop_may_be_blocked": False,
    }


def _unlink_original_OLD_only(path, row, writer, proof, inspect):
    """Last original physical inode and all-PID FD check before unlink."""
    uid, gid = writer.receipts.uid, writer.queue.writer_gid
    archive = _archive_paths(writer, proof)[2]
    if (path.parent != archive or
            path.name != f"{row['native_number']:03d}.txt"):
        raise V2OriginalConfigRefused("stopped_old_retirement_foreign_path")
    stat, data, identity = _native_rebind_stable_snapshot(
        path, uid, gid, allowed_links=(1,))
    if ((stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) !=
            (row["old_device"], row["old_inode"], row["old_size"],
             row["old_mtime_ns"]) or
            _digest(data) != row["old_sha256"] or
            inspect(path, stat.st_dev, stat.st_ino, owner=proof.owner,
                    writer_gid=gid) is not FDState.DRAINED):
        raise V2OriginalConfigRefused(
            "stopped_old_retirement_inode_or_fd_changed")
    second, newer, observed = _native_rebind_stable_snapshot(
        path, uid, gid, allowed_links=(1,))
    if (observed != identity or
            _digest(newer) != row["old_sha256"] or
            (second.st_dev, second.st_ino) != (stat.st_dev, stat.st_ino)):
        raise V2OriginalConfigRefused("stopped_old_retirement_last_inode_raced")
    # Only this archived inode. Never unlink producer NEW/debug, or apply a
    # second destination/Config write to manually editable Found/managed.
    os.unlink(path)
    _sync(archive)
    if path.exists() or path.is_symlink():
        raise V2OriginalConfigRefused("stopped_old_retirement_unlink_not_durable")


def retire_original_learning_stopped_OLD_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Crash-resumable OLD-only cleanup, with original FD9 and no ACK claim.

    Real native STOPPED owner is independently attested before *every*
    physical unlink and again after. Never called by operator Stop. The
    first invocation must see ALL OLD archive inodes and original live
    Found/managed postimages; subsequent partial recovery is accepted ONLY
    with the pre-existing, exact write-once intent. If a new engine/owner
    starts, cleanup refuses while normal lifecycle continues.
    """
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (not isinstance(proof, LearningGenerationProof) or
                not callable(inspect)):
            raise V2OriginalConfigRefused(
                "stopped_old_retirement_original_schema3_required")
        slot, folder, archive = _retirement_paths(writer, proof)
        before = preview_original_learning_stopped_guard_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        expected = _canonical(_original_retirement_plan(writer, proof, before))
        present_intent = folder / INTENT
        folder_exists = folder.exists() or folder.is_symlink()
        if folder_exists:
            _directory(folder, writer.receipts.uid)
            if set(os.listdir(folder)) - {INTENT, COMPLETE}:
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_foreign_journal")
            if present_intent.exists() or present_intent.is_symlink():
                if _read(present_intent, writer.receipts.uid) != expected:
                    raise V2OriginalConfigRefused(
                        "stopped_old_retirement_original_intent_changed")
            elif before["old_archive_state"] != "all-retained":
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_missing_intent_after_unlink")
        if not present_intent.exists() and not present_intent.is_symlink():
            if before["old_archive_state"] != "all-retained":
                # Never infer that a missing OLD file was deleted by this
                # operation when there is no previously fsynced intent.
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_unattributed_OLD_loss")
            original = preview_original_learning_stopped_destination_reconciliation_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect)
            if (original["current_destinations_match_original_physical_postimages"]
                    is not True or
                    original["historical_wal_all_destination_commits_complete"]
                    is not True or
                    original["native_pending_ack_authorized"] is not False):
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_original_found_not_committed")
            if attest_learning_stopped_generation() != proof:
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_owner_changed_before_intent")
            if not folder_exists:
                _held(writer, proof, workspace, config_fd,
                      config_path, attest)
                folder.mkdir(mode=0o700)
                _sync(slot)
            _directory(folder, writer.receipts.uid)
            if os.listdir(folder):
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_partial_unqualified")
            # A STOPPED owner and ALL original old inode identities must
            # still be genuine after the initial real target inspection.
            again = preview_original_learning_stopped_guard_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect)
            if again != before or again["old_archive_state"] != "all-retained":
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_initial_owner_or_archive_raced")
            _held(writer, proof, workspace, config_fd, config_path, attest)
            if attest_learning_stopped_generation() != proof:
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_owner_raced_before_intent")
            _write_once(folder, INTENT, expected, writer.receipts.uid)
        if _read(present_intent, writer.receipts.uid) != expected:
            raise V2OriginalConfigRefused(
                "stopped_old_retirement_plan_not_durable")
        complete_path = folder / COMPLETE
        complete_expected = _canonical(_retired_complete_record(proof, expected))
        if complete_path.exists() or complete_path.is_symlink():
            if _read(complete_path, writer.receipts.uid) != complete_expected:
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_completion_changed")
            if before["old_archive_state"] != "all-missing":
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_premature_completion")
        rows = json.loads(expected)["profiles"]
        for row in rows:
            current = preview_original_learning_stopped_guard_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect)
            if (current["release_guard_sha256"] !=
                    before["release_guard_sha256"] or
                    _read(present_intent, writer.receipts.uid) != expected):
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_owner_or_intent_changed")
            number = row["native_number"]
            if number in current["missing_old_native_numbers"]:
                continue
            if number not in current["retained_old_native_numbers"]:
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_undeclared_old_inode")
            if complete_path.exists() or complete_path.is_symlink():
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_completed_but_old_present")
            # This is NOT a caller-provided proof. It reattests actual
            # FreeBSD stopped-owner lifecycle/process census independently.
            if attest_learning_stopped_generation() != proof:
                raise V2OriginalConfigRefused(
                    "stopped_old_retirement_owner_replaced")
            _held(writer, proof, workspace, config_fd, config_path, attest)
            path = archive / f"{number:03d}.txt"
            _unlink_original_OLD_only(path, row, writer, proof, inspect)
        final = preview_original_learning_stopped_guard_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (final["old_archive_state"] != "all-missing" or
                len(final["missing_old_native_numbers"]) != len(proof.learning)
                or _read(present_intent, writer.receipts.uid) != expected):
            raise V2OriginalConfigRefused(
                "stopped_old_retirement_not_all_fsynced")
        _held(writer, proof, workspace, config_fd, config_path, attest)
        _write_once(folder, COMPLETE, complete_expected, writer.receipts.uid)
        replay = preview_original_learning_stopped_guard_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (replay != final or
                _read(present_intent, writer.receipts.uid) != expected or
                _read(complete_path, writer.receipts.uid) != complete_expected
                or set(os.listdir(folder)) != {INTENT, COMPLETE}):
            raise V2OriginalConfigRefused(
                "stopped_old_retirement_completion_not_attested")
        return {
            "generation": proof.generation, "sequence": 2,
            "original_OLD_archive_physically_retired": True,
            "old_archive_state": "all-missing",
            "retirement_intent_sha256": _digest(expected),
            "retirement_completion_sha256": _digest(complete_expected),
            "new_native_live_files_touched": False,
            "new_native_debug_touched": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
            "operator_stop_may_be_blocked": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, ReceiptRefused, GenerationRefused,
            DestinationRefused, OriginalLockRefused,
            QueueSafetyError, DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "stopped_old_retirement_original_fd9_or_source_refused") from exc


def main():
    raise SystemExit("Original STOPPED OLD retirement is not a worker")


if __name__ == "__main__":
    main()
