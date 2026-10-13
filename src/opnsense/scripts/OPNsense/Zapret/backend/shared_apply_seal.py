#!/usr/bin/env python3
"""Seal the ONE detached Config/plan/release bundle before shared FD9 Apply.

This is an integrity witness within the existing shared-work operation, NOT
another transaction log, persistence owner, or runtime service. Production CLI
accepts only one operation ID and requires the original FreeBSD root FD9.

A sealed bundle cannot be altered/reused unnoticed between candidate build,
runtime activation and native Config save. Unknown files, symlinks, hardlinks,
foreign owners, nonregular objects and interrupted seal writes fail closed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys

from shared_apply_operation import _secure, SharedOperationError

WORK = Path("/var/db/zapret2/shared-work")
ID = re.compile(r"^[a-f0-9]{32}$")
SEAL = "bundle-seal.json"
TMP = ".bundle-seal.pending"
FILES = {"candidate.xml": 16 * 1024 * 1024, "plan.json": 4 * 1024 * 1024}
MAX_FILES = 4096
MAX_BYTES = 256 * 1024 * 1024


class SharedBundleError(RuntimeError):
    pass


def _stat(path: Path, owner: int, directory: bool = False) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise SharedBundleError("missing shared bundle resource") from exc
    valid = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not valid or info.st_uid != owner or info.st_mode & 0o022 or (
        not directory and info.st_nlink != 1
    ):
        raise SharedBundleError("untrusted shared bundle owner, type or mode")
    return info


def _hash_file(path: Path, owner: int, maximum: int) -> str:
    info = _stat(path, owner)
    if info.st_size > maximum:
        raise SharedBundleError("shared bundle file size exceeded")
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        pinned = os.fstat(fd)
        if (pinned.st_dev, pinned.st_ino, pinned.st_size) != (
            info.st_dev, info.st_ino, info.st_size
        ):
            raise SharedBundleError("shared bundle file replaced during read")
        remaining = maximum + 1
        while True:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            if remaining <= 0:
                raise SharedBundleError("shared bundle file grew during read")
            digest.update(chunk)
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
            pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns
        ):
            raise SharedBundleError("shared bundle changed during hashing")
    finally:
        os.close(fd)
    return digest.hexdigest()


def _release_hash(release: Path, owner: int) -> str:
    _stat(release, owner, directory=True)
    count, total = 0, 0
    proof = hashlib.sha256()
    # Strict traversal: no symlinks, special files or path escape possible.
    for root, dirs, files in os.walk(release, topdown=True, followlinks=False):
        path = Path(root)
        _stat(path, owner, directory=True)
        dirs.sort()
        files.sort()
        for directory in dirs:
            child = path / directory
            _stat(child, owner, directory=True)
            name = child.relative_to(release).as_posix()
            proof.update(("D\0" + name + "\n").encode())
            count += 1
        for filename in files:
            child = path / filename
            info = _stat(child, owner)
            count += 1
            total += info.st_size
            if count > MAX_FILES or total > MAX_BYTES:
                raise SharedBundleError("shared release exceeds bounded inventory")
            name = child.relative_to(release).as_posix()
            sha = _hash_file(child, owner, MAX_BYTES)
            proof.update(("F\0" + name + "\0" + sha + "\n").encode())
    if count == 0:
        raise SharedBundleError("empty shared candidate release")
    return proof.hexdigest()


def fingerprint(work: Path, *, owner: int | None = None) -> dict:
    owner = os.geteuid() if owner is None else owner
    work = Path(work)
    if not ID.fullmatch(work.name):
        raise SharedBundleError("invalid shared work operation ID")
    _stat(work.parent, owner, directory=True)
    _stat(work, owner, directory=True)
    hashes = {name: _hash_file(work / name, owner, limit)
              for name, limit in FILES.items()}
    hashes["release"] = _release_hash(work / "release", owner)
    return {"schema": 1, "id": work.name, "sha256": hashes}


def _check_seal_root(work: Path, owner: int) -> None:
    _stat(work, owner, directory=True)
    if (work / TMP).exists() or (work / TMP).is_symlink():
        raise SharedBundleError("interrupted shared bundle seal must be reviewed")


def create_seal(work: Path, *, owner: int | None = None) -> dict:
    owner = os.geteuid() if owner is None else owner
    _check_seal_root(work, owner)
    if (work / SEAL).exists() or (work / SEAL).is_symlink():
        raise SharedBundleError("shared bundle is already sealed")
    manifest = fingerprint(work, owner=owner)
    raw = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    target = work / TMP
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as writer:
            writer.write(raw)
            writer.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(target, work / SEAL)
    dfd = os.open(work, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                  getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return manifest


def verify_seal(work: Path, *, owner: int | None = None) -> dict:
    owner = os.geteuid() if owner is None else owner
    _check_seal_root(work, owner)
    target = work / SEAL
    if _stat(target, owner).st_size > 1024:
        raise SharedBundleError("oversized shared bundle seal")
    fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        content = os.read(fd, 1025)
    finally:
        os.close(fd)
    if len(content) > 1024:
        raise SharedBundleError("oversized shared bundle seal")
    try:
        observed = json.loads(content)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SharedBundleError("corrupt shared bundle seal") from exc
    expected = fingerprint(work, owner=owner)
    if not isinstance(observed, dict) or set(observed) != set(expected) or \
       not hmac.compare_digest(
           json.dumps(observed, sort_keys=True),
           json.dumps(expected, sort_keys=True)
       ):
        raise SharedBundleError("shared Config/release bundle changed after seal")
    return expected


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("seal", "verify") or \
       not ID.fullmatch(argv[2]):
        return 64
    try:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
        _secure(WORK, directory=True, owner=0)
        work = WORK / argv[2]
        if argv[1] == "seal":
            create_seal(work, owner=0)
        else:
            verify_seal(work, owner=0)
    except (SharedOperationError, SharedBundleError, OSError, ValueError) as exc:
        print("ERROR: shared release integrity refused: " + str(exc),
              file=sys.stderr)
        return 69
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
