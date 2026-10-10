#!/usr/bin/env python3
"""Production-only staging of the sealed *previous* Voice runtime recovery.

Requires the existing Zapret FD9 lifecycle lock and the durable schema-2+
whole-cutover journal in MUTATING phase. Restorable Config and runtime are
materialized into a new, root-private directory. Nothing is installed: this
action never changes /conf/config.xml, the active tree, IPFW or dvtws2.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_journal import VoiceCutoverJournal
from voice_cutover_restore_stage import prepare_restore_stage
from voice_firewall_ledger import VoiceOwnershipStore
import voice_ipfw_runtime as native


class NativeRestorePreparationError(RuntimeError):
    pass


def prepare_recovery(previous_dir: Path, destination: Path,
                     whole: VoiceCutoverJournal, firewall: VoiceOwnershipStore,
                     *, verify_live=None) -> dict:
    """Bind staged restore bytes to a pending whole-system cutover.

    A previously committed cutover cannot be rolled back. Keep the durable
    original snapshot and journal intact even when staging fails.
    """
    record = whole.read()
    if not isinstance(record, dict) or record.get("schema", 0) < 2 or \
       record.get("phase") != "mutating":
        raise NativeRestorePreparationError(
            "no unfinished mutating whole-system Voice cutover to restore"
        )
    expected = record["previous"]
    if firewall.owned() is None:
        raise NativeRestorePreparationError(
            "native IPFW previous ownership is not recorded"
        )
    pending = firewall.pending()
    if pending is not None:
        from voice_firewall_ledger import decode_manifest
        previous = decode_manifest(pending["previous"])
        if firewall.owned() != previous or pending["phase"] != "mutating":
            raise NativeRestorePreparationError(
                "IPFW intent is not the same uncommitted previous owner"
            )
    if verify_live is not None:
        # Production does not mutate based on an injected provider. The
        # injected callback is used only in isolated regression fixtures.
        verify_live()
    old = bound_resource_fingerprints(previous_dir, expected)
    if old["config"] != expected["config"] or old["runtime"] != expected["runtime"]:
        raise NativeRestorePreparationError("sealed Config/runtime hashes changed")
    result = prepare_restore_stage(previous_dir, destination, expected)
    if result.get("activation_authorized") is not False or \
       result.get("previous") != old:
        raise NativeRestorePreparationError("recovery files were not sealed")
    # The cross-system intent remains in MUTATING: this step alone can
    # never bless kernel, process, supervisor or Config restoration.
    if whole.read() != record:
        raise NativeRestorePreparationError(
            "whole-system Voice journal changed while staging previous files"
        )
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "prepare":
        print("usage: voice_cutover_restore_prepare.py prepare", file=sys.stderr)
        return 64
    try:
        native.require_native_lock()
        whole = VoiceCutoverJournal(native.WHOLE)
        ledger = VoiceOwnershipStore(native.LEDGER)
        result = prepare_recovery(
            native.WHOLE / "previous",
            native.WHOLE / "restore-staged",
            whole, ledger,
        )
        print("native-voice-restore=staged-only")
        print("previous-config-sha256=" + result["previous"]["config"])
        print("previous-runtime-sha256=" + result["previous"]["runtime"])
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print("ERROR: native Voice restore-stage refused: " + str(error),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
