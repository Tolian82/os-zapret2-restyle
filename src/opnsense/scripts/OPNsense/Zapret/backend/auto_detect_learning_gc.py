#!/usr/bin/env python3
"""Bounded schema3 epoch history reclamation under the original FD9/P2a.

The existing EpochReceipts.prune_completed is the single history owner.
Only a finished immutable terminal ACK/intent/ready with physically sealed
old N/debug archives may become a .gc3- tombstone. An interrupted deletion
resumes only from that protected tombstone; it never inspects or deletes
working producer names, Found, managed or Config.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import re
import stat

from auto_detect_cursor_chain import CursorChain
from auto_detect_epoch_receipts import (
    EpochReceipts, ReceiptRefused, HEX32, _canonical, _directory, _read, _sync,
)
from auto_detect_fd import OwnerToken
from auto_detect_learning_retirement import (
    RETIRE_DIR, INTENT, READY, _entry, _expected, _image, MAX_NATIVE,
)
from auto_detect_owner import LearningGenerationProof
from auto_detect_queue import DurableInbox
from shared_apply_seal import WORK

RECEIPTS = frozenset({"pretraffic.json", "epoch.json"})
ARCHIVE_RECEIPTS = frozenset({INTENT, READY})


def _proof(receipts: EpochReceipts, generation: str) -> LearningGenerationProof:
    folder = receipts._generation(generation, create=False)
    raw = _read(folder / "epoch.json", receipts.uid)
    try:
        epoch = json.loads(raw)
        if (raw != _canonical(epoch) or type(epoch) is not dict or
                set(epoch) != {
                    "schema", "kind", "generation", "operation_id",
                    "owner_candidate_sha256", "final_args_sha256",
                    "native_map_sha256", "pretraffic_sha256", "owner_pid",
                    "owner_start", "owner_executable", "files",
                    "learning", "ack_authorized",
                } or epoch["schema"] != 3 or
                epoch["kind"] != "original-native-learning-epoch" or
                epoch["generation"] != generation or
                epoch["operation_id"] != generation or
                epoch["ack_authorized"] is not False or
                type(epoch["learning"]) is not list or
                not 1 <= len(epoch["learning"]) <= 255):
            raise ReceiptRefused("historical_learning_epoch_not_qualified")
        learning = tuple(
            (row["native_number"], row["hostlist"], row["path"])
            for row in epoch["learning"])
        return LearningGenerationProof(
            OwnerToken(epoch["owner_pid"], epoch["owner_start"],
                       epoch["owner_executable"]),
            generation, generation, epoch["owner_candidate_sha256"],
            epoch["final_args_sha256"], epoch["native_map_sha256"], learning)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ReceiptRefused("historical_learning_epoch_not_qualified") from exc


def qualified_completed_learning(receipts: EpochReceipts, queue: DurableInbox,
                                 generation: str, *,
                                 expected_candidate: str | None = None,
                                 expected_ready_sha256: str | None = None) -> int:
    """Return ordering timestamp only for an exact completed schema3 source.

    This does not attest a *running* historical PID. The original epoch
    and sealed release, full dynamic cursor chain, terminal intent/ready and
    archived physical bytes are checked read-only while current FD9/P2a owns
    the filesystem. An unfinished/foreign/changed archive is never pruned.
    """
    if (not isinstance(receipts, EpochReceipts) or
            not isinstance(queue, DurableInbox) or not queue._held or
            queue.uid != receipts.uid or queue.writer_gid != receipts.writer_gid or
            not isinstance(generation, str) or not HEX32.fullmatch(generation)):
        raise ReceiptRefused("historical_learning_original_queue_required")
    folder = receipts._generation(generation, create=False)
    if (_entry(folder / "cursor-chain-v2.next") or
            _entry(folder / "cursor-chain-v2.old") or
            set(os.listdir(folder)) - (
                RECEIPTS | {"cursor-chain-v2", RETIRE_DIR})):
        raise ReceiptRefused("historical_learning_unfinished_rollover")
    proof = _proof(receipts, generation)
    if expected_candidate is not None and proof.owner_candidate_sha256 != expected_candidate:
        raise ReceiptRefused("historical_learning_candidate_changed")
    # This uses the same historical sealed release/zero cut and original
    # receipt parser as the current source, without an old live PID.
    tip = CursorChain(receipts, queue).learning_tip(
        proof, WORK / generation, reclaim_unsealed=False)
    if (tip["slot"] is not None or tip["intent"] is not None or
            tip.get("debug_cut_pending") is not None or
            tip["root"].parent != folder or
            set(tip["state"]) != {row[0] for row in proof.learning}):
        raise ReceiptRefused("historical_learning_unacknowledged_tip")
    expected = _expected(proof, tip)
    archive = folder / RETIRE_DIR
    _directory(archive, receipts.uid)
    raw = _read(archive / INTENT, receipts.uid)
    ready_raw = _read(archive / READY, receipts.uid)
    try:
        plan = json.loads(raw)
        ready = json.loads(ready_raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ReceiptRefused("historical_learning_corrupt_retirement") from exc
    if (raw != _canonical(plan) or
            set(plan) != set(expected) | {"sources"} or
            {k: v for k, v in plan.items() if k != "sources"} != expected or
            type(plan["sources"]) is not list or
            len(plan["sources"]) != len(expected["cursors"]) or
            ready_raw != _canonical(ready) or
            ready != {
                "schema": 3,
                "kind": "original-stopped-learning-terminal-ready",
                "generation": generation,
                "intent_sha256": hashlib.sha256(raw).hexdigest(),
                "cycle": tip["cycle"],
                "sequence": tip["sequence"],
                "previous_ack_sha256": tip["previous_ack_sha256"],
                "ack_authorized": False,
            }):
        raise ReceiptRefused("historical_learning_terminal_receipts_changed")
    expected_names = {INTENT, READY}
    for source, cursor in zip(plan["sources"], expected["cursors"]):
        if (type(source) is not dict or
                set(source) != {"name", "native_number", "image"} or
                source["name"] != cursor["name"] or
                source["native_number"] != cursor["native_number"] or
                type(source["image"]) is not list or
                source["image"] != [
                    cursor["cursor"]["device"], cursor["cursor"]["inode"],
                    cursor["cursor"]["offset"],
                    cursor["cursor"]["prefix_sha256"],
                ]):
            raise ReceiptRefused("historical_learning_terminal_cursor_changed")
        archive_name = "old-" + source["name"]
        expected_names.add(archive_name)
        # Snapshot enforces nofollow, exact file bytes/identity, ownership,
        # mode, one link and bounded size. There is no truncated copy.
        _image(archive / archive_name, receipts, queue,
               expected=source["image"])
    if set(os.listdir(archive)) != expected_names:
        raise ReceiptRefused("historical_learning_foreign_archive")
    if (_read(archive / INTENT, receipts.uid) != raw or
            _read(archive / READY, receipts.uid) != ready_raw or
            (expected_ready_sha256 is not None and
             hashlib.sha256(ready_raw).hexdigest() != expected_ready_sha256)):
        raise ReceiptRefused("historical_learning_terminal_receipts_changed")
    return folder.stat().st_mtime_ns


def erase_completed_learning(receipts: EpochReceipts, queue: DurableInbox,
                             tombstone: Path) -> None:
    """Resume ONLY the already-renamed schema3 .gc3- epoch, never an owner."""
    if (not isinstance(receipts, EpochReceipts) or
            not isinstance(queue, DurableInbox) or not queue._held or
            queue.uid != receipts.uid or queue.writer_gid != receipts.writer_gid or
            not isinstance(tombstone, Path) or
            tombstone.parent != receipts.root or
            not re.fullmatch(r"\.gc3-[0-9a-f]{32}", tombstone.name)):
        raise ReceiptRefused("historical_learning_tombstone_owner_required")
    _directory(tombstone, receipts.uid)
    generation = tombstone.name[5:]
    if set(os.listdir(tombstone)) - (
            RECEIPTS | {"cursor-chain-v2", RETIRE_DIR}):
        raise ReceiptRefused("historical_learning_foreign_tombstone")
    for child in sorted(tombstone.iterdir()):
        if child.name == "cursor-chain-v2":
            CursorChain(receipts, queue)._erase_old_tree(child)
        elif child.name == RETIRE_DIR:
            _directory(child, receipts.uid)
            names = set(os.listdir(child))
            intent_path = child / INTENT
            ready_path = child / READY
            if INTENT not in names:
                # Intent is always deleted LAST; if absent, all physical
                # sources and the ready receipt must already be gone.
                if names:
                    raise ReceiptRefused("historical_learning_tombstone_lost_intent")
            else:
                raw = _read(intent_path, receipts.uid)
                try:
                    plan = json.loads(raw)
                except (ValueError, TypeError, UnicodeError) as exc:
                    raise ReceiptRefused("historical_learning_tombstone_intent_changed") from exc
                if (raw != _canonical(plan) or
                        type(plan) is not dict or
                        plan.get("schema") != 3 or
                        plan.get("kind") != "original-stopped-learning-terminal-intent" or
                        plan.get("generation") != generation or
                        type(plan.get("sources")) is not list or
                        not 2 <= len(plan["sources"]) <= 256):
                    raise ReceiptRefused("historical_learning_tombstone_intent_changed")
                original = {}
                for row in plan["sources"]:
                    if (type(row) is not dict or
                            set(row) != {"name", "native_number", "image"} or
                            type(row["name"]) is not str or
                            type(row["native_number"]) is not int or
                            type(row["image"]) is not list or
                            len(row["image"]) != 4 or
                            any(type(v) is not int or v < 0
                                for v in row["image"][:3]) or
                            type(row["image"][3]) is not str or
                            re.fullmatch(r"[0-9a-f]{64}", row["image"][3]) is None):
                        raise ReceiptRefused("historical_learning_tombstone_source_changed")
                    name = row["name"]
                    if name == "debug.log":
                        if row["native_number"] != 0:
                            raise ReceiptRefused("historical_learning_invalid_debug_archive")
                    else:
                        match = re.fullmatch(
                            r"learning-" + generation + r"-([1-9][0-9]{0,2})\.txt",
                            name)
                        if (match is None or
                                row["native_number"] != int(match.group(1))):
                            raise ReceiptRefused("historical_learning_invalid_native_archive")
                    archived_name = "old-" + name
                    if archived_name in original:
                        raise ReceiptRefused("historical_learning_duplicate_archive")
                    original[archived_name] = row["image"]
                if ("old-debug.log" not in original or
                        names - (set(original) | ARCHIVE_RECEIPTS)):
                    raise ReceiptRefused("historical_learning_foreign_retired_file")
                if READY in names:
                    ready_raw = _read(ready_path, receipts.uid)
                    try:
                        ready = json.loads(ready_raw)
                    except (ValueError, TypeError, UnicodeError) as exc:
                        raise ReceiptRefused("historical_learning_tombstone_ready_changed") from exc
                    if (ready_raw != _canonical(ready) or
                            ready.get("schema") != 3 or
                            ready.get("kind") != "original-stopped-learning-terminal-ready" or
                            ready.get("generation") != generation or
                            ready.get("intent_sha256") != hashlib.sha256(raw).hexdigest()):
                        raise ReceiptRefused("historical_learning_tombstone_ready_changed")
                elif any(name in names for name in original):
                    # Ready may only disappear after the final source.
                    raise ReceiptRefused("historical_learning_ready_missing_before_sources")
                # A partial .gc3- is already approved for removal, but every
                # surviving source must STILL match its original immutable
                # byte image. Do not discard a changed inode after a crash.
                for name, expected_image in sorted(original.items()):
                    if name in names:
                        _image(child / name, receipts, queue,
                               expected=expected_image)
                for name in sorted(original):
                    if name in names:
                        (child / name).unlink()
                        _sync(child)
                if READY in names:
                    ready_path.unlink()
                    _sync(child)
                intent_path.unlink()
                _sync(child)
            child.rmdir()
            _sync(tombstone)
        elif child.name in RECEIPTS:
            info = child.lstat()
            if (not stat.S_ISREG(info.st_mode) or
                    info.st_uid != receipts.uid or info.st_nlink != 1 or
                    stat.S_IMODE(info.st_mode) != 0o600):
                raise ReceiptRefused("historical_learning_untrusted_receipt")
            child.unlink()
        else:
            raise ReceiptRefused("historical_learning_unknown_tombstone_entry")
    _sync(tombstone)
    tombstone.rmdir()
    _sync(receipts.root)


def main() -> None:
    raise SystemExit("original FD9-only schema3 history GC; no standalone CLI")


if __name__ == "__main__":
    main()
