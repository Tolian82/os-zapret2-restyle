#!/usr/bin/env python3
"""STEP 15b2b: original post-archive NEW native/debug positive pair, READ ONLY.

Only the one original FD4/FD9/P2a/GUI and all-PID P2b proof may be used.
The original three-slot WAL, final physical destinations and independent OLD
mirror must be already sealed. No OLD archive inode is opened for pairing.
No cursor/Found/managed/ACK/Config/IPFW or active runtime state is changed.
A native append alone is NOT a positive event; a debug positive alone is
NOT proof of a durable native append. Both must match N, path and hostname.
"""
from __future__ import annotations

import json
from pathlib import Path

from auto_detect_debug_window import (
    ADD, MAX_RAW, MAX_WINDOW, MAX_EVENTS, _hostname, _raw_hosts,
    _read_exact, DebugWindowRefused,
)
from auto_detect_epoch_receipts import _read, _canonical, ReceiptRefused
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_original_history import _held, _digest
from auto_detect_original_history_postimages import (
    read_original_learning_independent_postimages_locked,
)
from auto_detect_original_v2_model import (
    _native_rebind_stable_snapshot, V2OriginalConfigRefused,
)
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError


def _positive_snapshot_once(writer, proof, inspect):
    """One bounded physical N+debug attestation after third committed cuts."""
    uid, gid = writer.receipts.uid, writer.queue.writer_gid
    slot = (writer.receipts.root / proof.generation /
            "cursor-chain-v2" / "00000002")
    intent_raw = _read(slot / "intent.json", uid)
    intent = json.loads(intent_raw)
    if (intent_raw != _canonical(intent) or
            intent.get("schema") != 3 or
            intent.get("sequence") != 2 or
            intent.get("generation") != proof.generation or
            intent.get("ack_authorized") is not False or
            intent.get("cursor_advanced") is not False or
            intent.get("profiles_count") != len(proof.learning)):
        raise V2OriginalConfigRefused("native_positive_third_intent_unqualified")
    seen = set()
    witnesses = []
    total_bytes = 0
    by_path = {}
    for number, hostlist, pathname in proof.learning:
        path = Path(pathname)
        if (path.parent != writer.queue.root or
                pathname in by_path or
                hostlist not in ("youtube", "user")):
            raise V2OriginalConfigRefused("native_positive_foreign_profile_map")
        receipt_raw = _read(slot / "native" / f"{number:03d}.json", uid)
        receipt = json.loads(receipt_raw)
        cursor = receipt["cursor"]
        if (receipt_raw != _canonical(receipt) or
                receipt.get("schema") != 3 or
                receipt.get("kind") != "original-learning-third-native-cut" or
                receipt.get("generation") != proof.generation or
                receipt.get("sequence") != 2 or
                receipt.get("native_number") != number or
                receipt.get("hostlist") != hostlist or
                receipt.get("ack_authorized") is not False or
                cursor.get("new_path") != pathname or
                type(cursor.get("new_end")) is not int or
                cursor["new_end"] < 0):
            raise V2OriginalConfigRefused("native_positive_unqualified_N_cut")
        stat, data, identity = _native_rebind_stable_snapshot(
            path, uid, gid, allowed_links=(1,))
        end = cursor["new_end"]
        if ((stat.st_dev, stat.st_ino) !=
                (cursor.get("new_device"), cursor.get("new_inode")) or
                end > len(data) or
                _digest(data[:end]) != cursor.get("new_end_sha256") or
                inspect(path, stat.st_dev, stat.st_ino,
                        owner=proof.owner, writer_gid=gid) is not FDState.DRAINED):
            raise V2OriginalConfigRefused("native_positive_new_inode_unqualified")
        tail = data[end:]
        total_bytes += len(tail)
        if total_bytes > MAX_RAW:
            raise V2OriginalConfigRefused("native_positive_combined_N_over_limit")
        if tail:
            for host in _raw_hosts(tail):
                seen.add((number, hostlist, host))
                if len(seen) > MAX_EVENTS:
                    raise V2OriginalConfigRefused("native_positive_N_event_limit")
        witnesses.append((
            number, pathname, stat.st_dev, stat.st_ino, len(data),
            stat.st_mtime_ns, stat.st_ctime_ns, _digest(data),
        ))
        by_path[pathname] = (number, hostlist)
    debug_path = writer.queue.root / "debug.log"
    stat_debug, debug_bytes = _read_exact(
        debug_path, owner_uid=uid, writer_gid=gid)
    debug = intent["debug"]
    cut = debug["end"]
    if (type(cut) is not int or cut < 0 or cut > len(debug_bytes) or
            (stat_debug.st_dev, stat_debug.st_ino) !=
            (debug["device"], debug["inode"]) or
            _digest(debug_bytes[:cut]) != debug["end_sha256"] or
            inspect(debug_path, stat_debug.st_dev, stat_debug.st_ino,
                    owner=proof.owner, writer_gid=gid) is not FDState.DRAINED):
        raise V2OriginalConfigRefused("native_positive_debug_inode_unqualified")
    tail = debug_bytes[cut:]
    if len(tail) > MAX_WINDOW or (tail and not tail.endswith(b"\n")):
        raise V2OriginalConfigRefused("native_positive_debug_window_unsealed")
    positives = set()
    for line in tail.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise V2OriginalConfigRefused("native_positive_debug_partial_line")
        try:
            text = line[:-1].decode("ascii")
        except UnicodeError as exc:
            raise V2OriginalConfigRefused(
                "native_positive_debug_nonascii") from exc
        if " : adding to " not in text:
            continue
        match = ADD.fullmatch(text)
        if match is None or not _hostname(match["host"]):
            raise V2OriginalConfigRefused("native_positive_malformed_debug")
        provenance = by_path.get(match["path"])
        if provenance is None or int(match["profile"]) != provenance[0]:
            raise V2OriginalConfigRefused("native_positive_foreign_N_debug")
        positives.add((provenance[0], provenance[1], match["host"]))
        if len(positives) > MAX_EVENTS:
            raise V2OriginalConfigRefused("native_positive_debug_event_limit")
    # Upstream emits debug before append: neither orphan can be consumed.
    # Duplicates within one N are deduplicated, never across different N.
    if seen != positives:
        raise V2OriginalConfigRefused("native_positive_new_debug_pair_mismatch")
    return {
        "native": tuple(witnesses),
        "debug": (stat_debug.st_dev, stat_debug.st_ino,
                  stat_debug.st_size, stat_debug.st_ctime_ns,
                  stat_debug.st_mtime_ns, _digest(debug_bytes)),
        "native_bytes_after_third": total_bytes,
        "debug_bytes_after_third": len(tail),
        "positive": tuple(sorted(positives)),
    }


