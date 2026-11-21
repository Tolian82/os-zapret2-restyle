#!/usr/bin/env python3
"""#1052 ТЗ_6v4 third original cursor-chain SOURCE ONLY, no new writer.

All mutations here are write-once N source receipts under the SAME original
EpochReceipts/cursor-chain-v2. NO P1/destination writes, native ACK, unlink,
P2 queue ownership, Config save, new daemon, cron or service restart.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from auto_detect_epoch_receipts import (
    ReceiptRefused, _canonical, _directory, _read, _write_once, _sync,
)
from auto_detect_original_lock_handoff import (
    CONFIG_PATH, assert_inherited_config_fd, OriginalLockRefused,
)
from auto_detect_queue import QueueSafetyError
from auto_detect_owner import LearningGenerationProof
from auto_detect_destination_commit import DestinationCommit, DestinationRefused
from auto_detect_debug_window import DebugWindowRefused
from auto_detect_original_v2_model import (
    V2OriginalConfigRefused, preview_original_learning_late_tails_locked,
)


def prepare_third_source_locked(
        writer: DestinationCommit, proof: LearningGenerationProof,
        workspace: Path, *, config_fd: int, config_path: Path,
        attest, inspect) -> dict:
    """Seal 00000002/native/<N>.json first, aggregate intent.json LAST.

    The *completed* second original Found->managed destination checkpoint
    and cursor-progress are reverified before each preview. Replayed cuts
    are frozen: late append on the old pending FD or the new live FD can
    never widen a previously published intent.
    """
    if (not isinstance(writer, DestinationCommit) or
            not isinstance(proof, LearningGenerationProof) or
            not writer.queue._held or not getattr(writer, "_gui_held", False) or
            not isinstance(workspace, Path) or not workspace.is_absolute() or
            workspace.name != proof.generation or
            not isinstance(config_path, Path) or
            not config_path.is_absolute() or
            type(config_fd) is not int or config_fd < 3 or
            not callable(attest) or not callable(inspect) or
            (sys.platform.startswith("freebsd") and (
                config_path != CONFIG_PATH or writer.receipts.uid != 0 or
                writer.queue.uid != 0)) or attest() != proof):
        raise V2OriginalConfigRefused(
            "original_third_source_fd4_fd9_owner_required")

    uid = writer.receipts.uid

    def held():
        assert_inherited_config_fd(
            config_fd, config_path,
            owner_uid=None if config_path == CONFIG_PATH else uid)
        if attest() != proof:
            raise V2OriginalConfigRefused(
                "original_third_source_owner_changed")

    def preview(frozen=None):
        return preview_original_learning_late_tails_locked(
            writer, proof, workspace, config_fd=config_fd,
            config_path=config_path, attest=attest, inspect=inspect,
            sealed_window=frozen)

    def digest(rows):
        return hashlib.sha256(json.dumps(
            rows, separators=(",", ":"), sort_keys=True
        ).encode()).hexdigest()

    def pack(candidate, former):
        if (len(candidate["native"]) != len(proof.learning) or
                len(former) != len(proof.learning)):
            raise V2OriginalConfigRefused(
                "original_third_source_N_count_changed")
        packed = []
        for index, (number, hostlist, pathname) in enumerate(proof.learning):
            prior = former[index]
            late = candidate["native"][index]
            if (prior["native_number"] != number or
                    prior["hostlist"] != hostlist or
                    late["native_number"] != number or
                    late["hostlist"] != hostlist or
                    (prior["new_path"] or prior["old_path"]) != pathname):
                raise V2OriginalConfigRefused(
                    "original_third_source_profile_map_changed")
            updated = dict(prior)
            for side in ("old", "new"):
                part = late[side]
                if prior[f"{side}_path"] is None:
                    if side != "new" or part is not None:
                        raise V2OriginalConfigRefused(
                            "original_third_source_partial_inode")
                    continue
                if (type(part) is not dict or
                        part.get("path") != prior[f"{side}_path"] or
                        part.get("device") != prior[f"{side}_device"] or
                        part.get("inode") != prior[f"{side}_inode"] or
                        part.get("start") != prior[f"{side}_end"] or
                        part.get("start_sha256") !=
                        prior[f"{side}_end_sha256"] or
                        type(part.get("end")) is not int or
                        part["end"] < part["start"] or
                        type(part.get("end_sha256")) is not str):
                    raise V2OriginalConfigRefused(
                        "original_third_source_native_cursor_changed")
                updated[f"{side}_end"] = part["end"]
                updated[f"{side}_end_sha256"] = part["end_sha256"]
            rec = {
                "schema": 3, "kind": "original-learning-third-native-cut",
                "generation": proof.generation, "sequence": 2,
                "previous_source_intent_sha256":
                    candidate["source_intent_sha256"],
                "previous_cursor_progress_sha256":
                    candidate["cursor_progress_sha256"],
                "native_number": number, "hostlist": hostlist,
                "cursor": updated, "cursor_advanced": False,
                "ack_authorized": False,
            }
            packed.append((f"{number:03d}.json", _canonical(rec)))
        return packed

    def make_intent(candidate, previous, packed):
        if (not candidate["native_observations"] or
                candidate["p2b_drained"] is not True or
                candidate["cursor_advanced"] is not False or
                candidate["native_pending_ack_authorized"] is not False or
                candidate["native_cleanup_authorized"] is not False or
                candidate["generation_retired"] is not False):
            raise V2OriginalConfigRefused(
                "original_third_source_no_verified_late_events")
        next_debug = dict(previous["debug"])
        current_debug = candidate["debug"]
        if (current_debug["device"] != next_debug["device"] or
                current_debug["inode"] != next_debug["inode"] or
                current_debug["start"] != next_debug["end"] or
                current_debug["start_sha256"] !=
                next_debug["end_sha256"]):
            raise V2OriginalConfigRefused(
                "original_third_source_debug_cursor_changed")
        next_debug["end"] = current_debug["end"]
        next_debug["end_sha256"] = current_debug["end_sha256"]
        return {
            "schema": 3, "kind": "original-learning-third-slot-prepared",
            "generation": proof.generation, "sequence": 2,
            "owner_pid": proof.owner.pid,
            "owner_start": proof.owner.started,
            "operation_id": proof.operation_id,
            "owner_candidate_sha256": proof.owner_candidate_sha256,
            "final_args_sha256": proof.final_args_sha256,
            "native_map_sha256": proof.native_map_sha256,
            "first_slot_sha256": previous["first_slot_sha256"],
            "native_rebind_manifest_sha256":
                previous["native_rebind_manifest_sha256"],
            "previous_source_intent_sha256":
                candidate["source_intent_sha256"],
            "previous_cursor_progress_sha256":
                candidate["cursor_progress_sha256"],
            "debug": next_debug,
            "profiles_count": len(packed),
            "profiles_sha256": hashlib.sha256(b"".join(
                hashlib.sha256(raw).digest()
                for _, raw in packed)).hexdigest(),
            "observations_count": len(candidate["observations"]),
            "observations_sha256": digest(candidate["observations"]),
            "native_observations_sha256":
                digest(candidate["native_observations"]),
            "native_observations": candidate["native_observations"],
            "observations": candidate["observations"],
            "cursor_advanced": False,
            "commit_authorized": False, "ack_authorized": False,
        }

    try:
        held()
        chain = writer.receipts.root / proof.generation / "cursor-chain-v2"
        _directory(chain, uid)
        second = chain / "00000001"
        former_intent_raw = _read(second / "intent.json", uid)
        former_intent = json.loads(former_intent_raw)
        if (former_intent_raw != _canonical(former_intent) or
                former_intent.get("schema") != 3 or
                former_intent.get("kind") !=
                "original-learning-forward-second-slot-prepared" or
                former_intent.get("sequence") != 1 or
                former_intent.get("generation") != proof.generation):
            raise V2OriginalConfigRefused(
                "original_third_source_previous_intent_invalid")
        former = []
        for number, hostlist, _ in proof.learning:
            raw = _read(second / "native" / f"{number:03d}.json", uid)
            obj = json.loads(raw)
            if (raw != _canonical(obj) or
                    obj.get("schema") != 3 or
                    obj.get("kind") !=
                    "original-learning-forward-native-cut" or
                    obj.get("generation") != proof.generation or
                    obj.get("native_number") != number or
                    obj.get("hostlist") != hostlist or
                    obj.get("sequence") != 1 or
                    obj.get("ack_authorized") is not False):
                raise V2OriginalConfigRefused(
                    "original_third_source_previous_N_cut_invalid")
            former.append(obj["cursor"])
        names = set(os.listdir(chain))
        if names not in ({"00000000", "00000001"},
                         {"00000000", "00000001", "00000002"}):
            raise V2OriginalConfigRefused(
                "original_third_source_foreign_chain")
        slot = chain / "00000002"
        if slot.exists() or slot.is_symlink():
            _directory(slot, uid)
        else:
            # Prior to even publishing an empty slot directory, require
            # original committed second cursor/FD4+FD9/P2b attestation.
            preview()
            slot.mkdir(mode=0o700)
            _sync(chain)
        if set(os.listdir(slot)) - {"native", "intent.json"}:
            raise V2OriginalConfigRefused(
                "original_third_source_foreign_destination")
        native = slot / "native"
        if native.exists() or native.is_symlink():
            _directory(native, uid)
        else:
            if (slot / "intent.json").exists() or (
                    slot / "intent.json").is_symlink():
                raise V2OriginalConfigRefused(
                    "original_third_source_intent_without_N_receipts")
            native.mkdir(mode=0o700)
            _sync(slot)
        allowed = {f"{n:03d}.json" for n, _, _ in proof.learning}
        if set(os.listdir(native)) - allowed:
            raise V2OriginalConfigRefused(
                "original_third_source_foreign_N_receipt")

        destination = slot / "intent.json"
        if destination.exists() or destination.is_symlink():
            encoded = _read(destination, uid)
            record = json.loads(encoded)
            if (encoded != _canonical(record) or
                    set(os.listdir(slot)) != {"native", "intent.json"} or
                    set(os.listdir(native)) != allowed):
                raise V2OriginalConfigRefused(
                    "original_third_source_not_complete")
            frozen_rows = []
            for number, hostlist, _ in proof.learning:
                data = _read(native / f"{number:03d}.json", uid)
                row = json.loads(data)
                if (data != _canonical(row) or
                        row.get("kind") !=
                        "original-learning-third-native-cut" or
                        row.get("schema") != 3 or
                        row.get("generation") != proof.generation or
                        row.get("native_number") != number or
                        row.get("hostlist") != hostlist or
                        row.get("sequence") != 2 or
                        row.get("cursor_advanced") is not False or
                        row.get("ack_authorized") is not False):
                    raise V2OriginalConfigRefused(
                        "original_third_source_N_record_corrupt")
                frozen_rows.append(row)
            current = preview({
                "native": [row["cursor"] for row in frozen_rows],
                "debug": record["debug"],
            })
            repacked = pack(current, former)
            if (record != make_intent(current, former_intent, repacked) or
                    any(_read(native / name, uid) != raw
                        for name, raw in repacked)):
                raise V2OriginalConfigRefused(
                    "original_third_source_sealed_replay_changed")
            held()
            return {
                "generation": proof.generation, "sequence": 2,
                "slot": str(slot),
                "intent_sha256": hashlib.sha256(encoded).hexdigest(),
                "profiles_count": len(repacked),
                "observations_count": len(current["observations"]),
                "cursor_advanced": False,
                "commit_authorized": False, "ack_authorized": False,
            }

        candidate = preview()
        packed = pack(candidate, former)
        intent = _canonical(make_intent(candidate, former_intent, packed))
        for name, raw in packed:
            if name in os.listdir(native) and _read(native / name, uid) != raw:
                raise V2OriginalConfigRefused(
                    "original_third_source_partial_N_conflict")
        held()
        for name, raw in packed:
            _write_once(native, name, raw, uid)
        frozen = {
            "native": [json.loads(raw)["cursor"] for _, raw in packed],
            "debug": json.loads(intent)["debug"],
        }
        if (preview(frozen) != candidate or
                set(os.listdir(native)) != allowed):
            raise V2OriginalConfigRefused(
                "original_third_source_replay_before_seal_changed")
        held()
        _write_once(slot, "intent.json", intent, uid)
        if (set(os.listdir(slot)) != {"native", "intent.json"} or
                _read(destination, uid) != intent):
            raise V2OriginalConfigRefused(
                "original_third_source_manifest_not_durable")
        return {
            "generation": proof.generation, "sequence": 2,
            "slot": str(slot),
            "intent_sha256": hashlib.sha256(intent).hexdigest(),
            "profiles_count": len(packed),
            "observations_count": len(candidate["observations"]),
            "cursor_advanced": False, "commit_authorized": False,
            "ack_authorized": False,
        }
    except V2OriginalConfigRefused:
        raise
    except (ReceiptRefused, OriginalLockRefused, QueueSafetyError,
            DestinationRefused, DebugWindowRefused, OSError, ValueError,
            TypeError, KeyError, AttributeError, UnicodeError) as exc:
        raise V2OriginalConfigRefused(
            "original_third_source_unqualified_inode_or_journal") from exc
