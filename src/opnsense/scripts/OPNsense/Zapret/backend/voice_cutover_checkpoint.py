#!/usr/bin/env python3
"""Capture the REAL previous OPNsense Config and Zapret2 runtime before Voice ON.

Production service-only entrypoint; invoked exclusively under the shared
zapret_service.sh FD9 lock. Checks the installed, running, all-OFF engine,
legacy PoC absence and actual kernel IPFW ownership before durable backup.

This does not start a Voice cutover, change kernel rules or grant ON Apply.
The whole Config/dvtws2/supervisor/rollback transaction remains required.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys

from voice_cutover_backup import (
    VoiceBackupError, capture_previous, inspect_previous,
    bound_resource_fingerprints, _verify_sources,
)
from voice_cutover_journal import VoiceCutoverJournal
from voice_firewall_ledger import VoiceOwnershipStore
from voice_firewall_transaction import verify_prior_state
from voice_ipfw_adapter import FreeBSDIPFWAdapter
import voice_ipfw_runtime as native


BACKUP_DIR = native.WHOLE / "previous"


class VoiceCheckpointError(RuntimeError):
    pass


def _private_dir(path: Path) -> None:
    if path.is_symlink():
        raise VoiceCheckpointError("unsafe Voice checkpoint directory")
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or \
       info.st_mode & 0o077:
        raise VoiceCheckpointError("Voice checkpoint directory is not root-private")


def checkpoint(config: Path, runtime: Path, backup_root: Path, ledger_root: Path,
               adapter, desired: dict, verify_engine, verify_sources) -> dict:
    """Save a durable pre-mutation snapshot after verifying actual runtime.

    This is the same production implementation when the CLI passes the fixed
    OPNsense directories and real FreeBSD adapter. Tests inject private dirs
    and FakeIPFW, never contacting the appliance.
    """
    if desired["tables"] or len(desired["rules"]) > 2:
        raise VoiceCheckpointError("native Voice checkpoint requires all services OFF")
    if backup_root.is_symlink() or ledger_root.is_symlink():
        raise VoiceCheckpointError("untrusted Voice checkpoint or ledger root")
    # A completed old checkpoint must never be overwritten or replaced with
    # bytes from a different concurrent Config generation.
    if backup_root.exists():
        _private_dir(backup_root)
        if VoiceCutoverJournal(backup_root).read() is not None:
            raise VoiceCheckpointError("unfinished Voice whole-system transaction")
        if (backup_root / "previous").exists() or \
           (backup_root / "previous").is_symlink():
            raise VoiceCheckpointError("existing Voice previous-state checkpoint")
    if ledger_root.exists():
        store = VoiceOwnershipStore(ledger_root)
        if store.pending() is not None or store.owned() is not None:
            raise VoiceCheckpointError("native IPFW already owns rules or has pending intent")
    verify_prior_state(adapter, desired, desired)
    verify_engine()
    verify_sources()
    # Creating only a private backup directory does NOT take ownership of
    # IPFW or create a cutover intent. The normal OFF lifecycle stays usable.
    _private_dir(backup_root.parent)
    _private_dir(backup_root)
    snapshot = capture_previous(config, runtime, backup_root / "previous")
    inspect_previous(backup_root / "previous")
    evidence = bound_resource_fingerprints(backup_root / "previous")
    if evidence["config"] != snapshot["config"]["sha256"]:
        raise VoiceCheckpointError("previous Config fingerprint mismatch")
    # Verify process, Config generation and IPFW a second time after the
    # fsync/rename of both sealed backup resources.
    verify_sources()
    verify_engine()
    _verify_sources(config, runtime, snapshot)
    verify_prior_state(adapter, desired, desired)
    return evidence


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "prepare":
        print("usage: voice_cutover_checkpoint.py prepare", file=sys.stderr)
        return 64
    try:
        native.require_native_lock()
        desired, proof = native.load_candidate()
        if proof.get("enabled_services"):
            raise VoiceCheckpointError("only a running all-OFF release may be captured")
        adapter = FreeBSDIPFWAdapter(19000, 19010, allow_mutations=False)
        native.require_no_legacy(adapter)
        evidence = checkpoint(
            native.CONFIG, native.ACTIVE_ROOT, native.WHOLE, native.LEDGER,
            adapter, desired,
            lambda: native.require_engine_process(proof),
            lambda: native.load_candidate(),
        )
        print("native-voice-checkpoint=sealed")
        print("previous-config-sha256=" + evidence["config"])
        print("previous-runtime-sha256=" + evidence["runtime"])
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print("ERROR: native Voice checkpoint refused: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
