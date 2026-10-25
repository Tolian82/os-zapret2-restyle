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

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
GLOBAL_FUNCTION = re.compile(r"(?<![\w.:])function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
GLOBAL_ASSIGN = re.compile(r"(?<![\w.:])([A-Za-z_][A-Za-z0-9_]*)\s*=\s*function\s*\(")
DYNAMIC = re.compile(r"(?<![\w])(?:dofile|loadfile|loadstring|load|require|rawset|setfenv)\s*\(|(?:_G|package)\s*[\[.]")
MAX_TOTAL_LUA = 6 * 1024 * 1024


def _long_start(src: str, offset: int) -> tuple[int, str] | None:
    if offset >= len(src) or src[offset] != "[":
        return None
    end = offset + 1
    while end < len(src) and src[end] == "=" and end - offset <= 15:
        end += 1
    if end < len(src) and src[end] == "[":
        return end + 1, "]" + src[offset + 1:end] + "]"
    return None


def _lua_code_only(src: str) -> str:
    """Mask quoted Lua and long-bracket strings/comments without executing."""
    out = list(src)
    pos = 0

    def blank(lo: int, hi: int) -> None:
        for j in range(lo, hi):
            if src[j] not in "\r\n":
                out[j] = " "

    while pos < len(src):
        if src.startswith("--", pos):
            long = _long_start(src, pos + 2)
            if long:
                start, end_token = long
                end_at = src.find(end_token, start)
                if end_at < 0:
                    raise PreflightError("unterminated Lua long comment")
                end = end_at + len(end_token)
            else:
                end = src.find("\n", pos)
                if end < 0:
                    end = len(src)
            blank(pos, end)
            pos = end
        elif src[pos] in ("'", '"'):
            quote = src[pos]
            start = pos
            pos += 1
            while pos < len(src):
                if src[pos] == "\\":
                    pos += 2
                elif src[pos] == quote:
                    pos += 1
                    break
                else:
                    pos += 1
            else:
                raise PreflightError("unterminated Lua quoted string")
            blank(start, min(pos, len(src)))
        elif src[pos] == "[" and (long := _long_start(src, pos)):
            start, end_token = long
            end_at = src.find(end_token, start)
            if end_at < 0:
                raise PreflightError("unterminated Lua long string")
            end = end_at + len(end_token)
            blank(pos, end)
            pos = end
        else:
            pos += 1
    return "".join(out)


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
            code = _lua_code_only(raw.decode("utf-8"))
        except UnicodeError as exc:
            raise PreflightError("non-UTF-8 Lua source is not statically inspectable") from exc
        # This reports declarations present in source, not globals actually
        # exported after execution. Conditional/local/reassigned cases are
        # intentionally never promoted to a positive compatibility result.
        for match in GLOBAL_FUNCTION.finditer(code):
            lead = code[max(0, match.start() - 12):match.start()]
            if not re.search(r"\blocal\s*$", lead):
                declarations.add(match.group(1))
        for match in GLOBAL_ASSIGN.finditer(code):
            lead = code[max(0, match.start() - 12):match.start()]
            if not re.search(r"\blocal\s*$", lead):
                declarations.add(match.group(1))
        dynamic_source |= bool(DYNAMIC.search(code))
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
