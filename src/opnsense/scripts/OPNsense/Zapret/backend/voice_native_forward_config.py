#!/usr/bin/env python3
"""Read-only compatibility verifier for historical forward Config redo.

The separate Voice candidate-Config writer was never a normal Apply entrypoint
and is retired. A partially written historical candidate still requires an
inode-bound, checksum-sealed redo and verified candidate prefix before the
existing previous-Config rollback may recognize it. No forward writes, marker
arming, commit, or independent Voice Config ownership live in this module.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import CHUNK, MAX_BYTES, _private_dir
from voice_cutover_config_restore import _pinned_regular, _sha_fd
from voice_cutover_journal import RUNTIME_BOUND_SCHEMA

NAME = "forward-config-redo.json"
MAX_MARKER = 4096


class ForwardConfigError(RuntimeError):
    pass


def _digest(body):
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _validate(marker):
    names = {
        "schema", "whole_check", "config_dev", "config_inode", "config_uid",
        "config_gid", "previous_sha256", "candidate_sha256",
        "candidate_bytes", "previous_mode", "source_path", "source_dev",
        "source_inode", "source_uid", "source_gid", "check",
    }
    if not isinstance(marker, dict) or set(marker) != names or (
        type(marker["schema"]) is not int or marker["schema"] != 1
    ):
        raise ForwardConfigError("invalid candidate Config redo schema")
    if any(type(marker[key]) is not int or marker[key] < 0 for key in (
        "config_dev", "config_inode", "config_uid", "config_gid",
        "candidate_bytes", "previous_mode", "source_dev", "source_inode",
        "source_uid", "source_gid",
    )) or marker["candidate_bytes"] > MAX_BYTES or marker["previous_mode"] > 0o7777:
        raise ForwardConfigError("invalid candidate Config inode/size/mode")
    path = marker["source_path"]
    if not isinstance(path, str) or not path.startswith("/") or len(path) > 4096 or (
        "\x00" in path or ".." in Path(path).parts
    ):
        raise ForwardConfigError("invalid sealed candidate Config source path")
    if any(type(marker[key]) is not str or len(marker[key]) != 64 or (
        set(marker[key]) - set("0123456789abcdef")
    ) for key in ("whole_check", "previous_sha256", "candidate_sha256", "check")):
        raise ForwardConfigError("invalid candidate Config digest")
    if marker["check"] != _digest({k: v for k, v in marker.items() if k != "check"}):
        raise ForwardConfigError("candidate Config redo checksum mismatch")
    return marker


def read_forward_config_redo(root: Path):
    root = Path(root)
    _private_dir(root)
    try:
        fd = os.open(root / NAME, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (
            info.st_uid != os.geteuid() or info.st_mode & 0o077
            or info.st_size > MAX_MARKER
        ):
            raise ForwardConfigError("unsafe candidate Config redo inode")
        raw = os.read(fd, MAX_MARKER + 1)
        if len(raw) > MAX_MARKER:
            raise ForwardConfigError("oversized candidate Config redo")
        try:
            return _validate(json.loads(raw))
        except (ValueError, UnicodeError, TypeError) as exc:
            raise ForwardConfigError("corrupt candidate Config redo") from exc
    finally:
        os.close(fd)


def _candidate_prefix(live_fd, source_fd, source_bytes):
    size = os.fstat(live_fd).st_size
    if size > source_bytes:
        return False
    os.lseek(live_fd, 0, os.SEEK_SET)
    os.lseek(source_fd, 0, os.SEEK_SET)
    remaining = size
    while remaining:
        old = os.read(live_fd, min(CHUNK, remaining))
        new = os.read(source_fd, len(old))
        if not old or old != new:
            return False
        remaining -= len(old)
    return True


def is_bound_forward_candidate_prefix(marker, journal_record, live_fd, live_info):
    """Allow *previous* rollback of a torn candidate Config only with exact redo.

    Validates the sealed candidate source again on a pinned no-follow inode.
    Called ONLY by the already locked five-resource previous Config restorer.
    This never authorizes forward execution or automatic reboot cleanup.
    """
    if marker is None:
        return False
    _validate(marker)
    if journal_record["schema"] != RUNTIME_BOUND_SCHEMA or (
        journal_record["phase"] != "mutating"
        or marker["whole_check"] != journal_record["check"]
        or marker["previous_sha256"] != journal_record["previous"]["config"]
        or marker["candidate_sha256"] != journal_record["candidate"]["saved_xml_sha256"]
        or (live_info.st_dev, live_info.st_ino, live_info.st_uid, live_info.st_gid) != (
            marker["config_dev"], marker["config_inode"],
            marker["config_uid"], marker["config_gid"],
        )
    ):
        raise ForwardConfigError("forward Config redo not bound to locked Config/intent")
    source = Path(marker["source_path"])
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        _pinned_regular(source, fd, owner=(marker["source_uid"], marker["source_gid"]))
        stat_source = os.fstat(fd)
        if (stat_source.st_dev, stat_source.st_ino) != (
            marker["source_dev"], marker["source_inode"]
        ) or _sha_fd(fd) != (marker["candidate_sha256"], marker["candidate_bytes"]):
            raise ForwardConfigError("forward Config source changed after redo")
        return _candidate_prefix(live_fd, fd, marker["candidate_bytes"])
    finally:
        os.close(fd)

