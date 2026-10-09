#!/usr/bin/env python3
"""Staging-only read-only cross-journal Voice recovery triage.

Does NOT enable activation, replay, IPFW access or boot recovery.
"""
from __future__ import annotations
from pathlib import Path
from voice_cutover_backup import bound_resource_fingerprints
from voice_firewall_ledger import LedgerError, canonical_manifest, fingerprint


def _result(state, reason, **extras):
    return {"schema": 1, "state": state, "reason": reason,
            "can_activate": False, "can_recover_automatically": False,
            "safe_to_mutate": False, **extras}


def inspect_recovery(cutover, firewall, previous_backup: Path) -> dict:
    """Cross-check immutable previous bytes and two durable journal records.

    Previous firewall SHA must be the canonical ownership manifest fingerprint.
    There is no desired firewall SHA in the whole journal schema 1, so unknown
    post-cutover ownership cannot be accepted as safe or automatically restored.
    """
    try:
        record = cutover.read()
        owned = firewall.owned() if firewall is not None else None
        pending = firewall.pending() if firewall is not None else None
        if record is None:
            if pending is not None:
                return _result("blocked", "orphan-ipfw-intent")
            if owned is not None:
                return _result("blocked", "native-ipfw-owner-without-cutover")
            return _result("no-intent", "no-recovery-evidence")
        phase = record["phase"]
        if firewall is None:
            return _result("blocked", "missing-ipfw-ledger", phase=phase)
        bound_resource_fingerprints(previous_backup, record["previous"])
        prior = record["previous"]["firewall"]
        if pending is not None:
            if pending["previous_sha256"] != prior:
                return _result("blocked", "cross-journal-previous-ipfw-mismatch",
                               phase=phase)
            if owned is None:
                return _result("blocked", "missing-ipfw-ownership", phase=phase)
            current = fingerprint(canonical_manifest(owned))
            if current not in (pending["previous_sha256"], pending["desired_sha256"]):
                return _result("blocked", "unrecognized-ipfw-owner", phase=phase)
            if pending["phase"] == "prepared" and current != prior:
                return _result("blocked", "premature-ipfw-ownership-change", phase=phase)
            if phase == "prepared" or (phase == "committed" and pending["phase"] != "mutating"):
                return _result("blocked", "inconsistent-journal-phase",
                               phase=phase, ipfw_phase=pending["phase"])
            if phase == "committed" and current != pending["desired_sha256"]:
                return _result("blocked", "uncommitted-ipfw-ownership", phase=phase)
            return _result("review-required", "dual-journals-bound",
                           phase=phase, ipfw_phase=pending["phase"])
        if owned is None:
            return _result("blocked", "missing-ipfw-ownership", phase=phase)
        if fingerprint(canonical_manifest(owned)) != prior:
            return _result("blocked", "unbound-ipfw-ownership", phase=phase)
        return _result("review-required", "previous-snapshot-bound", phase=phase)
    except (OSError, ValueError, TypeError, KeyError, LedgerError):
        return _result("blocked", "invalid-or-untrusted-recovery-evidence")
