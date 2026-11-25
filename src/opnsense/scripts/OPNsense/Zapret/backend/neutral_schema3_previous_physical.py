#!/usr/bin/env python3
"""TZ6v5 S10b2b2b3b2a: full previous active tree + live PID/birth/argv.

Import-only read-only conjunction of EXISTING root FD9 saved Config/WAN,
previous native-common engine/IPFW inspection, sealed release fingerprint,
and original P2c exact kernel argv/owner-birth checks. No journal advance,
no new process scanner/lock/writer, no SIGSTOP or IPFW mutation.

Deliberately no stopped/cold owner authority: existing stopped native P2c
retirement/epoch proof and a first-install no-kernel attestor remain required.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

from auto_detect_fd import OwnerToken, _START, _owner_snapshot
from auto_detect_owner import (
    _pid, _run, _snapshot, _freebsd_argv, _secure_bytes,
    _exact_common_supervisor_argv, GenerationRefused, MAX_ARGS,
)
from neutral_effective_diff import EffectiveSnapshot
from neutral_native_parity import NativeParity
from neutral_schema3_saved_wan_preimage import (
    _attest_saved_wan, SavedWanPreimageReceipt, SavedWanPreimageRefused,
)
from shared_apply_operation import (
    SharedApplyOperation, SharedOperationError, DEFAULT_ROOT,
)
from shared_apply_seal import (
    WORK, SharedBundleError, verify_seal, _release_hash,
)
from voice_ipfw_adapter import require_lifecycle_lock
from voice_live_inspect import (
    COMMON_ACTIVE, CHILD_PID, MONITOR_PID, CHILD_EXEC, MONITOR_EXEC,
)

# One existing exact root, two canonical process + kernel syscall readers.
MAX_NATIVE_CENSUS = 131072


class PreviousPhysicalRefused(ValueError):
    """Private fixed refusal, never prints native arguments, Config or PID."""


@dataclass(frozen=True)
class PriorRunningToken:
    pid: int
    started: str
    monitor_pid: int
    monitor_started: str
    argv_sha256: str


@dataclass(frozen=True)
class CompletePriorPreimage:
    generation: str
    root_sha256: str
    previous_generation: str
    old_release_sha256: str
    active_release_sha256: str
    saved_config_base_sha256: str
    resolved_wan_device: str | None
    prior_pid: int
    prior_birth: str
    supervisor_pid: int
    supervisor_birth: str
    original_kernel_argv_sha256: str
    status: str = "ORIGINAL_SCHEMA3_PREPARED_PRIOR_FULL_RUNNING_READ_ONLY"
    authorization: str = "NONE"
    physical_transition_allowed: bool = False
    promotion_allowed: bool = False
    stopped_epoch_pending: bool = True
    retired_observer_ack_pending: bool = True
    original_kernel_executable_inode_pending: bool = True
    first_install_native_cold_pending: bool = True
    final_fd9_recheck_required: bool = True


def _full_prior_tree(previous_work: Path, active: Path,
                     owner_uid: int) -> str:
    """Original full bundle seal + same bounded root-private tree hasher.

    This is stronger than the original Status subset comparison. Require
    exactly the same relative names, directories and every file's SHA.
    Do not trust a shell cmp of mutable filename subsets or a GUI manifest.
    """
    seal = verify_seal(previous_work, owner=owner_uid)
    if (type(seal) is not dict or seal.get("schema") != 1 or
            type(seal.get("sha256")) is not dict or
            type(seal["sha256"].get("release")) is not str):
        raise PreviousPhysicalRefused("PREVIOUS_FULL_SEAL_INVALID")
    expected = seal["sha256"]["release"]
    active_digest = _release_hash(active, owner_uid)
    if active_digest != expected:
        raise PreviousPhysicalRefused("PREVIOUS_FULL_ACTIVE_TREE_CHANGED")
    return active_digest


def _running_native(previous_release: Path, *,
                    owner_uid: int, child_pidfile: Path,
                    monitor_pidfile: Path,
                    runner=subprocess.run, argv_reader=None) -> PriorRunningToken:
    """Reuse original P2c owner-birth, kernel argv and monitor contracts.

    Does not check old epoch ACK; does not authorize stop/transition.
    """
    if argv_reader is None:
        argv_reader = _freebsd_argv
    pid = _pid(child_pidfile, owner_uid)
    monitor = _pid(monitor_pidfile, owner_uid)
    if pid == monitor:
        raise PreviousPhysicalRefused("PREVIOUS_PROCESS_PID_COLLISION")
    birth, shown = _snapshot(runner, pid)
    monitor_birth, monitor_shown = _snapshot(runner, monitor)
    if (not _START.fullmatch(birth) or
            not _START.fullmatch(monitor_birth) or
            not shown or shown[0] != CHILD_EXEC or
            not _exact_common_supervisor_argv(monitor_shown, child_pidfile, pid)):
        raise PreviousPhysicalRefused("PREVIOUS_PROCESS_IDENTITY_INVALID")
    original_argv = _secure_bytes(
        previous_release / "dvtws.args", MAX_ARGS, owner_uid)
    try:
        expected = [CHILD_EXEC] + original_argv.decode("utf-8").split() + [
            "--sockarg=0x200", "--user=nobody"]
    except (ValueError, UnicodeError):
        raise PreviousPhysicalRefused("PREVIOUS_SEALED_ARGV_INVALID") from None
    first = argv_reader(pid)
    if type(first) is not list or first != expected:
        raise PreviousPhysicalRefused("PREVIOUS_KERNEL_ARGV_MISMATCH")
    # Reuse the original full native census rather than trusting pidfile alone.
    census = _run(runner, ["/bin/ps", "-A", "-ww", "-o", "pid=", "-o", "command="])
    if len(census) > MAX_NATIVE_CENSUS:
        raise PreviousPhysicalRefused("PREVIOUS_CENSUS_OVERSIZE")
    engines = []
    monitors = []
    for line in census.splitlines():
        tokens = line.split()
        if not tokens or not tokens[0].isdigit():
            raise PreviousPhysicalRefused("PREVIOUS_CENSUS_INVALID")
        if len(tokens) < 2:
            if int(tokens[0]) in (0, 1):
                continue
            raise PreviousPhysicalRefused("PREVIOUS_CENSUS_INVALID")
        executable = tokens[1]
        if executable == CHILD_EXEC:
            engines.append(int(tokens[0]))
        if executable == MONITOR_EXEC or (
                len(tokens) > 2 and executable == "/bin/sh" and
                tokens[2] == MONITOR_EXEC):
            monitors.append(int(tokens[0]))
    if engines != [pid] or monitors != [monitor]:
        raise PreviousPhysicalRefused("PREVIOUS_FOREIGN_PROCESS_CENSUS")
    token = OwnerToken(pid, birth, CHILD_EXEC)
    if (not _owner_snapshot(token, runner) or
            (_pid(child_pidfile, owner_uid),
             _pid(monitor_pidfile, owner_uid)) != (pid, monitor)):
        raise PreviousPhysicalRefused("PREVIOUS_PID_BIRTH_RACED")
    later_birth, later_shown = _snapshot(runner, pid)
    later_monitor_birth, later_monitor_shown = _snapshot(runner, monitor)
    second = argv_reader(pid)
    if (later_birth != birth or later_shown != shown or
            later_monitor_birth != monitor_birth or
            later_monitor_shown != monitor_shown or second != first):
        raise PreviousPhysicalRefused("PREVIOUS_PROCESS_EPOCH_CHANGED")
    digest = sha256(
        json.dumps(first, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return PriorRunningToken(pid, birth, monitor, monitor_birth, digest)


def _attest_previous_physical(*, generation: str,
                             native: NativeParity,
                             effective: EffectiveSnapshot, enabled: bool,
                             parent: Path, journal_root: Path, owner_uid: int,
                             active: Path, child_pidfile: Path,
                             monitor_pidfile: Path,
                             runner=subprocess.run, argv_reader=None
                             ) -> CompletePriorPreimage:
    """Read-only original FD9 preimage; never a physical phase grant."""
    try:
        store = SharedApplyOperation(journal_root, owner=owner_uid)
        before = store.read()
        if (type(before) is not dict or
                before.get("phase") != "prepared" or
                type(before.get("manifest")) is not dict or
                before["manifest"].get("schema") not in (1, 2) or
                type(before.get("previous")) is not dict or
                type(before.get("detail")) is not dict or
                before["detail"]["id"] != generation or
                before["previous"]["id"] == generation or
                before["previous"]["candidate"] != before["detail"]["base"]):
            raise PreviousPhysicalRefused("PREVIOUS_ORIGINAL_BOUND_REQUIRED")
        previous = before["previous"]
        prior_work = parent / previous["id"]
        args = dict(generation=generation, native=native, effective=effective,
                    enabled=enabled, parent=parent, journal_root=journal_root,
                    owner_uid=owner_uid)
        saved = _attest_saved_wan(**args)
        if (type(saved) is not SavedWanPreimageReceipt or
                saved.authorization != "NONE" or
                saved.physical_transition_allowed or saved.promotion_allowed or
                saved.generation != generation or
                saved.previous_generation != previous["id"] or
                saved.previous_state != "ready" or
                saved.config_base_sha256 != previous["candidate"]):
            # A stopped old owner requires the existing immutable native
            # epoch/P2c retirement attestation. A missing owner is NOT cold.
            raise PreviousPhysicalRefused("PREVIOUS_RUNNING_OWNER_REQUIRED")
        original_hash = _full_prior_tree(prior_work, active, owner_uid)
        first = _running_native(
            prior_work / "release", owner_uid=owner_uid,
            child_pidfile=child_pidfile, monitor_pidfile=monitor_pidfile,
            runner=runner, argv_reader=argv_reader)
        if store.read() != before:
            raise PreviousPhysicalRefused("PREVIOUS_ORIGINAL_JOURNAL_RACED")
        saved_again = _attest_saved_wan(**args)
        again_hash = _full_prior_tree(prior_work, active, owner_uid)
        second = _running_native(
            prior_work / "release", owner_uid=owner_uid,
            child_pidfile=child_pidfile, monitor_pidfile=monitor_pidfile,
            runner=runner, argv_reader=argv_reader)
        if (saved != saved_again or original_hash != again_hash or
                first != second or store.read() != before):
            raise PreviousPhysicalRefused("PREVIOUS_NATIVE_PREIMAGE_CHANGED")
        return CompletePriorPreimage(
            generation=generation, root_sha256=saved.root_sha256,
            previous_generation=previous["id"],
            old_release_sha256=original_hash,
            active_release_sha256=again_hash,
            saved_config_base_sha256=saved.config_base_sha256,
            resolved_wan_device=saved.verified_wan_device,
            prior_pid=first.pid, prior_birth=first.started,
            supervisor_pid=first.monitor_pid,
            supervisor_birth=first.monitor_started,
            original_kernel_argv_sha256=first.argv_sha256)
    except (PreviousPhysicalRefused, SavedWanPreimageRefused,
            GenerationRefused, SharedOperationError, SharedBundleError,
            OSError, TypeError, KeyError, UnicodeError,
            subprocess.SubprocessError, ValueError):
        raise PreviousPhysicalRefused("PREVIOUS_PHYSICAL_ATTEST_REFUSED") from None


def attest_previous_physical_under_fd9(*, generation: str,
                                      native: NativeParity,
                                      effective: EffectiveSnapshot,
                                      enabled: bool) -> CompletePriorPreimage:
    """Fixed original production paths + existing root lock FD9; no CLI."""
    try:
        require_lifecycle_lock()
    except (OSError, RuntimeError, ValueError):
        raise PreviousPhysicalRefused("PREVIOUS_ORIGINAL_FD9_REQUIRED") from None
    return _attest_previous_physical(
        generation=generation, native=native, effective=effective,
        enabled=enabled, parent=WORK, journal_root=DEFAULT_ROOT, owner_uid=0,
        active=COMMON_ACTIVE, child_pidfile=CHILD_PID,
        monitor_pidfile=MONITOR_PID)
