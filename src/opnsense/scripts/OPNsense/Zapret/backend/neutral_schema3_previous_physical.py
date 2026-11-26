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


@dataclass(frozen=True)
class LockedRunningPredecessor:
    generation: str
    previous_generation: str
    previous_root_sha256: str
    config_base_sha256: str
    release_sha256: str
    running: PriorRunningToken
    epoch_sha256: str | None
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def attest_bound_running_predecessor_under_fd9(
        record: dict, *, preimage: CompletePriorPreimage,
        config_fd: int, config_digest: str) -> LockedRunningPredecessor:
    """Recheck the earlier running preimage under the original Config lock.

    Private ordinary PREPARED only. Never call the earlier PHP preflight
    while holding Config; never acquire P2a or grant physical transition.
    Legacy unpinned predecessors remain outside this qualified scope.
    """
    import sys
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from auto_detect_owner import attest_prepared_ordinary_learning_predecessor
    from auto_detect_minute import inspect_inert_release
    from neutral_root_stage import verify_original_operation_pins, _verify_original_pinned_root
    from voice_ipfw_adapter import FreeBSDIPFWAdapter, shared_release_manifest
    from voice_firewall_transaction import verify_prior_state

    try:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                type(record) is not dict or type(preimage) is not CompletePriorPreimage or
                type(config_fd) is not int or config_fd < 3 or config_fd == 9):
            raise PreviousPhysicalRefused("BOUND_RUNNING_NATIVE_SCOPE_REQUIRED")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
        if (store.read() != record or record.get("phase") != "prepared" or
                "found" in record or type(record.get("manifest")) is not dict or
                type(record.get("previous_manifest")) is not dict or
                type(record.get("previous")) is not dict):
            raise PreviousPhysicalRefused("BOUND_RUNNING_PREPARED_REQUIRED")
        detail, prior = record["detail"], record["previous"]
        pin, old_pin = record["manifest"], record["previous_manifest"]
        if (pin["schema"] not in (1, 2) or old_pin["schema"] not in (1, 2) or
                prior["id"] == detail["id"] or
                config_digest != detail["base"] or config_digest != prior["candidate"] or
                preimage.generation != detail["id"] or
                preimage.previous_generation != prior["id"] or
                preimage.root_sha256 != pin["root_sha256"] or
                preimage.saved_config_base_sha256 != config_digest or
                preimage.old_release_sha256 != preimage.active_release_sha256 or
                preimage.authorization != "NONE" or preimage.physical_transition_allowed or
                preimage.promotion_allowed or preimage.final_fd9_recheck_required is not True):
            raise PreviousPhysicalRefused("BOUND_RUNNING_PREIMAGE_CHANGED")
        expected = PriorRunningToken(
            preimage.prior_pid, preimage.prior_birth, preimage.supervisor_pid,
            preimage.supervisor_birth, preimage.original_kernel_argv_sha256)
        work = WORK / prior["id"]
        release = work / "release"

        def observe():
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != record:
                raise PreviousPhysicalRefused("BOUND_RUNNING_JOURNAL_CHANGED")
            verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
            root = json.loads(_verify_original_pinned_root(
                detail=prior, binding=old_pin, parent=WORK, owner_uid=0))
            service = root["service"]
            learning = old_pin["schema"] == 2
            if (root["schema"] != old_pin["schema"] or root["generation"] != prior["id"] or
                    service["enabled"] is not True or
                    service["target_mode"] not in ("all", "list", "auto") or
                    learning != (service["target_mode"] == "auto")):
                raise PreviousPhysicalRefused("BOUND_RUNNING_PRIOR_MODE_CHANGED")
            tree = _full_prior_tree(work, COMMON_ACTIVE, 0)
            running = _running_native(release, owner_uid=0,
                                      child_pidfile=CHILD_PID, monitor_pidfile=MONITOR_PID)
            if tree != preimage.active_release_sha256 or running != expected:
                raise PreviousPhysicalRefused("BOUND_RUNNING_PRIOR_PHYSICAL_CHANGED")
            manifest = shared_release_manifest(release)
            if manifest["rule_base"] != 19000 or manifest["rule_max"] not in (19010, 19099):
                raise PreviousPhysicalRefused("BOUND_RUNNING_KERNEL_SCOPE_INVALID")
            verify_prior_state(FreeBSDIPFWAdapter(19000, 19099), manifest, manifest)
            epoch_sha = None
            if learning:
                proof, epoch_sha = attest_prepared_ordinary_learning_predecessor(record, config_fd)
                if (proof.operation_id != prior["id"] or proof.generation != prior["id"] or
                        proof.owner_candidate_sha256 != config_digest or
                        (proof.owner.pid, proof.owner.started) != (running.pid, running.started) or
                        type(epoch_sha) is not str or len(epoch_sha) != 64 or
                        any(c not in "0123456789abcdef" for c in epoch_sha)):
                    raise PreviousPhysicalRefused("BOUND_RUNNING_PRIOR_EPOCH_CHANGED")
            elif inspect_inert_release(release, owner_uid=0) != "inactive":
                raise PreviousPhysicalRefused("BOUND_RUNNING_PRIOR_INERT_REQUIRED")
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != record:
                raise PreviousPhysicalRefused("BOUND_RUNNING_JOURNAL_CHANGED")
            return LockedRunningPredecessor(
                detail["id"], prior["id"], old_pin["root_sha256"], config_digest,
                tree, running, epoch_sha)

        first = observe()
        if observe() != first:
            raise PreviousPhysicalRefused("BOUND_RUNNING_PRIOR_WITNESS_CHANGED")
        return first
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError,
            subprocess.SubprocessError):
        raise PreviousPhysicalRefused("BOUND_RUNNING_PREDECESSOR_REFUSED") from None


