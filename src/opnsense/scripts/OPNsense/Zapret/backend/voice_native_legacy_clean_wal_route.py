#!/usr/bin/env python3
"""Operator-only old Telegram PoC clean-boundary reverse WAL seal.

Use the ORIGINAL Zapret FD9 lock and ORIGINAL Config inode flock for one
strictly read-only quiescence observation followed by the existing write-once,
fsynced legacy reverse WAL publication. Old process stopping, IPFW deletion,
marker removal, active Config/runtime changes, restart, native Voice Apply and
automatic boot recovery are OUTSIDE this command.

A separate operator must already have brought the previous PoC to the
clean, stopped state. Partial/foreign journals remain fail-closed; this route
does not adopt an unsafe or already-present WAL. No configd or GUI binding.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import sys

from voice_cutover_backup import _private_dir
from voice_cutover_config_restore import _pinned_regular
from voice_native_recovery_quiescence import (
    EXPECTED_SCRIPTS, PIDFILES, _locked_config,
)
from voice_native_legacy_previous_seal import NAME, inspect_legacy_previous
from voice_native_legacy_restore_plan import PLAN_NAME, inspect_legacy_restore_plan
from voice_native_legacy_reverse_wal import (
    WAL_NAME, prepare_legacy_reverse_wal, inspect_legacy_reverse_wal,
)
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_ipfw_adapter import FreeBSDIPFWAdapter
import voice_ipfw_runtime as native


class LegacyCleanWALRouteError(RuntimeError):
    pass


def seal_old_clean_boundary(
    *, root, config_path, config_fd, config_owner, ledger_root,
    marker_path, active_runtime, process_probe, readonly_ipfw,
    require_lifecycle_owner,
):
    """Connect the existing two sealed predecessors to one clean-boundary WAL.

    The real WAL writer performs the authoritative two-pass quiescence,
    exact IPFW/ledger/marker checks, old-plan checksum verification and
    final source reattestation before the atomic rename. This wrapper does
    not confer execution or Voice ON authority.
    """
    if not callable(require_lifecycle_owner):
        raise LegacyCleanWALRouteError("original lifecycle owner required")
    root, config_path = Path(root), Path(config_path)
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    _pinned_regular(config_path, config_fd, owner=config_owner)
    _private_dir(root)
    if set(os.listdir(root)) != {NAME, PLAN_NAME}:
        raise LegacyCleanWALRouteError("only fully sealed old predecessor/plan admitted")
    if not isinstance(readonly_ipfw, FreeBSDIPFWAdapter) or readonly_ipfw.allow_mutations:
        raise LegacyCleanWALRouteError("mutating or non-native IPFW adapter refused")
    previous = inspect_legacy_previous(root)
    plan = inspect_legacy_restore_plan(root)
    if (previous["previous_five"] != plan["previous_five"]
        or previous["process_security_policy_sha256"] !=
           plan["process_security_policy_sha256"]):
        raise LegacyCleanWALRouteError("old predecessor and reverse plan unbound")
    wal = prepare_legacy_reverse_wal(
        root, config_path=config_path, config_fd=config_fd,
        config_owner=config_owner, ledger_root=ledger_root,
        legacy_marker=marker_path, active_runtime=active_runtime,
        process_probe=process_probe, readonly_ipfw=readonly_ipfw,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if (wal["state"] != "reverse-wal-sealed-not-executable"
        or wal["phase"] != "prepared-clean-kernel-not-executable"
        or wal["previous_five"] != previous["previous_five"]
        or wal["safe_to_execute"] is not False
        or wal["safe_to_mutate"] is not False
        or wal["safe_to_enable_voice"] is not False
        or wal["public_voice_apply"] is not False):
        raise LegacyCleanWALRouteError("clean predecessor WAL not sealed")
    require_lifecycle_owner()
    _locked_config(config_path, config_fd, config_owner)
    if (set(os.listdir(root)) != {NAME, PLAN_NAME, WAL_NAME}
        or inspect_legacy_previous(root) != previous
        or inspect_legacy_restore_plan(root) != plan
        or inspect_legacy_reverse_wal(root) != wal):
        raise LegacyCleanWALRouteError("old quiescent WAL changed after publication")
    return {
        "state": "legacy-clean-boundary-wal-sealed-reverse-owner-pending",
        "safe_to_execute": False, "safe_to_mutate": False,
        "safe_to_enable_voice": False, "public_voice_apply": False,
        "boot_recovery_validated": False, "media_pass": False,
    }


def main(argv):
    if argv != ["seal-clean-wal"]:
        print("usage: voice_native_legacy_clean_wal_route.py seal-clean-wal",
              file=sys.stderr)
        return 64
    fd = None
    try:
        native.require_native_lock()
        fd = os.open(native.CONFIG, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        _pinned_regular(native.CONFIG, fd, owner=(0, 0))
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        root = native.WHOLE
        _private_dir(root)
        if set(os.listdir(root)) != {NAME, PLAN_NAME}:
            raise LegacyCleanWALRouteError("old previous/plan not safely sealed")
        report = seal_old_clean_boundary(
            root=root, config_path=native.CONFIG, config_fd=fd,
            config_owner=(0, 0), ledger_root=native.LEDGER,
            marker_path=native.LEGACY_MARKER, active_runtime=native.ACTIVE_ROOT,
            process_probe=FreeBSDVoiceProcessProbe(
                EXPECTED_SCRIPTS, PIDFILES, root / NAME / "previous",
            ),
            readonly_ipfw=FreeBSDIPFWAdapter(19000, 19010),
            require_lifecycle_owner=native.require_native_lock,
        )
        print("legacy-voice-clean-boundary=" + report["state"])
        print("native-voice-public-apply=disabled")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        print("ERROR: old PoC not proven clean; retain journal for manual review",
              file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
