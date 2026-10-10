#!/usr/bin/env python3
"""Injected-adapter Voice IPFW activation controller: NOT attached to service.

This module tests the ordering contract under the existing lifecycle lock:
verified old ownership -> durable intent -> mutate -> committed ownership ->
verified cleanup -> journal finish. It never invokes IPFW on import and has
no CLI entrypoint. Wiring it into OPNsense requires an audited FreeBSD
adapter, complete dvtws2/config tree handoff and rollback, and migration.
"""
from __future__ import annotations

from voice_firewall_transaction import (
    VoiceFirewallError, apply_transaction, verify_prior_state,
    cleanup_committed, table_contents_equal,
)
from voice_firewall_ledger import VoiceOwnershipStore, LedgerError


class VoiceActivationError(VoiceFirewallError):
    pass


def activate_mockable(adapter, ledger: VoiceOwnershipStore,
                      previous: dict, desired: dict) -> None:
    """No implicit lock: caller MUST already hold zapret2's lifecycle lock."""
    if ledger.pending() is not None:
        raise VoiceActivationError("pending Voice intent requires restart review")
    if ledger.owned() != previous:
        raise VoiceActivationError("current IPFW ownership differs from trusted manifest")
    # No state mutation before both checks complete.
    verify_prior_state(adapter, previous, desired)
    ledger.begin(previous, desired)
    ledger.mark_mutating()   # fsync before first kernel action

    try:
        apply_transaction(adapter, previous, desired)
    except Exception:
        # Only an exact restored previous state permits automatic rollback
        # bookkeeping. Any partial/ambiguous state retains the intent for
        # manual inspection: never silently certify a broken firewall.
        if ledger.inspect(adapter) == "previous-intact":
            ledger.abort(adapter)
        raise

    # On successful IPFW replacement the desired kernel rules are observable.
    # The in-memory unit tests model this kernel view; a real adapter must
    # independently prove it and the dvtws2 runtime before commit.
    if adapter.list_rules(desired["rule_base"], desired["rule_max"]) != desired["rules"]:
        raise VoiceActivationError("post-install Voice IPFW rules differ from candidate")
    for table, targets in desired["tables"].items():
        if not table_contents_equal(adapter.get_table(table), targets):
            raise VoiceActivationError("post-install Voice IPFW table differs from candidate")

    # Any failure here leaves the durable intent and never enables a new
    # Apply request. A real orchestrator must restore the complete previous
    # release and supervisor as well as IPFW; this mock-only controller does
    # not claim a production-ready end-to-end transaction.
    ledger.commit(desired)
    cleanup_committed(adapter, previous, desired)
    ledger.finish(adapter)
