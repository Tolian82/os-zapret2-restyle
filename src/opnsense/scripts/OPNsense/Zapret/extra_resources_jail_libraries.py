#!/usr/local/bin/python3.13
"""Static, bounded DT_NEEDED graph of exact engine and explicit shared libraries.

Reuses the existing FreeBSD ELF reader: no ldd, dlopen, loader or dvtws2 run.
PT_INTERP, RPATH, dlopen, symbol resolution and Lua exports remain UNKNOWN.
This input evidence cannot authorize resource deletion.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from extra_resources_engine_abi import _needed_libraries, EngineABIError
from extra_resources_preflight import PreflightError

MAX_LIBRARIES = 48
MAX_LIBRARY_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 96 * 1024 * 1024
SEARCH_DIRS = ("lib", "usr/lib", "usr/local/lib")
SONAME = re.compile(r"lib[A-Za-z0-9_+.-]{1,128}\.so(?:\.[0-9]+)*\Z")


def _trusted_dir(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise PreflightError("library source directory unavailable") from exc
    if (not stat.S_ISDIR(info.st_mode) or path.is_symlink()
            or info.st_uid != os.geteuid() or info.st_mode & 0o022):
        raise PreflightError("unsafe explicit library source directory")


def _read_named(root: Path, name: str,
                reader: Callable[[Path, int], bytes]) -> tuple[str, bytes]:
    if not SONAME.fullmatch(name) or ".." in name:
        raise PreflightError("unsafe DT_NEEDED library name")
    matches: list[tuple[str, Path]] = []
    for directory in SEARCH_DIRS:
        path = root / directory
        parts = Path(directory).parts
        for n in range(1, len(parts) + 1):
            intermediate = root.joinpath(*parts[:n])
            if intermediate.is_symlink():
                raise PreflightError("linked library directory")
        if not path.exists():
            continue
        _trusted_dir(path)
        candidate = path / name
        if candidate.is_symlink():
            raise PreflightError("linked DT_NEEDED library is not attested")
        if candidate.exists():
            matches.append((directory + "/" + name, candidate))
    if len(matches) != 1:
        raise PreflightError("DT_NEEDED library missing or ambiguous")
    relative, candidate = matches[0]
    try:
        info = candidate.lstat()
    except OSError as exc:
        raise PreflightError("DT_NEEDED library missing") from exc
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid != os.geteuid() or info.st_mode & 0o022):
        raise PreflightError("unsafe DT_NEEDED library inode")
    data = reader(candidate, MAX_LIBRARY_BYTES)
    if not isinstance(data, bytes) or not 64 <= len(data) <= MAX_LIBRARY_BYTES:
        raise PreflightError("invalid DT_NEEDED library bytes")
    return relative, data


def collect_static_needed_libraries(
    engine_bytes: bytes, library_root: Path,
    pinned_reader: Callable[[Path, int], bytes]
) -> tuple[dict, dict[str, bytes]]:
    """Compute bounded nested DT_NEEDED inputs; NOT a real loader closure.

    library_root is explicitly supplied by a guarded caller, not inferred
    from Config, the engine, environment or host loader state. Caller retains
    original native FD9/Config locks and authenticates that source root.
    """
    root = Path(library_root)
    if not root.is_absolute() or not callable(pinned_reader):
        raise PreflightError("explicit absolute library root/reader required")
    _trusted_dir(root)
    try:
        pending = sorted(set(_needed_libraries(engine_bytes)))
    except EngineABIError as exc:
        raise PreflightError("installed engine ELF graph invalid") from exc
    names: dict[str, str] = {}
    blobs: dict[str, bytes] = {}
    total = 0
    while pending:
        name = pending.pop(0)
        if name in names:
            continue
        if len(names) >= MAX_LIBRARIES:
            raise PreflightError("too many ELF DT_NEEDED libraries")
        path, data = _read_named(root, name, pinned_reader)
        if path in blobs:
            raise PreflightError("duplicate DT_NEEDED library path")
        names[name] = path
        blobs[path] = data
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise PreflightError("oversized DT_NEEDED graph")
        try:
            nested = _needed_libraries(data)
        except EngineABIError as exc:
            raise PreflightError("dependency library ELF invalid") from exc
        for item in nested:
            if item not in names and item not in pending:
                pending.append(item)
        pending.sort()
    rows = [(name, path, hashlib.sha256(blobs[path]).hexdigest())
            for name, path in sorted(names.items())]
    witness = hashlib.sha256(json.dumps(rows, separators=(",", ":"),
                                       ensure_ascii=True).encode("ascii")).hexdigest()
    return {
        "state": "elf-dt-needed-static-graph-input-only",
        "static_needed_libraries": len(names),
        "static_needed_witness_sha256": witness,
        "loader_path_resolution": "unproven",
        "dlopen_dependencies": "unknown",
        "dynamic_library_closure": "unknown",
        "runnable": False,
        "engine_lua_proof": "not-run",
        "compatibility": "unknown",
        "authorized": False,
    }, blobs
