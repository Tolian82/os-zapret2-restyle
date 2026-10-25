#!/usr/local/bin/python3.13
"""Non-executing *source-shape* evidence for Lua exports used by native argv.

Read only the files already validated by the upstream-only direct-reference
attestor. Lexically mask Lua strings and comments before collecting plain
global function declarations; never claim that an initializer ran, that a
conditional definition executed, that a function body resolves, or that
transitive dependencies work. UNKNOWN remains UNKNOWN, never compatible.

This is deliberately NOT an interpreter or a second Strategies parser.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from extra_resources_lua_inputs import attest_candidate_lua_files, _safe_file, MAX_ARGS, MAX_RESOURCE
from extra_resources_preflight import PreflightError
from strategy_lab_py.lua_declarations import inspect_lua_declarations, LuaSourceEvidenceError

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
MAX_TOTAL_LUA = 6 * 1024 * 1024


def inspect_lua_source_shape(argv: Path, upstream: Path) -> dict:
    """Read-only bounded diagnostics; never a Lua execution or export proof."""
    direct = attest_candidate_lua_files(argv, upstream)
    tokens = _safe_file(Path(argv), MAX_ARGS).decode("utf-8").split()
    requested = []
    loaded = {}
    has_inline = False
    for token in tokens:
        if token.startswith("--lua-init="):
            val = token[len("--lua-init="):]
            if val.startswith("@"):
                # The direct attestor already rejected absent/foreign/link files.
                source = Path(val[1:])
                loaded[source] = None
            else:
                has_inline = True
        elif token.startswith("--lua-desync="):
            name = token[len("--lua-desync="):].split(":", 1)[0]
            if not NAME.fullmatch(name):
                raise PreflightError("unexpected Lua desync name")
            requested.append(name)
    declarations: set[str] = set()
    digest_rows = []
    total = 0
    dynamic_source = False
    for lua in sorted(loaded):
        raw = _safe_file(lua, MAX_RESOURCE)
        total += len(raw)
        if total > MAX_TOTAL_LUA:
            raise PreflightError("prospective Lua sources exceed bounded input")
        try:
            evidence = inspect_lua_declarations(raw)
        except LuaSourceEvidenceError as exc:
            raise PreflightError("Lua source is not statically inspectable") from exc
        # Shared with Strategy Lab: these are hints from declarations
        # in source, NEVER verified exports from a Lua runtime.
        declarations.update(evidence["global_declarations"])
        dynamic_source |= evidence["dynamic_source"]
        digest_rows.append(hashlib.sha256(raw).hexdigest())
    known_syntax = sum(name in declarations for name in requested)
    if has_inline:
        # Inline initializers can declare or overwrite functions dynamically.
        dynamic_source = True
    witness = hashlib.sha256(json.dumps(
        [direct["resource_witness_sha256"], digest_rows,
         sorted(declarations), sorted(requested), dynamic_source],
        separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()
    return {
        "state": "lua-export-source-shape-inspected",
        "source_shape_sha256": witness,
        "requested_calls": len(requested),
        "declaration_matches": known_syntax,
        "unaccounted_decl_syntax": len(requested) - known_syntax,
        "dynamic_source_indicators": bool(dynamic_source),
        "engine_lua_proof": "not-run",
        "exports": "unknown",
        "transitive_dependencies": "unknown",
        "compatibility": "unknown",
        "authorized": False,
    }
