#!/usr/bin/env python3
"""Read-only validator for historical Voice forward-runtime redo evidence.

The retired private forward runtime installer has no normal GUI/configd/service
caller. Older interrupted schema-4 recovery records can still exist on an
appliance and must be read safely by voice_cutover_file_rollback. This module
therefore retains the original on-disk format, inode/owner/mode checks, strict
record schema and digest validation, but exposes NO filesystem mutation path.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

MARKER="forward-runtime-redo.json"
LIMIT=4096
HEX=frozenset("0123456789abcdef")


class ForwardRuntimeError(RuntimeError):
    pass


def _digest(obj):
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,
    ).encode("ascii")).hexdigest()


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

