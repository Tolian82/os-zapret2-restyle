#!/usr/bin/env python3
"""TZ6v5 S10b2b2b3a: read-only genuine PREPARED old-owner preimage bridge.

There is ONE original FD9 owner, ONE original S10b1 operation.json and the
accepted S10b2b2b2 bound schema-2 root. Reuse the existing native-common
read-only process + IPFW + sealed-previous-release inspector, never invent a
second process/kernel witness or permit a phase advance. Saved Config/WAN,
complete active-root, exact PID birth/epoch and crash rollback remain gates
of the later POSITIVE S10b2b2b3b transition, not assertions of this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_root_bound_preflight import (
    _attest_bound_candidate, BoundRootReceipt, BoundRootRefused,
)
from shared_apply_operation import (
    SharedApplyOperation, SharedOperationError, DEFAULT_ROOT,
)
from shared_apply_seal import WORK, SharedBundleError
from voice_ipfw_adapter import require_lifecycle_lock, IPFWAdapterError
from voice_firewall_transaction import VoiceFirewallError
from voice_live_inspect import examine_shared, VoiceInspectError


class OriginalPredecessorRefused(ValueError):
    """Fixed private diagnostics: never print Config, args, IPFW or PID."""


@dataclass(frozen=True)
class PreviousRuntimeReceipt:
    generation: str
    root_sha256: str
    previous_generation: str
    previous_candidate_sha256: str
    observed_previous_state: str
    previous_rule_count: int
    previous_table_count: int
    status: str = "ORIGINAL_SCHEMA3_PREPARED_PREVIOUS_READ_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    saved_config_required: bool = True
    saved_wan_required: bool = True
    complete_active_root_required: bool = True
    original_pid_birth_epoch_required: bool = True
    reattest_under_original_fd9: bool = True


def _qualified_observation(observed: object, previous: dict) -> tuple[str, int, int]:
    # Only the ORIGINAL native-common observer may qualify real kernel and
    # process state. A boolean callback alone is never authorization.
    if (type(observed) is not dict or
            observed.get("source") != "native-common" or
            observed.get("can_activate") is not False or
            observed.get("config_digest") != previous["candidate"] or
            observed.get("state") not in ("ready", "stopped") or
            type(observed.get("rule_count")) is not int or
            type(observed.get("table_count")) is not int or
            not 0 <= observed["rule_count"] <= 100 or
            not 0 <= observed["table_count"] <= 100 or
            type(observed.get("runtime")) is not dict):
        raise OriginalPredecessorRefused("ORIGINAL_PREVIOUS_RUNTIME_UNQUALIFIED")
    runtime = observed["runtime"]
    status = observed["state"]
    if (runtime.get("source_verified") is not True or
            runtime.get("state") != ("running" if status == "ready" else "stopped") or
            runtime.get("engine_verified") is not (status == "ready") or
            runtime.get("supervisor_verified") is not (status == "ready") or
            (status == "ready" and observed.get("condition") !=
             "common-runtime-and-ipfw-verified") or
            (status == "stopped" and observed.get("condition") not in
             ("common-runtime-stopped", "common-stopped-ipfw-kernel-absent")) or
            (status == "stopped" and
             (observed["rule_count"] != 0 or observed["table_count"] != 0))):
        raise OriginalPredecessorRefused("ORIGINAL_PREVIOUS_OWNER_INCOMPLETE")
    return status, observed["rule_count"], observed["table_count"]


def _attest_prepared_previous(*, generation: str, native: NativeParity,
                             effective: EffectiveSnapshot, enabled: bool,
                             parent: Path, journal_root: Path, owner_uid: int
                             ) -> PreviousRuntimeReceipt:
    """No transition, no write. Testable only with trusted disposable paths."""
    try:
        store = SharedApplyOperation(journal_root, owner=owner_uid)
        before = store.read()
        if (type(before) is not dict or before.get("phase") != "prepared" or
                "found" in before or type(before.get("manifest")) is not dict or
                before["manifest"].get("schema") not in (1, 2) or
                type(before.get("detail")) is not dict or
                before["detail"].get("id") != generation or
                type(before.get("previous")) is not dict or
                before["previous"]["id"] == generation or
                before["previous"]["candidate"] != before["detail"]["base"]):
            raise OriginalPredecessorRefused("ORIGINAL_PREVIOUS_COMMITTED_REQUIRED")
        previous = before["previous"]
        schema3 = before["manifest"]["schema"] == 2
        if (type(native) is not NativeParity or
                native.mode not in ("all", "list", "auto") or
                (schema3 != (native.mode == "auto" and enabled is True))):
            raise OriginalPredecessorRefused("ORIGINAL_BOUND_MODE_MISMATCH")
        bound_args = dict(
            generation=generation, native=native, effective=effective,
            mode=native.mode, enabled=enabled, parent=parent,
            journal_root=journal_root, owner_uid=owner_uid, schema3=schema3,
        )
        root = _attest_bound_candidate(**bound_args)
        if (type(root) is not BoundRootReceipt or
                root.authorization != "NONE" or
                root.physical_transition_allowed or root.promotion_allowed or
                root.native_owner_preflight_required is not True or
                root.root_sha256 != before["manifest"]["root_sha256"] or
                root.original_seal_sha256 != before["manifest"]["seal_sha256"] or
                root.original_candidate_sha256 != before["manifest"]["candidate_sha256"] or
                store.read() != before):
            raise OriginalPredecessorRefused("ORIGINAL_BOUND_ROOT_CHANGED")
        # examine_shared() is the single existing native process, physical
        # release and IPFW inspector. It demands the older sealed release,
        # actual current owner, and the exact bounded original rules.
        # It refuses partial/foreign kernel or mixed engine/monitor.
        old = {"schema": 1, "phase": "committed", "detail": previous}
        first = _qualified_observation(
            examine_shared(old, work_root=parent), previous)
        if (store.read() != before or
                _attest_bound_candidate(**bound_args) != root):
            raise OriginalPredecessorRefused("ORIGINAL_PREVIOUS_CHANGED")
        second = _qualified_observation(
            examine_shared(old, work_root=parent), previous)
        if (first != second or store.read() != before or
                _attest_bound_candidate(**bound_args) != root):
            raise OriginalPredecessorRefused("ORIGINAL_PREVIOUS_CHANGED")
        return PreviousRuntimeReceipt(
            generation, root.root_sha256, previous["id"],
            previous["candidate"], *first)
    except (SharedOperationError, BoundRootRefused, VoiceInspectError,
            SharedBundleError, VoiceFirewallError, IPFWAdapterError,
            subprocess.SubprocessError, OSError, KeyError, TypeError, ValueError):
        raise OriginalPredecessorRefused("ORIGINAL_PREVIOUS_PROOF_REFUSED") from None


def attest_prepared_previous_under_fd9(*, generation: str,
                                      native: NativeParity,
                                      effective: EffectiveSnapshot,
                                      enabled: bool) -> PreviousRuntimeReceipt:
    """Only inherited ORIGINAL root FD9. Never an activation or rollback API."""
    try:
        require_lifecycle_lock()
    except (OSError, ValueError, RuntimeError):
        raise OriginalPredecessorRefused("ORIGINAL_FD9_REQUIRED") from None
    return _attest_prepared_previous(
        generation=generation, native=native, effective=effective,
        enabled=enabled, parent=WORK, journal_root=DEFAULT_ROOT, owner_uid=0)
