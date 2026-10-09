#!/usr/bin/env python3
"""Private pre-cutover Config/runtime backup (staging only, no live mutations).

A durable cutover journal containing only hashes cannot restore config.xml or
a runtime tree after reboot. This isolated helper captures both into a
write-once, fsync'd 0700 directory, with a checksum manifest and all saved
bytes held as regular 0600 files. It has no CLI or production call site.

Caller MUST hold native Config+lifecycle locks and separately verify the
engine, supervisor, IPFW state and absence/adoption of legacy PoC. A future
restoration adapter MUST independently validate this snapshot before restoring
anything and must restore original modes/ownership as appropriate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

MAX_FILES = 20000
MAX_BYTES = 512 * 1024 * 1024
MAX_MANIFEST = 4 * 1024 * 1024
CHUNK = 1024 * 1024


class VoiceBackupError(ValueError):
    pass


def _private_dir(path: Path) -> None:
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or \
       (info.st_mode & 0o077):
        raise VoiceBackupError("Voice backup directory must be owner-private")


def _regular(path: Path) -> os.stat_result:
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise VoiceBackupError("Voice backup source must be a real regular file")
    return info


def _copy_regular(source: Path, dest: Path, info: os.stat_result) -> tuple[str, int]:
    if info.st_size > MAX_BYTES:
        raise VoiceBackupError("Voice backup source exceeds configured bound")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    input_fd = os.open(source, flags)
    try:
        start = os.fstat(input_fd)
        if not stat.S_ISREG(start.st_mode) or start.st_ino != info.st_ino or \
           start.st_dev != info.st_dev or start.st_nlink != 1:
            raise VoiceBackupError("Voice backup source changed during open")
        dest_fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(dest_fd, "wb") as output:
                dest_fd = -1
                while True:
                    chunk = os.read(input_fd, CHUNK)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise VoiceBackupError("Voice backup source too large")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            finish = os.fstat(input_fd)
            if size != info.st_size or start.st_size != finish.st_size or \
               start.st_mtime_ns != finish.st_mtime_ns or \
               start.st_ctime_ns != finish.st_ctime_ns:
                raise VoiceBackupError("Voice backup source changed during copy")
            return digest.hexdigest(), size
        finally:
            if dest_fd != -1:
                os.close(dest_fd)
    finally:
        os.close(input_fd)


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _tree(source: Path, destination: Path) -> tuple[dict, int]:
    if source.is_symlink() or not source.is_dir():
        raise VoiceBackupError("Voice runtime source must be a real directory")
    result = {}
    total_bytes = 0
    count = 0
    for here, folders, files in os.walk(source, topdown=True, followlinks=False):
        current = Path(here)
        if current.is_symlink():
            raise VoiceBackupError("runtime tree directory symlink forbidden")
        relative = current.relative_to(source)
        target = destination / relative
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        _sync_dir(target)
        for name in sorted(folders + files):
            item = current / name
            rel = item.relative_to(source).as_posix()
            if not name or name in (".", "..") or rel.startswith("/") or ".." in Path(rel).parts:
                raise VoiceBackupError("unsafe Voice runtime path")
            info = os.lstat(item)
            if stat.S_ISLNK(info.st_mode) or (not stat.S_ISDIR(info.st_mode) and
                                              not stat.S_ISREG(info.st_mode)):
                raise VoiceBackupError("Voice runtime contains symlink or special file")
            if stat.S_ISDIR(info.st_mode):
                result[rel + "/"] = {"type": "dir", "mode": stat.S_IMODE(info.st_mode)}
                continue
            count += 1
            if count > MAX_FILES or total_bytes + info.st_size > MAX_BYTES:
                raise VoiceBackupError("Voice runtime snapshot bounds exceeded")
            dst = target / name
            sha, length = _copy_regular(item, dst, info)
            total_bytes += length
            result[rel] = {"type": "file", "mode": stat.S_IMODE(info.st_mode),
                           "sha256": sha, "bytes": length}
        _sync_dir(target)
    return result, total_bytes


def _live_sha(path: Path) -> tuple[str, int, int]:
    info = _regular(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        start = os.fstat(fd)
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = os.read(fd, CHUNK)
            if not chunk:
                break
            count += len(chunk)
            if count > MAX_BYTES:
                raise VoiceBackupError("Voice live source exceeds configured bound")
            digest.update(chunk)
        finish = os.fstat(fd)
        if start.st_ino != info.st_ino or start.st_dev != info.st_dev or \
           start.st_size != finish.st_size or start.st_mtime_ns != finish.st_mtime_ns or \
           start.st_ctime_ns != finish.st_ctime_ns or count != start.st_size:
            raise VoiceBackupError("Voice live source changed during verification")
        return digest.hexdigest(), count, stat.S_IMODE(start.st_mode)
    finally:
        os.close(fd)


def _verify_sources(config: Path, runtime: Path, manifest: dict) -> None:
    config_row = manifest["config"]
    if _live_sha(config) != (config_row["sha256"], config_row["bytes"], config_row["mode"]):
        raise VoiceBackupError("Voice Config changed while building previous-state backup")
    entries = manifest["runtime"]
    actual = set()
    for here, folders, files in os.walk(runtime, topdown=True, followlinks=False):
        current = Path(here)
        if current.is_symlink():
            raise VoiceBackupError("Voice runtime directory changed to symlink")
        for name in folders + files:
            item = current / name
            info = os.lstat(item)
            rel = item.relative_to(runtime).as_posix()
            key = rel + "/" if stat.S_ISDIR(info.st_mode) else rel
            if key not in entries:
                raise VoiceBackupError("Voice runtime changed after snapshot")
            actual.add(key)
            record = entries[key]
            if stat.S_ISDIR(info.st_mode):
                if record != {"type": "dir", "mode": stat.S_IMODE(info.st_mode)}:
                    raise VoiceBackupError("Voice runtime directory changed")
            elif stat.S_ISREG(info.st_mode):
                if record.get("type") != "file" or _live_sha(item) != (
                    record["sha256"], record["bytes"], record["mode"]
                ):
                    raise VoiceBackupError("Voice runtime file changed after snapshot")
            else:
                raise VoiceBackupError("Voice runtime contains an unsafe changed entry")
    if actual != set(entries):
        raise VoiceBackupError("Voice runtime entries changed while snapshotting")


def capture_previous(config: Path, runtime: Path, output: Path) -> dict:
    """Create one immutable, durable private backup; never overwrite output."""
    config, runtime, output = Path(config), Path(runtime), Path(output)
    _regular(config)
    if runtime.is_symlink() or not runtime.is_dir():
        raise VoiceBackupError("Voice runtime source missing or unsafe")
    parent = output.parent
    _private_dir(parent)
    if output.exists() or output.is_symlink():
        raise VoiceBackupError("Voice previous snapshot already exists")
    temporary = Path(tempfile.mkdtemp(prefix=".voice-backup-", dir=parent))
    try:
        os.chmod(temporary, 0o700)
        config_dir = temporary / "config"
        runtime_dir = temporary / "runtime"
        config_dir.mkdir(mode=0o700)
        runtime_dir.mkdir(mode=0o700)
        info = _regular(config)
        sha, length = _copy_regular(config, config_dir / "config.xml", info)
        entries, total = _tree(runtime, runtime_dir)
        manifest = {
            "schema": 1, "config": {"sha256": sha, "bytes": length,
                                      "mode": stat.S_IMODE(info.st_mode)},
            "runtime": entries,
            "runtime_bytes": total,
        }
        # Re-read live sources after the full copy, before publishing the
        # snapshot. The future live adapter must STILL hold both locks and
        # compare this immutable snapshot with its pinned preflight proof.
        _verify_sources(config, runtime, manifest)
        encoded = (json.dumps(manifest, sort_keys=True, separators=(",", ":"))+"\n").encode("utf-8")
        if len(encoded) > MAX_MANIFEST:
            raise VoiceBackupError("Voice previous snapshot manifest too large")
        with (temporary / "manifest.json").open("xb") as handle:
            os.chmod(temporary / "manifest.json", 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # A separate content seal detects torn/accidentally modified
        # manifests independently of the per-file backup hashes.
        seal = (hashlib.sha256(encoded).hexdigest() + "\n").encode("ascii")
        with (temporary / "manifest.sha256").open("xb") as handle:
            os.chmod(temporary / "manifest.sha256", 0o600)
            handle.write(seal)
            handle.flush()
            os.fsync(handle.fileno())
        _sync_dir(config_dir)
        _sync_dir(runtime_dir)
        _sync_dir(temporary)
        # Do not publish an incomplete backup; same-parent rename is atomic.
        os.rename(temporary, output)
        _sync_dir(parent)
        return manifest
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _read_private_file(path: Path, limit: int) -> bytes:
    # O_NOFOLLOW protects the actual open, not just a prior lstat.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or \
           info.st_uid != os.geteuid() or info.st_mode & 0o077 or \
           info.st_size > limit:
            raise VoiceBackupError("Voice backup metadata is not private and regular")
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(fd, min(CHUNK, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > limit:
            raise VoiceBackupError("Voice backup metadata too large")
        return bytes(data)
    finally:
        os.close(fd)


def _verify_file(file: Path, row: dict) -> None:
    info = _regular(file)
    if not isinstance(row, dict) or set(row) != {"sha256", "bytes", "mode"} and \
       set(row) != {"type", "sha256", "bytes", "mode"}:
        raise VoiceBackupError("malformed Voice backup manifest record")
    if info.st_size != row["bytes"] or not isinstance(row["bytes"], int):
        raise VoiceBackupError("Voice backup file size mismatch")
    if not isinstance(row["sha256"], str) or len(row["sha256"]) != 64:
        raise VoiceBackupError("Voice backup file digest invalid")
    sha = hashlib.sha256()
    with file.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(CHUNK), b""):
            sha.update(chunk)
    if sha.hexdigest() != row["sha256"]:
        raise VoiceBackupError("Voice backup file digest mismatch")
    if info.st_mode & 0o077:
        raise VoiceBackupError("Voice backup file is not private")


def inspect_previous(output: Path) -> dict:
    """Read-only verification; fail on extra, symlink, missing or changed files."""
    output = Path(output)
    _private_dir(output.parent)
    _private_dir(output)
    raw_manifest = _read_private_file(output / "manifest.json", MAX_MANIFEST)
    raw_seal = _read_private_file(output / "manifest.sha256", 65)
    expected_seal = (hashlib.sha256(raw_manifest).hexdigest() + "\n").encode("ascii")
    if raw_seal != expected_seal:
        raise VoiceBackupError("Voice backup manifest checksum mismatch")
    try:
        manifest = json.loads(raw_manifest)
    except (ValueError, UnicodeError) as e:
        raise VoiceBackupError("invalid Voice backup manifest") from e
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema", "config", "runtime", "runtime_bytes"
    } or manifest["schema"] != 1 or not isinstance(manifest["runtime"], dict):
        raise VoiceBackupError("invalid Voice backup schema")
    _verify_file(output / "config/config.xml", manifest["config"])
    declared = set(manifest["runtime"])
    actual = set()
    actual_bytes = 0
    base = output / "runtime"
    if base.is_symlink() or not base.is_dir():
        raise VoiceBackupError("Voice backup runtime folder missing or unsafe")
    for here, dirs, files in os.walk(base, topdown=True, followlinks=False):
        parent = Path(here)
        _private_dir(parent)
        for name in dirs + files:
            item = parent / name
            rel = item.relative_to(base).as_posix()
            info = os.lstat(item)
            key = rel + "/" if stat.S_ISDIR(info.st_mode) else rel
            actual.add(key)
            if key not in declared:
                raise VoiceBackupError("unexpected Voice backup runtime entry")
            row = manifest["runtime"][key]
            if stat.S_ISDIR(info.st_mode):
                _private_dir(item)
                if row.get("type") != "dir":
                    raise VoiceBackupError("runtime directory manifest differs")
            elif stat.S_ISREG(info.st_mode):
                _verify_file(item, row)
                actual_bytes += info.st_size
            else:
                raise VoiceBackupError("Voice backup runtime contains unsafe entry")
    if declared != actual:
        raise VoiceBackupError("Voice backup has missing runtime entries")
    if type(manifest["runtime_bytes"]) is not int or \
       actual_bytes != manifest["runtime_bytes"]:
        raise VoiceBackupError("Voice backup runtime total size mismatch")
    # Forbid unexpected files outside the strict storage layout.
    if sorted(p.name for p in output.iterdir()) != \
       ["config", "manifest.json", "manifest.sha256", "runtime"] or \
       sorted(p.name for p in (output / "config").iterdir()) != ["config.xml"]:
        raise VoiceBackupError("Voice backup contains unknown payloads")
    return manifest


def bound_resource_fingerprints(output: Path, previous: dict | None = None) -> dict:
    """Bind real previous Config/runtime bytes to the whole-cutover journal.

    The journal also requires independently verified engine, supervisor and
    owned-IPFW fingerprints. This only attests the two resource types for
    which this snapshot has restorable bytes. It never mutates anything.
    """
    verified = inspect_previous(output)
    config_sha = verified["config"]["sha256"]
    runtime_content = {
        "entries": verified["runtime"],
        "total_bytes": verified["runtime_bytes"],
    }
    runtime_sha = hashlib.sha256(json.dumps(
        runtime_content, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()
    result = {"config": config_sha, "runtime": runtime_sha}
    if previous is not None:
        if not isinstance(previous, dict) or any(
            previous.get(name) != result[name] for name in result
        ):
            raise VoiceBackupError("previous Config/runtime journal fingerprint mismatch")
    return result
