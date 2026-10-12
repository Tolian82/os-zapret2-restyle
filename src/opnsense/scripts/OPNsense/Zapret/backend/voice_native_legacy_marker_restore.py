#!/usr/bin/env python3
"""Durable restoration of EXACT previous Telegram PoC transient marker.

Internal import-only real filesystem step. No service, configd, GUI or boot
entrypoint, no process restart and no five-resource completed receipt.
Requires verified old IPFW table/rules, old runtime + original locked Config
already restored, stopped 3-role process set, no native kernel owner and
write-once intact old PoC evidence.

Fsync intent before touching /var/run; fsync the exact old bytes/mode to a
deterministic same-directory private staging inode, then link it into the
ABSENT target without ever replacing a foreign file. The temporary hardlink
is unlinked only after source/target are verified to be the same inode.
Power loss between hardlink and unlink is detectable and recoverable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import (
    _private_dir, _read_private_file, _sync_dir, inspect_previous,
)
from voice_native_legacy_previous_seal import _digest, _write_once, NAME
from voice_native_legacy_restore_plan import PLAN_NAME, inspect_legacy_restore_plan
from voice_native_legacy_reverse_wal import (
    WAL_NAME, inspect_legacy_reverse_wal, _stopped, _ledger_clear,
)
from voice_native_legacy_files_ready import (
    FILES_NAME, inspect_legacy_files_ready,
)
from voice_native_legacy_ipfw_replay import (
    REPLAY_NAME, _strict_snapshot, _expected_after, _steps,
)
from voice_native_legacy_runtime_restore import (
    NAME_RESTORE, _intent_data, _read_intent,
)
from voice_native_legacy_config_restore import (
    CONFIG_NAME, _record as config_record, _read_intent_config,
)
from voice_cutover_runtime_restore import _safe_parent, _fingerprint
from voice_cutover_config_restore import _sha_fd, _pinned_regular
from voice_native_recovery_quiescence import _locked_config

MARKER_NAME = "legacy-marker-restore"
SCHEMA = 1
MAX_RECORD = 8192
FILES = frozenset(("intent.json", "intent.sha256"))
ROOT_FILES = frozenset((
    NAME, PLAN_NAME, WAL_NAME, REPLAY_NAME, FILES_NAME,
    NAME_RESTORE, CONFIG_NAME,
))


class LegacyMarkerRestoreError(RuntimeError):
    pass


def _read_intent_marker(root, expected):
    directory = root / MARKER_NAME
    _private_dir(directory)
    if set(os.listdir(directory)) != FILES:
        raise LegacyMarkerRestoreError("incomplete or foreign marker restore intent")
    body = _read_private_file(directory / "intent.json", MAX_RECORD)
    if _read_private_file(directory / "intent.sha256", 65) != (
        _digest(body) + "\n"
    ).encode("ascii") or json.loads(body) != expected:
        raise LegacyMarkerRestoreError("marker intent digest or owner mismatch")
    return expected


def _arm(root, value):
    directory = root / MARKER_NAME
    os.mkdir(directory, mode=0o700)
    _sync_dir(root)
    body = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(body) > MAX_RECORD:
        raise LegacyMarkerRestoreError("marker redo record exceeds size bound")
    _write_once(directory / "intent.json", body)
    _write_once(directory / "intent.sha256", (_digest(body)+"\n").encode("ascii"))
    _sync_dir(directory)
    return _read_intent_marker(root,value)


def _marker_stat(path, raw, old_mode, *, links):
    """Pin no-follow same-parent marker bytes, exact owner, mode and link count."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != links
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != old_mode
            or info.st_size != len(raw)):
            raise LegacyMarkerRestoreError("foreign marker inode/mode/owner/links")
        if os.read(fd,len(raw)+1)!=raw:
            raise LegacyMarkerRestoreError("marker bytes differ from sealed previous")
        return info
    finally:
        os.close(fd)


