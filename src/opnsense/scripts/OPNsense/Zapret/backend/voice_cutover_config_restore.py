#!/usr/bin/env python3
"""In-place previous OPNsense Config restoration for a FUTURE locked cutover.

This is an actual descriptor-based file writer, but has NO CLI, service, GUI
or boot caller. It is *not* permission to perform a standalone recovery:
the future coordinator must acquire native FD9, prove the whole five-resource
MUTATING transaction, stop the candidate engine and restore every resource.
OPNsense Config::save() uses flock() and ftruncate() on an open config.xml
file; os.replace()/rename() here would detach that inode from PHP's lock.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import os
from pathlib import Path
import stat
from typing import Callable

from voice_cutover_backup import (
    CHUNK, MAX_BYTES, VoiceBackupError, bound_resource_fingerprints,
    inspect_previous,
)
from voice_cutover_journal import VoiceCutoverJournal
from voice_native_file_observer import observe_live_files


class VoiceConfigRestoreError(RuntimeError):
    """No transaction may be declared rolled back after this exception."""


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _pinned_regular(path: Path, fd: int, *, owner: tuple[int, int]) -> os.stat_result:
    """Reject symlinks, hardlinks, replaced paths and foreign owners."""
    path_info = os.lstat(path)
    info = os.fstat(fd)
    if not stat.S_ISREG(path_info.st_mode) or not stat.S_ISREG(info.st_mode) or \
       info.st_nlink != 1 or path_info.st_nlink != 1 or \
       _identity(info) != _identity(path_info) or \
       (info.st_uid, info.st_gid) != owner:
        raise VoiceConfigRestoreError("Config inode/owner changed or is unsafe")
    return info


def _sha_fd(fd: int) -> tuple[str, int]:
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    count = 0
    while True:
        block = os.read(fd, CHUNK)
        if not block:
            break
        count += len(block)
        if count > MAX_BYTES:
            raise VoiceConfigRestoreError("Config exceeds saved Voice byte bound")
        digest.update(block)
    return digest.hexdigest(), count


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError(errno.EIO, "short write to OPNsense Config")
        view = view[written:]


def restore_previous_config_in_place(
    config_path: Path, install_image: Path, previous_backup: Path,
    journal: VoiceCutoverJournal, *, require_lifecycle_owner: Callable[[], None],
    expected_owner: tuple[int, int],
) -> str:
    """Restore Config bytes WITHOUT replacing its locked inode.

    Preconditions: future native caller must already hold the same FD9
    lifecycle lease across *all* resources and validate process/IPFW state.
    require_lifecycle_owner MUST be native.require_native_lock in production;
    tests inject an isolated witness. The current Config must match EITHER
    journal.candidate.saved_xml_sha256 or sealed previous Config exactly.
    Any third-party changed Config is a conflict, never silently overwritten.
    This helper does not close or mark the whole-cutover journal.
    """
    if not callable(require_lifecycle_owner) or \
       not isinstance(expected_owner, tuple) or len(expected_owner) != 2 or \
       any(type(x) is not int or x < 0 for x in expected_owner):
        raise VoiceConfigRestoreError("explicit native lock and Config owner policy required")
    require_lifecycle_owner()
    record = journal.read()
    if not isinstance(record, dict) or record["schema"] < 2 or \
       record["phase"] != "mutating":
        raise VoiceConfigRestoreError("no mutating, bound whole-system Voice intent")
    saved = inspect_previous(Path(previous_backup))
    bound_resource_fingerprints(Path(previous_backup), record["previous"])
    if saved["schema"] != 2:
        raise VoiceConfigRestoreError("previous Config needs schema-2 sealed snapshot")

    image = Path(install_image)
    if observe_live_files(image / "config.xml", image / "runtime",
                          previous_backup=previous_backup) != {
        name: record["previous"][name] for name in ("config", "runtime")
    }:
        raise VoiceConfigRestoreError("previous install image does not match durable intent")
    config_path = Path(config_path)
    # The preimage is pinned by the actual candidate Config digest. A helper
    # can refuse a rollback if another OPNsense writer changed the file.
    expected_live = record["candidate"]["saved_xml_sha256"]
    expected_previous = record["previous"]["config"]
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | \
        getattr(os, "O_CLOEXEC", 0)
    live_fd = os.open(config_path, flags)
    try:
        _pinned_regular(config_path, live_fd, owner=expected_owner)
        try:
            fcntl.flock(live_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise VoiceConfigRestoreError("OPNsense Config is locked by another writer") from exc
            raise
        _pinned_regular(config_path, live_fd, owner=expected_owner)
        before_hash, before_size = _sha_fd(live_fd)
        if before_hash not in (expected_live, expected_previous):
            raise VoiceConfigRestoreError("foreign Config contents; previous rollback refused")

        original_mode = saved["config"]["mode"]
        source_fd = os.open(
            image / "config.xml",
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
            getattr(os, "O_CLOEXEC", 0),
        )
        try:
            _pinned_regular(image / "config.xml", source_fd,
                            owner=(os.geteuid(), os.getegid()))
            source_hash, source_bytes = _sha_fd(source_fd)
            if source_hash != expected_previous or \
               source_bytes != saved["config"]["bytes"]:
                raise VoiceConfigRestoreError("install-image Config changed before restore")
            # Still holding flock on the SAME live inode, and FD9 from the
            # outer coordinator. Revalidate journal just before first write.
            require_lifecycle_owner()
            if journal.read() != record:
                raise VoiceConfigRestoreError("Voice journal changed while restoring Config")
            _pinned_regular(config_path, live_fd, owner=expected_owner)
            if _sha_fd(live_fd) != (before_hash, before_size):
                raise VoiceConfigRestoreError("live Config changed while restoring")
            if before_hash == expected_previous and \
               stat.S_IMODE(os.fstat(live_fd).st_mode) == original_mode:
                return "already-previous"

            # Truncating the original inode (rather than rename) preserves
            # existing OPNsense Config::save() lock identity. A write failure
            # leaves the durable MUTATING intent AND original backup intact.
            # There is deliberately no implicit journal abort.
            os.ftruncate(live_fd, 0)
            os.lseek(live_fd, 0, os.SEEK_SET)
            os.lseek(source_fd, 0, os.SEEK_SET)
            while True:
                block = os.read(source_fd, CHUNK)
                if not block:
                    break
                _write_all(live_fd, block)
            os.fchmod(live_fd, original_mode)
            os.fsync(live_fd)
            if _sha_fd(live_fd) != (expected_previous, saved["config"]["bytes"]) or \
               stat.S_IMODE(os.fstat(live_fd).st_mode) != original_mode:
                raise VoiceConfigRestoreError("restored Config did not verify")
            if _sha_fd(source_fd) != (expected_previous, source_bytes):
                raise VoiceConfigRestoreError("Config restore source changed during write")
            _pinned_regular(config_path, live_fd, owner=expected_owner)
            require_lifecycle_owner()
            if journal.read() != record:
                raise VoiceConfigRestoreError("Voice journal changed after Config write")
            return "previous-config-restored"
        finally:
            os.close(source_fd)
    finally:
        # Releasing this lock never signals whole-system rollback success.
        # The caller must still restore runtime, engine, firewall/supervisor.
        os.close(live_fd)
