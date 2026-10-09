#!/usr/bin/env python3
"""Read-only Voice IPFW ownership inspector for FreeBSD OPNsense.

Never modifies kernel, dvtws2, config.xml or ledger. Do not use this utility
as an unattended repair daemon. When ownership is not proven, report blocked.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from voice_firewall_ledger import LedgerError, VoiceOwnershipStore
from voice_cutover_journal import CutoverJournalError, VoiceCutoverJournal
from voice_ipfw_adapter import FreeBSDIPFWAdapter, IPFWAdapterError
from voice_firewall_transaction import (
    SERVICES, TABLE_PREFIX, VoiceFirewallError, table_contents_equal,
)


class VoiceInspectError(RuntimeError):
    pass


def examine(store, adapter, cutover=None) -> dict:
    """Inspect without side effects; 'ready' requires exact owned kernel state.

    An incomplete whole-runtime Config/engine/IPFW transition takes priority
    even if this moment's individual IPFW rules happen to appear correct.
    """
    if cutover is not None:
        phase = cutover.inspect()
        if phase != "no-intent":
            return {
                "state": "interrupted",
                "condition": phase,
                "can_activate": False,
                "remedy": "whole-runtime-manual-review",
            }
    if store.pending() is not None:
        condition = store.inspect(adapter)
        return {
            "state": "interrupted",
            "condition": condition,
            "can_activate": False,
            "remedy": "manual-inspection" if condition == "manual-review"
                      else "verified-recovery-required",
        }

    expected = store.owned()
    if expected is None:
        return {
            "state": "uninitialized",
            "can_activate": False,
            "remedy": "explicit-ownership-adoption-required",
        }
    if adapter.rule_base != expected["rule_base"] or \
       adapter.rule_max != expected["rule_max"]:
        return {"state": "mismatched-range", "can_activate": False,
                "remedy": "manual-inspection"}

    # Inspect *all* service tables (even if OFF) to catch foreign/stale
    # tables before enabling a service for the first time.
    observed = adapter.list_rules(expected["rule_base"], expected["rule_max"])
    if observed != expected["rules"]:
        return {"state": "foreign-or-modified-rules", "can_activate": False,
                "remedy": "manual-inspection"}
    for name in SERVICES:
        table = TABLE_PREFIX + name
        if not table_contents_equal(adapter.get_table(table), expected["tables"].get(table)):
            return {
                "state": "foreign-or-modified-table",
                "service": name,
                "can_activate": False,
                "remedy": "manual-inspection",
            }
        if adapter.get_table(table + "_stage") is not None:
            return {
                "state": "orphan-stage-table",
                "service": name,
                "can_activate": False,
                "remedy": "manual-inspection",
            }
    return {"state": "ready", "can_activate": True,
            "rule_count": len(observed), "table_count": len(expected["tables"])}


def main(args: list[str]) -> int:
    if len(args) != 1:
        print("usage: voice_live_inspect.py", file=sys.stderr)
        return 64
    try:
        # A whole-runtime cutover intent is stronger than a momentary IPFW
        # observation: deny readiness even when the per-IPFW ledger is absent.
        cutover_dir = Path("/var/db/zapret2/voice-cutover")
        cutover = None
        if cutover_dir.exists() or cutover_dir.is_symlink():
            cutover = VoiceCutoverJournal(cutover_dir)
            status = cutover.inspect()
            if status != "no-intent":
                print(json.dumps({
                    "state": "interrupted", "condition": status,
                    "can_activate": False, "remedy": "whole-runtime-manual-review",
                }, sort_keys=True))
                return 2
        # Fixed private path. The production code must explicitly prepare
        # the directory under the existing lifecycle lock after migration.
        directory = Path("/var/db/zapret2/voice-ipfw")
        if not directory.exists() and not directory.is_symlink():
            print(json.dumps({"state": "uninitialized", "can_activate": False,
                              "remedy": "explicit-ownership-adoption-required"},
                             sort_keys=True))
            return 2
        store = VoiceOwnershipStore(directory)
        adapter = FreeBSDIPFWAdapter(19000, 19010)
        report = examine(store, adapter, cutover)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["state"] == "ready" else 2
    except (OSError, ValueError, VoiceFirewallError, LedgerError,
            IPFWAdapterError, CutoverJournalError) as error:
        # Never dump kernel rule text, sensitive config or tables to stdout.
        print(json.dumps({
            "state": "inspection-error",
            "can_activate": False,
            "remedy": "manual-inspection",
            "error": type(error).__name__,
        }, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
