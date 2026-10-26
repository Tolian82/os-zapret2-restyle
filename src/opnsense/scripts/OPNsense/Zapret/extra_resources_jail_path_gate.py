#!/usr/local/bin/python3.13
"""Non-authorizing closure witness for staged native argv file paths.

This is a file-namespace gate after the ORIGINAL native compiler and existing
Lua/BIN + managed-target relocators, not another Strategies/options parser.
It refuses malformed or inconsistent staged references and explicitly counts
remaining host/unknown paths. No engine, loader, Lua, jail or service execution.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

from extra_resources_lua_inputs import MAX_ARGS, MAX_TOKENS
from extra_resources_preflight import PreflightError

RESOURCE = re.compile(r"[A-Za-z0-9_.-]{1,220}\.(?:lua|bin)\Z")
MANAGED = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}\.txt\Z")
BLOB = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
# Upstream v1.0.6 native file-bearing options not yet relocated. Their
# relative values need no slash to access the host filesystem.
UNMAPPED_FILE_OPTIONS = frozenset((
    "--hostlist-auto", "--ipset-auto", "--hostlist-auto-debug",
    "--ipset-exclude", "--pidfile", "--chdir", "--wf-save",
))
# Native flags with possible filesystem or process side effects.
RUNTIME_SIDE_EFFECT_OPTIONS = frozenset((
    "--hostlist-auto", "--hostlist-auto-debug", "--pidfile", "--chdir",
    "--wf-save", "--daemon", "--writable", "--uid", "--user",
))

# These paths are the *existing* staged input layout, not host paths.
DIRECT_LUA = "--lua-init=@/upstream/lua/"
DIRECT_BLOB = "--blob="
MANAGED_OPTIONS = {
    "--hostlist=": ("native-managed/", "hostlist-"),
    "--ipset=": ("native-managed/", "ipset-"),
    "--hostlist-exclude=": ("native-managed/", "hostlist-exclude.txt"),
}


def attest_staged_native_file_paths(
    args: bytes, staged_sha256: Mapping[str, str],
) -> dict:
    """Validate all known staged file options; report unresolved host paths.

    The caller must pin the original saved Config/FD9 and digest-check staged
    file contents. A zero-unresolved result proves only that KNOWN file
    arguments reference staged paths, NOT that all native options, Lua imports,
    shared libraries, dlopen or symbol exports are safe or runnable.
    """
    if (not isinstance(args, bytes) or not 0 < len(args) <= MAX_ARGS
            or b"\x00" in args or b"\r" in args):
        raise PreflightError("unsafe jailed native argument bytes")
    try:
        decoded = args.decode("utf-8")
    except UnicodeError as exc:
        raise PreflightError("jailed native argument encoding is invalid") from exc
    if not decoded.endswith("\n"):
        raise PreflightError("jailed native arguments lack line terminator")
    tokens = decoded[:-1].split("\n")
    if not 0 < len(tokens) <= MAX_TOKENS or any(not x for x in tokens):
        raise PreflightError("jailed native arguments contain empty or excessive tokens")
    if not isinstance(staged_sha256, Mapping):
        raise PreflightError("missing staged file digest manifest")

    referenced: dict[str, str] = {}
    unresolved = 0
    file_tokens = 0
    unreviewed_options = 0
    runtime_side_effects = 0
    for token in tokens:
        relative = None
        if token.startswith(DIRECT_LUA):
            name = token[len(DIRECT_LUA):]
            if not RESOURCE.fullmatch(name) or not name.endswith(".lua"):
                raise PreflightError("invalid jailed Lua file reference")
            relative = "upstream/lua/" + name
        elif token.startswith(DIRECT_BLOB):
            key, sep, value = token[len(DIRECT_BLOB):].partition(":@/upstream/files/fake/")
            if sep:
                if not BLOB.fullmatch(key) or not RESOURCE.fullmatch(value) or not value.endswith(".bin"):
                    raise PreflightError("invalid jailed BIN file reference")
                relative = "upstream/files/fake/" + value
        if relative is None:
            for option, (_, prefix) in MANAGED_OPTIONS.items():
                if not token.startswith(option + "/native-managed/"):
                    continue
                name = token[len(option + "/native-managed/"):]
                if not MANAGED.fullmatch(name):
                    raise PreflightError("invalid jailed managed file reference")
                if (option == "--hostlist-exclude=" and name != prefix) or (
                        option != "--hostlist-exclude=" and not name.startswith(prefix)):
                    raise PreflightError("jailed managed file kind mismatch")
                relative = "native-managed/" + name
                break
        if relative is None and (token.startswith("--lua-init=") or
                                 token.startswith("--blob=")):
            raise PreflightError("native Lua/BIN argument bypassed staged mapping")
        option_name = token.partition("=")[0]
        if relative is None and (
                option_name in UNMAPPED_FILE_OPTIONS
                or any(token.startswith(option) for option in MANAGED_OPTIONS)):
            unresolved += 1
            if option_name in RUNTIME_SIDE_EFFECT_OPTIONS:
                runtime_side_effects += 1
            continue
        if relative is not None:
            expected = staged_sha256.get(relative)
            if not isinstance(expected, str) or not DIGEST.fullmatch(expected):
                raise PreflightError("jailed file reference lacks pinned staged bytes")
            if relative in referenced and referenced[relative] != expected:
                raise PreflightError("jailed file digest changed during argument scan")
            referenced[relative] = expected
            file_tokens += 1
        elif token != "--new":
            # Non-path spellings are NOT evidence of safe native semantics:
            # --writable, --uid, new switches and Lua calls still need review.
            unreviewed_options += 1
            if option_name in RUNTIME_SIDE_EFFECT_OPTIONS:
                runtime_side_effects += 1
            if "/" in token or "@" in token:
                # NEVER normalize or inspect unknown host paths.
                unresolved += 1

    rows = sorted(referenced.items())
    witness = hashlib.sha256(
        json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()
    return {
        "state": (
            "unresolved-native-file-paths" if unresolved
            else "unreviewed-native-runtime-controls" if runtime_side_effects
            else "unreviewed-native-option-semantics" if unreviewed_options
            else "known-native-file-paths-staged-only"
        ),
        "known_file_references": file_tokens,
        "unique_staged_files": len(rows),
        "unresolved_path_tokens": unresolved,
        "unreviewed_native_option_tokens": unreviewed_options,
        "runtime_side_effect_option_tokens": runtime_side_effects,
        "file_reference_witness_sha256": witness,
        "engine_option_semantics": "unknown",
        "dynamic_library_closure": "unknown",
        "runnable": False,
        "engine_lua_proof": "not-run",
        "compatibility": "unknown",
        "authorized": False,
    }
