#!/usr/bin/env python3
"""TZ6v5 S10b2b2b1: original FD9 schema3 physical root preflight (read only).

Check the four exact original-produced immutable refs and the ORIGINAL seal,
PREPARED plan, and typed pre/postpromotion witnesses. This never stages/binds
a root or grants PREPARED->ACTIVATING permission. Runtime WAN/Config/IPFW/PID
preimages and original journal activation belong to the next ordered gate.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat

from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_root_manifest import RootCandidate
from neutral_root_refs import (
    _identity, _open_dir, _open_parent, _read_file, _verify_dir_still,
    SealedRefsRefused,
)
from neutral_root_stage import _journal, RootStageRefused
from neutral_schema3_final_root import (
    FinalSchema3Refused, compile_final_schema3, validate_final_schema3,
)
from neutral_schema3_source_bridge import (
    OriginalSchema3Refused, _attest_original_schema3, _read_promoted,
)
from shared_apply_operation import DEFAULT_ROOT
from shared_apply_seal import WORK, SharedBundleError, verify_seal
from voice_ipfw_adapter import require_lifecycle_lock


class PhysicalSchema3Refused(ValueError):
    """Content-free refusal; never print WAN, Config, args or domain data."""


@dataclass(frozen=True)
class PhysicalSchema3Receipt:
    generation: str
    root_sha256: str
    seal_sha256: str
    candidate_sha256: str
    native_ref_sha256: tuple[tuple[str, str], ...]
    candidate: RootCandidate
    status: str = "ORIGINAL_SCHEMA3_PHYSICAL_REFS_READ_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    original_fd9_reattest_required: bool = True
    runtime_preimages_required: bool = True


# Exact original promoter artifacts; S10b2b2a enumerates this same ordering.
_REFS = (
    ("dvtws.args", 0o644),
    ("dvtws.original.args", 0o644),
    ("auto-detect-source-map.json", 0o600),
    ("auto-detect-generation.json", 0o644),
)


def _pinned_ref(fd: int, name: str, mode: int, owner_uid: int) -> bytes:
    """Check exact source mode, not the more permissive S10b2b1 reader."""
    first = os.stat(name, dir_fd=fd, follow_symlinks=False)
    if (not stat.S_ISREG(first.st_mode) or first.st_uid != owner_uid or
            first.st_nlink != 1 or stat.S_IMODE(first.st_mode) != mode):
        raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_REF_MODE_OR_OWNER")
    raw = (_read_file(fd, name, owner_uid) if mode == 0o600 else
           _read_promoted(fd, name, owner_uid))
    if _identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != _identity(first):
        raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_REF_REPLACED")
    return raw


def _attest_physical_schema3(*, generation: str, native: NativeParity,
                             effective: EffectiveSnapshot, enabled: bool,
                             parent: Path, journal_root: Path,
                             owner_uid: int,
                             allow_bound_schema3: bool = False) -> PhysicalSchema3Receipt:
    """Testable original-artifact preflight. Paths are fixed by FD9 wrapper."""
    if (type(enabled) is not bool or type(owner_uid) is not int or
            not isinstance(parent, Path) or not isinstance(journal_root, Path) or
            type(allow_bound_schema3) is not bool):
        raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_PHYSICAL_INPUT_REQUIRED")
    try:
        original = _attest_original_schema3(
            generation=generation, native=native, effective=effective,
            parent=parent, journal_root=journal_root, owner_uid=owner_uid,
            allow_bound_schema3=allow_bound_schema3)
        journal, candidate_sha = _journal(
            generation, journal_root=journal_root, owner_uid=owner_uid)
        work = parent / generation
        with ExitStack() as stack:
            pfd = _open_parent(parent, owner_uid)
            stack.callback(os.close, pfd)
            wfd = _open_dir(pfd, generation, owner_uid)
            stack.callback(os.close, wfd)
            rfd = _open_dir(wfd, "release", owner_uid)
            stack.callback(os.close, rfd)
            before = verify_seal(work, owner=owner_uid)
            if before.get("id") != generation:
                raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_SEAL_GENERATION")
            seal = _read_file(wfd, "bundle-seal.json", owner_uid)
            if (hashlib.sha256(seal).hexdigest() != original.seal_sha256 or
                    candidate_sha != original.candidate_sha256):
                raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_SEAL_OR_OWNER_CHANGED")
            values = tuple(_pinned_ref(rfd, name, mode, owner_uid)
                           for name, mode in _REFS)
            args, old_args, source_map, active_map = values
            inputs = dict(
                proof=original, native=native, original_effective=effective,
                original_args=old_args, final_args=args,
                original_source_map=source_map,
                active_generation_map=active_map,
                enabled=enabled, owner_uid=owner_uid,
            )
            proposal = compile_final_schema3(**inputs)
            if "manifest" in journal:
                # A bound PREPARED must pin the EXACT freshly recomputed
                # final physical schema3 root, not a plausible detached SHA.
                binding = journal["manifest"]
                if (not allow_bound_schema3 or binding["schema"] != 2 or
                        binding["generation"] != generation or
                        binding["root_sha256"] != proposal.candidate.sha256 or
                        binding["seal_sha256"] != original.seal_sha256 or
                        binding["candidate_sha256"] != candidate_sha):
                    raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_BOUND_ROOT_CHANGED")
            if validate_final_schema3(proposal.candidate.json_bytes, **inputs) != proposal:
                raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_ROOT_UNSTABLE")
            # One original seal, not an invented second authority. All opened
            # descriptors and the actual original journal are checked again.
            if (verify_seal(work, owner=owner_uid) != before or
                    _read_file(wfd, "bundle-seal.json", owner_uid) != seal or
                    tuple(_pinned_ref(rfd, name, mode, owner_uid)
                          for name, mode in _REFS) != values or
                    _journal(generation, journal_root=journal_root,
                             owner_uid=owner_uid)[0] != journal):
                raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_CHANGED_DURING_ATTEST")
            _verify_dir_still(wfd, "release", rfd)
            _verify_dir_still(pfd, generation, wfd)
            if _identity(parent.lstat()) != _identity(os.fstat(pfd)):
                raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_PARENT_CHANGED")
        if _attest_original_schema3(
                generation=generation, native=native, effective=effective,
                parent=parent, journal_root=journal_root,
                owner_uid=owner_uid,
                allow_bound_schema3=allow_bound_schema3) != original:
            raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_SOURCE_CHANGED")
        return PhysicalSchema3Receipt(
            generation, proposal.candidate.sha256, original.seal_sha256,
            candidate_sha, tuple((name, hashlib.sha256(value).hexdigest())
                                 for (name, _), value in zip(_REFS, values)),
            proposal.candidate)
    except (OriginalSchema3Refused, FinalSchema3Refused, RootStageRefused,
            SealedRefsRefused, SharedBundleError, OSError, ValueError,
            TypeError, KeyError):
        raise PhysicalSchema3Refused("ORIGINAL_SCHEMA3_PHYSICAL_UNQUALIFIED") from None


def attest_physical_schema3_under_fd9(*, generation: str,
                                      native: NativeParity,
                                      effective: EffectiveSnapshot,
                                      enabled: bool) -> PhysicalSchema3Receipt:
    """Installed read-only entry; neither a new lock nor a CLI."""
    try:
        require_lifecycle_lock()
    except (OSError, RuntimeError, ValueError):
        raise PhysicalSchema3Refused("ORIGINAL_FD9_REQUIRED") from None
    return _attest_physical_schema3(
        generation=generation, native=native, effective=effective,
        enabled=enabled, parent=WORK, journal_root=DEFAULT_ROOT, owner_uid=0)
