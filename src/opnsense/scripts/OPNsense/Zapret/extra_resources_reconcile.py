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


def tracked_resources(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir() or not (root / ".git").exists():
        raise PreflightError("installed Zapret2 Git checkout is missing or unsafe")
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, timeout=30, check=False)
    if top.returncode or top.stdout.strip() != str(root.resolve()):
        raise PreflightError("unexpected upstream Git working tree")
    listing = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "-z",
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
