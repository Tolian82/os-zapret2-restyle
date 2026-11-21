#!/usr/bin/env python3
"""STEP 15b1: independent, READ-ONLY original committed-WAL inspection.

This is not an ACK or a new DestinationCommit/recovery writer. It proves the
original three destination checkpoints, exact final Found/managed states, and
current NEW live/debug prefixes without opening ANY archived OLD inode.
Every authorization remains false until full crash recovery and live P2b
post-unlink acceptance are proven independently.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from auto_detect_epoch_receipts import _canonical, _read, _directory, ReceiptRefused
from auto_detect_original_history import (
    _held, _digest, _read_history_once, _archive_paths,
)
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, _original_learning_forward_progress_record,
    _original_learning_third_progress_record, _native_rebind_stable_snapshot,
)
from auto_detect_destination_commit import (
    DestinationRefused, qualified_destination_plan, _file_identity, _target,
)
from auto_detect_debug_window import _read_exact, _raw_hosts, DebugWindowRefused
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError
import auto_detect_original_v2_model as original_model


def _read_original_wal_once(writer, proof, old_images, inspect):
    uid, gid = writer.receipts.uid, writer.queue.writer_gid
    first_folder = writer.receipts.root / proof.generation / "cursor-chain-v2"
    rows = []
    plans = []
    for seq in (0, 1, 2):
        slot = first_folder / f"{seq:08d}"
        _directory(slot, uid)
        intent_raw = _read(slot / "intent.json", uid)
        intent = json.loads(intent_raw)
        if (intent_raw != _canonical(intent) or
                intent.get("schema") != 3 or
                intent.get("generation") != proof.generation or
                intent.get("sequence") != seq or
                intent.get("ack_authorized") is not False):
            raise V2OriginalConfigRefused("native_history_wal_source_unqualified")
        plan, plan_raw = qualified_destination_plan(
            slot, intent, uid, targets=writer.targets)
        cp_raw = _read(slot / "destination" / "checkpoint.json", uid)
        cp = json.loads(cp_raw)
        debug_end = (intent["debug_end_offset"] if seq == 0
                     else intent["debug"]["end"])
        debug_sha = (intent["debug_end_sha256"] if seq == 0
                     else intent["debug"]["end_sha256"])
        expected_cp = {
            "schema": 1, "kind": "destination-and-cursor-committed",
            "generation": proof.generation,
            "pending_name": f"learning-{seq:08d}",
            "plan_sha256": _digest(plan_raw),
            "evidence": "learning-native-debug",
            "committed_cursor_offset": debug_end,
            "committed_cursor_sha256": debug_sha,
            "ack_authorized": False,
        }
        if (cp_raw != _canonical(cp) or cp != expected_cp or
                plan.get("schema") != 3 or "live" not in plan or
                plan.get("source_intent_sha256") != _digest(intent_raw)):
            raise V2OriginalConfigRefused("native_history_wal_checkpoint_unqualified")
        rows.append((intent, intent_raw, cp, cp_raw, plan, plan_raw))
        plans.append(plan)
    second = rows[1]
    second_progress_raw = _read(
        first_folder / "00000001" / "cursor-progress.json", uid)
    expected_second = _canonical(_original_learning_forward_progress_record(
        second[0], second[1], second[3], second[2]))
    if second_progress_raw != expected_second:
        raise V2OriginalConfigRefused("native_history_second_cursor_unqualified")
    third = rows[2]
    third_progress_raw = _read(
        first_folder / "00000002" / "cursor-progress.json", uid)
    third_progress = json.loads(third_progress_raw)
    pinned = third_progress.get("destination_postimages")
    if (type(pinned) is not dict or set(pinned) != {"writes", "live"} or
            any(type(pinned[k]) is not dict or
                set(pinned[k]) != set(third[4][k])
                for k in ("writes", "live")) or
            third_progress_raw != _canonical(
                _original_learning_third_progress_record(
                    third[0], third[1], third[3], third[2], pinned))):
        raise V2OriginalConfigRefused("native_history_third_cursor_unqualified")
    # Exact original destination postimages. The third receipt pins the
    # physical inode/mtime, not only digest. Earlier last-writers have SHA
    # evidence but no third physical pin: never promote them to ACK proof.
    latest = {}
    for seq, plan in enumerate(plans):
        for kind in ("writes", "live"):
            for name, row in plan[kind].items():
                latest[(kind, name)] = (seq, row)
    destinations = {}
    all_final_destinations_inode_pinned = True
    continuation = first_folder / "00000003" / "destination" / "plan.json"
    historical_rows = None
    continuation_intent = None
    if continuation.exists() or continuation.is_symlink():
        from auto_detect_original_history_running_late import (
            read_original_learning_late_postimages, _frozen_prefix_still_exists,
        )
        post = json.loads(_read(
            _archive_paths(writer, proof)[2] / "history" / "postimages.json", uid))
        # Preserve the immutable third seal. The fourth original WAL must
        # inherit those exact before-inodes and pin its own final inodes.
        _, progress = read_original_learning_late_postimages(
            writer, proof, post["destinations"])
        if progress is None:
            raise V2OriginalConfigRefused("native_history_late_progress_missing")
        last = first_folder / f"{progress['sequence']:08d}" / "intent.json"
        continuation_intent = json.loads(_read(last, uid))
        _frozen_prefix_still_exists(writer, proof, continuation_intent, inspect)
        historical_rows = {row["target"]: row for row in post["destinations"]}
    for (kind, name), (seq, row) in sorted(latest.items()):
        path = (writer.targets[name] if kind == "writes" else
                original_model.COMMON_ACTIVE / "managed" /
                f"hostlist-{name}.txt")
        if row["path"] != str(path):
            raise V2OriginalConfigRefused("native_history_foreign_destination_path")
        if historical_rows is None:
            data, stat = _target(path, uid)
            digest, identity = _digest(data), _file_identity(stat)
        else:
            old = historical_rows[f"{kind}:{name}"]
            if old["path"] != str(path) or old["last_writer_sequence"] != seq:
                raise V2OriginalConfigRefused("native_history_late_predecessor_changed")
            digest = old["sha256"]
            identity = tuple(old[key] for key in (
                "device", "inode", "ctime_ns", "mtime_ns", "size"))
        if digest != row["after"]:
            raise V2OriginalConfigRefused("native_history_destination_not_committed")
        if seq == 2:
            pin = pinned[kind][name]
            expected_pin = dict(
                path=str(path), sha256=digest,
                device=identity[0], inode=identity[1],
                ctime_ns=identity[2], mtime_ns=identity[3],
                size=identity[4])
            if pin != expected_pin:
                raise V2OriginalConfigRefused("native_history_third_postimage_changed")
        else:
            all_final_destinations_inode_pinned = False
        destinations[f"{kind}:{name}"] = (str(path), digest, identity, seq)
    # Check every physical NEW current inode against its immutable native N
    # cut. Unread suffix is preserved, NEVER declared found or processed.
    # Debug-positive attribution of those suffixes is a separate OPEN gate.
    native = {}
    total_unread = 0
    for number, hostlist, pathname in proof.learning:
        record_raw = _read(
            first_folder / "00000002" / "native" /
            f"{number:03d}.json", uid)
        record = json.loads(record_raw)
        cursor = record["cursor"]
        old = old_images[number]
        if (record_raw != _canonical(record) or
                record.get("native_number") != number or
                record.get("hostlist") != hostlist or
                cursor.get("old_end") != len(old) or
                cursor.get("old_end_sha256") != _digest(old) or
                cursor.get("new_path") != pathname or
                type(cursor.get("new_end")) is not int or
                cursor["new_end"] < 0):
            raise V2OriginalConfigRefused("native_history_native_old_or_new_unbound")
        path = Path(pathname)
        if path.parent != writer.queue.root:
            raise V2OriginalConfigRefused("native_history_new_native_outside_owner")
        stat, data, identity = _native_rebind_stable_snapshot(
            path, uid, gid, allowed_links=(1,))
        end = cursor["new_end"]
        if ((stat.st_dev, stat.st_ino) !=
                (cursor["new_device"], cursor["new_inode"]) or
                end > len(data) or
                _digest(data[:end]) != cursor["new_end_sha256"] or
                inspect(path, stat.st_dev, stat.st_ino,
                        owner=proof.owner, writer_gid=gid) is not FDState.DRAINED):
            raise V2OriginalConfigRefused("native_history_new_inode_unqualified")
        effective_end = end
        if continuation_intent is not None:
            current = next(r for r in continuation_intent["native"]
                           if r["native_number"] == number)
            effective_end = current["frozen_end"]
        unread = data[effective_end:]
        if unread:
            _raw_hosts(unread)
        total_unread += len(unread)
        native[number] = (pathname, _digest(data), identity, len(unread))
    debug = third[0]["debug"]
    path_debug = writer.queue.root / "debug.log"
    stat_debug, debug_bytes = _read_exact(
        path_debug, owner_uid=uid, writer_gid=gid)
    if (type(debug.get("end")) is not int or
            debug["end"] > len(debug_bytes) or
            (stat_debug.st_dev, stat_debug.st_ino) !=
            (debug["device"], debug["inode"]) or
            _digest(debug_bytes[:debug["end"]]) != debug["end_sha256"] or
            inspect(path_debug, stat_debug.st_dev, stat_debug.st_ino,
                    owner=proof.owner, writer_gid=gid) is not FDState.DRAINED):
        raise V2OriginalConfigRefused("native_history_debug_inode_unqualified")
    processed_debug_end = (continuation_intent["debug"]["frozen_end"]
                           if continuation_intent is not None else debug["end"])
    return {
        "sequence": 2,
        "checkpoint_sha256": tuple(_digest(row[3]) for row in rows),
        "third_progress_sha256": _digest(third_progress_raw),
        "all_three_original_wal_checkpoints_verified": True,
        "destination_witnesses": destinations,
        "all_final_destinations_inode_pinned": all_final_destinations_inode_pinned,
        "native_witnesses": native,
        "debug_witness": (
            stat_debug.st_dev, stat_debug.st_ino, stat_debug.st_size,
            stat_debug.st_ctime_ns, stat_debug.st_mtime_ns,
            _digest(debug_bytes),
        ),
        "unprocessed_new_native_bytes": total_unread,
        "unprocessed_new_debug_bytes": len(debug_bytes) - processed_debug_end,
        "new_positive_debug_attribution_verified": False,
    }


def preview_original_learning_independent_wal_locked(
        writer, proof, workspace: Path, *,
        config_fd: int, config_path: Path, attest,
        inspect=probe_pending_fd,
) -> dict:
    """No historical old inode opened, no durable file or Config modified."""
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if not callable(inspect):
            raise V2OriginalConfigRefused("native_history_missing_all_PID_P2b")
        old, mirror_digest = _read_history_once(writer, proof)
        before = _read_original_wal_once(writer, proof, old, inspect)
        # The dvtws2 native writer does NOT obey P2a. Reattest all-N new
        # physical files, debug, 3 WAL checkpoints and old mirror once more.
        re_old, re_digest = _read_history_once(writer, proof)
        after = _read_original_wal_once(writer, proof, re_old, inspect)
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if re_old != old or re_digest != mirror_digest or before != after:
            raise V2OriginalConfigRefused("native_history_postunlink_replay_raced")
        return {
            "generation": proof.generation,
            "sequence": 2,
            "old_mirror_sha256": mirror_digest,
            "all_three_original_wal_checkpoints_verified": True,
            "third_destination_postimages_verified": True,
            "all_final_destinations_inode_pinned":
                before["all_final_destinations_inode_pinned"],
            "unprocessed_new_native_bytes":
                before["unprocessed_new_native_bytes"],
            "unprocessed_new_debug_bytes":
                before["unprocessed_new_debug_bytes"],
            "new_positive_debug_attribution_verified": False,
            "source_independent_transaction_replay_available": False,
            "native_pending_ack_authorized": False,
            "archive_unlink_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            DebugWindowRefused, OriginalLockRefused, QueueSafetyError) as exc:
        raise V2OriginalConfigRefused(
            "native_history_postunlink_wal_replay_refused") from exc


def main():
    raise SystemExit("Independent original WAL replay is not a worker")


if __name__ == "__main__":
    main()
