#!/usr/bin/env python3
"""Read-only legacy five-domain rollback disk triage under original FD9/Config.

This is an operator-only inspect route. It never invokes an old reverse
actuator, starts/stops processes, touches IPFW, closes journals or authorizes
native Voice. Receipt-valid means only *disk* proof; cold-boot running kernel
and process epochs require explicit independent live reconciliation.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import sys

from voice_cutover_backup import _private_dir
from voice_cutover_config_restore import _pinned_regular
from voice_native_recovery_quiescence import _locked_config
from voice_native_legacy_five_domain_coordinator import FIRST, STAGES, _prefix
from voice_native_legacy_whole_receipt import (
    inspect_legacy_whole_receipt, receipt_directory,
)
import voice_ipfw_runtime as native


class LegacyBootReviewError(RuntimeError):
    pass


def inspect_legacy_boot_disk(*, root, config_path, config_fd, config_owner,
                             require_lifecycle_owner):
    """Never infer live restoration from on-disk stage names or a checksum."""
    if not callable(require_lifecycle_owner):
        raise LegacyBootReviewError("original lifecycle lock required")
    root = Path(root)
    def held():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        _pinned_regular(Path(config_path), config_fd, owner=config_owner)
    held()
    receipt = receipt_directory(root)
    root_exists = os.path.lexists(root)
    receipt_exists = os.path.lexists(receipt)
    if receipt_exists:
        # This validates ALL nine trees and the original process receipt.
        # If the primary root was lost, the receipt MUST NOT rescue it.
        sealed = inspect_legacy_whole_receipt(root)
        held()
        if inspect_legacy_whole_receipt(root) != sealed:
            raise LegacyBootReviewError("whole receipt changed during disk inspection")
        return {
            "state": "legacy-whole-disk-valid-live-boot-recheck-required",
            "previous_five": sealed["previous_five"],
            "completed_stages": len(STAGES),
            "safe_to_mutate": False, "safe_to_start": False,
            "safe_to_enable_voice": False, "public_voice_apply": False,
            "boot_recovery_validated": False, "media_pass": False,
        }
    if not root_exists:
        held()
        if os.path.lexists(root) or os.path.lexists(receipt):
            raise LegacyBootReviewError("journal appeared during disk inspection")
        return {
            "state": "no-legacy-five-domain-journal-observed",
            "safe_to_mutate": False, "safe_to_start": False,
            "public_voice_apply": False, "boot_recovery_validated": False,
        }
    _private_dir(root)
    entries = set(os.listdir(root))
    if not (set(FIRST) <= entries):
        # Ordinary native prior checkpoint/cutover is NOT old PoC evidence.
        # Do not claim that native or ordinary lifecycle is safe here.
        held()
        if set(os.listdir(root)) != entries or os.path.lexists(receipt):
            raise LegacyBootReviewError("unknown journal changed during read")
        return {
            "state": "not-a-legacy-five-domain-journal",
            "safe_to_mutate": False, "safe_to_start": False,
            "public_voice_apply": False, "boot_recovery_validated": False,
        }
    phase = _prefix(root)  # Exact monotonic prefix, foreign => manual review.
    held()
    if _prefix(root) != phase or os.path.lexists(receipt):
        raise LegacyBootReviewError("old five-domain journal changed during read")
    # Stage directories record INTENT, not necessarily durable completion.
    return {
        "state": "legacy-five-domain-incomplete-manual-review",
        "stage_directories_present": phase,
        "stages_total": len(STAGES),
        "safe_to_mutate": False, "safe_to_start": False,
        "public_voice_apply": False, "boot_recovery_validated": False,
    }


def main(argv):
    if argv != ["inspect"]:
        return 64
    fd = None
    try:
        native.require_native_lock()
        fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        _pinned_regular(native.CONFIG, fd, owner=(0,0))
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = inspect_legacy_boot_disk(
            root=native.WHOLE, config_path=native.CONFIG, config_fd=fd,
            config_owner=(0,0), require_lifecycle_owner=native.require_native_lock,
        )
        print("legacy-voice-boot-review="+json.dumps(
            report, sort_keys=True, separators=(",", ":"),
        ))
        return 0
    except (OSError, ValueError, RuntimeError):
        print("ERROR: old Voice rollback evidence unknown; manual review required",
              file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
