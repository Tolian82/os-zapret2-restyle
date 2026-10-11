#!/usr/bin/env python3
"""One-lock FIVE-resource previous-state Voice rollback executor (unwired).

REAL Config and runtime restoration, REAL verified native IPFW rollback via
the existing transaction code, and single-engine/supervisor stop/restart
through explicit trusted lifecycle actions. The eventual on-router caller
MUST implement those two actions using the existing launcher and supervisor
with pinned process identity, never a bare PID kill/exec or a shell string.

The entire sequence holds a single OPNsense Config inode flock and requires
the native Zapret FD9 lease. Crash/failure leaves the whole MUTATING journal,
file redo records and retired candidate intact: this function deliberately
does NOT close intent, mark Voice ON or install a boot hook. That final
transition needs independently durable five-resource restart attestation.
"""
from __future__ import annotations

import errno
import fcntl
import os
from pathlib import Path
from typing import Callable

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_journal import _digest
from voice_cutover_journal import (
    VoiceCutoverJournal, BOUND_FIELD, RUNTIME_BOUND_SCHEMA,
    bound_candidate_runtime,
)
from voice_firewall_ledger import (
    VoiceOwnershipStore, canonical_manifest, decode_manifest, fingerprint,
)
from voice_ipfw_runtime import rollback_precommit_verified
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_recovery_quiescence import (
    _locked_config, inspect_quiescence,
)
from voice_cutover_file_rollback import restore_previous_files
from voice_native_file_observer import observe_live_files
from voice_process_recovery_evidence import (
    _normalize, _runtime_args_digest, inspect_process_evidence,
)
from voice_cutover_backup import inspect_previous
from voice_cutover_config_restore import _pinned_regular
from voice_native_process_actions import FreeBSDVoiceProcessActions


class FiveResourceRollbackError(RuntimeError):
    """The complete Voice intent MUST remain MUTATING if this is raised."""


def _verify_restart(probe, saved_process: dict, expected_scripts: dict,
                    previous_backup: Path) -> str:
    """New PID/start identity, but exact single-engine/supervisor topology."""
    original = saved_process["observation"]
    previous_state = original["engine"]["state"]
    snapshot = inspect_previous(previous_backup)
    args_hash = _runtime_args_digest(snapshot)
    a = _normalize(probe.probe(), expected_scripts, args_hash)
    b = _normalize(probe.probe(), expected_scripts, args_hash)
    if a != b:
        raise FiveResourceRollbackError("Voice process identity changed after restart")
    if a["engine"]["state"] != previous_state or \
       a["supervisor"]["state"] != previous_state:
        raise FiveResourceRollbackError("previous engine/supervisor topology not restored")
    if previous_state == "running":
        # A restarted engine is a NEW OS process. Requiring an old PID/start
        # from the checkpoint makes valid recovery impossible after reboot.
        for current, old in (
            (a["engine"]["process"], original["engine"]["process"]),
            (a["supervisor"]["daemon"], original["supervisor"]["daemon"]),
            (a["supervisor"]["monitor"], original["supervisor"]["monitor"]),
        ):
            if (current["pid"],current["start_ns"]) == \
               (old["pid"],old["start_ns"]):
                raise FiveResourceRollbackError(
                    "old process identity reused instead of verified restart"
                )
    return previous_state


