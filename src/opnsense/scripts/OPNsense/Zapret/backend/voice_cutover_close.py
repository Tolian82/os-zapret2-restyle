#!/usr/bin/env python3
"""Voice whole rollback archive transition, crash resumable, always start-blocked.

The terminal intent.json is NEVER unlinked: after fsynced write-ahead closure
intent it is renamed atomically into immutable previous-archived-intent.json
inside the SAME private directory. Production legacy start guard must block
BOTH sides of that rename; archiving NEVER grants Voice ON or boot replay.

Only a native FD9 + original Config flock owner, with exact old five-resource
process/kernel epoch and finalization proof, may request this transition.
All original rollback/redo/finalization artifacts and kernel IPFW are retained.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _sync_dir
from voice_cutover_journal import validate_record, mutating_predecessor
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_finalization import (
    read_finalization_proof, expected_finalization_proof,
)
from voice_native_recovery_quiescence import _locked_config

NAME="previous-close-intent.json"
ARCHIVE="previous-archived-intent.json"
MAX_BYTES=8192
HEX=frozenset("0123456789abcdef")


class CloseError(RuntimeError):
    pass


def _sha(v):
    return type(v) is str and len(v)==64 and set(v)<=HEX


def _hash(fields):
    return hashlib.sha256(json.dumps(
        fields,sort_keys=True,separators=(",",":"),ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _validate(data):
    fields={"schema","phase","terminal_check","original_check",
            "finalization_check","config_dev","config_inode",
            "journal_dev","journal_inode","archive_name","check"}
    if not isinstance(data,dict) or set(data)!=fields or (
        type(data["schema"]) is not int or data["schema"]!=1
        or data["phase"]!="archive-intent"
        or data["archive_name"]!=ARCHIVE
    ):
        raise CloseError("invalid Voice whole-closure journal")
    for field in ("terminal_check","original_check","finalization_check","check"):
        if not _sha(data[field]):
            raise CloseError("invalid closure journal fingerprint")
    for field in ("config_dev","config_inode","journal_dev","journal_inode"):
        if type(data[field]) is not int or data[field]<0:
            raise CloseError("invalid original closure inode")
    if data["check"]!=_hash({k:v for k,v in data.items() if k!="check"}):
        raise CloseError("whole-closure journal checksum mismatch")
    return data


def _read_private_file(directory, name, *, max_bytes):
    root=Path(directory)
    _private_dir(root)
    try:
        fd=os.open(root/name,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    except FileNotFoundError:
        return None,None
    with os.fdopen(fd,"rb") as src:
        info=os.fstat(src.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or (
            info.st_uid!=os.geteuid() or info.st_mode&0o077
            or info.st_size>max_bytes
        ):
            raise CloseError("untrusted Voice closure/archive file")
        raw=src.read(max_bytes+1)
    if len(raw)>max_bytes:
        raise CloseError("oversized Voice closure/archive file")
    try:
        return json.loads(raw),info
    except (TypeError,ValueError,UnicodeError) as exc:
        raise CloseError("corrupted Voice closure/archive content") from exc


def read_close_intent(directory):
    record,_=_read_private_file(directory,NAME,max_bytes=MAX_BYTES)
    return None if record is None else _validate(record)


def _archived_record(directory):
    from voice_cutover_journal import MAX_BYTES as JOURNAL_BYTES
    obj,info=_read_private_file(directory,ARCHIVE,max_bytes=JOURNAL_BYTES)
    return (None,None) if obj is None else (validate_record(obj),info)


class ArchivedJournalView:
    """Read-only source compatible with existing five-resource inspection."""
    def __init__(self,directory,record):
        self.directory=Path(directory)
        self._record=record

    def read(self):
        return self._record


def _expected(*,directory,terminal,info,config_path,active_runtime):
    if terminal is None or terminal["phase"]!="rolled_back":
        raise CloseError("no complete terminal rollback for archival")
    if info is None or not stat.S_ISREG(info.st_mode) or (
        info.st_nlink!=1 or info.st_uid!=os.geteuid()
        or info.st_mode&0o077
    ):
        raise CloseError("original whole journal is not an owner-private regular file")
    journal=ArchivedJournalView(directory,terminal)
    finalization=read_finalization_proof(directory)
    if finalization is None or finalization!=expected_finalization_proof(
        journal=journal,config_path=config_path,active_runtime=active_runtime,
    ):
        raise CloseError("missing or foreign full rollback finalization proof")
    orig=mutating_predecessor(terminal)
    cfg=os.lstat(config_path)
    if (cfg.st_dev,cfg.st_ino)!=(
        finalization["config_dev"],finalization["config_inode"]
    ):
        raise CloseError("original Config inode changed before journal archive")
    fields={
        "schema":1,"phase":"archive-intent",
        "terminal_check":terminal["check"],
        "original_check":orig["check"],
        "finalization_check":finalization["check"],
        "config_dev":cfg.st_dev,"config_inode":cfg.st_ino,
        "journal_dev":info.st_dev,"journal_inode":info.st_ino,
        "archive_name":ARCHIVE,
    }
    return _validate({**fields,"check":_hash(fields)})


def inspect_close_placement(*,journal,config_path,active_runtime):
    """Read-only: classify before/after atomic rename; reject orphan archive."""
    marker=read_close_intent(journal.directory)
    archived,archive_info=_archived_record(journal.directory)
    current=journal.read()
    if marker is None:
        if archived is not None:
            raise CloseError("archive without fsynced closure intent")
        return {"state":"absent","record":current,"view":journal}
    if (archived is None)==(current is None):
        raise CloseError("whole intent and archive must have exactly one owner")
    terminal=archived if archived is not None else current
    from voice_cutover_journal import MAX_BYTES as JOURNAL_BYTES
    if archived is None:
        _,info=_read_private_file(journal.directory,"intent.json",
                                  max_bytes=JOURNAL_BYTES)
    else:
        info=archive_info
    expected=_expected(
        directory=journal.directory,terminal=terminal,info=info,
        config_path=Path(config_path),active_runtime=Path(active_runtime),
    )
    if marker!=expected:
        raise CloseError("whole archive closure marker differs from sealed evidence")
    return {
        "state":"archived-awaiting-native-acceptance" if archived is not None
                else "archive-armed",
        "record":terminal,
        "view":ArchivedJournalView(journal.directory,terminal)
               if archived is not None else journal,
    }


def _publish(directory,record):
    if read_close_intent(directory) is not None:
        raise CloseError("closure write-ahead already exists")
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(raw)>MAX_BYTES:
        raise CloseError("oversized closure intent")
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
    if read_close_intent(directory)!=record:
        raise CloseError("closure intent not durably readable")


def _rename(root):
    fd=os.open(root,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|
               getattr(os,"O_NOFOLLOW",0))
    try:
        if os.path.lexists(Path(root)/ARCHIVE):
            raise CloseError("archive destination already exists")
        os.rename("intent.json",ARCHIVE,src_dir_fd=fd,dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        os.close(fd)


def archive_verified_whole_intent(
    *,journal,ledger,previous_backup,process_evidence,security_evidence,
    install_image,config_path,active_runtime,probe,adapter,config_fd,
    config_owner,require_lifecycle_owner,
):
    """Explicit native-only archival, not an unguarded regular-service start."""
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
    if report["state"] not in (
        "previous-rollback-sealed-needs-manual-finalization",
        "previous-journal-archived-awaits-native-acceptance",
    ) or (
        report["phase"]!="rolled_back" or report["config"]!="previous"
        or report["runtime"]!="previous" or report["kernel"]!="previous"
        or report["processes"]!="running"
        or report["previous_receipt"]!="process-epoch-matches-not-readiness"
        or report["previous_finalization"]!="sealed-awaiting-owner-acceptance"
        or report["candidate_reclaim"]!="candidate-root-released-awaiting-finalization"
        or report["safe_to_close_intent"] is not False
        or report["voice_on"] is not False
    ):
        raise CloseError("native whole-system state not safe for archive")
    place=inspect_close_placement(
        journal=journal,config_path=config_path,active_runtime=active_runtime,
    )
    if place["state"]=="absent":
        from voice_cutover_journal import MAX_BYTES as JOURNAL_BYTES
        _,info=_read_private_file(journal.directory,"intent.json",
                                  max_bytes=JOURNAL_BYTES)
        expected=_expected(
            directory=journal.directory,terminal=journal.read(),info=info,
            config_path=config_path,active_runtime=active_runtime,
        )
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        _publish(journal.directory,expected)
        place=inspect_close_placement(
            journal=journal,config_path=config_path,active_runtime=active_runtime,
        )
    if place["state"]=="archive-armed":
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        _rename(journal.directory)
    completed=inspect_close_placement(
        journal=journal,config_path=config_path,active_runtime=active_runtime,
    )
    if completed["state"]!="archived-awaiting-native-acceptance":
        raise CloseError("whole rollback archive transition did not complete")
    # Complete parent directory fsync even after a crash immediately after rename.
    _sync_dir(journal.directory)
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    if ledger.pending() is not None or completed["record"]["previous"] != (
        place["record"]["previous"]
    ):
        raise CloseError("whole archive changed or scoped IPFW pending")
    return {
        "state":"whole-rollback-archived-awaiting-native-acceptance",
        "safe_to_start":False,"safe_to_close_intent":False,"voice_on":False,
    }
