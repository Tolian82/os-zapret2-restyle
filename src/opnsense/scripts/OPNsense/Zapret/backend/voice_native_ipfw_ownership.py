#!/usr/bin/env python3
"""Unwired, read-only FreeBSD IPFW ownership witness for Voice cutover.

Checks the kernel's complete plugin-owned rule interval plus all five active
and stage tables against the durable ownership ledger. It NEVER adopts
foreign rules, claims an incomplete commit, mutates IPFW or authorizes Apply.
An exact comparison returns the LEDGER's canonical fingerprint so unordered
IPFW address-table enumeration cannot produce false mismatches.
A caller still needs native Config/lifecycle locks and complete independent
engine/supervisor and Config evidence before any recovery operation.
"""
from __future__ import annotations

from voice_firewall_ledger import (
    LedgerError, canonical_manifest, fingerprint,
)
from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, VoiceFirewallError, table_contents_equal,
)
from voice_ipfw_adapter import FreeBSDIPFWAdapter, IPFWAdapterError


class KernelOwnershipError(ValueError):
    pass


def observe_owned_ipfw(store, adapter: FreeBSDIPFWAdapter) -> str:
    """Return a matching 64-byte canonical SHA256 digest, otherwise refuse.

    This is a deliberately restrictive witness of the CURRENT ledger owner.
    It cannot authorize a desired-target commit or recover orphaned kernel
    objects. The caller must independently verify that the journal owner is
    itself bound to the previous/desired whole-cutover transaction.
    """
    if not isinstance(adapter, FreeBSDIPFWAdapter) or \
       adapter.allow_mutations is not False:
        raise KernelOwnershipError("a non-mutating native IPFW adapter is required")
    try:
        owned = store.owned()
        pending = store.pending()
        if owned is None:
            raise KernelOwnershipError("no durable Voice IPFW owner to compare")
        original = canonical_manifest(owned)
        if adapter.rule_base != owned["rule_base"] or \
           adapter.rule_max != owned["rule_max"]:
            raise KernelOwnershipError("native IPFW interval differs from owner")
        rules = adapter.list_rules(owned["rule_base"], owned["rule_max"])
        if rules != owned["rules"]:
            raise KernelOwnershipError("native IPFW rules are not precisely owned")

        for service in SERVICES:
            name = TABLE_PREFIX + service
            live = adapter.get_table(name)
            if not table_contents_equal(live, owned["tables"].get(name)):
                raise KernelOwnershipError(
                    "native IPFW address table disagrees with durable ownership"
                )
            if adapter.get_table(name + "_stage") is not None:
                raise KernelOwnershipError("unresolved native IPFW stage table")

        if store.owned() != owned or store.pending() != pending:
            raise KernelOwnershipError("durable Voice IPFW ledger changed during inspection")
        return fingerprint(original)
    except (IPFWAdapterError, LedgerError, VoiceFirewallError) as exc:
        raise KernelOwnershipError("untrusted native IPFW read-only evidence") from exc
