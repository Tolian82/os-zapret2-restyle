#!/usr/local/bin/python3.13
"""Translate ONLY checked direct Lua/BIN references in original native argv.

One argument per line is the existing native launcher contract. This is NOT
a generic command-line parser, a shell command or a complete jail argv.
Unmapped original arguments (hostlists, IP sets, etc.) remain NOT runnable.
Never execute the resulting bytes or authorize removal.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import re

from extra_resources_lua_inputs import (
    MAX_ARGS, MAX_TOKENS, _reference,
)
from extra_resources_preflight import PreflightError

BLOB_NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")


def relocate_direct_native_argv(raw: bytes, upstream: Path) -> tuple[bytes, dict]:
    """Yield safe per-line Lua/BIN relocations and *non-authorizing* evidence.

    Always use original native-compiled bytes supplied by a caller holding
    original FD9/Config locks. File resolution delegates to the EXISTING
    native provenance checker _reference; no new XML/Strategies parsing.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ARGS:
        raise PreflightError("invalid native argv for jail relocation")
    if b"\x00" in raw or b"\r" in raw:
        raise PreflightError("unsafe native argv delimiters")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreflightError("native argv is not UTF-8") from exc
    lines = content.split("\n")
    if lines[-1] == "":
        lines.pop()
    if not 0 < len(lines) <= MAX_TOKENS or any(line == "" for line in lines):
        raise PreflightError("native argv contains blank or excessive arguments")

    replaced: list[str] = []
    direct: dict[str, str] = {}
    lua_count = 0
    blob_count = 0
    unmapped_paths = 0
    profiles = 1
    for token in lines:
        if token.startswith("--lua-init="):
            raw_path = token[len("--lua-init="):]
            if not raw_path.startswith("@"):
                # Inline source is executable and cannot be relocated as a
                # proven upstream Lua file. Block a runnable candidate.
                raise PreflightError("inline Lua initializer cannot be relocated")
            relative, digest = _reference(Path(upstream), raw_path[1:], "lua")
            if relative in direct and direct[relative] != digest:
                raise PreflightError("Lua resource changed during relocation")
            direct[relative] = digest
            replaced.append("--lua-init=@/upstream/" + relative)
            lua_count += 1
        elif token.startswith("--blob="):
            key, sep, value = token[len("--blob="):].partition(":")
            if not sep or not value.startswith("@") or not BLOB_NAME.fullmatch(key):
                raise PreflightError("non-file or invalid BLOB cannot be relocated")
            relative, digest = _reference(Path(upstream), value[1:], "bin")
            if relative in direct and direct[relative] != digest:
                raise PreflightError("BIN resource changed during relocation")
            direct[relative] = digest
            replaced.append("--blob=" + key + ":@/upstream/" + relative)
            blob_count += 1
        else:
            # Preserve the exact native argument (and every --new boundary).
            # Absolute paths in other options CANNOT be silently mapped to
            # host files inside jail; keep a visible unresolved-path count.
            if token == "--new":
                profiles += 1
            if "/" in token or "@" in token:
                unmapped_paths += 1
            replaced.append(token)
    if lua_count == 0:
        raise PreflightError("missing standard Lua initializer")
    mapped = ("\n".join(replaced) + "\n").encode("utf-8")
    if len(mapped) > MAX_ARGS:
        raise PreflightError("relocated native argv exceeds maximum size")
    return mapped, {
        "state": "direct-lua-bin-relocation-only",
        "direct_lua_init": lua_count,
        "direct_blob_files": blob_count,
        "native_profiles": profiles,
        "unmapped_path_tokens": unmapped_paths,
        "direct_reference_sha256": hashlib.sha256(
            repr(sorted(direct.items())).encode("ascii")
        ).hexdigest(),
        "runnable": False,
        "engine_lua_proof": "not-run",
        "compatibility": "unknown",
        "authorized": False,
    }