def restore_legacy_marker(
    *, root, config_path, config_fd, config_owner, active_runtime,
    marker_path, ledger_root, process_probe, readonly_ipfw,
    require_lifecycle_owner,
):
    """Actual original PoC marker install; no public authorization to start."""
    if (not callable(require_lifecycle_owner)
        or type(config_fd) is not int or config_fd < 0):
        raise LegacyMarkerRestoreError("missing original FD9/Config authority")
    root,config_path,active,marker=map(
        Path,(root,config_path,active_runtime,marker_path),
    )
    def held():
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        return _pinned_regular(config_path,config_fd,owner=config_owner)

    held()
    _private_dir(root)
    entries=set(os.listdir(root))
    if entries not in (ROOT_FILES, ROOT_FILES|{MARKER_NAME}):
        raise LegacyMarkerRestoreError("unknown previous-PoC recovery evidence")
    resumed=MARKER_NAME in entries
    plan=inspect_legacy_restore_plan(root)
    wal=inspect_legacy_reverse_wal(
        root,allow_ipfw_replay=True,allow_files_stage=FILES_NAME,
        allow_runtime_restore=True,allow_config_restore=True,
        allow_marker_restore=resumed,
    )
    image_info=inspect_legacy_files_ready(
        root,allow_runtime_restore=True,allow_config_restore=True,
        allow_marker_restore=resumed,
    )
    if image_info["previous_five"]!=plan["previous_five"]:
        raise LegacyMarkerRestoreError("old marker image previous-five mismatch")
    source=root/NAME/"previous"
    image=root/FILES_NAME/"install-image"
    saved=inspect_previous(source)
    config_expected=config_record(plan,wal,held(),saved)
    _read_intent_config(root,config_expected)
    if _sha_fd(config_fd)!=(plan["previous_five"]["config"],saved["config"]["bytes"]):
        raise LegacyMarkerRestoreError("prior Config not yet restored")

    parent=_safe_parent(marker.parent)
    runtime_parent=_safe_parent(active.parent)
    restore_record=_intent_data(plan,wal,active,runtime_parent)
    _read_intent(root,restore_record)
    retired=active.with_name(restore_record["retired_name"])
    ready=active.with_name(restore_record["ready_name"])
    if marker.name in ("",".","..") or marker.is_symlink():
        raise LegacyMarkerRestoreError("unsafe old PoC marker target")
    if marker.parent == root:
        raise LegacyMarkerRestoreError("old transient marker cannot be stored in recovery root")
    saved_marker=_read_private_file(root/FILES_NAME/"marker.bin",64)
    md=plan["marker"]
    if _digest(saved_marker)!=md["sha256"] or len(saved_marker)!=md["bytes"]:
        raise LegacyMarkerRestoreError("saved transient marker differs")
    stage=marker.with_name("." + marker.name + ".voice-legacy-" +
                           wal["restore_plan_sha256"][:20])
    if stage==marker:
        raise LegacyMarkerRestoreError("marker staging target overlaps")

    intent={
        "schema":SCHEMA,"phase":"marker-restoring-three-processes-not-started",
        "restore_plan_sha256":wal["restore_plan_sha256"],
        "previous_marker_sha256":md["sha256"],
        "previous_marker_bytes":md["bytes"],"previous_marker_mode":md["mode"],
        "marker_path":str(marker),"stage_name":stage.name,
        "parent_dev":parent.st_dev,"parent_ino":parent.st_ino,
        "config_dev":config_expected["device"],
        "config_ino":config_expected["inode"],
        "safe_to_start":False,"safe_to_enable_voice":False,
        "whole_rollback_complete":False,
    }

    def gate():
        held()
        if (parent.st_dev,parent.st_ino)!=(
            _safe_parent(marker.parent).st_dev,_safe_parent(marker.parent).st_ino
        ):
            raise LegacyMarkerRestoreError("marker parent changed during recovery")
        if _stopped(process_probe)!="exact-three-role-absence" or (
            _ledger_clear(ledger_root) not in ("no-native-ledger","empty-private-ledger")
        ):
            raise LegacyMarkerRestoreError("process or native owner appeared")
        if _strict_snapshot(readonly_ipfw)!=_expected_after(
            plan,len(plan["legacy_ipfw_commands"])
        ):
            raise LegacyMarkerRestoreError("previous PoC kernel changed")
        n,partial=_steps(root/REPLAY_NAME,plan)
        if partial or n!=len(plan["legacy_ipfw_commands"]):
            raise LegacyMarkerRestoreError("old Telegram IPFW redo incomplete")
        if _sha_fd(config_fd)!=(plan["previous_five"]["config"],saved["config"]["bytes"]):
            raise LegacyMarkerRestoreError("Config changed after old restore")
        if stat.S_IMODE(os.fstat(config_fd).st_mode)!=saved["config"]["mode"]:
            raise LegacyMarkerRestoreError("restored Config mode changed")
        if ready.exists() or ready.is_symlink():
            raise LegacyMarkerRestoreError("unexpected runtime recovery ready dir")
        if _fingerprint(image/"config.xml",active,source,
                        must_match_previous_modes=True)!=plan["previous_five"]["runtime"]:
            raise LegacyMarkerRestoreError("active old runtime changed")
        if _fingerprint(image/"config.xml",retired,source,
                        must_match_previous_modes=False)!=wal["candidate_runtime_sha256"]:
            raise LegacyMarkerRestoreError("retired candidate runtime changed")
        if inspect_legacy_reverse_wal(
            root,allow_ipfw_replay=True,allow_files_stage=FILES_NAME,
            allow_runtime_restore=True,allow_config_restore=True,
            allow_marker_restore=resumed,
        )!=wal or inspect_legacy_files_ready(
            root,allow_runtime_restore=True,allow_config_restore=True,
            allow_marker_restore=resumed,
        )!=image_info:
            raise LegacyMarkerRestoreError("immutable old PoC evidence changed")
        _read_intent(root,restore_record)
        _read_intent_config(root,config_expected)
        if resumed:
            _read_intent_marker(root,intent)

    gate()
    if not resumed:
        if os.path.lexists(marker) or os.path.lexists(stage):
            raise LegacyMarkerRestoreError("foreign preexisting marker/stage")
        _arm(root,intent)
        resumed=True
    gate()

    # Existing marker before a durable intent was never adopted. After intent,
    # exact target+stage identity is required to finish a cut after os.link.
    target_exists=os.path.lexists(marker)
    stage_exists=os.path.lexists(stage)
    if target_exists:
        if stage_exists:
            a=_marker_stat(marker,saved_marker,md["mode"],links=2)
            b=_marker_stat(stage,saved_marker,md["mode"],links=2)
            if (a.st_dev,a.st_ino)!=(b.st_dev,b.st_ino):
                raise LegacyMarkerRestoreError("target and pending stage have different inodes")
            gate()
            os.unlink(stage)
            _sync_dir(marker.parent)
        else:
            _marker_stat(marker,saved_marker,md["mode"],links=1)
    else:
        if not stage_exists:
            fd=os.open(stage,os.O_WRONLY|os.O_CREAT|os.O_EXCL|
                       getattr(os,"O_NOFOLLOW",0),0o600)
            try:
                os.write(fd,saved_marker)
                os.fchmod(fd,md["mode"])
                os.fsync(fd)
            finally:
                os.close(fd)
            _sync_dir(marker.parent)
        _marker_stat(stage,saved_marker,md["mode"],links=1)
        gate()
        # Hardlink no-replace guarantees we never overwrite a foreign marker.
        os.link(stage,marker,follow_symlinks=False)
        _sync_dir(marker.parent)
        _marker_stat(marker,saved_marker,md["mode"],links=2)
        gate()
        os.unlink(stage)
        _sync_dir(marker.parent)
    gate()
    _marker_stat(marker,saved_marker,md["mode"],links=1)
    return {
        "state":"legacy-marker-restored-old-processes-not-restarted",
        "marker_sha256":md["sha256"],
        "marker_mode":md["mode"],
        "config_runtime_ipfw_previously_restored":True,
        "safe_to_start":False,"safe_to_enable_voice":False,
        "whole_rollback_complete":False,"public_voice_apply":False,
    }
