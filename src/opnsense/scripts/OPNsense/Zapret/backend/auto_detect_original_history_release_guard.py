#!/usr/bin/env python3
"""STEP 15b3a: original crash-state OLD archive classifier, NO unlink/ACK.

The one original FD4/FD9/P2a/GUI, all-PID P2b and completed three-slot
DestinationCommit proof must seal a pre-disposal immutable guard while every
OLD archive inode still physically exists. A later read can classify an
arbitrary missing subset without opening missing OLD inodes or attempting
to restore/erase them. This module is import-only; it performs NO unlink,
cursor write, Found/managed change, Config write or retirement.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from auto_detect_epoch_receipts import (
    _canonical, _directory, _read, _write_once, ReceiptRefused,
)
from auto_detect_original_history import (
    _held, _digest, _history_root, _read_history_once, _archive_paths,
)
from auto_detect_original_history_positive import (
    preview_original_learning_independent_positive_locked,
)
from auto_detect_original_native_archive import _read_archive_plan
from auto_detect_original_v2_model import (
    _native_rebind_stable_snapshot, V2OriginalConfigRefused,
)
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import NATIVE_PENDING, QueueSafetyError
from auto_detect_debug_window import DebugWindowRefused
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_owner import (
    LearningGenerationProof, GenerationRefused,
    attest_learning_running_generation,
)

GUARD = "release-guard.json"


def _expected_guard(writer, proof, old_images, mirror_digest, postimages_sha):
    """Rebuild from original immutable prepared N + independent OLD images."""
    slot, prepared, archive = _archive_paths(writer, proof)
    uid = writer.receipts.uid
    archive_raw = _read(archive / "manifest.json", uid)
    prepared_raw = _read(prepared / "manifest.json", uid)
    rows = []
    for number, hostlist, pathname in proof.learning:
        raw = _read(prepared / f"{number:03d}.json", uid)
        row = json.loads(raw)
        pending = Path(row["old_pending_path"])
        match = NATIVE_PENDING.fullmatch(pending.name)
        old = old_images[number]
        if (raw != _canonical(row) or
                match is None or match[1] != proof.generation or
                int(match[2]) != number or
                pending.parent != writer.queue.pending or
                row.get("generation") != proof.generation or
                row.get("sequence") != 2 or
                row.get("kind") != "original-learning-third-pending-ack-N" or
                row.get("native_number") != number or
                row.get("hostlist") != hostlist or
                row.get("live_path") != pathname or
                row.get("old_size") != len(old) or
                row.get("old_sha256") != _digest(old) or
                type(row.get("old_device")) is not int or
                type(row.get("old_inode")) is not int or
                type(row.get("old_mtime_ns")) is not int or
                row["old_device"] < 0 or row["old_inode"] <= 0 or
                row.get("ack_authorized") is not False or
                row.get("unlink_authorized") is not False):
            raise V2OriginalConfigRefused("native_release_guard_prepared_N_unqualified")
        rows.append({
            "native_number": number, "hostlist": hostlist,
            "old_pending_path": str(pending),
            "archive_path": str(archive / f"{number:03d}.txt"),
            "old_device": row["old_device"],
            "old_inode": row["old_inode"],
            "old_size": len(old), "old_mtime_ns": row["old_mtime_ns"],
            "old_sha256": _digest(old),
            "prepared_receipt_sha256": _digest(raw),
        })
    return {
        "schema": 3, "kind": "original-learning-old-archive-release-guard",
        "generation": proof.generation, "sequence": 2,
        "owner_pid": proof.owner.pid, "owner_start": proof.owner.started,
        "operation_id": proof.operation_id,
        "native_map_sha256": proof.native_map_sha256,
        "old_mirror_manifest_sha256": mirror_digest,
        "archive_manifest_sha256": _digest(archive_raw),
        "prepared_manifest_sha256": _digest(prepared_raw),
        "all_final_postimages_sha256": postimages_sha,
        "profiles": rows,
        "source_independent_transaction_replay_available": False,
        "archive_unlink_authorized": False,
        "native_pending_ack_authorized": False,
        "generation_retired": False,
    }


def _scan_original_archive(writer, proof, rows, inspect):
    """Classify physical survivors while refusing changed names or inodes."""
    _, _, archive = _archive_paths(writer, proof)
    uid, gid = writer.receipts.uid, writer.queue.writer_gid
    _directory(archive, uid)
    names = set(os.listdir(archive))
    expected = {f"{number:03d}.txt" for number, _, _ in proof.learning}
    if ("manifest.json" not in names or "history" not in names or
            names - (expected | {"manifest.json", "history"})):
        raise V2OriginalConfigRefused("native_release_guard_archive_foreign_entry")
    _directory(archive / "history", uid)
    retained = []
    missing = []
    for row in rows:
        number = row["native_number"]
        pending = Path(row["old_pending_path"])
        archived = Path(row["archive_path"])
        if (pending.exists() or pending.is_symlink() or
                pending.parent != writer.queue.pending or
                archived.parent != archive or
                archived.name != f"{number:03d}.txt"):
            raise V2OriginalConfigRefused("native_release_guard_old_pending_reappeared")
        if archived.name not in names:
            if archived.exists() or archived.is_symlink():
                raise V2OriginalConfigRefused("native_release_guard_OLD_name_raced")
            missing.append(number)
            continue
        stat, content, _ = _native_rebind_stable_snapshot(
            archived, uid, gid, allowed_links=(1,))
        if ((stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) !=
                (row["old_device"], row["old_inode"], row["old_size"],
                 row["old_mtime_ns"]) or
                _digest(content) != row["old_sha256"] or
                inspect(archived, stat.st_dev, stat.st_ino,
                        owner=proof.owner, writer_gid=gid) is not FDState.DRAINED):
            raise V2OriginalConfigRefused("native_release_guard_old_survivor_changed")
        retained.append(number)
    if set(os.listdir(archive)) != names:
        raise V2OriginalConfigRefused("native_release_guard_archive_raced")
    return tuple(retained), tuple(missing)


def _read_guard_once(writer, proof, workspace, config_fd, config_path, attest,
                     inspect):
    _held(writer, proof, workspace, config_fd, config_path, attest)
    old, mirror = _read_history_once(writer, proof)
    positive = preview_original_learning_independent_positive_locked(
        writer, proof, workspace, config_fd=config_fd,
        config_path=config_path, attest=attest, inspect=inspect)
    if (positive.get("new_positive_debug_attribution_verified") is not True or
            positive.get("all_final_destinations_inode_pinned") is not True or
            positive.get("archive_unlink_authorized") is not False or
            positive.get("native_pending_ack_authorized") is not False):
        raise V2OriginalConfigRefused("native_release_guard_positive_unqualified")
    expected = _canonical(_expected_guard(
        writer, proof, old, mirror, positive["postimages_sha256"]))
    root = _history_root(writer, proof)
    raw = _read(root / GUARD, writer.receipts.uid)
    if raw != expected:
        raise V2OriginalConfigRefused("native_release_guard_immutable_plan_changed")
    rows = json.loads(expected)["profiles"]
    survivors, missing = _scan_original_archive(writer, proof, rows, inspect)
    return _digest(raw), positive, survivors, missing


def preview_original_learning_release_guard_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Source-independent diagnostic for all retained/partial/all missing."""
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if not callable(inspect):
            raise V2OriginalConfigRefused("native_release_guard_P2b_required")
        before = _read_guard_once(
            writer, proof, workspace, config_fd, config_path, attest, inspect)
        after = _read_guard_once(
            writer, proof, workspace, config_fd, config_path, attest, inspect)
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if before != after:
            raise V2OriginalConfigRefused("native_release_guard_after_read_raced")
        digest, positive, retained, missing = after
        return {
            "generation": proof.generation, "sequence": 2,
            "release_guard_sha256": digest,
            "retained_old_native_numbers": list(retained),
            "missing_old_native_numbers": list(missing),
            "old_archive_state": (
                "all-retained" if not missing else
                "all-missing" if not retained else "partially-missing"),
            "positive_event_count": positive["positive_event_count"],
            "all_final_destinations_inode_pinned": True,
            "new_positive_debug_attribution_verified": True,
            "old_bytes_source_independent": True,
            "source_independent_transaction_replay_available": False,
            "physical_old_archive_cleanup_authorized": False,
            "archive_unlink_authorized": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, OriginalLockRefused,
            QueueSafetyError, DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "native_release_guard_independent_preview_refused") from exc


