#!/usr/bin/env python3
"""Read-only boot/lifecycle gate for an unfinished native Voice cutover.

This protects the EXISTING legacy service while the production Voice Apply
adapter is not yet available. It never removes/creates journals, touches
IPFW, changes config.xml, or starts/kills dvtws2.

The calling zapret_service.sh holds the existing /usr/bin/lockf lifecycle
lock. Unexpected owner, symlink, corrupted or incomplete journal MUST
block any lifecycle mutation pending explicit supervised recovery.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from voice_cutover_journal import VoiceCutoverJournal, CutoverJournalError
from voice_firewall_ledger import VoiceOwnershipStore, LedgerError

WHOLE_ROOT = Path("/var/db/zapret2/voice-cutover")
IPFW_ROOT = Path("/var/db/zapret2/voice-ipfw")


def _present(path: Path) -> bool:
    """lstat catches symlinks, including dangling links, as unsafe objects."""
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def check_pending(whole_root: Path, ipfw_root: Path) -> dict:
    """Return a bounded, machine-readable advisory without kernel reads."""
    try:
        if _present(whole_root):
            state = VoiceCutoverJournal(whole_root).inspect()
            if state != "no-intent":
                return {
                    "state": "blocked", "reason": "whole-runtime-intent",
                    "phase": state, "safe_to_mutate": False,
                }
        if _present(ipfw_root):
            pending = VoiceOwnershipStore(ipfw_root).pending()
            if pending is not None:
                return {
                    "state": "blocked", "reason": "ipfw-intent",
                    "phase": pending["phase"], "safe_to_mutate": False,
                }
        return {"state": "clear", "safe_to_mutate": True}
    except (OSError, ValueError, LedgerError, CutoverJournalError):
        # Do not leak file contents/config/kernel state into configd logs.
        return {
            "state": "blocked", "reason": "invalid-or-untrusted-journal",
            "safe_to_mutate": False,
        }


def main(argv: list[str]) -> int:
    # No CLI-specified directory or bypass flag exists in the production
    # executable; unit tests call check_pending() using private temp dirs.
    if len(argv) != 1:
        return 64
    result = check_pending(WHOLE_ROOT, IPFW_ROOT)
    if result["safe_to_mutate"]:
        return 0
    print("ERROR: unfinished or untrusted native Voice journal; "
          "existing Zapret2 lifecycle mutation blocked until verified recovery",
          file=sys.stderr)
    return 69


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
