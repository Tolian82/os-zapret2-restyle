#!/usr/bin/env python3
"""Staging-only read-only live Config/runtime fingerprint witness.

Mirrors voice_cutover_backup's exact Config SHA256 and canonical runtime-tree
fingerprint without writing or staging a file.
When bound to a sealed previous backup, also require its exact Config mode;
Config content hashes deliberately exclude the mode bits. Uses anchored descriptor-relative
traversal and O_NOFOLLOW; refuses symlinks, hard links, special files, unstable
inode metadata, unsafe owners, excessive depth/files/bytes, and torn scans.

No CLI, restore, process control, IPFW changes, or lifecycle hook. The caller
MUST hold the native Config and lifecycle locks before treating any result as
a trustworthy cutover observation. Hash equality alone does not prove locks,
process identity, kernel IPFW ownership, or automatic recovery.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from voice_cutover_backup import (
    CHUNK, MAX_BYTES, MAX_FILES, VoiceBackupError, inspect_previous,
)

MAX_DEPTH = 32
MAX_PATH_BYTES = 4096
_DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | \
    getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | \
    getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)


class LiveFileEvidenceError(ValueError):
    pass


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            stat.S_IMODE(info.st_mode))


def _require_directory(info):
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise LiveFileEvidenceError("untrusted live Voice runtime directory")


def _require_regular(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or \
       info.st_uid != os.geteuid() or info.st_size > MAX_BYTES:
        raise LiveFileEvidenceError("untrusted live Voice regular file")


def _open_root(path: Path) -> int:
    original = os.lstat(path)
    _require_directory(original)
    fd = os.open(path, _DIR_FLAGS)
    try:
        observed = os.fstat(fd)
        _require_directory(observed)
        if _identity(original) != _identity(observed):
            raise LiveFileEvidenceError("live Voice runtime root changed during open")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _hash_file(path: str | Path, *, parent_fd: int | None = None) -> tuple[str,int,int]:
    before = (os.stat(path, dir_fd=parent_fd, follow_symlinks=False)
              if parent_fd is not None else os.lstat(path))
    _require_regular(before)
    fd = (os.open(path, _FILE_FLAGS, dir_fd=parent_fd)
          if parent_fd is not None else os.open(path, _FILE_FLAGS))
    try:
        start = os.fstat(fd)
        _require_regular(start)
        if _identity(start) != _identity(before):
            raise LiveFileEvidenceError("live Voice file changed before read")
        sha = hashlib.sha256()
        length = 0
        while True:
            chunk = os.read(fd, CHUNK)
            if not chunk:
                break
            length += len(chunk)
            if length > MAX_BYTES:
                raise LiveFileEvidenceError("live Voice file exceeds safety limit")
            sha.update(chunk)
        finish = os.fstat(fd)
        if length != start.st_size or _identity(start) != _identity(finish):
            raise LiveFileEvidenceError("live Voice file changed while reading")
        return sha.hexdigest(), length, stat.S_IMODE(start.st_mode)
    finally:
        os.close(fd)


def _scan_dir(fd, prefix, depth, entries, bounds):
    if depth > MAX_DEPTH:
        raise LiveFileEvidenceError("live Voice runtime exceeds maximum depth")
    before = os.fstat(fd)
    _require_directory(before)
    names = os.listdir(fd)
    if len(names) + bounds["entries"] > MAX_FILES:
        raise LiveFileEvidenceError("live Voice runtime entry count exceeds bound")
    for name in sorted(names):
        if not isinstance(name, str) or name in ("", ".", "..") or \
           "/" in name or "\x00" in name:
            raise LiveFileEvidenceError("unsafe Voice runtime entry")
        rel = prefix + name
        if len(os.fsencode(rel)) > MAX_PATH_BYTES:
            raise LiveFileEvidenceError("live Voice runtime path exceeds bound")
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        bounds["entries"] += 1
        if bounds["entries"] > MAX_FILES:
            raise LiveFileEvidenceError("live Voice runtime entry count exceeds bound")
        if stat.S_ISDIR(info.st_mode):
            _require_directory(info)
            child = os.open(name, _DIR_FLAGS, dir_fd=fd)
            try:
                start = os.fstat(child)
                _require_directory(start)
                if _identity(info) != _identity(start):
                    raise LiveFileEvidenceError("live runtime directory replaced")
                entries[rel + "/"] = {
                    "type": "dir", "mode": stat.S_IMODE(start.st_mode),
                }
                _scan_dir(child, rel + "/", depth + 1, entries, bounds)
                if _identity(start) != _identity(os.fstat(child)):
                    raise LiveFileEvidenceError("live runtime directory changed during scan")
            finally:
                os.close(child)
        elif stat.S_ISREG(info.st_mode):
            sha, length, mode = _hash_file(name, parent_fd=fd)
            bounds["bytes"] += length
            if bounds["bytes"] > MAX_BYTES:
                raise LiveFileEvidenceError("live Voice runtime exceeds byte bound")
            entries[rel] = {"type": "file", "sha256": sha, "bytes": length, "mode": mode}
        else:
            raise LiveFileEvidenceError("symlink or special file in live runtime")
    if _identity(before) != _identity(os.fstat(fd)):
        raise LiveFileEvidenceError("live runtime directory mutated during enumeration")


def _scan(config: Path, runtime: Path):
    config_sha, config_size, config_mode = _hash_file(config)
    fd = _open_root(runtime)
    try:
        root_before = os.fstat(fd)
        entries = {}
        bounds = {"entries": 0, "bytes": 0}
        _scan_dir(fd, "", 0, entries, bounds)
        if _identity(root_before) != _identity(os.fstat(fd)):
            raise LiveFileEvidenceError("live Voice runtime root changed during scan")
        runtime_content = {"entries": entries, "total_bytes": bounds["bytes"]}
        runtime_sha = hashlib.sha256(json.dumps(
            runtime_content, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")).hexdigest()
        return (config_sha, config_size, config_mode), runtime_sha
    finally:
        os.close(fd)


def observe_live_files(config: Path, runtime: Path,
                       *, previous_backup: Path | None = None) -> dict[str, str]:
    """Two full stable read-only sweeps of Config and runtime, fail closed."""
    config, runtime = Path(config), Path(runtime)
    if not config.is_absolute() or not runtime.is_absolute() or \
       config == runtime:
        raise LiveFileEvidenceError("fixed absolute Config and runtime paths required")
    try:
        first = _scan(config, runtime)
        second = _scan(config, runtime)
    except (OSError, VoiceBackupError, UnicodeError, RecursionError) as exc:
        raise LiveFileEvidenceError("untrusted live Voice file inspection") from exc
    if first != second:
        raise LiveFileEvidenceError("live Config/runtime changed between observations")
    if previous_backup is not None:
        # The whole-cutover config fingerprint intentionally contains only
        # the SHA256 of config bytes. To certify the *previous* live state,
        # separately require the exact saved permission bits, not just bytes.
        try:
            old = inspect_previous(Path(previous_backup))
        except (OSError, VoiceBackupError) as exc:
            raise LiveFileEvidenceError("invalid sealed previous Voice Config mode") from exc
        if first[0][2] != old["config"]["mode"]:
            raise LiveFileEvidenceError("live Config permission mode differs from sealed prior")
    return {"config": first[0][0], "runtime": first[1]}


class LiveFileObserver:
    """Injectable two-resource source for the eventual five-resource observer."""

    def __init__(self, config: Path, runtime: Path,
                 previous_backup: Path | None = None):
        self.config, self.runtime = Path(config), Path(runtime)
        self.previous_backup = (Path(previous_backup) if previous_backup is not None
                                else None)

    def observe(self) -> dict[str, str]:
        return observe_live_files(self.config, self.runtime,
                                  previous_backup=self.previous_backup)