def preview_original_learning_independent_positive_locked(
        writer, proof, workspace: Path, *, config_fd: int, config_path: Path,
        attest, inspect=probe_pending_fd,
) -> dict:
    """Prove current NEW source only. Never publish a cursor or authorize unlink."""
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if not callable(inspect):
            raise V2OriginalConfigRefused("native_positive_P2b_required")
        postimages_before = read_original_learning_independent_postimages_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        before = _positive_snapshot_once(writer, proof, inspect)
        after = _positive_snapshot_once(writer, proof, inspect)
        postimages_after = read_original_learning_independent_postimages_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect)
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (before != after or postimages_before != postimages_after or
                postimages_before["all_final_destinations_inode_pinned"] is not True):
            raise V2OriginalConfigRefused("native_positive_postunlink_source_raced")
        return {
            "generation": proof.generation, "sequence": 2,
            "postimages_sha256": postimages_before["postimages_sha256"],
            "positive_event_count": len(before["positive"]),
            "positive_native_observations": [
                {"native_number": number, "hostlist": hostlist, "hostname": host}
                for number, hostlist, host in before["positive"]],
            "unprocessed_new_native_bytes": before["native_bytes_after_third"],
            "unprocessed_new_debug_bytes": before["debug_bytes_after_third"],
            "all_final_destinations_inode_pinned": True,
            "new_positive_debug_attribution_verified": True,
            "old_bytes_source_independent": True,
            "source_independent_transaction_replay_available": False,
            "native_pending_ack_authorized": False,
            "archive_unlink_authorized": False,
            "generation_retired": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, DebugWindowRefused,
            OriginalLockRefused, QueueSafetyError) as exc:
        raise V2OriginalConfigRefused(
            "native_positive_postunlink_readonly_refused") from exc


def main():
    raise SystemExit("Independent original native-positive reader is not a worker")


if __name__ == "__main__":
    main()
