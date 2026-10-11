#!/usr/bin/env python3
"""Durable, NON-DESTRUCTIVE postrollback cleanup PREPARE for Voice schema-4.

Never remove Config/runtime, retired candidate, Config/runtime redo, receipt,
whole journal or owned IPFW. A once-only, fsync'd cleanup plan binds exactly
one MUTATING cutover and its independently observed previous five-resource
state, kernel argv attestation, Config inode, retired candidate SHA and redo.

The caller MUST keep original native lifecycle FD9 and same Config flock
acquired by the five-resource restorer. This is a staging primitive, not a
boot hook, completion, Voice ON or permission to reclaim any path. Reboot
with stale PID/start cannot use the old receipt without a NEW attestation
protocol.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _sync_dir, bound_resource_fingerprints
from voice_cutover_journal import RUNTIME_BOUND_SCHEMA, RUNTIME_FIELD, SECURITY_FIELD
from voice_cutover_recovery_receipt import read_receipt, ROLES
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_config_redo import ConfigRestoreRedo
from voice_cutover_runtime_restore import _read_redo
from voice_native_file_observer import observe_live_files
from voice_native_recovery_quiescence import (
    EXPECTED_SCRIPTS, PIDFILES, _locked_config,
)
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_firewall_ledger import canonical_manifest, fingerprint

NAME="previous-cleanup-plan.json"
MAX_PLAN=8192


class CleanupPrepareError(RuntimeError):
    pass


def _checksum(obj:dict)->str:
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _is_sha(value):
    return type(value) is str and len(value)==64 and all(
        ch in "0123456789abcdef" for ch in value
    )


def _validate(data:dict)->dict:
    names={
        "schema","phase","whole_check","receipt_check","previous",
        "candidate_runtime_sha256","config_dev","config_inode",
        "config_redo_check","runtime_redo_check","retired_name",
        "retired_sha256","instances","check",
    }
    if not isinstance(data,dict) or set(data)!=names or (
        type(data["schema"]) is not int or data["schema"]!=1
        or data["phase"]!="prepared-only"
    ):
        raise CleanupPrepareError("invalid native Voice cleanup plan schema")
    for k in ("whole_check","receipt_check","candidate_runtime_sha256","check"):
        if not _is_sha(data[k]):
            raise CleanupPrepareError("bad cleanup plan fingerprint")
    if not isinstance(data["previous"],dict) or set(data["previous"])!={
        "config","runtime","engine","supervisor","firewall",
    } or any(not _is_sha(v) for v in data["previous"].values()):
        raise CleanupPrepareError("invalid saved five-resource identity")
    for k in ("config_redo_check","runtime_redo_check","retired_sha256"):
        if data[k] is not None and not _is_sha(data[k]):
            raise CleanupPrepareError("invalid optional cleanup fingerprint")
    if type(data["config_dev"]) is not int or type(data["config_inode"]) is not int or (
        data["config_dev"]<0 or data["config_inode"]<0
    ):
        raise CleanupPrepareError("invalid original Config inode")
    if not isinstance(data["instances"],dict) or set(data["instances"])!=set(ROLES):
        raise CleanupPrepareError("missing native previous process identities")
    for row in data["instances"].values():
        if not isinstance(row,dict) or set(row)!={"pid","start_ns"} or (
            type(row["pid"]) is not int or row["pid"]<2
            or type(row["start_ns"]) is not int or row["start_ns"]<=0
        ):
            raise CleanupPrepareError("unsafe process instance in cleanup plan")
    if data["retired_name"] is not None and (
        not isinstance(data["retired_name"],str)
        or not data["retired_name"].startswith(".voice-restore-retired-")
        or "/" in data["retired_name"] or ".." in data["retired_name"]
    ):
        raise CleanupPrepareError("unsafe candidate retirement path")
    if (data["retired_name"] is None)!=(data["retired_sha256"] is None):
        raise CleanupPrepareError("unpaired retired runtime in cleanup plan")
    if data["retired_name"] is not None and data["runtime_redo_check"] is None:
        raise CleanupPrepareError("retired runtime requires durable runtime redo")
    if _checksum({k:v for k,v in data.items() if k!="check"})!=data["check"]:
        raise CleanupPrepareError("Voice cleanup plan checksum mismatch")
    return data


def read_cleanup_plan(directory:Path)->dict|None:
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
            or info.st_size>MAX_PLAN
        ):
            raise CleanupPrepareError("untrusted cleanup plan file")
        raw=stream.read(MAX_PLAN+1)
    if len(raw)>MAX_PLAN:
        raise CleanupPrepareError("oversized cleanup plan")
    try:
        return _validate(json.loads(raw))
    except (TypeError,ValueError,UnicodeError) as exc:
        raise CleanupPrepareError("corrupted cleanup plan") from exc


def prepare_previous_cleanup(
    *,journal,ledger,previous_backup:Path,install_image:Path,
    config_path:Path,active_runtime:Path,config_fd:int,
    config_owner:tuple[int,int],probe:FreeBSDVoiceProcessProbe,
    adapter:FreeBSDIPFWAdapter,integrity_report:dict,
    require_lifecycle_owner,
)->dict:
    """Persist crash-safe plan under BOTH original locks; NEVER delete bytes."""
    if not callable(require_lifecycle_owner) or (
        not isinstance(probe,FreeBSDVoiceProcessProbe)
        or probe.expected!=EXPECTED_SCRIPTS or probe.pidfiles!=PIDFILES
        or Path(probe.previous_backup)!=Path(previous_backup)
        or not isinstance(adapter,FreeBSDIPFWAdapter)
        or adapter.allow_mutations is not False
        or (adapter.rule_base,adapter.rule_max)!=(19000,19010)
    ):
        raise CleanupPrepareError("untrusted kernel or lifecycle witness")
    config_path,active_runtime=Path(config_path),Path(active_runtime)
    previous_backup,install_image=Path(previous_backup),Path(install_image)
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    whole=journal.read()
    if whole is None or whole["schema"]!=RUNTIME_BOUND_SCHEMA or (
        whole["phase"]!="mutating"
    ):
        raise CleanupPrepareError("no unfinished schema-4 whole cutover")
    receipt=read_receipt(journal.directory)
    if receipt is None or (
        receipt["whole_check"]!=whole["check"]
        or receipt["previous"]!=whole["previous"]
        or receipt["candidate_runtime_sha256"]!=whole["candidate"][RUNTIME_FIELD]
        or receipt["security_policy_sha256"]!=whole["candidate"][SECURITY_FIELD]
    ):
        raise CleanupPrepareError("durable previous rollback receipt missing/foreign")
    owner=_pinned_regular(config_path,config_fd,owner=config_owner)
    if (owner.st_dev,owner.st_ino)!=(
        receipt["config_dev"],receipt["config_inode"]
    ):
        raise CleanupPrepareError("previous Config inode differs from receipt")
    old=bound_resource_fingerprints(previous_backup,whole["previous"])
    for cfg,tree in (
        (config_path,active_runtime),
        (install_image/"config.xml",install_image/"runtime"),
    ):
        if observe_live_files(
            cfg,tree,previous_backup=previous_backup
        )!=old:
            raise CleanupPrepareError("previous Config/runtime image not preserved")
    if not isinstance(integrity_report,dict) or (
        integrity_report.get("state")!="previous-restart-integrity-observed"
        or integrity_report.get("whole_intent_phase")!="mutating"
        or integrity_report.get("safe_to_enable_voice") is not False
        or integrity_report.get("safe_to_finish_intent") is not False
        or integrity_report.get("security_policy_sha256")!=whole["candidate"][SECURITY_FIELD]
        or integrity_report.get("instances")!=receipt["instances"]
    ):
        raise CleanupPrepareError("fresh native kernel argv/image attestation required")
    a,b=probe.probe(),probe.probe()
    if a!=b or a["engine"]["state"]!="running" or (
        a["supervisor"]["state"]!="running"
    ):
        raise CleanupPrepareError("unstable previous engine/supervisor topology")
    rows={
        "engine":a["engine"]["process"],
        "daemon":a["supervisor"]["daemon"],
        "monitor":a["supervisor"]["monitor"],
    }
    for role in ROLES:
        if receipt["instances"][role]!={
            "pid":rows[role]["pid"],"start_ns":rows[role]["start_ns"],
        } or rows[role]["executable"]!=EXPECTED_SCRIPTS[role]:
            raise CleanupPrepareError("stale previous process restart epoch")
    owned=ledger.owned()
    if ledger.pending() is not None or owned is None or (
        fingerprint(canonical_manifest(owned))!=old["firewall"]
        or observe_owned_ipfw(ledger,adapter)!=old["firewall"]
    ):
        raise CleanupPrepareError("foreign or unfinished previous IPFW state")
    config_redo=ConfigRestoreRedo(journal.directory).read()
    runtime_redo=_read_redo(journal.directory)
    if config_redo is not None and (
        config_redo["cutover_check"]!=whole["check"]
        or config_redo["previous_sha256"]!=old["config"]
        or config_redo["before_sha256"]!=whole["candidate"]["saved_xml_sha256"]
        or (config_redo["device"],config_redo["inode"])!=(
            receipt["config_dev"],receipt["config_inode"]
        )
    ):
        raise CleanupPrepareError("foreign Config redo")
    if runtime_redo is not None and (
        runtime_redo["cutover_check"]!=whole["check"]
        or runtime_redo["candidate_sha256"]!=whole["candidate"][RUNTIME_FIELD]
        or runtime_redo["previous_sha256"]!=old["runtime"]
        or runtime_redo["active_name"]!=active_runtime.name
        or (runtime_redo["parent_dev"],runtime_redo["parent_ino"])!=(
            active_runtime.parent.stat().st_dev,active_runtime.parent.stat().st_ino
        )
    ):
        raise CleanupPrepareError("foreign runtime redo")
    retired_name=None
    retired_sha=None
    if runtime_redo is not None:
        suffix=whole["check"][:20]
        if (runtime_redo["retired_name"]!=".voice-restore-retired-"+suffix
            or runtime_redo["ready_name"]!=".voice-restore-ready-"+suffix):
            raise CleanupPrepareError("runtime redo points to foreign candidate path")
        retired=active_runtime.with_name(runtime_redo["retired_name"])
        if retired.exists() or retired.is_symlink():
            if retired.is_symlink() or observe_live_files(
                install_image/"config.xml",retired
            )["runtime"]!=whole["candidate"][RUNTIME_FIELD]:
                raise CleanupPrepareError("foreign retired Voice candidate")
            retired_name=retired.name
            retired_sha=whole["candidate"][RUNTIME_FIELD]
        elif (active_runtime.with_name(runtime_redo["ready_name"]).exists()
              or active_runtime.with_name(runtime_redo["ready_name"]).is_symlink()):
            raise CleanupPrepareError("unrecovered runtime staging path")
        else:
            # A redo without its expected retired candidate is not a
            # completed rollback. The next cleanup executor must not erase
            # a journal for unknown missing candidate bytes.
            raise CleanupPrepareError("runtime redo has missing retired candidate")
    fields={
        "schema":1,"phase":"prepared-only","whole_check":whole["check"],
        "receipt_check":receipt["check"],
        "previous":dict(old),
        "candidate_runtime_sha256":whole["candidate"][RUNTIME_FIELD],
        "config_dev":owner.st_dev,"config_inode":owner.st_ino,
        "config_redo_check":None if config_redo is None else config_redo["checksum"],
        "runtime_redo_check":None if runtime_redo is None else runtime_redo["checksum"],
        "retired_name":retired_name,"retired_sha256":retired_sha,
        "instances":dict(receipt["instances"]),
    }
    plan={**fields,"check":_checksum(fields)}
    _validate(plan)
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    if journal.read()!=whole or read_receipt(journal.directory)!=receipt or (
        ledger.owned()!=owned or ledger.pending() is not None
        or probe.probe()!=a
        or ConfigRestoreRedo(journal.directory).read()!=config_redo
        or _read_redo(journal.directory)!=runtime_redo
        or observe_live_files(
            config_path,active_runtime,previous_backup=previous_backup
        )!=old
    ):
        raise CleanupPrepareError("previous five-resource evidence changed before plan")
    existing=read_cleanup_plan(journal.directory)
    if existing is not None:
        if existing!=plan:
            raise CleanupPrepareError("foreign or stale previous cleanup plan")
        return {"state":"previous-cleanup-already-prepared",
                "safe_to_finish_intent":False,"safe_to_enable_voice":False}
    raw=(json.dumps(plan,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(raw)>MAX_PLAN:
        raise CleanupPrepareError("oversized previous cleanup plan")
    fd=os.open(journal.directory/NAME,os.O_WRONLY|os.O_CREAT|os.O_EXCL|
               getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        with os.fdopen(fd,"wb") as stream:
            fd=-1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd>=0:os.close(fd)
    _sync_dir(journal.directory)
    if read_cleanup_plan(journal.directory)!=plan:
        raise CleanupPrepareError("previous cleanup plan not durably readable")
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    if journal.read()!=whole or read_receipt(journal.directory)!=receipt:
        raise CleanupPrepareError("whole cutover changed after cleanup prepare")
    return {"state":"previous-cleanup-prepared-only",
            "safe_to_finish_intent":False,"safe_to_enable_voice":False}
