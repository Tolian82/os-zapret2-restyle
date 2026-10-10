#!/usr/bin/env python3
"""Read-only, fail-closed five-resource Voice restart-attestation contract.

STAGING ONLY: no CLI, configd action, locks, process control or kernel adapter.
Inputs from the *injected* observer are untrusted observations, NOT permission
to replay, stop, start or mark journals complete. In particular, a schema-2
cutover journal does not bind the desired Config/runtime/engine/supervisor;
a matching previous snapshot cannot prove a committed desired state.
"""
from __future__ import annotations

from pathlib import Path

from voice_cutover_backup import (
    VoiceBackupError, bound_resource_fingerprints,
)
from voice_cutover_journal import (
    CutoverJournalError, RESOURCE_NAMES, SECURITY_BOUND_SCHEMA,
)
from voice_cutover_recovery_preflight import inspect_recovery
from voice_security_policy_evidence import (
    SecurityPolicyError, inspect_security_policy, verify_current_security,
)
from voice_firewall_ledger import LedgerError
from voice_process_recovery_evidence import (
    ProcessEvidenceError, inspect_process_evidence,
)

_HEX = set("0123456789abcdef")


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _result(state, reason, *, phase=None, domains=None, cross_journal_reason=None):
    """Every outcome is non-authorizing, including full previous-state match."""
    return {"schema": 1, "state": state, "reason": reason,
            "phase": phase, "domains": domains or {},
            "cross_journal_reason": cross_journal_reason,
            "can_activate": False, "can_recover_automatically": False,
            "safe_to_mutate": False, "safe_to_finish_intent": False}


def _sample(observer):
    """Invoke a read-only-only injected observer; reject partial/foreign data."""
    value = observer.observe()
    if not isinstance(value, dict) or set(value) != set(RESOURCE_NAMES) or \
       any(not _sha(v) for v in value.values()):
        raise ValueError("untrusted or incomplete live resource inventory")
    return {name: value[name] for name in RESOURCE_NAMES}


def inspect_full_recovery(cutover, firewall, previous_backup: Path,
                          process_evidence: Path, expected_executables: dict,
                          observer, *, security_evidence: Path | None = None,
                          security_reader=None) -> dict:
    """Correlate sealed previous Config/runtime, process evidence and journals.

    This is intentionally an OFFLINE DECISION CONTRACT, not a recovery plan.
    The injected observer must eventually prove actual on-router hashes for
    Config, runtime, engine process, supervisor and *kernel* IPFW rules.
    That adapter does NOT exist yet. A previous-running PID/start identity
    cannot be reused as evidence of recovery after reboot.
    """
    try:
        record = cutover.read()
        if record is None:
            return _result("blocked", "missing-whole-cutover-intent")
        phase = record["phase"]
        cross = inspect_recovery(cutover, firewall, previous_backup)
        if cross["state"] != "review-required":
            return _result("blocked", "cross-journal-not-bound",
                           phase=phase, cross_journal_reason=cross["reason"])

        old_files = bound_resource_fingerprints(previous_backup, record["previous"])
        old_process = inspect_process_evidence(
            process_evidence, previous_backup, expected_executables,
            record["previous"],
        )
        prior = {**old_files, **old_process["previous"],
                 "firewall": record["previous"]["firewall"]}
        if set(prior) != set(RESOURCE_NAMES):
            raise ValueError("incomplete previous Voice snapshot")

        sealed_security = None
        if record["schema"] == SECURITY_BOUND_SCHEMA:
            if security_evidence is None or security_reader is None:
                return _result("blocked", "missing-native-security-attestation",
                               phase=phase, cross_journal_reason=cross["reason"])
            sealed_security = inspect_security_policy(
                security_evidence, previous_backup, process_evidence,
                journal_record=record, expected_scripts=expected_executables,
            )
            policy = sealed_security["policy"]
            if (getattr(security_reader, "expected_scripts", None) != policy["scripts"]
                or getattr(security_reader, "kernel_images", None) != policy["images"]
                or getattr(security_reader, "credentials", None) != policy["credentials"]):
                return _result("blocked", "foreign-native-security-reader",
                               phase=phase, cross_journal_reason=cross["reason"])
            security_report = security_reader.inspect_twice()
            if not verify_current_security(security_report, sealed_security):
                return _result("blocked", "native-security-policy-mismatch",
                               phase=phase, cross_journal_reason=cross["reason"])
            observed_roles = security_report["roles"]
            old_roles = {"engine": old_process["observation"]["engine"]["process"],
                         "daemon": old_process["observation"]["supervisor"]["daemon"],
                         "monitor": old_process["observation"]["supervisor"]["monitor"]}
            if any(observed_roles[role]["pid"] != old_roles[role]["pid"] or
                   observed_roles[role]["start_ns"] != old_roles[role]["start_ns"]
                   for role in old_roles):
                return _result("blocked", "security-process-instance-differs",
                               phase=phase, cross_journal_reason=cross["reason"])

        first = _sample(observer)
        second = _sample(observer)
        # After both observations, the immutable sources and BOTH journals
        # must still describe the same intended old snapshot.
        if sealed_security is not None and (
            inspect_security_policy(
                security_evidence, previous_backup, process_evidence,
                journal_record=record, expected_scripts=expected_executables,
            )["policy_sha256"] != sealed_security["policy_sha256"] or
            security_reader.inspect_twice() != security_report
        ):
            return _result("blocked", "unstable-native-security-attestation",
                           phase=phase, cross_journal_reason=cross["reason"])
        if first != second or cutover.read() != record or \
           inspect_recovery(cutover, firewall, previous_backup) != cross or \
           bound_resource_fingerprints(previous_backup, record["previous"]) != old_files or \
           inspect_process_evidence(
               process_evidence, previous_backup, expected_executables,
               record["previous"],
           )["previous"] != old_process["previous"]:
            return _result("blocked", "unstable-recovery-observation", phase=phase,
                           cross_journal_reason=cross["reason"])

        domains = {name: ("previous" if first[name] == prior[name]
                          else "unknown-or-changed") for name in RESOURCE_NAMES}

        if phase == "committed":
            # Only IPFW desired hash is durable in schema 2. The other four
            # desired-resource digests are missing; never infer a good commit
            # by matching an old process or just the IPFW ownership ledger.
            return _result("blocked", "committed-system-not-fully-attestable",
                           phase=phase, domains=domains,
                           cross_journal_reason=cross["reason"])

        if any(value != "previous" for value in domains.values()):
            return _result("blocked", "mixed-or-untrusted-previous-state",
                           phase=phase, domains=domains,
                           cross_journal_reason=cross["reason"])

        # Even an exact five-way match cannot authorize a replay: process
        # fingerprints are snapshots, IPFW needs live kernel proof, and the
        # cutover intent remains durable until a real locked restorer exists.
        return _result("review-required", "all-previous-fingerprints-observed",
                       phase=phase, domains=domains,
                       cross_journal_reason=cross["reason"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            VoiceBackupError, ProcessEvidenceError, CutoverJournalError,
            LedgerError, RuntimeError, SecurityPolicyError):
        return _result("blocked", "invalid-or-incomplete-whole-system-evidence")
