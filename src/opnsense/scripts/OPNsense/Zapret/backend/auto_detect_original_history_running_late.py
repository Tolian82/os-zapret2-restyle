#!/usr/bin/env python3
"""Original RUNNING continuation of the existing native P2/P1/WAL.

Freeze the independently verified post-third NEW native/debug positive cut
while the original schema3 dvtws2 owner is still genuinely RUNNING.
The existing original FD4/FD9/P2a+GUI/P2b locks are required. This source
receipt freezes the source for the original DestinationCommit. The same P1,
Found-first/managed-after CAS and partial-WAL recovery process one window;
its cursor/postimages then qualify the next window without a process action.

Historic third-slot postimages stay immutable. Later original destination
plans must inherit the exact previous postimages, and each committed cursor
pins the new physical identities. Native cleanup/ACK, capacity rollover and
lifecycle activation remain separate gates; this is not an installed worker.
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
from auto_detect_debug_window import (
    ADD, _raw_hosts, _hostname, _read_exact, DebugWindowRefused,
)
from auto_detect_fd import FDState, probe_pending_fd
from auto_detect_owner import (
    LearningGenerationProof, GenerationRefused,
    attest_learning_running_generation,
)
from auto_detect_destination_commit import (
    DestinationRefused, _original_source_plan_fields, qualified_destination_plan,
    _target, _file_identity,
)
from auto_detect_original_lock_handoff import OriginalLockRefused
from auto_detect_queue import QueueSafetyError
from auto_detect_cursor_chain import MAX_STEPS


INTENT = "intent.json"


def _paths(writer, proof, sequence=3):
    chain = writer.receipts.root / proof.generation / "cursor-chain-v2"
    return chain, chain / "00000002", chain / f"{sequence:08d}"


def _source_receipt(writer, proof, physical, positive, *, sequence=3):
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
    previous = third_intent
    previous_raw, previous_progress_raw = third_raw, progress_raw
    if sequence > 3:
        previous_folder = chain / f"{sequence - 1:08d}"
        previous_raw = _read(previous_folder / INTENT, uid)
        previous = json.loads(previous_raw)
        previous_progress_raw = _read(previous_folder / "cursor-progress.json", uid)
        if (previous.get("sequence") != sequence - 1 or
                previous_raw != _canonical(previous) or
                previous.get("generation") != proof.generation):
            raise V2OriginalConfigRefused("running_late_previous_cursor_changed")
    rows = []
    by_n = {n: (hostlist, pathname) for n, hostlist, pathname in proof.learning}
    if len(physical["native"]) != len(by_n):
        raise V2OriginalConfigRefused("running_late_missing_native_N")
    for number, pathname, dev, inode, size, mtime, ctime, sha in physical["native"]:
        if (number not in by_n or pathname != by_n[number][1] or
                type(size) is not int or size < 0):
            raise V2OriginalConfigRefused("running_late_foreign_native")
        if sequence == 3:
            native_raw = _read(third / "native" / f"{number:03d}.json", uid)
            native = json.loads(native_raw)
            if native_raw != _canonical(native):
                raise V2OriginalConfigRefused("running_late_original_N_noncanonical")
            cut = native["cursor"]
        else:
            prior = next(r for r in previous["native"] if r["native_number"] == number)
            cut = {
                "new_path": prior["path"], "new_device": prior["device"],
                "new_inode": prior["inode"], "new_end": prior["frozen_end"],
                "new_end_sha256": prior["frozen_sha256"],
            }
        if (cut.get("new_path") != pathname or
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
    prior_debug = previous["debug"]
    if sequence > 3:
        prior_debug = {**prior_debug, "end": prior_debug["frozen_end"],
                       "end_sha256": prior_debug["frozen_sha256"]}
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
    result = {
        "schema": 3, "kind": "original-learning-running-fourth-source-prepared"
        if sequence == 3 else "original-learning-running-source-prepared",
        "generation": proof.generation, "sequence": sequence,
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
        # Pin every registered destination, including a HOSTLIST which
        # had no earlier discovery. A later first User event must be able
        # to continue an earlier YouTube-only physical history.
        "destination_preimages": _destination_preimages(writer, proof, post),
        "source_only": True,
        "destination_commit_authorized": False,
        "native_pending_ack_authorized": False,
        "generation_retired": False,
    }
    if sequence > 3:
        result.update(previous_source_intent_sha256=_digest(previous_raw),
                      previous_cursor_progress_sha256=_digest(previous_progress_raw))
    return result


def _destination_preimages(writer, proof, original_postimages):
    import auto_detect_original_v2_model as model
    prior, _ = read_original_learning_late_postimages(
        writer, proof, original_postimages["destinations"])
    by_key = {row["target"]: row for row in prior}
    paths = {f"writes:{name}": path for name, path in writer.targets.items()}
    paths.update({f"live:{name}": model.COMMON_ACTIVE / "managed" /
                  f"hostlist-{name}.txt" for name in ("youtube", "user")})
    rows = []
    for key, path in sorted(paths.items()):
        data, st = _target(path, writer.receipts.uid)
        row = dict(target=key, path=str(path), sha256=_digest(data),
                   device=st.st_dev, inode=st.st_ino,
                   ctime_ns=st.st_ctime_ns, mtime_ns=st.st_mtime_ns,
                   size=st.st_size,
                   last_writer_sequence=by_key.get(key, {}).get("last_writer_sequence", -1))
        if key in by_key and by_key[key] != row:
            raise V2OriginalConfigRefused("running_late_destination_predecessor_changed")
        rows.append(row)
    return rows


def _check_destination_preimages(writer, intent):
    for row in intent["destination_preimages"]:
        data, st = _target(Path(row["path"]), writer.receipts.uid)
        if (_digest(data) != row["sha256"] or _file_identity(st) != tuple(
                row[k] for k in ("device", "inode", "ctime_ns", "mtime_ns", "size"))):
            raise V2OriginalConfigRefused("running_late_original_destination_preimage_changed")


def _frozen_prefix_still_exists(writer, proof, intent, inspect):
    """Independently pin exact frozen prefixes, allowing later producer append."""
    uid, gid = writer.receipts.uid, writer.queue.writer_gid
    expected = {n: (name, path) for n, name, path in proof.learning}
    native = intent.get("native")
    if (type(native) is not list or len(native) != len(expected) or
            [r.get("native_number") for r in native] != sorted(expected)):
        raise V2OriginalConfigRefused("running_late_frozen_N_count_changed")
    seen, by_path = set(), {}
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
                _digest(raw[:row["previous_end"]]) != row["previous_sha256"] or
                inspect(path, st.st_dev, st.st_ino, owner=proof.owner,
                        writer_gid=gid) is not FDState.DRAINED):
            raise V2OriginalConfigRefused("running_late_frozen_N_changed_or_busy")
        tail = raw[row["previous_end"]:row["frozen_end"]]
        if tail:
            seen.update((n, row["hostlist"], host) for host in _raw_hosts(tail))
        by_path[str(path)] = (n, row["hostlist"])
    debug = intent["debug"]
    path = Path(debug["path"])
    if path != writer.queue.root / "debug.log":
        raise V2OriginalConfigRefused("running_late_debug_path_changed")
    st, raw = _read_exact(path, owner_uid=uid, writer_gid=gid)
    if ((st.st_dev, st.st_ino) != (debug["device"], debug["inode"]) or
            len(raw) < debug["frozen_end"] or
            _digest(raw[:debug["frozen_end"]]) != debug["frozen_sha256"] or
            _digest(raw[:debug["previous_end"]]) != debug["previous_sha256"] or
            inspect(path, st.st_dev, st.st_ino, owner=proof.owner,
                    writer_gid=gid) is not FDState.DRAINED):
        raise V2OriginalConfigRefused("running_late_frozen_debug_changed_or_busy")
    positives = set()
    tail = raw[debug["previous_end"]:debug["frozen_end"]]
    if tail and not tail.endswith(b"\n"):
        raise V2OriginalConfigRefused("running_late_frozen_debug_partial")
    for line in tail.splitlines():
        text = line.decode("ascii")
        if " : adding to " not in text:
            continue
        match = ADD.fullmatch(text)
        if match is None or not _hostname(match["host"]):
            raise V2OriginalConfigRefused("running_late_frozen_debug_malformed")
        provenance = by_path.get(match["path"])
        if provenance is None or provenance[0] != int(match["profile"]):
            raise V2OriginalConfigRefused("running_late_frozen_debug_foreign_N")
        positives.add((*provenance, match["host"]))
    expected = [{"native_number": n, "hostlist": label, "hostname": host}
                for n, label, host in sorted(seen)]
    if seen != positives or intent.get("native_positive_observations") != expected:
        raise V2OriginalConfigRefused("running_late_frozen_positive_not_physical")


def _prepared_result(slot, raw, intent):
    return {
        "generation": intent["generation"], "sequence": intent["sequence"],
        "slot": str(slot), "source_intent_sha256": _digest(raw),
        "frozen_positive_count": len(intent["native_positive_observations"]),
        "original_running_owner_freshly_reattested": True,
        "frozen_native_and_debug_prefixes_verified": True,
        "p1_destination_checkpoint_created": False,
        "native_pending_ack_authorized": False,
        "generation_retired": False,
        "operator_stop_may_be_blocked": False,
    }


def prepare_original_learning_running_late_source_locked(
        writer, proof, workspace, *, config_fd, config_path, attest,
        inspect=probe_pending_fd, sequence=3,
) -> dict:
    """Freeze/replay one original source, leaving later appends unread."""
    from auto_detect_original_history_postimages import (
        read_original_learning_independent_postimages_locked,
    )
    try:
        _held(writer, proof, workspace, config_fd, config_path, attest)
        if (not isinstance(proof, LearningGenerationProof) or
                not callable(inspect) or type(sequence) is not int or
                not 3 <= sequence < MAX_STEPS):
            raise V2OriginalConfigRefused("running_late_original_schema3_required")
        if attest_learning_running_generation() != proof:
            raise V2OriginalConfigRefused("running_late_original_owner_not_running")
        chain, _, slot = _paths(writer, proof, sequence)
        uid = writer.receipts.uid
        args = dict(config_fd=config_fd, config_path=config_path,
                    attest=attest, inspect=inspect)
        present = slot.exists() or slot.is_symlink()
        if present:
            _directory(slot, uid)
            names = set(os.listdir(slot))
            if names - {INTENT, "destination", "cursor-progress.json"}:
                raise V2OriginalConfigRefused("running_late_foreign_slot_entry")
        else:
            names = set()
        if INTENT in names:
            raw = _read(slot / INTENT, uid)
            frozen = json.loads(raw)
            _original_source_plan_fields(slot, frozen, uid)
            if (frozen.get("sequence") != sequence or
                    any(frozen.get(k) != value for k, value in (
                        ("generation", proof.generation),
                        ("owner_pid", proof.owner.pid),
                        ("owner_start", proof.owner.started),
                        ("native_map_sha256", proof.native_map_sha256)))):
                raise V2OriginalConfigRefused("running_late_existing_source_foreign")
            if "destination" in names:
                journal = slot / "destination"
                _directory(journal, uid)
                entries = set(os.listdir(journal))
                if entries:
                    qualified_destination_plan(slot, frozen, uid, targets=writer.targets)
                else:
                    # Original writer crashed after mkdir, before plan.
                    # No CAS was authorized: the exact previous images
                    # must still be current before preparing that plan.
                    read_original_learning_independent_postimages_locked(
                        writer, proof, workspace, **args)
                    _check_destination_preimages(writer, frozen)
            else:
                read_original_learning_independent_postimages_locked(
                    writer, proof, workspace, **args)
                _check_destination_preimages(writer, frozen)
        else:
            if names:
                raise V2OriginalConfigRefused("running_late_missing_original_intent")
            before = read_original_learning_independent_postimages_locked(
                writer, proof, workspace, **args)
            first = _positive_snapshot_once(writer, proof, inspect, sequence=sequence - 1)
            second = _positive_snapshot_once(writer, proof, inspect, sequence=sequence - 1)
            if first != second or not first["positive"]:
                raise V2OriginalConfigRefused("running_late_no_stable_positive_new")
            positive = {
                "positive_event_count": len(first["positive"]),
                "positive_native_observations": [
                    {"native_number": n, "hostlist": name, "hostname": host}
                    for n, name, host in first["positive"]],
                "postimages_sha256": before["postimages_sha256"],
            }
            frozen = _source_receipt(writer, proof, first, positive, sequence=sequence)
            _check_destination_preimages(writer, frozen)
            raw = _canonical(frozen)
            if (attest_learning_running_generation() != proof or
                    _positive_snapshot_once(writer, proof, inspect,
                                            sequence=sequence - 1) != first or
                    read_original_learning_independent_postimages_locked(
                        writer, proof, workspace, **args) != before):
                raise V2OriginalConfigRefused("running_late_source_raced_before_seal")
            _held(writer, proof, workspace, config_fd, config_path, attest)
            if not present:
                slot.mkdir(mode=0o700)
                _sync(chain)
            _directory(slot, uid)
            if os.listdir(slot):
                raise V2OriginalConfigRefused("running_late_empty_slot_raced")
            _write_once(slot, INTENT, raw, uid)
            _original_source_plan_fields(slot, frozen, uid)
        for _ in range(2):
            _frozen_prefix_still_exists(writer, proof, frozen, inspect)
            _held(writer, proof, workspace, config_fd, config_path, attest)
            if attest_learning_running_generation() != proof:
                raise V2OriginalConfigRefused("running_late_wal_owner_changed")
        if _read(slot / INTENT, uid) != raw:
            raise V2OriginalConfigRefused("running_late_wal_source_raced")
        return _prepared_result(slot, raw, frozen)
    except V2OriginalConfigRefused:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, ReceiptRefused, DestinationRefused,
            GenerationRefused, OriginalLockRefused, QueueSafetyError,
            DebugWindowRefused, StopIteration) as exc:
        raise V2OriginalConfigRefused("running_late_original_source_not_safe") from exc


def commit_original_learning_running_late(writer, proof, workspace, *, sequence=3, **kwargs):
    """Remaining NEW through the original P1 and sole DestinationCommit.

    No native mutation/ACK, process action or Config write is performed.
    This uses exactly the third-slot consumer and partial-CAS recovery;
    only the original frozen source adapter differs.
    """
    from auto_detect_original_v2_model import _commit_with_original_learning_slot

    def prepare(*args, **context):
        result = prepare_original_learning_running_late_source_locked(
            *args, sequence=sequence, **context)
        return {
            **result, "intent_sha256": result["source_intent_sha256"],
            "cursor_advanced": False, "commit_authorized": False,
            "ack_authorized": False,
        }

    result = _commit_with_original_learning_slot(
        writer, proof, workspace, sequence=sequence, prepare=prepare, **kwargs)
    context = {key: kwargs[key] for key in ("config_fd", "config_path", "attest")}
    inspect = kwargs.get("inspect", probe_pending_fd)
    with writer.exclusive_targets():
        _held(writer, proof, workspace, **context)
        _, _, slot = _paths(writer, proof, sequence)
        if not (slot / "cursor-progress.json").exists():
            # The committed checkpoint cannot be replayed as a fresh P1.
            # Publish only its physical postimage/cursor continuation.
            source = json.loads(_read(slot / INTENT, writer.receipts.uid))
            _frozen_prefix_still_exists(writer, proof, source, inspect)
            base = json.loads(_read(_history_root(writer, proof) /
                                    "postimages.json", writer.receipts.uid))
            rows, progress = read_original_learning_late_postimages(
                writer, proof, base["destinations"], allow_unsealed=True,
                through_sequence=sequence)
            if attest_learning_running_generation() != proof:
                raise V2OriginalConfigRefused("running_late_progress_owner_changed")
            _held(writer, proof, workspace, **context)
            _write_once(slot, "cursor-progress.json", _canonical(progress), writer.receipts.uid)
            _frozen_prefix_still_exists(writer, proof, source, inspect)
            read_original_learning_late_postimages(writer, proof, base["destinations"])
        return result


def _running_progress_record(intent, intent_raw, plan_raw, cp_raw, rows):
    return {
        "schema": 3, "kind": "original-learning-running-cursor-progress",
        "generation": intent["generation"], "sequence": intent["sequence"],
        "source_intent_sha256": _digest(intent_raw),
        "destination_plan_sha256": _digest(plan_raw),
        "destination_checkpoint_sha256": _digest(cp_raw),
        "previous_cursor_progress_sha256": intent.get(
            "previous_cursor_progress_sha256", intent["third_cursor_progress_sha256"]),
        "original_third_postimages_sha256": intent["original_third_postimages_sha256"],
        "destination_postimages": rows,
        "cursor_advanced": True, "native_pending_ack_authorized": False,
        "generation_retired": False,
    }


def _read_late_slot_postimages(
        writer, proof, base_rows, slot, *, allow_unsealed=False, verify_current=True):
    """Follow original before→after lineage; never rewrite historic receipts.

    A legitimate later CAS replaces earlier physical inodes. Its original
    plan must use precisely the earlier sealed postimage as its preimage;
    a completed cursor pins the resulting physical inode again. Historical
    OLD proofs can follow that lineage without replaying a destination or
    mistaking a GUI edit for an authorized continuation.
    """
    uid = writer.receipts.uid
    sequence = int(slot.name)
    if not (slot / "destination").exists() and not (slot / "destination").is_symlink():
        return base_rows, None
    intent_raw = _read(slot / INTENT, uid)
    intent = json.loads(intent_raw)
    plan, plan_raw = qualified_destination_plan(slot, intent, uid, targets=writer.targets)
    source = _original_source_plan_fields(slot, intent, uid)
    cp_raw = _read(slot / "destination" / "checkpoint.json", uid)
    cp = {
        "schema": 1, "kind": "destination-and-cursor-committed",
        "generation": proof.generation, "pending_name": source["pending_name"],
        "plan_sha256": _digest(plan_raw), "evidence": "learning-native-debug",
        "committed_cursor_offset": source["debug_end_offset"],
        "committed_cursor_sha256": source["debug_end_sha256"],
        "ack_authorized": False,
    }
    if cp_raw != _canonical(cp) or "live" not in plan:
        raise V2OriginalConfigRefused("running_late_lineage_incomplete_destination")
    baseline = {r["target"]: r for r in base_rows}
    if len(baseline) != len(base_rows):
        raise V2OriginalConfigRefused("running_late_lineage_repeated_target")
    preimages = {r["target"]: r for r in intent["destination_preimages"]}
    if any(preimages.get(key) != row for key, row in baseline.items()):
        raise V2OriginalConfigRefused("running_late_lineage_predecessor_not_sealed")
    baseline = preimages
    updates = {f"{kind}:{name}": row for kind in ("writes", "live")
               for name, row in plan[kind].items()}
    if set(updates) - set(baseline):
        raise V2OriginalConfigRefused("running_late_lineage_unpinned_predecessor")
    progress_path = slot / "cursor-progress.json"
    progress_raw = None
    if progress_path.exists() or progress_path.is_symlink():
        progress_raw = _read(progress_path, uid)
        saved = json.loads(progress_raw)
        rows = saved["destination_postimages"]
    elif allow_unsealed and verify_current:
        rows = []
        for key, before in sorted(baseline.items()):
            data, st = _target(Path(before["path"]), uid)
            row = dict(before)
            if key in updates:
                row.update(sha256=_digest(data), device=st.st_dev, inode=st.st_ino,
                           ctime_ns=st.st_ctime_ns, mtime_ns=st.st_mtime_ns,
                           size=st.st_size, last_writer_sequence=sequence)
            rows.append(row)
    else:
        raise V2OriginalConfigRefused("running_late_lineage_cursor_missing")
    actual_rows = {r["target"]: r for r in rows}
    if len(actual_rows) != len(rows) or set(actual_rows) != set(baseline):
        raise V2OriginalConfigRefused("running_late_lineage_target_set_changed")
    for key, before in baseline.items():
        after = actual_rows[key]
        change = updates.get(key)
        if change is None:
            if after != before:
                raise V2OriginalConfigRefused("running_late_lineage_untouched_target_changed")
        elif (change["path"] != before["path"] or
                change["before"] != before["sha256"] or
                any(change["before_" + field] != before[field]
                    for field in ("device", "inode", "ctime_ns", "mtime_ns", "size")) or
                set(after) != set(before) or after["target"] != key or
                after["path"] != before["path"] or
                after["sha256"] != change["after"] or
                after["last_writer_sequence"] != sequence):
            raise V2OriginalConfigRefused("running_late_lineage_not_original_CAS")
        if verify_current:
            data, st = _target(Path(after["path"]), uid)
            if (_digest(data) != after["sha256"] or _file_identity(st) != tuple(
                    after[field] for field in ("device", "inode", "ctime_ns", "mtime_ns", "size"))):
                raise V2OriginalConfigRefused("running_late_lineage_physical_postimage_changed")
    expected = _running_progress_record(intent, intent_raw, plan_raw, cp_raw, rows)
    if progress_raw is not None and progress_raw != _canonical(expected):
        raise V2OriginalConfigRefused("running_late_lineage_progress_changed")
    return rows, expected


def read_original_learning_late_postimages(
        writer, proof, base_rows, *, allow_unsealed=False, verify_current=True,
        through_sequence=None):
    """Follow completed original slots in order; inspect only the final inodes."""
    chain, _, _ = _paths(writer, proof)
    if through_sequence is None:
        through_sequence = MAX_STEPS - 1
    _directory(chain, writer.receipts.uid)
    names = set(os.listdir(chain))
    if any(len(name) != 8 or not name.isascii() or not name.isdecimal()
           for name in names):
        raise V2OriginalConfigRefused("running_late_foreign_cursor_slot")
    sequences = sorted(int(name) for name in names)
    if sequences != list(range(len(sequences))) or len(sequences) > MAX_STEPS:
        raise V2OriginalConfigRefused("running_late_cursor_gap_or_capacity")
    slots = []
    for sequence in sequences:
        if sequence < 3 or sequence > through_sequence:
            continue
        slot = chain / f"{sequence:08d}"
        _directory(slot, writer.receipts.uid)
        journal = slot / "destination"
        if journal.exists() or journal.is_symlink():
            _directory(journal, writer.receipts.uid)
            entries = set(os.listdir(journal))
            if entries:
                slots.append(slot)
            elif sequence != sequences[-1]:
                raise V2OriginalConfigRefused("running_late_empty_predecessor_WAL")
        elif sequence != sequences[-1]:
            raise V2OriginalConfigRefused("running_late_uncommitted_predecessor")
    rows, progress = base_rows, None
    for index, slot in enumerate(slots):
        final = index == len(slots) - 1
        rows, progress = _read_late_slot_postimages(
            writer, proof, rows, slot,
            allow_unsealed=allow_unsealed and final,
            verify_current=verify_current and final)
    return rows, progress


def process_original_learning_running_late_once(writer, proof, workspace, **kwargs):
    """One bounded continuation, or idle; reuse a torn slot before a new one.

    This is a consumer in the existing Config-held P2 pipeline. Activation
    remains guarded until native ACK, source compaction and lifecycle are
    qualified together. The caller owns the original queue and Config FDs.
    """
    context = {key: kwargs[key] for key in ("config_fd", "config_path", "attest")}
    inspect = kwargs.get("inspect", probe_pending_fd)
    with writer.exclusive_targets():
        _held(writer, proof, workspace, **context)
        if attest_learning_running_generation() != proof:
            raise V2OriginalConfigRefused("running_late_cycle_owner_not_running")
        chain, _, _ = _paths(writer, proof)
        _directory(chain, writer.receipts.uid)
        names = set(os.listdir(chain))
        if any(len(n) != 8 or not n.isascii() or not n.isdecimal() for n in names):
            raise V2OriginalConfigRefused("running_late_cycle_foreign_slot")
        seqs = sorted(int(n) for n in names)
        if seqs != list(range(len(seqs))) or len(seqs) < 3:
            raise V2OriginalConfigRefused("running_late_cycle_original_chain_missing")
        last = seqs[-1]
        if last >= 3 and not (chain / f"{last:08d}" / "cursor-progress.json").exists():
            sequence = last
        else:
            from auto_detect_original_history_postimages import (
                read_original_learning_independent_postimages_locked,
            )
            read_original_learning_independent_postimages_locked(
                writer, proof, workspace, inspect=inspect, **context)
            first = _positive_snapshot_once(writer, proof, inspect, sequence=last)
            second = _positive_snapshot_once(writer, proof, inspect, sequence=last)
            if first != second:
                raise V2OriginalConfigRefused("running_late_cycle_source_raced")
            if not first["positive"]:
                _held(writer, proof, workspace, **context)
                if attest_learning_running_generation() != proof:
                    raise V2OriginalConfigRefused("running_late_idle_owner_changed")
                return None
            sequence = last + 1
        if sequence >= MAX_STEPS:
            raise V2OriginalConfigRefused("running_late_original_chain_capacity")
    return commit_original_learning_running_late(
        writer, proof, workspace, sequence=sequence, **kwargs)


def main():
    raise SystemExit("Original RUNNING late source is not a worker")


if __name__ == "__main__":
    main()
