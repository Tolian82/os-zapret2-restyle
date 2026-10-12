#!/usr/bin/env python3
"""Restore sealed legacy Telegram PoC Config on its ORIGINAL locked inode.

Internal only: no public service/GUI/boot/configd route and no Voice ON.
Requires completed exact old IPFW redo, two-rename old runtime restore,
stopped original process triad, absent legacy marker/native ledger owner,
unchanged immutable previous/install image and same original FD9/Config
flock. A write-once fsynced, inode-pinned intent precedes ftruncate.

A cut between ftruncate and fsync may leave a strict prefix of previous
bytes; only the same, authenticated redo and inode may authorize resuming.
There is no cleanup or five-domain restored receipt here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _read_private_file, _sync_dir
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
from voice_cutover_runtime_restore import _safe_parent, _fingerprint
from voice_cutover_config_restore import (
    _sha_fd, _pinned_regular, _write_all,
)
from voice_cutover_config_redo import _prefix_matches
from voice_native_legacy_poc_guard import _legacy_read
from voice_native_recovery_quiescence import _locked_config

CONFIG_NAME = "legacy-config-restore"
SCHEMA = 1
LIMIT = 8192
FILES = frozenset(("intent.json", "intent.sha256"))
BASE = frozenset((NAME, PLAN_NAME, WAL_NAME, REPLAY_NAME, FILES_NAME, NAME_RESTORE))


class LegacyConfigRestoreError(RuntimeError):
    pass


def _record(plan, wal, info, saved):
    return {
        "schema":SCHEMA, "phase":"old-config-write-armed-not-whole-restored",
        "restore_plan_sha256":wal["restore_plan_sha256"],
        "device":info.st_dev, "inode":info.st_ino,
        "uid":info.st_uid, "gid":info.st_gid,
        "candidate_config_sha256":wal["candidate_config_sha256"],
        "previous_config_sha256":plan["previous_five"]["config"],
        "previous_bytes":saved["config"]["bytes"],
        "previous_mode":saved["config"]["mode"],
        "safe_to_enable_voice":False,
        "whole_rollback_complete":False,
    }


def _read_intent_config(root, expected):
    directory=root/CONFIG_NAME
    _private_dir(directory)
    if set(os.listdir(directory)) != FILES:
        raise LegacyConfigRestoreError("unsealed or foreign Config redo")
    body=_read_private_file(directory/"intent.json",LIMIT)
    if _read_private_file(directory/"intent.sha256",65) != (
        _digest(body)+"\n"
    ).encode("ascii"):
        raise LegacyConfigRestoreError("Config redo checksum mismatch")
    if json.loads(body) != expected:
        raise LegacyConfigRestoreError("Config redo changed or inode differs")
    return expected


def _arm(root, expected):
    # There is intentionally no temporary rename: a partial intent must
    # block retry before any Config write, not become an innocuous omission.
    path=root/CONFIG_NAME
    os.mkdir(path,0o700)
    _sync_dir(root)
    body=(json.dumps(expected,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(body)>LIMIT:
        raise LegacyConfigRestoreError("oversized legacy Config intent")
    _write_once(path/"intent.json",body)
    _write_once(path/"intent.sha256",(_digest(body)+"\n").encode("ascii"))
    _sync_dir(path)
    return _read_intent_config(root,expected)


def restore_legacy_config(
    *, root, config_path, config_fd, config_owner, active_runtime,
    legacy_marker, ledger_root, process_probe, readonly_ipfw,
    require_lifecycle_owner,
):
    """Real same-inode Config restore, but never complete five-domain recovery."""
    if not callable(require_lifecycle_owner) or (
        type(config_fd) is not int or config_fd<0
    ):
        raise LegacyConfigRestoreError("original FD9/Config flock is required")
    root,config_path,active=Path(root),Path(config_path),Path(active_runtime)
    def held():
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        return _pinned_regular(config_path,config_fd,owner=config_owner)

    held()
    _private_dir(root)
    names=set(os.listdir(root))
    if names not in (BASE, BASE|{CONFIG_NAME}):
        raise LegacyConfigRestoreError("unexpected file in legacy recovery root")
    resumed=CONFIG_NAME in names
    plan=inspect_legacy_restore_plan(root)
    wal=inspect_legacy_reverse_wal(
        root,allow_ipfw_replay=True,allow_files_stage=FILES_NAME,
        allow_runtime_restore=True,allow_config_restore=resumed,
    )
    ready=inspect_legacy_files_ready(
        root,allow_runtime_restore=True,allow_config_restore=resumed,
    )
    if ready["previous_five"]!=plan["previous_five"]:
        raise LegacyConfigRestoreError("previous image fingerprint mismatch")
    source=root/NAME/"previous"
    image=root/FILES_NAME/"install-image"
    parent=_safe_parent(active.parent)
    rename=_intent_data(plan,wal,active,parent)
    _read_intent(root,rename)
    retired=active.with_name(rename["retired_name"])
    other=active.with_name(rename["ready_name"])
    saved=__import__("voice_cutover_backup").inspect_previous(source)
    old_mode=saved["config"]["mode"]
    old_sha=plan["previous_five"]["config"]
    old_size=saved["config"]["bytes"]
    expected=_record(plan,wal,held(),saved)
    if old_sha!=saved["config"]["sha256"]:
        raise LegacyConfigRestoreError("saved old Config does not match previous manifest")

    def guard():
        held()
        if _stopped(process_probe)!="exact-three-role-absence" or (
            _ledger_clear(ledger_root) not in ("no-native-ledger","empty-private-ledger")
        ):
            raise LegacyConfigRestoreError("process/owner drift before Config restore")
        if _legacy_read(Path(legacy_marker)) is not None:
            raise LegacyConfigRestoreError("legacy marker unexpectedly active")
        if _strict_snapshot(readonly_ipfw)!=_expected_after(
            plan,len(plan["legacy_ipfw_commands"])
        ):
            raise LegacyConfigRestoreError("legacy IPFW changed since durable replay")
        count,started=_steps(root/REPLAY_NAME,plan)
        if started or count!=len(plan["legacy_ipfw_commands"]):
            raise LegacyConfigRestoreError("legacy IPFW redo is incomplete")
        if other.exists() or other.is_symlink():
            raise LegacyConfigRestoreError("stray ready runtime beside installed old tree")
        if _fingerprint(image/"config.xml",active,source,
                        must_match_previous_modes=True)!=plan["previous_five"]["runtime"]:
            raise LegacyConfigRestoreError("previous active runtime drifted")
        if _fingerprint(image/"config.xml",retired,source,
                        must_match_previous_modes=False)!=wal["candidate_runtime_sha256"]:
            raise LegacyConfigRestoreError("retired runtime was replaced")
        if _safe_parent(active.parent).st_dev!=parent.st_dev or (
            _safe_parent(active.parent).st_ino!=parent.st_ino
        ):
            raise LegacyConfigRestoreError("runtime parent changed")
        if inspect_legacy_reverse_wal(
            root,allow_ipfw_replay=True,allow_files_stage=FILES_NAME,
            allow_runtime_restore=True,allow_config_restore=resumed,
        )!=wal or inspect_legacy_files_ready(
            root,allow_runtime_restore=True,allow_config_restore=resumed,
        )!=ready:
            raise LegacyConfigRestoreError("recovery proof changed")
        _read_intent(root,rename)

    guard()
    flags=os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)
    source_fd=os.open(image/"config.xml",flags)
    try:
        _pinned_regular(image/"config.xml",source_fd,
                        owner=(os.geteuid(),os.getegid()))
        if _sha_fd(source_fd)!=(old_sha,old_size):
            raise LegacyConfigRestoreError("install image Config tampered")
        marker=_read_intent_config(root,expected) if resumed else None
        before=_sha_fd(config_fd)
        live_info=held()
        if (live_info.st_dev,live_info.st_ino,live_info.st_uid,live_info.st_gid)!=(expected["device"],expected["inode"],expected["uid"],expected["gid"]):
            raise LegacyConfigRestoreError("live Config inode/owner drift")
        previous=(before==(old_sha,old_size) and
                  stat.S_IMODE(live_info.st_mode)==old_mode)
        if not resumed and not previous and before[0]!=wal["candidate_config_sha256"]:
            raise LegacyConfigRestoreError("foreign original Config, no old redo")
        if resumed and not previous and (
            before[0]!=wal["candidate_config_sha256"] and
            not _prefix_matches(config_fd,source_fd,old_size)
        ):
            raise LegacyConfigRestoreError("untrusted partial Config after power cut")
        if previous and not resumed:
            # Even an already-previous Config must have a durable record.
            _arm(root,expected)
            resumed=True
        if not previous:
            if not resumed:
                _arm(root,expected)
                resumed=True
            guard()
            _read_intent_config(root,expected)
            if _sha_fd(config_fd)!=before:
                raise LegacyConfigRestoreError("Config changed before truncate")
            # Never os.replace/rename Config: OPNsense PHP owns this inode.
            os.ftruncate(config_fd,0)
            os.lseek(config_fd,0,os.SEEK_SET)
            os.lseek(source_fd,0,os.SEEK_SET)
            while True:
                block=os.read(source_fd,1024*1024)
                if not block:
                    break
                _write_all(config_fd,block)
            os.fchmod(config_fd,old_mode)
            os.fsync(config_fd)
        guard()
        _read_intent_config(root,expected)
        if _sha_fd(config_fd)!=(old_sha,old_size) or (
            stat.S_IMODE(os.fstat(config_fd).st_mode)!=old_mode
        ) or _sha_fd(source_fd)!=(old_sha,old_size):
            raise LegacyConfigRestoreError("restored Config failed exact validation")
        return {
            "state":"legacy-config-restored-marker-and-processes-pending",
            "config_inode_preserved":True,
            "runtime_restored":True, "ipfw_replay_complete":True,
            "marker_restored":False,"process_restart_verified":False,
            "whole_rollback_complete":False,"safe_to_enable_voice":False,
            "public_voice_apply":False,
        }
    finally:
        os.close(source_fd)