@dataclass(frozen=True)
class FinalBoundRuntimeReceipt:
    generation: str
    root_sha256: str
    config_sha256: str
    release_sha256: str
    running: PriorRunningToken | None
    epoch_sha256: str | None
    kernel_state: str
    pretraffic_sha256: str | None = None
    retired_ready_sha256: str | None = None
    idle_producer: tuple | None = None
    authorization: str = "NONE"
    physical_transition_allowed: bool = False


def attest_bound_candidate_final_under_fd9(record: dict, *, config_fd: int,
                                           config_digest: str, enabled: bool,
                                           runtime_mode: str,
                                           retired_ready_sha256: str | None = None,
                                           queue_fd: int | None = None,
                                           expected_idle_producer: tuple | None = None) -> FinalBoundRuntimeReceipt:
    """Final installed candidate proof, not a phase writer or activation permit.

    The original Config owner supplies its fresh saved digest while holding
    inherited FD4; no nested PHP or queue acquisition. FD9 excludes the
    minute owner. Require the exact final kernel, never verify-cleanup or
    a staged rollback state. Learning requires the real finalized epoch
    and its current original producer inodes; appends do not change identity.
    """
    import pwd
    import sys
    from auto_detect_original_lock_handoff import CONFIG_PATH, assert_inherited_config_fd
    from auto_detect_epoch_receipts import EpochReceipts, _canonical
    from auto_detect_owner import attest_learning_epoch_finalizing_generation
    from auto_detect_storage import ROOT as PRODUCER, ENGINE_USER, FILE_MODE, _secure
    from auto_detect_queue import DurableInbox
    from auto_detect_minute import inspect_inert_release
    from neutral_root_stage import verify_original_operation_pins, _verify_original_pinned_root
    from neutral_schema3_quiescent_preimage import (
        _zero_processes, _empty_kernel, _safe_empty_directory, DAEMON_PID,
        _verify_retired_history, _verify_idle_producer)
    from auto_detect_post_drop import _original_epoch_queue, _qualified_learning_sources
    from voice_ipfw_adapter import FreeBSDIPFWAdapter, shared_release_manifest
    from voice_firewall_transaction import verify_prior_state

    try:
        if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
                type(record) is not dict or type(config_fd) is not int or
                config_fd < 3 or config_fd == 9 or type(enabled) is not bool or
                runtime_mode not in ("0", "1") or (runtime_mode == "1" and not enabled)):
            raise PreviousPhysicalRefused("BOUND_FINAL_NATIVE_SCOPE_REQUIRED")
        require_lifecycle_lock()
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        store = SharedApplyOperation(DEFAULT_ROOT, owner=0)
        if store.read() != record or type(record.get("manifest")) is not dict:
            raise PreviousPhysicalRefused("BOUND_FINAL_OWNER_REQUIRED")
        detail, pin = record["detail"], record["manifest"]
        learning = pin["schema"] == 2
        retired = record.get("previous_manifest", {}).get("schema") == 2
        needs_queue = retired or expected_idle_producer is not None
        if (retired != (retired_ready_sha256 is not None) or
                (learning and expected_idle_producer is not None) or
                (retired and not learning and expected_idle_producer is None) or
                (needs_queue and (type(queue_fd) is not int or queue_fd < 3 or
                                  queue_fd in (9, config_fd))) or
                (not needs_queue and queue_fd is not None)):
            raise PreviousPhysicalRefused("BOUND_FINAL_RETIRED_QUEUE_REQUIRED")
        if (pin["schema"] not in (1, 2) or config_digest != detail["candidate"] or
                record["phase"] != ("epoch-finalizing" if learning else "config-saved") or
                (learning and runtime_mode != "1") or
                ("found" in record and record["found"].get("runtime_mode") != runtime_mode) or
                ("found" not in record and enabled != (runtime_mode == "1"))):
            raise PreviousPhysicalRefused("BOUND_FINAL_PHASE_CONFIG_MISMATCH")
        work = WORK / detail["id"]
        release = work / "release"

        def observe():
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != record:
                raise PreviousPhysicalRefused("BOUND_FINAL_OWNER_CHANGED")
            verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
            root = json.loads(_verify_original_pinned_root(
                detail=detail, binding=pin, parent=WORK, owner_uid=0))
            service = root["service"]
            if (root["schema"] != pin["schema"] or root["generation"] != detail["id"] or
                    service["enabled"] is not enabled or
                    service["target_mode"] not in ("all", "list", "auto") or
                    learning != (service["target_mode"] == "auto" and enabled)):
                raise PreviousPhysicalRefused("BOUND_FINAL_ROOT_MODE_CHANGED")
            tree = _full_prior_tree(work, COMMON_ACTIVE, 0)
            process = epoch_digest = pretraffic_digest = idle = None
            if expected_idle_producer is not None:
                queue, receipts = _original_epoch_queue()
                with queue.inherited_exclusive(queue_fd):
                    if retired:
                        _verify_retired_history(record, queue, receipts, retired_ready_sha256)
                    idle = _verify_idle_producer(queue, receipts)
                    if idle != expected_idle_producer:
                        raise PreviousPhysicalRefused("BOUND_FINAL_IDLE_PRODUCER_CHANGED")
            elif not learning:
                _safe_empty_directory(PRODUCER, 0)
            if runtime_mode == "1":
                process = _running_native(release, owner_uid=0,
                                          child_pidfile=CHILD_PID, monitor_pidfile=MONITOR_PID)
                manifest = shared_release_manifest(release)
                if manifest["rule_base"] != 19000 or manifest["rule_max"] not in (19010, 19099):
                    raise PreviousPhysicalRefused("BOUND_FINAL_KERNEL_SCOPE_INVALID")
                # Even a sealed legacy-width release must have no residual
                # rules anywhere in the existing allocated 19000..19099 scope.
                verify_prior_state(FreeBSDIPFWAdapter(19000, 19099), manifest, manifest)
                kernel = "native-managed-kernel-final"
                if learning:
                    proof = attest_learning_epoch_finalizing_generation(detail["id"])
                    if (proof.operation_id != detail["id"] or proof.generation != detail["id"] or
                            proof.owner_candidate_sha256 != config_digest or
                            (proof.owner.pid, proof.owner.started) != (process.pid, process.started)):
                        raise PreviousPhysicalRefused("BOUND_FINAL_LEARNING_OWNER_CHANGED")
                    epoch = EpochReceipts(owner_uid=0).verify_learning_stopped_epoch(
                        proof, workspace=work)
                    if retired:
                        _, names = _qualified_learning_sources(proof.learning, PRODUCER)
                        queue, receipts = _original_epoch_queue(names)
                        with queue.inherited_exclusive(queue_fd):
                            _verify_retired_history(record, queue, receipts, retired_ready_sha256)
                    gid = pwd.getpwnam(ENGINE_USER).pw_gid
                    queue = DurableInbox(PRODUCER, owner_uid=0, writer_gid=gid)
                    queue._verify()  # read-only, FD9 excludes original minute ingress
                    _safe_empty_directory(queue.pending, 0)
                    for row in epoch["files"]:
                        info = _secure(PRODUCER / row["name"], directory=False,
                                       uid=0, gid=gid, mode=FILE_MODE, links=1)
                        if (info.st_dev, info.st_ino, info.st_nlink) != (
                                row["device"], row["inode"], row["nlink"]):
                            raise PreviousPhysicalRefused("BOUND_FINAL_LEARNING_INODE_CHANGED")
                    epoch_digest = sha256(_canonical(epoch)).hexdigest()
                    pretraffic_digest = epoch["pretraffic_sha256"]
                elif inspect_inert_release(release, owner_uid=0) != "inactive":
                    raise PreviousPhysicalRefused("BOUND_FINAL_INERT_RELEASE_REQUIRED")
            else:
                _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
                if inspect_inert_release(release, owner_uid=0) != "inactive":
                    raise PreviousPhysicalRefused("BOUND_FINAL_INERT_RELEASE_REQUIRED")
                kernel = _empty_kernel(release)
            require_lifecycle_lock()
            assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
            if store.read() != record:
                raise PreviousPhysicalRefused("BOUND_FINAL_OWNER_CHANGED")
            return FinalBoundRuntimeReceipt(detail["id"], pin["root_sha256"], config_digest,
                                            tree, process, epoch_digest, kernel, pretraffic_digest,
                                            retired_ready_sha256, idle)

        first = observe()
        if observe() != first:
            raise PreviousPhysicalRefused("BOUND_FINAL_PHYSICAL_WITNESS_CHANGED")
        return first
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError,
            subprocess.SubprocessError):
        raise PreviousPhysicalRefused("BOUND_FINAL_PHYSICAL_ATTEST_REFUSED") from None
