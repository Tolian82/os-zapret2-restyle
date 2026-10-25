#!/usr/local/bin/python3.13
"""Read-only ABI fingerprint of the INSTALLED dvtws2 ELF; never execute it.

This is *not* a Lua or engine preflight. The installed engine can link a
runtime statically or load it with dlopen, so an ELF DT_NEEDED hint cannot
prove that Lua initializes, exports functions, or resolves dependencies.
The output is always unknown/non-authorizing.

Bounded ELF64/LE/amd64 FreeBSD parser: only ELF headers, PT_LOAD/PT_DYNAMIC,
DT_NEEDED and dynamic string table. No ldd, subprocess, dlopen or network.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import struct

MAX_ENGINE_BYTES = 64 * 1024 * 1024
MAX_PHDR = 128
MAX_DYNAMIC = 8192
MAX_STRTAB = 2 * 1024 * 1024
ELF_MAGIC = b"\x7fELF"


class EngineABIError(ValueError):
    """Binary provenance is unsafe/invalid; never consider compatible."""


def _u16(data: bytes, pos: int) -> int:
    return struct.unpack_from("<H", data, pos)[0]


def _u32(data: bytes, pos: int) -> int:
    return struct.unpack_from("<I", data, pos)[0]


def _u64(data: bytes, pos: int) -> int:
    return struct.unpack_from("<Q", data, pos)[0]


def _bounded(data: bytes, off: int, size: int) -> None:
    if off < 0 or size < 0 or off > len(data) or size > len(data) - off:
        raise EngineABIError("ELF table is truncated or outside installed engine")


def _needed_libraries(data: bytes) -> tuple[str, ...]:
    _bounded(data, 0, 64)
    if (data[:4] != ELF_MAGIC or data[4:6] != b"\x02\x01"
            or data[6] != 1 or data[7] not in (0, 9)
            or _u16(data, 18) != 62
            or _u16(data, 16) not in (2, 3)):
        raise EngineABIError("installed engine is not ELF64 amd64 FreeBSD")
    phoff = _u64(data, 32)
    phsize = _u16(data, 54)
    phcount = _u16(data, 56)
    if phsize != 56 or not 0 < phcount <= MAX_PHDR:
        raise EngineABIError("invalid ELF program header layout")
    _bounded(data, phoff, phsize * phcount)
    loads: list[tuple[int, int, int]] = []
    dynamics: list[tuple[int, int]] = []
    for index in range(phcount):
        off = phoff + index * phsize
        typ = _u32(data, off)
        fileoff = _u64(data, off + 8)
        vaddr = _u64(data, off + 16)
        filesz = _u64(data, off + 32)
        _bounded(data, fileoff, filesz)
        if typ == 1:
            loads.append((vaddr, fileoff, filesz))
        elif typ == 2:
            dynamics.append((fileoff, filesz))
    if not dynamics:
        return ()  # static-linked engine is UNKNOWN, not proof of no Lua
    if len(dynamics) != 1:
        raise EngineABIError("ambiguous dynamic linker metadata")
    dynamic_off, dynamic_size = dynamics[0]
    if dynamic_size % 16 or dynamic_size // 16 > MAX_DYNAMIC:
        raise EngineABIError("invalid ELF dynamic table size")
    needed: list[int] = []
    str_vaddr = None
    str_size = None
    terminated = False
    for off in range(dynamic_off, dynamic_off + dynamic_size, 16):
        tag = _u64(data, off)
        val = _u64(data, off + 8)
        if tag == 0:
            terminated = True
            break
        if tag == 1:
            needed.append(val)
        elif tag == 5:
            str_vaddr = val
        elif tag == 10:
            str_size = val
    if not terminated or str_vaddr is None or str_size is None:
        raise EngineABIError("incomplete ELF dynamic linker metadata")
    if str_size == 0 or str_size > MAX_STRTAB or len(needed) > 128:
        raise EngineABIError("invalid dynamic library string table")
    translated = []
    for va, fo, size in loads:
        if va <= str_vaddr and str_size <= size - (str_vaddr - va):
            translated.append(fo + (str_vaddr - va))
    if len(set(translated)) != 1 or not translated:
        raise EngineABIError("dynamic library table has ambiguous address mapping")
    start = translated[0]
    _bounded(data, start, str_size)
    strings = data[start:start + str_size]
    names = []
    for off in needed:
        if off >= len(strings):
            raise EngineABIError("invalid DT_NEEDED offset")
        end = strings.find(b"\x00", off)
        if end < 0:
            raise EngineABIError("unterminated DT_NEEDED name")
        try:
            name = strings[off:end].decode("ascii")
        except UnicodeError as exc:
            raise EngineABIError("non-ASCII dynamic library name") from exc
        if not name or "/" in name or len(name) > 200:
            raise EngineABIError("unsafe DT_NEEDED library name")
        names.append(name)
    return tuple(names)


def _label(names: tuple[str, ...]) -> str:
    lua_names = []
    for name in names:
        if re.fullmatch(r"libluajit(?:-5\.1)?\.so(?:\.[0-9]+)*", name):
            lua_names.append("luajit-5.1")
        else:
            match = re.fullmatch(r"liblua(?:-)?(5\.[1-5]|5[1-5])\.so(?:\.[0-9]+)*", name)
            if match:
                version = match.group(1).replace("54", "5.4").replace("55", "5.5")
                version = version.replace("51", "5.1").replace("52", "5.2").replace("53", "5.3")
                lua_names.append("lua-" + version)
            elif re.fullmatch(r"liblua\.so(?:\.[0-9]+)*", name):
                lua_names.append("lua-version-unidentified")
    # Multiple runtimes, static/dlopen/no known lib => must stay UNKNOWN.
    unique = set(lua_names)
    return next(iter(unique)) if len(unique) == 1 else "unknown"


def inspect_installed_engine_abi(path: Path) -> dict:
    """Actual installed file, no execution; always NOT an authorization."""
    path = Path(path)
    if not path.is_absolute():
        raise EngineABIError("engine path must be absolute")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return {
            "state": "engine-not-installed",
            "abi": "unknown",
            "engine_sha256": None,
            "engine_lua_proof": "not-run",
            "compatibility": "unknown",
            "authorized": False,
        }
    except OSError as exc:
        raise EngineABIError("cannot safely open installed engine") from exc
    try:
        before = os.fstat(fd)
        pathname = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or not (before.st_mode & 0o111)
                or not 64 <= before.st_size <= MAX_ENGINE_BYTES
                or before.st_nlink < 1
                or (before.st_dev, before.st_ino) != (pathname.st_dev, pathname.st_ino)):
            raise EngineABIError("installed engine inode is not a trusted executable file")
        data = bytearray()
        while len(data) <= MAX_ENGINE_BYTES:
            part = os.read(fd, min(1024 * 1024, MAX_ENGINE_BYTES + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        after = os.fstat(fd)
        try:
            pathname_after = path.lstat()
        except OSError as exc:
            raise EngineABIError("installed engine path changed during ABI read") from exc
        # The open FD can remain unchanged when another inode replaces
        # the installed filename. Bind its identity to BOTH pathname reads.
        evidence = lambda s: (
            s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns,
            s.st_mode, s.st_nlink, s.st_uid, s.st_gid,
        )
        if (len(data) != before.st_size or evidence(before) != evidence(pathname)
                or evidence(before) != evidence(after)
                or evidence(after) != evidence(pathname_after)):
            raise EngineABIError("installed engine changed during ABI read")
    finally:
        os.close(fd)
    libs = _needed_libraries(bytes(data))
    return {
        "state": "engine-elf-abi-hint-only",
        "abi": _label(libs),
        "engine_sha256": hashlib.sha256(data).hexdigest(),
        "engine_lua_proof": "not-run",
        "compatibility": "unknown",
        "authorized": False,
    }
