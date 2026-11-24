#!/usr/bin/env python3
"""TZ6v5 S10b2b1: genuine pre/post schema3 original-source bridge, READ ONLY.

S08c/S08d are witnesses of the ORIGINAL nonactivating argv, not its
schema3-promoted successor. Original FD9 producer saves dvtws.original.args,
then installs dvtws.args and auto-detect-generation.json. The ORIGINAL
auto_detect_origin_map.verify_learning_promotion is the only trusted author
of that projection. This bridge binds its two distinct SHA values to the
existing sealed PREPARED journal without synthesizing a new argv or map.

This is source proof ONLY. It does not stage/bind an S10 manifest, update
the journal, approve a transition or modify Config/P1/PID/IPFW/engine.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import auto_detect_origin_map as origin
from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity, NativeSourceRow
from neutral_root_refs import (_open_parent, _open_dir, _read_file,
                               _verify_dir_still, _identity, SealedRefsRefused)
from neutral_root_stage import _journal, _original_plan_matches, RootStageRefused
from shared_apply_operation import DEFAULT_ROOT
from shared_apply_seal import WORK, verify_seal, SharedBundleError
from voice_ipfw_adapter import require_lifecycle_lock

_ID = re.compile(r"[a-f0-9]{32}\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_READ = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
         getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0))
_LIMIT = {"dvtws.args": 262144, "dvtws.original.args": 262144,
          "auto-detect-generation.json": 1048576}
_ORIGINAL_STATUS = "ORIGINAL_NONACTIVATING_MAP_AND_OWNER_INDEPENDENT_PROPOSAL"


class OriginalSchema3Refused(ValueError):
    """Redacted fixed refusal; never leak native argv, list, Config or WAN."""


@dataclass(frozen=True)
class OriginalSchema3Receipt:
    generation: str
    candidate_sha256: str
    old_args_sha256: str
    final_args_sha256: str
    original_source_map_sha256: str
    active_generation_sha256: str
    seal_sha256: str
    working_native_count: int
    learning_native_count: int
    status: str = "ORIGINAL_SCHEMA3_S08_SOURCE_BRIDGE_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    original_fd9_recheck_required: bool = True


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_promoted(fd: int, name: str, owner_uid: int) -> bytes:
    """Two fixed original-promoter outputs have original mode 0644.

    S09b's stricter native dvtws.args/source map/seal reader stays unchanged.
    Use pinned directory-relative no-follow fd and reject partial/foreign
    writes, symlinks, hardlinks and racing replacement.
    """
    if name not in _LIMIT:
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_ARTIFACT_UNKNOWN")
    try:
        first = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if (not stat.S_ISREG(first.st_mode) or first.st_uid != owner_uid or
                stat.S_IMODE(first.st_mode) not in (0o600, 0o644) or
                first.st_nlink != 1 or not 0 < first.st_size <= _LIMIT[name]):
            raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_ARTIFACT_UNTRUSTED")
        handle = os.open(name, _READ, dir_fd=fd)
        try:
            if _identity(os.fstat(handle)) != _identity(first):
                raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_ARTIFACT_RACE")
            raw = os.read(handle, _LIMIT[name] + 1)
            if (len(raw) != first.st_size or
                    _identity(os.fstat(handle)) != _identity(first) or
                    _identity(os.stat(name, dir_fd=fd, follow_symlinks=False))
                    != _identity(first)):
                raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_ARTIFACT_CHANGED")
            return raw
        finally:
            os.close(handle)
    except OSError:
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_ARTIFACT_UNAVAILABLE") from None


def _json(data: bytes, *, maximum: int) -> dict:
    if type(data) is not bytes or not 0 < len(data) <= maximum:
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_JSON_BOUNDED")
    def pairs(rows):
        value = {}
        for k, v in rows:
            if k in value:
                raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_JSON_DUPLICATE")
            value[k] = v
        return value
    try:
        parsed = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(
                                OriginalSchema3Refused("ORIGINAL_SCHEMA3_NONFINITE")))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_JSON_INVALID") from None
    if (type(parsed) is not dict or
            data != (json.dumps(parsed, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True) + "\n").encode("ascii")):
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_JSON_NONCANONICAL")
    return parsed


def _validate_typed_source(native: NativeParity, effective: EffectiveSnapshot,
                           source: dict, active: dict, original: bytes,
                           final: bytes, candidate_sha: str, generation: str) -> None:
    if (type(native) is not NativeParity or
            native.status != "ORIGINAL_SOURCE_PARITY_ONLY" or
            native.authorization != "NONE" or native.physical_transition_allowed or
            native.mode != "auto" or native.source_map_status != _ORIGINAL_STATUS or
            type(effective) is not EffectiveSnapshot or
            effective.status != "DETACHED_EFFECTIVE_INPUT_ONLY" or
            effective.authorization != "NONE" or effective.physical_transition_allowed or
            effective.external_ref_count != 0 or
            native.original_args_sha256 != _sha(original) or
            native.proposed_args_sha256 != _sha(final) or
            effective.argv_sha256 != _sha(original) or
            native.original_args_sha256 == native.proposed_args_sha256 or
            source.get("generation") != generation or
            source.get("final_args_sha256") != _sha(original) or
            active.get("generation") != generation or
            active.get("original_args_sha256") != _sha(original) or
            active.get("final_args_sha256") != _sha(final) or
            active.get("owner_candidate_sha256") != candidate_sha or
            active.get("schema") != 3 or
            active.get("activation_authorized") is not True):
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_TYPED_PARITY_MISMATCH")
    rows = source.get("profiles")
    promoted = active.get("profiles")
    if (type(rows) is not list or len(rows) < 2 or
            type(promoted) is not list or
            native.ordinary_native_count != len(rows) - 1 or
            any(type(row) is not dict for row in rows + promoted)):
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_SOURCE_ROWS_UNQUALIFIED")
    typed = tuple(NativeSourceRow(
        row.get("native_number"), row.get("source_number"), row.get("selector"),
        row.get("role"), row.get("status"), row.get("hostlist"))
        for row in rows[:-1])
    learners = [row for row in promoted if row.get("role") == "learning"]
    if (native.working_profiles != typed or
            native.learning_native_count <= 0 or
            native.learning_native_count != len(learners) or
            [row.native_number for row in native.learning_profiles] !=
            [row.get("native_number") for row in learners] or
            [row.hostlist for row in native.learning_profiles] !=
            [row.get("hostlist") for row in learners]):
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_FIRST_MATCH_CHANGED")


def _attest_original_schema3(*, generation: str, native: NativeParity,
                             effective: EffectiveSnapshot, parent: Path,
                             journal_root: Path, owner_uid: int) -> OriginalSchema3Receipt:
    """Testable read-only source proof; paths are fixed by installed FD9 wrapper."""
    if (type(generation) is not str or not _ID.fullmatch(generation) or
            type(owner_uid) is not int or owner_uid < 0 or
            not isinstance(parent, Path) or not isinstance(journal_root, Path)):
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_IDENTITY_REQUIRED")
    try:
        original_record, candidate_sha = _journal(
            generation, journal_root=journal_root, owner_uid=owner_uid)
        if ("manifest" in original_record or
                not _SHA.fullmatch(candidate_sha) or
                not _original_plan_matches(
                    parent=parent, generation=generation,
                    journal=original_record, owner_uid=owner_uid)):
            raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_PREPARED_REQUIRED")
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
                raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_SEAL_ID")
            seal = _read_file(wfd, "bundle-seal.json", owner_uid)
            source_raw = _read_file(rfd, "auto-detect-source-map.json", owner_uid)
            previous = _read_promoted(rfd, "dvtws.original.args", owner_uid)
            final = _read_promoted(rfd, "dvtws.args", owner_uid)
            active_raw = _read_promoted(rfd, "auto-detect-generation.json", owner_uid)
            source = _json(source_raw, maximum=262144)
            active = _json(active_raw, maximum=1048576)
            actual = origin.verify_learning_promotion(work, candidate_sha)
            if actual != active:
                raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_PRODUCER_CHANGED")
            _validate_typed_source(native, effective, source, active,
                                   previous, final, candidate_sha, generation)
            # Original full sealed inventory and all pinned physical refs
            # are checked *again* before returning a nonauthorizing receipt.
            after = verify_seal(work, owner=owner_uid)
            if (before != after or
                    seal != _read_file(wfd, "bundle-seal.json", owner_uid) or
                    source_raw != _read_file(rfd, "auto-detect-source-map.json", owner_uid) or
                    previous != _read_promoted(rfd, "dvtws.original.args", owner_uid) or
                    final != _read_promoted(rfd, "dvtws.args", owner_uid) or
                    active_raw != _read_promoted(rfd, "auto-detect-generation.json", owner_uid) or
                    _journal(generation, journal_root=journal_root,
                             owner_uid=owner_uid)[0] != original_record):
                raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_CHANGED_DURING_ATTEST")
            _verify_dir_still(wfd, "release", rfd)
            _verify_dir_still(pfd, generation, wfd)
            if _identity(parent.lstat()) != _identity(os.fstat(pfd)):
                raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_PARENT_CHANGED")
        return OriginalSchema3Receipt(
            generation, candidate_sha, _sha(previous), _sha(final),
            _sha(source_raw), _sha(active_raw), _sha(seal),
            native.ordinary_native_count, native.learning_native_count)
    except (RootStageRefused, SealedRefsRefused, SharedBundleError,
            origin.AttributionError, OSError, KeyError, TypeError, ValueError):
        raise OriginalSchema3Refused("ORIGINAL_SCHEMA3_UNQUALIFIED") from None


def attest_schema3_under_fd9(*, generation: str, native: NativeParity,
                             effective: EffectiveSnapshot) -> OriginalSchema3Receipt:
    """Only root original FD9; never allow even a read-only GUI path."""
    try:
        require_lifecycle_lock()
    except (OSError, RuntimeError, ValueError):
        raise OriginalSchema3Refused("ORIGINAL_FD9_REQUIRED") from None
    return _attest_original_schema3(
        generation=generation, native=native, effective=effective,
        parent=WORK, journal_root=DEFAULT_ROOT, owner_uid=0)
