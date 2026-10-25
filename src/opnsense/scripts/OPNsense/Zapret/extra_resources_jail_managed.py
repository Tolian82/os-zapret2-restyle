#!/usr/local/bin/python3.13
"""Non-runnable staging of exact NATIVE generated managed target references.

Operate solely on already mapped per-line candidate argv and native compiler
output release/managed. No production runtime directory is read. Native
orchestrator/registry/storage own target generation; this module does NOT
parse saved strategies, resolve runtime-hosted targets or execute the engine.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

from extra_resources_preflight import PreflightError

MANAGED_REFERENCE = "/usr/local/etc/zapret2/runtime-v2/managed/"
OPTIONS = ("--hostlist=", "--ipset=", "--hostlist-exclude=")
NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}\.txt\Z")
MAX_FILES = 32
MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 16 * 1024 * 1024


def stage_native_managed_targets(
    direct_mapped_argv: bytes,
    native_managed_source: Path,
    pinned_reader: Callable[[Path, int], bytes],
) -> tuple[bytes, dict, dict[str, bytes]]:
    """Return (partially relocated args, NON-AUTHORIZING evidence, source bytes).

    The source root MUST be release/managed from the exact original native
    compiler. The caller retains original FD9 + Config locks and reattests
    source bytes after use. Runtime targets outside managed/ are never read.
    """
    if not isinstance(direct_mapped_argv, bytes):
        raise PreflightError("native managed candidate must be bytes")
    try:
        text = direct_mapped_argv.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreflightError("native managed argv is not UTF-8") from exc
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise PreflightError("native managed argv has unsafe delimiters")
    if not callable(pinned_reader):
        raise PreflightError("native managed pinned reader unavailable")
    source = Path(native_managed_source)
    # This is source provenance supplied by the caller's protected native
    # build, not an arbitrary mapping of installed active runtime files.
    if not source.is_absolute() or source.name != "managed":
        raise PreflightError("native managed source directory is not exact")
    rewritten: list[str] = []
    files: dict[str, bytes] = {}
    unresolved = 0
    managed_refs = 0
    total = 0
    for token in text.splitlines():
        if not token:
            raise PreflightError("empty native managed argument")
        option = next((prefix for prefix in OPTIONS if token.startswith(prefix)), None)
        if option is None:
            # Lua and BIN direct references are already in the inert jail
            # tree. Other paths, including future profile options, remain
            # NOT runnable until a separate validated mapping exists.
            if ("/" in token or "@" in token) and not (
                token.startswith("--lua-init=@/upstream/") or
                token.startswith("--blob=") and ":@/upstream/" in token
            ):
                unresolved += 1
            rewritten.append(token)
            continue
        original = token[len(option):]
        if not original.startswith(MANAGED_REFERENCE):
            unresolved += 1
            rewritten.append(token)
            continue
        filename = original[len(MANAGED_REFERENCE):]
        if not NAME.fullmatch(filename):
            raise PreflightError("unsafe native managed filename")
        # Native storage/registry determines the file kind; reject a
        # cross-option target even when a file happens to exist.
        if ((option == "--ipset=" and not filename.startswith("ipset-"))
            or (option == "--hostlist=" and not filename.startswith("hostlist-"))
            or (option == "--hostlist-exclude=" and filename != "hostlist-exclude.txt")):
            raise PreflightError("native managed option/source type mismatch")
        try:
            directory = source.lstat()
        except OSError as exc:
            raise PreflightError("native managed source is absent") from exc
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.geteuid()
                or source.is_symlink()):
            raise PreflightError("native managed source directory is unsafe")
        if filename not in files:
            if len(files) >= MAX_FILES:
                raise PreflightError("native managed file count exceeds limit")
            data = pinned_reader(source / filename, MAX_FILE)
            if not isinstance(data, bytes) or not 0 < len(data) <= MAX_FILE:
                raise PreflightError("native managed resource has invalid bytes")
            total += len(data)
            if total > MAX_TOTAL:
                raise PreflightError("native managed resources exceed size limit")
            files[filename] = data
        rewritten.append(option + "/native-managed/" + filename)
        managed_refs += 1
    if not rewritten:
        raise PreflightError("native managed argv is empty")
    mapped = ("\n".join(rewritten) + "\n").encode("utf-8")
    manifest = [(name, hashlib.sha256(data).hexdigest())
                for name, data in sorted(files.items())]
    return mapped, {
        "state": "native-managed-targets-input-only",
        "managed_file_references": managed_refs,
        "managed_files": len(files),
        "unresolved_path_tokens": unresolved,
        "managed_witness_sha256": hashlib.sha256(
            json.dumps(manifest, separators=(",", ":")).encode("ascii")
        ).hexdigest(),
        "runnable": False,
        "engine_lua_proof": "not-run",
        "compatibility": "unknown",
        "authorized": False,
    }, files
