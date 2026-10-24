#!/usr/local/bin/python3.13
"""Exact Lua/BIN reconciliation planner for the installed Zapret2 Git HEAD.

Read-only. Caller serializes with setup.lock and the native FD9 lifecycle.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from extra_resources_preflight import (
    PreflightError, git_blob_sha, resource_path, sha256, validate_runtime_path,
)

MAX_FILES = 4096
MAX_FILE = 2 * 1024 * 1024


def tracked_resources(root: Path, git_bin: str = "git") -> dict[str, str]:
    if root.is_symlink() or not root.is_dir() or not (root / ".git").exists():
        raise PreflightError("installed Zapret2 Git checkout is missing or unsafe")
    top = subprocess.run([git_bin, "-C", str(root), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, timeout=30, check=False)
    if top.returncode or top.stdout.strip() != str(root.resolve()):
        raise PreflightError("unexpected upstream Git working tree")
    listing = subprocess.run([git_bin, "-C", str(root), "ls-tree", "-r", "-z",
                              "HEAD", "--", "lua", "files/fake"],
                             capture_output=True, timeout=30, check=False)
    if listing.returncode:
        raise PreflightError("cannot inspect installed upstream Git HEAD")
    tracked: dict[str, str] = {}
    for item in listing.stdout.split(b"\0"):
        if not item:
            continue
        try:
            metadata, raw_path = item.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split()
            name = raw_path.decode("utf-8")
        except (UnicodeError, ValueError) as exc:
            raise PreflightError("invalid upstream Git tree entry") from exc
        if not resource_path(name):
            continue
        if mode not in ("100644", "100755") or kind != "blob" or not re.fullmatch(r"[0-9a-f]{40}", oid):
            raise PreflightError(f"unsafe upstream Git resource: {name}")
        if name in tracked or len(tracked) >= MAX_FILES:
            raise PreflightError("duplicate or excessive upstream resources")
        path = validate_runtime_path(root, name)
        if path.is_symlink() or not path.is_file():
            raise PreflightError(f"upstream resource missing or unsafe: {name}")
        data = path.read_bytes()
        if not data or len(data) > MAX_FILE or git_blob_sha(data) != oid:
            raise PreflightError(f"upstream Git-tracked resource changed: {name}")
        tracked[name] = sha256(data)
    return tracked


def installed_resources(root: Path) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for folder, suffix in (("lua", ".lua"), ("files/fake", ".bin")):
        directory = root / folder
        if directory.is_symlink() or not directory.is_dir():
            raise PreflightError(f"unsafe resource directory: {folder}")
        for path in directory.iterdir():
            if path.suffix != suffix:
                continue
            name = f"{folder}/{path.name}"
            if not resource_path(name) or path.is_symlink() or not path.is_file():
                raise PreflightError(f"unsafe current runtime resource: {name}")
            if len(inventory) >= MAX_FILES:
                raise PreflightError("too many runtime resources")
            data = path.read_bytes()
            if not data or len(data) > MAX_FILE:
                raise PreflightError(f"invalid runtime resource size: {name}")
            inventory[name] = sha256(data)
    return inventory


def previous_metadata(path: Path) -> dict[str, str]:
    if path.is_symlink():
        raise PreflightError("managed resource metadata is symlinked")
    if not path.exists():
        return {}
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, ValueError) as exc:
        raise PreflightError("managed resource metadata unreadable") from exc
    if not isinstance(metadata, dict) or metadata.get("schema") != 1 or not isinstance(metadata.get("files"), dict):
        raise PreflightError("invalid managed resource metadata")
    previous = metadata["files"]
    for name, digest in previous.items():
        if not resource_path(name) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PreflightError("unsafe managed metadata entry")
    return previous


def make_plan(payloads: dict[str, bytes], root: Path, managed: Path) -> dict:
    upstream = tracked_resources(root)
    live = installed_resources(root)
    prior = previous_metadata(managed)
    for name, digest in prior.items():
        if name in upstream:
            raise PreflightError(f"previous managed resource is now upstream-owned: {name}")
        if live.get(name) != digest:
            raise PreflightError(f"previously managed resource changed or missing: {name}")
    incoming: dict[str, str] = {}
    for name, data in payloads.items():
        if not resource_path(name) or not isinstance(data, bytes) or not data or len(data) > MAX_FILE:
            raise PreflightError(f"invalid catalog resource: {name}")
        digest = sha256(data)
        if name in upstream:
            if upstream[name] != digest:
                raise PreflightError(f"upstream/additional resource collision: {name}")
            continue  # Identical upstream file, never claim ownership.
        incoming[name] = digest
    foreign = {name: digest for name, digest in live.items() if name not in upstream}
    removed = sorted(set(foreign) - set(incoming))
    if root == Path("/usr/local/etc/zapret2"):
        config = Path("/conf/config.xml")
        if config.is_symlink():
            raise PreflightError("saved configuration is symlinked")
        if config.is_file():
            raw = config.read_bytes()
            for name in removed:
                if name.encode() in raw or name.rsplit("/", 1)[1].encode() in raw:
                    raise PreflightError(f"saved strategy references orphan resource: {name}")
    return {
        "previous": foreign, "incoming": incoming, "upstream": upstream,
        "removed": removed,
        "new": sum(name not in foreign for name in incoming),
        "updated": sum(name in foreign and foreign[name] != digest for name, digest in incoming.items()),
        "unchanged": sum(name in foreign and foreign[name] == digest for name, digest in incoming.items()),
    }


# Remove Additional Resources, Stage 1: bounded READ-ONLY prospective inventory.
# This module deliberately does not decide strategy/Voice compatibility or perform
# any deletion. A future mutating caller MUST hold setup.lock -> native FD9, run
# upstream-only Strategies+Voice validation and re-attest all witnesses under the
# same locks immediately before native Stop.
def _remove_head(root: Path, git_bin: str) -> str:
    try:
        completed = subprocess.run(
            [git_bin, "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError("cannot resolve installed upstream HEAD") from exc
    sha = completed.stdout.strip()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise PreflightError("invalid installed upstream HEAD commit")
    return sha


def _remove_file_attestation(path: Path, limit: int) -> tuple[bytes, dict]:
    """Reject non-regular/symlink files and observable replacement/read races."""
    import os
    import stat

    def identity(s):
        return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
                s.st_size, s.st_mtime_ns, s.st_ctime_ns)

    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise PreflightError(f"unsafe or oversized removal witness: {path}")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                     getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or identity(before) != identity(opened):
                raise PreflightError(f"resource changed during removal planning: {path}")
            body = stream.read(limit + 1)
            closed = os.fstat(stream.fileno())
        after = path.lstat()
    except (OSError, ValueError) as exc:
        raise PreflightError(f"cannot safely attest removal witness: {path}") from exc
    if (len(body) > limit or len(body) != before.st_size or
            identity(before) != identity(closed) or identity(before) != identity(after)):
        raise PreflightError(f"resource changed during removal planning: {path}")
    return body, {
        "sha256": sha256(body), "size": len(body), "mode": stat.S_IMODE(before.st_mode),
        "uid": before.st_uid, "gid": before.st_gid, "mtime_ns": before.st_mtime_ns,
        "dev": before.st_dev, "ino": before.st_ino,
    }


def _remove_directory_witness(root: Path) -> dict[str, tuple]:
    import stat

    witness = {}
    for name in ("", "lua", "files", "files/fake"):
        directory = root / name
        try:
            entry = directory.lstat()
        except OSError as exc:
            raise PreflightError(f"missing resource directory: {name or 'runtime'}") from exc
        if not stat.S_ISDIR(entry.st_mode):
            raise PreflightError(f"unsafe resource directory: {name or 'runtime'}")
        witness[name] = (entry.st_dev, entry.st_ino, entry.st_mode,
                         entry.st_mtime_ns, entry.st_ctime_ns)
    return witness


def make_remove_plan(
    root: Path, managed: Path, config: Path = Path("/conf/config.xml"),
    git_bin: str = "git",
) -> dict:
    """Plan *all* non-HEAD direct Lua/BIN removal, without side effects.

    Caller provides the authoritative setup/native lifecycle locks. This
    intentionally returns compatibility=unknown and authorized=False until
    the future Strategies+Voice and combined-runtime gates are implemented.
    """
    import hashlib
    import json

    directories = _remove_directory_witness(root)
    head = _remove_head(root, git_bin)
    upstream = tracked_resources(root, git_bin)
    actual = installed_resources(root)
    previous = previous_metadata(managed)

    if not config.is_file() or config.is_symlink():
        raise PreflightError("saved OPNsense configuration is missing or unsafe")
    config_raw, config_meta = _remove_file_attestation(config, 64 * 1024 * 1024)

    if managed.is_symlink():
        raise PreflightError("managed resource manifest is symlinked")
    manifest_sha = None
    if previous and not managed.exists():
        raise PreflightError("managed resource manifest disappeared during planning")
    if managed.exists():
        raw, _ = _remove_file_attestation(managed, 4 * 1024 * 1024)
        manifest_sha = sha256(raw)
        # Compare with the manifest decoded by the existing authoritative reader.
        try:
            manifest = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise PreflightError("invalid managed resource manifest") from exc
        if not isinstance(manifest, dict) or manifest.get("files") != previous:
            raise PreflightError("managed resource manifest changed during planning")

    # An installed manifest must describe only extra files, never current HEAD.
    for name, digest in previous.items():
        if name in upstream or actual.get(name) != digest:
            raise PreflightError(f"managed resource ownership differs from disk: {name}")

    stats = {}
    for name, digest in sorted(actual.items()):
        path = validate_runtime_path(root, name)
        body, record = _remove_file_attestation(path, MAX_FILE)
        if not body or record["sha256"] != digest:
            raise PreflightError(f"resource changed during removal planning: {name}")
        if name in upstream and upstream[name] != record["sha256"]:
            raise PreflightError(f"upstream resource changed during removal planning: {name}")
        stats[name] = record

    # A second census and HEAD/dir check detect changes while constructing the
    # digest-bound plan. A later transaction must repeat these checks.
    if (_remove_head(root, git_bin) != head or
            _remove_directory_witness(root) != directories or
            installed_resources(root) != actual or
            tracked_resources(root, git_bin) != upstream):
        raise PreflightError("upstream or runtime inventory changed during removal planning")
    if _remove_file_attestation(config, 64 * 1024 * 1024) != (config_raw, config_meta):
        raise PreflightError("saved configuration changed during removal planning")
    if managed.exists():
        if sha256(_remove_file_attestation(managed, 4 * 1024 * 1024)[0]) != manifest_sha:
            raise PreflightError("managed resource manifest changed during removal planning")
    else:
        if manifest_sha is not None:
            raise PreflightError("managed resource manifest disappeared during planning")

    removed = sorted(set(actual) - set(upstream))
    candidates = [{"path": name, **stats[name]} for name in removed]
    envelope = {
        "upstream_head": head, "upstream": upstream, "installed": actual,
        "managed": previous, "managed_manifest_sha256": manifest_sha,
        "config_sha256": sha256(config_raw),
        "remove": candidates,
    }
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": 1, "operation": "remove", "status": "dry_run_only",
        "compatibility": "unknown", "authorized": False,
        "upstream_head": head, "upstream": upstream, "installed": actual,
        "remove": candidates,
        "counts": {
            "lua": sum(name.startswith("lua/") for name in removed),
            "bin": sum(name.startswith("files/fake/") for name in removed),
            "total": len(removed),
        },
        "witness": {
            "config_sha256": envelope["config_sha256"],
            "managed_manifest_sha256": manifest_sha,
            "inventory_sha256": hashlib.sha256(canonical).hexdigest(),
        },
    }
