#!/usr/bin/env python3
"""STEP 15a: source-independent OLD bytes, NOT a post-unlink transaction replay.

One root-private, write-once image per native N lives inside the SAME original
pending-ack-archive. Each chunk uses the existing fail-closed receipt
writer; an all-N manifest is published LAST. It is intentionally import-only.
No source path is unlinked, no ACK is granted, no Config/GUI/IPFW is mutated.
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
from auto_detect_original_lock_handoff import (
    CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
)
from auto_detect_original_native_archive import (
    _archive_paths, _read_archive_plan,
    preview_original_learning_archive_release_locked,
)
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, _native_rebind_stable_snapshot,
)
from auto_detect_owner import LearningGenerationProof
from auto_detect_destination_commit import DestinationCommit
from auto_detect_queue import QueueSafetyError

# Keep every raw chunk below the original immutable receipt 16-KiB limit.
CHUNK = 8192


def _held(writer, proof, workspace, config_fd, config_path, attest):
    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or
            not getattr(writer, "_gui_held", False) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or
            (sys.platform.startswith("freebsd") and (
                config_path != CONFIG_PATH or writer.receipts.uid != 0 or
                writer.queue.uid != 0)) or attest() != proof):
        raise V2OriginalConfigRefused("native_history_original_fd4_fd9_required")
    assert_inherited_config_fd(
        config_fd, config_path,
        owner_uid=None if config_path == CONFIG_PATH else writer.receipts.uid)
    if attest() != proof:
        raise V2OriginalConfigRefused("native_history_original_owner_changed")


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _history_root(writer, proof):
    return _archive_paths(writer, proof)[2] / "history"


def _image_metadata(writer, proof, number, hostlist, old):
    slot, _, archive = _archive_paths(writer, proof)
    uid = writer.receipts.uid
    prepared_raw = _read(slot / "pending-ack-prepare" /
                         f"{number:03d}.json", uid)
    prepared = json.loads(prepared_raw)
    if (prepared_raw != _canonical(prepared) or
            prepared.get("generation") != proof.generation or
            prepared.get("native_number") != number or
            prepared.get("hostlist") != hostlist or
            prepared.get("old_sha256") != _digest(old) or
            prepared.get("old_size") != len(old) or
            prepared.get("ack_authorized") is not False or
            prepared.get("unlink_authorized") is not False):
        raise V2OriginalConfigRefused("native_history_prepared_source_mismatch")
    return {
        "schema": 3, "kind": "original-learning-independent-old-image",
        "generation": proof.generation, "sequence": 2,
        "native_number": number, "hostlist": hostlist,
        "prepared_receipt_sha256": _digest(prepared_raw),
        "old_device": prepared["old_device"],
        "old_inode": prepared["old_inode"],
        "old_size": len(old), "old_sha256": _digest(old),
        "chunk_bytes": CHUNK,
        "chunks": (len(old) + CHUNK - 1) // CHUNK,
        "archive_unlink_authorized": False,
        "generation_retired": False,
    }


def _read_history_once(writer, proof):
    """Rebuild bytes from sealed receipts without opening ANY old inode."""
    slot, prepared_folder, archive = _archive_paths(writer, proof)
    uid = writer.receipts.uid
    root = _history_root(writer, proof)
    _directory(root, uid)
    _directory(archive, uid)
    _directory(prepared_folder, uid)
    expected = {f"{n:03d}" for n, _, _ in proof.learning}
    available = {"manifest.json"}
    if (root / "postimages.json").exists() or (root / "postimages.json").is_symlink():
        _read(root / "postimages.json", uid)
        available.add("postimages.json")
    if (root / "release-guard.json").exists() or (root / "release-guard.json").is_symlink():
        _read(root / "release-guard.json", uid)
        available.add("release-guard.json")
    if set(os.listdir(root)) != expected | available:
        raise V2OriginalConfigRefused("native_history_unsealed_or_foreign_N")
    archive_manifest = _read(archive / "manifest.json", uid)
    prepared_manifest = _read(prepared_folder / "manifest.json", uid)
    progress = _read(slot / "cursor-progress.json", uid)
    source = _read(slot / "intent.json", uid)
    # Independently attest the original immutable owner/source chain, not
    # merely the freshly generated mirror manifest. None of this opens an
    # OLD inode and all comparisons remain mandatory after physical unlink.
    archive_plan = json.loads(archive_manifest)
    prepared_plan = json.loads(prepared_manifest)
    cursor_progress = json.loads(progress)
    source_intent = json.loads(source)
    if (archive_manifest != _canonical(archive_plan) or
            prepared_manifest != _canonical(prepared_plan) or
            progress != _canonical(cursor_progress) or
            source != _canonical(source_intent) or
            archive_plan.get("kind") !=
            "original-learning-third-pending-archive-plan" or
            prepared_plan.get("kind") !=
            "original-learning-third-pending-ack-prepared" or
            cursor_progress.get("kind") !=
            "original-learning-third-cursor-progress" or
            source_intent.get("kind") !=
            "original-learning-third-slot-prepared" or
            any(row.get("generation") != proof.generation or
                row.get("sequence") != 2
                for row in (archive_plan, prepared_plan, cursor_progress,
                            source_intent)) or
            any(row.get("owner_pid") != proof.owner.pid or
                row.get("owner_start") != proof.owner.started or
                row.get("native_map_sha256") != proof.native_map_sha256
                for row in (archive_plan, prepared_plan)) or
            archive_plan.get("prepared_manifest_sha256") !=
            _digest(prepared_manifest) or
            archive_plan.get("third_cursor_progress_sha256") !=
            _digest(progress) or
            prepared_plan.get("third_cursor_progress_sha256") !=
            _digest(progress) or
            cursor_progress.get("source_intent_sha256") != _digest(source) or
            archive_plan.get("profiles_sha256") !=
            prepared_plan.get("profiles_sha256") or
            archive_plan.get("archive_unlink_authorized") is not False or
            prepared_plan.get("unlink_authorized") is not False or
            cursor_progress.get("native_pending_ack_authorized") is not False):
        raise V2OriginalConfigRefused("native_history_original_chain_unqualified")
    images = {}
    packed = []
    prepared_receipts = []
    for number, hostlist, _ in proof.learning:
        folder = root / f"{number:03d}"
        _directory(folder, uid)
        receipt_raw = _read(folder / "receipt.json", uid)
        receipt = json.loads(receipt_raw)
        chunks = receipt.get("chunks")
        if (type(chunks) is not int or chunks < 0 or chunks > 512 or
                receipt.get("chunk_bytes") != CHUNK):
            raise V2OriginalConfigRefused("native_history_chunk_count_refused")
        names = {f"{i:05d}.bin" for i in range(chunks)}
        if set(os.listdir(folder)) != names | {"receipt.json"}:
            raise V2OriginalConfigRefused("native_history_foreign_or_missing_chunk")
        old = b"".join(_read(folder / name, uid) for name in sorted(names))
        expected_row = _image_metadata(writer, proof, number, hostlist, old)
        if (receipt_raw != _canonical(receipt) or receipt != expected_row or
                len(old) > 512 * CHUNK or
                (len(old) + CHUNK - 1) // CHUNK != chunks):
            raise V2OriginalConfigRefused("native_history_source_image_changed")
        images[number] = old
        prepared_receipts.append(_read(prepared_folder / f"{number:03d}.json", uid))
        packed.append({
            "native_number": number,
            "receipt_sha256": _digest(receipt_raw),
        })
    if (prepared_plan.get("profiles_count") != len(proof.learning) or
            archive_plan.get("profiles_count") != len(proof.learning) or
            prepared_plan.get("profiles_sha256") != _digest(b"".join(
                hashlib.sha256(raw).digest() for raw in prepared_receipts))):
        raise V2OriginalConfigRefused("native_history_prepared_all_N_unqualified")
    manifest = {
        "schema": 3, "kind": "original-learning-independent-history",
        "generation": proof.generation, "sequence": 2,
        "owner_pid": proof.owner.pid,
        "owner_start": proof.owner.started,
        "operation_id": proof.operation_id,
        "native_map_sha256": proof.native_map_sha256,
        "archive_manifest_sha256": _digest(archive_manifest),
        "prepared_manifest_sha256": _digest(prepared_manifest),
        "third_cursor_progress_sha256": _digest(progress),
        "third_source_intent_sha256": _digest(source),
        "profiles": packed,
        "archive_unlink_authorized": False,
        "native_pending_ack_authorized": False,
        "generation_retired": False,
        "source_independent_transaction_replay_available": False,
    }
    manifest_raw = _read(root / "manifest.json", uid)
    if manifest_raw != _canonical(manifest):
        raise V2OriginalConfigRefused("native_history_manifest_not_source_bound")
    if (set(os.listdir(root)) != expected | available or
            _read(archive / "manifest.json", uid) != archive_manifest or
            _read(prepared_folder / "manifest.json", uid) != prepared_manifest or
            _read(slot / "cursor-progress.json", uid) != progress or
            _read(slot / "intent.json", uid) != source):
        raise V2OriginalConfigRefused("native_history_manifest_raced")
    return images, _digest(manifest_raw)


def read_original_learning_independent_history_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
):
    """Only OLD historical bytes; does NOT validate/repair committed GUI state.

    This reader intentionally never invokes original first/second/third replay
    or _read_archive_plan: those need the old inode. A future post-unlink
    recovery must separately prove destination WAL, P1/Found/managed and NEW
    live/debug ownership before any ACK or physical archive unlink.
    """
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        first = _read_history_once(writer, proof)
        second = _read_history_once(writer, proof)
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if second != first:
            raise V2OriginalConfigRefused("native_history_all_N_raced")
        return {
            "generation": proof.generation, "sequence": 2,
            "old_images": first[0], "manifest_sha256": first[1],
            "old_bytes_source_independent": True,
            "source_independent_transaction_replay_available": False,
            "archive_unlink_authorized": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, OriginalLockRefused,
            QueueSafetyError) as exc:
        raise V2OriginalConfigRefused("native_history_replay_refused") from exc


def seal_original_learning_independent_history_locked(
        writer, proof, workspace, *, config_fd, config_path, attest, inspect,
):
    """Write-once chunked pre-unlink mirror, manifest LAST, under original FD9.

    Original archive and all N old inodes MUST still be present. A crash after a durable chunk is resumable through identical chunks;
    a torn temporary receipt refuses until safely investigated.
    """
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        preview = preview_original_learning_archive_release_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        if (preview.get("archive_unlink_authorized") is not False or
                preview.get("source_independent_replay_available") is not False):
            raise V2OriginalConfigRefused("native_history_archive_gate_changed")
        before = _read_archive_plan(writer, proof)
        if before is None:
            raise V2OriginalConfigRefused("native_history_no_original_archive")
        _, _, archive = _archive_paths(writer, proof)
        uid = writer.receipts.uid
        root = _history_root(writer, proof)
        if not root.exists() and not root.is_symlink():
            root.mkdir(mode=0o700)
            _sync(archive)
        _directory(root, uid)
        for number, hostlist, _ in proof.learning:
            physical, prepared = before[0][number]
            if physical != archive / f"{number:03d}.txt":
                raise V2OriginalConfigRefused("native_history_not_fully_archived")
            st, old, _ = _native_rebind_stable_snapshot(
                physical, uid, writer.queue.writer_gid, allowed_links=(1,))
            if ((st.st_dev, st.st_ino, st.st_size) !=
                    (prepared["old_device"], prepared["old_inode"],
                     prepared["old_size"]) or
                    _digest(old) != prepared["old_sha256"]):
                raise V2OriginalConfigRefused("native_history_old_inode_changed")
            folder = root / f"{number:03d}"
            if not folder.exists() and not folder.is_symlink():
                folder.mkdir(mode=0o700)
                _sync(root)
            _directory(folder, uid)
            for i in range((len(old) + CHUNK - 1) // CHUNK):
                _write_once(folder, f"{i:05d}.bin",
                            old[i*CHUNK:(i+1)*CHUNK], uid)
            receipt = _image_metadata(writer, proof, number, hostlist, old)
            if set(os.listdir(folder)) != (
                    {f"{i:05d}.bin" for i in range(receipt["chunks"])} |
                    {"receipt.json"} if (folder / "receipt.json").exists()
                    else {f"{i:05d}.bin" for i in range(receipt["chunks"])}):
                raise V2OriginalConfigRefused("native_history_unexpected_partial_N")
            _write_once(folder, "receipt.json", _canonical(receipt), uid)
        # No source image may have changed during the multi-N copy. In
        # particular the original native writer is not serialized by FD9.
        if _read_archive_plan(writer, proof) != before:
            raise V2OriginalConfigRefused("native_history_old_changed_during_copy")
        expected = {f"{n:03d}" for n, _, _ in proof.learning}
        if set(os.listdir(root)) - (expected | {"manifest.json", "postimages.json", "release-guard.json"}):
            raise V2OriginalConfigRefused("native_history_foreign_folder")
        slot, prepared_folder, archive = _archive_paths(writer, proof)
        packed = []
        for n, _, _ in proof.learning:
            raw = _read(root / f"{n:03d}" / "receipt.json", uid)
            packed.append({"native_number": n, "receipt_sha256": _digest(raw)})
        manifest = {
            "schema": 3, "kind": "original-learning-independent-history",
            "generation": proof.generation, "sequence": 2,
            "owner_pid": proof.owner.pid, "owner_start": proof.owner.started,
            "operation_id": proof.operation_id,
            "native_map_sha256": proof.native_map_sha256,
            "archive_manifest_sha256": _digest(_read(archive / "manifest.json", uid)),
            "prepared_manifest_sha256": _digest(
                _read(prepared_folder / "manifest.json", uid)),
            "third_cursor_progress_sha256": _digest(
                _read(slot / "cursor-progress.json", uid)),
            "third_source_intent_sha256": _digest(
                _read(slot / "intent.json", uid)),
            "profiles": packed,
            "archive_unlink_authorized": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
            "source_independent_transaction_replay_available": False,
        }
        _held(writer, proof, workspace, config_fd, config_path, attest)
        _write_once(root, "manifest.json", _canonical(manifest), uid)
        result = read_original_learning_independent_history_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest)
        if (_read_archive_plan(writer, proof) != before or
                result["manifest_sha256"] != _digest(_canonical(manifest))):
            raise V2OriginalConfigRefused("native_history_postseal_source_raced")
        return {
            "generation": proof.generation, "sequence": 2,
            "profiles_sealed": len(proof.learning),
            "old_bytes_source_independent": True,
            "source_independent_transaction_replay_available": False,
            "archive_unlink_authorized": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, OriginalLockRefused,
            QueueSafetyError) as exc:
        raise V2OriginalConfigRefused("native_history_seal_refused") from exc


def main():
    raise SystemExit("Independent history is not a standalone worker")


if __name__ == "__main__":
    main()
