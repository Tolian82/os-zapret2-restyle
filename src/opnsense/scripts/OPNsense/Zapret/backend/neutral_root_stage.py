#!/usr/bin/env python3
"""TZ6v5 S10a: original-FD9-only *candidate* attachment beside sealed release.

One original shared-work operation has candidate.xml / plan.json / release
covered by its original seal. A root JSON containing that seal's SHA cannot
also be hashed *inside* the same seal (cryptographic dependency cycle).
Stage the generated root as a sibling within this SAME original work ID,
never inside release, and strictly cross-attest original seal+S08/S09+the
existing PREPARED journal on every read. No second journal, independent owner,
active promotion, Config writer, processes or IPFW. S10b/c will promote and
recover via the existing original FD9 and checked rollback transitions.

Do not invoke stage_manifest() from an ordinary GUI/CLI action. It must remain
under the already-held original lifecycle FD9 and original PREPARED work.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_root_manifest import RootCandidate
from neutral_root_refs import (attest_sealed_original, SealedRefsRefused,
                               _open_parent, _open_dir, _verify_dir_still,
                               _identity)
from shared_apply_operation import SharedApplyOperation, DEFAULT_ROOT, SharedOperationError
from shared_apply_seal import WORK, verify_seal, SharedBundleError
from voice_ipfw_adapter import require_lifecycle_lock

ROOT_NAME = "manifest.json"
PENDING_NAME = ".manifest.json.pending"
ROOT_LIMIT = 16384
_READ = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)


class RootStageRefused(ValueError):
    """No raw Config/argv/manifest content in diagnostics."""


@dataclass(frozen=True)
class PreparedRootReceipt:
    generation: str
    root_sha256: str
    original_seal_sha256: str
    original_candidate_sha256: str
    status: str = "ORIGINAL_PREPARED_ROOT_STAGED_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    reattest_under_original_fd9: bool = True


def _journal(generation: str, *, journal_root: Path, owner_uid: int) -> tuple[dict, str]:
    try:
        record = SharedApplyOperation(journal_root, owner=owner_uid).read()
        if (type(record) is not dict or record.get("phase") != "prepared" or
                "found" in record or type(record.get("detail")) is not dict or
                record["detail"].get("id") != generation):
            raise RootStageRefused("ORIGINAL_PREPARED_OWNER_REQUIRED")
        # The original sealed candidate hash must be this same operation's
        # immutable candidate. Exact record validation stays with original code.
        candidate_sha = record["detail"]["candidate"]
        if type(candidate_sha) is not str or len(candidate_sha) != 64:
            raise RootStageRefused("ORIGINAL_CANDIDATE_UNQUALIFIED")
        return record, candidate_sha
    except (SharedOperationError, OSError, ValueError) as exc:
        if isinstance(exc, RootStageRefused):
            raise
        raise RootStageRefused("ORIGINAL_PREPARED_OWNER_INVALID") from None


def _original_plan_matches(*, parent: Path, generation: str,
                           journal: dict, owner_uid: int) -> bool:
    # The original PHP SharedApplyConfig::preflight computes the journal's
    # logical `candidate` digest from the plan's Config object, NOT from the
    # candidate.xml bytes. Never invent a second PHP digest serializer here.
    # The original seal authenticates the exact plan and XML as one bundle.
    pfd = wfd = None
    try:
        pfd = _open_parent(parent, owner_uid)
        wfd = _open_dir(pfd, generation, owner_uid)
        name = "plan.json"
        before = os.stat(name, dir_fd=wfd, follow_symlinks=False)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner_uid or
                before.st_mode & 0o022 or before.st_nlink != 1 or
                not 0 < before.st_size <= 4 * 1024 * 1024):
            return False
        fd = os.open(name, _READ, dir_fd=wfd)
        try:
            if _identity(before) != _identity(os.fstat(fd)):
                return False
            raw = os.read(fd, 4 * 1024 * 1024 + 1)
            if (len(raw) != before.st_size or
                    _identity(before) != _identity(os.fstat(fd)) or
                    _identity(before) != _identity(os.stat(
                        name, dir_fd=wfd, follow_symlinks=False))):
                return False
        finally:
            os.close(fd)
        plan = json.loads(raw)
        detail = journal["detail"]
        _verify_dir_still(pfd, generation, wfd)
        return (type(plan) is dict and plan.get("result") == "prepared" and
                plan.get("page") == detail["page"] and
                plan.get("dependencies") == detail["base"] and
                plan.get("changed_fields") == detail["changed_fields"] and
                type(plan.get("candidate")) is dict)
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        return False
    finally:
        if wfd is not None:
            os.close(wfd)
        if pfd is not None:
            os.close(pfd)


def _original_preflight(*, generation: str, root_bytes: bytes,
                        effective: EffectiveSnapshot, native: NativeParity,
                        mode: str, enabled: bool, parent: Path,
                        journal_root: Path, owner_uid: int, schema3: bool = False,
                        allow_bound_schema3: bool = False):
    if (type(schema3) is not bool or type(allow_bound_schema3) is not bool or
            (allow_bound_schema3 and not schema3)):
        raise RootStageRefused("ORIGINAL_ROOT_SOURCE_MODE_INVALID")
    before, candidate_sha = _journal(generation, journal_root=journal_root,
                                     owner_uid=owner_uid)
    try:
        if schema3:
            # Same S10a writer and one original seal, with the REAL final
            # promoted source instead of pretending that S08d is final argv.
            # The pinned schema-2 bytes MUST equal the actual typed proposal.
            from neutral_schema3_physical_refs import (
                _attest_physical_schema3, PhysicalSchema3Refused,
            )
            if mode != "auto":
                raise RootStageRefused("ORIGINAL_SCHEMA3_AUTO_ONLY")
            source = _attest_physical_schema3(
                generation=generation, native=native, effective=effective,
                enabled=enabled, parent=parent, journal_root=journal_root,
                owner_uid=owner_uid, allow_bound_schema3=allow_bound_schema3)
            if root_bytes != source.candidate.json_bytes:
                raise RootStageRefused("ORIGINAL_SCHEMA3_ROOT_BYTES_MISMATCH")
            attested = PreparedRootReceipt(
                generation, source.root_sha256, source.seal_sha256,
                source.candidate_sha256)
        else:
            attested = attest_sealed_original(
                shared_work_parent=parent, generation=generation, root_bytes=root_bytes,
                effective=effective, native=native, mode=mode, enabled=enabled,
                owner_uid=owner_uid)
        original = verify_seal(parent / generation, owner=owner_uid)
    except (SealedRefsRefused, SharedBundleError, OSError, ValueError):
        raise RootStageRefused("ORIGINAL_SEALED_REFS_UNQUALIFIED") from None
    if (original.get("id") != generation or
            not _original_plan_matches(parent=parent, generation=generation,
                                       journal=before, owner_uid=owner_uid) or
            _journal(generation, journal_root=journal_root, owner_uid=owner_uid)[0] != before):
        raise RootStageRefused("ORIGINAL_JOURNAL_SEAL_CHANGED")
    return attested, candidate_sha, before


def attest_prepared_source_root(*, source, candidate_sha256: str,
                                enabled: bool, parent: Path,
                                journal_root: Path, owner_uid: int) -> RootCandidate:
    """Connect the actual S10c2 sealed readback to existing PREPARED refs.

    Import-only, read-only. Candidate SHA/enabled come from the original PHP
    preflight; caller must qualify installed engine version and FD9 separately.
    No physical permission, no root or journal write, no Found phase bypass.
    """
    from neutral_shared_apply_source_gate import SourceGateReceipt
    from neutral_root_manifest import compile_candidate
    from neutral_schema3_physical_refs import _attest_physical_schema3
    from neutral_root_refs import _read_file

    if (type(source) is not SourceGateReceipt or
            source.status != "ORIGINAL_SEALED_POSTPROMOTION_PARITY_ONLY" or
            source.authorization != "NONE" or source.physical_transition_allowed or
            type(source.native) is not NativeParity or
            type(source.effective) is not EffectiveSnapshot or
            source.effective.argv_sha256 != source.original_args_sha256 or
            source.native.original_args_sha256 != source.original_args_sha256 or
            source.native.mode != source.mode or
            type(enabled) is not bool):
        raise RootStageRefused("ORIGINAL_TYPED_SEALED_SOURCE_REQUIRED")
    generation = source.generation
    record, digest = _journal(generation, journal_root=journal_root,
                              owner_uid=owner_uid)
    if (digest != candidate_sha256 or "manifest" in record or
            not _original_plan_matches(parent=parent, generation=generation,
                                       journal=record, owner_uid=owner_uid)):
        raise RootStageRefused("ORIGINAL_PREPARED_SOURCE_IDENTITY_MISMATCH")
    if source.mode == "auto" and source.native_candidate_sha256 != digest:
        raise RootStageRefused("ORIGINAL_AUTO_CANDIDATE_IDENTITY_MISMATCH")
    work = parent / generation
    try:
        if verify_seal(work, owner=owner_uid)["sha256"]["candidate.xml"] != source.candidate_input_sha256:
            raise RootStageRefused("ORIGINAL_SOURCE_XML_CHANGED")
        if source.mode == "auto" and source.final_args_sha256 != source.original_args_sha256:
            proof = _attest_physical_schema3(
                generation=generation, native=source.native, effective=source.effective,
                enabled=enabled, parent=parent, journal_root=journal_root,
                owner_uid=owner_uid)
            if (proof.seal_sha256 != source.original_seal_sha256 or
                    dict(proof.native_ref_sha256)["dvtws.args"] != source.final_args_sha256 or
                    proof.candidate_sha256 != digest):
                raise RootStageRefused("ORIGINAL_FINAL_SOURCE_IDENTITY_CHANGED")
            candidate = proof.candidate
        else:
            pfd = _open_parent(parent, owner_uid)
            try:
                wfd = _open_dir(pfd, generation, owner_uid)
                try:
                    _require_only_sibling_root(wfd, owner_uid)
                    rfd = _open_dir(wfd, "release", owner_uid)
                    try:
                        args = _read_file(rfd, "dvtws.args", owner_uid)
                        origin = (_read_file(rfd, "auto-detect-source-map.json", owner_uid)
                                  if source.mode == "auto" else None)
                        seal_sha = hashlib.sha256(
                            _read_file(wfd, "bundle-seal.json", owner_uid)).hexdigest()
                        if (seal_sha != source.original_seal_sha256 or
                                hashlib.sha256(args).hexdigest() != source.final_args_sha256):
                            raise RootStageRefused("ORIGINAL_FINAL_SOURCE_IDENTITY_CHANGED")
                        candidate = compile_candidate(
                            effective=source.effective, generation=generation,
                            target_mode=source.mode, enabled=enabled, original_args=args,
                            original_source_map=origin, seal_sha256=seal_sha,
                            owner_uid=owner_uid)
                    finally:
                        os.close(rfd)
                finally:
                    os.close(wfd)
            finally:
                os.close(pfd)
            witness = attest_sealed_original(
                shared_work_parent=parent, generation=generation,
                root_bytes=candidate.json_bytes, effective=source.effective,
                native=source.native, mode=source.mode, enabled=enabled,
                owner_uid=owner_uid)
            if witness.original_seal_sha256 != source.original_seal_sha256:
                raise RootStageRefused("ORIGINAL_SOURCE_SEAL_CHANGED")
        if _journal(generation, journal_root=journal_root, owner_uid=owner_uid)[0] != record:
            raise RootStageRefused("ORIGINAL_PREPARED_SOURCE_JOURNAL_CHANGED")
        return candidate
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        raise RootStageRefused("ORIGINAL_PREPARED_SOURCE_ROOT_UNQUALIFIED") from None


def _absent(fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    except OSError:
        raise RootStageRefused("STAGED_ROOT_PATH_UNAVAILABLE") from None
    return False


def _require_only_sibling_root(wfd: int, owner_uid: int) -> None:
    # Exactly ONE proposed root for this original operation. A second root
    # sealed inside the release would create ambiguous owner/manifest order.
    rfd = _open_dir(wfd, "release", owner_uid)
    try:
        if not _absent(rfd, ROOT_NAME) or not _absent(rfd, PENDING_NAME):
            raise RootStageRefused("SECOND_RELEASE_ROOT_FORBIDDEN")
    finally:
        os.close(rfd)


def _read_staged(wfd: int, owner_uid: int) -> bytes:
    try:
        info = os.stat(ROOT_NAME, dir_fd=wfd, follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != owner_uid or
                stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or
                not 0 < info.st_size <= ROOT_LIMIT):
            raise RootStageRefused("STAGED_ROOT_UNTRUSTED")
        fd = os.open(ROOT_NAME, _READ, dir_fd=wfd)
        try:
            pinned = os.fstat(fd)
            if _identity(info) != _identity(pinned):
                raise RootStageRefused("STAGED_ROOT_RACE")
            data = os.read(fd, ROOT_LIMIT + 1)
            if (len(data) != pinned.st_size or
                    _identity(os.fstat(fd)) != _identity(pinned) or
                    _identity(os.stat(ROOT_NAME, dir_fd=wfd,
                                      follow_symlinks=False)) != _identity(pinned)):
                raise RootStageRefused("STAGED_ROOT_CHANGED")
            return data
        finally:
            os.close(fd)
    except OSError:
        raise RootStageRefused("STAGED_ROOT_UNAVAILABLE") from None


def verify_prepared_recovery_pin(*, record: dict, parent: Path,
                                 owner_uid: int) -> None:
    """Verify an already bound immutable root for PREPARED-only abort.

    Unlike activation, this may rely on the EXACT previously bound bytes:
    no caller-supplied S08 receipt, physical mutation, or new authority.
    The original journal must remain PREPARED throughout this read.
    """
    if (record.get("phase") != "prepared" or "found" in record or
            not ("manifest" in record or "previous_manifest" in record)):
        raise RootStageRefused("RECOVERY_NOT_PREPARED")
    # Reuse the same exact root/seal/plan verification for both immutable
    # generations. Never mistake the aborted new root for the old owner.
    for key, detail_key in (("manifest", "detail"),
                            ("previous_manifest", "previous")):
        if key in record:
            _verify_original_pinned_root(detail=record[detail_key],
                                         binding=record[key], parent=parent,
                                         owner_uid=owner_uid)


def _verify_original_pinned_root(*, detail: dict, binding: dict,
                                parent: Path, owner_uid: int) -> bytes:
    """Read exact original durable pin; NOT live runtime authorization."""
    from neutral_root_refs import _read_file
    from shared_apply_operation import _validate_manifest_binding

    pfd = wfd = None
    try:
        binding = _validate_manifest_binding(binding, detail)
        generation = detail["id"]
        pfd = _open_parent(parent, owner_uid)
        wfd = _open_dir(pfd, generation, owner_uid)
        if not _absent(wfd, PENDING_NAME):
            raise RootStageRefused("RECOVERY_ROOT_INCOMPLETE")
        _require_only_sibling_root(wfd, owner_uid)
        root = _read_staged(wfd, owner_uid)
        seal = _read_file(wfd, "bundle-seal.json", owner_uid)
        if (hashlib.sha256(root).hexdigest() != binding["root_sha256"] or
                hashlib.sha256(seal).hexdigest() != binding["seal_sha256"] or
                binding["candidate_sha256"] != detail["candidate"] or
                verify_seal(parent / generation, owner=owner_uid)["id"] != generation or
                not _original_plan_matches(parent=parent, generation=generation,
                                           journal={"detail": detail}, owner_uid=owner_uid)):
            raise RootStageRefused("RECOVERY_BOUND_ROOT_CHANGED")
        if (not _absent(wfd, PENDING_NAME) or
                _read_staged(wfd, owner_uid) != root or
                _read_file(wfd, "bundle-seal.json", owner_uid) != seal):
            raise RootStageRefused("RECOVERY_BOUND_ROOT_RACED")
        _require_only_sibling_root(wfd, owner_uid)
        _verify_dir_still(pfd, generation, wfd)
        if _identity(parent.lstat()) != _identity(os.fstat(pfd)):
            raise RootStageRefused("RECOVERY_BOUND_PARENT_CHANGED")
        return root
    except (SharedOperationError, SharedBundleError, SealedRefsRefused,
            OSError, ValueError, TypeError, KeyError):
        raise RootStageRefused("RECOVERY_BOUND_PIN_REFUSED") from None
    finally:
        if wfd is not None:
            os.close(wfd)
        if pfd is not None:
            os.close(pfd)


def _stage_candidate(*, generation: str, candidate: RootCandidate,
                     effective: EffectiveSnapshot, native: NativeParity,
                     mode: str, enabled: bool, parent: Path,
                     journal_root: Path, owner_uid: int,
                     schema3: bool = False) -> PreparedRootReceipt:
    # Internal writer. Public entry must have already attested ORIGINAL FD9.
    if (type(candidate) is not RootCandidate or
            candidate.status != "DETACHED_CANDIDATE_ONLY" or
            candidate.authorization != "NONE" or candidate.physical_transition_allowed or
            type(candidate.json_bytes) is not bytes or
            not 0 < len(candidate.json_bytes) <= ROOT_LIMIT or
            hashlib.sha256(candidate.json_bytes).hexdigest() != candidate.sha256):
        raise RootStageRefused("DETACHED_ROOT_REQUIRED")
    witness, candidate_sha, journal = _original_preflight(
        generation=generation, root_bytes=candidate.json_bytes,
        effective=effective, native=native, mode=mode, enabled=enabled,
        parent=parent, journal_root=journal_root, owner_uid=owner_uid,
        schema3=schema3)
    pfd = wfd = None
    try:
        pfd = _open_parent(parent, owner_uid)
        wfd = _open_dir(pfd, generation, owner_uid)
        if not _absent(wfd, ROOT_NAME) or not _absent(wfd, PENDING_NAME):
            raise RootStageRefused("STAGED_ROOT_ALREADY_PRESENT_OR_INCOMPLETE")
        _require_only_sibling_root(wfd, owner_uid)
        if _journal(generation, journal_root=journal_root, owner_uid=owner_uid)[0] != journal:
            raise RootStageRefused("ORIGINAL_JOURNAL_CHANGED_BEFORE_STAGE")
        # One original-owner staging file. Crash before link leaves only
        # pending; crash after link before unlink leaves both. Both MUST block
        # next stage/read, never silently continue or overwrite a candidate.
        fd = os.open(PENDING_NAME,
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                     0o600, dir_fd=wfd)
        try:
            os.fchmod(fd, 0o600)
            view = memoryview(candidate.json_bytes)
            while view:
                consumed = os.write(fd, view)
                if consumed <= 0:
                    raise RootStageRefused("STAGED_ROOT_WRITE_INCOMPLETE")
                view = view[consumed:]
            os.fsync(fd)
        finally:
            os.close(fd)
        # Hardlink creation has O_EXCL semantics on the destination. An
        # unexpected root can never be overwritten by rename().
        os.link(PENDING_NAME, ROOT_NAME, src_dir_fd=wfd, dst_dir_fd=wfd,
                follow_symlinks=False)
        os.unlink(PENDING_NAME, dir_fd=wfd)
        os.fsync(wfd)
        if _read_staged(wfd, owner_uid) != candidate.json_bytes:
            raise RootStageRefused("STAGED_ROOT_CONTENT_CHANGED")
        _verify_dir_still(pfd, generation, wfd)
        if _journal(generation, journal_root=journal_root, owner_uid=owner_uid)[0] != journal:
            raise RootStageRefused("ORIGINAL_JOURNAL_CHANGED_AFTER_STAGE")
        # Poststage cross-attestation catches release/owner races and the seal
        # remains the preexisting one (root is not in release inventory).
        after, after_sha, _ = _original_preflight(
            generation=generation, root_bytes=candidate.json_bytes,
            effective=effective, native=native, mode=mode, enabled=enabled,
            parent=parent, journal_root=journal_root, owner_uid=owner_uid,
            schema3=schema3)
        if after != witness or after_sha != candidate_sha or (
                _read_staged(wfd, owner_uid) != candidate.json_bytes):
            raise RootStageRefused("STAGED_ROOT_PROOF_CHANGED")
    except (OSError, SealedRefsRefused) as exc:
        raise RootStageRefused("ORIGINAL_STAGE_FILESYSTEM_REFUSED") from None
    finally:
        if wfd is not None:
            os.close(wfd)
        if pfd is not None:
            os.close(pfd)
    return PreparedRootReceipt(generation, candidate.sha256,
                               witness.original_seal_sha256, candidate_sha)


def stage_manifest(*, generation: str, candidate: RootCandidate,
                   effective: EffectiveSnapshot, native: NativeParity,
                   mode: str, enabled: bool) -> PreparedRootReceipt:
    """Private internal primitive, ONLY the original FreeBSD root FD9 owner.

    Does not advance the journal or write active Config/runtime. Never call
    from user GUI; production integration is separately gated by S10b.
    """
    try:
        require_lifecycle_lock()
    except (OSError, ValueError, RuntimeError):
        raise RootStageRefused("ORIGINAL_FD9_REQUIRED") from None
    return _stage_candidate(
        generation=generation, candidate=candidate, effective=effective,
        native=native, mode=mode, enabled=enabled, parent=WORK,
        journal_root=DEFAULT_ROOT, owner_uid=0)


def attest_staged_candidate(*, generation: str,
                            effective: EffectiveSnapshot, native: NativeParity,
                            mode: str, enabled: bool, parent: Path,
                            journal_root: Path, owner_uid: int,
                            schema3: bool = False,
                            allow_bound_schema3: bool = False) -> PreparedRootReceipt:
    """Strict read-only detached preflight, no physical authorization."""
    pfd = wfd = None
    try:
        pfd = _open_parent(parent, owner_uid)
        wfd = _open_dir(pfd, generation, owner_uid)
        if not _absent(wfd, PENDING_NAME):
            raise RootStageRefused("STAGED_ROOT_INCOMPLETE")
        _require_only_sibling_root(wfd, owner_uid)
        root = _read_staged(wfd, owner_uid)
        witness, candidate_sha, journal = _original_preflight(
            generation=generation, root_bytes=root, effective=effective,
            native=native, mode=mode, enabled=enabled, parent=parent,
            journal_root=journal_root, owner_uid=owner_uid,
            schema3=schema3, allow_bound_schema3=allow_bound_schema3)
        if (_read_staged(wfd, owner_uid) != root or
                _journal(generation, journal_root=journal_root, owner_uid=owner_uid)[0] != journal):
            raise RootStageRefused("STAGED_ROOT_PROOF_CHANGED")
        _verify_dir_still(pfd, generation, wfd)
    except (OSError, SealedRefsRefused):
        raise RootStageRefused("STAGED_ROOT_UNQUALIFIED") from None
    finally:
        if wfd is not None:
            os.close(wfd)
        if pfd is not None:
            os.close(pfd)
    return PreparedRootReceipt(generation, hashlib.sha256(root).hexdigest(),
                               witness.original_seal_sha256, candidate_sha)

def stage_schema3_manifest(*, generation: str, candidate: RootCandidate,
                           effective: EffectiveSnapshot, native: NativeParity,
                           enabled: bool) -> PreparedRootReceipt:
    """Same original FD9 and S10a atomic sibling writer, final schema3 source.

    Stages an immutable root only. NEVER binds, starts or advances the journal.
    """
    try:
        require_lifecycle_lock()
    except (OSError, ValueError, RuntimeError):
        raise RootStageRefused("ORIGINAL_FD9_REQUIRED") from None
    return _stage_candidate(
        generation=generation, candidate=candidate, effective=effective,
        native=native, mode="auto", enabled=enabled, parent=WORK,
        journal_root=DEFAULT_ROOT, owner_uid=0, schema3=True)


def attest_staged_schema3_candidate(*, generation: str,
                                    effective: EffectiveSnapshot,
                                    native: NativeParity, enabled: bool,
                                    parent: Path, journal_root: Path,
                                    owner_uid: int,
                                    allow_bound_schema3: bool = False
                                    ) -> PreparedRootReceipt:
    """Same S10a original staged byte reader, with actual final schema3 refs.

    Allow bound receipts only for the original postjournal reattestation path,
    after strict source/map/seal/manifest SHA cross-check. Not an activator.
    """
    return attest_staged_candidate(
        generation=generation, effective=effective, native=native,
        mode="auto", enabled=enabled, parent=parent,
        journal_root=journal_root, owner_uid=owner_uid,
        schema3=True, allow_bound_schema3=allow_bound_schema3)
