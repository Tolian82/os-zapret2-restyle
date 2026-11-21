#!/usr/bin/env python3
"""Original FD9 native pending archival handoff, never final unlink/ACK.

The same original P2a/GUI and inherited Config FD4 own a durable one-shot
archive plan in cursor-chain-v2/00000002. Actual old bytes are MOVED (not
deleted) from original pending to root-private generation archive, retaining
the SAME device/inode for original P1/second/third source replay.

This is an import-only phase, NOT wired to minute/Apply/launcher. There is
no independent queue, witness database, Config writer, service stop, packet
rule change, native producer reinitialization or physical archive unlink.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from auto_detect_epoch_receipts import (
    _canonical, _directory, _read, _sync, _write_once, ReceiptRefused,
)
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_lock_handoff import (
    CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
)
from auto_detect_queue import QueueSafetyError, NATIVE_PENDING


def _archive_paths(writer, proof):
    slot = (writer.receipts.root / proof.generation /
            "cursor-chain-v2" / "00000002")
    return slot, slot / "pending-ack-prepare", slot / "pending-ack-archive"


def _read_archive_plan(writer, proof):
    """Verify original immutable prepared-N identities and one archive plan.

    Returns (per-N selected physical path, exact original prepared records)
    only after the manifest is published. A partial archive folder before
    manifest is recoverable only when it has NO moved old inode.
    """
    from auto_detect_original_v2_model import (
        V2OriginalConfigRefused, _native_rebind_stable_snapshot,
    )
    slot, prepared, archive = _archive_paths(writer, proof)
    if not archive.exists() and not archive.is_symlink():
        return None
    uid = writer.receipts.uid
    _directory(slot, uid)
    _directory(archive, uid)
    # An os.rename() cannot be an atomic source-preserving transition
    # across filesystems. Reject a separate/mounted epoch archive
    # BEFORE attempting any per-N move, never resort to copy/unlink.
    if archive.stat().st_dev != writer.queue.pending.stat().st_dev:
        raise V2OriginalConfigRefused("native_archive_cross_device_refused")
    names = set(os.listdir(archive))
    expected_archives = {f"{n:03d}.txt" for n, _, _ in proof.learning}
    if names - (expected_archives | {"manifest.json"}):
        raise V2OriginalConfigRefused("native_archive_foreign_directory_entry")
    if "manifest.json" not in names:
        if names:
            raise V2OriginalConfigRefused("native_archive_move_before_manifest")
        return None
    _directory(prepared, uid)
    expected_prep = {f"{n:03d}.json" for n, _, _ in proof.learning}
    if set(os.listdir(prepared)) != expected_prep | {"manifest.json"}:
        raise V2OriginalConfigRefused("native_archive_prepared_N_missing")
    progress_raw = _read(slot / "cursor-progress.json", uid)
    source_raw = _read(slot / "intent.json", uid)
    progress = json.loads(progress_raw)
    if (progress_raw != _canonical(progress) or
            progress.get("kind") !=
            "original-learning-third-cursor-progress" or
            progress.get("generation") != proof.generation or
            progress.get("sequence") != 2 or
            progress.get("native_pending_ack_authorized") is not False or
            progress.get("native_cleanup_authorized") is not False or
            progress.get("source_intent_sha256") !=
            hashlib.sha256(source_raw).hexdigest()):
        raise V2OriginalConfigRefused("native_archive_progress_unqualified")
    progress_sha = hashlib.sha256(progress_raw).hexdigest()
    original_sha = hashlib.sha256(source_raw).hexdigest()
    prepared_raw = _read(prepared / "manifest.json", uid)
    prepared_manifest = json.loads(prepared_raw)
    packed = []
    current = {}
    expected_lines = set()
    for number, hostlist, live in proof.learning:
        nfile = f"{number:03d}.json"
        old_raw = _read(prepared / nfile, uid)
        row = json.loads(old_raw)
        native_raw = _read(slot / "native" / nfile, uid)
        native = json.loads(native_raw)
        cursor = native["cursor"]
        # The original pending identity is read from the immutable
        # prepared receipt and checked against the ENTIRE native-name
        # grammar, not a permissive prefix or caller-derived basename.
        pending = Path(row["old_pending_path"])
        match = NATIVE_PENDING.fullmatch(pending.name)
        if (old_raw != _canonical(row) or
                match is None or match[1] != proof.generation or
                int(match[2]) != number or
                row.get("kind") != "original-learning-third-pending-ack-N" or
                row.get("schema") != 3 or
                row.get("sequence") != 2 or
                row.get("generation") != proof.generation or
                row.get("native_number") != number or
                row.get("hostlist") != hostlist or
                row.get("live_path") != live or
                row.get("third_cursor_progress_sha256") != progress_sha or
                row.get("third_source_intent_sha256") != original_sha or
                row.get("ack_authorized") is not False or
                row.get("unlink_authorized") is not False or
                pending.parent != writer.queue.pending or
                native_raw != _canonical(native) or
                native.get("kind") != "original-learning-third-native-cut" or
                native.get("generation") != proof.generation or
                native.get("native_number") != number or
                cursor.get("old_path") != str(pending) or
                cursor.get("new_path") != live or
                cursor.get("old_device") != row.get("old_device") or
                cursor.get("old_inode") != row.get("old_inode") or
                cursor.get("old_end") != row.get("old_size") or
                cursor.get("old_end_sha256") != row.get("old_sha256")):
            raise V2OriginalConfigRefused("native_archive_foreign_source_or_N")
        packed.append(old_raw)
        archived = archive / f"{number:03d}.txt"
        if archived.name in names:
            if pending.exists() or pending.is_symlink():
                raise V2OriginalConfigRefused(
                    "native_archive_both_old_names_present")
            physical = archived
            expected_lines.add(archived.name)
        else:
            if not pending.exists() or pending.is_symlink():
                raise V2OriginalConfigRefused(
                    "native_archive_old_missing_without_archived_inode")
            physical = pending
        stat_old, data, _ = _native_rebind_stable_snapshot(
            physical, uid, writer.queue.writer_gid, allowed_links=(1,))
        if ((stat_old.st_dev, stat_old.st_ino, stat_old.st_size,
             stat_old.st_mtime_ns) !=
            (row["old_device"], row["old_inode"], row["old_size"],
             row["old_mtime_ns"]) or
                hashlib.sha256(data).hexdigest() != row["old_sha256"] or
                (physical == pending and
                 stat_old.st_ctime_ns != row["old_ctime_ns"])):
            raise V2OriginalConfigRefused(
                "native_archive_old_image_or_inode_changed")
        current[number] = (physical, row)

    expected_prepared = {
        "schema": 3,
        "kind": "original-learning-third-pending-ack-prepared",
        "generation": proof.generation, "sequence": 2,
        "owner_pid": proof.owner.pid,
        "owner_start": proof.owner.started,
        "operation_id": proof.operation_id,
        "native_map_sha256": proof.native_map_sha256,
        "third_cursor_progress_sha256": progress_sha,
        "third_source_intent_sha256": original_sha,
        "profiles_count": len(proof.learning),
        "profiles_sha256": hashlib.sha256(b"".join(
            hashlib.sha256(raw).digest() for raw in packed)).hexdigest(),
        "ack_authorized": False,
        "unlink_authorized": False,
        "generation_retired": False,
    }
    if (prepared_raw != _canonical(prepared_manifest) or
            prepared_manifest != expected_prepared):
        raise V2OriginalConfigRefused("native_archive_prepared_manifest_drift")
    expected_plan = {
        "schema": 3,
        "kind": "original-learning-third-pending-archive-plan",
        "generation": proof.generation, "sequence": 2,
        "owner_pid": proof.owner.pid,
        "owner_start": proof.owner.started,
        "operation_id": proof.operation_id,
        "native_map_sha256": proof.native_map_sha256,
        "third_cursor_progress_sha256": progress_sha,
        "prepared_manifest_sha256":
            hashlib.sha256(prepared_raw).hexdigest(),
        "profiles_count": len(proof.learning),
        "profiles_sha256": prepared_manifest["profiles_sha256"],
        "archive_relocation": True,
        "native_pending_ack_authorized": False,
        "archive_unlink_authorized": False,
        "generation_retired": False,
    }
    plan_raw = _read(archive / "manifest.json", uid)
    if plan_raw != _canonical(expected_plan):
        raise V2OriginalConfigRefused("native_archive_manifest_changed")
    # Re-list only AFTER every inode has been opened and inspected:
    # the original P2a serializes the owner, but a native writer does
    # not obey that flock. Reject path or manifest swaps mid-read.
    if (names != expected_lines | {"manifest.json"} or
            set(os.listdir(archive)) != names or
            _read(archive / "manifest.json", uid) != plan_raw or
            _read(prepared / "manifest.json", uid) != prepared_raw):
        raise V2OriginalConfigRefused("native_archive_orphan_or_raced_inode")
    return current, expected_plan


def _move_original_pending(source: Path, archived: Path) -> None:
    """Crash point: filesystem rename, fsync destination and source dirs."""
    os.rename(source, archived)
    _sync(archived.parent)
    _sync(source.parent)


def archive_original_learning_pending_locked(
        writer, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """Original P2a/FD9 protected, crash-resumable preservation of all N.

    It performs an actual MOVE into the original protected journal, never
    an unlink. Both paths remain root-only by their parent directory.
    Every original old byte and original inode are retained, so a crash
    after any individual native rename resumes from the same manifest.
    All this remains import-only, not called by installed production flows.
    """
    from auto_detect_original_v2_model import (
        V2OriginalConfigRefused,
        _native_rebind_stable_snapshot,
        prepare_original_learning_third_pending_ack_locked,
        preview_original_learning_third_pending_retirement_locked,
        seal_original_learning_third_progress_locked,
    )
    from auto_detect_destination_commit import DestinationCommit
    from auto_detect_owner import LearningGenerationProof
    from auto_detect_queue import NATIVE_PENDING

    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or
            not getattr(writer, "_gui_held", False) or
            not isinstance(workspace, Path) or not workspace.is_absolute()
            or workspace.name != proof.generation or
            not isinstance(config_path, Path) or
            not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and (
                config_path != CONFIG_PATH or writer.receipts.uid != 0 or
                writer.queue.uid != 0)) or attest() != proof):
        raise V2OriginalConfigRefused("native_archive_original_fd4_fd9_required")

    def held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH
            else writer.receipts.uid)
        if attest() != proof:
            raise V2OriginalConfigRefused("native_archive_owner_changed")

    slot, _, archive = _archive_paths(writer, proof)
    try:
        held()
        if not archive.exists() and not archive.is_symlink():
            # The entire original P1+third-cursor pipeline and every
            # pending N are re-attested BEFORE creating archive intent.
            prepare_original_learning_third_pending_ack_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect)
            held()
            archive.mkdir(mode=0o700)
            _sync(slot)
        elif archive.is_symlink():
            raise V2OriginalConfigRefused("native_archive_symlink_folder")
        _directory(archive, writer.receipts.uid)
        if not (archive / "manifest.json").exists():
            if os.listdir(archive):
                raise V2OriginalConfigRefused("native_archive_partial_unqualified")
            prepared = prepare_original_learning_third_pending_ack_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect)
            prepared_raw = _read(
                slot / "pending-ack-prepare" / "manifest.json",
                writer.receipts.uid)
            # Copy only the original sealed, fully source-bound fields.
            plan = {
                "schema": 3,
                "kind": "original-learning-third-pending-archive-plan",
                "generation": proof.generation, "sequence": 2,
                "owner_pid": proof.owner.pid,
                "owner_start": proof.owner.started,
                "operation_id": proof.operation_id,
                "native_map_sha256": proof.native_map_sha256,
                "third_cursor_progress_sha256":
                    hashlib.sha256(_read(
                        slot / "cursor-progress.json",
                        writer.receipts.uid)).hexdigest(),
                "prepared_manifest_sha256":
                    hashlib.sha256(prepared_raw).hexdigest(),
                "profiles_count": prepared["profiles_count"],
                "profiles_sha256": json.loads(
                    prepared_raw)["profiles_sha256"],
                "archive_relocation": True,
                "native_pending_ack_authorized": False,
                "archive_unlink_authorized": False,
                "generation_retired": False,
            }
            held()
            _write_once(
                archive, "manifest.json", _canonical(plan),
                writer.receipts.uid)
        # Once a move starts, original prepare() cannot be re-run:
        # it deliberately requires every OLD inode still in pending.
        state = _read_archive_plan(writer, proof)
        if state is None:
            raise V2OriginalConfigRefused("native_archive_missing_manifest")
        previous = state[1]
        for number, hostlist, _ in proof.learning:
            held()
            known = _read_archive_plan(writer, proof)
            if known is None or known[1] != previous:
                raise V2OriginalConfigRefused("native_archive_plan_changed")
            physical, prepared_row = known[0][number]
            original = Path(prepared_row["old_pending_path"])
            archived = archive / f"{number:03d}.txt"
            if physical == archived:
                continue
            if (physical != original or
                    NATIVE_PENDING.fullmatch(original.name) is None or
                    original.parent != writer.queue.pending):
                raise V2OriginalConfigRefused(
                    "native_archive_wrong_pending_source")
            # The normal original third P1/managed source owner and all-N
            # FD9/P2b must still be qualified before EACH individual move.
            progress = seal_original_learning_third_progress_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect)
            preview = preview_original_learning_third_pending_retirement_locked(
                writer, proof, workspace, config_fd=config_fd,
                config_path=config_path, attest=attest, inspect=inspect)
            matching = [row for row in preview["profiles"]
                        if row["native_number"] == number]
            if (progress["progress_sha256"] !=
                    previous["third_cursor_progress_sha256"] or
                    len(matching) != 1 or
                    matching[0]["status"] !=
                    "covered-old-pending-no-ACK" or
                    matching[0]["unprocessed_old_bytes"] != 0 or
                    preview["native_pending_ack_authorized"] is not False):
                raise V2OriginalConfigRefused("native_archive_unprocessed_old")
            st, data, identity = _native_rebind_stable_snapshot(
                original, writer.receipts.uid, writer.queue.writer_gid,
                allowed_links=(1,))
            if ((st.st_dev, st.st_ino, st.st_size, st.st_ctime_ns,
                 st.st_mtime_ns) !=
                (prepared_row["old_device"], prepared_row["old_inode"],
                 prepared_row["old_size"], prepared_row["old_ctime_ns"],
                 prepared_row["old_mtime_ns"]) or
                    hashlib.sha256(data).hexdigest() !=
                    prepared_row["old_sha256"] or
                    inspect(original, st.st_dev, st.st_ino,
                            owner=proof.owner,
                            writer_gid=writer.queue.writer_gid)
                    is not FDState.DRAINED):
                raise V2OriginalConfigRefused("native_archive_last_FD_or_old_drift")
            fresh, fresh_bytes, fresh_identity = _native_rebind_stable_snapshot(
                original, writer.receipts.uid, writer.queue.writer_gid,
                allowed_links=(1,))
            if (identity != fresh_identity or
                    hashlib.sha256(fresh_bytes).hexdigest() !=
                    prepared_row["old_sha256"] or
                    (fresh.st_dev, fresh.st_ino) != (st.st_dev, st.st_ino) or
                    archive.joinpath(f"{number:03d}.txt").exists() or
                    archive.joinpath(f"{number:03d}.txt").is_symlink()):
                raise V2OriginalConfigRefused("native_archive_race_before_move")
            held()
            _move_original_pending(original, archived)
            moved = _read_archive_plan(writer, proof)
            if moved is None or moved[1] != previous or (
                    moved[0][number][0] != archived):
                raise V2OriginalConfigRefused("native_archive_postmove_not_proven")
        held()
        final = _read_archive_plan(writer, proof)
        if (final is None or final[1] != previous or
                any(final[0][number][0] !=
                    archive / f"{number:03d}.txt"
                    for number, _, _ in proof.learning) or
                seal_original_learning_third_progress_locked(
                    writer, proof, workspace, config_fd=config_fd,
                    config_path=config_path, attest=attest,
                    inspect=inspect)["progress_sha256"] !=
                    previous["third_cursor_progress_sha256"]):
            raise V2OriginalConfigRefused("native_archive_final_replay_unqualified")
        return {
            "generation": proof.generation, "sequence": 2,
            "profiles_archived": len(proof.learning),
            "pending_relocated": True,
            "pending_bytes_preserved": True,
            "native_pending_ack_authorized": False,
            "archive_unlink_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, ReceiptRefused, OriginalLockRefused,
            QueueSafetyError) as exc:
        raise V2OriginalConfigRefused("native_archive_original_transition_refused") from exc


def main() -> int:
    raise SystemExit("Native pending archive is NOT a standalone worker")


if __name__ == "__main__":
    main()
