#!/usr/local/bin/python3.13
"""Pinned FreeBSD PT_INTERP and dynamic path overrides, WITHOUT ELF execution.

This augments existing DT_NEEDED graph snapshots; it is not loader resolution.
Only the standard amd64 FreeBSD interpreter path can be copied as inert bytes.
Nonempty/empty DT_RPATH/RUNPATH or other unmodelled loader-path directives
reject before any execution. PT_INTERP absence is UNKNOWN, not positive proof.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Callable

from extra_resources_engine_abi import (
    _needed_libraries, _bounded, _u16, _u32, _u64, EngineABIError,
    MAX_PHDR, MAX_DYNAMIC,
)
from extra_resources_preflight import PreflightError
from extra_resources_jail_libraries import _trusted_dir

STANDARD_INTERPRETER = "/libexec/ld-elf.so.1"
MAX_LOADER_BYTES = 16 * 1024 * 1024
# DT_RPATH, DT_RUNPATH, DT_FILTER, DT_AUXILIARY, DT_AUDIT, DT_DEPAUDIT
UNMODELED_PATH_TAGS = frozenset((
    15, 29, 0x7fffffff, 0x7ffffffd, 0x6ffffefc, 0x6ffffefb,
))


def _elf_interpreter(data: bytes, *, dependency: bool) -> str | None:
    """Inspect validated original ELF PHDR/DYNAMIC metadata, fail closed."""
    try:
        _needed_libraries(data)  # REUSE the existing bounded ELF verifier.
        header_count = _u16(data, 56)
        phoff = _u64(data, 32)
        phsize = _u16(data, 54)
        if not 0 < header_count <= MAX_PHDR or phsize != 56:
            raise EngineABIError("invalid ELF program header layout")
        _bounded(data, phoff, header_count * phsize)
        interpreters: list[str] = []
        for index in range(header_count):
            ph = phoff + index * phsize
            kind = _u32(data, ph)
            offset = _u64(data, ph + 8)
            size = _u64(data, ph + 32)
            if kind == 3:  # PT_INTERP
                if size < 2 or size > 256:
                    raise EngineABIError("invalid ELF interpreter size")
                _bounded(data, offset, size)
                value = data[offset:offset + size]
                if (not value.endswith(b"\x00") or
                        b"\x00" in value[:-1]):
                    raise EngineABIError("invalid ELF interpreter terminator")
                try:
                    interpreters.append(value[:-1].decode("ascii"))
                except UnicodeError as exc:
                    raise EngineABIError("invalid ELF interpreter encoding") from exc
            elif kind == 2:  # PT_DYNAMIC
                if size % 16 or size // 16 > MAX_DYNAMIC:
                    raise EngineABIError("invalid ELF dynamic layout")
                _bounded(data, offset, size)
                for entry in range(offset, offset + size, 16):
                    tag = _u64(data, entry)
                    if tag == 0:
                        break
                    if tag in UNMODELED_PATH_TAGS:
                        raise EngineABIError("unsupported ELF dynamic loader path directive")
        if len(interpreters) > 1:
            raise EngineABIError("multiple ELF interpreters")
        if dependency and interpreters:
            raise EngineABIError("shared library unexpectedly has PT_INTERP")
        if interpreters and interpreters[0] != STANDARD_INTERPRETER:
            raise EngineABIError("nonstandard FreeBSD ELF interpreter")
        return interpreters[0] if interpreters else None
    except EngineABIError as exc:
        raise PreflightError("ELF loader metadata incompatible or unsafe") from exc


def attest_static_loader_input(
    engine: bytes, libraries: dict[str, bytes], source_root: Path,
    pinned_reader: Callable[[Path, int], bytes],
) -> tuple[dict, dict[str, bytes]]:
    """Optional INERT loader bytes for a guarded, explicit source namespace.

    No static observation validates actual loader search, RPATH, symbol
    versions, dlopen, or Lua. The caller is responsible for FD9/Config and
    authenticating the library namespace. No executable chmod or subprocess.
    """
    if not isinstance(libraries, dict) or not callable(pinned_reader):
        raise PreflightError("invalid pinned ELF inputs")
    root = Path(source_root)
    if not root.is_absolute():
        raise PreflightError("library source root must be absolute")
    _trusted_dir(root)
    interp = _elf_interpreter(engine, dependency=False)
    for file in libraries.values():
        if not isinstance(file, bytes):
            raise PreflightError("invalid nested ELF bytes")
        _elf_interpreter(file, dependency=True)
    inputs: dict[str, bytes] = {}
    if interp is not None:
        libexec = root / "libexec"
        _trusted_dir(libexec)
        loader = libexec / "ld-elf.so.1"
        try:
            inode = loader.lstat()
        except OSError as exc:
            raise PreflightError("FreeBSD interpreter unavailable") from exc
        if (not stat.S_ISREG(inode.st_mode) or inode.st_nlink != 1
                or inode.st_uid != os.geteuid() or inode.st_mode & 0o022):
            raise PreflightError("unsafe FreeBSD interpreter inode")
        data = pinned_reader(loader, MAX_LOADER_BYTES)
        if not isinstance(data, bytes) or not 64 <= len(data) <= MAX_LOADER_BYTES:
            raise PreflightError("invalid FreeBSD interpreter bytes")
        _elf_interpreter(data, dependency=True)
        inputs["libexec/ld-elf.so.1"] = data
    record = {
        "interpreter": interp if interp else "absent-unproven",
        "libraries_inspected": len(libraries),
        "pinned_loader_sha256": (
            hashlib.sha256(inputs["libexec/ld-elf.so.1"]).hexdigest()
            if inputs else None
        ),
    }
    digest = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    return {
        "state": "elf-interpreter-static-input-only",
        "elf_interpreter": record["interpreter"],
        "elf_loader_witness_sha256": digest,
        "elf_loader_source": "explicit-pinned",
        "dynamic_library_closure": "unknown",
        "loader_path_resolution": "unproven",
        "dlopen_dependencies": "unknown",
        "runnable": False,
        "engine_lua_proof": "not-run",
        "compatibility": "unknown",
        "authorized": False,
    }, inputs
