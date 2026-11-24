#!/usr/bin/env python3
"""TZ6v5 S09b: read-only, nonauthorizing original sealed-candidate refs.

Only the existing original shared Apply bundle seal is the inventory owner.
The caller supplies its trusted shared-work parent, never a path from JSON.
Every file is opened relative to pinned directory descriptors, without
following a symlink. No FD9 acquisition, Config, PID, IPFW, engine or writes.
A positive receipt is DETACHED evidence only, never Start/Apply authority.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat

from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_root_manifest import RootManifestRefused, validate_candidate
from shared_apply_seal import SharedBundleError, verify_seal

_GEN = re.compile(r"[0-9a-f]{32}\Z")
_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
_DIR_FLAGS = _READ_FLAGS | getattr(os, "O_DIRECTORY", 0)
_MAX = {"bundle-seal.json": 1024, "dvtws.args": 262144,
        "auto-detect-source-map.json": 1048576}
_AUTO = "ORIGINAL_NONACTIVATING_MAP_AND_OWNER_INDEPENDENT_PROPOSAL"
_NONAUTO = "ORIGINAL_NONAUTO_NO_SOURCE_MAP"


class SealedRefsRefused(ValueError):
    """Stable redacted failure, never include configuration or argv bytes."""


@dataclass(frozen=True)
class SealedRefsReceipt:
    generation: str
    root_sha256: str
    original_seal_sha256: str
    ref_sha256: tuple[tuple[str, str], ...]
    status: str = "DETACHED_S09B_ORIGINAL_REF_PROOF_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    reattest_under_original_fd9: bool = True


def _identity(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _directory(info: os.stat_result, owner: int) -> None:
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != owner or
            info.st_mode & 0o022):
        raise SealedRefsRefused("ORIGINAL_DIRECTORY_UNTRUSTED")


def _open_parent(path: Path, owner: int) -> int:
    # The original FD9 transaction supplies this trusted parent; no
    # manifest-controlled root, path traversal or recursive include exists.
    try:
        initial = path.lstat()
        _directory(initial, owner)
        fd = os.open(path, _DIR_FLAGS)
        if _identity(os.fstat(fd)) != _identity(initial):
            os.close(fd)
            raise SealedRefsRefused("ORIGINAL_PARENT_RACE")
        return fd
    except OSError:
        raise SealedRefsRefused("ORIGINAL_PARENT_UNAVAILABLE") from None


def _open_dir(parent_fd: int, name: str, owner: int) -> int:
    if name not in ("release",) and not _GEN.fullmatch(name):
        raise SealedRefsRefused("ORIGINAL_DIRECTORY_NAME_REFUSED")
    try:
        initial = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        _directory(initial, owner)
        fd = os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
        if _identity(os.fstat(fd)) != _identity(initial):
            os.close(fd)
            raise SealedRefsRefused("ORIGINAL_DIRECTORY_RACE")
        return fd
    except OSError:
        raise SealedRefsRefused("ORIGINAL_DIRECTORY_UNAVAILABLE") from None


def _verify_dir_still(parent_fd: int, name: str, fd: int) -> None:
    try:
        if _identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != _identity(os.fstat(fd)):
            raise SealedRefsRefused("ORIGINAL_DIRECTORY_CHANGED")
    except OSError:
        raise SealedRefsRefused("ORIGINAL_DIRECTORY_CHANGED") from None


def _read_file(dir_fd: int, name: str, owner: int) -> bytes:
    # No subdirectories and no user-supplied filenames are accepted.
    maximum = _MAX.get(name)
    if maximum is None:
        raise SealedRefsRefused("ORIGINAL_REF_NAME_REFUSED")
    try:
        before = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner or
                stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or
                not 0 < before.st_size <= maximum):
            raise SealedRefsRefused("ORIGINAL_REF_UNTRUSTED")
        fd = os.open(name, _READ_FLAGS, dir_fd=dir_fd)
        try:
            pinned = os.fstat(fd)
            if _identity(before) != _identity(pinned):
                raise SealedRefsRefused("ORIGINAL_REF_RACE")
            chunks = []
            remaining = maximum + 1
            while True:
                part = os.read(fd, min(65536, remaining))
                if not part:
                    break
                chunks.append(part)
                remaining -= len(part)
                if remaining <= 0:
                    raise SealedRefsRefused("ORIGINAL_REF_OVERSIZE")
            data = b"".join(chunks)
            if (len(data) != pinned.st_size or
                    _identity(os.fstat(fd)) != _identity(pinned) or
                    _identity(os.stat(name, dir_fd=dir_fd, follow_symlinks=False)) != _identity(pinned)):
                raise SealedRefsRefused("ORIGINAL_REF_CHANGED")
            return data
        finally:
            os.close(fd)
    except OSError:
        raise SealedRefsRefused("ORIGINAL_REF_UNAVAILABLE") from None


def attest_sealed_original(*, shared_work_parent: Path, generation: str,
                           root_bytes: bytes, effective: EffectiveSnapshot,
                           native: NativeParity, mode: str, enabled: bool,
                           owner_uid: int = 0) -> SealedRefsReceipt:
    """Attest exact original sealed *detached* bytes, not executable state.

    Native parity must have been computed by S08c from the same ORIGINAL
    generator's inputs. S09b checks its original argv digest/mode; S08c owns
    deeper profile attribution and S08d owns the effective fingerprint.
    S10 must recheck under original FD9 before promotion/activation.
    """
    if (not isinstance(shared_work_parent, Path) or
            type(generation) is not str or not _GEN.fullmatch(generation) or
            type(owner_uid) is not int or owner_uid < 0 or
            type(enabled) is not bool or mode not in ("all", "list", "auto") or
            type(native) is not NativeParity or native.status != "ORIGINAL_SOURCE_PARITY_ONLY" or
            native.authorization != "NONE" or native.physical_transition_allowed or
            native.mode != mode or
            native.source_map_status != (_AUTO if mode == "auto" else _NONAUTO)):
        raise SealedRefsRefused("ORIGINAL_NATIVE_PARITY_REQUIRED")
    work = shared_work_parent / generation
    with ExitStack() as stack:
        pfd = _open_parent(shared_work_parent, owner_uid)
        stack.callback(os.close, pfd)
        wfd = _open_dir(pfd, generation, owner_uid)
        stack.callback(os.close, wfd)
        rfd = _open_dir(wfd, "release", owner_uid)
        stack.callback(os.close, rfd)

        # Reuse the ORIGINAL full inventory verifier. Never implement a
        # competing seal, inventory format, manifest writer or journal.
        try:
            before_seal = verify_seal(work, owner=owner_uid)
        except (SharedBundleError, OSError, ValueError):
            raise SealedRefsRefused("ORIGINAL_SEAL_INVALID") from None
        if (type(before_seal) is not dict or before_seal.get("id") != generation):
            raise SealedRefsRefused("ORIGINAL_SEAL_GENERATION_MISMATCH")
        seal = _read_file(wfd, "bundle-seal.json", owner_uid)
        digest = hashlib.sha256(seal).hexdigest()
        args = _read_file(rfd, "dvtws.args", owner_uid)
        if mode != "auto":
            try:
                os.stat("auto-detect-source-map.json", dir_fd=rfd,
                        follow_symlinks=False)
            except FileNotFoundError:
                pass
            except OSError:
                raise SealedRefsRefused("ORIGINAL_SOURCE_MAP_UNQUALIFIED") from None
            else:
                raise SealedRefsRefused("UNEXPECTED_NONAUTO_SOURCE_MAP")
        source_map = (_read_file(rfd, "auto-detect-source-map.json", owner_uid)
                      if mode == "auto" else None)
        if hashlib.sha256(args).hexdigest() != native.original_args_sha256:
            raise SealedRefsRefused("ORIGINAL_ARGS_NATIVE_PARITY_CHANGED")
        try:
            root = validate_candidate(
                root_bytes, effective=effective, expected_generation=generation,
                expected_mode=mode, expected_enabled=enabled, original_args=args,
                original_source_map=source_map, expected_seal_sha256=digest,
                expected_uid=owner_uid)
        except RootManifestRefused:
            raise SealedRefsRefused("ORIGINAL_ROOT_BINDING_INVALID") from None
        try:
            after_seal = verify_seal(work, owner=owner_uid)
        except (SharedBundleError, OSError, ValueError):
            raise SealedRefsRefused("ORIGINAL_SEAL_CHANGED") from None
        if before_seal != after_seal or seal != _read_file(wfd, "bundle-seal.json", owner_uid):
            raise SealedRefsRefused("ORIGINAL_SEAL_CHANGED")
        if args != _read_file(rfd, "dvtws.args", owner_uid) or (
                source_map is not None and
                source_map != _read_file(rfd, "auto-detect-source-map.json", owner_uid)):
            raise SealedRefsRefused("ORIGINAL_REF_CHANGED")
        _verify_dir_still(wfd, "release", rfd)
        _verify_dir_still(pfd, generation, wfd)
        try:
            if _identity(shared_work_parent.lstat()) != _identity(os.fstat(pfd)):
                raise SealedRefsRefused("ORIGINAL_PARENT_CHANGED")
        except OSError:
            raise SealedRefsRefused("ORIGINAL_PARENT_CHANGED") from None
    return SealedRefsReceipt(
        generation, root.sha256, digest,
        (("dvtws.args", hashlib.sha256(args).hexdigest()),) +
        ((("auto-detect-source-map.json", hashlib.sha256(source_map).hexdigest()),)
         if source_map is not None else ()))
