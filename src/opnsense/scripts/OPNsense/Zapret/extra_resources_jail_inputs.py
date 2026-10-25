#!/usr/local/bin/python3.13
"""Temporary, NON-RUNNABLE saved Strategies jail-input snapshot (Stage 2).

Only for a caller already holding the original FD9 + native Config locks and
the private Git HEAD upstream-only view. No CLI, network, subprocess, jails,
engine/Lua execution, live resource writes or compatibility authorization.

This deliberately does not rewrite absolute native dvtws.args paths, resolve
dynamic Lua imports, or stage runtime ELF shared libraries. Thus even a valid
snapshot is NOT a runnable jail root or engine Lua proof.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Callable, Iterator

from extra_resources_engine_abi import (
    EngineABIError, MAX_ENGINE_BYTES, inspect_installed_engine_abi,
)
from extra_resources_lua_inputs import (
    MAX_ARGS, MAX_RESOURCE, attest_candidate_lua_files,
)
from extra_resources_preflight import PreflightError
from extra_resources_jail_argv import relocate_direct_native_argv

MAX_RESOURCES = 256
MAX_TOTAL_RESOURCE_BYTES = 64 * 1024 * 1024
RESOURCE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,220}\.(?:lua|bin)\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")


class JailInputError(PreflightError):
    """Missing/raced/surprising input. Never promote it to compatible."""


def _read_pinned(path: Path, limit: int) -> bytes:
    """Reject symlinks and pathname swaps even when an opened FD remains valid."""
    try:
        first = path.lstat()
        if (not stat.S_ISREG(first.st_mode) or first.st_nlink != 1
                or not 0 < first.st_size <= limit):
            raise JailInputError("unsafe jail input inode or size")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            before = os.fstat(fd)
            chunks = bytearray()
            while len(chunks) <= limit:
                part = os.read(fd, min(1024 * 1024, limit + 1 - len(chunks)))
                if not part:
                    break
                chunks.extend(part)
            after = os.fstat(fd)
            last = path.lstat()
        finally:
            os.close(fd)
        signature = lambda s: (
            s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_uid,
            s.st_gid, s.st_size, s.st_mtime_ns, s.st_ctime_ns,
        )
        if (len(chunks) != first.st_size or
                signature(first) != signature(before) or
                signature(before) != signature(after) or
                signature(after) != signature(last)):
            raise JailInputError("jail input changed during snapshot")
        return bytes(chunks)
    except OSError as exc:
        raise JailInputError("jail input is unavailable or raced") from exc


def _resources(view: Path) -> list[tuple[str, Path]]:
    """Direct Lua/BIN only; source provenance comes from caller-held Git view."""
    if not view.is_absolute() or view.is_symlink() or not view.is_dir():
        raise JailInputError("missing private upstream-only resource view")
    result: list[tuple[str, Path]] = []
    for relative, suffix in (("lua", ".lua"), ("files/fake", ".bin")):
        folder = view / relative
        if folder.is_symlink() or not folder.is_dir():
            raise JailInputError("unsafe standard resource directory")
        for path in folder.iterdir():
            if not path.name.endswith(suffix):
                continue
            if not RESOURCE_NAME.fullmatch(path.name):
                raise JailInputError("unsafe standard resource name")
            if path.is_symlink():
                raise JailInputError("linked upstream-only resource")
            result.append((relative + "/" + path.name, path))
            if len(result) > MAX_RESOURCES:
                raise JailInputError("too many upstream-only resources")
    if not any(name.startswith("lua/") for name, _ in result):
        raise JailInputError("upstream-only Lua files are absent")
    return sorted(result)


def _private_workspace(workspace: Path, view: Path) -> None:
    if not workspace.is_absolute() or workspace.is_symlink():
        raise JailInputError("jail staging workspace must be absolute")
    try:
        info = workspace.lstat()
        base = workspace.resolve(strict=True)
        upstream = view.resolve(strict=True)
    except OSError as exc:
        raise JailInputError("jail staging workspace is absent") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077 or base == upstream
            or upstream in base.parents or base in upstream.parents):
        raise JailInputError("jail workspace may overlap resource source")


def _save(root: Path, relative: str, data: bytes) -> None:
    dest = root / relative
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o400)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    dest.chmod(0o400)  # Snapshot is intentionally not directly executable.


@contextmanager
def staged_inert_jail_inputs(
    installed_engine: Path,
    native_argv: Path,
    upstream_only_view: Path,
    workspace_root: Path,
    *,
    expected_engine_sha256: str,
    expected_argv_sha256: str,
    check_lifecycle: Callable[[], object],
) -> Iterator[tuple[dict, Path]]:
    """Yield digest-pinned snapshot files and ALWAYS delete them at exit.

    Inputs MUST come from the original native saved-Strategies FD9/Config lock,
    and the authoritative Git HEAD upstream-only view. Expected hashes are
    mandatory; this helper cannot authenticate their caller's provenance.
    """
    engine, argv, view, workspace = map(
        Path, (installed_engine, native_argv, upstream_only_view, workspace_root)
    )
    if (not callable(check_lifecycle) or
            not SHA256.fullmatch(expected_engine_sha256) or
            not SHA256.fullmatch(expected_argv_sha256)):
        raise JailInputError("missing lifecycle or exact SHA256 witnesses")
    _private_workspace(workspace, view)

    def pin_inputs():
        check_lifecycle()
        try:
            hint = inspect_installed_engine_abi(engine)
        except EngineABIError as exc:
            raise JailInputError("installed engine ELF attestation failed") from exc
        if (hint["state"] != "engine-elf-abi-hint-only" or
                hint["engine_sha256"] != expected_engine_sha256 or
                hint["authorized"] is not False):
            raise JailInputError("installed engine SHA256 witness mismatch")
        engine_data = _read_pinned(engine, MAX_ENGINE_BYTES)
        argv_data = _read_pinned(argv, MAX_ARGS)
        if (hashlib.sha256(engine_data).hexdigest() != expected_engine_sha256
                or hashlib.sha256(argv_data).hexdigest() != expected_argv_sha256):
            raise JailInputError("native engine/argv bytes changed")
        direct = attest_candidate_lua_files(argv, view)
        if (direct["authorized"] is not False or
                direct["engine_lua_proof"] != "not-run"):
            raise JailInputError("unexpected authorizing Lua reference evidence")
        items = _resources(view)
        files: dict[str, bytes] = {}
        total = 0
        for name, path in items:
            data = _read_pinned(path, MAX_RESOURCE)
            total += len(data)
            if total > MAX_TOTAL_RESOURCE_BYTES:
                raise JailInputError("upstream-only jail bundle is too large")
            files[name] = data
        check_lifecycle()
        return engine_data, argv_data, files, direct["resource_witness_sha256"]

    initial_engine, initial_argv, initial_files, direct_witness = pin_inputs()
    mapped_argv, relocation = relocate_direct_native_argv(initial_argv, view)
    with tempfile.TemporaryDirectory(prefix="zapret-inert-jail-inputs-",
                                     dir=workspace) as temporary:
        root = Path(temporary)
        _save(root, "engine/dvtws2", initial_engine)
        _save(root, "native/original-dvtws.args", initial_argv)
        _save(root, "native/jailed-direct-resources.args", mapped_argv)
        digests = {"engine/dvtws2": expected_engine_sha256,
                   "native/original-dvtws.args": expected_argv_sha256,
                   "native/jailed-direct-resources.args": hashlib.sha256(mapped_argv).hexdigest()}
        for name, data in initial_files.items():
            _save(root, "upstream/" + name, data)
            digests["upstream/" + name] = hashlib.sha256(data).hexdigest()

        # Invalidate the snapshot if ANY source input changes during copying.
        final_engine, final_argv, final_files, final_witness = pin_inputs()
        if ((initial_engine, initial_argv, initial_files, direct_witness)
                != (final_engine, final_argv, final_files, final_witness)):
            raise JailInputError("jail inputs changed during staging")
        def attest_staged_files():
            # Check actual bytes inside the candidate root, not merely the
            # source SHA claims. A consumer changing the staged bundle must
            # cause refusal, never an apparently verified hand-off.
            for name, digest in digests.items():
                staged = root / name
                if (staged.is_symlink() or staged.stat().st_mode & 0o111
                        or hashlib.sha256(_read_pinned(staged, MAX_ENGINE_BYTES
                            if name == "engine/dvtws2" else MAX_ARGS
                            if name.startswith("native/")
                            else MAX_RESOURCE)).hexdigest() != digest):
                    raise JailInputError("staged jail input changed")

        attest_staged_files()
        canonical = json.dumps(sorted(digests.items()),
                               separators=(",", ":"), ensure_ascii=True)
        report = {
            "state": "inert-jail-input-snapshot-only",
            "snapshot_sha256": hashlib.sha256(canonical.encode("ascii")).hexdigest(),
            "staged_resources": len(initial_files),
            "engine_sha256": expected_engine_sha256,
            "argv_sha256": expected_argv_sha256,
            "direct_resource_witness_sha256": direct_witness,
            "argv_relocation": relocation["state"],
            "unmapped_path_tokens": relocation["unmapped_path_tokens"],
            "native_profiles": relocation["native_profiles"],
            "runnable": False,
            "dynamic_library_closure": "unknown",
            "transitive_dependencies": "unknown",
            "engine_lua_proof": "not-run",
            "compatibility": "unknown",
            "authorized": False,
        }
        yield report, root
        attest_staged_files()
        # Context-manager consumers cannot silently return success if the
        # original FD9/lifecycle or candidate inputs changed while in use.
        end_engine, end_argv, end_files, end_witness = pin_inputs()
        if ((initial_engine, initial_argv, initial_files, direct_witness)
                != (end_engine, end_argv, end_files, end_witness)):
            raise JailInputError("jail inputs changed before workspace teardown")
