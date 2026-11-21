#!/usr/bin/env python3
"""Terminal schema3 native-N/debug retirement by the ONE original FD9.

The existing dynamic CursorChain has already delivered every N/debug event
through original Config/P1/DestinationCommit and physically ACKed its prefix.
This module only archives exact fully-ACKed stopped producer inodes, replaces
debug.log with an empty inode, and makes the original prelaunch root free of
the previous generation's N files. No new event parser, Config writer, or
process owner exists here.

A protected intent precedes every rename. A crash at any individual rename
is resumed with the SAME immutable plan, original stopped owner, P2a lock,
all-PID P2b census and physical inode/SHA evidence. Never copytruncate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from auto_detect_cursor_chain import CursorChain, _learning_records_digest
from auto_detect_epoch_receipts import (
    EpochReceipts, _canonical, _directory, _read, _sync, _write_once,
)
from auto_detect_fd import FDState
from auto_detect_original_v2_model import _native_rebind_stable_snapshot
from auto_detect_queue import DurableInbox
from auto_detect_storage import LEARNING_NAME
from auto_detect_owner import LearningGenerationProof

RETIRE_DIR = "learning-retirement"
INTENT = "intent.json"
READY = "ready.json"
MAX_NATIVE = 4 * 1024 * 1024


class LearningRetirementRefused(RuntimeError):
    """Never authorize a replacement engine after uncertain source state."""


def _entry(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _require_owner(receipts, queue, proof, workspace, attest):
    if (not isinstance(receipts, EpochReceipts) or
            not isinstance(queue, DurableInbox) or not queue._held or
            receipts.uid != queue.uid or
            receipts.writer_gid != queue.writer_gid or
            not isinstance(proof, LearningGenerationProof) or
            not isinstance(workspace, Path) or
            not workspace.is_absolute() or workspace.name != proof.generation or
            not callable(attest) or attest() != proof):
        raise LearningRetirementRefused("stopped_original_fd9_owner_required")
    if sys.platform.startswith("freebsd"):
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        if receipts.uid != 0 or os.geteuid() != 0:
            raise LearningRetirementRefused("stopped_original_root_required")
    queue._verify()


def _image(path: Path, receipts, queue, *, expected=None):
    st, data, _ = _native_rebind_stable_snapshot(
        path, receipts.uid, queue.writer_gid, allowed_links=(1,))
    identity = [st.st_dev, st.st_ino, len(data),
                hashlib.sha256(data).hexdigest()]
    if len(data) > MAX_NATIVE or (expected is not None and identity != expected):
        raise LearningRetirementRefused("stopped_learning_source_changed")
    return identity, st, data


def _drained(path, row, proof, queue, inspect):
    if (not callable(inspect) or
            inspect(path, row[0], row[1], owner=proof.owner,
                    writer_gid=queue.writer_gid) is not FDState.DRAINED):
        raise LearningRetirementRefused("stopped_learning_source_fd_not_drained")


def _tip(receipts, queue, proof, workspace):
    tip = CursorChain(receipts, queue).learning_tip(proof, workspace)
    if (tip["slot"] is not None or tip["intent"] is not None or
            tip.get("debug_cut_pending") is not None or
            queue.segments()):
        raise LearningRetirementRefused("stopped_learning_unacknowledged_source")
    if (tip["root"].parent != receipts._generation(proof.generation, create=False) or
            set(tip["state"]) != {number for number, _, _ in proof.learning} or
            tip["debug"]["path"] != str(queue.root / "debug.log")):
        raise LearningRetirementRefused("stopped_learning_final_tip_untrusted")
    for number, hostlist, source_path in proof.learning:
        state = tip["state"][number]
        if (state["path"] != source_path or
                state["hostlist"] != hostlist or
                len(state["streams"]) != 1 or
                state["streams"][0]["path"] != source_path or
                Path(source_path).parent != queue.root):
            raise LearningRetirementRefused("stopped_learning_native_stream_unretired")
    return tip


def _expected(proof, tip):
    numbers = [(number, Path(source_path)) for number, _, source_path in proof.learning]
    return {
        "schema": 3,
        "kind": "original-stopped-learning-terminal-intent",
        "generation": proof.generation,
        "owner_candidate_sha256": proof.owner_candidate_sha256,
        "final_args_sha256": proof.final_args_sha256,
        "native_map_sha256": proof.native_map_sha256,
        "cycle": tip["cycle"],
        "sequence": tip["sequence"],
        "previous_ack_sha256": tip["previous_ack_sha256"],
        "epoch_sha256": tip["epoch_sha256"],
        "native_sha256": _learning_records_digest(tip["state"]),
        "cursors": [
            {"name": path.name, "native_number": number,
             "cursor": tip["state"][number]["streams"][0]}
            for number, path in numbers
        ] + [{"name": "debug.log", "native_number": 0,
              "cursor": tip["debug"]}],
        "ack_authorized": False,
    }


def _root_entries(queue, proof, *, temporary=False):
    allowed = {"pending", "worker.lock", "inbox.txt", "debug.log"}
    allowed.update(Path(path).name for _, _, path in proof.learning)
    if temporary:
        allowed.add(".learning-retire-" + proof.generation + "-debug")
    if set(os.listdir(queue.root)) - allowed:
        raise LearningRetirementRefused("stopped_learning_foreign_producer_entry")


def _plan(receipts, queue, proof, workspace, tip, folder, attest, inspect,
          *, repair):
    intent_path = folder / INTENT
    expected = _expected(proof, tip)
    if _entry(intent_path):
        raw = _read(intent_path, receipts.uid)
        try:
            plan = json.loads(raw)
        except (ValueError, UnicodeError, TypeError) as exc:
            raise LearningRetirementRefused("stopped_learning_corrupt_terminal_intent") from exc
        if (raw != _canonical(plan) or
                set(plan) != set(expected) | {"sources"} or
                {k: v for k, v in plan.items() if k != "sources"} != expected or
                type(plan["sources"]) is not list or
                len(plan["sources"]) != len(expected["cursors"])):
            raise LearningRetirementRefused("stopped_learning_terminal_plan_changed")
        for row, cursor in zip(plan["sources"], expected["cursors"]):
            if (type(row) is not dict or
                    set(row) != {"name", "native_number", "image"} or
                    row["name"] != cursor["name"] or
                    row["native_number"] != cursor["native_number"] or
                    type(row["image"]) is not list or len(row["image"]) != 4 or
                    any(type(x) is not int or x < 0 for x in row["image"][:3]) or
                    type(row["image"][3]) is not str or
                    len(row["image"][3]) != 64 or
                    any(c not in "0123456789abcdef" for c in row["image"][3]) or
                    row["image"][:2] != [
                        cursor["cursor"]["device"], cursor["cursor"]["inode"]] or
                    row["image"][2] != cursor["cursor"]["offset"] or
                    row["image"][3] != cursor["cursor"]["prefix_sha256"]):
                raise LearningRetirementRefused("stopped_learning_terminal_cursor_not_ack")
        return plan, raw
    if not repair:
        return None, None
    if _entry(folder / READY):
        raise LearningRetirementRefused("stopped_learning_orphan_terminal_ready")
    _root_entries(queue, proof)
    inbox, _, inbox_data = _image(queue.inbox, receipts, queue)
    if inbox_data:
        raise LearningRetirementRefused("stopped_learning_legacy_inbox_not_empty")
    _drained(queue.inbox, inbox, proof, queue, inspect)
    plan = {**expected, "sources": []}
    for cursor in expected["cursors"]:
        path = queue.root / cursor["name"]
        image, _, data = _image(path, receipts, queue)
        if (image[:2] != [cursor["cursor"]["device"],
                          cursor["cursor"]["inode"]] or
                image[2] != cursor["cursor"]["offset"] or
                image[3] != cursor["cursor"]["prefix_sha256"] or
                (data and not data.endswith(b"\n"))):
            raise LearningRetirementRefused("stopped_learning_terminal_bytes_not_acked")
        _drained(path, image, proof, queue, inspect)
        plan["sources"].append({
            "name": cursor["name"],
            "native_number": cursor["native_number"],
            "image": image,
        })
    if attest() != proof or queue.segments():
        raise LearningRetirementRefused("stopped_learning_owner_changed_before_terminal")
    for row in plan["sources"]:
        path = queue.root / row["name"]
        _image(path, receipts, queue, expected=row["image"])
        _drained(path, row["image"], proof, queue, inspect)
    _write_once(folder, INTENT, _canonical(plan), receipts.uid)
    return plan, _canonical(plan)


def _fresh_debug(path, receipts, queue):
    if not _entry(path):
        return False
    image, st, data = _image(path, receipts, queue)
    if (data or image[2] != 0 or
            st.st_gid != queue.writer_gid or
            stat.S_IMODE(st.st_mode) != 0o660):
        raise LearningRetirementRefused("stopped_learning_new_debug_not_empty")
    return True


def _retire_files(receipts, queue, proof, folder, plan, attest, inspect,
                  *, repair):
    """Rename exact old N into private epoch; replace debug only after archive.

    The sole temporary path is predeclared in the original producer root.
    Every rename is separately fsynced and replayable. An absent live debug
    while the old inode is safely archived is an *interrupted* transition,
    not evidence permitting another engine to start.
    """
    temp = queue.root / (".learning-retire-" + proof.generation + "-debug")
    _root_entries(queue, proof, temporary=True)
    for row in plan["sources"]:
        name = row["name"]
        old = row["image"]
        live = queue.root / name
        archived = folder / ("old-" + name)
        exists = _entry(archived)
        live_exists = _entry(live)
        if exists:
            _image(archived, receipts, queue, expected=old)
            _drained(archived, old, proof, queue, inspect)
            if name != "debug.log" and live_exists:
                raise LearningRetirementRefused("stopped_learning_native_archive_alias")
            if name == "debug.log" and live_exists:
                _fresh_debug(live, receipts, queue)
                if _entry(temp):
                    raise LearningRetirementRefused("stopped_learning_debug_temp_alias")
        elif not live_exists:
            raise LearningRetirementRefused("stopped_learning_original_source_missing")
        if not exists:
            if not repair:
                return False
            _image(live, receipts, queue, expected=old)
            _drained(live, old, proof, queue, inspect)
            if name == "debug.log":
                if not _entry(temp):
                    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                 os.O_NOFOLLOW, 0o600)
                    try:
                        os.fchown(fd, receipts.uid, queue.writer_gid)
                        os.fchmod(fd, 0o660)
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    _sync(queue.root)
                _fresh_debug(temp, receipts, queue)
            if attest() != proof:
                raise LearningRetirementRefused("stopped_learning_original_owner_changed")
            if live.stat().st_dev != folder.stat().st_dev:
                raise LearningRetirementRefused("stopped_learning_cross_device_archive")
            os.rename(live, archived)
            _sync(queue.root)
            _sync(folder)
            _image(archived, receipts, queue, expected=old)
            _drained(archived, old, proof, queue, inspect)
        if name == "debug.log":
            if not _entry(live):
                if not repair:
                    return False
                if not _entry(temp) or not _fresh_debug(temp, receipts, queue):
                    raise LearningRetirementRefused("stopped_learning_debug_replacement_missing")
                if attest() != proof:
                    raise LearningRetirementRefused("stopped_learning_original_owner_changed")
                os.replace(temp, live)
                _sync(queue.root)
            if not _fresh_debug(live, receipts, queue):
                raise LearningRetirementRefused("stopped_learning_debug_not_replaced")
            fresh, _, _ = _image(live, receipts, queue)
            if fresh[:2] == old[:2]:
                raise LearningRetirementRefused("stopped_learning_debug_old_inode_reused")
            _drained(live, fresh, proof, queue, inspect)
        elif _entry(live):
            raise LearningRetirementRefused("stopped_learning_native_not_retired")
        if attest() != proof:
            raise LearningRetirementRefused("stopped_learning_owner_changed_after_rename")
    if _entry(temp):
        raise LearningRetirementRefused("stopped_learning_unconsumed_debug_temporary")
    return True


def retired_learning_stopped(receipts: EpochReceipts, queue: DurableInbox,
                             proof: LearningGenerationProof, workspace: Path, *,
                             attest, inspect, repair: bool = False) -> bool:
    """Verify or resume terminal retired schema3, never accept a partial state.

    The calling original lifecycle owns FD9 and P2a. Read-only mode never
    creates a directory, receipt, archive, or replacement inode.
    """
    _require_owner(receipts, queue, proof, workspace, attest)
    tip = _tip(receipts, queue, proof, workspace)
    epoch = receipts._generation(proof.generation, create=False)
    folder = epoch / RETIRE_DIR
    if not _entry(folder):
        if not repair:
            return False
        folder.mkdir(mode=0o700)
        _sync(epoch)
    _directory(folder, receipts.uid)
    if set(os.listdir(folder)) - (
            {INTENT, READY} |
            {f"old-{Path(path).name}" for _, _, path in proof.learning} |
            {"old-debug.log"}):
        raise LearningRetirementRefused("stopped_learning_foreign_archive_entry")
    plan, raw = _plan(receipts, queue, proof, workspace, tip, folder, attest,
                      inspect, repair=repair)
    if plan is None:
        return False
    if not _retire_files(receipts, queue, proof, folder, plan,
                         attest, inspect, repair=repair):
        return False
    inbox, _, data = _image(queue.inbox, receipts, queue)
    if data:
        raise LearningRetirementRefused("stopped_learning_original_inbox_changed")
    _drained(queue.inbox, inbox, proof, queue, inspect)
    _root_entries(queue, proof)
    if any(_entry(queue.root / Path(path).name) for _, _, path in proof.learning):
        raise LearningRetirementRefused("stopped_learning_old_native_name_remains")
    if not _fresh_debug(queue.root / "debug.log", receipts, queue):
        raise LearningRetirementRefused("stopped_learning_new_debug_missing")
    new_debug, _, _ = _image(queue.root / "debug.log", receipts, queue)
    _drained(queue.root / "debug.log", new_debug, proof, queue, inspect)
    expected_ready = {
        "schema": 3, "kind": "original-stopped-learning-terminal-ready",
        "generation": proof.generation,
        "intent_sha256": hashlib.sha256(raw).hexdigest(),
        "cycle": tip["cycle"],
        "sequence": tip["sequence"],
        "previous_ack_sha256": tip["previous_ack_sha256"],
        "ack_authorized": False,
    }
    ready_path = folder / READY
    if not _entry(ready_path):
        if not repair:
            return False
        if attest() != proof:
            raise LearningRetirementRefused("stopped_learning_owner_changed_before_ready")
        _write_once(folder, READY, _canonical(expected_ready), receipts.uid)
    if (_read(ready_path, receipts.uid) != _canonical(expected_ready) or
            attest() != proof or queue.segments()):
        raise LearningRetirementRefused("stopped_learning_ready_drift")
    return True


def main() -> None:
    raise SystemExit("original FD9-only stopped learning retirement; no standalone CLI")


if __name__ == "__main__":
    main()
