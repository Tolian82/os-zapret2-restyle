#!/usr/bin/env python3
"""Native Voice forward Apply, phase 0: durable *prepared* schema-4 intent.

A REAL fsync-backed forward preparation combining the existing bound release,
the sealed previous five-resource checkpoint, immutable previous process
security evidence and exact staged candidate runtime. Unlike the mock-only
coordinator this is the actual preparation primitive for native Voice Apply.

NO CLI, configd, GUI or boot caller yet: the entire forward five-resource
execution/rollback and on-device acceptance are not qualified. The only
write is whole journal intent.json in PREPARED, NEVER MUTATING; it must be
performed under an already held original Config flock and lifecycle FD9.

A prepared record is intentionally not silently undone on failure: the
legacy service sees it and blocks unsafe start until manual reconciliation.
"""
from __future__ import annotations

import os
from pathlib import Path

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import (
    VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA, RUNTIME_FIELD, BOUND_FIELD,
)
from voice_cutover_close import NAME as CLOSE_NAME, ARCHIVE
from voice_firewall_ledger import (
    VoiceOwnershipStore, canonical_manifest, fingerprint,
)
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_file_observer import observe_live_files
from voice_process_recovery_evidence import inspect_process_evidence
from voice_security_policy_evidence import inspect_security_policy
from voice_native_recovery_quiescence import _locked_config
from voice_cutover_coordinator import validate_proof


class ForwardPrepareError(RuntimeError):
    pass


def _witness(previous, observer, *, require_owner):
    """Double-sample all five previous domains before any journal write."""
    require_owner()
    first=observer.observe()
    if first!=previous:
        raise ForwardPrepareError("previous five-resource state not intact")
    require_owner()
    if observer.observe()!=first:
        raise ForwardPrepareError("previous five-resource state changed")
    return first


def prepare_forward_voice_intent(
    *, journal, ledger, previous_backup, process_evidence, security_evidence,
    previous_observer, config_path, active_runtime, staged_config,
    candidate_runtime, proof, desired_manifest, expected_scripts,
    ipfw_adapter, config_fd, config_owner, require_lifecycle_owner,
):
    """Persist PREPARED schema-4 whole journal, leaving live service intact.

    Caller must supply a native FD9-bound observer and truly read-only IPFW
    adapter. No ownership seed or IPFW mutation occurs inside this function.
    """
    from voice_ipfw_adapter import FreeBSDIPFWAdapter
    from voice_native_full_observer import NativePreviousObserver
    from voice_cutover_backup import _private_dir
    from voice_cutover_journal import CutoverJournalError

    if not isinstance(journal,VoiceCutoverJournal) or (
        not isinstance(ledger,VoiceOwnershipStore)
        or not isinstance(ipfw_adapter,FreeBSDIPFWAdapter)
        or ipfw_adapter.allow_mutations is not False
        or not isinstance(previous_observer,NativePreviousObserver)
        or not callable(require_lifecycle_owner)
    ):
        raise ForwardPrepareError("untrusted native whole-service preparation")
    config_path,active_runtime=Path(config_path),Path(active_runtime)
    previous_backup=Path(previous_backup)
    staged_config,candidate_runtime=Path(staged_config),Path(candidate_runtime)
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    _pinned_regular(config_path,config_fd,owner=config_owner)
    if os.path.lexists(journal.directory/CLOSE_NAME) or (
        os.path.lexists(journal.directory/ARCHIVE)
    ) or journal.read() is not None:
        raise ForwardPrepareError("previous or active Voice whole intent remains")
    # An IPFW owner must have been EXPLICITLY seeded under the same native
    # lifecycle lock, never inferred from a guessed rule number.
    if ledger.pending() is not None:
        raise ForwardPrepareError("unresolved native IPFW transaction")
    old_owner=ledger.owned()
    if old_owner is None:
        raise ForwardPrepareError("native Voice IPFW previous owner is not sealed")
    desired_canon=canonical_manifest(desired_manifest)
    desired_digest=fingerprint(desired_canon)
    validate_proof(proof)
    if not proof["enabled_services"] or not desired_manifest["tables"] or (
        proof["rule_base"]!=desired_manifest["rule_base"]
        or proof["rule_max"]!=desired_manifest["rule_max"]
        or proof["rule_count"]!=len(desired_manifest["rules"])
        or proof["table_count"]!=len(desired_manifest["tables"])
    ):
        raise ForwardPrepareError("Voice ON handoff does not match native IPFW")
    prior=bound_resource_fingerprints(previous_backup)
    processes=inspect_process_evidence(
        process_evidence,previous_backup,expected_scripts,
    )
    previous={**prior,**processes["previous"]}
    if "firewall" in previous:
        raise ForwardPrepareError("process witness attempts to overwrite IPFW")
    previous["firewall"]=fingerprint(canonical_manifest(old_owner))
    if set(previous)!={"config","runtime","engine","supervisor","firewall"}:
        raise ForwardPrepareError("incomplete old five-resource SHA")
    policy=inspect_security_policy(
        security_evidence,previous_backup,process_evidence,
        expected_scripts=expected_scripts,
    )
    if policy["policy"]["previous"]!=previous:
        raise ForwardPrepareError("native supervisor security policy differs")
    if observe_owned_ipfw(ledger,ipfw_adapter)!=previous["firewall"]:
        raise ForwardPrepareError("original scoped IPFW no longer belongs to ledger")
    if observe_live_files(
        config_path,active_runtime,previous_backup=previous_backup,
    )!=prior:
        raise ForwardPrepareError("previous Config/runtime bytes are not active")
    if observe_live_files(
        staged_config,candidate_runtime,
    )["config"]!=proof["saved_xml_sha256"]:
        raise ForwardPrepareError("candidate staged OPNsense Config differs from proof")
    _witness(previous,previous_observer,require_owner=require_lifecycle_owner)
    _locked_config(config_path,config_fd,config_owner)
    # Reopening stable journal/ledger just before the ONLY disk mutation
    # rejects a replaced proof/owner or a racing already-started cutover.
    if ledger.owned()!=old_owner or ledger.pending() is not None or (
        journal.read() is not None
    ):
        raise ForwardPrepareError("another native owner started cutover")
    journal.begin_runtime_bound(
        previous,proof,desired_manifest,security_evidence,previous_backup,
        process_evidence,expected_scripts,
        staged_config=staged_config,candidate_runtime=candidate_runtime,
    )
    # Do not advance PREPARED to MUTATING. On error retain journal to require
    # manual review of a potentially durable prepared intent.
    sealed=journal.read()
    if sealed is None or sealed["phase"]!="prepared" or (
        sealed["schema"]!=RUNTIME_BOUND_SCHEMA
        or sealed["previous"]!=previous
        or sealed["candidate"][BOUND_FIELD]!=desired_digest
        or sealed["candidate"][RUNTIME_FIELD] is None
    ):
        raise ForwardPrepareError("prepared Voice forward journal not durably sealed")
    require_lifecycle_owner()
    _locked_config(config_path,config_fd,config_owner)
    if ledger.owned()!=old_owner or ledger.pending() is not None:
        raise ForwardPrepareError("native firewall owner changed after prepared journal")
    return {
        "state":"native-voice-forward-prepared-not-mutating",
        "whole_check":sealed["check"],
        "previous":previous,
        "desired_ipfw_sha256":desired_digest,
        "candidate_runtime_sha256":sealed["candidate"][RUNTIME_FIELD],
        "safe_to_start":False,
        "safe_to_mutate":False,
        "voice_on":False,
    }
