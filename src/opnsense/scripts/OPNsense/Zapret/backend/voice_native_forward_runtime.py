#!/usr/bin/env python3
"""Native forward Voice runtime installation, recoverable across power loss.

Real filesystem operations, deliberately NO CLI/GUI/configd caller. A trusted
future FD9+original Config-flock forward executor must FIRST durably advance
the schema-4 whole journal to MUTATING and independently stop all dvtws2 and
supervisor processes while preserving previous IPFW ownership.

Copies and fsyncs the exact bound candidate into a same-parent 'ready' tree,
fsyncs an owner-private write-ahead redo record, then atomically renames
old active -> retained previous and ready -> active. The original old tree and
candidate source remain intact; no deletion, no engine start, no IPFW or Config
mutation, no Voice ON or commit. Retries ONLY exact known crash states.

A crash BEFORE redo publication may leave an unowned ready directory; never
adopt it silently. A crash AFTER a persisted marker is retried under the SAME
native owner with a separate independent all-process quiescence gate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import (
    bound_resource_fingerprints, _copy_regular, _sync_dir,
)
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA
from voice_cutover_runtime_restore import _safe_parent
from voice_native_file_observer import observe_live_files
from voice_native_recovery_quiescence import _locked_config

MARKER="forward-runtime-redo.json"
LIMIT=4096
HEX=frozenset("0123456789abcdef")


class ForwardRuntimeError(RuntimeError):
    pass


def _digest(obj):
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _marked(fields):
    return {**fields,"check":_digest(fields)}


def _validate(data):
    fields={"schema","whole_check","config_dev","config_inode",
            "parent_dev","parent_inode","active_name","candidate_sha256",
            "previous_sha256","ready_name","retained_name","check"}
    if not isinstance(data,dict) or set(data)!=fields or (
        type(data["schema"]) is not int or data["schema"]!=1
        or any(type(data[k]) is not int or data[k]<0 for k in (
            "config_dev","config_inode","parent_dev","parent_inode"
        ))
    ):
        raise ForwardRuntimeError("invalid forward runtime redo")
    if any(type(data[k]) is not str or len(data[k])!=64 or (
        set(data[k]) - HEX
    ) for k in ("whole_check","candidate_sha256","previous_sha256","check")):
        raise ForwardRuntimeError("invalid forward runtime digest")
    if data["check"]!=_digest({k:v for k,v in data.items() if k!="check"}):
        raise ForwardRuntimeError("forward runtime redo checksum mismatch")
    suffix=data["whole_check"][:20]
    if (
        not data["active_name"] or "/" in data["active_name"]
        or data["active_name"] in (".","..")
        or data["ready_name"]!=".voice-forward-ready-"+suffix
        or data["retained_name"]!=".voice-forward-previous-"+suffix
    ):
        raise ForwardRuntimeError("foreign forward runtime filenames")
    return data


def _read_redo(directory):
    root=Path(directory)
    fd=None
    try:
        fd=os.open(root/MARKER,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    except FileNotFoundError:
        return None
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or (
            info.st_uid!=os.geteuid() or info.st_mode&0o077
            or info.st_size>LIMIT
        ):
            raise ForwardRuntimeError("untrusted forward runtime redo inode")
        raw=os.read(fd,LIMIT+1)
        if len(raw)>LIMIT:
            raise ForwardRuntimeError("oversized forward runtime redo")
        try:
            return _validate(json.loads(raw))
        except (ValueError,UnicodeError,TypeError) as exc:
            raise ForwardRuntimeError("corrupt forward runtime redo") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _arm(directory,body):
    record=_validate(_marked(body))
    root=Path(directory)
    if os.path.lexists(root/MARKER):
        raise ForwardRuntimeError("forward runtime redo already exists")
    data=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
    if len(data)>LIMIT:
        raise ForwardRuntimeError("forward redo exceeds bound")
    fd=os.open(root/MARKER,os.O_WRONLY|os.O_CREAT|os.O_EXCL|
               getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        with os.fdopen(fd,"wb") as output:
            fd=-1
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    finally:
        if fd>=0:os.close(fd)
    _sync_dir(root)
    if _read_redo(root)!=record:
        raise ForwardRuntimeError("persisted forward redo differs")
    return record


def _copy_candidate(source,ready):
    """Bounded no-follow copy, restoring original candidate modes."""
    if source.is_symlink() or not source.is_dir() or (
        os.path.lexists(ready)
    ):
        raise ForwardRuntimeError("untrusted candidate source/destination")
    ready.mkdir(mode=0o700)
    os.chmod(ready,0o700)
    for here,dirs,files in os.walk(source,topdown=True,followlinks=False):
        current=Path(here)
        if current.is_symlink():
            raise ForwardRuntimeError("candidate runtime has linked directory")
        rel=current.relative_to(source)
        target=ready/rel
        original=os.lstat(current)
        if not stat.S_ISDIR(original.st_mode) or original.st_uid!=os.geteuid():
            raise ForwardRuntimeError("candidate directory ownership changed")
        for name in sorted(dirs):
            node=current/name
            info=os.lstat(node)
            if not stat.S_ISDIR(info.st_mode) or (
                stat.S_ISLNK(info.st_mode) or info.st_uid!=os.geteuid()
            ):
                raise ForwardRuntimeError("candidate contains linked/foreign directory")
            (target/name).mkdir(mode=0o700)
        for name in sorted(files):
            node=current/name
            info=os.lstat(node)
            if not stat.S_ISREG(info.st_mode) or (
                info.st_uid!=os.geteuid() or info.st_nlink!=1
            ):
                raise ForwardRuntimeError("candidate contains linked/foreign file")
            dst=target/name
            _copy_regular(node,dst,info)
            os.chmod(dst,stat.S_IMODE(info.st_mode))
        # Directory modes restored only AFTER child directory entries exist.
    for here,dirs,files in os.walk(source,topdown=False,followlinks=False):
        current=Path(here)
        target=ready/current.relative_to(source)
        info=os.lstat(current)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ForwardRuntimeError("candidate directory mutated")
        os.chmod(target,stat.S_IMODE(info.st_mode))
        _sync_dir(target)
    _sync_dir(ready.parent)


def install_forward_runtime(
    *,active_runtime,staged_config,candidate_runtime,previous_backup,journal,
    config_path,locked_config_fd,config_owner,require_lifecycle_owner,
    require_all_processes_stopped,
):
    """Mutate ONLY runtime path on a schema-4 whole MUTATING transaction.

    Does not transition prepared->mutating: the upper coordinator must save
    its irreversible write-ahead decision BEFORE stopping previous processes.
    """
    if not isinstance(journal,VoiceCutoverJournal) or not callable(
        require_lifecycle_owner
    ) or not callable(require_all_processes_stopped):
        raise ForwardRuntimeError("native lifecycle and quiescence owners required")
    active_runtime,staged_config,candidate_runtime=map(
        Path,(active_runtime,staged_config,candidate_runtime)
    )
    config_path=Path(config_path)
    require_lifecycle_owner()
    _locked_config(config_path,locked_config_fd,config_owner)
    cfg=_pinned_regular(config_path,locked_config_fd,owner=config_owner)
    record=journal.read()
    if record is None or record["phase"]!="mutating" or (
        record["schema"]!=RUNTIME_BOUND_SCHEMA
    ):
        raise ForwardRuntimeError("whole Voice transaction not schema-4 MUTATING")
    previous=bound_resource_fingerprints(previous_backup,record["previous"])
    candidate_sha=record["candidate"]["candidate_runtime_sha256"]
    candidate=observe_live_files(staged_config,candidate_runtime)
    if candidate["runtime"]!=candidate_sha or (
        candidate["config"]!=record["candidate"]["saved_xml_sha256"]
    ):
        raise ForwardRuntimeError("staged candidate differs from whole Voice journal")
    if cfg.st_dev!=os.lstat(config_path).st_dev or (
        cfg.st_ino!=os.lstat(config_path).st_ino
    ):
        raise ForwardRuntimeError("Config inode replaced")
    if observe_live_files(config_path,candidate_runtime)["config"]!=previous["config"]:
        raise ForwardRuntimeError("live Config must still be previous before runtime swap")
    parent=_safe_parent(active_runtime.parent)
    suffix=record["check"][:20]
    ready=active_runtime.with_name(".voice-forward-ready-"+suffix)
    retained=active_runtime.with_name(".voice-forward-previous-"+suffix)
    fields={
        "schema":1,"whole_check":record["check"],
        "config_dev":cfg.st_dev,"config_inode":cfg.st_ino,
        "parent_dev":parent.st_dev,"parent_inode":parent.st_ino,
        "active_name":active_runtime.name,
        "candidate_sha256":candidate_sha,
        "previous_sha256":previous["runtime"],
        "ready_name":ready.name,"retained_name":retained.name,
    }
    expected=_validate(_marked(fields))
    seen=_read_redo(journal.directory)
    if seen is not None and seen!=expected:
        raise ForwardRuntimeError("foreign forward-runtime redo marker")

    def check_owner():
        require_lifecycle_owner()
        _locked_config(config_path,locked_config_fd,config_owner)
        if require_all_processes_stopped() is not True:
            raise ForwardRuntimeError("dvtws2 and supervisor not all stopped")
        if journal.read()!=record or (
            _read_redo(journal.directory)!=expected
        ):
            raise ForwardRuntimeError("whole or forward journal changed")
        now=_safe_parent(active_runtime.parent)
        if (now.st_dev,now.st_ino)!=(parent.st_dev,parent.st_ino):
            raise ForwardRuntimeError("runtime parent replaced")
        current=_pinned_regular(config_path,locked_config_fd,owner=config_owner)
        if (current.st_dev,current.st_ino)!=(cfg.st_dev,cfg.st_ino):
            raise ForwardRuntimeError("Config original inode changed")

    def check_tree(path,sha):
        if os.path.lexists(path):
            if path.is_symlink():
                raise ForwardRuntimeError("linked active/staging runtime")
            return observe_live_files(staged_config,path)["runtime"]==sha
        return False

    if seen is None:
        if os.path.lexists(ready) or os.path.lexists(retained):
            raise ForwardRuntimeError("orphan forward runtime path, manual review")
        if not check_tree(active_runtime,previous["runtime"]):
            raise ForwardRuntimeError("old active runtime already changed")
        require_lifecycle_owner()
        if require_all_processes_stopped() is not True:
            raise ForwardRuntimeError("stop old engine/supervisor before staging")
        _copy_candidate(candidate_runtime,ready)
        if not check_tree(ready,candidate_sha):
            raise ForwardRuntimeError("candidate copy changed")
        if observe_live_files(staged_config,candidate_runtime)!=candidate:
            raise ForwardRuntimeError("candidate source changed during copy")
        _arm(journal.directory,fields)
    check_owner()
    if not os.path.lexists(retained):
        if not check_tree(active_runtime,previous["runtime"]) or (
            not check_tree(ready,candidate_sha)
        ):
            raise ForwardRuntimeError("unexpected runtime before old tree retirement")
        check_owner()
        if os.path.lexists(retained):
            raise ForwardRuntimeError("retained previous runtime appeared")
        os.rename(active_runtime,retained)
        _sync_dir(active_runtime.parent)
        check_owner()
    if not check_tree(retained,previous["runtime"]):
        raise ForwardRuntimeError("retained previous runtime changed")
    if not os.path.lexists(active_runtime):
        if not check_tree(ready,candidate_sha):
            raise ForwardRuntimeError("ready candidate missing after first rename")
        check_owner()
        os.rename(ready,active_runtime)
        _sync_dir(active_runtime.parent)
        check_owner()
    if os.path.lexists(ready) or not check_tree(
        active_runtime,candidate_sha
    ) or not check_tree(retained,previous["runtime"]):
        raise ForwardRuntimeError("forward Voice runtime did not converge")
    check_owner()
    return {
        "state":"native-voice-forward-runtime-installed",
        "previous_preserved":True,
        "whole_phase":"mutating",
        "safe_to_start":False,
        "safe_to_commit":False,
        "voice_on":False,
    }
