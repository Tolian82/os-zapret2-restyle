#!/usr/bin/env python3
"""Crash-resumable directory restoration of the previous Voice runtime.

REAL filesystem staging and same-parent directory renames, but deliberately
NO production CLI, service, GUI or boot hook. The eventual coordinator MUST
hold native FD9 and the complete Config/lifecycle authority, stop candidate
dvtws2, and independently prove firewall/supervisor ownership before calling.

Unlike Config restoration, runtime is a directory: preserve the candidate by
renaming it to a deterministic retired path, then rename a fully fsync'd old
tree into the active path. A write-once private redo record makes the gap
between the two renames detectable on retry. The old candidate is NEVER
destroyed here; completing the whole-system rollback remains separate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Callable

from voice_cutover_backup import (
    VoiceBackupError, _copy_regular, _regular, _private_dir, _sync_dir,
    bound_resource_fingerprints, inspect_previous,
)
from voice_cutover_install_image import _restore_mode
from voice_cutover_journal import VoiceCutoverJournal
from voice_native_file_observer import observe_live_files

REDO = "runtime-restore-redo.json"
MAX_REDO = 4096
HEX = set("0123456789abcdef")


class VoiceRuntimeRestoreError(RuntimeError):
    """The complete cutover journal MUST remain pending on errors."""


def _digest(obj: dict) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def _record(fields: dict) -> dict:
    return {**fields, "checksum": _digest(fields)}


def _validate(record: dict) -> dict:
    names = {"schema", "cutover_check", "parent_dev", "parent_ino",
             "active_name", "candidate_sha256", "previous_sha256",
             "ready_name", "retired_name", "checksum"}
    if not isinstance(record, dict) or set(record) != names or \
       type(record["schema"]) is not int or record["schema"] != 1:
        raise VoiceRuntimeRestoreError("invalid runtime redo schema")
    for k in ("parent_dev", "parent_ino"):
        if type(record[k]) is not int or record[k] < 0:
            raise VoiceRuntimeRestoreError("invalid runtime redo parent")
    for k in ("cutover_check", "candidate_sha256", "previous_sha256", "checksum"):
        s = record[k]
        if not isinstance(s, str) or len(s) != 64 or not set(s) <= HEX:
            raise VoiceRuntimeRestoreError("invalid runtime redo digest")
    for k in ("active_name", "ready_name", "retired_name"):
        name = record[k]
        if not isinstance(name, str) or not name or name in (".", "..") or \
           "/" in name or "\x00" in name or len(name) > 200:
            raise VoiceRuntimeRestoreError("unsafe runtime redo path")
    if len({record[k] for k in ("active_name","ready_name","retired_name")}) != 3:
        raise VoiceRuntimeRestoreError("runtime redo paths overlap")
    if record["checksum"] != _digest({k:v for k,v in record.items()
                                      if k != "checksum"}):
        raise VoiceRuntimeRestoreError("runtime redo checksum mismatch")
    return record


def _read_redo(root: Path) -> dict | None:
    _private_dir(root)
    try:
        fd = os.open(root / REDO, os.O_RDONLY |
                     getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or \
           info.st_uid != os.geteuid() or info.st_mode & 0o077 or \
           info.st_size > MAX_REDO:
            raise VoiceRuntimeRestoreError("unsafe runtime redo file")
        data = stream.read(MAX_REDO + 1)
    if len(data) > MAX_REDO:
        raise VoiceRuntimeRestoreError("runtime redo exceeds size bound")
    try:
        return _validate(json.loads(data))
    except (ValueError, UnicodeError) as exc:
        raise VoiceRuntimeRestoreError("corrupt runtime redo") from exc


def _arm(root: Path, data: dict) -> dict:
    data = _validate(data)
    existing = _read_redo(root)
    if existing is not None:
        if existing != data:
            raise VoiceRuntimeRestoreError("runtime redo belongs to another cutover")
        return existing
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":"))+"\n").encode()
    if len(raw) > MAX_REDO:
        raise VoiceRuntimeRestoreError("oversized runtime redo")
    fd = os.open(root / REDO, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            fd = -1
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    _sync_dir(root)
    if _read_redo(root) != data:
        raise VoiceRuntimeRestoreError("runtime redo was not published")
    return data


def _safe_parent(parent: Path) -> os.stat_result:
    a = os.lstat(parent)
    if not stat.S_ISDIR(a.st_mode) or a.st_uid != os.geteuid() or \
       a.st_mode & 0o022:
        raise VoiceRuntimeRestoreError("unsafe writable runtime parent directory")
    return a


def _fingerprint(config: Path, root: Path, backup: Path,
                 *, must_match_previous_modes: bool = True) -> str:
    return observe_live_files(
        config, root, previous_backup=(backup if must_match_previous_modes else None)
    )["runtime"]


def _stage_old_tree(image: Path, backup: Path, staging: Path,
                    expected_sha: str) -> None:
    """Publish a verified old tree on the SAME filesystem as runtime-v2."""
    old = inspect_previous(backup)
    if old["schema"] != 2:
        raise VoiceRuntimeRestoreError("root mode missing from old runtime snapshot")
    if staging.exists() or staging.is_symlink():
        raise VoiceRuntimeRestoreError("foreign runtime ready path exists")
    parent = staging.parent
    temporary = Path(tempfile.mkdtemp(prefix=".voice-runtime-copy-", dir=parent))
    try:
        # The temporary tree is private while incomplete; all reads go
        # through _copy_regular's O_NOFOLLOW pinned regular-file descriptors.
        os.chmod(temporary, 0o700)
        source = image / "runtime"
        for here, folders, files in os.walk(source, topdown=True,
                                             followlinks=False):
            current = Path(here)
            rel = current.relative_to(source)
            target = temporary / rel
            for name in folders:
                item = current / name
                key = (rel / name).as_posix()+"/"
                info = os.lstat(item)
                if not stat.S_ISDIR(info.st_mode) or \
                   old["runtime"].get(key, {}).get("type") != "dir":
                    raise VoiceRuntimeRestoreError("linked/unexpected runtime directory")
                (target / name).mkdir(mode=0o700)
            for name in files:
                item = current / name
                key = (rel / name).as_posix()
                row = old["runtime"].get(key)
                if row is None or row.get("type") != "file":
                    raise VoiceRuntimeRestoreError("unexpected runtime payload")
                info = _regular(item)
                digest, size = _copy_regular(item, target / name, info)
                if (digest, size) != (row["sha256"], row["bytes"]):
                    raise VoiceRuntimeRestoreError("runtime image file differs")
        for name,row in old["runtime"].items():
            if row["type"] == "file":
                _restore_mode(temporary / name, row["mode"])
        folders = sorted(
            ((name,row) for name,row in old["runtime"].items()
             if row["type"]=="dir"),
            key=lambda entry: len(Path(entry[0]).parts),reverse=True,
        )
        for name,row in folders:
            _restore_mode(temporary / name.rstrip("/"), row["mode"],
                          directory=True)
        _restore_mode(temporary, old["runtime_root_mode"], directory=True)
        if _fingerprint(image / "config.xml", temporary, backup) != expected_sha:
            raise VoiceRuntimeRestoreError("prepared runtime fingerprint mismatch")
        for here,dirs,files in os.walk(temporary,topdown=False):
            _sync_dir(Path(here))
        if staging.exists() or staging.is_symlink():
            raise VoiceRuntimeRestoreError("runtime ready directory appeared")
        os.rename(temporary, staging)
        _sync_dir(parent)
    finally:
        if temporary.exists():
            # Deliberately fail closed instead of deleting a possibly
            # permission-inaccessible incomplete tree at a live path.
            # The empty/incomplete temporary never becomes active.
            import shutil
            shutil.rmtree(temporary)


def restore_previous_runtime(
    active: Path, install_image: Path, previous_backup: Path,
    journal: VoiceCutoverJournal, *, require_lifecycle_owner: Callable[[], None],
    expected_candidate_runtime_sha256: str,
) -> str:
    """Perform and resume a two-rename runtime rollback with durable redo.

    The caller must independently certify expected_candidate_runtime_sha256
    against the exact running candidate under BOTH locks. This isolated
    helper cannot itself prove process/IPFW state or own native locks.
    """
    if not callable(require_lifecycle_owner) or \
       not isinstance(expected_candidate_runtime_sha256, str) or \
       len(expected_candidate_runtime_sha256) != 64 or \
       not set(expected_candidate_runtime_sha256) <= HEX:
        raise VoiceRuntimeRestoreError("trusted active runtime proof/lock required")
    require_lifecycle_owner()
    record = journal.read()
    if record is None or record["phase"] != "mutating" or record["schema"] < 2:
        raise VoiceRuntimeRestoreError("no mutating whole Voice cutover")
    previous_backup, install_image = Path(previous_backup), Path(install_image)
    sealed = bound_resource_fingerprints(previous_backup, record["previous"])
    previous_sha = sealed["runtime"]
    if observe_live_files(install_image/"config.xml", install_image/"runtime",
                          previous_backup=previous_backup) != sealed:
        raise VoiceRuntimeRestoreError("install image changed from sealed previous")
    active = Path(active)
    parent_info = _safe_parent(active.parent)
    suffix = record["check"][:20]
    ready = active.with_name(".voice-restore-ready-"+suffix)
    retired = active.with_name(".voice-restore-retired-"+suffix)
    fields = {
        "schema": 1, "cutover_check": record["check"],
        "parent_dev": parent_info.st_dev, "parent_ino": parent_info.st_ino,
        "active_name": active.name,
        "candidate_sha256": expected_candidate_runtime_sha256,
        "previous_sha256": previous_sha,
        "ready_name": ready.name, "retired_name": retired.name,
    }
    expected_redo = _record(fields)
    marker = _read_redo(journal.directory)
    if marker is not None and marker != expected_redo:
        raise VoiceRuntimeRestoreError("runtime redo does not match this transaction")

    def verify(path: Path, sha: str) -> bool:
        if path.is_symlink():
            raise VoiceRuntimeRestoreError("linked runtime directory forbidden")
        if not path.exists():
            return False
        return _fingerprint(
            install_image/"config.xml", path, previous_backup,
            must_match_previous_modes=(sha == previous_sha)
        ) == sha

    def check_owner() -> None:
        require_lifecycle_owner()
        if journal.read() != record:
            raise VoiceRuntimeRestoreError("whole Voice journal changed")
        info = _safe_parent(active.parent)
        if (info.st_dev, info.st_ino) != (parent_info.st_dev, parent_info.st_ino):
            raise VoiceRuntimeRestoreError("active runtime parent changed")
        if _read_redo(journal.directory) != expected_redo:
            raise VoiceRuntimeRestoreError("runtime redo disappeared/changed")

    if marker is None:
        if ready.exists() or ready.is_symlink() or \
           retired.exists() or retired.is_symlink():
            raise VoiceRuntimeRestoreError("unowned runtime restore paths exist")
        if verify(active, previous_sha):
            return "already-previous-runtime"
        if not verify(active, expected_candidate_runtime_sha256):
            raise VoiceRuntimeRestoreError("foreign or missing active runtime")
        _stage_old_tree(install_image, previous_backup, ready, previous_sha)
        if not verify(ready, previous_sha):
            raise VoiceRuntimeRestoreError("ready runtime failed verification")
        # Publish redo before FIRST live rename. A crash before arm leaves
        # live active candidate untouched and a clearly unowned ready tree.
        _arm(journal.directory, expected_redo)
    check_owner()

    # Crash state 1: old active was renamed to retired; active is absent.
    if not retired.exists() and not retired.is_symlink():
        if not verify(active, expected_candidate_runtime_sha256) or \
           not verify(ready, previous_sha):
            raise VoiceRuntimeRestoreError("unexpected runtime before first rename")
        check_owner()
        if retired.exists() or retired.is_symlink():
            raise VoiceRuntimeRestoreError("foreign retired runtime path appeared")
        os.rename(active, retired)
        _sync_dir(active.parent)
        check_owner()

    if not verify(retired, expected_candidate_runtime_sha256):
        raise VoiceRuntimeRestoreError("retired candidate runtime differs")

    # Crash state 2: after active->retired, the active path is missing.
    if not active.exists() and not active.is_symlink():
        if not verify(ready, previous_sha):
            raise VoiceRuntimeRestoreError("previous ready runtime missing")
        check_owner()
        os.rename(ready, active)
        _sync_dir(active.parent)
        check_owner()

    # Crash state 3: verified old tree active, candidate still saved.
    if ready.exists() or ready.is_symlink() or \
       not verify(active, previous_sha) or \
       not verify(retired, expected_candidate_runtime_sha256):
        raise VoiceRuntimeRestoreError("runtime cutover cannot be certified")
    check_owner()
    # Do NOT clear marker or retired candidate until the WHOLE system
    # rollback is independently verified (Config/dvtws2/IPFW/supervisor).
    return "previous-runtime-restored"
