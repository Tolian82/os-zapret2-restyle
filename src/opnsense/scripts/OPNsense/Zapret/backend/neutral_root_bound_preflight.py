#!/usr/bin/env python3
"""TZ6v5 S10b2a: read-only exact-bound PREPARED root evidence under original FD9.

The original shared Apply journal is the ONLY durable identity. S10a attests
the original sealed sibling root and the caller's S08c/S08d typed witnesses.
This gate checks the immutable S10b1 root/seal/candidate SHA pin before any
future bound PREPARED->ACTIVATING. It does not authorize a phase transition,
promote files or use the launcher, Config, IPFW, P1 or a new witness journal.
The actual S10b2b native service source adapter is NOT implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_root_stage import (
    attest_staged_candidate, PreparedRootReceipt, RootStageRefused,
)
from shared_apply_operation import (
    SharedApplyOperation, SharedOperationError, _validate_manifest_binding,
    DEFAULT_ROOT,
)
from shared_apply_seal import WORK
from voice_ipfw_adapter import require_lifecycle_lock


class BoundRootRefused(ValueError):
    """Content-free refusal; never leak Config, argv, hostlists or old owner."""


@dataclass(frozen=True)
class BoundRootReceipt:
    generation: str
    root_sha256: str
    original_seal_sha256: str
    original_candidate_sha256: str
    status: str = "PREPARED_ORIGINAL_BOUND_READ_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    reattest_under_original_fd9: bool = True
    native_owner_preflight_required: bool = True


def _attest_bound_candidate(*, generation: str, effective: EffectiveSnapshot,
                            native: NativeParity, mode: str, enabled: bool,
                            parent: Path, journal_root: Path,
                            owner_uid: int) -> BoundRootReceipt:
    """Detached testable physical/source proof, always nonauthorizing.

    Do not pass untrusted paths from a root JSON/GUI. Production uses only
    fixed WORK and DEFAULT_ROOT under the original FD9.
    """
    try:
        original = SharedApplyOperation(journal_root, owner=owner_uid)
        before = original.read()
        if (type(before) is not dict or before.get("phase") != "prepared" or
                "found" in before or "manifest" not in before or
                type(before.get("detail")) is not dict or
                before["detail"].get("id") != generation):
            raise BoundRootRefused("ORIGINAL_BOUND_PREPARED_REQUIRED")
        binding = _validate_manifest_binding(
            before["manifest"], before["detail"])
        witness = attest_staged_candidate(
            generation=generation, effective=effective, native=native,
            mode=mode, enabled=enabled, parent=parent, journal_root=journal_root,
            owner_uid=owner_uid)
        if (type(witness) is not PreparedRootReceipt or
                witness.generation != generation or
                witness.authorization != "NONE" or
                witness.promotion_allowed or witness.physical_transition_allowed or
                witness.reattest_under_original_fd9 is not True or
                binding["root_sha256"] != witness.root_sha256 or
                binding["seal_sha256"] != witness.original_seal_sha256 or
                binding["candidate_sha256"] != witness.original_candidate_sha256):
            raise BoundRootRefused("ORIGINAL_BOUND_ROOT_IDENTITY_CHANGED")
        # A second S10a read after the pinned journal read eliminates
        # passing a stale physical root or an asynchronously advanced phase.
        again = attest_staged_candidate(
            generation=generation, effective=effective, native=native,
            mode=mode, enabled=enabled, parent=parent, journal_root=journal_root,
            owner_uid=owner_uid)
        if again != witness or original.read() != before:
            raise BoundRootRefused("ORIGINAL_BOUND_ROOT_CHANGED_DURING_ATTEST")
        return BoundRootReceipt(
            generation, witness.root_sha256, witness.original_seal_sha256,
            witness.original_candidate_sha256)
    except (SharedOperationError, RootStageRefused, OSError, TypeError, KeyError):
        raise BoundRootRefused("ORIGINAL_BOUND_ROOT_UNQUALIFIED") from None


def attest_bound_under_fd9(*, generation: str, effective: EffectiveSnapshot,
                           native: NativeParity, mode: str,
                           enabled: bool) -> BoundRootReceipt:
    """Original installed root FD9 only. Never an activation permit."""
    try:
        require_lifecycle_lock()
    except (OSError, RuntimeError, ValueError):
        raise BoundRootRefused("ORIGINAL_FD9_REQUIRED") from None
    return _attest_bound_candidate(
        generation=generation, effective=effective, native=native,
        mode=mode, enabled=enabled, parent=WORK, journal_root=DEFAULT_ROOT,
        owner_uid=0)
