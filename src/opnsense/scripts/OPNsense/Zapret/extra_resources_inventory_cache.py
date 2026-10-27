#!/usr/local/bin/python3.13
"""Cached, provenance-aware inventory for the Strategies full-help panel.

Refresh ONLY after a native resource/upstream transaction. The GUI read command
only reads a bounded JSON file; it never scans the runtime or invokes Git.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys

from extra_resources_reconcile import installed_resources, previous_metadata, tracked_resources

RUNTIME = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle/extra-resources")
CACHE_NAME = "inventory-cache.json"
MAX_CACHE_SIZE = 1024 * 1024
NAME = re.compile(r"^(?:lua/[A-Za-z0-9_.+-]+\.lua|files/fake/[A-Za-z0-9_.+-]+\.bin)$")


class InventoryCacheError(RuntimeError):
    pass


def generate(root: Path, state: Path) -> dict:
    """Snapshot actual safe on-disk files and installed Git HEAD provenance."""
    tracked = tracked_resources(root)
    actual = installed_resources(root)
    manifest = state / "installed.json"
    managed = previous_metadata(manifest)
    for name, digest in managed.items():
        if actual.get(name) != digest:
            raise InventoryCacheError("managed resource inventory differs from installed files")
    items = {"lua": [], "bin": []}
    for name in sorted(actual):
        if NAME.fullmatch(name) is None:
            raise InventoryCacheError("unsafe resource basename in inventory")
        kind = "lua" if name.startswith("lua/") else "bin"
        items[kind].append({
            "name": name.rsplit("/", 1)[-1],
            "origin": "upstream" if name in tracked else "other",
        })
    return {"schema": 1, "installed": manifest.is_file(), **items}


def publish(data: dict, state: Path) -> None:
    if state.is_symlink() or not state.is_dir():
        raise InventoryCacheError("unsafe extra-resource state directory")
    target = state / CACHE_NAME
    staging = state / (CACHE_NAME + ".new")
    if target.is_symlink() or staging.exists() or staging.is_symlink():
        raise InventoryCacheError("unsafe inventory cache destination")
    raw = (json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
    if len(raw) > MAX_CACHE_SIZE:
        raise InventoryCacheError("resource cache exceeds size limit")
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staging, 0o644)
        os.replace(staging, target)
        directory_fd = os.open(state, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if staging.exists():
            staging.unlink()


def invalidate(state: Path) -> None:
    """Durably retire old Help cache before actual resource-set mutation."""
    if state.is_symlink() or not state.is_dir():
        raise InventoryCacheError("unsafe extra-resource state directory")
    cache = state / CACHE_NAME
    if cache.is_symlink() or (cache.exists() and not cache.is_file()):
        raise InventoryCacheError("unsafe inventory cache destination")
    if cache.is_file():
        cache.unlink()
        directory_fd = os.open(state, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


def read_cached(state: Path) -> dict:
    """No filesystem inventory or git access here: bounded cache read only."""
    path = state / CACHE_NAME
    if state.is_symlink() or path.is_symlink() or not path.is_file():
        raise InventoryCacheError("cache unavailable")
    with path.open("rb") as stream:
        raw = stream.read(MAX_CACHE_SIZE + 1)
    if len(raw) > MAX_CACHE_SIZE:
        raise InventoryCacheError("oversized inventory cache")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("schema") != 1 or type(data.get("installed")) is not bool:
            raise ValueError("invalid cache header")
        for key, suffix in (("lua", ".lua"), ("bin", ".bin")):
            values = data.get(key)
            if not isinstance(values, list) or len(values) > 4096:
                raise ValueError("invalid resource array")
            if any(not isinstance(x, dict) or x.get("origin") not in ("upstream", "other")
                   or not isinstance(x.get("name"), str) or
                   len(x["name"]) > 255 or NAME.fullmatch(
                       ("lua/" if key == "lua" else "files/fake/") + x["name"]
                   ) is None or not x["name"].endswith(suffix)
                   for x in values):
                raise ValueError("invalid resource entry")
        return {"status": "ok", "installed": data["installed"],
                "lua": data["lua"], "bin": data["bin"]}
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise InventoryCacheError("invalid inventory cache") from exc


def refresh(root: Path = RUNTIME, state: Path = STATE) -> dict:
    data = generate(root, state)
    publish(data, state)
    return data


def main(args: list[str]) -> int:
    if len(args) != 2 or args[1] not in {"refresh", "show"}:
        print("usage: extra_resources_inventory_cache.py {refresh|show}", file=sys.stderr)
        return 64
    try:
        if args[1] == "refresh":
            refresh()
            print("OK")
        else:
            print(json.dumps(read_cached(STATE), separators=(",", ":"), ensure_ascii=False))
        return 0
    except (InventoryCacheError, OSError, ValueError) as exc:
        if args[1] == "show":
            print('{"status":"unavailable"}')
        else:
            print(f"INVENTORY_CACHE_UNAVAILABLE: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
