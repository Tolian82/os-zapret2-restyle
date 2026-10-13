#!/usr/bin/env python3
"""Manual, root-only old Telegram PoC five-domain rollback under ORIGINAL locks.

Only `zapret_service.sh native-voice-legacy-rollback-five` owns the existing
FD9. This fixed, parameterless route borrows the one original Config inode
flock for the full six-stage undo. It can WRITE previous IPFW/Config/runtime,
restore the old marker, and restart the old three-role process set ONCE, but
only from the independently sealed previous/restore-plan/clean-boundary WAL.
Unknown evidence remains untouched for operator investigation.

NO configd, GUI, boot hook, daemon, automatic fallback or Voice ON admission.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import sys

from voice_cutover_backup import _private_dir
from voice_cutover_config_restore import _pinned_regular
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_legacy_five_domain_coordinator import (
    FIRST, _prefix, recover_legacy_five_domains,
)
from voice_native_legacy_previous_seal import NAME, inspect_legacy_previous
from voice_native_legacy_restore_plan import inspect_legacy_restore_plan
from voice_native_legacy_reverse_wal import inspect_legacy_reverse_wal
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_freebsd_kernel_argv import FreeBSDKernelArgvReader
from voice_security_policy_evidence import inspect_security_policy
from voice_ipfw_adapter import FreeBSDIPFWAdapter
import voice_ipfw_runtime as native


class OperatorOldRollbackError(RuntimeError):
    pass


def execute_manual_legacy_rollback(
    *, root, config_path, config_fd, config_owner, active_runtime,
    marker_path, ledger_root, process_probe, readonly_ipfw, mutating_ipfw,
    security_reader, argv_reader, require_lifecycle_owner,
    runner=None, actuator=None,
):
    """Require exact durable predecessor before delegating to the REAL engine.

    `runner` and `actuator` are internal test/DI arguments, NEVER CLI
    arguments. Production uses fixed installed process actuator only.
    """
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    _pinned_regular(Path(config_path), config_fd, owner=config_owner)
    root=Path(root)
    _private_dir(root)
    if not FIRST.issubset(set(os.listdir(root))):
        raise OperatorOldRollbackError("complete old WAL predecessor required")
    phase=_prefix(root)  # Foreign/missing/interleaved intent fails before writes.
    old=inspect_legacy_previous(root)
    plan=inspect_legacy_restore_plan(root)
    wal=inspect_legacy_reverse_wal(
        root, allow_ipfw_replay=phase>=1,
        allow_files_stage="legacy-files-ready" if phase>=2 else None,
        allow_runtime_restore=phase>=3, allow_config_restore=phase>=4,
        allow_marker_restore=phase>=5, allow_process_restart=phase>=6,
    )
    if (old["previous_five"]!=plan["previous_five"] or
        wal["previous_five"]!=plan["previous_five"] or
        not old["process_security_sealed"]):
        raise OperatorOldRollbackError("foreign old five-domain predecessor")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    kwargs=dict(
        root=root, config_path=config_path, config_fd=config_fd,
        config_owner=config_owner, active_runtime=active_runtime,
        marker_path=marker_path, ledger_root=ledger_root,
        process_probe=process_probe, readonly_ipfw=readonly_ipfw,
        mutating_ipfw=mutating_ipfw, security_reader=security_reader,
        argv_reader=argv_reader,
        require_lifecycle_owner=require_lifecycle_owner,
    )
    if runner is not None:
        kwargs["runner"]=runner
    if actuator is not None:
        kwargs["actuator"]=actuator
    result=recover_legacy_five_domains(**kwargs)
    if (result["state"]!="legacy-five-domains-whole-receipt-sealed-boot-pending"
        or result["whole_rollback_complete"] is not True or
        result["safe_to_enable_voice"] is not False or
        result["safe_to_close_intent"] is not False or
        result["boot_recovery_validated"] is not False or
        result["public_voice_apply"] is not False or
        result["media_pass"] is not False):
        raise OperatorOldRollbackError("rollback did not seal its bounded receipt")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    return {
        "state":"legacy-five-domains-whole-receipt-sealed-boot-pending",
        "safe_to_enable_voice":False,"safe_to_close_intent":False,
        "boot_recovery_validated":False,"public_voice_apply":False,
        "media_pass":False,
    }


def main(argv):
    if argv!=["rollback"]:
        print("usage: voice_native_legacy_rollback_route.py rollback",file=sys.stderr)
        return 64
    fd=None
    try:
        native.require_native_lock()
        fd=os.open(native.CONFIG,os.O_RDWR | getattr(os,"O_NOFOLLOW",0))
        _pinned_regular(native.CONFIG,fd,owner=(0,0))
        fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
        root=native.WHOLE
        _private_dir(root)
        _prefix(root)
        old=root/NAME/"previous"
        probe=FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS,PIDFILES,old)
        policy=inspect_security_policy(
            root/NAME/"process-security-policy",old,
            root/NAME/"process-evidence",expected_scripts=EXPECTED_SCRIPTS,
        )
        security=FreeBSDProcessSecurityReader(
            EXPECTED_SCRIPTS,policy["policy"]["images"],
            policy["policy"]["credentials"],probe,
        )
        argv_reader=FreeBSDKernelArgvReader(EXPECTED_SCRIPTS,probe)
        report=execute_manual_legacy_rollback(
            root=root,config_path=native.CONFIG,config_fd=fd,
            config_owner=(0,0),active_runtime=native.ACTIVE_ROOT,
            marker_path=native.LEGACY_MARKER,ledger_root=native.LEDGER,
            process_probe=probe,readonly_ipfw=FreeBSDIPFWAdapter(19000,19010),
            mutating_ipfw=FreeBSDIPFWAdapter(19000,19010,allow_mutations=True),
            security_reader=security,argv_reader=argv_reader,
            require_lifecycle_owner=native.require_native_lock,
        )
        print("legacy-voice-rollback="+report["state"])
        print("native-voice-public-apply=disabled")
        print("native-voice-boot-acceptance=pending")
        return 0
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):
        print("ERROR: old Telegram rollback refused; inspect retained WAL and IPFW",
              file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
