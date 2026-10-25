#!/usr/local/bin/python3.13
"""Fail-closed Lua/BIN file-reference witness for an ORIGINAL native candidate.

Operate on *compiled* dvtws.args, NEVER browser XML or a duplicate Strategies
parser. This attests only direct file references against a private, pinned
upstream-only inventory. Lua execution, exported function existence and
indirect/transitive dependencies are ALWAYS UNPROVEN. The output cannot
authorize resource removal; no interpreter or dvtws2 is executed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

from extra_resources_preflight import PreflightError

MAX_ARGS = 4 * 1024 * 1024
MAX_TOKENS = 20000
MAX_RESOURCE = 4 * 1024 * 1024
NAME = re.compile(r"[A-Za-z0-9_.-]{1,220}\.(?:lua|bin)\Z")
FUNCTION = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _safe_file(path: Path, max_size: int) -> bytes:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or not 0 < info.st_size <= max_size):
            raise PreflightError("unsafe or empty prospective candidate file")
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            data = stream.read(max_size + 1)
            after = os.fstat(stream.fileno())
        signature = lambda x: (
            x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns, x.st_mode
        )
        if (len(data) != info.st_size or signature(info) != signature(before)
                or signature(info) != signature(after)):
            raise PreflightError("prospective file changed during Lua reference attestation")
    except (OSError, UnicodeError) as exc:
        raise PreflightError("prospective Lua reference cannot be read safely") from exc
    return data


def _reference(upstream: Path, raw: str, kind: str) -> tuple[str, str]:
    """Allow only an exact top-level Lua/BIN inside the *prospective* view."""
    # Do NOT .resolve() a hostile path before checking its components.
    # Files nested in Lua/BIN, traversal and original live resource paths
    # must not be treated as valid upstream-only source references.
    if not raw.startswith("/") or "\x00" in raw:
        raise PreflightError("candidate Lua/BIN reference is not absolute")
    value = Path(raw)
    try:
        relative = value.relative_to(upstream)
    except ValueError as exc:
        raise PreflightError("candidate Lua/BIN reference escapes upstream-only view") from exc
    parts = relative.parts
    if kind == "lua":
        valid = len(parts) == 2 and parts[0] == "lua" and parts[1].endswith(".lua")
    else:
        valid = (len(parts) == 3 and parts[:2] == ("files", "fake")
                 and parts[2].endswith(".bin"))
    if (not valid or not NAME.fullmatch(parts[-1])
            or any(part in ("", ".", "..") for part in parts)):
        raise PreflightError("candidate Lua/BIN reference is not an exact direct resource")
    if str(value) != raw or any(component.is_symlink() for component in (
        upstream, upstream / parts[0],
        *( [upstream / "files/fake"] if kind == "bin" else [] ),
        value,
    )):
        raise PreflightError("candidate Lua/BIN resource path is noncanonical or linked")
    return relative.as_posix(), hashlib.sha256(_safe_file(value, MAX_RESOURCE)).hexdigest()


def attest_candidate_lua_files(argv: Path, upstream: Path) -> dict:
    """Return bounded non-authorizing direct-file proof from native output."""
    if not upstream.is_absolute() or upstream.is_symlink() or not upstream.is_dir():
        raise PreflightError("prospective upstream-only root is unsafe")
    try:
        tokens = _safe_file(Path(argv), MAX_ARGS).decode("utf-8").split()
    except UnicodeError as exc:
        raise PreflightError("native candidate arguments are not UTF-8") from exc
    if len(tokens) > MAX_TOKENS:
        raise PreflightError("too many native candidate arguments")
    direct: dict[str, str] = {}
    lua_init = 0
    blob_files = 0
    inline_init = 0
    functions: list[str] = []
    for token in tokens:
        if token.startswith("--lua-init="):
            value = token[len("--lua-init="):]
            if not value:
                raise PreflightError("empty Lua initializer")
            if value.startswith("@"):
                key, digest = _reference(upstream, value[1:], "lua")
                previous = direct.setdefault(key, digest)
                if previous != digest:
                    raise PreflightError("prospective Lua initializer changed")
                lua_init += 1
            else:
                # Executable inline Lua may refer to arbitrary dynamic data.
                # Its presence is never a positive export/transitive proof.
                inline_init += 1
        elif token.startswith("--blob="):
            value = token[len("--blob="):]
            _name, sep, data = value.partition(":")
            if sep and data.startswith("@"):
                key, digest = _reference(upstream, data[1:], "bin")
                previous = direct.setdefault(key, digest)
                if previous != digest:
                    raise PreflightError("prospective BIN blob changed")
                blob_files += 1
        elif token.startswith("--lua-desync="):
            value = token[len("--lua-desync="):].split(":", 1)[0]
            if not FUNCTION.fullmatch(value):
                raise PreflightError("candidate Lua function name is invalid")
            functions.append(value)
    if not lua_init:
        raise PreflightError("native candidate has no verified upstream Lua initializer")
    payload = json.dumps(sorted(direct.items()), separators=(",", ":"), ensure_ascii=True)
    return {
        "state": "native-lua-direct-files-attested",
        "resource_witness_sha256": hashlib.sha256(payload.encode("ascii")).hexdigest(),
        "lua_init_files": lua_init,
        "blob_files": blob_files,
        "inline_lua_initializers": inline_init,
        "desync_calls": len(functions),
        "engine_lua_proof": "not-run",
        "exports": "unknown",
        "transitive_dependencies": "unknown",
        "compatibility": "unknown",
        "authorized": False,
    }
