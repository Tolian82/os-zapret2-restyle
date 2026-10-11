#!/usr/bin/env python3
"""Native Voice rollback phase four: durable NON-CLOSING finalization receipt.

No deletion, no whole-intent transition, no boot replay, no Voice ON.
The write-once receipt follows a fully durable quarantine -> prune -> rmdir
pipeline and cross-seals all previous five-resource evidence and original
Config/runtime inode. Only a native owner with FD9 and original Config flock
may create this receipt; every startup can inspect it read-only after restart.
Actual intent closure still needs a SEPARATE, owner-live FreeBSD acceptance.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _sync_dir
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_config_redo import ConfigRestoreRedo
from voice_cutover_cleanup_prepare import read_cleanup_plan
from voice_cutover_journal import mutating_predecessor, RUNTIME_FIELD
from voice_cutover_prune import read_prune_intent
from voice_cutover_reclaim import read_reclaim_intent
from voice_cutover_recovery_receipt import read_receipt
from voice_cutover_root_release import (
    read_root_release_intent, expected_root_release_intent,
    inspect_root_release_placement,
)
from voice_cutover_runtime_restore import _read_redo
from voice_native_file_observer import observe_live_files
from voice_native_recovery_quiescence import _locked_config
from voice_firewall_ledger import fingerprint, canonical_manifest
from voice_native_ipfw_ownership import observe_owned_ipfw

NAME="previous-finalization-proof.json"
MAX_BYTES=8192
_HEX=frozenset("0123456789abcdef")


class FinalizationError(RuntimeError):
    pass


def _sha(value):
    return type(value) is str and len(value)==64 and set(value)<=_HEX


def _checksum(record):
    return hashlib.sha256(json.dumps(
        record,sort_keys=True,separators=(",",":"),ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _validate(data):
    names={
        "schema","state","terminal_check","original_check",
        "receipt_check","cleanup_check","config_redo_check",
        "runtime_redo_check","reclaim_check","prune_check",
        "root_release_check","candidate_runtime_sha256",
        "config_dev","config_inode","runtime_parent_dev","runtime_parent_inode",
        "previous","instances","check",
    }
    if not isinstance(data,dict) or set(data)!=names or (
        type(data["schema"]) is not int or data["schema"]!=1
        or data["state"]!="sealed-awaiting-owner-acceptance"
    ):
        raise FinalizationError("invalid Voice finalization schema")
    for key in (
        "terminal_check","original_check","receipt_check","cleanup_check",
        "runtime_redo_check","reclaim_check","prune_check",
        "root_release_check","candidate_runtime_sha256","check",
    ):
        if not _sha(data[key]):
            raise FinalizationError("invalid Voice finalization SHA")
    if data["config_redo_check"] is not None and not _sha(data["config_redo_check"]):
        raise FinalizationError("invalid Voice Config redo identity")
    for key in ("config_dev","config_inode","runtime_parent_dev","runtime_parent_inode"):
        if type(data[key]) is not int or data[key]<0:
            raise FinalizationError("invalid finalization inode")
    if not isinstance(data["previous"],dict) or set(data["previous"])!={
        "config","runtime","engine","supervisor","firewall"
    } or not all(_sha(x) for x in data["previous"].values()):
        raise FinalizationError("invalid previous five-resource identity")
    if not isinstance(data["instances"],dict) or set(data["instances"])!={
        "engine","daemon","monitor"
    }:
        raise FinalizationError("invalid previous process instance map")
    for row in data["instances"].values():
        if not isinstance(row,dict) or set(row)!={"pid","start_ns"} or (
            type(row["pid"]) is not int or row["pid"]<2
            or type(row["start_ns"]) is not int or row["start_ns"]<=0
        ):
            raise FinalizationError("invalid previous process instance")
    if _checksum({k:v for k,v in data.items() if k!="check"})!=data["check"]:
        raise FinalizationError("Voice finalization checksum mismatch")
    return data


def read_finalization_proof(directory:Path):
    root=Path(directory)
    _private_dir(root)
    try:
        fd=os.open(root/NAME,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd,"rb") as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or (
            info.st_uid!=os.geteuid() or info.st_mode&0o077
            or info.st_size>MAX_BYTES
        ):
            raise FinalizationError("untrusted finalization proof file")
        raw=stream.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:
        raise FinalizationError("oversized finalization proof")
    try:
        return _validate(json.loads(raw))
    except (TypeError,ValueError,UnicodeError) as exc:
        raise FinalizationError("corrupt finalization proof") from exc


def expected_finalization_proof(*,journal,config_path:Path,active_runtime:Path):
    """Deterministic SHA-bound predecessor proof without process/readiness claims."""
    terminal=journal.read()
    if terminal is None or terminal["phase"]!="rolled_back":
        raise FinalizationError("no sealed whole-system rollback")
    prior=mutating_predecessor(terminal)
    receipt=read_receipt(journal.directory)
    plan=read_cleanup_plan(journal.directory)
    config_redo=ConfigRestoreRedo(journal.directory).read()
    runtime_redo=_read_redo(journal.directory)
    reclaim=read_reclaim_intent(journal.directory)
    prune=read_prune_intent(journal.directory)
    release=read_root_release_intent(journal.directory)
    if any(x is None for x in (
        receipt,plan,runtime_redo,reclaim,prune,release,
    )):
        raise FinalizationError("complete durable rollback cleanup chain required")
    expected_release=expected_root_release_intent(
        terminal=terminal,plan=plan,receipt=receipt,redo=runtime_redo,
        reclaim=reclaim,prune=prune,config_path=Path(config_path),
        active_runtime=Path(active_runtime),
    )
    if release!=expected_release or (
        inspect_root_release_placement(
            directory=journal.directory,parent=Path(active_runtime).parent,
            reclaim_record=reclaim,plan=plan,journal_record=terminal,
            prune_record=prune,release_record=release,
        )!="candidate-root-released-awaiting-finalization"
    ):
        raise FinalizationError("old candidate quarantine is not fully released")
    if (
        plan["whole_check"]!=prior["check"]
        or receipt["whole_check"]!=prior["check"]
        or plan["receipt_check"]!=receipt["check"]
        or plan["previous"]!=prior["previous"]
        or receipt["previous"]!=prior["previous"]
        or plan["instances"]!=receipt["instances"]
        or plan["candidate_runtime_sha256"]!=prior["candidate"][RUNTIME_FIELD]
        or receipt["candidate_runtime_sha256"]!=prior["candidate"][RUNTIME_FIELD]
        or plan["runtime_redo_check"]!=runtime_redo["checksum"]
        or plan["config_redo_check"]!=(
            None if config_redo is None else config_redo["checksum"]
        )
        or (plan["config_dev"],plan["config_inode"])!=(
            receipt["config_dev"],receipt["config_inode"]
        )
        or runtime_redo["cutover_check"]!=prior["check"]
        or runtime_redo["candidate_sha256"]!=prior["candidate"][RUNTIME_FIELD]
        or runtime_redo["previous_sha256"]!=prior["previous"]["runtime"]
    ):
        raise FinalizationError("finalization does not belong to previous whole intent")
    info=os.lstat(config_path)
    parent=os.lstat(Path(active_runtime).parent)
    if (
        (info.st_dev,info.st_ino)!=(plan["config_dev"],plan["config_inode"])
        or (parent.st_dev,parent.st_ino)!=(
            release["parent_dev"],release["parent_inode"]
        )
    ):
        raise FinalizationError("original Config/runtime parent inode changed")
    fields={
        "schema":1,"state":"sealed-awaiting-owner-acceptance",
        "terminal_check":terminal["check"],"original_check":prior["check"],
        "receipt_check":receipt["check"],"cleanup_check":plan["check"],
        "config_redo_check":None if config_redo is None else config_redo["checksum"],
        "runtime_redo_check":runtime_redo["checksum"],
        "reclaim_check":reclaim["check"],"prune_check":prune["check"],
        "root_release_check":release["check"],
        "candidate_runtime_sha256":prior["candidate"][RUNTIME_FIELD],
        "config_dev":info.st_dev,"config_inode":info.st_ino,
        "runtime_parent_dev":parent.st_dev,"runtime_parent_inode":parent.st_ino,
        "previous":dict(prior["previous"]),
        "instances":dict(receipt["instances"]),
    }
    return _validate({**fields,"check":_checksum(fields)})


def inspect_finalization_proof(*,journal,config_path,active_runtime):
    """Read-only cold-boot validation; always retains whole-intent start gate."""
    marker=read_finalization_proof(journal.directory)
    if marker is None:
        return "absent"
    if marker!=expected_finalization_proof(
        journal=journal,config_path=config_path,active_runtime=active_runtime,
    ):
        raise FinalizationError("foreign or stale Voice finalization proof")
    return "sealed-awaiting-owner-acceptance"


def _publish(directory,record):
    if read_finalization_proof(directory) is not None:
        raise FinalizationError("finalization proof is write-once")
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(raw)>MAX_BYTES:
        raise FinalizationError("finalization proof exceeds maximum size")
    fd=os.open(Path(directory)/NAME,os.O_WRONLY|os.O_CREAT|os.O_EXCL|
               getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        with os.fdopen(fd,"wb") as writer:
            fd=-1
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
    finally:
        if fd>=0:os.close(fd)
    _sync_dir(Path(directory))
    if read_finalization_proof(directory)!=record:
        raise FinalizationError("finalization proof not durably readable")


def seal_finalization_proof(
    *,journal,ledger,previous_backup,process_evidence,security_evidence,
    install_image,config_path,active_runtime,probe,adapter,config_fd,
    config_owner,require_lifecycle_owner,
):
    """Explicit native owner; require live kernel/old process, retain all data."""
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
        report["phase"]!="rolled_back" or report["config"]!="previous"
        or report["runtime"]!="previous" or report["kernel"]!="previous"
        or report["processes"]!="running"
        or report["previous_receipt"]!="process-epoch-matches-not-readiness"
        or report["candidate_reclaim"]!="candidate-root-released-awaiting-finalization"
        or report["safe_to_close_intent"] is not False
        or report["voice_on"] is not False
    ):
        raise FinalizationError("five-resource original-state attestation required")
    expected=expected_finalization_proof(
        journal=journal,config_path=config_path,active_runtime=active_runtime,
    )
    existing=read_finalization_proof(journal.directory)
    if existing is not None and existing!=expected:
        raise FinalizationError("foreign durable finalization proof")
    previous=journal.read()
    owner=ledger.owned()
    if owner is None or ledger.pending() is not None or (
        fingerprint(canonical_manifest(owner))!=previous["previous"]["firewall"]
        or observe_owned_ipfw(ledger,adapter)!=previous["previous"]["firewall"]
    ):
        raise FinalizationError("original IPFW ownership not observed")
    expected_files={
        "config":previous["previous"]["config"],
        "runtime":previous["previous"]["runtime"],
    }
    observed=observe_live_files(config_path,active_runtime,previous_backup=previous_backup)
    if observed!=expected_files:
        raise FinalizationError("original previous Config/runtime bytes not intact")
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    if journal.read()!=previous or ledger.owned()!=owner or ledger.pending() is not None:
        raise FinalizationError("whole rollback changed before finalization seal")
    if expected_finalization_proof(
        journal=journal,config_path=config_path,active_runtime=active_runtime,
    )!=expected:
        raise FinalizationError("cleanup predecessor changed before finalization")
    if existing is None:
        _publish(journal.directory,expected)
    if inspect_finalization_proof(
        journal=journal,config_path=config_path,active_runtime=active_runtime,
    )!="sealed-awaiting-owner-acceptance":
        raise FinalizationError("finalization proof re-open failed")
    return {"state":"finalization-sealed-awaiting-owner-acceptance",
            "safe_to_close_intent":False,"safe_to_start":False,
            "voice_on":False}
