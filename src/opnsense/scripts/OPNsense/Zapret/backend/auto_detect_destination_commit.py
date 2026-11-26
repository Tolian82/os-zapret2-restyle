#!/usr/bin/env python3
"""#1052 P2k8p: one v2 per-slot P2k2b destination CAS/checkpoint owner.

Original P2a queue, original Config/P1 and GUI destination flocks must be
held by the caller. No superseded single-intent destination entrypoint.
"""
from __future__ import annotations

from contextlib import contextmanager

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused, _canonical, _read, _sync, _write_once, _directory
from auto_detect_queue import DurableInbox

MAX_TARGET = 4 * 1024 * 1024
HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class DestinationRefused(ReceiptRefused):
    """The unacknowledged source stays retained on any unsafe destination."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _target(path: Path, uid: int, *, links: int = 1) -> tuple[bytes, os.stat_result]:
    """Strict regular-file snapshot; never trust a symlink or a stale FD."""
    try:
        parent = path.parent.lstat()
        st = path.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid or
                parent.st_mode & 0o022 or
                not stat.S_ISREG(st.st_mode) or st.st_uid != uid or
                st.st_nlink != links or st.st_mode & 0o022 or
                st.st_size > MAX_TARGET):
            raise DestinationRefused("unsafe_destination")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            a = os.fstat(fd)
            data = os.read(fd, MAX_TARGET + 1)
            b = os.fstat(fd)
        finally:
            os.close(fd)
        identity = _target_identity(st)
        if (identity != _target_identity(a) or identity != _target_identity(b) or
                identity != _target_identity(path.lstat()) or len(data) != st.st_size):
            raise DestinationRefused("destination_changed_during_read")
        data.decode("utf-8")
        return data, st
    except (OSError, UnicodeError) as exc:
        raise DestinationRefused("destination_read_failed") from exc


def _edit(before: bytes, add: list[str], remove: list[str]) -> bytes:
    if (not isinstance(add, list) or not isinstance(remove, list) or
            len(add) + len(remove) > 4096 or
            any(type(x) is not str or not HOST.fullmatch(x) or ".." in x
                for x in add + remove)):
        raise DestinationRefused("invalid_domain_effects")
    text = before.decode("utf-8")
    # Preserve every non-owned modifier, comment and existing user row verbatim.
    lines = text.splitlines(keepends=True)
    removed = set(remove)
    out = [line for line in lines if line.rstrip("\r\n") not in removed]
    present = {line.rstrip("\r\n") for line in out}
    for host in sorted(set(add)):
        if host not in present:
            if out and not out[-1].endswith("\n"):
                out.append("\n")
            out.append(host + "\n")
            present.add(host)
    result = "".join(out).encode("utf-8")
    if len(result) > MAX_TARGET:
        raise DestinationRefused("destination_growth_limit")
    return result


def _file_identity(st: os.stat_result) -> tuple:
    return st.st_dev, st.st_ino, st.st_ctime_ns, st.st_mtime_ns, st.st_size


def _target_identity(st: os.stat_result) -> tuple:
    return (*_file_identity(st), st.st_mode, st.st_uid, st.st_gid, st.st_nlink)


def _stage_pin(st: os.stat_result, data: bytes) -> dict:
    return {"device": st.st_dev, "inode": st.st_ino, "mtime_ns": st.st_mtime_ns,
            "size": st.st_size, "sha256": _sha(data)}


def _native_list_modification_visible(before: os.stat_result,
                                      after: os.stat_result) -> bool:
    """Match pinned Zapret2 v1.0.7 FILE_MOD_COMPARE: mtime(ns) + size.

    An atomic inode change with identical mtime and size would be invisible
    to the running engine's next-packet reload check. Never checkpoint or
    acknowledge such a replacement; leave the old file and P2 pending.
    """
    return (before.st_mtime_ns != after.st_mtime_ns or
            before.st_size != after.st_size)


def _replace(path: Path, current: bytes, expected: bytes, uid: int, *,
             stage_fn=None, expected_identity=None) -> None:
    """One protected same-directory replace after read-side CAS under GUI lock."""
    now, st = _target(path, uid)
    if now != current or (expected_identity is not None and
                          expected_identity not in (_file_identity(st), _target_identity(st))):
        raise DestinationRefused("destination_conflict_with_gui")
    temp = path.parent / (".auto-detect-" + secrets.token_hex(16) + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    created = None
    try:
        created = os.fstat(fd)
        os.fchown(fd, st.st_uid, st.st_gid)
        os.fchmod(fd, stat.S_IMODE(st.st_mode))
        data = memoryview(expected)
        while data:
            n = os.write(fd, data)
            if n <= 0:
                raise DestinationRefused("short_destination_write")
            data = data[n:]
        os.fsync(fd)
        written = os.fstat(fd)

        # Upstream v1.0.7 compares mtime+size, NOT inode or content SHA.
        # Check the actual fsynced staged inode, before its atomic rename.
        # A same-signature replacement is not proof of a native hot reload.
        staged_bytes, staged_stat = _target(temp, uid)
        staged_identity = _target_identity(written)
        if staged_bytes != expected or _target_identity(staged_stat) != staged_identity:
            raise DestinationRefused("original_staged_temp_changed")
        if (current != expected and
                not _native_list_modification_visible(st, staged_stat)):
            raise DestinationRefused("native_list_reload_signature_unchanged")
        if stage_fn is not None:
            # Persist the inode observed through the writer's own descriptor.
            stage_fn("ready", temp, expected, written)
            staged_bytes, staged_stat = _target(temp, uid)
            if staged_bytes != expected or _target_identity(staged_stat) != staged_identity:
                raise DestinationRefused("original_staged_temp_changed")

        # Recheck the destination at the rename boundary after stage fsync.
        again, check = _target(path, uid)
        if again != current or _target_identity(check) != _target_identity(st):
            raise DestinationRefused("destination_conflict_with_gui")
        if _target_identity(temp.lstat()) != staged_identity:
            raise DestinationRefused("original_staged_temp_changed")
        os.replace(temp, path)
        _sync(path.parent)
        if stage_fn is not None:
            installed, installed_stat = _target(path, uid)
            if installed != expected or not os.path.samestat(installed_stat, written):
                raise DestinationRefused("original_staged_inode_changed_at_rename")
            stage_fn("installed", path, installed, installed_stat)
    finally:
        # Keep the original inode open until cleanup so its number cannot
        # be recycled for another file at the temporary path.
        try:
            try:
                current_temp = temp.lstat()
            except FileNotFoundError:
                pass
            else:
                if created is not None and os.path.samestat(created, current_temp):
                    temp.unlink()
                    _sync(path.parent)
        finally:
            os.close(fd)



@contextmanager
def exclusive_destination_lock(gui_lock: Path, owner_uid: int):
    """Shared native root flock for GUI save/read and P2k4 destination writes.

    This lock is intentionally independent of queue/FD9/Config locks; GUI
    edits neither assume nor acquire authority to mutate config.xml.
    """
    path = Path(gui_lock)
    if not path.is_absolute():
        raise DestinationRefused("unsafe_gui_lock_path")
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != owner_uid
            or parent.st_mode & 0o022):
        raise DestinationRefused("unsafe_gui_lock_directory")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        name = path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != owner_uid or
                stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or
                (st.st_dev, st.st_ino) != (name.st_dev, name.st_ino)):
            raise DestinationRefused("unsafe_gui_lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DestinationRefused("gui_writer_busy") from None
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _original_third_source_plan_fields(
        folder: Path, intent: dict, uid: int) -> dict:
    """Bind the third N-window to the SAME committed original cursor/WAL.

    This is a *read-only* source-plan verifier, not a new writer or a
    destination commit. The previous destination's exact checkpoint and
    cursor progress MUST be durable before the third intent can qualify.
    No physical native cleanup, pending ACK or generation retirement.
    """
    if (folder.name != "00000002" or
            folder.parent.name != "cursor-chain-v2" or
            folder.parent.parent.name != intent.get("generation") or
            intent.get("schema") != 3 or
            intent.get("sequence") != 2 or
            intent.get("kind") != "original-learning-third-slot-prepared" or
            intent.get("cursor_advanced") is not False or
            intent.get("commit_authorized") is not False or
            intent.get("ack_authorized") is not False):
        raise DestinationRefused("original_third_source_wrong_chain")
    _directory(folder, uid)
    source_raw = _read(folder / "intent.json", uid)
    if (source_raw != _canonical(intent) or
            not isinstance(intent.get("observations"), list) or
            not isinstance(intent.get("native_observations"), list)):
        raise DestinationRefused("original_third_source_intent_not_durable")

    second_slot = folder.parent / "00000001"
    _directory(second_slot, uid)
    second_raw = _read(second_slot / "intent.json", uid)
    try:
        second = json.loads(second_raw)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise DestinationRefused("original_third_source_second_invalid") from exc
    if (second_raw != _canonical(second) or
            second.get("schema") != 3 or
            second.get("kind") !=
            "original-learning-forward-second-slot-prepared" or
            second.get("sequence") != 1 or
            second.get("generation") != intent["generation"] or
            _sha(second_raw) != intent.get("previous_source_intent_sha256")):
        raise DestinationRefused("original_third_source_second_unbound")
    # This recursion follows only the fixed second->first direction.
    # It independently checks the first original destination checkpoint,
    # physical-rebind receipt SHA and ALL second-slot native receipts.
    second_plan, second_plan_raw = qualified_destination_plan(
        second_slot, second, uid)
    second_cp_raw = _read(
        second_slot / "destination" / "checkpoint.json", uid)
    second_checkpoint = json.loads(second_cp_raw)
    if (second_cp_raw != _canonical(second_checkpoint) or
            second_checkpoint != {
                "schema": 1,
                "kind": "destination-and-cursor-committed",
                "generation": intent["generation"],
                "pending_name": "learning-00000001",
                "plan_sha256": _sha(second_plan_raw),
                "evidence": "learning-native-debug",
                "committed_cursor_offset": second["debug"]["end"],
                "committed_cursor_sha256": second["debug"]["end_sha256"],
                "ack_authorized": False} or
            second_plan.get("schema") != 3 or
            "live" not in second_plan):
        raise DestinationRefused("original_third_source_second_uncommitted")
    second_progress_raw = _read(
        second_slot / "cursor-progress.json", uid)
    second_progress = json.loads(second_progress_raw)
    expected_progress = {
        "schema": 3,
        "kind": "original-learning-forward-cursor-progress",
        "generation": second["generation"],
        "sequence": 1,
        "owner_pid": second["owner_pid"],
        "owner_start": second["owner_start"],
        "operation_id": second["operation_id"],
        "native_map_sha256": second["native_map_sha256"],
        "first_slot_sha256": second["first_slot_sha256"],
        "native_rebind_manifest_sha256":
            second["native_rebind_manifest_sha256"],
        "source_intent_sha256": _sha(second_raw),
        "destination_plan_sha256": _sha(second_plan_raw),
        "destination_checkpoint_sha256": _sha(second_cp_raw),
        "profiles_count": second["profiles_count"],
        "native_cursor_receipts_sha256": second["profiles_sha256"],
        "debug": second["debug"],
        "cursor_advanced": True,
        "native_pending_ack_authorized": False,
        "native_cleanup_authorized": False,
        "generation_retired": False,
    }
    if (second_progress != expected_progress or
            second_progress_raw != _canonical(second_progress) or
            _sha(second_progress_raw) !=
            intent.get("previous_cursor_progress_sha256")):
        raise DestinationRefused("original_third_source_second_progress_changed")

    # Attestation of sequence identity before any per-N physical cursor.
    owner_fields = ("owner_pid", "owner_start", "operation_id",
                    "owner_candidate_sha256", "final_args_sha256",
                    "native_map_sha256", "first_slot_sha256",
                    "native_rebind_manifest_sha256")
    if (any(intent.get(k) != second.get(k) for k in owner_fields) or
            type(intent.get("profiles_count")) is not int or
            intent["profiles_count"] != second["profiles_count"] or
            not 0 < intent["profiles_count"] <= 255):
        raise DestinationRefused("original_third_source_foreign_owner_or_n")

    second_debug = second["debug"]
    debug = intent.get("debug")
    if (type(debug) is not dict or
            set(debug) != set(second_debug) or
            any(debug[k] != second_debug[k]
                for k in ("device", "inode", "start", "start_sha256")) or
            type(debug.get("end")) is not int or
            debug["end"] < second_debug["end"] or
            type(debug.get("end_sha256")) is not str or
            not SHA256.fullmatch(debug["end_sha256"])):
        raise DestinationRefused("original_third_source_debug_cursor_changed")

    native_folder = folder / "native"
    second_native = second_slot / "native"
    _directory(native_folder, uid)
    _directory(second_native, uid)
    first = json.loads(_read(
        folder.parent / "00000000" / "intent.json", uid))
    if (len(first.get("native", [])) != intent["profiles_count"] or
            first.get("generation") != intent["generation"]):
        raise DestinationRefused("original_third_source_first_map_invalid")
    native_digests = []
    valid_profiles = set()
    expected_names = set()
    saw_unread = False
    for root in first["native"]:
        number, hostlist = root["native_number"], root["hostlist"]
        name = f"{number:03d}.json"
        expected_names.add(name)
        valid_profiles.add((number, hostlist))
        previous_raw = _read(second_native / name, uid)
        prior = json.loads(previous_raw)
        # This was already verified by qualified_destination_plan(second).
        if (prior.get("kind") != "original-learning-forward-native-cut" or
                prior.get("native_number") != number or
                prior.get("hostlist") != hostlist):
            raise DestinationRefused("original_third_source_previous_N_changed")
        child_raw = _read(native_folder / name, uid)
        child = json.loads(child_raw)
        if (child_raw != _canonical(child) or
                type(child) is not dict or
                set(child) != {
                    "schema", "kind", "generation", "sequence",
                    "previous_source_intent_sha256",
                    "previous_cursor_progress_sha256",
                    "native_number", "hostlist", "cursor",
                    "cursor_advanced", "ack_authorized"} or
                child["schema"] != 3 or
                child["kind"] != "original-learning-third-native-cut" or
                child["generation"] != intent["generation"] or
                child["sequence"] != 2 or
                child["native_number"] != number or
                child["hostlist"] != hostlist or
                child["previous_source_intent_sha256"] != _sha(second_raw) or
                child["previous_cursor_progress_sha256"] !=
                _sha(second_progress_raw) or
                child["cursor_advanced"] is not False or
                child["ack_authorized"] is not False):
            raise DestinationRefused("original_third_source_N_unbound")
        original = prior["cursor"]
        current = child["cursor"]
        if (type(current) is not dict or
                set(current) != set(original) or
                any(current.get(k) != value for k, value in original.items()
                    if k not in ("old_end", "old_end_sha256",
                                 "new_end", "new_end_sha256"))):
            raise DestinationRefused("original_third_source_N_identity_changed")
        for side in ("old", "new"):
            old_end = original[f"{side}_end"]
            new_end = current[f"{side}_end"]
            old_sha = original[f"{side}_end_sha256"]
            new_sha = current[f"{side}_end_sha256"]
            if old_end is None:
                if (new_end is not None or new_sha is not None or
                        old_sha is not None):
                    raise DestinationRefused("original_third_source_partial_new_inode")
                continue
            if (type(old_end) is not int or
                    type(new_end) is not int or
                    new_end < old_end or
                    type(old_sha) is not str or
                    type(new_sha) is not str or
                    not SHA256.fullmatch(old_sha) or
                    not SHA256.fullmatch(new_sha)):
                raise DestinationRefused("original_third_source_cursor_regressed")
            saw_unread |= new_end > old_end
        native_digests.append(hashlib.sha256(child_raw).digest())
    if (set(os.listdir(native_folder)) != expected_names or
            set(os.listdir(second_native)) != expected_names or
            not saw_unread or
            type(intent.get("profiles_sha256")) is not str or
            _sha(b"".join(native_digests)) != intent["profiles_sha256"]):
        raise DestinationRefused("original_third_source_N_receipts_incomplete")

    observations = intent["observations"]
    native_observations = intent["native_observations"]
    if (not 0 < len(observations) <= 4096 or
            len(observations) != intent.get("observations_count") or
            len(native_observations) != len(observations) or
            any(type(row) is not dict or
                set(row) != {"native_number", "hostlist", "hostname"} or
                type(row["native_number"]) is not int or
                type(row["hostlist"]) is not str or
                type(row["hostname"]) is not str or
                (row["native_number"], row["hostlist"]) not in
                valid_profiles or
                not HOST.fullmatch(row["hostname"]) or
                ".." in row["hostname"]
                for row in native_observations)):
        raise DestinationRefused("original_third_source_attribution_invalid")
    ordered = [(x["native_number"], x["hostlist"], x["hostname"])
               for x in native_observations]
    if (ordered != sorted(set(ordered)) or
            observations != [{"hostname": host, "hostlist": label}
                             for _, label, host in ordered] or
            _sha(json.dumps(
                observations, sort_keys=True,
                separators=(",", ":")).encode()) !=
            intent.get("observations_sha256") or
            _sha(json.dumps(
                native_observations, sort_keys=True,
                separators=(",", ":")).encode()) !=
            intent.get("native_observations_sha256")):
        raise DestinationRefused("original_third_source_observations_not_bound")

    return {
        "schema": 3, "kind": "durable-destination-plan",
        "generation": intent["generation"],
        "pending_name": "learning-00000002",
        "pending_sha256": _sha(
            _canonical({"observations": observations})),
        "evidence": "learning-native-debug",
        "debug_end_offset": debug["end"],
        "debug_end_sha256": debug["end_sha256"],
        "source_intent_sha256": _sha(source_raw),
        "previous_cursor_progress_sha256": _sha(second_progress_raw),
    }


def _original_running_late_source_plan_fields(folder: Path, intent: dict,
                                             uid: int) -> dict:
    """Continue the original WAL from the sealed third native cursor.

    This validates source provenance only. Physical prefix/FD/owner proof
    remains the original consumer's responsibility on every invocation.
    """
    from auto_detect_cursor_chain import MAX_STEPS
    sequence = intent.get("sequence")
    if (type(sequence) is not int or not 3 <= sequence < MAX_STEPS or
            folder.name != f"{sequence:08d}" or
            folder.parent.name != "cursor-chain-v2" or
            folder.parent.parent.name != intent.get("generation") or
            intent.get("schema") != 3 or
            intent.get("kind") != ("original-learning-running-fourth-source-prepared"
                                    if sequence == 3 else "original-learning-running-source-prepared") or
            intent.get("source_only") is not True or
            intent.get("destination_commit_authorized") is not False or
            intent.get("native_pending_ack_authorized") is not False or
            intent.get("generation_retired") is not False):
        raise DestinationRefused("running_late_source_wrong_original_chain")
    _directory(folder, uid)
    source_raw = _read(folder / "intent.json", uid)
    if source_raw != _canonical(intent):
        raise DestinationRefused("running_late_source_not_durable")
    third_folder = folder.parent / "00000002"
    third_raw = _read(third_folder / "intent.json", uid)
    third = json.loads(third_raw)
    plan, plan_raw = qualified_destination_plan(third_folder, third, uid)
    cp_raw = _read(third_folder / "destination" / "checkpoint.json", uid)
    cp = json.loads(cp_raw)
    expected_cp = {
        "schema": 1, "kind": "destination-and-cursor-committed",
        "generation": intent["generation"], "pending_name": "learning-00000002",
        "plan_sha256": _sha(plan_raw), "evidence": "learning-native-debug",
        "committed_cursor_offset": third["debug"]["end"],
        "committed_cursor_sha256": third["debug"]["end_sha256"],
        "ack_authorized": False,
    }
    progress_raw = _read(third_folder / "cursor-progress.json", uid)
    progress = json.loads(progress_raw)
    # Import lazily: the original model itself consumes this plan codec.
    from auto_detect_original_v2_model import _original_learning_third_progress_record
    if (third_raw != _canonical(third) or cp_raw != _canonical(expected_cp) or
            cp != expected_cp or plan.get("schema") != 3 or "live" not in plan or
            progress_raw != _canonical(_original_learning_third_progress_record(
                third, third_raw, cp_raw, cp, progress["destination_postimages"])) or
            intent.get("third_source_intent_sha256") != _sha(third_raw) or
            intent.get("third_cursor_progress_sha256") != _sha(progress_raw) or
            any(intent.get(k) != third.get(k) for k in (
                "generation", "owner_pid", "owner_start", "operation_id",
                "native_map_sha256"))):
        raise DestinationRefused("running_late_third_checkpoint_or_owner_changed")
    post_raw = _read(third_folder / "pending-ack-archive" / "history" /
                     "postimages.json", uid)
    post = json.loads(post_raw)
    if (post_raw != _canonical(post) or
            _sha(post_raw) != intent.get("original_third_postimages_sha256") or
            post.get("generation") != intent["generation"] or
            post.get("third_cursor_progress_sha256") != _sha(progress_raw)):
        raise DestinationRefused("running_late_original_postimages_changed")
    previous, previous_progress_raw = third, progress_raw
    if sequence > 3:
        previous_folder = folder.parent / f"{sequence - 1:08d}"
        previous_raw = _read(previous_folder / "intent.json", uid)
        previous = json.loads(previous_raw)
        previous_plan, previous_plan_raw = qualified_destination_plan(
            previous_folder, previous, uid)
        previous_cp_raw = _read(previous_folder / "destination" / "checkpoint.json", uid)
        # qualified_destination_plan() already verified that predecessor's
        # complete source lineage. Reuse its bound fields; recursing a
        # second time here makes a minute grow exponentially with history.
        previous_source = previous_plan
        previous_cp = {
            "schema": 1, "kind": "destination-and-cursor-committed",
            "generation": intent["generation"],
            "pending_name": previous_source["pending_name"],
            "plan_sha256": _sha(previous_plan_raw), "evidence": "learning-native-debug",
            "committed_cursor_offset": previous_source["debug_end_offset"],
            "committed_cursor_sha256": previous_source["debug_end_sha256"],
            "ack_authorized": False,
        }
        previous_progress_raw = _read(previous_folder / "cursor-progress.json", uid)
        previous_progress = json.loads(previous_progress_raw)
        from auto_detect_original_history_running_late import _running_progress_record
        if (previous_raw != _canonical(previous) or
                previous.get("sequence") != sequence - 1 or
                any(intent.get(k) != previous.get(k) for k in (
                    "generation", "owner_pid", "owner_start", "operation_id",
                    "native_map_sha256", "third_source_intent_sha256",
                    "third_cursor_progress_sha256", "original_third_postimages_sha256")) or
                intent.get("previous_source_intent_sha256") != _sha(previous_raw) or
                intent.get("previous_cursor_progress_sha256") != _sha(previous_progress_raw) or
                previous_cp_raw != _canonical(previous_cp) or "live" not in previous_plan or
                previous_progress_raw != _canonical(_running_progress_record(
                    previous, previous_raw, previous_plan_raw, previous_cp_raw,
                    previous_progress["destination_postimages"]))):
            raise DestinationRefused("running_late_previous_WAL_unqualified")
    native = intent.get("native")
    if (type(native) is not list or
            len(native) != third.get("profiles_count") or not 0 < len(native) <= 255):
        raise DestinationRefused("running_late_source_N_count_changed")
    valid = set()
    ordered_numbers = []
    for row in native:
        if type(row) is not dict or type(row.get("native_number")) is not int:
            raise DestinationRefused("running_late_source_N_invalid")
        n = row["native_number"]
        if sequence == 3:
            prior_raw = _read(third_folder / "native" / f"{n:03d}.json", uid)
            prior = json.loads(prior_raw)
            if prior_raw != _canonical(prior):
                raise DestinationRefused("running_late_prior_N_noncanonical")
            cut = prior["cursor"]
        else:
            prior = next((r for r in previous["native"] if r["native_number"] == n), None)
            if prior is None:
                raise DestinationRefused("running_late_source_foreign_N")
            cut = {"new_path": prior["path"], "new_device": prior["device"],
                   "new_inode": prior["inode"], "new_end": prior["frozen_end"],
                   "new_end_sha256": prior["frozen_sha256"]}
        if (row.get("hostlist") != prior.get("hostlist") or
                any(row.get(k) != cut.get(v) for k, v in (
                    ("path", "new_path"), ("device", "new_device"),
                    ("inode", "new_inode"), ("previous_end", "new_end"),
                    ("previous_sha256", "new_end_sha256"))) or
                type(row.get("frozen_end")) is not int or
                row["frozen_end"] < row["previous_end"] or
                type(row.get("frozen_sha256")) is not str or
                not SHA256.fullmatch(row["frozen_sha256"])):
            raise DestinationRefused("running_late_source_N_cursor_unbound")
        ordered_numbers.append(n)
        valid.add((n, row["hostlist"]))
    if (ordered_numbers != sorted(set(ordered_numbers)) or
            not any(r["frozen_end"] > r["previous_end"] for r in native)):
        raise DestinationRefused("running_late_source_N_repeated_or_empty")
    debug = intent.get("debug")
    previous_debug = previous["debug"]
    if sequence > 3:
        previous_debug = {**previous_debug, "end": previous_debug["frozen_end"],
                          "end_sha256": previous_debug["frozen_sha256"]}
    if (type(debug) is not dict or
            any(debug.get(k) != previous_debug.get(v) for k, v in (
                ("device", "device"), ("inode", "inode"),
                ("previous_end", "end"), ("previous_sha256", "end_sha256"))) or
            type(debug.get("frozen_end")) is not int or
            debug["frozen_end"] < debug["previous_end"] or
            type(debug.get("frozen_sha256")) is not str or
            not SHA256.fullmatch(debug["frozen_sha256"])):
        raise DestinationRefused("running_late_source_debug_unbound")
    observations = intent.get("native_positive_observations")
    if (type(observations) is not list or not 0 < len(observations) <= 4096 or
            any(type(r) is not dict or
                set(r) != {"native_number", "hostlist", "hostname"} or
                type(r["native_number"]) is not int or
                (r["native_number"], r["hostlist"]) not in valid or
                type(r["hostname"]) is not str or
                not HOST.fullmatch(r["hostname"]) or ".." in r["hostname"]
                for r in observations)):
        raise DestinationRefused("running_late_source_attribution_invalid")
    ordered = [(r["native_number"], r["hostlist"], r["hostname"])
               for r in observations]
    if (ordered != sorted(set(ordered)) or intent.get("observations") != [
            {"hostname": h, "hostlist": label} for _, label, h in ordered]):
        raise DestinationRefused("running_late_source_observations_changed")
    preimages = intent.get("destination_preimages")
    fields = {"target", "path", "sha256", "device", "inode", "ctime_ns",
              "mtime_ns", "size", "last_writer_sequence"}
    expected_targets = {"writes:auto", "writes:youtube", "writes:user",
                        "live:youtube", "live:user"}
    if (type(preimages) is not list or len(preimages) != len(expected_targets) or
            any(type(r) is not dict or set(r) != fields or
                type(r["target"]) is not str or r["target"] not in expected_targets or
                type(r["path"]) is not str or not Path(r["path"]).is_absolute() or
                type(r["sha256"]) is not str or not SHA256.fullmatch(r["sha256"]) or
                any(type(r[k]) is not int or r[k] < 0 for k in (
                    "device", "inode", "ctime_ns", "mtime_ns", "size")) or
                r["inode"] == 0 or r["size"] > MAX_TARGET or
                type(r["last_writer_sequence"]) is not int or
                not -1 <= r["last_writer_sequence"] < sequence
                for r in preimages) or
            [r["target"] for r in preimages] != sorted(expected_targets)):
        raise DestinationRefused("running_late_source_destinations_unpinned")
    return {
        "schema": 3, "kind": "durable-destination-plan",
        "generation": intent["generation"], "pending_name": f"learning-{sequence:08d}",
        "pending_sha256": _sha(_canonical({"observations": intent["observations"]})),
        "evidence": "learning-native-debug",
        "debug_end_offset": debug["frozen_end"],
        "debug_end_sha256": debug["frozen_sha256"],
        "source_intent_sha256": _sha(source_raw),
        "previous_cursor_progress_sha256": _sha(previous_progress_raw),
    }


def _original_source_plan_fields(folder: Path, intent: dict,
                                 uid: int) -> dict:
    """Bind ONE destination WAL to its original immutable source intent.

    Schema2 is the detached original P2a pending inode. Schema3's FIRST
    physical N-inbox epoch is a virtual source slot, not a detached pending
    inode; its exact protected original cursor intent SHA is part of the
    very same plan and prevents the two provenance kinds being confused.
    Neither mode grants a native-source cleanup or ACK capability.
    """
    if not isinstance(intent, dict):
        raise DestinationRefused("invalid_original_source_intent")
    if intent.get("schema") != 3:
        return {
            "schema": 2, "kind": "durable-destination-plan",
            "generation": intent["generation"],
            "pending_name": intent["pending_name"],
            "pending_sha256": intent["pending_sha256"],
            "evidence": intent["evidence"],
            "debug_end_offset": intent["debug_end_offset"],
            "debug_end_sha256": intent["debug_end_sha256"],
        }
    if intent.get("kind") == "original-learning-cycle-prepared":
        from auto_detect_cursor_chain import learning_cycle_source_fields
        return learning_cycle_source_fields(folder, intent, uid)
    if intent.get("kind") in ("original-learning-running-fourth-source-prepared",
                              "original-learning-running-source-prepared"):
        return _original_running_late_source_plan_fields(folder, intent, uid)
    # The third source remains a virtual original cursor slot. Rebind it
    # only to a complete original second Found->managed checkpoint and the
    # same durable logical N cursor progress; NEVER a second writer.
    if intent.get("kind") == "original-learning-third-slot-prepared":
        return _original_third_source_plan_fields(folder, intent, uid)
    # The SECOND original same-generation schema-3 source is a virtual
    # cursor slot, NOT a new P2 destination writer or real pending file.
    # Reuse this exact source-bound original plan/CAS/checkpoint path.
    if intent.get("kind") == "original-learning-forward-second-slot-prepared":
        if (folder.name != "00000001" or
                folder.parent.name != "cursor-chain-v2" or
                folder.parent.parent.name != intent.get("generation") or
                intent.get("schema") != 3 or intent.get("sequence") != 1 or
                intent.get("ack_authorized") is not False or
                intent.get("cursor_advanced") is not False or
                intent.get("commit_authorized") is not False):
            raise DestinationRefused("learning_forward_wal_not_original_second_slot")
        raw = _read(folder / "intent.json", uid)
        try:
            saved = json.loads(raw)
        except (ValueError, UnicodeError, TypeError) as exc:
            raise DestinationRefused("learning_forward_wal_source_unreadable") from exc
        if saved != intent or not isinstance(intent.get("observations"), list):
            raise DestinationRefused("learning_forward_wal_intent_changed")
        observations = intent["observations"]
        if (not 0 < len(observations) <= 4096 or
                len(observations) != intent.get("observations_count") or
                any(type(row) is not dict or
                    set(row) != {"hostname", "hostlist"} or
                    type(row["hostname"]) is not str or
                    row["hostlist"] not in {"youtube", "user"}
                    for row in observations) or
                _sha(json.dumps(
                    observations, sort_keys=True,
                    separators=(",", ":")).encode()) !=
                intent.get("observations_sha256")):
            raise DestinationRefused("learning_forward_wal_observations_not_sealed")
        first_slot = folder.parent / "00000000"
        _directory(first_slot, uid)
        first_raw = _read(first_slot / "intent.json", uid)
        if _sha(first_raw) != intent.get("first_slot_sha256"):
            raise DestinationRefused("learning_forward_wal_first_slot_changed")
        try:
            original = json.loads(first_raw)
        except (UnicodeError, ValueError, TypeError) as exc:
            raise DestinationRefused("learning_forward_wal_first_intent_invalid") from exc
        if (not isinstance(original, dict) or original.get("schema") != 3 or
                original.get("sequence") != 0 or
                original.get("generation") != intent["generation"]):
            raise DestinationRefused("learning_forward_wal_first_intent_foreign")
        # The original permanent Found+active managed destination MUST
        # already have its write-once checkpoint before a second slot
        # can legally source another P1 transaction.
        first_plan, first_plan_raw = qualified_destination_plan(
            first_slot, original, uid)
        first_cp = json.loads(_read(
            first_slot / "destination" / "checkpoint.json", uid))
        if first_cp != {
                "schema": 1,
                "kind": "destination-and-cursor-committed",
                "generation": intent["generation"],
                "pending_name": "learning-00000000",
                "plan_sha256": _sha(first_plan_raw),
                "evidence": "learning-native-debug",
                "committed_cursor_offset": original["debug_end_offset"],
                "committed_cursor_sha256": original["debug_end_sha256"],
                "ack_authorized": False}:
            raise DestinationRefused("learning_forward_wal_first_checkpoint_uncommitted")
        rebind = first_slot / "native-rebind"
        _directory(rebind, uid)
        if (_sha(_read(rebind / "manifest.json", uid)) !=
                intent.get("native_rebind_manifest_sha256")):
            raise DestinationRefused("learning_forward_wal_native_manifest_changed")
        native_dir = folder / "native"
        _directory(native_dir, uid)
        if (type(intent.get("profiles_count")) is not int or
                intent["profiles_count"] != len(original["native"]) or
                len(original["native"]) < 1 or
                type(intent.get("debug")) is not dict or
                intent["debug"].get("start") != original["debug_end_offset"] or
                intent["debug"].get("start_sha256") !=
                original["debug_end_sha256"] or
                intent["debug"].get("end") is None or
                type(intent["debug"]["end"]) is not int or
                intent["debug"]["end"] < intent["debug"]["start"] or
                type(intent.get("profiles_sha256")) is not str or
                not SHA256.fullmatch(intent["profiles_sha256"])):
            raise DestinationRefused("learning_forward_wal_unqualified_debug_or_n")
        profile_bytes = []
        exact_names = set()
        for first in original["native"]:
            number = first["native_number"]
            name = f"{number:03d}.json"
            exact_names.add(name)
            child_raw = _read(native_dir / name, uid)
            child = json.loads(child_raw)
            if (not isinstance(child, dict) or
                    child_raw != _canonical(child) or
                    child.get("schema") != 3 or
                    child.get("kind") != "original-learning-forward-native-cut" or
                    child.get("generation") != intent["generation"] or
                    child.get("sequence") != 1 or
                    child.get("first_slot_sha256") != _sha(first_raw) or
                    child.get("manifest_sha256") !=
                    intent["native_rebind_manifest_sha256"] or
                    (child.get("native_number"), child.get("hostlist")) !=
                    (number, first["hostlist"]) or
                    child.get("cursor_advanced") is not False or
                    child.get("ack_authorized") is not False):
                raise DestinationRefused("learning_forward_wal_foreign_native_cut")
            profile_bytes.append(hashlib.sha256(child_raw).digest())
        if (set(os.listdir(native_dir)) != exact_names or
                _sha(b"".join(profile_bytes)) != intent["profiles_sha256"]):
            raise DestinationRefused("learning_forward_wal_native_cuts_changed")
        return {
            "schema": 3, "kind": "durable-destination-plan",
            "generation": intent["generation"],
            "pending_name": "learning-00000001",
            "pending_sha256": _sha(
                _canonical({"observations": observations})),
            "evidence": "learning-native-debug",
            "debug_end_offset": intent["debug"]["end"],
            "debug_end_sha256": intent["debug"]["end_sha256"],
            "source_intent_sha256": _sha(raw),
        }
    if (folder.name != "00000000" or
            folder.parent.name != "cursor-chain-v2" or
            folder.parent.parent.name != intent.get("generation") or
            intent.get("schema") != 3 or
            intent.get("kind") != "original-learning-cursor-prepared" or
            intent.get("sequence") != 0 or
            intent.get("ack_authorized") is not False):
        raise DestinationRefused("learning_wal_not_original_first_slot")
    raw = _read(folder / "intent.json", uid)
    try:
        saved = json.loads(raw)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise DestinationRefused("learning_wal_source_invalid") from exc
    if saved != intent:
        raise DestinationRefused("learning_wal_source_intent_changed")
    return {
        "schema": 3, "kind": "durable-destination-plan",
        "generation": intent["generation"],
        # This is an original cursor slot name, NOT a real pending inode.
        "pending_name": "learning-00000000",
        "pending_sha256": _sha(_canonical({"observations": intent["observations"]})),
        "evidence": "learning-native-debug",
        "debug_end_offset": intent["debug_end_offset"],
        "debug_end_sha256": intent["debug_end_sha256"],
        "source_intent_sha256": _sha(raw),
    }


def qualified_destination_plan(folder: Path, intent: dict, uid: int,
                               targets: dict[str, Path] | None = None
                               ) -> tuple[dict, bytes]:
    """Verify the ONE immutable original plan, including pre-write inodes.

    Schema 2 was chosen for the current dormant journal, not as a legacy
    migration. A preimage identity must already exist INSIDE the original
    plan before the first physical destination write; replay cannot invent
    the identity after a GUI edit or a partial crash.
    """
    journal = folder / "destination"
    _directory(journal, uid)
    names = set(os.listdir(journal))
    if names - {"plan.json", "checkpoint.json"} or "plan.json" not in names:
        raise DestinationRefused("missing_or_foreign_destination_plan")
    plan_raw = _read(journal / "plan.json", uid)
    try:
        plan = json.loads(plan_raw)
    except (ValueError, UnicodeError) as exc:
        raise DestinationRefused("corrupt_destination_plan") from exc
    expected = _original_source_plan_fields(folder, intent, uid)
    if (not isinstance(plan, dict) or
            set(plan) not in (set(expected) | {"writes"},
                             set(expected) | {"writes", "live"}) or
            any(plan.get(k) != v for k, v in expected.items()) or
            not isinstance(plan.get("writes"), dict) or
            len(plan["writes"]) > 16 or
            (targets is not None and set(plan["writes"]) - set(targets))):
        raise DestinationRefused("destination_plan_not_bound_to_original_intent")
    for name, change in plan["writes"].items():
        identity = {
            "before_device", "before_inode", "before_ctime_ns",
            "before_mtime_ns", "before_size",
        }
        if (not isinstance(name, str) or
                not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", name) or
                not isinstance(change, dict) or
                set(change) != {"path", "before", "after", "add", "remove"} | identity or
                not isinstance(change.get("path"), str) or
                not Path(change["path"]).is_absolute() or
                (targets is not None and
                 change["path"] != str(targets[name])) or
                any(not isinstance(change.get(d), str) or
                    not SHA256.fullmatch(change[d])
                    for d in ("before", "after")) or
                any(type(change.get(k)) is not int or change[k] < 0
                    for k in identity) or
                change["before_inode"] == 0 or
                change["before_size"] > MAX_TARGET or
                any(type(change.get(k)) is not list or
                    len(change[k]) > 4096 or
                    any(type(x) is not str or
                        not HOST.fullmatch(x) or ".." in x
                        for x in change[k])
                    for k in ("add", "remove")) or
                len(change["add"]) + len(change["remove"]) > 4096):
            raise DestinationRefused("destination_preimage_plan_invalid")
    # Optional live managed files are part of THIS original P2 journal.
    # Historical source-only schema-2 plans remain readable for interrupted
    # original receipts; they cannot be silently promoted to live writes.
    live = plan.get("live", {})
    if (not isinstance(live, dict) or
            set(live) - {"youtube", "user"} or len(live) > 2):
        raise DestinationRefused("unqualified_live_managed_plan")
    for name, row in live.items():
        identity = {"before_device", "before_inode", "before_ctime_ns",
                    "before_mtime_ns", "before_size"}
        if (not isinstance(row, dict) or
                set(row) != {"path", "before", "after"} | identity or
                not isinstance(row.get("path"), str) or
                not Path(row["path"]).is_absolute() or
                any(not isinstance(row.get(key), str) or
                    not SHA256.fullmatch(row[key])
                    for key in ("before", "after")) or
                row["before"] == row["after"] or
                any(type(row.get(key)) is not int or row[key] < 0
                    for key in identity) or
                row["before_inode"] == 0 or
                row["before_size"] > MAX_TARGET):
            raise DestinationRefused("invalid_live_managed_preimage")
    if intent.get("kind") in ("original-learning-running-fourth-source-prepared",
                              "original-learning-running-source-prepared"):
        preimages = {row["target"]: row for row in intent["destination_preimages"]}
        for kind, entries in (("writes", plan["writes"]), ("live", live)):
            for name, row in entries.items():
                before = preimages.get(f"{kind}:{name}")
                if (before is None or row["path"] != before["path"] or
                        row["before"] != before["sha256"] or
                        any(row["before_" + key] != before[key] for key in (
                            "device", "inode", "ctime_ns", "mtime_ns", "size"))):
                    raise DestinationRefused("running_late_plan_preimage_not_original_source")
    return plan, plan_raw


class DestinationCommit:
    """A prepared-intent journal: prepare -> per-file CAS -> checkpoint.

    The caller's owner/FD proofs are NOT implied by this API. No automatic
    invocation is installed. The queue lock must be held for every call, and
    GUI must use the same external lock before P3 enables native writes.
    """

    def __init__(self, receipts: EpochReceipts, queue: DurableInbox,
                 targets: dict[str, Path], gui_lock: Path):
        self.receipts, self.queue = receipts, queue
        self.targets = {k: Path(v) for k, v in targets.items()}
        self.gui_lock = Path(gui_lock)
        if (not self.targets or "auto" not in self.targets or
                any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", k)
                    for k in self.targets) or
                len(set(self.targets.values())) != len(self.targets) or
                any(not p.is_absolute() for p in self.targets.values()) or
                not self.gui_lock.is_absolute() or
                self.gui_lock in self.targets.values()):
            raise DestinationRefused("unqualified_destination_mapping")

    @contextmanager
    def exclusive_targets(self):
        """Lock the P1 snapshot and P2k2b CAS under the same root flock."""
        if getattr(self, "_gui_held", False):
            raise DestinationRefused("gui_lock_already_held")
        with exclusive_destination_lock(self.gui_lock, self.receipts.uid):
            self._gui_held = True
            try:
                yield self
            finally:
                self._gui_held = False

    def _locked_commit(self, folder: Path, intent: dict, raw: bytes,
                       effects: dict, *, live: dict | None = None) -> dict:
        if not getattr(self, "_gui_held", False):
            raise DestinationRefused("gui_lock_required")
        source = _original_source_plan_fields(folder, intent, self.receipts.uid)
        if source["schema"] == 3:
            # Schema3 MUST provide an exact live-managed preimage plan even
            # for a zero-change P1 batch. A source-only known Found write
            # without the active same-PID counterpart cannot be accepted.
            if live is None or raw != _canonical(
                    {"observations": intent["observations"]}):
                raise DestinationRefused("learning_wal_requires_live_and_source")
        # Callers may supply canonical after-BYTES, never a callback or a
        # stale file path alone. The original Config/P2 owner must derive
        # these bytes from its currently locked native manual/owned sources.
        if live is not None and (
                not isinstance(live, dict) or
                set(live) - {"youtube", "user"} or
                any(not isinstance(row, dict) or
                    set(row) != {"path", "before_sha256", "after"} or
                    not isinstance(row["path"], Path) or
                    not row["path"].is_absolute() or
                    type(row["before_sha256"]) is not str or
                    not SHA256.fullmatch(row["before_sha256"]) or
                    type(row["after"]) is not bytes or
                    len(row["after"]) > MAX_TARGET
                    for row in live.values())):
            raise DestinationRefused("unqualified_live_after_images")
        journal = folder / "destination"
        if not journal.exists() and not journal.is_symlink():
            journal.mkdir(mode=0o700)
            _sync(folder)
        _directory(journal, self.receipts.uid)
        names = set(os.listdir(journal))
        if names - {"plan.json", "checkpoint.json"}:
            raise DestinationRefused("foreign_destination_receipts")
        plan_path, checkpoint_path = journal / "plan.json", journal / "checkpoint.json"
        if "plan.json" not in names:
            writes = {}
            for name, change in sorted(effects.items()):
                path = self.targets[name]
                before, st = _target(path, self.receipts.uid)
                after = _edit(before, change["add"], change["remove"])
                writes[name] = {
                    "path": str(path), "before": _sha(before),
                    "after": _sha(after), "add": change["add"],
                    "remove": change["remove"],
                    "before_device": st.st_dev, "before_inode": st.st_ino,
                    "before_ctime_ns": st.st_ctime_ns,
                    "before_mtime_ns": st.st_mtime_ns,
                    "before_size": st.st_size,
                }
            live_rows = {}
            for name, candidate in sorted((live or {}).items()):
                active_bytes, active_st = _target(
                    candidate["path"], self.receipts.uid)
                if _sha(active_bytes) != candidate["before_sha256"]:
                    raise DestinationRefused("live_managed_not_aligned_at_prepare")
                if active_bytes == candidate["after"]:
                    continue  # no live mutation; no synthetic preimage WAL
                live_rows[name] = {
                    "path": str(candidate["path"]),
                    "before": _sha(active_bytes),
                    "after": _sha(candidate["after"]),
                    "before_device": active_st.st_dev,
                    "before_inode": active_st.st_ino,
                    "before_ctime_ns": active_st.st_ctime_ns,
                    "before_mtime_ns": active_st.st_mtime_ns,
                    "before_size": active_st.st_size,
                }
            plan = {**source, "writes": writes}
            if live is not None:
                plan["live"] = live_rows
            _write_once(journal, "plan.json", _canonical(plan), self.receipts.uid)
        plan, plan_raw = qualified_destination_plan(
            folder, intent, self.receipts.uid, targets=self.targets)
        # A source-only replay cannot downgrade a sealed live-managed slot.
        # A new live plan cannot retroactively amend a previous checkpoint.
        sealed_live = plan.get("live", {})
        if live is not None:
            if set(live) != set(sealed_live) and (
                    set(sealed_live) != {name for name, candidate in live.items()
                                       if _sha(candidate["after"]) !=
                                       candidate["before_sha256"]}):
                raise DestinationRefused("original_live_plan_changed")
            for name, row in sealed_live.items():
                proposed = live.get(name)
                if (proposed is None or str(proposed["path"]) != row["path"] or
                        _sha(proposed["after"]) != row["after"] or
                        proposed["before_sha256"] != row["before"]):
                    raise DestinationRefused("original_live_after_image_changed")
        elif sealed_live:
            raise DestinationRefused("original_live_plan_required")
        if checkpoint_path.exists() or checkpoint_path.is_symlink():
            checkpoint = json.loads(_read(checkpoint_path, self.receipts.uid))
            if (checkpoint.get("plan_sha256") != _sha(plan_raw) or
                    checkpoint.get("evidence") != source["evidence"] or
                    checkpoint.get("committed_cursor_offset") != source["debug_end_offset"] or
                    checkpoint.get("committed_cursor_sha256") != source["debug_end_sha256"]):
                raise DestinationRefused("checkpoint_differs_from_plan")
            return checkpoint  # never undo later GUI deletion on acknowledged replay
        # All-target preflight BEFORE any physical CAS replacement. A GUI
        # delete after an earlier write can restore the original BYTE digest
        # but not the original inode/ctime. The old content hash ALONE must
        # never authorize putting the manually deleted row back.
        todo = []
        for name, change in sorted(plan["writes"].items()):
            path = self.targets[name]
            current, st = _target(path, self.receipts.uid)
            if _sha(current) == change["after"]:
                continue  # fully applied (or a no-op); do not rewrite it
            if (_sha(current) != change["before"] or
                    (st.st_dev, st.st_ino, st.st_ctime_ns,
                     st.st_mtime_ns, st.st_size) !=
                    (change["before_device"], change["before_inode"],
                     change["before_ctime_ns"], change["before_mtime_ns"],
                     change["before_size"])):
                raise DestinationRefused("destination_gui_or_preimage_changed")
            new = _edit(current, change["add"], change["remove"])
            if _sha(new) != change["after"]:
                raise DestinationRefused("destination_plan_diverged")
            todo.append((path, current, new,
                         (st.st_dev, st.st_ino, st.st_ctime_ns,
                          st.st_mtime_ns, st.st_size)))
        live_todo = []
        for name, row in sorted(sealed_live.items()):
            path = Path(row["path"])
            current, st = _target(path, self.receipts.uid)
            if _sha(current) == row["after"]:
                continue
            before_identity = (row["before_device"], row["before_inode"],
                               row["before_ctime_ns"], row["before_mtime_ns"],
                               row["before_size"])
            if (_sha(current) != row["before"] or
                    _file_identity(st) != before_identity):
                raise DestinationRefused("live_managed_preimage_changed")
            if live is None or _sha(live[name]["after"]) != row["after"]:
                raise DestinationRefused("live_managed_after_image_unavailable")
            live_todo.append((path, current, live[name]["after"], before_identity))
        # First original auto-owned source CAS, then exact active images;
        # checkpoint and physical ACK must remain absent if either fails.
        for path, current, new, identity in todo:
            _replace(path, current, new, self.receipts.uid,
                     expected_identity=identity)
        for path, current, new, identity in live_todo:
            _replace(path, current, new, self.receipts.uid,
                     expected_identity=identity)
        for row in sealed_live.values():
            current, _ = _target(Path(row["path"]), self.receipts.uid)
            if _sha(current) != row["after"]:
                raise DestinationRefused("live_managed_postimage_not_installed")
        checkpoint = {"schema": 1, "kind": "destination-and-cursor-committed",
                      "generation": source["generation"], "pending_name": source["pending_name"],
                      "plan_sha256": _sha(plan_raw),
                      "evidence": source["evidence"],
                      "committed_cursor_offset": source["debug_end_offset"],
                      "committed_cursor_sha256": source["debug_end_sha256"],
                      "ack_authorized": False}
        _write_once(journal, "checkpoint.json", _canonical(checkpoint), self.receipts.uid)
        return checkpoint


# TZ6v2 Shared Apply: the SAME original P2 destination CAS owner.
# No alternative file writer, no new CLI, no new Config writer or journal.
# The public operation is bound to the existing original FD9 + activating
# Shared Apply record + sealed original candidate. The low-level helper is
# deliberately private for controlled preflight/partial-failure tests.
SHARED_FOUND_NAMES = ("youtube", "user", "auto")
SHARED_FOUND_LIMIT = 40 * 1024
_PHP_INT64_MAX = (1 << 63) - 1
_NATIVE_U64_MAX = (1 << 64) - 1


def _shared_found_identity_integer(value: object) -> int | None:
    """Normalize ONLY a lossless native stat ID, never a PHP-rounded float.

    PHP JSON_BIGINT_AS_STRING preserves FreeBSD unsigned st_dev/st_ino
    that exceed PHP_INT_MAX as canonical decimal strings. Small numbers
    must remain actual JSON integers. Every result is compared to original
    os.stat() under the existing Config/P2 locks before any file mutation.
    """
    if type(value) is int:
        return value if 0 <= value <= _NATIVE_U64_MAX else None
    if (type(value) is str and
            re.fullmatch(r"[1-9][0-9]{18,19}", value)):
        number = int(value)
        if _PHP_INT64_MAX < number <= _NATIVE_U64_MAX:
            return number
    return None


def _qualified_shared_found_batch(rows: dict) -> dict:
    from domain_policy import PublicSuffixList, normalize_found_editor

    if not isinstance(rows, dict) or list(rows) != list(SHARED_FOUND_NAMES):
        raise DestinationRefused("shared_found_batch_incomplete")
    psl = PublicSuffixList.load()
    out = {}
    identity = ("before_device", "before_inode", "before_ctime_ns",
                "before_mtime_ns", "before_size")
    for name in SHARED_FOUND_NAMES:
        entry = rows[name]
        numeric = ({key: _shared_found_identity_integer(entry.get(key))
                    for key in identity} if isinstance(entry, dict) else {})
        if (not isinstance(entry, dict) or
                set(entry) != {"before", "after", "before_status",
                               "before_revision", *identity} or
                not isinstance(entry["before"], str) or
                not isinstance(entry["after"], str) or
                entry["before_status"] not in ("present", "missing") or
                not isinstance(entry["before_revision"], str) or
                not SHA256.fullmatch(entry["before_revision"]) or
                any(numeric[k] is None for k in identity)):
            raise DestinationRefused("shared_found_candidate_shape")
        before, after = (entry[k].encode("utf-8") for k in ("before", "after"))
        if len(before) > SHARED_FOUND_LIMIT or len(after) > SHARED_FOUND_LIMIT:
            raise DestinationRefused("shared_found_candidate_revision")
        if entry["before_status"] == "missing":
            if (name != "auto" or before != b"" or
                    any(numeric[k] != 0 for k in identity) or
                    _sha(b"missing\0") != entry["before_revision"]):
                raise DestinationRefused("shared_found_candidate_revision")
        elif (numeric["before_inode"] == 0 or
              numeric["before_size"] != len(before) or
              _sha(b"present\0" + before) != entry["before_revision"]):
            raise DestinationRefused("shared_found_candidate_revision")
        try:
            for text in (entry["before"], entry["after"]):
                parsed = normalize_found_editor(text, name, psl=psl)["normalized"]
                if text != (parsed + "\n" if parsed else ""):
                    raise DestinationRefused("shared_found_candidate_noncanonical")
        except (ValueError, TypeError) as exc:
            raise DestinationRefused("shared_found_candidate_domain_policy") from exc
        out[name] = (before, after, tuple(numeric[k] for k in identity),
                     entry["before_status"])
    return out


def _shared_found_assert_missing(path: Path, uid: int) -> None:
    """Qualify an absent shared-auto name without following any symlink."""
    try:
        parent = path.parent.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid or
                parent.st_mode & 0o022):
            raise DestinationRefused("shared_found_missing_parent_unsafe")
        path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise DestinationRefused("shared_found_missing_unreadable") from exc
    raise DestinationRefused("shared_found_expected_missing")


def _plan_shared_found_under_original_locks(
        baselines: dict, drafts: dict, manual: dict, global_exclude: str,
        targets: dict, *, uid: int) -> tuple[dict, dict]:
    """Rebase P1 user intent onto exact locked P2 before-images (PRIVATE).

    The original FD9 service must hold original Config -> destination locks
    and supply verified candidate manual/exclusion fields. This read-only
    preparation does not authorize writes or initialize missing files.
    """
    from auto_detect_five_editor_plan import (
        FiveEditorPlanRefused, preview_five_sources,
    )

    if (not isinstance(targets, dict) or
            list(targets) != list(SHARED_FOUND_NAMES) or
            len(set(map(str, targets.values()))) != len(SHARED_FOUND_NAMES) or
            not isinstance(global_exclude, str)):
        raise DestinationRefused("shared_found_planner_input_incomplete")
    currents = {}
    pinned = {}
    for name in SHARED_FOUND_NAMES:
        path = Path(targets[name])
        if not path.is_absolute():
            raise DestinationRefused("shared_found_target_not_absolute")
        try:
            raw, st = _target(path, uid)
            status = "present"
        except DestinationRefused as exc:
            if name != "auto" or not isinstance(exc.__cause__, FileNotFoundError):
                raise DestinationRefused("shared_found_preimage_unavailable") from exc
            # Only this shared source may be genuinely absent on first install.
            _shared_found_assert_missing(path, uid)
            raw, st, status = b"", None, "missing"
        if len(raw) > SHARED_FOUND_LIMIT:
            raise DestinationRefused("shared_found_preimage_too_large")
        content = raw.decode("utf-8")
        currents[name] = {
            "status": "missing" if status == "missing" else (
                "populated" if content else "empty"),
            "revision": _sha(b"missing\0" if status == "missing"
                             else b"present\0" + raw),
            "content": content,
        }
        pinned[name] = st

    try:
        preview = preview_five_sources(
            baselines, drafts, currents, manual, global_exclude)
    except FiveEditorPlanRefused as exc:
        raise DestinationRefused(
            "shared_found_planner_" + exc.source + "_" + exc.code) from None
    if (preview.get("result") != "preview_only" or
            preview.get("cross_source_validated") is not True or
            preview.get("commit_authorized") is not False):
        raise DestinationRefused("shared_found_planner_not_qualified")

    rows = {}
    for name in SHARED_FOUND_NAMES:
        st = pinned[name]
        rows[name] = {
            "before": currents[name]["content"],
            "after": preview["sources"][name]["content"],
            "before_status": "missing" if st is None else "present",
            "before_revision": currents[name]["revision"],
            "before_device": st.st_dev if st is not None else 0,
            "before_inode": st.st_ino if st is not None else 0,
            "before_ctime_ns": st.st_ctime_ns if st is not None else 0,
            "before_mtime_ns": st.st_mtime_ns if st is not None else 0,
            "before_size": st.st_size if st is not None else 0,
        }
    # Existing P2 writer validates the identical canonical/identity schema.
    _qualified_shared_found_batch(rows)
    return rows, preview


def _locked_shared_found_replace(rows: dict, targets: dict, *, uid: int,
                                 replace_fn=None, create_fn=None,
                                 stage_fn=None) -> dict:
    """All-target CAS before any write, with bounded synchronous compensation.

    Caller MUST hold original FD9 and Config->P2 destination lock. A missing
    shared-auto file is qualified as ABSENT, never as a present empty inode.
    The return is file-only and cannot authorize native Config success.
    """
    if (not isinstance(targets, dict) or
            list(targets) != list(SHARED_FOUND_NAMES) or
            len(set(map(str, targets.values()))) != len(SHARED_FOUND_NAMES)):
        raise DestinationRefused("shared_found_targets_incomplete")
    batch = _qualified_shared_found_batch(rows)
    replace = _replace if replace_fn is None else replace_fn
    if create_fn is None:
        # Original P2k5 root/private same-directory durable link-once writer.
        from auto_detect_gui_hostlist import _create
        create = _create
    else:
        create = create_fn
    original = {}
    for name in SHARED_FOUND_NAMES:
        path = Path(targets[name])
        if not path.is_absolute():
            raise DestinationRefused("shared_found_target_not_absolute")
        before, after, preimage, status = batch[name]
        if status == "missing":
            _shared_found_assert_missing(path, uid)
        else:
            now, st = _target(path, uid)
            observed = (st.st_dev, st.st_ino, st.st_ctime_ns,
                        st.st_mtime_ns, st.st_size)
            if now != before or observed != preimage:
                raise DestinationRefused("shared_found_preimage_changed")
        original[name] = (path, before, after, status)
    modified = []
    created_pins = {}
    own_written_inodes = {}
    ready_pins = {}

    def file_stage(name: str, phase: str, target: Path, contents: bytes,
                   observed_stat: os.stat_result | None = None) -> None:
        if stage_fn is None:
            return
        if observed_stat is None:
            observed, observed_stat = _target(target, uid)
            if observed != contents:
                raise DestinationRefused("original_staged_inode_content_changed")
        pin = _stage_pin(observed_stat, contents)
        if phase == "ready":
            if name in ready_pins:
                raise DestinationRefused("duplicate_original_staged_inode")
            pin["temp"] = target.name
            ready_pins[name] = pin
        elif phase == "installed":
            if name not in ready_pins:
                raise DestinationRefused("original_staged_inode_disappeared")
            pin["temp"] = ready_pins[name]["temp"]
            if pin != ready_pins[name]:
                raise DestinationRefused("original_staged_inode_changed_at_rename")
        else:
            raise DestinationRefused("invalid_original_staged_inode_phase")
        stage_fn(name, phase, pin)

    try:
        for name in SHARED_FOUND_NAMES:
            path, before, after, status = original[name]
            if before == after:
                continue
            # The previous all-source scan is NOT enough: a foreign actor
            # could alter a later source during an earlier physical write.
            # Revalidate the exact sealed preimage immediately before EACH
            # replacement, even if the byte contents have stayed identical.
            if status == "missing":
                _shared_found_assert_missing(path, uid)
            else:
                fresh, st = _target(path, uid)
                physical = (st.st_dev, st.st_ino, st.st_ctime_ns,
                            st.st_mtime_ns, st.st_size)
                if fresh != before or physical != batch[name][2]:
                    raise DestinationRefused(
                        "shared_found_preimage_changed_before_write")
            # Include a potentially completed rename/link that raises before
            # returning. Never blindly unlink an unpinned ambiguous create.
            modified.append(name)
            if status == "missing":
                if stage_fn is not None and create_fn is None:
                    create(path, after, uid,
                           stage_fn=lambda phase, item, contents, n=name:
                               file_stage(n, phase, item, contents))
                else:
                    create(path, after, uid)
            else:
                if stage_fn is not None and replace_fn is None:
                    replace(path, before, after, uid,
                            expected_identity=batch[name][2],
                            stage_fn=lambda phase, item, contents, info, n=name:
                                file_stage(n, phase, item, contents, info))
                else:
                    replace(path, before, after, uid)
            actual, st = _target(path, uid)
            if status == "missing":
                created_pins[name] = (st.st_dev, st.st_ino, st.st_ctime_ns,
                                           st.st_mtime_ns, st.st_size)
            if actual != after:
                raise DestinationRefused("shared_found_postwrite_unverified")
            own_written_inodes[name] = (st.st_dev, st.st_ino, st.st_ctime_ns,
                                           st.st_mtime_ns, st.st_size)
        # All physical after-pins originate from this controlled writer.
        # Inode identity is captured after rename/link under P2, then
        # independently rechecked before the same FD9 journal is fsynced.
        post = {}
        for name in SHARED_FOUND_NAMES:
            path, before, after, status = original[name]
            if status == "missing" and before == after:
                _shared_found_assert_missing(path, uid)
                post[name] = {
                    "status": "missing", "device": 0, "inode": 0,
                    "ctime_ns": 0, "mtime_ns": 0, "size": 0,
                    "sha256": _sha(b"missing\0")}
                continue
            actual, st = _target(path, uid)
            identity = (st.st_dev, st.st_ino, st.st_ctime_ns,
                        st.st_mtime_ns, st.st_size)
            if actual != after or (name in own_written_inodes and
                                   identity != own_written_inodes[name]):
                raise DestinationRefused("shared_found_postimage_inode_drift")
            if before == after and status == "present" and identity != batch[name][2]:
                # A file not modified by this transaction may NOT be
                # substituted by an unrelated same-byte inode while P2
                # is held. The original preimage is the sole authority.
                raise DestinationRefused("shared_found_untouched_source_drift")
            post[name] = {
                "status": "present", "device": st.st_dev, "inode": st.st_ino,
                "ctime_ns": st.st_ctime_ns, "mtime_ns": st.st_mtime_ns,
                "size": st.st_size, "sha256": _sha(after)}
        return {
            "result": "files-applied-under-original-transaction",
            "post_images": post,
            "files": {
                name: {"before_sha256": _sha(original[name][1]),
                       "before_status": original[name][3],
                       "before_revision": rows[name]["before_revision"],
                       "after_sha256": _sha(original[name][2]),
                       "changed": original[name][1] != original[name][2]}
                for name in SHARED_FOUND_NAMES
            },
            "config_committed": False, "commit_authorized": False,
        }
    except (OSError, ValueError, DestinationRefused) as error:
        if stage_fn is not None:
            # Durable forward pins already describe the actual replacements.
            # Only journaled rollback may replace a before-image after this.
            raise
        try:
            for name in reversed(modified):
                path, before, after, status = original[name]
                if status == "missing":
                    try:
                        current, st = _target(path, uid)
                    except DestinationRefused as exc:
                        if not isinstance(exc.__cause__, FileNotFoundError):
                            raise
                        _shared_found_assert_missing(path, uid)
                        continue
                    current_pin = (st.st_dev, st.st_ino, st.st_ctime_ns,
                                   st.st_mtime_ns, st.st_size)
                    if (name not in created_pins or current != after or
                            current_pin != created_pins[name]):
                        raise DestinationRefused("shared_found_restore_unknown_create")
                    path.unlink()
                    _sync(path.parent)
                    _shared_found_assert_missing(path, uid)
                    continue
                current, st = _target(path, uid)
                if current == after:
                    # Never compensate a same-byte foreign inode. A durable
                    # rename can raise AFTER replacing the name: without a
                    # captured writer-owned inode, the outcome is ambiguous.
                    writer_pin = own_written_inodes.get(name)
                    current_pin = (st.st_dev, st.st_ino, st.st_ctime_ns,
                                   st.st_mtime_ns, st.st_size)
                    if writer_pin is None or current_pin != writer_pin:
                        raise DestinationRefused("shared_found_restore_unpinned_after")
                    replace(path, after, before, uid)
                elif current == before:
                    # If no own post-image was recorded, ONLY the exact
                    # original preimage may be left alone. A foreign inode
                    # with restored-looking bytes is not proof of rollback.
                    pinned_before = batch[name][2]
                    observed = (st.st_dev, st.st_ino, st.st_ctime_ns,
                                st.st_mtime_ns, st.st_size)
                    if observed != pinned_before:
                        raise DestinationRefused("shared_found_restore_foreign_before")
                else:
                    raise DestinationRefused("shared_found_restore_foreign_state")
            for name in SHARED_FOUND_NAMES:
                path, before, _, status = original[name]
                if status == "missing":
                    _shared_found_assert_missing(path, uid)
                else:
                    current, current_stat = _target(path, uid)
                    if current != before:
                        raise DestinationRefused("shared_found_restore_mismatch")
                    if name not in modified:
                        current_pin = (
                            current_stat.st_dev, current_stat.st_ino,
                            current_stat.st_ctime_ns, current_stat.st_mtime_ns,
                            current_stat.st_size)
                        if current_pin != batch[name][2]:
                            raise DestinationRefused(
                                "shared_found_restore_untouched_source_drift")
        except (OSError, ValueError, DestinationRefused) as rollback:
            raise DestinationRefused("shared_found_requires_review") from rollback
        raise DestinationRefused("shared_found_restored_after_failure") from error



def _locked_shared_found_apply_journal(rows: dict, targets: dict, *,
                                       store, detail: dict, plan_bytes: bytes,
                                       uid: int, attest, replace_fn=None,
                                       create_fn=None, bound_attest=None) -> dict:
    """Original common WAL -> existing three-file CAS -> common WAL.

    Import-only. Caller MUST hold FD9 + original Config lock + original P2
    flock across the ENTIRE function. A failure after files-writing is
    never a safe terminal restore/commit, even if the CAS compensated bytes.
    Full native Config save and phase-aware cold recovery are NOT enabled.
    """
    from shared_apply_operation import SharedApplyOperation
    if (not isinstance(store, SharedApplyOperation) or
            not isinstance(detail, dict) or
            not isinstance(plan_bytes, bytes) or
            not callable(attest)):
        raise DestinationRefused("shared_found_original_journal_required")
    try:
        plan = json.loads(plan_bytes)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise DestinationRefused("shared_found_original_plan_unreadable") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            plan.get("dependencies") != detail.get("base") or
            plan.get("changed_fields") != detail.get("changed_fields") or
            not isinstance(plan.get("found_intent"), dict) or
            plan["found_intent"].get("config_revision") != detail.get("base") or
            plan["found_intent"].get("commit_authorized") is not False or
            plan.get("found_batch") != rows):
        raise DestinationRefused("shared_found_plan_or_file_rows_mismatch")
    _qualified_shared_found_batch(rows)
    before = store.read()
    if (before is None or before["phase"] != "prepared" or
            before["detail"] != detail or "found" not in before or
            before["found"]["plan_sha256"] != _sha(plan_bytes)):
        raise DestinationRefused("shared_found_missing_original_prepared_intent")
    bound_kwargs = {} if bound_attest is None else {"bound_attest": bound_attest}
    store.advance_found_files("found-files-writing", detail, plan_bytes, attest,
                              **bound_kwargs)
    # Original Config/P2 locks forbid any minute write interleaving.
    # A SIGKILL between renames leaves the journal in files-writing.
    def durable_file_stage(name: str, phase: str, pin: dict) -> None:
        store.advance_found_stage(
            detail, plan_bytes, name, phase, pin,
            lambda stage, content, staged_name, staged_pin: (
                staged_name == name and staged_pin == pin and
                attest("found-stage-" + stage, content) is True),
            **bound_kwargs)

    result = _locked_shared_found_replace(
        rows, targets, uid=uid, replace_fn=replace_fn, create_fn=create_fn,
        stage_fn=durable_file_stage)
    post = result["post_images"]
    qualified = _qualified_shared_found_batch(rows)
    for name in SHARED_FOUND_NAMES:
        before, after, _, initial = qualified[name]
        target = targets[name]
        if initial == "missing" and before == after:
            _shared_found_assert_missing(target, uid)
        else:
            observed, st = _target(target, uid)
            pin = post[name]
            identity = (st.st_dev, st.st_ino, st.st_ctime_ns,
                        st.st_mtime_ns, st.st_size)
            expected = tuple(pin[key] for key in
                             ("device", "inode", "ctime_ns", "mtime_ns", "size"))
            if observed != after or pin["status"] != "present" or identity != expected:
                raise DestinationRefused("shared_found_writer_postimage_changed")
    store.advance_found_files("found-files-written", detail, plan_bytes,
                              attest, post_images=post, **bound_kwargs)
    return {**result, "journal_phase": "found-files-written",
            "config_committed": False, "commit_authorized": False}


def _matches_stage(pin: dict, data: bytes, st: os.stat_result) -> bool:
    return _stage_pin(st, data) == {key: pin[key] for key in
                                   ("device", "inode", "mtime_ns", "size", "sha256")}


def _found_temp(path: Path, pin: dict, uid: int, *, links: int = 1) -> Path | None:
    name = pin.get("temp")
    if name is None:
        return None
    temp = path.with_name(name)
    try:
        data, info = _target(temp, uid, links=links)
    except DestinationRefused as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return None
        raise
    if not _matches_stage(pin, data, info):
        raise DestinationRefused("foreign_found_temporary_inode")
    return temp


def _managed_write_images(store, record: dict, name: str, parent: Path) -> tuple:
    """Read both sealed originals and prove a one-file complete release delta."""
    from neutral_effective_diff import _REF_FILE
    from neutral_root_stage import verify_original_operation_pins
    from shared_apply_seal import _release_hash, verify_seal

    if store.read() != record or not _REF_FILE.fullmatch(name):
        raise DestinationRefused("original_managed_owner_changed")
    uid = store.owner
    verify_original_operation_pins(record=record, parent=parent, owner_uid=uid)
    old = parent / record["previous"]["id"]
    new = parent / record["detail"]["id"]
    relative = "managed/" + name
    old_bytes, old_stat = _target(old / "release" / relative, uid)
    new_bytes, new_stat = _target(new / "release" / relative, uid)
    old_hash = verify_seal(old, owner=uid)["sha256"]["release"]
    new_hash = verify_seal(new, owner=uid)["sha256"]["release"]
    if (old_bytes == new_bytes or os.path.samestat(old_stat, new_stat) or
            _release_hash(old / "release", uid, replacement=(
                relative, _sha(old_bytes), _sha(new_bytes))) != new_hash):
        raise DestinationRefused("original_managed_delta_requires_promotion")
    return old_bytes, old_stat, new_bytes, new_stat, old_hash, new_hash


def _write_bound_managed_file_locked(store, record: dict, preimage: tuple, *,
                                     parent: Path, active: Path, attest,
                                     running_sha256: str | None = None) -> dict:
    """One original FD9/Config/P2 replacement. Keep the Config save fenced."""
    from shared_apply_seal import _release_hash, _stat

    if (record.get("phase") != "prepared" or "found" in record or
            record.get("manifest", {}).get("schema") != 1 or
            record.get("previous_manifest", {}).get("schema") != 1 or
            record["detail"]["page"] != "strategies"):
        raise DestinationRefused("original_managed_prepared_required")
    name, old_sha, new_sha, old_identity, new_identity, live_identity = preimage
    content, old_stat, desired, new_stat, old_hash, new_hash = _managed_write_images(
        store, record, name, parent)
    path = active / "managed" / name
    uid = store.owner
    _stat(active, uid, directory=True)
    current, current_stat = _target(path, uid)
    if (old_sha != _sha(content) or new_sha != _sha(desired) or current != content or
            (old_identity, new_identity, live_identity) != tuple(map(_target_identity,
                (old_stat, new_stat, current_stat))) or
            len({identity[:2] for identity in (old_identity, new_identity, live_identity)}) != 3 or
            _release_hash(active, uid) != old_hash):
        raise DestinationRefused("original_managed_preimage_changed")
    row = {"name": name, "before_sha256": old_sha, "after_sha256": new_sha,
           "before_identity": list(live_identity)}
    if running_sha256 is not None:
        row["running_sha256"] = running_sha256
    record = store._checkpoint_managed_write(record, row, attest, shared_work_parent=parent)

    def stage(phase, item, data, info):
        nonlocal record
        if phase == "ready":
            new_now, new_info = _target(parent / record["detail"]["id"] / "release" /
                                       "managed" / name, uid)
            if new_now != desired or _target_identity(new_info) != new_identity:
                raise DestinationRefused("original_managed_candidate_changed")
            changes = {"ready": {**_stage_pin(info, data), "temp": item.name}}
        else:
            if _release_hash(active, uid) != new_hash:
                raise DestinationRefused("original_managed_after_release_changed")
            changes = {"installed": list(_target_identity(info))}
        record = store._checkpoint_managed_write(record, {**record["managed"], **changes},
                                                 attest, shared_work_parent=parent)

    _replace(path, content, desired, uid, stage_fn=stage, expected_identity=live_identity)
    return record


def _attest_bound_managed_installed_locked(store, record: dict, *, parent: Path,
                                          active: Path) -> None:
    from shared_apply_seal import _release_hash, _stat

    row = record["managed"]
    before, _, after, _, _, after_hash = _managed_write_images(store, record, row["name"], parent)
    _stat(active, store.owner, directory=True)
    current, info = _target(active / "managed" / row["name"], store.owner)
    # Keep the original refusal and short-circuit order. Distinct source
    # locations let the existing bounded M03 trace identify the failed proof
    # without logging paths, bytes, digests, inode values or timestamps.
    if current != after:
        raise DestinationRefused("original_managed_installed_image_changed")
    if (_sha(before), _sha(after)) != (row["before_sha256"], row["after_sha256"]):
        raise DestinationRefused("original_managed_installed_image_changed")
    identity = list(_target_identity(info))
    installed = row["installed"]
    if identity != installed:
        if identity[:2] != installed[:2]:  # device / inode
            raise DestinationRefused("original_managed_installed_image_changed")
        if identity[2:3] != installed[2:3]:  # ctime_ns
            raise DestinationRefused("original_managed_installed_image_changed")
        if identity[3:4] != installed[3:4]:  # mtime_ns
            raise DestinationRefused("original_managed_installed_image_changed")
        if identity[4:5] != installed[4:5]:  # size
            raise DestinationRefused("original_managed_installed_image_changed")
        # Mode / uid / gid / links, or a noncanonical identity shape.
        raise DestinationRefused("original_managed_installed_image_changed")
    if _release_hash(active, store.owner) != after_hash:
        raise DestinationRefused("original_managed_installed_image_changed")


def _restore_bound_managed_file_locked(store, record: dict, *, parent: Path,
                                       active: Path, attest, saved_base: str | None = None) -> dict:
    """Restore one interrupted CAS with the previous Config established."""
    from shared_apply_operation import MANAGED_WRITING, _managed_restore_has_base
    from shared_apply_seal import _release_hash, _stat

    allowed = (record.get("phase") == MANAGED_WRITING if saved_base is None
               else _managed_restore_has_base(record, saved_base))
    if not allowed or store.read() != record or attest() is not True:
        raise DestinationRefused("original_managed_restore_owner_required")
    row = record["managed"]
    name = row["name"]
    before, _, after, _, old_hash, new_hash = _managed_write_images(store, record, name, parent)
    if (row["before_sha256"], row["after_sha256"]) != (_sha(before), _sha(after)):
        raise DestinationRefused("original_managed_restore_sources_changed")
    path = active / "managed" / name
    uid = store.owner
    _stat(active, uid, directory=True)

    def observe():
        raw, info = _target(path, uid)
        identity = list(_target_identity(info))
        if raw == before and (identity == row["before_identity"] or
                "restore" in row and _matches_stage(row["restore"], raw, info) and
                identity[5:] == row["before_identity"][5:]):
            return "before", identity
        if (raw == after and "ready" in row and _matches_stage(row["ready"], raw, info) and
                identity[5:] == row["before_identity"][5:] and
                ("installed" not in row or identity == row["installed"])):
            return "after", identity
        raise DestinationRefused("original_managed_restore_foreign_image")

    state, identity = observe()
    temps = [_found_temp(path, row[k], uid) for k in ("ready", "restore") if k in row]
    for temp in temps:
        if temp is not None:
            temp.unlink()
            _sync(temp.parent)
    if (observe() != (state, identity) or
            _release_hash(active, uid) != (old_hash if state == "before" else new_hash)):
        raise DestinationRefused("original_managed_restore_release_changed")
    if state == "after":
        def stage(phase, item, data, info):
            nonlocal record, row
            if phase == "ready":
                row = {**row, "restore": {**_stage_pin(info, data), "temp": item.name}}
                record = store._checkpoint_managed_write(record, row, attest,
                    shared_work_parent=parent, saved_base=saved_base)

        _replace(path, after, before, uid, stage_fn=stage, expected_identity=tuple(identity))

    # Recovery may itself resume after rename but before directory fsync.
    _sync(path.parent)

    def restored():
        return attest() is True and observe()[0] == "before" and _release_hash(active, uid) == old_hash

    return store._checkpoint_managed_write(record, None, restored, shared_work_parent=parent,
                                            saved_base=saved_base)


def _observe_found_source(path: Path, name: str, row: tuple,
                         found: dict, uid: int) -> tuple[str, tuple | None, Path | None]:
    before, after, original, status = row
    stage = found["stages"].get(name)
    forward = stage["pin"] if stage is not None else None
    rollback = found.get("restoring", {})
    backward = rollback.get(name)
    linked_temp = None
    try:
        raw, info = _target(path, uid)
    except DestinationRefused as exc:
        if status != "missing":
            raise
        if isinstance(exc.__cause__, FileNotFoundError):
            _shared_found_assert_missing(path, uid)
            if name in rollback and backward is None:
                return "restored", None, None
            if stage is None or stage["state"] == "ready":
                return "before", None, None
            raise DestinationRefused("found_installed_source_missing") from exc
        if forward is None or stage["state"] != "ready":
            raise
        # A crash between link-once and unlinking its temporary name leaves
        # two links only for a newly created shared list. Pin both names.
        raw, info = _target(path, uid, links=2)
        linked_temp = _found_temp(path, forward, uid, links=2)
        if linked_temp is None or not _matches_stage(forward, raw, info):
            raise DestinationRefused("foreign_found_hardlink") from exc
    identity = _file_identity(info)
    if backward is not None and raw == before and _matches_stage(backward, raw, info):
        return "restored", identity, None
    if (status == "present" and raw == before and identity == original and
            (stage is None or stage["state"] == "ready")):
        return "before", identity, None
    if before != after and raw == after and forward is not None and _matches_stage(
            forward, raw, info):
        post = found.get("post", {}).get(name)
        if post is not None and identity != tuple(post[k] for k in
                ("device", "inode", "ctime_ns", "mtime_ns", "size")):
            raise DestinationRefused("found_postimage_changed")
        return "after", identity, linked_temp
    raise DestinationRefused("foreign_found_source_image")


def _recover_found_preimages_locked(rows: dict, targets: dict, *, store, record: dict,
                                   plan_bytes: bytes, uid: int, attest,
                                   bound_attest=None) -> dict:
    """Restore only journal-attributed writes with the original Config and P2 held."""
    from shared_apply_operation import FOUND_RESTORING, FOUND_ROLLBACK_FROM

    if record["phase"] not in FOUND_ROLLBACK_FROM | {FOUND_RESTORING}:
        raise DestinationRefused("found_rollback_phase_refused")
    verified = _qualified_shared_found_batch(rows)
    if set(targets) != set(verified) or len(set(targets.values())) != len(verified):
        raise DestinationRefused("shared_found_targets_incomplete")
    if store.read() != record or attest() is not True:
        raise DestinationRefused("original_found_rollback_witness_refused")

    def observe_all():
        found = record["found"]
        out = {}
        for name in SHARED_FOUND_NAMES:
            path = targets[name]
            current = _observe_found_source(path, name, verified[name], found, uid)
            # Validate every extant temporary name before the first mutation.
            pinned = found["stages"].get(name, {}).get("pin")
            if pinned is not None and current[2] is None:
                _found_temp(path, pinned, uid)
            restored = found.get("restoring", {}).get(name)
            if restored is not None:
                _found_temp(path, restored, uid)
            out[name] = current
        return out

    observe_all()
    store._attest_bound_found_checkpoint(record, bound_attest)
    if record["phase"] != FOUND_RESTORING:
        record = store.record_found_rollback(
            record, plan_bytes, bound_attest=bound_attest)
    for name in reversed(SHARED_FOUND_NAMES):
        path = targets[name]
        before, after, _, status = verified[name]
        found = record["found"]
        state, identity, linked_temp = observe_all()[name]
        if attest() is not True:
            raise DestinationRefused("original_found_rollback_witness_refused")
        store._attest_bound_found_checkpoint(record, bound_attest)
        if state == "after":
            if status == "missing":
                record = store.record_found_rollback(
                    record, plan_bytes, source=name, bound_attest=bound_attest)
                # Recheck the exact attributed inode immediately before unlink.
                if _observe_found_source(path, name, verified[name], record["found"],
                                         uid) != (state, identity, linked_temp):
                    raise DestinationRefused("found_create_changed_during_rollback")
                path.unlink()
                _sync(path.parent)
            else:
                # A refused or interrupted prior rollback may have left its
                # own staged before-image. It is never another authority.
                prior = found["restoring"].get(name)
                temp = _found_temp(path, prior, uid) if prior is not None else None
                if temp is not None:
                    temp.unlink()
                    _sync(path.parent)

                def stage_restore(phase, item, content, info):
                    nonlocal record
                    if phase == "ready":
                        if content != before or attest() is not True:
                            raise DestinationRefused("original_found_restore_stage_refused")
                        pin = {**_stage_pin(info, content), "temp": item.name}
                        record = store.record_found_rollback(
                            record, plan_bytes, source=name, pin=pin,
                            bound_attest=bound_attest)

                _replace(path, after, before, uid, stage_fn=stage_restore,
                         expected_identity=identity)
        # Clean a ready forward file that never installed, or the remaining
        # link of an interrupted create. Never scan/unlink by a name pattern.
        forward = found["stages"].get(name, {}).get("pin")
        temp = _found_temp(path, forward, uid) if forward is not None else None
        if temp is not None:
            temp.unlink()
            _sync(path.parent)
    if (any(state == "after" for state, _, _ in observe_all().values()) or
            attest() is not True):
        raise DestinationRefused("original_found_restore_not_attested")
    return store.record_found_rollback(
        record, plan_bytes, complete=True, bound_attest=bound_attest)


def _native_found_wal_context(operation_id: str, config_fd: int):
    """Bind a private found phase to the existing locked Config and seal."""
    import sys
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation_id, str) or
            not re.fullmatch(r"[a-f0-9]{32}", operation_id) or
            type(config_fd) is not int or config_fd < 3):
        raise DestinationRefused("original_native_fd9_required")
    from shared_apply_seal import WORK, verify_seal
    from shared_apply_operation import SharedApplyOperation
    from auto_detect_owned_sources import OWNED_ROOT
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd)
    from auto_detect_gui_hostlist import AUTO_HOSTLIST
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    # The original OPNsense Config lock is an inherited real open file
    # description; a JSON token or fresh guessed lock is insufficient.
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    store = SharedApplyOperation(owner=0)
    record = store.read()
    if (record is None or
            "found" not in record or
            record["detail"]["id"] != operation_id or
            record["detail"]["page"] != "strategies"):
        raise DestinationRefused("original_apply_not_activating")
    work = WORK / operation_id
    signed = verify_seal(work, owner=0)
    target = work / "plan.json"
    raw, mode = _target(target, 0)
    if (stat.S_IMODE(mode.st_mode) != 0o600 or not raw or
            _sha(raw) != signed["sha256"]["plan.json"] or
            _sha(raw) != record["found"]["plan_sha256"]):
        raise DestinationRefused("shared_found_original_plan_changed")
    try:
        plan = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise DestinationRefused("shared_found_original_plan_invalid") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            plan.get("result") != "prepared" or
            plan.get("dependencies") != record["detail"]["base"] or
            plan.get("changed_fields") != record["detail"]["changed_fields"] or
            not isinstance(plan.get("found_intent"), dict) or
            plan["found_intent"].get("commit_authorized") is not False or
            plan["found_intent"].get("config_revision") != record["detail"]["base"] or
            not isinstance(plan.get("found_batch"), dict)):
        raise DestinationRefused("shared_found_plan_not_original_owner")
    targets = {"youtube": OWNED_ROOT / "youtube.txt",
               "user": OWNED_ROOT / "user.txt",
               "auto": AUTO_HOSTLIST}
    def attest() -> bool:
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        return verify_seal(work, owner=0) == signed

    return store, record, raw, plan["found_batch"], targets, attest


def _bound_found_native_witness(store, original: dict, attest):
    """Same original FD4/FD9/P2 scope, exact immutable identity across phases.

    The caller holds the existing destination lock continuously. The WAL
    checks both roots itself; this witness additionally binds each phase to
    the original native Config descriptor and sealed operation context.
    No phase, caller-provided digest or semantic receipt grants lifecycle.
    """
    if "manifest" not in original and "previous_manifest" not in original:
        return None
    if "manifest" not in original or "found" not in original:
        raise DestinationRefused("original_found_candidate_pin_required")
    identity = tuple(original.get(key) for key in
                     ("detail", "previous", "manifest", "previous_manifest"))
    intent = tuple(original["found"].get(key) for key in
                   ("schema", "kind", "plan_sha256", "sources", "runtime_mode"))

    def witness(record):
        return (type(record) is dict and "found" in record and
                tuple(record.get(key) for key in
                      ("detail", "previous", "manifest", "previous_manifest")) == identity and
                tuple(record["found"].get(key) for key in
                      ("schema", "kind", "plan_sha256", "sources", "runtime_mode")) == intent and
                store.read() == record and attest() is True and store.read() == record)
    return witness


def _attest_found_after_locked(rows: dict, targets: dict, record: dict, *, uid: int) -> bool:
    """The recorded post-images belong to this Apply, including untouched sources."""
    batch = _qualified_shared_found_batch(rows)
    found = record["found"]
    if set(batch) != set(found["post"]):
        return False
    for name, row in batch.items():
        state, physical, alias = _observe_found_source(targets[name], name, row, found, uid)
        pin = found["post"][name]
        expected = "after" if row[0] != row[1] else "before"
        expected_pin = (None if pin["status"] == "missing" else tuple(
            pin[key] for key in ("device", "inode", "ctime_ns", "mtime_ns", "size")))
        if state != expected or physical != expected_pin or alias is not None:
            return False
    return True


def _attest_bound_inert_found_predecessor(record: dict) -> tuple[str, str]:
    """Original full stopped owner proof before bound file save or rollback.

    No native Config or P2a queue acquisition here. The original caller
    already holds FD9 -> Config -> P2. Retired learning needs its own
    lock-order-correct retirement proof, so it remains explicitly refused.
    """
    from neutral_schema3_quiescent_preimage import (
        _zero_processes, _safe_empty_directory, _empty_kernel,
        CHILD_PID, MONITOR_PID, DAEMON_PID, PRODUCER_ROOT)
    from neutral_schema3_previous_physical import _full_prior_tree
    from auto_detect_minute import inspect_inert_release
    from shared_apply_seal import WORK
    from voice_live_inspect import COMMON_ACTIVE

    prior = record.get("previous")
    if (type(prior) is not dict or
            prior["candidate"] != record["detail"]["base"] or
            record.get("previous_manifest", {}).get("schema") == 2):
        raise DestinationRefused("bound_found_stopped_inert_owner_required")
    _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
    old_work = WORK / prior["id"]
    tree = _full_prior_tree(old_work, COMMON_ACTIVE, 0)
    if inspect_inert_release(old_work / "release", owner_uid=0) != "inactive":
        raise DestinationRefused("bound_found_inert_owner_required")
    _safe_empty_directory(PRODUCER_ROOT, 0)
    kernel = _empty_kernel(old_work / "release")
    _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
    return tree, kernel


@contextmanager
def _bound_found_queue_scope(queue_fd: int | None):
    """Borrow P2a from the original parent; never acquire it after Config."""
    if queue_fd is None:
        yield None
        return
    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
    from voice_ipfw_adapter import require_lifecycle_lock
    import pwd

    require_lifecycle_lock()
    gid = pwd.getpwnam(ENGINE_USER).pw_gid
    if gid <= 0:
        raise DestinationRefused("bound_found_learning_gid_unqualified")
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
    # No fresh Config lock on exit: the original PHP Config::save may
    # already have released FD4 while the parent still owns P2a.
    with queue.inherited_exclusive(queue_fd):
        yield queue


def _attest_bound_found_predecessor(record: dict, config_fd: int,
                                    queue: DurableInbox | None):
    """Full stopped original owner, inert or already terminal retired learning.

    A running owner is never qualified for physical Found writes by this
    function. Learning requires the original inherited P2a before Config,
    immutable historical PID/epoch, terminal ACK/archive and all-PID P2b.
    No retirement repair, queue acquisition, signal or Config save here.
    """
    if record.get("previous_manifest", {}).get("schema") != 2:
        return _attest_bound_inert_found_predecessor(record)
    if not isinstance(queue, DurableInbox) or not queue._held:
        raise DestinationRefused("bound_found_original_queue_fd_required")

    from auto_detect_owner import attest_bound_found_stopped_learning_predecessor
    from auto_detect_learning_retirement import retired_learning_stopped, RETIRE_DIR, READY
    from auto_detect_fd import _probe_original_inode
    from neutral_schema3_quiescent_preimage import (
        _zero_processes, _empty_kernel, CHILD_PID, MONITOR_PID, DAEMON_PID)
    from neutral_schema3_previous_physical import _full_prior_tree
    from neutral_root_stage import verify_original_operation_pins
    from shared_apply_seal import WORK
    from voice_live_inspect import COMMON_ACTIVE

    prior = record["previous"]
    def attest():
        return attest_bound_found_stopped_learning_predecessor(record, config_fd)

    def inspect(path, device, inode, *, owner, writer_gid):
        return _probe_original_inode(
            path, device, inode, owner=owner, writer_gid=writer_gid,
            attest_owner=lambda: attest().owner == owner)

    verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
    _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
    proof = attest()
    if (proof.operation_id != prior["id"] or proof.generation != prior["id"] or
            proof.owner_candidate_sha256 != prior["candidate"]):
        raise DestinationRefused("bound_found_retired_owner_changed")
    old_work = WORK / prior["id"]
    tree = _full_prior_tree(old_work, COMMON_ACTIVE, 0)
    receipts = EpochReceipts(owner_uid=0, writer_gid=queue.writer_gid)
    ready = receipts._generation(proof.generation, create=False) / RETIRE_DIR / READY
    before = _read(ready, 0)
    if not retired_learning_stopped(
            receipts, queue, proof, old_work,
            attest=attest, inspect=inspect, repair=False):
        raise DestinationRefused("bound_found_learning_retirement_incomplete")
    kernel = _empty_kernel(old_work / "release")
    _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
    verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
    if (attest() != proof or _read(ready, 0) != before or
            _full_prior_tree(old_work, COMMON_ACTIVE, 0) != tree):
        raise DestinationRefused("bound_found_retired_owner_changed")
    return tree, kernel, proof, _sha(before)


def shared_apply_bound_found_files_original_fd9(operation_id: str, config_fd: int,
                                               *, raw_pipe: bytes, config_digest: str,
                                               before_save, queue_fd: int | None = None) -> dict:
    """Private original PHP/FD9 file-save integration, not a lifecycle command.

    Bind from the actual original source, then enter the existing three-file
    CAS and Config-saving checkpoint while the same final semantic P2 scope
    remains held. No alternate file or Config writer. The first supported
    physical predecessor is stopped: inert or fully retired learning under
    the original inherited P2a. A running predecessor remains fenced.
    """
    from neutral_shared_apply_source_gate import (
        native_bind_found_prepared_fd9, _with_native_found_prepared_semantic)

    if not callable(before_save):
        raise DestinationRefused("bound_found_original_save_scope_required")
    def write_locked(semantic, store, record, raw, rows, targets, attest):
        prior = record.get("previous")
        mode = record["found"].get("runtime_mode")
        if (type(prior) is not dict or semantic.previous_state != "stopped" or
                semantic.previous_generation != prior["id"] or
                semantic.candidate_root_sha256 != record["manifest"]["root_sha256"] or
                mode not in ("0", "1") or (mode == "1" and not semantic.candidate_enabled)):
            raise DestinationRefused("bound_found_stopped_inert_owner_required")

        physical = _attest_bound_found_predecessor(record, config_fd, queue)
        if (_attest_bound_found_predecessor(record, config_fd, queue) != physical or
                store.read() != record or attest() is not True):
            raise DestinationRefused("bound_found_old_owner_changed")
        native_witness = _bound_found_native_witness(store, record, attest)

        def bound_attest(current):
            # Recheck full old owner immediately before the first physical
            # write and before Config::save. Between those two, original
            # FD9+FD4+P2 and immutable pins guard every durable inode stage.
            return (native_witness(current) and
                    (current["phase"] not in ("prepared", "found-files-written") or
                     _attest_bound_found_predecessor(current, config_fd, queue) == physical))

        return _write_shared_found_files_locked(
            store, record, raw, rows, targets, attest,
            before_save=before_save, bound_attest=bound_attest)

    with _bound_found_queue_scope(queue_fd) as queue:
        _, pending, _, _, _, _ = _native_found_wal_context(operation_id, config_fd)
        if pending.get("previous_manifest", {}).get("schema") == 2 and queue is None:
            raise DestinationRefused("bound_found_original_queue_fd_required")
        witness, _ = native_bind_found_prepared_fd9(
            operation_id, raw_pipe, config_fd, config_digest=config_digest)
        return _with_native_found_prepared_semantic(
            witness, config_fd, config_digest=config_digest,
            continue_locked=write_locked)


def shared_apply_found_files_original_fd9(operation_id: str, config_fd: int,
                                          *, before_save=None) -> dict:
    """Apply the P2 files under the original WAL and keep P2 through native save."""
    from auto_detect_gui_hostlist import AUTO_LOCK

    store, record, raw, rows, targets, attest = _native_found_wal_context(
        operation_id, config_fd)
    if record["phase"] != "prepared":
        raise DestinationRefused("original_apply_not_prepared")
    # A verified OLD root is not a verified successor. Never enter P2 writes.
    if "previous_manifest" in record or "manifest" in record:
        raise DestinationRefused("original_found_dual_root_not_bound")
    with exclusive_destination_lock(AUTO_LOCK, 0):
        return _write_shared_found_files_locked(
            store, record, raw, rows, targets, attest, before_save=before_save)


def _write_shared_found_files_locked(store, record, raw, rows, targets, attest, *,
                                    before_save, bound_attest=None) -> dict:
    """One existing CAS/WAL path, already under original Config then P2."""
    from auto_detect_effective_known import _verify_planned_preimages_locked
    from auto_detect_owned_sources import OWNED_ROOT, read_owned
    verified = _qualified_shared_found_batch(rows)
    _verify_planned_preimages_locked(verified, targets, owned_root=OWNED_ROOT, owner_uid=0)

    def exact_original_witness(phase: str, content: bytes) -> bool:
        if content != raw or not attest():
            return False
        if phase == "found-files-writing":
            _verify_planned_preimages_locked(
                verified, targets, owned_root=OWNED_ROOT, owner_uid=0)
        elif phase == "found-files-written":
            owned = read_owned(OWNED_ROOT, owner_uid=0)
            if (owned is None or any(owned[name].encode() != verified[name][1]
                                      for name in ("youtube", "user"))):
                return False
        return True

    bound_kwargs = {} if bound_attest is None else {"bound_attest": bound_attest}
    result = _locked_shared_found_apply_journal(
        rows, targets, store=store, detail=record["detail"],
        plan_bytes=raw, uid=0, attest=exact_original_witness, **bound_kwargs)
    if before_save is not None:
        store.advance_found_config(
            "found-config-saving", record["detail"], raw,
            lambda phase, content: attest() and _attest_found_after_locked(
                rows, targets, store.read(), uid=0), **bound_kwargs)
        # Config::save() can release FD4. The callback must only wait for
        # the PHP parent's acknowledgement; never try to re-lock Config.
        before_save()
    return result