def restore_previous_five_resources(
    *, journal: VoiceCutoverJournal, ledger: VoiceOwnershipStore,
    previous_backup: Path, install_image: Path, process_evidence: Path,
    expected_scripts: dict, config_path: Path, active_runtime: Path,
    expected_owner: tuple[int, int], expected_candidate_runtime_sha256: str,
    candidate_proof: dict, process_probe, read_ipfw_adapter,
    write_ipfw_adapter, stop_candidate: Callable[[], None] | None = None,
    start_previous: Callable[[], None] | None = None,
    require_lifecycle_owner: Callable[[], None],
    process_actions_factory: Callable[[int], FreeBSDVoiceProcessActions] | None = None,
    seal_previous: Callable[[int], dict] | None = None,
) -> dict:
    """Rollback under one lock: stop → kernel → runtime → Config → restart.

    This module has no production CLI. The stop/start callbacks need an
    eventually audited FreeBSD launcher/supervisor adapter, not mock-like
    lambdas: CI tests inject deterministic processes and a fake kernel.
    """
    if not callable(require_lifecycle_owner) or (
        process_actions_factory is None and
        (not callable(stop_candidate) or not callable(start_previous))
    ) or (
        process_actions_factory is not None and
        (not callable(process_actions_factory) or
         stop_candidate is not None or start_previous is not None)
    ):
        raise FiveResourceRollbackError(
            "exclusive native process actuator or injected test callbacks required"
        )
    if type(expected_owner) is not tuple or len(expected_owner) != 2 or \
       any(type(v) is not int or v < 0 for v in expected_owner):
        raise FiveResourceRollbackError("trusted native Config owner required")
    require_lifecycle_owner()
    original = journal.read()
    if original is None or original["phase"] != "mutating" or \
       original["schema"] < 2:
        raise FiveResourceRollbackError("no mutating bound five-resource intent")
    if original["schema"] == RUNTIME_BOUND_SCHEMA:
        # A future production rollback MUST take the candidate runtime hash
        # from the persisted, checked cutover. It cannot be guessed from an
        # absent active tree after a power failure or caller-chosen input.
        sealed_candidate = bound_candidate_runtime(original)
        if expected_candidate_runtime_sha256 is not None and (
            expected_candidate_runtime_sha256 != sealed_candidate
        ):
            raise FiveResourceRollbackError(
                "caller candidate runtime differs from sealed whole intent"
            )
        expected_candidate_runtime_sha256 = sealed_candidate
    elif expected_candidate_runtime_sha256 is None:
        raise FiveResourceRollbackError(
            "unbound old cutover has no trusted candidate runtime digest"
        )
    previous_backup = Path(previous_backup)
    install_image = Path(install_image)
    config_path = Path(config_path)
    active_runtime = Path(active_runtime)
    prior_files = bound_resource_fingerprints(
        previous_backup, original["previous"]
    )
    saved_process = inspect_process_evidence(
        Path(process_evidence), previous_backup,
        expected_scripts, original["previous"],
    )
    old_owner = ledger.owned()
    if old_owner is None or fingerprint(canonical_manifest(old_owner)) != \
       original["previous"]["firewall"]:
        raise FiveResourceRollbackError("IPFW previous owner mismatch")
    pending = ledger.pending()
    if pending is not None:
        prior_manifest = decode_manifest(pending["previous"])
        desired_manifest = decode_manifest(pending["desired"])
        if pending["phase"] != "mutating" or \
           prior_manifest != old_owner or \
           pending["previous_sha256"] != original["previous"]["firewall"] or \
           pending["desired_sha256"] != original["candidate"][BOUND_FIELD]:
            raise FiveResourceRollbackError("IPFW transition not bound to whole cutover")
    elif observe_owned_ipfw(ledger, read_ipfw_adapter) != \
         original["previous"]["firewall"]:
        raise FiveResourceRollbackError(
            "no pending IPFW rollback and live previous kernel not verified"
        )
    if journal.read() != original:
        raise FiveResourceRollbackError("whole intent changed during preflight")

    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | \
        getattr(os, "O_CLOEXEC", 0)
    fd = os.open(config_path, flags)
    try:
        _pinned_regular(config_path,fd,owner=expected_owner)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise FiveResourceRollbackError(
                    "OPNsense Config is locked by another writer"
                ) from exc
            raise
        _locked_config(config_path,fd,expected_owner)
        require_lifecycle_owner()
        if journal.read()!=original:
            raise FiveResourceRollbackError("whole intent changed after Config lock")
        if process_actions_factory is not None:
            # Construct only AFTER acquiring the actual Config flock: the
            # process actuator receives a borrowed descriptor whose identity
            # must remain stable across BOTH stop and restart.
            actuator = process_actions_factory(fd)
            if not isinstance(actuator, FreeBSDVoiceProcessActions) or                actuator.config_fd != fd or actuator.config_path != config_path or                actuator.active_runtime != active_runtime or                actuator.previous_backup != previous_backup or                actuator.journal.directory != journal.directory:
                raise FiveResourceRollbackError(
                    "foreign/misbound native process actuator"
                )
            stop_candidate = actuator.stop_candidate
            start_previous = actuator.start_previous

        # Stop precisely the candidate one-engine topology, including both
        # supervisor roles, without touching the normal legacy lifecycle.
        # This action must itself prove PID/exec/start identity and absence
        # of orphan dvtws2 before returning.
        stop_candidate()
        require_lifecycle_owner()
        stopped = process_probe.probe()
        if stopped.get("engine",{}).get("state")!="stopped" or \
           stopped.get("supervisor",{}).get("state")!="stopped" or \
           process_probe.probe()!=stopped:
            raise FiveResourceRollbackError(
                "Voice engine/supervisor not stably stopped"
            )

        # Existing native IPFW rollback performs actual bounded kernel
        # mutations AND clears only the per-IPFW pending journal after exact
        # old-kernel verification. The WHOLE journal remains MUTATING.
        pending = ledger.pending()
        if pending is not None:
            prior_manifest = decode_manifest(pending["previous"])
            desired_manifest = decode_manifest(pending["desired"])
            if prior_manifest != old_owner or \
               pending["desired_sha256"]!=original["candidate"][BOUND_FIELD]:
                raise FiveResourceRollbackError("IPFW ownership changed before rollback")
            rollback_precommit_verified(
                ledger,write_ipfw_adapter,journal,candidate_proof,
            )
        require_lifecycle_owner()

        def quiescent() -> bool:
            report = inspect_quiescence(
                journal, ledger, previous_backup, process_probe,
                read_ipfw_adapter, config_path=config_path,
                locked_config_fd=fd,config_owner=expected_owner,
                require_lifecycle_owner=require_lifecycle_owner,
            )
            return report["state"]=="stopped-and-previous-ipfw"

        if quiescent() is not True:
            raise FiveResourceRollbackError("kernel/process gate refused files")
        restored = restore_previous_files(
            config_path,active_runtime,install_image,previous_backup,journal,
            expected_owner=expected_owner,
            expected_candidate_runtime_sha256=expected_candidate_runtime_sha256,
            require_lifecycle_owner=require_lifecycle_owner,
            require_quiescent=quiescent,locked_config_fd=fd,
        )
        if restored["state"]!="previous-files-restored":
            raise FiveResourceRollbackError("previous Config/runtime not restored")
        require_lifecycle_owner()
        if quiescent() is not True:
            raise FiveResourceRollbackError("stopped/kernel gate changed before restart")
        if journal.read()!=original:
            raise FiveResourceRollbackError("whole intent changed before restart")

        if saved_process["observation"]["engine"]["state"]=="running":
            start_previous()
        # Whether prior topology was STOPPED or RUNNING, probe twice.
        result_state = _verify_restart(
            process_probe, saved_process, expected_scripts,previous_backup,
        )
        require_lifecycle_owner()
        if observe_owned_ipfw(ledger,read_ipfw_adapter) != \
           original["previous"]["firewall"]:
            raise FiveResourceRollbackError("IPFW ownership changed after prior restart")
        if observe_live_files(
            config_path,active_runtime,previous_backup=previous_backup
        ) != prior_files or journal.read()!=original or \
           ledger.owned()!=old_owner or ledger.pending() is not None:
            raise FiveResourceRollbackError("five-resource recovery postcheck failed")
        _locked_config(config_path,fd,expected_owner)
        # One last durable witness must be written BEFORE unlocking Config:
        # calling it after this function returns is a TOCTOU error.
        # No receipt ever commits/removes the still-MUTATING whole intent.
        receipt_state="not-sealed"
        attestation=None
        if seal_previous is not None:
            if not callable(seal_previous):
                raise FiveResourceRollbackError("invalid sealed recovery receipt owner")
            attestation=seal_previous(fd)
            if not isinstance(attestation,dict) or (
                attestation.get("state") not in (
                    "previous-receipt-sealed","previous-receipt-already-sealed",
                )
                or attestation.get("can_finish_intent") is not False
            ):
                raise FiveResourceRollbackError("durable previous receipt refused")
            receipt_state=attestation["state"]
        _locked_config(config_path,fd,expected_owner)
        require_lifecycle_owner()
        actual=journal.read()
        completion_phase="mutating"
        if attestation is not None and (
            attestation.get("whole_intent_phase")=="rolled_back"
        ):
            if actual is None or actual["phase"]!="rolled_back":
                raise FiveResourceRollbackError("durable rollback seal missing")
            prior={k:v for k,v in actual.items() if k!="check"}
            prior["phase"]="mutating"
            if _digest(prior)!=original["check"] or (
                prior["previous"]!=original["previous"]
                or prior["candidate"]!=original["candidate"]
            ):
                raise FiveResourceRollbackError("foreign rollback seal")
            completion_phase="rolled_back"
        elif actual!=original:
            raise FiveResourceRollbackError("whole intent changed after receipt")

        return {
            "recovery_receipt":receipt_state,
            "state":"five-previous-domains-observed",
            "config":"previous", "runtime":"previous",
            "engine":result_state,"supervisor":result_state,
            "ipfw":"previous",
            "whole_intent_phase":completion_phase,
            "safe_to_clear_intent":False,
            "safe_to_enable_voice":False,
            "requires_durable_restart_finalization":True,
        }
    finally:
        os.close(fd)