def seal_original_learning_release_guard_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Write-once PRE-release guard with ALL OLD INODES PRESENT; NO unlink."""
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if not callable(inspect):
            raise V2OriginalConfigRefused("native_release_guard_P2b_required")
        before = _read_archive_plan(writer, proof)
        if before is None:
            raise V2OriginalConfigRefused("native_release_guard_original_archive_absent")
        _, _, archive = _archive_paths(writer, proof)
        if any(before[0][n][0] != archive / f"{n:03d}.txt"
               for n, _, _ in proof.learning):
            raise V2OriginalConfigRefused("native_release_guard_not_fully_archived")
        old, mirror = _read_history_once(writer, proof)
        positive = preview_original_learning_independent_positive_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        rows = _expected_guard(
            writer, proof, old, mirror, positive["postimages_sha256"])
        expected = _canonical(rows)
        present, absent = _scan_original_archive(
            writer, proof, rows["profiles"], inspect)
        if absent or len(present) != len(proof.learning):
            raise V2OriginalConfigRefused("native_release_guard_OLD_not_complete")
        _held(writer, proof, workspace, config_fd, config_path, attest)
        _write_once(_history_root(writer, proof), GUARD,
                    expected, writer.receipts.uid)
        result = preview_original_learning_release_guard_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (_read_archive_plan(writer, proof) != before or
                result["release_guard_sha256"] != _digest(expected) or
                result["old_archive_state"] != "all-retained"):
            raise V2OriginalConfigRefused("native_release_guard_source_raced")
        return result
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, OriginalLockRefused,
            QueueSafetyError, DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused("native_release_guard_seal_refused") from exc



def preview_original_learning_release_owner_live_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """STEP 15b3b: independently reattest the *running* native owner twice.

    The caller's attest() is an FD9 handoff check, not a substitute for
    FreeBSD process/census/argv/supervisor and terminal shared Apply proof.
    Always use the ORIGINAL schema-3 native owner attester; it requires
    the existing lifecycle lock and never accepts a detached proposal.
    A stopped/changed owner fails closed for this optional cleanup
    preflight, but must NOT block the operator's Stop/Restart/Apply path.

    This path writes nothing and explicitly cannot authorize physical
    old removal, native ACK or epoch retirement.
    """
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if not isinstance(proof, LearningGenerationProof):
            raise V2OriginalConfigRefused(
                "native_release_owner_schema3_required")
        current = attest_learning_running_generation()
        if current != proof:
            raise V2OriginalConfigRefused(
                "native_release_owner_not_original_running_generation")
        preview = preview_original_learning_release_guard_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        second = attest_learning_running_generation()
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (second != current or second != proof or
                preview.get("generation") != proof.generation or
                preview.get("source_independent_transaction_replay_available")
                is not False or
                preview.get("physical_old_archive_cleanup_authorized")
                is not False or
                preview.get("archive_unlink_authorized") is not False or
                preview.get("native_pending_ack_authorized") is not False or
                preview.get("generation_retired") is not False):
            raise V2OriginalConfigRefused(
                "native_release_owner_changed_across_guard")
        return {
            **preview,
            "original_running_owner_freshly_reattested": True,
            "owner_lifecycle_mutation_authorized": False,
            "source_independent_transaction_replay_available": False,
            "physical_old_archive_cleanup_authorized": False,
            "archive_unlink_authorized": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (GenerationRefused, OSError, ValueError, TypeError, KeyError,
            AttributeError, UnicodeError, ReceiptRefused,
            OriginalLockRefused, QueueSafetyError,
            DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "native_release_original_running_owner_unavailable") from exc


def main():
    raise SystemExit("Original OLD-archive release guard is not a worker")


if __name__ == "__main__":
    main()
