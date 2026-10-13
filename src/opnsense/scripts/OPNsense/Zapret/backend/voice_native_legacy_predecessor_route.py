#!/usr/bin/env python3
"""Manual OLD Telegram PoC previous-five backup and reverse plan, one owner.

Not a migration, quiescence/stop, boot recovery, GUI or configd action.
The old process/marker/IPFW remain running unchanged. Write-once previous
and its read-only restoration plan share the original FD9 + Config flock.
Interrupted capture/plan is retained for manual inspection, never retried.
"""
from __future__ import annotations

import fcntl
import os
import re
from pathlib import Path
import sys

from voice_cutover_backup import _private_dir, _sync_dir
from voice_cutover_config_restore import _pinned_regular
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_legacy_previous_seal import (
    NAME, capture_legacy_previous, inspect_legacy_previous,
)
from voice_native_legacy_restore_plan import (
    PLAN_NAME, prepare_legacy_restore_plan, inspect_legacy_restore_plan,
)
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_native_prepare_route import _expected_credentials
from voice_ipfw_adapter import FreeBSDIPFWAdapter
import voice_ipfw_runtime as native


class LegacyPredecessorRouteError(RuntimeError):
    pass


def prepare_old_rollback_predecessor(
    *, root, config_path, config_fd, config_owner, active_runtime,
    legacy_marker, ledger_root, process_probe, kernel_reader, readonly_ipfw,
    security_reader, require_lifecycle_owner,
):
    """Require an empty root; no adoption of existing partial stage."""
    if not callable(require_lifecycle_owner):
        raise LegacyPredecessorRouteError("original lifecycle owner required")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    _pinned_regular(Path(config_path),config_fd,owner=config_owner)
    root=Path(root)
    _private_dir(root)
    if os.listdir(root):
        raise LegacyPredecessorRouteError("existing Voice evidence requires manual review")
    if not isinstance(readonly_ipfw,FreeBSDIPFWAdapter) or readonly_ipfw.allow_mutations:
        raise LegacyPredecessorRouteError("only read-only IPFW adapter allowed")
    previous=capture_legacy_previous(
        root=root,config_path=config_path,active_runtime=active_runtime,
        legacy_marker=legacy_marker,ledger_root=ledger_root,
        probe=process_probe,kernel_reader=kernel_reader,ipfw_adapter=readonly_ipfw,
        security_reader=security_reader,config_fd=config_fd,
        config_owner=config_owner,require_lifecycle_owner=require_lifecycle_owner,
    )
    if (previous["state"]!="legacy-poc-previous-five-domains-sealed-not-owned"
        or previous["safe_to_mutate"] is not False
        or previous["safe_to_enable_voice"] is not False
        or previous["public_voice_apply"] is not False):
        raise LegacyPredecessorRouteError("previous PoC evidence was not sealed")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    if set(os.listdir(root))!={NAME} or inspect_legacy_previous(root)!=previous:
        raise LegacyPredecessorRouteError("previous PoC evidence changed")
    # No IPFW/process/runtime mutation. A partial plan leaves durable evidence
    # under the strict normal lifecycle guard; never auto-clean or retry it.
    plan=prepare_legacy_restore_plan(
        root,config_path=config_path,config_fd=config_fd,
        config_owner=config_owner,require_lifecycle_owner=require_lifecycle_owner,
    )
    if (plan["state"]!="legacy-reverse-actions-sealed-not-authorized"
        or plan["previous_five"]!=previous["previous_five"]
        or plan["safe_to_execute"] is not False
        or plan["safe_to_enable_voice"] is not False
        or plan["public_voice_apply"] is not False):
        raise LegacyPredecessorRouteError("reverse plan did not seal")
    require_lifecycle_owner()
    _locked_config(Path(config_path),config_fd,config_owner)
    if set(os.listdir(root))!={NAME,PLAN_NAME} or (
        inspect_legacy_previous(root)!=previous
        or inspect_legacy_restore_plan(root)!=plan
    ):
        raise LegacyPredecessorRouteError("previous or reverse plan drifted")
    return {
        "state":"legacy-poc-previous-and-reverse-plan-sealed-quiescence-pending",
        "safe_to_mutate":False,"safe_to_execute":False,
        "safe_to_enable_voice":False,"public_voice_apply":False,
        "boot_recovery_validated":False,"media_pass":False,
    }


