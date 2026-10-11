#!/usr/bin/env python3
"""Durable READ-ONLY five-resource rollback attestation receipt (write-once).

Called only INSIDE existing FD9 + the same Config inode flock, after real
rollback verifies Config, runtime, all three process roles and scoped IPFW.
The receipt is a durable *observation*, never a journal commit, deletion,
restart authorization, reboot auto-replay or voice-readiness proof.

Crash before fsync leaves a corrupt/incomplete marker and MUST block future
finalization. Reboot with changed PID/start also requires a NEW separately
designed epoch protocol; this record is never silently overwritten.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir,_sync_dir,bound_resource_fingerprints
from voice_cutover_journal import RUNTIME_BOUND_SCHEMA, RUNTIME_FIELD, SECURITY_FIELD
from voice_cutover_config_restore import _pinned_regular
from voice_native_recovery_quiescence import _locked_config, EXPECTED_SCRIPTS, PIDFILES
from voice_native_file_observer import observe_live_files
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_firewall_ledger import fingerprint,canonical_manifest
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_ipfw_adapter import FreeBSDIPFWAdapter

NAME="previous-rollback-receipt.json"
MAX_RECEIPT=8192
ROLES=("engine","daemon","monitor")
_HEX=set("0123456789abcdef")


class RecoveryReceiptError(RuntimeError):
    pass


def _sha(value):
    return type(value) is str and len(value)==64 and set(value)<=_HEX


def _hash(value:dict)->str:
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _validate(value:dict)->dict:
    fields={"schema","phase","whole_check","previous","candidate_runtime_sha256",
            "security_policy_sha256","config_dev","config_inode","instances","check"}
    if not isinstance(value,dict) or set(value)!=fields or (
        type(value.get("schema")) is not int or value["schema"]!=1
        or value.get("phase")!="observed-only"
    ):
        raise RecoveryReceiptError("invalid Voice previous receipt shape")
    if any(not _sha(value.get(k)) for k in (
        "whole_check","candidate_runtime_sha256","security_policy_sha256","check",
    )):
        raise RecoveryReceiptError("invalid Voice recovery receipt fingerprint")
    if not isinstance(value["previous"],dict) or len(value["previous"])!=5 or (
        set(value["previous"])!={"config","runtime","engine","supervisor","firewall"}
    ) or any(not _sha(v) for v in value["previous"].values()):
        raise RecoveryReceiptError("invalid prior five-resource fingerprints")
    if any(type(value.get(k)) is not int or value[k]<0
           for k in ("config_dev","config_inode")):
        raise RecoveryReceiptError("invalid Config inode identity")
    instances=value["instances"]
    if not isinstance(instances,dict) or set(instances)!=set(ROLES):
        raise RecoveryReceiptError("missing restored process identities")
    for role in ROLES:
        instance=instances[role]
        if not isinstance(instance,dict) or set(instance)!={"pid","start_ns"} or (
            type(instance["pid"]) is not int or not 1<instance["pid"]<=4194304
            or type(instance["start_ns"]) is not int or instance["start_ns"]<=0
        ):
            raise RecoveryReceiptError("invalid restarted Voice process identity")
    if len({instances[k]["pid"] for k in ROLES})!=3:
        raise RecoveryReceiptError("duplicate restored Voice process PID")
    if _hash({k:v for k,v in value.items() if k!="check"})!=value["check"]:
        raise RecoveryReceiptError("corrupt Voice previous receipt checksum")
    return value


def read_receipt(directory:Path)->dict|None:
    directory=Path(directory)
    _private_dir(directory)
    try:
        fd=os.open(directory/NAME,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd,"rb") as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or (
            info.st_uid!=os.geteuid() or info.st_mode&0o077 or info.st_size>MAX_RECEIPT
        ):
            raise RecoveryReceiptError("unsafe Voice previous receipt inode")
        raw=f.read(MAX_RECEIPT+1)
    if len(raw)>MAX_RECEIPT:
        raise RecoveryReceiptError("oversized Voice previous receipt")
    try:
        return _validate(json.loads(raw))
    except (ValueError,UnicodeError,TypeError) as exc:
        raise RecoveryReceiptError("corrupt Voice previous receipt") from exc


def seal_previous_receipt(
    *,journal,ledger,previous_backup:Path,config_path:Path,active_runtime:Path,
    config_fd:int,config_owner:tuple[int,int],probe:FreeBSDVoiceProcessProbe,
    adapter:FreeBSDIPFWAdapter,integrity_report:dict,require_lifecycle_owner,
)->dict:
    """Write fsync'd receipt BEFORE releasing same Config lock and FD9.

    The kernel image/credentials/argv report MUST already have been verified
    in this SAME lock epoch by the independent native restart attestor.
    Recheck all five live resources, journals and process instance numbers.
    """
    if not callable(require_lifecycle_owner) or not isinstance(probe,FreeBSDVoiceProcessProbe) or (
        probe.expected!=EXPECTED_SCRIPTS or probe.pidfiles!=PIDFILES
        or Path(probe.previous_backup)!=Path(previous_backup)
        or not isinstance(adapter,FreeBSDIPFWAdapter)
        or adapter.allow_mutations is not False
        or (adapter.rule_base,adapter.rule_max)!=(19000,19010)
    ):
        raise RecoveryReceiptError("untrusted native five-resource witnesses")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    original=journal.read()
    if original is None or original["schema"]!=RUNTIME_BOUND_SCHEMA or (
        original["phase"]!="mutating"
    ):
        raise RecoveryReceiptError("no schema-4 MUTATING five-resource intent")
    previous=bound_resource_fingerprints(previous_backup,original["previous"])
    if observe_live_files(
        config_path,active_runtime,previous_backup=previous_backup
    )!=previous:
        raise RecoveryReceiptError("previous Config/runtime not restored")
    if not isinstance(integrity_report,dict) or (
        integrity_report.get("state")!="previous-restart-integrity-observed"
        or integrity_report.get("whole_intent_phase")!="mutating"
        or integrity_report.get("safe_to_finish_intent") is not False
        or integrity_report.get("safe_to_enable_voice") is not False
        or integrity_report.get("security_policy_sha256")!=original["candidate"][SECURITY_FIELD]
    ):
        raise RecoveryReceiptError("native kernel image/argv attest missing")
    instances=integrity_report.get("instances")
    if not isinstance(instances,dict) or set(instances)!=set(ROLES):
        raise RecoveryReceiptError("native restart instances not three roles")
    first=probe.probe()
    second=probe.probe()
    if first!=second or first["engine"]["state"]!="running" or (
        first["supervisor"]["state"]!="running"
    ):
        raise RecoveryReceiptError("unstable previous one-engine/supervisor topology")
    rows={
        "engine":first["engine"]["process"],
        "daemon":first["supervisor"]["daemon"],
        "monitor":first["supervisor"]["monitor"],
    }
    if any(instances[role]!={"pid":rows[role]["pid"],"start_ns":rows[role]["start_ns"]}
           for role in ROLES):
        raise RecoveryReceiptError("kernel argv/image and process PID/start disagree")
    owned=ledger.owned()
    if owned is None or ledger.pending() is not None or (
        fingerprint(canonical_manifest(owned))!=original["previous"]["firewall"]
    ) or observe_owned_ipfw(ledger,adapter)!=original["previous"]["firewall"]:
        raise RecoveryReceiptError("old IPFW owner not independently restored")
    info=_pinned_regular(Path(config_path),config_fd,owner=config_owner)
    fields={
        "schema":1,"phase":"observed-only","whole_check":original["check"],
        "previous":dict(original["previous"]),
        "candidate_runtime_sha256":original["candidate"][RUNTIME_FIELD],
        "security_policy_sha256":original["candidate"][SECURITY_FIELD],
        "config_dev":info.st_dev,"config_inode":info.st_ino,
        "instances":instances,
    }
    expected={**fields,"check":_hash(fields)}
    _validate(expected)
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    if journal.read()!=original or ledger.pending() is not None or (
        probe.probe()!=first or
        observe_live_files(config_path,active_runtime,previous_backup=previous_backup)!=previous
    ):
        raise RecoveryReceiptError("five resource evidence drifted before seal")
    existing=read_receipt(journal.directory)
    if existing is not None:
        if existing!=expected:
            raise RecoveryReceiptError("foreign or stale previous rollback receipt")
        return {"state":"previous-receipt-already-sealed","can_finish_intent":False}
    raw=(json.dumps(expected,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(raw)>MAX_RECEIPT:
        raise RecoveryReceiptError("oversized native recovery receipt")
    fd=os.open(journal.directory/NAME,os.O_WRONLY|os.O_CREAT|os.O_EXCL|
               getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        with os.fdopen(fd,"wb") as f:
            fd=-1
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    finally:
        if fd>=0:os.close(fd)
    _sync_dir(journal.directory)
    if read_receipt(journal.directory)!=expected:
        raise RecoveryReceiptError("previous Voice receipt not durably verified")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    if journal.read()!=original:
        raise RecoveryReceiptError("whole Voice intent changed after receipt")
    return {"state":"previous-receipt-sealed","can_finish_intent":False}
