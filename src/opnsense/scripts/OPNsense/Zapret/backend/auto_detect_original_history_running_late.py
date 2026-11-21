#!/usr/bin/env python3
"""STEP 15b3h2a: original RUNNING fourth-source WAL, NOT destination commit.

Freeze the independently verified post-third NEW native/debug positive cut
while the original schema3 dvtws2 owner is still genuinely RUNNING.
The existing original FD4/FD9/P2a+GUI/P2b locks are required. This source
receipt prepares a future original DestinationCommit, without writing Found,
managed, Config, native files, debug, IPFW or issuing native ACK.

IMPORTANT: third-slot immutable postimages and the OLD-retirement release
guard do not yet know about a fourth destination checkpoint. Therefore
this module MUST NOT invoke DestinationCommit or claim physical retirement.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from auto_detect_epoch_receipts import (
    _canonical, _directory, _read, _sync, _write_once, ReceiptRefused,
)
from auto_detect_original_history import _held, _digest, _history_root
from auto_detect_original_history_positive import (
    _positive_snapshot_once, preview_original_learning_independent_positive_locked,
)
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, _native_rebind_stable_snapshot,
)
from auto_detect_debug_window import _read_exact, DebugWindowRefused
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_owner import (
    LearningGenerationProof, GenerationRefused,
    attest_learning_running_generation,
)
from auto_detect_destination_commit import DestinationRefused
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError


SLOT = "00000003"
INTENT = "intent.json"


def _paths(writer, proof):
    chain = writer.receipts.root / proof.generation / "cursor-chain-v2"
    return chain, chain / "00000002", chain / SLOT


def _source_receipt(writer, proof, physical, positive):
    """Construct one bounded FULL physical cut; future appends stay unread."""
    chain, third, _ = _paths(writer, proof)
    uid = writer.receipts.uid
    _directory(chain, uid)
    _directory(third, uid)
    third_raw = _read(third / "intent.json", uid)
    third_intent = json.loads(third_raw)
    progress_raw = _read(third / "cursor-progress.json", uid)
    progress = json.loads(progress_raw)
    if (third_raw != _canonical(third_intent) or
            progress_raw != _canonical(progress) or
            third_intent.get("generation") != proof.generation or
            third_intent.get("sequence") != 2 or
            progress.get("generation") != proof.generation or
            progress.get("sequence") != 2 or
            progress.get("cursor_advanced") is not True or
            progress.get("native_pending_ack_authorized") is not False or
            progress.get("source_intent_sha256") != _digest(third_raw)):
        raise V2OriginalConfigRefused("running_late_third_original_cursor_missing")
    history = _history_root(writer, proof)
    post_raw = _read(history / "postimages.json", uid)
    post = json.loads(post_raw)
    if (post_raw != _canonical(post) or
            post.get("generation") != proof.generation or
            post.get("sequence") != 2):
        raise V2OriginalConfigRefused("running_late_original_postimage_unqualified")
    if ((history / "release-guard.json").exists() or
            (history / "release-guard.json").is_symlink() or
            (third / "pending-old-retirement").exists() or
            (third / "pending-old-retirement").is_symlink()):
        raise V2OriginalConfigRefused("running_late_old_retirement_already_sealed")
    rows = []
    by_n = {n: (hostlist, pathname) for n, hostlist, pathname in proof.learning}
    if len(physical["native"]) != len(by_n):
        raise V2OriginalConfigRefused("running_late_missing_native_N")
    for number, pathname, dev, inode, size, mtime, ctime, sha in physical["native"]:
        if (number not in by_n or pathname != by_n[number][1] or
                type(size) is not int or size < 0):
            raise V2OriginalConfigRefused("running_late_foreign_native")
        native_raw = _read(third / "native" / f"{number:03d}.json", uid)
        native = json.loads(native_raw)
        cut = native["cursor"]
        if (native_raw != _canonical(native) or
                cut.get("new_path") != pathname or
                cut.get("new_device") != dev or cut.get("new_inode") != inode or
                type(cut.get("new_end")) is not int or
                cut["new_end"] > size):
            raise V2OriginalConfigRefused("running_late_original_N_cursor_changed")
        rows.append({
            "native_number": number, "hostlist": by_n[number][0],
            "path": pathname, "device": dev, "inode": inode,
            "frozen_end": size, "frozen_sha256": sha,
            "previous_end": cut["new_end"],
            "previous_sha256": cut["new_end_sha256"],
        })
    rows.sort(key=lambda row: row["native_number"])
    debug_dev, debug_inode, debug_size, _, _, debug_sha = physical["debug"]
    prior_debug = third_intent["debug"]
    if (debug_dev != prior_debug.get("device") or
            debug_inode != prior_debug.get("inode") or
            debug_size < prior_debug.get("end", -1)):
        raise V2OriginalConfigRefused("running_late_original_debug_cursor_changed")
    native_positive = [
        {"native_number": n, "hostlist": label, "hostname": host}
        for n, label, host in physical["positive"]
    ]
    if (not native_positive or physical["native_bytes_after_third"] <= 0 or
            native_positive != positive["positive_native_observations"] or
            positive["positive_event_count"] != len(native_positive) or
            positive["postimages_sha256"] != _digest(post_raw)):
        raise V2OriginalConfigRefused("running_late_unqualified_positive_or_postimage")
    return {
        "schema": 3, "kind": "original-learning-running-fourth-source-prepared",
        "generation": proof.generation, "sequence": 3,
        "owner_pid": proof.owner.pid, "owner_start": proof.owner.started,
        "operation_id": proof.operation_id,
        "native_map_sha256": proof.native_map_sha256,
        "third_source_intent_sha256": _digest(third_raw),
        "third_cursor_progress_sha256": _digest(progress_raw),
        "original_third_postimages_sha256": _digest(post_raw),
        "native": rows,
        "debug": {
            "path": str(writer.queue.root / "debug.log"),
            "device": debug_dev, "inode": debug_inode,
            "previous_end": prior_debug["end"],
            "previous_sha256": prior_debug["end_sha256"],
            "frozen_end": debug_size, "frozen_sha256": debug_sha,
        },
        "native_positive_observations": native_positive,
        "observations": [
            {"hostname": row["hostname"], "hostlist": row["hostlist"]}
            for row in native_positive
        ],
        "source_only": True,
        "destination_commit_authorized": False,
        "native_pending_ack_authorized": False,
        "generation_retired": False,
    }


def _frozen_prefix_still_exists(writer, proof, intent, inspect):
    """Independently pin exact frozen prefixes, allowing later producer append."""
    uid, gid = writer.receipts.uid, writer.queue.writer_gid
    expected = {n: (name, path) for n, name, path in proof.learning}
    native = intent.get("native")
    if (type(native) is not list or len(native) != len(expected) or
            [r.get("native_number") for r in native] != sorted(expected)):
        raise V2OriginalConfigRefused("running_late_frozen_N_count_changed")
    for row in native:
        n = row["native_number"]
        if ((row.get("hostlist"), row.get("path")) != expected[n] or
                type(row.get("frozen_end")) is not int or
                row["frozen_end"] < row.get("previous_end", 0)):
            raise V2OriginalConfigRefused("running_late_frozen_N_foreign")
        path = Path(row["path"])
        if path.parent != writer.queue.root:
            raise V2OriginalConfigRefused("running_late_frozen_N_path_changed")
        st, raw, _ = _native_rebind_stable_snapshot(
            path, uid, gid, allowed_links=(1,))
        if ((st.st_dev, st.st_ino) != (row["device"], row["inode"]) or
                len(raw) < row["frozen_end"] or
                _digest(raw[:row["frozen_end"]]) != row["frozen_sha256"] or
                inspect(path, st.st_dev, st.st_ino, owner=proof.owner,
                        writer_gid=gid) is not FDState.DRAINED):
            raise V2OriginalConfigRefused("running_late_frozen_N_changed_or_busy")
    debug = intent["debug"]
    path = Path(debug["path"])
    if path != writer.queue.root / "debug.log":
        raise V2OriginalConfigRefused("running_late_debug_path_changed")
    st, raw = _read_exact(path, owner_uid=uid, writer_gid=gid)
    if ((st.st_dev, st.st_ino) != (debug["device"], debug["inode"]) or
            len(raw) < debug["frozen_end"] or
            _digest(raw[:debug["frozen_end"]]) != debug["frozen_sha256"] or
            inspect(path, st.st_dev, st.st_ino, owner=proof.owner,
                    writer_gid=gid) is not FDState.DRAINED):
        raise V2OriginalConfigRefused("running_late_frozen_debug_changed_or_busy")


def prepare_original_learning_running_late_source_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """One write-once source receipt, never a P1/Found/managed destination."""
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (not isinstance(proof, LearningGenerationProof) or
                not callable(inspect)):
            raise V2OriginalConfigRefused("running_late_original_schema3_required")
        owner_before = attest_learning_running_generation()
        if owner_before != proof:
            raise V2OriginalConfigRefused("running_late_original_owner_not_running")
        args = dict(config_fd=config_fd, config_path=config_path,
                    attest=attest, inspect=inspect)
        positive = preview_original_learning_independent_positive_locked(
            writer, proof, workspace, **args)
        first = _positive_snapshot_once(writer, proof, inspect)
        second = _positive_snapshot_once(writer, proof, inspect)
        if first != second or positive["positive_event_count"] == 0:
            raise V2OriginalConfigRefused("running_late_no_stable_positive_new")
        expected = _source_receipt(writer, proof, second, positive)
        chain, third, slot = _paths(writer, proof)
        uid = writer.receipts.uid
        slot_preexisting = slot.exists() or slot.is_symlink()
        if slot_preexisting:
            _directory(slot, uid)
            contents = set(os.listdir(slot))
            if contents - {INTENT}:
                raise V2OriginalConfigRefused("running_late_unexpected_fourth_slot")
        else:
            contents = set()
        if contents == {INTENT}:
            saved_raw = _read(slot / INTENT, uid)
            saved = json.loads(saved_raw)
            if saved_raw != _canonical(saved):
                raise V2OriginalConfigRefused("running_late_noncanonical_source")
            # No re-freeze after crash. New append is NOT part of this WAL.
            # If the current source advanced, the initial full snapshot is
            # not equal to the original intent, but its frozen PREFIX must
            # still be physically present.
            if (saved.get("generation") != proof.generation or
                    saved.get("kind") != expected["kind"] or
                    saved.get("original_third_postimages_sha256") !=
                    expected["original_third_postimages_sha256"] or
                    saved.get("third_cursor_progress_sha256") !=
                    expected["third_cursor_progress_sha256"] or
                    saved.get("owner_pid") != proof.owner.pid or
                    saved.get("owner_start") != proof.owner.started or
                    saved.get("native_map_sha256") != proof.native_map_sha256 or
                    saved.get("destination_commit_authorized") is not False or
                    saved.get("native_pending_ack_authorized") is not False):
                raise V2OriginalConfigRefused("running_late_existing_source_foreign")
            raw = saved_raw
            frozen = saved
        else:
            # A crash between mkdir+fsync and the FIRST intent link is a
            # qualified empty-slot replay, not an invented completed WAL.
            # Any foreign entry or a conflicting saved intent still fails.
            raw = _canonical(expected)
            if (attest_learning_running_generation() != proof or
                    _positive_snapshot_once(writer, proof, inspect) != first or
                    preview_original_learning_independent_positive_locked(
                        writer, proof, workspace, **args) != positive):
                raise V2OriginalConfigRefused("running_late_source_raced_before_seal")
            _held(writer, proof, workspace, config_fd, config_path, attest)
            if not slot_preexisting:
                slot.mkdir(mode=0o700)
                _sync(chain)
            _directory(slot, uid)
            if os.listdir(slot):
                raise V2OriginalConfigRefused("running_late_empty_slot_raced")
            _write_once(slot, INTENT, raw, uid)
            frozen = expected
        _frozen_prefix_still_exists(writer, proof, frozen, inspect)
        again = preview_original_learning_independent_positive_locked(
            writer, proof, workspace, **args)
        if (attest_learning_running_generation() != owner_before or
                again["postimages_sha256"] != positive["postimages_sha256"] or
                _read(slot / INTENT, uid) != raw or
                set(os.listdir(slot)) != {INTENT}):
            raise V2OriginalConfigRefused("running_late_postseal_owner_or_source_raced")
        _held(writer, proof, workspace, config_fd, config_path, attest)
        return {
            "generation": proof.generation, "sequence": 3,
            "slot": str(slot), "source_intent_sha256": _digest(raw),
            "frozen_positive_count": len(frozen["native_positive_observations"]),
            "original_running_owner_freshly_reattested": True,
            "frozen_native_and_debug_prefixes_verified": True,
            "p1_destination_checkpoint_created": False,
            "native_pending_ack_authorized": False,
            "generation_retired": False,
            "operator_stop_may_be_blocked": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            GenerationRefused, OriginalLockRefused, QueueSafetyError,
            DebugWindowRefused) as exc:
        raise V2OriginalConfigRefused(
            "running_late_original_source_not_safe") from exc


def main():
    raise SystemExit("Original RUNNING late source is not a worker")


if __name__ == "__main__":
    main()
