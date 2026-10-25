"""Shared, bounded Lua source *declaration hints* for Strategy Lab and Remove.

This is a lexical scanner, NEVER a Lua evaluator, interpreter, export proof,
or transitive dependency validator. Identical masking ensures that a function
name in a comment/string is not an export candidate in either subsystem.
Uncertain or unreadable source fails closed; caller decides the diagnostic.
"""
from __future__ import annotations

import re

class LuaSourceEvidenceError(ValueError):
    """Uninspectable Lua source; must never authorize runtime compatibility."""


MAX_SOURCE_BYTES = 4 * 1024 * 1024
GLOBAL_FUNCTION = re.compile(r"(?<![\w.:])function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
GLOBAL_ASSIGN = re.compile(r"(?<![\w.:])([A-Za-z_][A-Za-z0-9_]*)\s*=\s*function\s*\(")
LINE_START_FUNCTION = re.compile(r"(?m)^[ \t]*function[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(")
DYNAMIC = re.compile(r"(?<![\w])(?:dofile|loadfile|loadstring|load|require|rawset|setfenv)\s*\(|(?:_G|package)\s*[\[.]")

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
                    raise LuaSourceEvidenceError("unterminated Lua long comment")
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
                raise LuaSourceEvidenceError("unterminated Lua quoted string")
            blank(start, min(pos, len(src)))
        elif src[pos] == "[" and (long := _long_start(src, pos)):
            start, end_token = long
            end_at = src.find(end_token, start)
            if end_at < 0:
                raise LuaSourceEvidenceError("unterminated Lua long string")
            end = end_at + len(end_token)
            blank(pos, end)
            pos = end
        else:
            pos += 1
    return "".join(out)



def inspect_lua_declarations(raw: bytes) -> dict:
    """Return source syntax evidence only, never runtime Lua export truth."""
    if not isinstance(raw, bytes) or len(raw) == 0 or len(raw) > MAX_SOURCE_BYTES:
        raise LuaSourceEvidenceError("Lua source is empty or exceeds the inspection limit")
    try:
        code = _lua_code_only(raw.decode("utf-8"))
    except UnicodeError as exc:
        raise LuaSourceEvidenceError("Lua source must be valid UTF-8") from exc
    declarations: set[str] = set()
    for pattern in (GLOBAL_FUNCTION, GLOBAL_ASSIGN):
        for match in pattern.finditer(code):
            lead = code[max(0, match.start() - 12):match.start()]
            if not re.search(r"\blocal\s*$", lead):
                declarations.add(match.group(1))
    return {
        "global_declarations": frozenset(declarations),
        "line_start_functions": frozenset(LINE_START_FUNCTION.findall(code)),
        "dynamic_source": bool(DYNAMIC.search(code)),
    }


def has_explicit_top_level_function(raw: bytes, name: str) -> bool:
    """Original Strategy Lab descriptor policy, but no comments/string fakes."""
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return False
    try:
        return name in inspect_lua_declarations(raw)["line_start_functions"]
    except LuaSourceEvidenceError:
        return False
