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
from voice_cutover_close import NAME as CLOSE_NAME, ARCHIVE as CLOSED_ARCHIVE
from shared_apply_operation import SharedApplyOperation, SharedOperationError

WHOLE_ROOT = Path("/var/db/zapret2/voice-cutover")
IPFW_ROOT = Path("/var/db/zapret2/voice-ipfw")


def _present(path: Path) -> bool:
    """lstat catches symlinks, including dangling links, as unsafe objects."""
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def check_pending(whole_root: Path, ipfw_root: Path, shared_root: Path | None = None) -> dict:
    """Return a bounded, machine-readable advisory without kernel reads."""
    try:
        # One shared Strategies/Voice Apply operation is stronger than the
        # ordinary lifecycle, including on reboot after power loss. Keep the
        # legacy guard as a bounded compatibility check, not a second writer.
        if shared_root is None:
            shared_root = whole_root.with_name("shared-apply")
        shared = SharedApplyOperation(shared_root).advisory()
        if not shared["safe_to_mutate"]:
            return shared
        # A durable old-PoC pre-stop intent is a sibling, not a member of
        # the strictly sealed rollback stage tree. Even orphaned after an
        # interrupted power cut, it is NEVER ordinary-start authority.
        old_quiescence=whole_root.with_name(whole_root.name+"-legacy-quiescence-intent")
        if _present(old_quiescence):
            return {
                "state": "blocked", "reason": "legacy-quiescence-intent-retained",
                "safe_to_mutate": False,
            }
        if _present(whole_root):
            # Once the rollback is archived, intent.json is intentionally absent.
            # Its closure WAL and immutable archive MUST still block legacy
            # lifecycle and cannot be treated as permission to start.
            if _present(whole_root / CLOSE_NAME) or _present(whole_root / CLOSED_ARCHIVE):
                return {
                    "state": "blocked", "reason": "native-closure-retained",
                    "safe_to_mutate": False,
                }
            state = VoiceCutoverJournal(whole_root).inspect()
            if state != "no-intent":
                return {
                    "state": "blocked", "reason": "whole-runtime-intent",
                    "phase": state, "safe_to_mutate": False,
                }
            # The legacy checkpoint command intentionally leaves ONLY a
            # sealed "previous" snapshot without taking over ordinary
            # start/stop/reconfigure. Preserve that established contract.
            # Any MORE ADVANCED five-domain staging, or a foreign artifact,
            # without intent.json means power loss or ambiguous ownership.
            entries = set(os.listdir(whole_root))
            if entries - {"previous"}:
                return {
                    "state": "blocked", "reason": "orphan-native-voice-evidence",
                    "safe_to_mutate": False,
                }
        # A whole old-PoC rollback receipt lives beside the strict stage
        # root. It must block lifecycle even if that root was lost or
        # accidentally removed: absence of WAL is not proof of no intent.
        old_receipt=whole_root.with_name(whole_root.name+"-legacy-whole-receipt")
        if _present(old_receipt):
            return {
                "state": "blocked", "reason": "legacy-whole-receipt-retained",
                "safe_to_mutate": False,
            }
        if _present(ipfw_root):
            ledger = VoiceOwnershipStore(ipfw_root)
            pending = ledger.pending()
            if pending is not None:
                return {
                    "state": "blocked", "reason": "ipfw-intent",
                    "phase": pending["phase"], "safe_to_mutate": False,
                }
            # Once *native* Voice owns an IPFW range, starting the legacy
            # PoC would be a second, unrelated owner even after the intent
            # was committed. This legacy-only service wrapper must refuse
            # until it is explicitly replaced by native ownership routing.
            if ledger.owned() is not None:
                return {
                    "state": "blocked", "reason": "native-ipfw-owned",
                    "safe_to_mutate": False,
                }
        return {"state": "clear", "safe_to_mutate": True}
    except (OSError, ValueError, LedgerError, CutoverJournalError, SharedOperationError):
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