COMMON_ID = re.compile(r"^[a-f0-9]{32}$")


def _capture_root_for_common_id(identity: str) -> Path:
    """Attach old immutable predecessor evidence to ONE sealed shared candidate.

    No shared journal, IPFW, Config or running-process owner is adopted by
    creating this archive. The prior PoC snapshot/plan remain the SAME
    existing code and schema, simply stored in this candidate's directory.
    """
    if not isinstance(identity, str) or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("invalid shared Apply candidate identity")
    from shared_apply_operation import SharedApplyOperation
    from shared_apply_seal import WORK, verify_seal

    if SharedApplyOperation(owner=0).read() is not None:
        raise LegacyPredecessorRouteError("common Apply owner already present")
    work = WORK / identity
    verify_seal(work, owner=0)
    _private_dir(work)
    return work / "legacy-backup"


def main(argv):
    candidate_id = argv[1] if (
        len(argv) == 2 and argv[0] == "capture-common"
        and COMMON_ID.fullmatch(argv[1])
    ) else None
    if argv != ["capture-plan"] and candidate_id is None:
        print("usage: voice_native_legacy_predecessor_route.py capture-plan|capture-common ID",
              file=sys.stderr)
        return 64
    fd=None
    try:
        native.require_native_lock()
        fd=os.open(native.CONFIG,os.O_RDWR| getattr(os,"O_NOFOLLOW",0))
        _pinned_regular(native.CONFIG,fd,owner=(0,0))
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        root = (_capture_root_for_common_id(candidate_id)
                if candidate_id is not None else native.WHOLE)
        _private_dir(root.parent)
        if not os.path.lexists(root):
            os.mkdir(root,0o700)
            _sync_dir(root.parent)
        _private_dir(root)
        if os.listdir(root):
            raise LegacyPredecessorRouteError("Voice journal already exists")
        probe=FreeBSDVoiceProcessProbe(EXPECTED_SCRIPTS,PIDFILES,root/"previous")
        security=FreeBSDProcessSecurityReader(
            EXPECTED_SCRIPTS,SYSTEM_PATHS,_expected_credentials(),probe,
        )
        result=prepare_old_rollback_predecessor(
            root=root,config_path=native.CONFIG,config_fd=fd,
            config_owner=(0,0),active_runtime=native.ACTIVE_ROOT,
            legacy_marker=native.LEGACY_MARKER,ledger_root=native.LEDGER,
            process_probe=probe,kernel_reader=FreeBSDKernelArgvReader(),
            readonly_ipfw=FreeBSDIPFWAdapter(19000,19010),
            security_reader=security,require_lifecycle_owner=native.require_native_lock,
        )
        if candidate_id is not None:
            # Protect against changes to the candidate after taking the
            # complete old snapshot. Interrupted evidence is never deleted.
            from shared_apply_seal import verify_seal, WORK
            from shared_apply_operation import SharedApplyOperation
            verify_seal(WORK / candidate_id, owner=0)
            if SharedApplyOperation(owner=0).read() is not None:
                raise LegacyPredecessorRouteError("shared owner appeared during capture")
            print("legacy-voice-bound-candidate="+candidate_id)
        print("legacy-voice-predecessor="+result["state"])
        print("native-voice-public-apply=disabled")
        return 0
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):
        print("ERROR: old Telegram PoC predecessor not sealed; manual review required",
              file=sys.stderr)
        return 69
    finally:
        if fd is not None:
            os.close(fd)


if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
