#!/usr/bin/env python3
"""Single-original-FD9-and-Config-flock legacy five-domain rollback coordinator.

IMPORT ONLY. No CLI, configd, GUI, boot hook, daemon, service registration,
voice-on permission, or MEDIA_PASS.

A caller who already holds the ORIGINAL Zapret lifecycle FD9 and the SAME
exclusive OPNsense Config inode flock invokes this once. The coordinator
drives the six existing, independently crash-safe actions in order:
IPFW, previous-files stage, runtime, Config, transient marker, three-role
process restart. All actions use that same borrowed locked Config descriptor.

Root admission is an exact monotonic prefix: no missing or foreign evidence,
no implicit journal repairs, no recreation of interrupted partial stages.
Only the CURRENT stage is resumed. A process-start attempt recorded before
a power cut is never reissued: the process module only reattests all three
roles or fails closed for manual review.

A successful return seals an immutable whole five-domain receipt. It is
NEVER boot acceptance or authority to enable Voice.
"""
from __future__ import annotations

import os
from pathlib import Path

from voice_cutover_backup import _private_dir
from voice_native_recovery_quiescence import _locked_config
from voice_native_legacy_previous_seal import NAME, inspect_legacy_previous
from voice_native_legacy_restore_plan import PLAN_NAME, inspect_legacy_restore_plan
from voice_native_legacy_reverse_wal import WAL_NAME, inspect_legacy_reverse_wal
from voice_native_legacy_ipfw_replay import (
    REPLAY_NAME, replay_legacy_ipfw, _steps, _strict_snapshot,
    _expected_after,
)
from voice_native_legacy_files_ready import (
    FILES_NAME, stage_legacy_previous_files, inspect_legacy_files_ready,
)
from voice_native_legacy_runtime_restore import (
    NAME_RESTORE, restore_legacy_runtime,
)
from voice_native_legacy_config_restore import (
    CONFIG_NAME, restore_legacy_config,
)
from voice_native_legacy_marker_restore import (
    MARKER_NAME, restore_legacy_marker,
)
from voice_native_legacy_process_restart import (
    PROCESS_NAME, restart_legacy_processes,
)
from voice_native_process_actions import SCRIPT
from voice_native_legacy_whole_receipt import seal_legacy_whole_receipt

FIRST = frozenset((NAME, PLAN_NAME, WAL_NAME))
STAGES = (
    REPLAY_NAME, FILES_NAME, NAME_RESTORE,
    CONFIG_NAME, MARKER_NAME, PROCESS_NAME,
)
STATES = (
    "legacy-ipfw-replayed-other-four-domains-not-restored",
    "legacy-previous-files-staged-not-installed",
    "legacy-runtime-restored-config-marker-and-processes-pending",
    "legacy-config-restored-marker-and-processes-pending",
    "legacy-marker-restored-old-processes-not-restarted",
    "legacy-three-roles-restarted-needs-whole-owner-acceptance",
)


class LegacyFiveDomainCoordinatorError(RuntimeError):
    pass


def _prefix(root):
    """Exact directory allowlist with no interleaved, orphan, or foreign stage."""
    _private_dir(root)
    actual=set(os.listdir(root))
    for n in range(len(STAGES)+1):
        expected=set(FIRST)|set(STAGES[:n])
        if actual==expected:
            return n
    raise LegacyFiveDomainCoordinatorError(
        "non-monotonic or foreign five-domain rollback journal; manual review"
    )


