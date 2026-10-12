#!/usr/bin/env python3
"""Original-FD9, original-Config-flock old Telegram runtime two-rename restore.

Import-only real filesystem mutation without CLI/configd/GUI/boot/service
wiring. The previous Config/runtime+marker image, fixed old-IPFW replay,
original candidate Config/runtime hashes (sealed BEFORE kernel writes)
and exactly stopped processes are checked under original locks.

A write-once fsynced runtime intent precedes both same-parent renames:
candidate active -> retired; previous ready -> active. A crash at either
rename is recovered ONLY from exact candidate/previous content hashes,
never an unknown/foreign directory. The retired candidate and all journals
remain durable. Config inode/bytes and old marker are NOT modified. Restored
runtime may contain old "enabled" state but without the marker/processes:
this is deliberately NOT an authorized service restart or Voice ON.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from voice_cutover_backup import _private_dir, _read_private_file, _sync_dir
from voice_native_legacy_previous_seal import _digest, _write_once, NAME
from voice_native_legacy_restore_plan import PLAN_NAME, inspect_legacy_restore_plan
from voice_native_legacy_reverse_wal import (
    WAL_NAME, inspect_legacy_reverse_wal, _stopped, _ledger_clear,
    _old_marker_off,
)
from voice_native_legacy_files_ready import (
    FILES_NAME, inspect_legacy_files_ready,
)
from voice_native_legacy_ipfw_replay import (
    REPLAY_NAME, _strict_snapshot, _expected_after, _steps,
)
from voice_native_legacy_poc_guard import _legacy_read
from voice_cutover_runtime_restore import (
    _safe_parent, _stage_old_tree, _fingerprint,
)
from voice_native_recovery_quiescence import _locked_config
from voice_cutover_config_restore import _sha_fd, _pinned_regular

NAME_RESTORE = "legacy-runtime-restore"
SCHEMA = 1
LIMIT = 8192
FILES = frozenset(("intent.json", "intent.sha256"))
BASE_FILES = frozenset((NAME, PLAN_NAME, WAL_NAME, REPLAY_NAME, FILES_NAME))


class LegacyRuntimeRestoreError(RuntimeError):
    pass


def _intent_data(plan, wal, active, parent):
    suffix = wal["restore_plan_sha256"][:20]
    return {
        "schema": SCHEMA,
        "phase": "legacy-runtime-mutating-not-five-domain-complete",
        "restore_plan_sha256": wal["restore_plan_sha256"],
        "previous_runtime_sha256": plan["previous_five"]["runtime"],
        "candidate_runtime_sha256": wal["candidate_runtime_sha256"],
        "candidate_config_sha256": wal["candidate_config_sha256"],
        "parent_dev": parent.st_dev, "parent_ino": parent.st_ino,
        "active_name": active.name,
        "ready_name": ".voice-legacy-ready-" + suffix,
        "retired_name": ".voice-legacy-retired-" + suffix,
        "safe_to_restart": False, "safe_to_enable_voice": False,
    }


def _read_intent(root, expected):
    directory = root / NAME_RESTORE
    _private_dir(directory)
    if set(os.listdir(directory)) != FILES:
        raise LegacyRuntimeRestoreError("foreign or incomplete old runtime intent")
    raw = _read_private_file(directory / "intent.json", LIMIT)
    if _read_private_file(directory / "intent.sha256", 65) != (
        _digest(raw) + "\n"
    ).encode("ascii"):
        raise LegacyRuntimeRestoreError("corrupt old runtime rename intent")
    if json.loads(raw) != expected:
        raise LegacyRuntimeRestoreError("old runtime intent belongs to another restore")
    return expected


def _write_intent(root, record):
    temp = root / NAME_RESTORE
    os.mkdir(temp, 0o700)
    _sync_dir(root)
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(raw) > LIMIT:
        raise LegacyRuntimeRestoreError("old runtime intent too large")
    _write_once(temp / "intent.json", raw)
    _write_once(temp / "intent.sha256", (_digest(raw) + "\n").encode("ascii"))
    _sync_dir(temp)
    return _read_intent(root, record)


def restore_legacy_runtime(
    *, root, config_path, config_fd, config_owner, active_runtime,
    legacy_marker, ledger_root, process_probe, readonly_ipfw,
    require_lifecycle_owner,
):
    """Real old-runtime restoration, NO Config/marker/process installation."""
    if not callable(require_lifecycle_owner) or (
        type(config_fd) is not int or config_fd < 0
    ):
        raise LegacyRuntimeRestoreError("original Zapret FD9/Config owner missing")
    root, active, config_path = Path(root), Path(active_runtime), Path(config_path)

    def held():
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        _pinned_regular(config_path, config_fd, owner=config_owner)

    held()
    _private_dir(root)
    entries = set(os.listdir(root))
    if entries not in (BASE_FILES, BASE_FILES | {NAME_RESTORE}):
        raise LegacyRuntimeRestoreError("foreign or partial Voice recovery artifact")
    resumed = NAME_RESTORE in entries
    # The prepared stage is the SINGLE allowed extra artifact, and its full
    # prior Config/runtime+marker manifest is re-opened before live changes.
    image_report = inspect_legacy_files_ready(
        root, allow_runtime_restore=resumed,
    )
    wal = inspect_legacy_reverse_wal(
        root, allow_ipfw_replay=True, allow_files_stage=FILES_NAME,
        allow_runtime_restore=resumed,
    )
    plan = inspect_legacy_restore_plan(root)
    if image_report["previous_five"] != plan["previous_five"]:
        raise LegacyRuntimeRestoreError("previous file image no longer matches old PoC")
    source = root / NAME / "previous"
    image = root / FILES_NAME / "install-image"
    if plan["previous_five"]["runtime"] == wal["candidate_runtime_sha256"]:
        raise LegacyRuntimeRestoreError("candidate and previous runtime indistinguishable")
    parent = _safe_parent(active.parent)
    record = _intent_data(plan, wal, active, parent)
    ready = active.with_name(record["ready_name"])
    retired = active.with_name(record["retired_name"])

    def verify(path, sha, previous_modes=False):
        if path.is_symlink():
            raise LegacyRuntimeRestoreError("linked recovery runtime path")
        if not path.exists():
            return False
        return _fingerprint(
            image / "config.xml", path, source,
            must_match_previous_modes=previous_modes,
        ) == sha

    def gate(*, require_disabled):
        held()
        if _sha_fd(config_fd)[0] != wal["candidate_config_sha256"]:
            raise LegacyRuntimeRestoreError("original Config candidate was modified")
        if _stopped(process_probe) != "exact-three-role-absence" or (
            _ledger_clear(ledger_root) not in (
                "no-native-ledger","empty-private-ledger",
            )
        ):
            raise LegacyRuntimeRestoreError("old/new engine or native ledger changed")
        if _legacy_read(Path(legacy_marker)) is not None:
            raise LegacyRuntimeRestoreError("legacy PoC marker reappeared")
        if require_disabled and (
            _old_marker_off(legacy_marker, active) !=
            "legacy-marker-absent-and-runtime-not-enabled"
        ):
            raise LegacyRuntimeRestoreError("legacy PoC runtime still enabled")
        if _strict_snapshot(readonly_ipfw) != _expected_after(
            plan, len(plan["legacy_ipfw_commands"])
        ):
            raise LegacyRuntimeRestoreError("restored old IPFW kernel drifted")
        count,started = _steps(root / REPLAY_NAME, plan)
        if started or count != len(plan["legacy_ipfw_commands"]):
            raise LegacyRuntimeRestoreError("old IPFW redo was not fully committed")
        if inspect_legacy_reverse_wal(
            root, allow_ipfw_replay=True, allow_files_stage=FILES_NAME,
            allow_runtime_restore=resumed,
        ) != wal:
            raise LegacyRuntimeRestoreError("reverse WAL was modified")
        if inspect_legacy_files_ready(
            root, allow_runtime_restore=resumed,
        ) != image_report:
            raise LegacyRuntimeRestoreError("previous file image was modified")
        if (parent.st_dev,parent.st_ino) != (
            _safe_parent(active.parent).st_dev, _safe_parent(active.parent).st_ino
        ):
            raise LegacyRuntimeRestoreError("runtime parent inode changed")

    gate(require_disabled=not resumed)
    if resumed:
        _read_intent(root,record)
    else:
        if (ready.exists() or ready.is_symlink() or
            retired.exists() or retired.is_symlink()):
            raise LegacyRuntimeRestoreError("foreign old runtime rename path")
        if not verify(active, wal["candidate_runtime_sha256"]):
            raise LegacyRuntimeRestoreError("untrusted active candidate runtime")
        # The immutable pre-image and exactly bound parent enter durable
        # storage BEFORE staging, and before the first live rename.
        _write_intent(root, record)
        resumed = True
    _read_intent(root,record)

    # Reentrant journal resume after a crash BEFORE installing the ready tree.
    if not (ready.exists() or ready.is_symlink()) and (
        not (retired.exists() or retired.is_symlink())
    ):
        if not verify(active, wal["candidate_runtime_sha256"]):
            raise LegacyRuntimeRestoreError("candidate changed before preparing old tree")
        gate(require_disabled=True)
        _stage_old_tree(image, source, ready, plan["previous_five"]["runtime"])

    # State 0: candidate active, prepared previous ready, nothing retired.
    if not (retired.exists() or retired.is_symlink()):
        if (not verify(active, wal["candidate_runtime_sha256"]) or
            not verify(ready, plan["previous_five"]["runtime"], True)):
            raise LegacyRuntimeRestoreError("unexpected pre-first-rename runtime")
        gate(require_disabled=True)
        _read_intent(root,record)
        os.rename(active,retired)
        _sync_dir(active.parent)
    if not verify(retired, wal["candidate_runtime_sha256"]):
        raise LegacyRuntimeRestoreError("retired candidate runtime was modified")

    # State 1: active missing after first rename; complete the second rename.
    if not active.exists() and not active.is_symlink():
        if not verify(ready, plan["previous_five"]["runtime"], True):
            raise LegacyRuntimeRestoreError("ready previous runtime absent or changed")
        gate(require_disabled=False)
        _read_intent(root,record)
        os.rename(ready,active)
        _sync_dir(active.parent)

    # State 2: previous tree active, candidate preserved, no ready tree.
    if (ready.exists() or ready.is_symlink() or
        not verify(active, plan["previous_five"]["runtime"], True) or
        not verify(retired, wal["candidate_runtime_sha256"])):
        raise LegacyRuntimeRestoreError("restored runtime not independently certified")
    gate(require_disabled=False)
    _read_intent(root,record)
    return {
        "state":"legacy-runtime-restored-config-marker-and-processes-pending",
        "candidate_retained": retired.name,
        "active_runtime_sha256":plan["previous_five"]["runtime"],
        "original_config_unchanged":True,
        "marker_restored":False,
        "process_restart_verified":False,
        "whole_rollback_complete":False,
        "safe_to_enable_voice":False, "public_voice_apply":False,
    }
