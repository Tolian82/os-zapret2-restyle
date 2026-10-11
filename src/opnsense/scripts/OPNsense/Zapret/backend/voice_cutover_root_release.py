#!/usr/bin/env python3
"""Post-rollback Voice reclaim phase three: release EMPTY quarantine root.

This is deliberately separate from candidate tree pruning. Only a checksum-
sealed, inode-pinned, already empty quarantine root may be removed (rmdir);
all prior Config/runtime backups, receipt, redo, five-domain journal, active
engine/supervisor, and scoped IPFW ownership stay untouched.

Write-ahead release marker is durable before rmdir and boot review can
classify either side of a crash. No automatic executor, journal finalization,
Voice ON or general recursive delete.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _sync_dir
from voice_cutover_cleanup_prepare import read_cleanup_plan
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_prune import (
    DIR, _check_inventory, _open_held, read_prune_intent,
    inspect_prune_placement,
)
from voice_cutover_reclaim import (
    expected_reclaim_intent, read_reclaim_intent,
)
from voice_cutover_recovery_receipt import read_receipt
from voice_cutover_runtime_restore import _read_redo, _safe_parent
from voice_native_recovery_quiescence import _locked_config

NAME="previous-root-release-intent.json"
MAX_BYTES=8192
_HEX=set("0123456789abcdef")


class RootReleaseError(RuntimeError):
    pass


def _checksum(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _sha(value):
    return type(value) is str and len(value)==64 and set(value)<=_HEX


def _validate(data):
    fields={
        "schema","phase","terminal_check","original_check","plan_check",
        "reclaim_check","prune_check","redo_check","candidate_sha256",
        "config_dev","config_inode","parent_dev","parent_inode",
        "root_dev","root_inode","root_uid","root_mode","held_name","check",
    }
    if not isinstance(data,dict) or set(data)!=fields or (
        type(data["schema"]) is not int or data["schema"]!=1
        or data["phase"]!="empty-root-release-intent"
    ):
        raise RootReleaseError("invalid Voice root-release marker schema")
    for key in (
        "terminal_check","original_check","plan_check","reclaim_check",
        "prune_check","redo_check","candidate_sha256","check",
    ):
        if not _sha(data[key]):
            raise RootReleaseError("invalid Voice root-release SHA identity")
    for key in (
        "config_dev","config_inode","parent_dev","parent_inode",
        "root_dev","root_inode","root_uid","root_mode",
    ):
        if type(data[key]) is not int or data[key]<0:
            raise RootReleaseError("invalid Voice root-release inode")
    if data["held_name"]!=".voice-reclaim-held-"+data["original_check"][:20]:
        raise RootReleaseError("foreign Voice root-release name")
    if data["check"]!=_checksum({k:v for k,v in data.items() if k!="check"}):
        raise RootReleaseError("Voice root-release marker checksum mismatch")
    return data


def read_root_release_intent(directory:Path):
    root=Path(directory)
    _private_dir(root)
    try:
        fd=os.open(root/NAME,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd,"rb") as inp:
        info=os.fstat(inp.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or (
            info.st_uid!=os.geteuid() or info.st_mode&0o077
            or info.st_size>MAX_BYTES
        ):
            raise RootReleaseError("untrusted Voice root-release marker")
        raw=inp.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:
        raise RootReleaseError("oversized root-release marker")
    try:
        return _validate(json.loads(raw))
    except (TypeError,ValueError,UnicodeError) as exc:
        raise RootReleaseError("corrupt root-release marker") from exc


def expected_root_release_intent(*,terminal,plan,receipt,redo,reclaim,prune,
                                 config_path,active_runtime):
    """Derive sealed expected release intent from old, unchanged evidence."""
    if terminal is None or terminal["phase"]!="rolled_back" or (
        plan is None or receipt is None or redo is None or
        reclaim is None or prune is None
    ):
        raise RootReleaseError("sealed terminal rollback and prune required")
    expected=expected_reclaim_intent(
        terminal=terminal,plan=plan,receipt=receipt,runtime_redo=redo,
        config_path=Path(config_path),active_runtime=Path(active_runtime),
    )
    if reclaim!=expected or (
        prune["reclaim_check"]!=reclaim["check"]
        or prune["terminal_check"]!=terminal["check"]
        or prune["plan_check"]!=plan["check"]
        or prune["original_check"]!=reclaim["original_check"]
        or prune["candidate_sha256"]!=reclaim["candidate_sha256"]
        or prune["held_name"]!=reclaim["quarantine_name"]
        or (prune["parent_dev"],prune["parent_inode"])!=(
            reclaim["parent_dev"],reclaim["parent_inode"]
        )
    ):
        raise RootReleaseError("foreign prior candidate reclaim/prune evidence")
    data={
        "schema":1,"phase":"empty-root-release-intent",
        "terminal_check":terminal["check"],"original_check":reclaim["original_check"],
        "plan_check":plan["check"],"reclaim_check":reclaim["check"],
        "prune_check":prune["check"],"redo_check":redo["checksum"],
        "candidate_sha256":reclaim["candidate_sha256"],
        "config_dev":reclaim["config_dev"],"config_inode":reclaim["config_inode"],
        "parent_dev":reclaim["parent_dev"],"parent_inode":reclaim["parent_inode"],
        "root_dev":prune["root_dev"],"root_inode":prune["root_inode"],
        "root_uid":prune["root_uid"],"root_mode":prune["root_mode"],
        "held_name":prune["held_name"],
    }
    return _validate({**data,"check":_checksum(data)})


def _remaining_verified(parent:Path,marker:dict,prune:dict):
    fd=_open_held(parent,prune)
    try:
        # Verify exact empty directory; if it has been repopulated after the
        # completed prune, do not treat it as an interruption to resume.
        remaining=_check_inventory(fd,prune)
        if remaining:
            raise RootReleaseError("Voice quarantine is not empty")
        info=os.fstat(fd)
        if (info.st_dev,info.st_ino,info.st_uid,stat.S_IMODE(info.st_mode))!=(
            marker["root_dev"],marker["root_inode"],
            marker["root_uid"],marker["root_mode"]
        ):
            raise RootReleaseError("Voice quarantine inode changed")
    finally:
        os.close(fd)


def inspect_root_release_placement(*,directory,parent,reclaim_record,plan,
                                   journal_record,prune_record,release_record):
    """Boot-safe read-only classification after durable root-release intent."""
    record=release_record
    if record is None:
        raise RootReleaseError("root-release intent absent")
    if record["terminal_check"]!=journal_record["check"] or (
        record["original_check"]!=reclaim_record["original_check"]
        or record["plan_check"]!=plan["check"]
        or record["reclaim_check"]!=reclaim_record["check"]
        or record["prune_check"]!=prune_record["check"]
        or record["candidate_sha256"]!=reclaim_record["candidate_sha256"]
        or record["held_name"]!=reclaim_record["quarantine_name"]
        or (record["parent_dev"],record["parent_inode"])!=(
            reclaim_record["parent_dev"],reclaim_record["parent_inode"]
        )
        or (record["root_dev"],record["root_inode"],record["root_uid"],
            record["root_mode"])!=(
            prune_record["root_dev"],prune_record["root_inode"],
            prune_record["root_uid"],prune_record["root_mode"]
        )
    ):
        raise RootReleaseError("root-release does not belong to original cutover")
    # Reopen native filesystem and old Config-inode context on every reboot.
    if (record["config_dev"],record["config_inode"])!=(
        reclaim_record["config_dev"],reclaim_record["config_inode"]
    ):
        raise RootReleaseError("root-release original Config inode changed")
    p=Path(parent)
    info=_safe_parent(p)
    if (info.st_dev,info.st_ino)!=(record["parent_dev"],record["parent_inode"]):
        raise RootReleaseError("root-release runtime parent was replaced")
    root=p/record["held_name"]
    if root.is_symlink():
        raise RootReleaseError("foreign symlink substituted for Voice quarantine")
    if root.exists():
        _remaining_verified(p,record,prune_record)
        return "candidate-root-release-armed"
    return "candidate-root-released-awaiting-finalization"


def _publish(directory,record):
    if read_root_release_intent(directory) is not None:
        raise RootReleaseError("root-release record already exists")
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(raw)>MAX_BYTES:
        raise RootReleaseError("oversized root-release intent")
    fd=os.open(Path(directory)/NAME,os.O_WRONLY|os.O_CREAT|os.O_EXCL|
               getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        with os.fdopen(fd,"wb") as stream:
            fd=-1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd>=0:os.close(fd)
    _sync_dir(Path(directory))
    if read_root_release_intent(directory)!=record:
        raise RootReleaseError("root-release write-ahead record not durable")


def _durable_rmdir(dirfd:int,held_name:str):
    os.rmdir(held_name,dir_fd=dirfd)
    os.fsync(dirfd)


def release_quarantined_root(
    *,journal,ledger,previous_backup,process_evidence,security_evidence,
    install_image,config_path,active_runtime,probe,adapter,config_fd,
    config_owner,require_lifecycle_owner,
):
    """Explicit native/private empty-root rmdir under original two locks.

    Existing partial candidate deletion is NOT recovered here. Phase two's
    inode-scoped prune must be complete and already classified by boot review.
    """
    from voice_native_boot_recovery_review import inspect_boot_recovery
    config_path,active_runtime=Path(config_path),Path(active_runtime)
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    _pinned_regular(config_path,config_fd,owner=config_owner)
    report=inspect_boot_recovery(
        journal=journal,ledger=ledger,previous_backup=previous_backup,
        process_evidence=process_evidence,security_evidence=security_evidence,
        install_image=install_image,config_path=config_path,
        active_runtime=active_runtime,probe=probe,adapter=adapter,
        config_fd=config_fd,config_owner=config_owner,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if report["state"]!="previous-rollback-sealed-needs-manual-finalization" or (
        report["phase"]!="rolled_back"
        or report["config"]!="previous" or report["runtime"]!="previous"
        or report["kernel"]!="previous" or report["processes"]!="running"
        or report["previous_receipt"]!="process-epoch-matches-not-readiness"
        or report["candidate_reclaim"] not in (
            "candidate-pruned-retained-root",
            "candidate-root-release-armed",
            "candidate-root-released-awaiting-finalization",
        )
        or report["safe_to_close_intent"] is not False
        or report["voice_on"] is not False
    ):
        raise RootReleaseError("original five-resource rollback preflight denied")
    terminal=journal.read()
    plan=read_cleanup_plan(journal.directory)
    receipt=read_receipt(journal.directory)
    redo=_read_redo(journal.directory)
    reclaim=read_reclaim_intent(journal.directory)
    prune=read_prune_intent(journal.directory)
    expected=expected_root_release_intent(
        terminal=terminal,plan=plan,receipt=receipt,redo=redo,
        reclaim=reclaim,prune=prune,config_path=config_path,
        active_runtime=active_runtime,
    )
    marker=read_root_release_intent(journal.directory)
    if marker is not None and marker!=expected:
        raise RootReleaseError("foreign root-release intent")
    if marker is None:
        if report["candidate_reclaim"]!="candidate-pruned-retained-root":
            raise RootReleaseError("cannot arm root-release without completed prune")
        _remaining_verified(active_runtime.parent,expected,prune)
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        _publish(journal.directory,expected)
    place=inspect_root_release_placement(
        directory=journal.directory,parent=active_runtime.parent,
        reclaim_record=reclaim,plan=plan,journal_record=terminal,
        prune_record=prune,release_record=expected,
    )
    if place=="candidate-root-release-armed":
        parent=_safe_parent(active_runtime.parent)
        fd=os.open(active_runtime.parent,DIR)
        try:
            fresh=os.fstat(fd)
            if (fresh.st_dev,fresh.st_ino)!=(expected["parent_dev"],expected["parent_inode"]):
                raise RootReleaseError("runtime parent changed before empty-root rmdir")
            leaf=os.stat(expected["held_name"],dir_fd=fd,follow_symlinks=False)
            if not stat.S_ISDIR(leaf.st_mode) or (
                leaf.st_dev,leaf.st_ino,leaf.st_uid,stat.S_IMODE(leaf.st_mode)
            )!=(expected["root_dev"],expected["root_inode"],
                expected["root_uid"],expected["root_mode"]):
                raise RootReleaseError("held root inode changed before rmdir")
            _remaining_verified(active_runtime.parent,expected,prune)
            require_lifecycle_owner()
            _locked_config(config_path,config_fd,config_owner)
            _durable_rmdir(fd,expected["held_name"])
        finally:
            os.close(fd)
    if inspect_root_release_placement(
        directory=journal.directory,parent=active_runtime.parent,
        reclaim_record=reclaim,plan=plan,journal_record=terminal,
        prune_record=prune,release_record=expected,
    )!="candidate-root-released-awaiting-finalization":
        raise RootReleaseError("empty Voice quarantine not durably released")
    # A retry after a crash between rmdir and parent fsync must complete
    # that durability boundary even when the directory is already absent.
    _sync_dir(active_runtime.parent)
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    if journal.read()!=terminal or read_cleanup_plan(journal.directory)!=plan or (
        read_receipt(journal.directory)!=receipt or _read_redo(journal.directory)!=redo
        or read_reclaim_intent(journal.directory)!=reclaim
        or read_prune_intent(journal.directory)!=prune
        or read_root_release_intent(journal.directory)!=expected
    ):
        raise RootReleaseError("sealed Voice rollback changed during root release")
    return {"state":"candidate-root-released-awaiting-finalization",
            "safe_to_close_intent":False,"voice_on":False}