def recover_legacy_five_domains(
    *, root, config_path, config_fd, config_owner,
    active_runtime, marker_path, ledger_root, process_probe,
    readonly_ipfw, mutating_ipfw, security_reader, argv_reader,
    require_lifecycle_owner, runner=None, actuator=SCRIPT,
):
    """Run each required restoration ONCE within the caller's SAME FD9+flock.

    Keep all journals and boot gates pending after a sealed whole receipt.
    Owner-live reboot/Telegram media acceptance is still required.
    """
    if (not callable(require_lifecycle_owner)
        or type(config_fd) is not int or config_fd<0
        or not isinstance(config_owner,tuple) or len(config_owner)!=2
        or any(type(x) is not int or x<0 for x in config_owner)):
        raise LegacyFiveDomainCoordinatorError(
            "original lifecycle owner and Config descriptor required"
        )
    root=Path(root)
    config_path=Path(config_path)
    active_runtime=Path(active_runtime)
    marker_path=Path(marker_path)

    def held():
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)

    held()
    n=_prefix(root)
    # No trust derived from a folder's name: all previous evidence must
    # still match the full original five-resource manifest.
    previous=inspect_legacy_previous(root)
    plan=inspect_legacy_restore_plan(root)
    if (previous["previous_five"]!=plan["previous_five"]
        or not previous["process_security_sealed"]):
        raise LegacyFiveDomainCoordinatorError("old PoC previous-five unbound")
    wal=inspect_legacy_reverse_wal(
        root,allow_ipfw_replay=n>=1,
        allow_files_stage=FILES_NAME if n>=2 else None,
        allow_runtime_restore=n>=3,
        allow_config_restore=n>=4,
        allow_marker_restore=n>=5,
        allow_process_restart=n>=6,
    )
    if (wal["previous_five"]!=plan["previous_five"]
        or wal["process_security_policy_sha256"]!=
           previous["process_security_policy_sha256"]):
        raise LegacyFiveDomainCoordinatorError("old whole rollback WAL drift")
    if n>=2 and inspect_legacy_files_ready(
        root,allow_runtime_restore=n>=3,allow_config_restore=n>=4,
        allow_marker_restore=n>=5,allow_process_restart=n>=6,
    )["previous_five"]!=plan["previous_five"]:
        raise LegacyFiveDomainCoordinatorError("old files-ready manifest drift")

    common={
        "root":root,"config_path":config_path,"config_fd":config_fd,
        "config_owner":config_owner,"ledger_root":ledger_root,
        "active_runtime":active_runtime,"process_probe":process_probe,
        "readonly_ipfw":readonly_ipfw,
        "require_lifecycle_owner":require_lifecycle_owner,
    }
    actions=(
        lambda: replay_legacy_ipfw(
            **common,legacy_marker=marker_path,mutating_ipfw=mutating_ipfw,
        ),
        lambda: stage_legacy_previous_files(
            **common,legacy_marker=marker_path,
        ),
        lambda: restore_legacy_runtime(
            **common,legacy_marker=marker_path,
        ),
        lambda: restore_legacy_config(
            **common,legacy_marker=marker_path,
        ),
        lambda: restore_legacy_marker(
            **common,marker_path=marker_path,
        ),
        lambda: restart_legacy_processes(
            **common,marker_path=marker_path,security_reader=security_reader,
            argv_reader=argv_reader,runner=runner,actuator=actuator,
        ),
    )

    # A stage directory is a durable INTENT, not proof of completion.
    # IPFW, runtime, Config, marker and process stages are reentrant and
    # must reattest their own exact per-stage redo (or finish an interrupted
    # write) before any newer stage may run. The files-ready image alone is
    # published atomically and explicitly refuses a duplicate staging call.
    # Never rewind past the current journal-owned stage.
    start=(n-1 if n in (1,3,4,5,6) else n)
    process_report=None
    for i in range(start,len(STAGES)):
        held()
        found=_prefix(root)
        if found not in (i,i+1):
            raise LegacyFiveDomainCoordinatorError(
                "concurrent/foreign legacy rollback phase transition"
            )
        if found!=i and i!=start:
            raise LegacyFiveDomainCoordinatorError(
                "unexpected completed future rollback phase"
            )
        evidence=actions[i]()
        held()
        if _prefix(root)!=i+1 or (
            not isinstance(evidence,dict)
            or evidence.get("state")!=STATES[i]
            or evidence.get("safe_to_enable_voice") is not False
        ) or evidence.get("whole_rollback_complete") is not False:
            raise LegacyFiveDomainCoordinatorError(
                "restoration did not publish its exact restricted phase"
            )
        if i==len(STAGES)-1:
            process_report=evidence
    if process_report is None:
        raise LegacyFiveDomainCoordinatorError("old process state was not attested")

    # Independent last-boundary check BEFORE returning the five-domain
    # observation. This is still not a terminal receipt, process-readiness
    # grant, or authority for boot/GUI/live Telegram voice.
    held()
    if _prefix(root)!=len(STAGES):
        raise LegacyFiveDomainCoordinatorError("five-domain journal drift")
    if (inspect_legacy_previous(root)["previous_five"]!=plan["previous_five"]
        or inspect_legacy_restore_plan(root)!=plan):
        raise LegacyFiveDomainCoordinatorError("previous PoC manifest changed")
    final_wal=inspect_legacy_reverse_wal(
        root,allow_ipfw_replay=True,allow_files_stage=FILES_NAME,
        allow_runtime_restore=True,allow_config_restore=True,
        allow_marker_restore=True,allow_process_restart=True,
    )
    if final_wal!=wal:
        raise LegacyFiveDomainCoordinatorError("five-domain WAL changed")
    if (inspect_legacy_files_ready(
        root,allow_runtime_restore=True,allow_config_restore=True,
        allow_marker_restore=True,allow_process_restart=True,
    )["previous_five"]!=plan["previous_five"]):
        raise LegacyFiveDomainCoordinatorError("final previous files image changed")
    completed,partial=_steps(root/REPLAY_NAME,plan)
    if (partial or completed!=len(plan["legacy_ipfw_commands"])
        or _strict_snapshot(readonly_ipfw)!=_expected_after(plan,completed)):
        raise LegacyFiveDomainCoordinatorError("final legacy IPFW drift")
    held()
    receipt=seal_legacy_whole_receipt(
        root=root,config_path=config_path,config_fd=config_fd,
        config_owner=config_owner,require_lifecycle_owner=require_lifecycle_owner,
        process_report=process_report,
    )
    held()
    return {
        "state":"legacy-five-domains-whole-receipt-sealed-boot-pending",
        "whole_receipt_state":receipt["state"],
        "journal_tree_sha256":receipt["journal_tree_sha256"],
        "previous_five":plan["previous_five"],
        "process_instances":process_report["instances"],
        "process_security_policy_sha256":
            process_report["process_security_policy_sha256"],
        "phases_completed":list(STAGES),
        "same_original_config_fd":True,
        "safe_to_enable_voice":False,
        "whole_rollback_complete":True,
        "safe_to_close_intent":False,
        "boot_recovery_validated":False,
        "public_voice_apply":False,
        "media_pass":False,
    }
