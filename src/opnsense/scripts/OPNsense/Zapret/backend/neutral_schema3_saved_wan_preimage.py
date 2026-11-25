#!/usr/bin/env python3
"""TZ6v5 S10b2b2b3b1: one original FD9 PREPARED + saved Config/WAN proof.

Reuse original OPNsense SharedApplyConfigWorker.preflight under Config lock
and the shipped WAN-first device/require probes. Both existing native readers
run twice, interleaved with genuine original bound-root and old runtime/IPFW
proof. No XML writer, new lock, engine signal, IPFW edit, or phase transition.
The PHP and WAN invocations intentionally inherit *only* original FD9.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess

from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_schema3_previous_preimage import (
    _attest_prepared_previous, OriginalPredecessorRefused, PreviousRuntimeReceipt,
)
from shared_apply_operation import (
    SharedApplyOperation, SharedOperationError, DEFAULT_ROOT,
)
from shared_apply_seal import WORK
from voice_ipfw_adapter import require_lifecycle_lock

_PHP = "/usr/local/bin/php"
_CONFIG = "/usr/local/opnsense/scripts/OPNsense/Zapret/shared_apply_config.php"
_WAN = "/usr/local/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_DEVICE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,63}\Z")
_SIZE = 4096
# The existing native WAN script emits these private state markers on refusal.
# A marker can also match the shell interface-name character class; never
# accept one as a forged physical device on the read-only handoff.
_WAN_STATE_MARKERS = frozenset((
    "wan-ready", "wan-required", "wan-invalid",
    "wan-not-required", "wan-unavailable",
))


class SavedWanPreimageRefused(ValueError):
    """Bounded private fixed refusal; never expose Config, argv or WAN data."""


@dataclass(frozen=True)
class SavedWanPreimageReceipt:
    generation: str
    root_sha256: str
    previous_generation: str
    previous_state: str
    config_base_sha256: str
    config_candidate_sha256: str
    verified_wan_device: str
    status: str = "ORIGINAL_FD9_SAVED_CONFIG_WAN_READ_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    complete_active_root_required: bool = True
    original_pid_birth_epoch_required: bool = True
    first_install_stopped_kernel_required: bool = True
    final_original_fd9_reattest_required: bool = True


def _native_call(argv: tuple[str, ...]) -> bytes:
    """Fixed production scripts, same original FD9 inherited by child PHP."""
    try:
        result = subprocess.run(
            argv, capture_output=True, timeout=12, check=False, pass_fds=(9,))
        if (result.returncode != 0 or type(result.stdout) is not bytes or
                len(result.stdout) > _SIZE or not result.stdout):
            raise SavedWanPreimageRefused("NATIVE_ORIGINAL_PROBE_REFUSED")
        return result.stdout
    except (OSError, subprocess.SubprocessError, ValueError):
        raise SavedWanPreimageRefused("NATIVE_ORIGINAL_PROBE_UNAVAILABLE") from None


def _native_preflight(generation: str, page: str) -> object:
    raw = _native_call((_PHP, _CONFIG, "preflight", generation, page))
    try:
        if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
            raise ValueError("multiple receipt lines")
        return json.loads(raw)
    except (UnicodeError, ValueError, TypeError):
        raise SavedWanPreimageRefused("ORIGINAL_CONFIG_RECEIPT_INVALID") from None


def _native_wan() -> str:
    # "require" is the original WAN-first prerequisite and "device" is
    # the existing same code's physical interface resolver (TUN/OPT allowed).
    # Neither is a new WAN classifier nor a guarantee of an IPv4 address.
    ready = _native_call((_WAN, "require"))
    device = _native_call((_WAN, "device"))
    if ready != b"wan-ready\n":
        raise SavedWanPreimageRefused("ORIGINAL_SAVED_WAN_NOT_READY")
    try:
        text = device.decode("ascii")
    except UnicodeError:
        raise SavedWanPreimageRefused("ORIGINAL_WAN_DEVICE_INVALID") from None
    if (not text.endswith("\n") or text[:-1] in _WAN_STATE_MARKERS or
            not _DEVICE.fullmatch(text[:-1])):
        raise SavedWanPreimageRefused("ORIGINAL_WAN_DEVICE_INVALID")
    return text[:-1]


def _qualified_config(receipt: object, detail: dict, enabled: bool) -> tuple:
    # The ORIGINAL PHP implementation obtains a fresh Config model under
    # Config->lock and SettingsApply::mergeForCommit verifies dependency SHA.
    # In particular the supplied 'base' alone is NOT proof; a successful
    # native worker preflight is required.
    fields = detail["changed_fields"]
    if (type(receipt) is not dict or
            set(receipt) != {"result", "snapshot", "enabled", "changes",
                             "base", "candidate", "fields"} or
            receipt["result"] != "prepared" or
            type(receipt["enabled"]) is not str or
            receipt["enabled"] != ("1" if enabled else "0") or
            receipt["base"] != detail["base"] or
            receipt["candidate"] != detail["candidate"] or
            receipt["snapshot"] != detail["candidate"] or
            type(receipt["changes"]) is not int or
            receipt["changes"] != len(fields) or
            type(receipt["fields"]) is not list or
            receipt["fields"] != fields or
            not all(type(receipt[key]) is str and
                    _HEX.fullmatch(receipt[key]) for key in
                    ("base", "candidate", "snapshot"))):
        raise SavedWanPreimageRefused("ORIGINAL_CONFIG_PREIMAGE_MISMATCH")
    return (receipt["base"], receipt["candidate"], receipt["enabled"],
            tuple(receipt["fields"]))


def _attest_saved_wan(*, generation: str, effective: EffectiveSnapshot,
                      native: NativeParity, enabled: bool,
                      parent: Path, journal_root: Path, owner_uid: int
                      ) -> SavedWanPreimageReceipt:
    """Bounded native reader seam; never callable as an activation grant."""
    try:
        if enabled is not True:
            raise SavedWanPreimageRefused("ORIGINAL_SCHEMA3_ACTIVE_WAN_REQUIRED")
        store = SharedApplyOperation(journal_root, owner=owner_uid)
        before = store.read()
        if (type(before) is not dict or
                before.get("phase") != "prepared" or
                type(before.get("manifest")) is not dict or
                before["manifest"].get("schema") not in (1, 2) or
                before.get("detail", {}).get("id") != generation or
                before["detail"].get("page") not in ("voice", "strategies")):
            raise SavedWanPreimageRefused("ORIGINAL_BOUND_PREPARED_REQUIRED")
        args = dict(generation=generation, effective=effective, native=native,
                    enabled=enabled, parent=parent, journal_root=journal_root,
                    owner_uid=owner_uid)
        old = _attest_prepared_previous(**args)
        if (type(old) is not PreviousRuntimeReceipt or old.authorization != "NONE" or
                old.physical_transition_allowed or old.promotion_allowed or
                old.generation != generation or
                old.root_sha256 != before["manifest"]["root_sha256"] or
                old.previous_candidate_sha256 != before["detail"]["base"]):
            raise SavedWanPreimageRefused("ORIGINAL_OLD_RUNTIME_UNQUALIFIED")
        first = _qualified_config(
            _native_preflight(generation, before["detail"]["page"]),
            before["detail"], enabled)
        first_wan = _native_wan()
        if (type(first_wan) is not str or first_wan in _WAN_STATE_MARKERS or
                not _DEVICE.fullmatch(first_wan)):
            raise SavedWanPreimageRefused("ORIGINAL_WAN_DEVICE_INVALID")
        if store.read() != before:
            raise SavedWanPreimageRefused("ORIGINAL_SAVED_PREIMAGE_RACED")
        old_again = _attest_prepared_previous(**args)
        second = _qualified_config(
            _native_preflight(generation, before["detail"]["page"]),
            before["detail"], enabled)
        second_wan = _native_wan()
        if (type(second_wan) is not str or second_wan in _WAN_STATE_MARKERS or
                not _DEVICE.fullmatch(second_wan)):
            raise SavedWanPreimageRefused("ORIGINAL_WAN_DEVICE_INVALID")
        if (old != old_again or first != second or
                first_wan != second_wan or store.read() != before):
            raise SavedWanPreimageRefused("ORIGINAL_SAVED_PREIMAGE_RACED")
        return SavedWanPreimageReceipt(
            generation, old.root_sha256, old.previous_generation,
            old.observed_previous_state, first[0], first[1], first_wan)
    except (OriginalPredecessorRefused, SharedOperationError,
            OSError, KeyError, TypeError, ValueError):
        raise SavedWanPreimageRefused("ORIGINAL_SAVED_WAN_PROOF_REFUSED") from None


def attest_saved_wan_under_fd9(*, generation: str,
                               effective: EffectiveSnapshot,
                               native: NativeParity,
                               enabled: bool) -> SavedWanPreimageReceipt:
    """One production FD9, fixed existing OPNsense readers. No CLI/Start."""
    try:
        require_lifecycle_lock()
    except (OSError, ValueError, RuntimeError):
        raise SavedWanPreimageRefused("ORIGINAL_FD9_REQUIRED") from None
    return _attest_saved_wan(
        generation=generation, effective=effective, native=native,
        enabled=enabled, parent=WORK, journal_root=DEFAULT_ROOT, owner_uid=0)
