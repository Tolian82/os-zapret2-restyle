#!/usr/bin/env python3
"""Durable write-ahead intent for an interrupted in-place Voice Config restore.

An OPNsense Config writer MUST NOT rename /conf/config.xml: PHP already holds
an open flock() inode. In-place truncate/write is not atomic, so an exact
write-ahead record must be fsync'd BEFORE the first truncate. This module
is read/write-once private file metadata only, NOT a cutover coordinator,
boot replay, standalone service, or permission to mutate live Config.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import _private_dir, _sync_dir

MAX_REDO = 4096
NAME = "config-restore-redo.json"


class VoiceConfigRedoError(ValueError):
    pass


def _canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _checksum(fields: dict) -> str:
    return hashlib.sha256(_canonical(fields)).hexdigest()


def _validate(data: dict) -> dict:
    if not isinstance(data, dict) or set(data) != {
        "schema", "phase", "cutover_check", "device", "inode",
        "uid", "gid", "before_sha256", "previous_sha256",
        "previous_bytes", "checksum",
    } or type(data["schema"]) is not int or data["schema"] != 1 or \
       data["phase"] != "armed":
        raise VoiceConfigRedoError("invalid Config redo record schema")
    for field in ("device", "inode", "uid", "gid", "previous_bytes"):
        if type(data[field]) is not int or data[field] < 0:
            raise VoiceConfigRedoError("invalid Config redo inode/owner/size")
    for field in ("cutover_check", "before_sha256", "previous_sha256", "checksum"):
        value = data[field]
        if not isinstance(value, str) or len(value) != 64 or \
           any(ch not in "0123456789abcdef" for ch in value):
            raise VoiceConfigRedoError("invalid Config redo hash")
    if data["checksum"] != _checksum({k: v for k, v in data.items()
                                      if k != "checksum"}):
        raise VoiceConfigRedoError("Config redo checksum mismatch")
    return data


class ConfigRestoreRedo:
    """Write-once, inode-bound recovery marker within the sealed journal root.

    The marker is retained through partial writes, retries AND successful
    standalone Config restoration. Only a future complete five-resource
    rollback owner may remove it after proving the previous system and
    closing the whole intent. A stale marker fails closed for a new intent.
    """

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        _private_dir(self.directory)

    def read(self) -> dict | None:
        _private_dir(self.directory)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(self.directory / NAME, flags)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or \
               info.st_uid != os.geteuid() or info.st_mode & 0o077 or \
               info.st_size > MAX_REDO:
                raise VoiceConfigRedoError("unsafe Config redo record")
            raw = stream.read(MAX_REDO + 1)
        if len(raw) > MAX_REDO:
            raise VoiceConfigRedoError("oversized Config redo record")
        try:
            return _validate(json.loads(raw))
        except (ValueError, UnicodeError) as exc:
            raise VoiceConfigRedoError("corrupted Config redo record") from exc

    def arm(self, *, journal_record: dict, info: os.stat_result,
            previous_bytes: int) -> dict:
        """Fsync intent + parent before caller can truncate Config."""
        if journal_record["phase"] != "mutating" or \
           journal_record["schema"] < 2:
            raise VoiceConfigRedoError("missing mutating bound Voice intent")
        data = {
            "schema": 1, "phase": "armed",
            "cutover_check": journal_record["check"],
            "device": info.st_dev, "inode": info.st_ino,
            "uid": info.st_uid, "gid": info.st_gid,
            "before_sha256": journal_record["candidate"]["saved_xml_sha256"],
            "previous_sha256": journal_record["previous"]["config"],
            "previous_bytes": previous_bytes,
        }
        data["checksum"] = _checksum(data)
        _validate(data)
        previous = self.read()
        if previous is not None:
            if previous != data:
                raise VoiceConfigRedoError("Config redo belongs to another cutover or inode")
            return previous
        encoded = _canonical(data) + b"\n"
        if len(encoded) > MAX_REDO:
            raise VoiceConfigRedoError("Config redo exceeds private bound")
        # O_EXCL forbids accidental replacement; an interrupted creation
        # remains malformed and MUST require explicit investigation.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | \
            getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.directory / NAME, flags, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as output:
                fd = -1
                output.write(encoded)
                output.flush()
                os.fsync(output.fileno())
        finally:
            if fd >= 0:
                os.close(fd)
        _sync_dir(self.directory)
        if self.read() != data:
            raise VoiceConfigRedoError("Config redo not durably readable")
        return data


def _prefix_matches(live_fd: int, source_fd: int, saved_bytes: int,
                    *, chunk_size: int = 1024 * 1024) -> bool:
    """A crash can only leave a prefix of the OLD bytes that we stream.

    Empty prefix is allowed because truncate may have reached storage before
    the first byte. Arbitrary partial data or changed suffixes are refused.
    """
    size = os.fstat(live_fd).st_size
    if size > saved_bytes:
        return False
    os.lseek(live_fd, 0, os.SEEK_SET)
    os.lseek(source_fd, 0, os.SEEK_SET)
    remaining = size
    while remaining:
        live = os.read(live_fd, min(chunk_size, remaining))
        source = os.read(source_fd, len(live))
        if not live or live != source:
            return False
        remaining -= len(live)
    return True


def may_resume_partial(redo: dict | None, *, journal_record: dict,
                       live_info: os.stat_result, live_fd: int,
                       source_fd: int, saved_bytes: int) -> bool:
    """Return True only for proven, same-inode, armed old-byte prefix."""
    if redo is None:
        return False
    _validate(redo)
    if redo["cutover_check"] != journal_record["check"] or \
       redo["device"] != live_info.st_dev or \
       redo["inode"] != live_info.st_ino or \
       (redo["uid"], redo["gid"]) != (live_info.st_uid, live_info.st_gid) or \
       redo["before_sha256"] != journal_record["candidate"]["saved_xml_sha256"] or \
       redo["previous_sha256"] != journal_record["previous"]["config"] or \
       redo["previous_bytes"] != saved_bytes:
        raise VoiceConfigRedoError("Config redo no longer matches sealed intent/inode")
    return _prefix_matches(live_fd, source_fd, saved_bytes)
