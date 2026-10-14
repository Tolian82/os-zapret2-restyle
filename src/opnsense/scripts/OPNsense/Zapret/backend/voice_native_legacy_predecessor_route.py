#!/usr/bin/env python3
"""Manual OLD Telegram PoC previous-five backup and reverse plan, one owner.

Not a migration, quiescence/stop, boot recovery, GUI or configd action.
The old process/marker/IPFW remain running unchanged. Write-once previous
and its read-only restoration plan share the original FD9 + Config flock.
Interrupted capture/plan is retained for manual inspection, never retried.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
import re
import stat
import subprocess
from pathlib import Path
import sys

from voice_cutover_backup import _private_dir, _sync_dir, inspect_previous, _verify_sources, _read_private_file
from voice_cutover_config_restore import _pinned_regular
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config
from voice_native_legacy_previous_seal import (
    NAME, capture_legacy_previous, inspect_legacy_previous,
    inspect_legacy_previous_live_identity,
)
from voice_native_legacy_restore_plan import (
    PLAN_NAME, prepare_legacy_restore_plan, inspect_legacy_restore_plan,
)
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_legacy_live_preflight import inspect_running_legacy_poc
from voice_native_legacy_poc_guard import _legacy_read
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


def cancel_unchanged_common_predecessor(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, ledger_root, process_probe, kernel_reader,
    readonly_ipfw, require_lifecycle_owner, begin=False, inspect_only=False,
):
    """Prove exact old live ownership before a boundary or cancellation.

    Recovery here is a journal-only change, never an actuator. Re-read the
    immutable old snapshot and all live sources while holding original locks.
    """
    from shared_apply_operation import fingerprint_legacy_predecessor
    work = Path(work)
    root = work / "legacy-backup"
    saved = inspect_legacy_previous_live_identity(root)
    def attest():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        digest = fingerprint_legacy_predecessor(work, owner=config_owner[0])
        manifest = inspect_previous(root / NAME / "previous")
        _verify_sources(Path(config_path), Path(active_runtime), manifest)
        current_marker = _legacy_read(Path(marker_path))
        previous_marker = _read_private_file(root / NAME / "marker.bin", 64)
        marker_mode = stat.S_IMODE(os.lstat(marker_path).st_mode)
        if current_marker != previous_marker or (
            marker_mode != saved["marker"]["mode"]
        ):
            raise LegacyPredecessorRouteError("old Telegram marker not pristine")
        current = inspect_running_legacy_poc(
            config_path=config_path, active_runtime=active_runtime,
            legacy_marker=marker_path, whole_root=native.WHOLE,
            ledger_root=ledger_root, probe=process_probe,
            kernel_reader=kernel_reader, ipfw_adapter=readonly_ipfw,
            config_fd=config_fd, config_owner=config_owner,
            require_lifecycle_owner=require_lifecycle_owner,
        )
        for name, expected in (
            ("legacy_ipfw_structure_sha256", saved["legacy_ipfw_structure_sha256"]),
            ("managed_ipv4_sha256", saved["managed_ipv4_sha256"]),
            ("active_argument_sha256", saved["active_argument_sha256"]),
            ("instances", saved["process_instances"]),
            ("legacy_ipfw_previous", saved["legacy_ipfw_previous"]),
        ):
            if current[name] != expected:
                raise LegacyPredecessorRouteError("old PoC live owner changed: " + name)
        _verify_sources(Path(config_path), Path(active_runtime), manifest)
        if _legacy_read(Path(marker_path)) != previous_marker:
            raise LegacyPredecessorRouteError("old Telegram marker changed")
        if fingerprint_legacy_predecessor(work, owner=config_owner[0]) != digest:
            raise LegacyPredecessorRouteError("legacy backup changed during cancellation")
        return digest

    if inspect_only:
        # An already armed STOP intent may reattest the same live old owner
        # without rewriting or cancelling any durable state.
        return attest()
    return (store.begin_legacy_quiesce(identity, attest) if begin
            else store.cancel_pristine_legacy(identity, attest))



def stop_armed_common_predecessor(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, ledger_root, process_probe, kernel_reader,
    readonly_ipfw, require_lifecycle_owner, runner=None,
):
    """PRIVATE first real mutation: stop old three processes under common FD9.

    No CLI, configd or GUI route until exact old-IPFW/marker retirement,
    common-engine activation and verified rollback are also implemented.
    An interruption leaves the SINGLE journal blocked in legacy-quiescing.
    The fixed existing process actuator takes no user PID or shell argument.
    """
    from shared_apply_operation import (
        SharedApplyOperation, fingerprint_legacy_predecessor,
    )
    from voice_native_live_preflight import _current_engine_args
    from voice_native_live_ipfw import observe_legacy_poc_ipfw
    from voice_native_process_actions import SCRIPT, _secure_script
    from voice_native_live_preflight import _instances
    if not isinstance(store, SharedApplyOperation) or (
        not isinstance(process_probe, FreeBSDVoiceProcessProbe)
        or not isinstance(kernel_reader, FreeBSDKernelArgvReader)
        or not isinstance(readonly_ipfw, FreeBSDIPFWAdapter)
        or readonly_ipfw.allow_mutations
        or (readonly_ipfw.rule_base, readonly_ipfw.rule_max) != (19000, 19010)
        or not callable(require_lifecycle_owner)
    ):
        raise LegacyPredecessorRouteError("old live owner stop lacks trusted probes")
    work = Path(work)
    root = work / "legacy-backup"
    if work.name != identity or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("old stop is not bound to sealed candidate")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    record = store.read()
    if record is None or record["phase"] != "legacy-quiescing" or (
        record["detail"]["id"] != identity or "previous" in record
        or "legacy_predecessor" not in record
    ):
        raise LegacyPredecessorRouteError("durable legacy-quiescing phase required")
    expected = cancel_unchanged_common_predecessor(
        identity=identity, store=store, work=work, config_path=config_path,
        config_fd=config_fd, config_owner=config_owner,
        active_runtime=active_runtime, marker_path=marker_path,
        ledger_root=ledger_root, process_probe=process_probe,
        kernel_reader=kernel_reader, readonly_ipfw=readonly_ipfw,
        require_lifecycle_owner=require_lifecycle_owner, inspect_only=True,
    )
    if expected != record["legacy_predecessor"] or store.read() != record:
        raise LegacyPredecessorRouteError("old live source changed before stop")
    # Verify the installed, fixed, root-owned actuator that reuses the one
    # launcher/supervisor. Never hand it arbitrary paths or PID arguments.
    _secure_script(SCRIPT)
    active_runner = subprocess.run if runner is None else runner
    if not callable(active_runner):
        raise LegacyPredecessorRouteError("invalid bounded stop runner")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    if store.read() != record:
        raise LegacyPredecessorRouteError("journal changed before stopping engine")
    result = active_runner(
        ["/bin/sh", str(SCRIPT), "stop"],
        check=False, capture_output=True, text=True, timeout=20,
        pass_fds=(9,), env={"LC_ALL": "C",
                            "PATH": "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin"},
    )
    if result.returncode != 0 or (
        len(result.stdout.encode("utf-8")) > 8192 or
        len(result.stderr.encode("utf-8")) > 8192
    ):
        raise LegacyPredecessorRouteError("old engine actuator did not finish safely")

    def stopped():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        previous = inspect_legacy_previous_live_identity(root)
        if fingerprint_legacy_predecessor(work, owner=config_owner[0]) != expected:
            raise LegacyPredecessorRouteError("old sealed predecessor drifted after stop")
        old = inspect_previous(root / NAME / "previous")
        _verify_sources(Path(config_path), Path(active_runtime), old)
        marker = _read_private_file(root / NAME / "marker.bin", 64)
        if _legacy_read(Path(marker_path)) != marker or (
            stat.S_IMODE(os.lstat(marker_path).st_mode) != previous["marker"]["mode"]
        ):
            raise LegacyPredecessorRouteError("old marker changed while stopping")
        a = process_probe.observe_processes()
        b = process_probe.observe_processes()
        if a != b or a["engine"]["state"] != "stopped" or (
            a["supervisor"]["state"] != "stopped"
        ):
            raise LegacyPredecessorRouteError("old engine/supervisor not wholly stopped")
        # The original legacy table/rules are NOT retired at this stage;
        # they must be exactly unchanged until the next durable action.
        current = observe_legacy_poc_ipfw(
            readonly_ipfw, _current_engine_args(active_runtime)[0],
            sorted(previous["legacy_ipfw_previous"]["targets"]),
        )
        if current["structure_sha256"] != previous["legacy_ipfw_structure_sha256"] or (
            current["previous_ipfw"] != previous["legacy_ipfw_previous"]
        ):
            raise LegacyPredecessorRouteError("old IPFW mutated during engine stop")
        return expected

    result = store.mark_legacy_processes_stopped(identity, stopped)
    if result["phase"] != "legacy-processes-stopped":
        raise LegacyPredecessorRouteError("old process stop journal incomplete")
    return result



def retire_stopped_common_legacy_ipfw(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, process_probe, readonly_ipfw,
    mutating_ipfw, require_lifecycle_owner,
):
    """PRIVATE: retire only sealed old Telegram IPFW under ONE common journal.

    The old engine is already stopped (phase legacy-processes-stopped).
    This stage does not change Config, runtime, legacy marker or start native
    engine. It cannot be resumed automatically after interrupted deletion:
    legacy-ipfw-retiring stays pending for an explicit verified reverse path.
    """
    from shared_apply_operation import (
        SharedApplyOperation, fingerprint_legacy_predecessor,
    )
    from voice_native_legacy_ipfw_replay import _strict_snapshot
    from voice_native_legacy_reverse_wal import _stopped
    from voice_native_live_ipfw import OLD_TABLE
    if not isinstance(store, SharedApplyOperation) or (
        not isinstance(process_probe, FreeBSDVoiceProcessProbe)
        or not isinstance(readonly_ipfw, FreeBSDIPFWAdapter)
        or readonly_ipfw.allow_mutations
        or not isinstance(mutating_ipfw, FreeBSDIPFWAdapter)
        or not mutating_ipfw.allow_mutations
        or (readonly_ipfw.rule_base, readonly_ipfw.rule_max) != (19000, 19010)
        or (mutating_ipfw.rule_base, mutating_ipfw.rule_max) != (19000, 19010)
        or type(config_fd) is not int or config_fd < 0
        or not callable(require_lifecycle_owner)
    ):
        raise LegacyPredecessorRouteError("old IPFW retirement lacks the one original owner")
    work = Path(work)
    root = work / "legacy-backup"
    if work.name != identity or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("old IPFW retirement candidate ID changed")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    record = store.read()
    if record is None or record["phase"] != "legacy-processes-stopped" or (
        record["detail"]["id"] != identity or "previous" in record
        or "legacy_predecessor" not in record
    ):
        raise LegacyPredecessorRouteError("sealed stopped legacy journal required")
    saved = inspect_legacy_previous_live_identity(root)
    plan = inspect_legacy_restore_plan(root)
    summary = inspect_legacy_previous(root)
    if plan["previous_five"] != summary["previous_five"]:
        raise LegacyPredecessorRouteError("old IPFW reverse plan seal changed")
    old = saved["legacy_ipfw_previous"]
    initial = {"rules": dict(old["rules"]), "targets": sorted(old["targets"])}
    if len(initial["rules"]) not in (2, 3) or not initial["targets"]:
        raise LegacyPredecessorRouteError("old Telegram IPFW is not a complete owner")

    def witness(needed):
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        if fingerprint_legacy_predecessor(work, owner=config_owner[0]) != (
            record["legacy_predecessor"]
        ):
            raise LegacyPredecessorRouteError("old predecessor seal changed during IPFW")
        if inspect_legacy_previous(root) != summary or (
            inspect_legacy_restore_plan(root) != plan
        ):
            raise LegacyPredecessorRouteError("old predecessor reverse plan changed")
        _verify_sources(
            Path(config_path), Path(active_runtime),
            inspect_previous(root / NAME / "previous"),
        )
        old_marker = _read_private_file(root / NAME / "marker.bin", 64)
        if _legacy_read(Path(marker_path)) != old_marker or (
            stat.S_IMODE(os.lstat(marker_path).st_mode) != saved["marker"]["mode"]
        ):
            raise LegacyPredecessorRouteError("old marker must remain unchanged")
        if _stopped(process_probe) != "exact-three-role-absence":
            raise LegacyPredecessorRouteError("old processes returned during IPFW retirement")
        if _strict_snapshot(readonly_ipfw) != needed:
            raise LegacyPredecessorRouteError("old IPFW kernel diverged from sealed retirement step")
        return record["legacy_predecessor"]

    witness(initial)
    # The journal is fsynced before deleting even one rule. On any failure
    # leave legacy-ipfw-retiring, never retry/auto-accept partial kernel.
    store.begin_legacy_ipfw_retire(identity, lambda: witness(initial))
    current = {"rules": dict(initial["rules"]), "targets": list(initial["targets"])}
    for number in sorted((int(value) for value in initial["rules"]), reverse=True):
        witness(current)
        mutating_ipfw.delete_rule(number)
        current["rules"].pop(str(number))
        witness(current)
    # Destroy the exact historical fixed-name table only after all old
    # rules are absent. Never sweep unrelated tables or rule numbers.
    witness(current)
    mutating_ipfw._run("table", OLD_TABLE, "destroy", modifying=True)
    current["targets"] = None
    witness(current)
    result = store.finish_legacy_ipfw_retire(identity, lambda: witness(current))
    if result["phase"] != "legacy-ipfw-retired":
        raise LegacyPredecessorRouteError("old IPFW retirement not durably complete")
    return result



def retire_stopped_common_legacy_marker(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, process_probe, readonly_ipfw,
    require_lifecycle_owner,
):
    """PRIVATE exact PoC marker removal after old IPFW retirement.

    Never exposed through CLI, configd or GUI until the five-domain
    undo and new common-runtime activation are proven. One journal, FD9.
    """
    from shared_apply_operation import (
        SharedApplyOperation, fingerprint_legacy_predecessor,
    )
    from voice_native_legacy_ipfw_replay import _strict_snapshot
    from voice_native_legacy_reverse_wal import _stopped
    if not isinstance(store, SharedApplyOperation) or (
        not isinstance(process_probe, FreeBSDVoiceProcessProbe)
        or not isinstance(readonly_ipfw, FreeBSDIPFWAdapter)
        or readonly_ipfw.allow_mutations
        or (readonly_ipfw.rule_base, readonly_ipfw.rule_max) != (19000, 19010)
        or type(config_fd) is not int or config_fd < 0
        or not callable(require_lifecycle_owner)
    ):
        raise LegacyPredecessorRouteError("missing original marker retirement owner")
    work, marker_path = Path(work), Path(marker_path)
    root = work / "legacy-backup"
    if work.name != identity or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("marker candidate ID changed")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    record = store.read()
    if record is None or record["phase"] != "legacy-ipfw-retired" or (
        record["detail"]["id"] != identity or "previous" in record
        or "legacy_predecessor" not in record
    ):
        raise LegacyPredecessorRouteError("completed old IPFW retirement required")
    saved = inspect_legacy_previous_live_identity(root)
    plan = inspect_legacy_restore_plan(root)
    summary = inspect_legacy_previous(root)
    if plan["previous_five"] != summary["previous_five"] or (
        plan["marker_target"] != str(marker_path)
    ):
        raise LegacyPredecessorRouteError("marker target differs from restore plan")
    old_marker = _read_private_file(root / NAME / "marker.bin", 64)
    mode = saved["marker"]["mode"]
    if not old_marker or len(old_marker) != saved["marker"]["bytes"] or (
        hashlib.sha256(old_marker).hexdigest() != saved["marker"]["sha256"]
    ):
        raise LegacyPredecessorRouteError("untrusted sealed old marker")

    def witness(present, phase):
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        now = store.read()
        if now is None or now["phase"] != phase or (
            now["detail"] != record["detail"]
            or now.get("legacy_predecessor") != record["legacy_predecessor"]
        ):
            raise LegacyPredecessorRouteError("common marker journal changed")
        if fingerprint_legacy_predecessor(work, owner=config_owner[0]) != (
            record["legacy_predecessor"]
        ) or inspect_legacy_previous(root) != summary or (
            inspect_legacy_restore_plan(root) != plan
        ):
            raise LegacyPredecessorRouteError("old predecessor drifted")
        _verify_sources(
            Path(config_path), Path(active_runtime),
            inspect_previous(root / NAME / "previous"),
        )
        if _stopped(process_probe) != "exact-three-role-absence" or (
            _strict_snapshot(readonly_ipfw) != {"rules": {}, "targets": None}
        ):
            raise LegacyPredecessorRouteError("legacy processes/IPFW not cleared")
        if present:
            if _legacy_read(marker_path) != old_marker or (
                stat.S_IMODE(os.lstat(marker_path).st_mode) != mode
            ):
                raise LegacyPredecessorRouteError("old marker replaced")
        elif os.path.lexists(marker_path):
            raise LegacyPredecessorRouteError("old marker still exists")
        return record["legacy_predecessor"]

    witness(True, "legacy-ipfw-retired")
    # The single journal is fsynced before unlink, including on tmpfs /var/run.
    store.begin_legacy_marker_retire(
        identity, lambda: witness(True, "legacy-ipfw-retired")
    )
    witness(True, "legacy-marker-retiring")
    parent_fd = os.open(
        marker_path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        parent = os.fstat(parent_fd)
        if not stat.S_ISDIR(parent.st_mode) or (
            parent.st_uid != config_owner[0] or parent.st_mode & 0o022
        ):
            raise LegacyPredecessorRouteError("unsafe old marker parent")
        fd = os.open(
            marker_path.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0), dir_fd=parent_fd,
        )
        try:
            pinned = os.fstat(fd)
            on_path = os.stat(
                marker_path.name, dir_fd=parent_fd, follow_symlinks=False
            )
            if not stat.S_ISREG(pinned.st_mode) or pinned.st_nlink != 1 or (
                pinned.st_uid != config_owner[0]
                or stat.S_IMODE(pinned.st_mode) != mode
                or pinned.st_size != len(old_marker)
                or (pinned.st_dev, pinned.st_ino) != (
                    on_path.st_dev, on_path.st_ino
                )
                or os.read(fd, len(old_marker) + 1) != old_marker
            ):
                raise LegacyPredecessorRouteError("old marker inode is foreign")
            witness(True, "legacy-marker-retiring")
            current = os.stat(
                marker_path.name, dir_fd=parent_fd, follow_symlinks=False
            )
            if (current.st_dev, current.st_ino) != (
                pinned.st_dev, pinned.st_ino
            ):
                raise LegacyPredecessorRouteError("old marker swapped before unlink")
            os.unlink(marker_path.name, dir_fd=parent_fd)
            os.fsync(parent_fd)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)
    result = store.finish_legacy_marker_retire(
        identity, lambda: witness(False, "legacy-marker-retiring")
    )
    if result["phase"] != "legacy-marker-retired":
        raise LegacyPredecessorRouteError("old marker retirement not completed")
    return result



# Installed service functions are the ONLY common runtime actuator.
# This Python caller retains original FD9 and the pinned Config flock while
# the fixed child shell imports existing functions without redispatching FD9.
NATIVE_COMMON_SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
_NATIVE_FORWARD_SHELL = """
ZAPRET_NATIVE_PRIVATE_IMPORT=retired-legacy-forward
. /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh || exit 69
unset ZAPRET_NATIVE_PRIVATE_IMPORT
case "$1" in
    probe) apply_runtime_probe "$2" 1 ;;
    activate) apply_runtime_activate_retired_legacy "$2" "$3" ;;
    attest) apply_runtime_rehydrate_retired_legacy "$2" "$3" ;;
    config-save) shared_apply_save_retired_legacy_config_service "$3" ;;
    *) exit 64 ;;
esac
"""


def _invoke_existing_native_common(
    *, mode, identity, work, config_fd, require_lifecycle_owner,
    service_script=None, runner=None,
):
    """Call the actual installed native actuator with the parent's two locks."""
    if mode not in ("probe", "activate", "attest", "config-save") or not isinstance(identity, str) or (
        COMMON_ID.fullmatch(identity) is None
    ):
        raise LegacyPredecessorRouteError("invalid fixed native forward action")
    work = Path(work)
    if work.name != identity or not work.is_absolute() or (
        type(config_fd) is not int or config_fd < 0 or config_fd == 9
    ) or not callable(require_lifecycle_owner):
        raise LegacyPredecessorRouteError("native callback lacks original pinned owner")
    # Test injection cannot override the canonical installed runtime path:
    # only the constant itself can be patched in an isolated test.
    script = NATIVE_COMMON_SERVICE if service_script is None else Path(service_script)
    if script != NATIVE_COMMON_SERVICE:
        raise LegacyPredecessorRouteError("foreign common actuator script")
    info = script.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
        or info.st_nlink != 1 or info.st_mode & 0o022):
        raise LegacyPredecessorRouteError("untrusted installed common actuator")
    require_lifecycle_owner()
    action = subprocess.run if runner is None else runner
    if not callable(action):
        raise LegacyPredecessorRouteError("invalid native runtime runner")
    # Arguments are positional, NEVER interpolated into the fixed shell
    # program. The original Config file description and FD9 stay inherited.
    result = action(
        ["/bin/sh", "-c", _NATIVE_FORWARD_SHELL,
         "native-common-forward", mode, str(work / "release"), identity],
        check=False, capture_output=True, text=True, timeout=90,
        # The caller MUST release the OLD pinned Config flock before the
        # native writer. PHP owns Config::lock/save; do not leak the old
        # Config descriptor into the Config::save subprocess. Original FD9
        # remains held across both the intent journal and native save.
        pass_fds=(9,) if mode == "config-save" else (9, config_fd),
        env={"LC_ALL": "C",
             "PATH": "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin"},
    )
    if (result.returncode != 0 or len(result.stdout.encode("utf-8")) > 8192
        or len(result.stderr.encode("utf-8")) > 8192):
        raise LegacyPredecessorRouteError("native common actuator requires review")
    return True



def activate_common_after_legacy_retirement(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, process_probe, readonly_ipfw,
    require_lifecycle_owner, common_preflight=None, common_activate=None,
    common_attest=None,
):
    """PRIVATE forward runtime actuator after exact old IPFW/marker retirement.

    The caller holds the ORIGINAL FD9 and pinned Config inode flock for the
    entire operation. Its fixed common_activate callback uses the EXISTING
    apply_runtime_activate (one engine/supervisor/IPFW), not an old PoC
    process. A durable intent is written BEFORE invoking that actuator.
    A crash never retries it: no cold-boot or GUI route exists yet.
    The native private path advances through ONE OPNsense Config save after
    journaling; final native IPFW COMMIT and full crash recovery remain gated.
    """
    from shared_apply_operation import (
        SharedApplyOperation, fingerprint_legacy_predecessor,
    )
    from voice_native_legacy_ipfw_replay import _strict_snapshot
    from voice_native_legacy_reverse_wal import _stopped
    from shared_apply_seal import verify_seal
    from voice_ipfw_adapter import shared_release_manifest, shared_firewall_action
    from voice_live_inspect import inspect_common_runtime

    if not isinstance(store, SharedApplyOperation) or (
        not isinstance(process_probe, FreeBSDVoiceProcessProbe)
        or not isinstance(readonly_ipfw, FreeBSDIPFWAdapter)
        or readonly_ipfw.allow_mutations
        or (readonly_ipfw.rule_base, readonly_ipfw.rule_max) != (19000, 19010)
        or type(config_fd) is not int or config_fd < 0
        or not callable(require_lifecycle_owner)
        or not (all(cb is None for cb in (
            common_preflight, common_activate, common_attest
        )) or all(callable(cb) for cb in (
            common_preflight, common_activate, common_attest
        )))
    ):
        raise LegacyPredecessorRouteError("missing original common runtime owner")
    work = Path(work)
    root = work / "legacy-backup"
    if work.name != identity or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("common runtime candidate identity changed")
    record = store.read()
    if record is None or record["phase"] != "legacy-marker-retired" or (
        record["detail"]["id"] != identity
        or record["detail"]["page"] != "voice"
        or "legacy_predecessor" not in record or "previous" in record
    ):
        raise LegacyPredecessorRouteError("old owner must be wholly retired before activation")
    old = inspect_previous(root / NAME / "previous")
    seal = inspect_legacy_previous(root)
    plan = inspect_legacy_restore_plan(root)
    if plan["previous_five"] != seal["previous_five"]:
        raise LegacyPredecessorRouteError("old rollback evidence no longer matches")
    release = work / "release"

    native_forward = common_preflight is None
    if native_forward:
        # The production caller now uses the actual installed common service
        # and the same engine/IPFW adapter, not hypothetical injection-only
        # callbacks. The journal intent is recorded before the ONLY start.
        def common_preflight():
            return _invoke_existing_native_common(
                mode="probe", identity=identity, work=work,
                config_fd=config_fd, require_lifecycle_owner=require_lifecycle_owner,
            )
        def common_activate():
            return _invoke_existing_native_common(
                mode="activate", identity=identity, work=work,
                config_fd=config_fd, require_lifecycle_owner=require_lifecycle_owner,
            )
        def common_attest():
            # The activation shell is already gone: restore its ephemeral
            # APPLY_* context ONLY after independently proving the installed
            # native release, single engine/supervisor and staged IPFW.
            _invoke_existing_native_common(
                mode="attest", identity=identity, work=work,
                config_fd=config_fd, require_lifecycle_owner=require_lifecycle_owner,
            )
            return record["detail"]["candidate"]

    def native_bundle():
        # Attest the SAME sealed Voice+Strategies release used by native
        # Apply. A callback's success string alone is not kernel evidence.
        verify_seal(work, owner=config_owner[0])
        manifest = shared_release_manifest(release)
        if (manifest["rule_base"], manifest["rule_max"]) != (19000, 19010):
            raise LegacyPredecessorRouteError("common IPFW range changed")
        return manifest

    def retired():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        if store.read() != record or (
            fingerprint_legacy_predecessor(work, owner=config_owner[0])
            != record["legacy_predecessor"]
        ) or inspect_legacy_previous(root) != seal or (
            inspect_legacy_restore_plan(root) != plan
        ):
            raise LegacyPredecessorRouteError("old owner or journal drifted before forward")
        _verify_sources(Path(config_path), Path(active_runtime), old)
        if os.path.lexists(marker_path) or (
            _stopped(process_probe) != "exact-three-role-absence"
        ) or _strict_snapshot(readonly_ipfw) != {"rules": {}, "targets": None}:
            raise LegacyPredecessorRouteError("old runtime/IPFW/marker not wholly retired")
        native_bundle()
        if common_preflight() is not True:
            raise LegacyPredecessorRouteError("ordinary common runtime preflight refused")
        return record["legacy_predecessor"]

    retired()
    intent = store.begin_legacy_common_activation(identity, retired)
    if intent["phase"] != "legacy-common-activating":
        raise LegacyPredecessorRouteError("common activation intent was not durable")
    # Any exception/failure below is intentionally fail-closed. No second
    # engine start or automatic old-PoC restart is attempted from this phase.
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    if store.read() != intent or common_activate() is not True:
        raise LegacyPredecessorRouteError("common runtime activation interrupted")

    def attested():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        if store.read() != intent or (
            fingerprint_legacy_predecessor(work, owner=config_owner[0])
            != record["legacy_predecessor"]
        ) or os.path.lexists(marker_path):
            raise LegacyPredecessorRouteError("previous seal changed after forward activation")
        # The fixed caller must independently prove exact installed release,
        # single engine/monitor PID+argv, scoped native IPFW and old Config.
        # This callback returns the saved candidate generation ONLY on proof.
        if common_attest() != record["detail"]["candidate"]:
            raise LegacyPredecessorRouteError("common engine/IPFW witness differs from candidate")
        if native_forward:
            # The original Config must still be unsaved at this boundary,
            # and the deterministic native BACKUP must match the complete
            # immutable old runtime captured before any PoC STOP. This is
            # independent of the shell's reconstructed APPLY_* variables.
            active = Path(active_runtime)
            backup = active.parent / (active.name + "-backups") / (
                active.name + "-" + identity
            )
            _verify_sources(Path(config_path), backup, old)
        manifest = native_bundle()
        runtime = inspect_common_runtime(release, manifest, active=Path(active_runtime))
        if not isinstance(runtime, dict) or runtime.get("state") != "running" or (
            runtime.get("source_verified") is not True
            or runtime.get("engine_verified") is not True
            or runtime.get("supervisor_verified") is not True
        ):
            raise LegacyPredecessorRouteError("installed common runtime is not independently running")
        # The original old IPFW state is wholly empty. Native Install
        # keeps rollback stages until native Config save and Commit; the
        # ordinary post-commit verify would incorrectly reject that phase.
        empty = {"rule_base": manifest["rule_base"],
                 "rule_max": manifest["rule_max"], "rules": {}, "tables": {}}
        shared_firewall_action(readonly_ipfw, "verify-staged", empty, manifest)
        return record["legacy_predecessor"]

    attested()
    result = store.finish_legacy_common_activation(identity, attested)
    if result["phase"] != "legacy-common-activated":
        raise LegacyPredecessorRouteError("common runtime not sealed after start")
    return result



def rollback_pristine_common_after_interruption(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, process_probe, readonly_ipfw,
    require_lifecycle_owner, common_absence,
):
    """PRIVATE one-way recovery of an interrupted but untouched common start.

    The caller holds original FD9 and original Config inode flock. Its
    common_absence callback must attest a complete absence of common engine,
    supervisor, installed/staged native artifacts and other kernel ownership.
    Changed/partial native activation is deliberately NOT handled here.
    """
    from shared_apply_operation import (
        SharedApplyOperation, fingerprint_legacy_predecessor,
    )
    from voice_native_legacy_ipfw_replay import _strict_snapshot
    from voice_native_legacy_reverse_wal import _stopped

    if not isinstance(store, SharedApplyOperation) or (
        not isinstance(process_probe, FreeBSDVoiceProcessProbe)
        or not isinstance(readonly_ipfw, FreeBSDIPFWAdapter)
        or readonly_ipfw.allow_mutations
        or (readonly_ipfw.rule_base, readonly_ipfw.rule_max) != (19000, 19010)
        or type(config_fd) is not int or config_fd < 0
        or not callable(require_lifecycle_owner)
        or not callable(common_absence)
    ):
        raise LegacyPredecessorRouteError("missing original pristine rollback owner")
    work, marker_path = Path(work), Path(marker_path)
    root = work / "legacy-backup"
    if work.name != identity or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("pristine rollback candidate identity changed")
    record = store.read()
    if record is None or record["phase"] != "legacy-common-activating" or (
        record["detail"]["id"] != identity
        or record["detail"]["page"] != "voice"
        or "legacy_predecessor" not in record or "previous" in record
    ):
        raise LegacyPredecessorRouteError("common activation has no reversible intent")
    old = inspect_previous(root / NAME / "previous")
    seal = inspect_legacy_previous(root)
    plan = inspect_legacy_restore_plan(root)
    if plan["previous_five"] != seal["previous_five"] or (
        plan["marker_target"] != str(marker_path)
    ):
        raise LegacyPredecessorRouteError("old restore evidence not bound to marker")

    def pristine():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        if store.read() != record or (
            fingerprint_legacy_predecessor(work, owner=config_owner[0])
            != record["legacy_predecessor"]
        ) or inspect_legacy_previous(root) != seal or (
            inspect_legacy_restore_plan(root) != plan
        ):
            raise LegacyPredecessorRouteError("old seal or common journal drifted")
        _verify_sources(Path(config_path), Path(active_runtime), old)
        if os.path.lexists(marker_path) or (
            _stopped(process_probe) != "exact-three-role-absence"
        ) or _strict_snapshot(readonly_ipfw) != {"rules": {}, "targets": None}:
            raise LegacyPredecessorRouteError("old runtime or IPFW not pristine")
        if common_absence() is not True:
            raise LegacyPredecessorRouteError("common engine or artifacts remain")
        return record["legacy_predecessor"]

    # atomic_install_tree uses deterministic original-service names for
    # the same candidate ID. Even a stage containing no running process
    # means the activation did mutate state and is NOT pristine.
    active = Path(active_runtime)
    native_paths = (
        active.parent / ("." + active.name + ".stage." + identity),
        active.parent / ("." + active.name + ".old." + identity),
        active.parent / (active.name + "-backups") /
            (active.name + "-" + identity),
    )
    def pristine_atomic():
        if any(os.path.lexists(path) for path in native_paths):
            raise LegacyPredecessorRouteError("native atomic stage/backup remains")
        return pristine()

    pristine_atomic()
    result = store.begin_pristine_common_activation_rollback(
        identity, pristine_atomic
    )
    if result["phase"] != "legacy-rollback-ipfw":
        raise LegacyPredecessorRouteError("old rollback intent not durable")
    return result


def restore_retired_common_legacy_ipfw(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, process_probe, readonly_ipfw,
    mutating_ipfw, require_lifecycle_owner,
):
    """PRIVATE reverse of the old IPFW removal, under the SAME shared journal.

    Reuses the fully sealed old restore plan and existing FreeBSD IPFW adapter.
    It is restartable only from exact rule/table prefixes of that plan; no
    second undo ledger, blind rule sweep, GUI/configd/boot entrypoint or new
    native owner is created. The old engine and marker remain OFF throughout.
    """
    from shared_apply_operation import (
        SharedApplyOperation, fingerprint_legacy_predecessor,
    )
    from voice_native_legacy_ipfw_replay import (
        _strict_snapshot, _expected_after,
    )
    from voice_native_legacy_reverse_wal import _stopped
    if not isinstance(store, SharedApplyOperation) or (
        not isinstance(process_probe, FreeBSDVoiceProcessProbe)
        or not isinstance(readonly_ipfw, FreeBSDIPFWAdapter)
        or readonly_ipfw.allow_mutations
        or not isinstance(mutating_ipfw, FreeBSDIPFWAdapter)
        or not mutating_ipfw.allow_mutations
        or (readonly_ipfw.rule_base, readonly_ipfw.rule_max) != (19000, 19010)
        or (mutating_ipfw.rule_base, mutating_ipfw.rule_max) != (19000, 19010)
        or type(config_fd) is not int or config_fd < 0
        or not callable(require_lifecycle_owner)
    ):
        raise LegacyPredecessorRouteError("missing original legacy rollback authority")
    work, marker_path = Path(work), Path(marker_path)
    root = work / "legacy-backup"
    if work.name != identity or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("old rollback candidate differs from seal")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    record = store.read()
    if record is None or record["phase"] not in (
        "legacy-marker-retired", "legacy-rollback-ipfw"
    ) or record["detail"]["id"] != identity or (
        "legacy_predecessor" not in record or "previous" in record
    ):
        raise LegacyPredecessorRouteError("verified retired marker/rollback intent required")
    original = inspect_legacy_previous(root)
    plan = inspect_legacy_restore_plan(root)
    if plan["previous_five"] != original["previous_five"] or (
        plan["marker_target"] != str(marker_path)
    ):
        raise LegacyPredecessorRouteError("old IPFW plan not bound to marker/owner")
    saved = inspect_legacy_previous_live_identity(root)
    expected = saved["legacy_ipfw_previous"]
    commands = plan["legacy_ipfw_commands"]
    if (not isinstance(commands, list) or not 3 <= len(commands) <= 4100):
        raise LegacyPredecessorRouteError("untrusted bounded original IPFW commands")
    total = len(commands)

    def held():
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        phase = store.read()
        if phase is None or phase["phase"] not in (
            "legacy-marker-retired", "legacy-rollback-ipfw"
        ) or phase["detail"] != record["detail"] or (
            phase.get("legacy_predecessor") != record["legacy_predecessor"]
        ):
            raise LegacyPredecessorRouteError("old rollback journal changed")
        if fingerprint_legacy_predecessor(work, owner=config_owner[0]) != (
            record["legacy_predecessor"]
        ) or inspect_legacy_previous(root) != original or (
            inspect_legacy_restore_plan(root) != plan
        ):
            raise LegacyPredecessorRouteError("immutable old restore plan changed")
        _verify_sources(
            Path(config_path), Path(active_runtime),
            inspect_previous(root / NAME / "previous"),
        )
        if os.path.lexists(marker_path):
            raise LegacyPredecessorRouteError("foreign/re-enabled old marker during rollback")
        if _stopped(process_probe) != "exact-three-role-absence":
            raise LegacyPredecessorRouteError("unexpected engine during old IPFW rollback")
        return phase

    if record["phase"] == "legacy-marker-retired":
        held()
        if _strict_snapshot(readonly_ipfw) != _expected_after(plan, 0):
            raise LegacyPredecessorRouteError("nonempty IPFW before old rollback intent")
        store.begin_legacy_ipfw_rollback(
            identity, lambda: (
                record["legacy_predecessor"] if (
                    held()["phase"] == "legacy-marker-retired" and
                    _strict_snapshot(readonly_ipfw) == _expected_after(plan, 0)
                ) else None
            )
        )
    else:
        held()

    # A power cut may follow an IPFW command before the next Python line.
    # Only an exact complete prefix of the sealed plan is resumable.
    live = _strict_snapshot(readonly_ipfw)
    matching = [n for n in range(total + 1)
                if _expected_after(plan, n) == live]
    if len(matching) != 1:
        raise LegacyPredecessorRouteError("unknown or ambiguous partial old IPFW rollback")
    start = matching[0]
    for index in range(start, total):
        if held()["phase"] != "legacy-rollback-ipfw":
            raise LegacyPredecessorRouteError("old rollback phase changed")
        if _strict_snapshot(readonly_ipfw) != _expected_after(plan, index):
            raise LegacyPredecessorRouteError("IPFW drift before next sealed restore command")
        cmd = commands[index]
        if not isinstance(cmd, list) or not cmd or cmd[0] != "/sbin/ipfw":
            raise LegacyPredecessorRouteError("untrusted original IPFW operation")
        mutating_ipfw._run(*cmd[1:], modifying=True)
        if _strict_snapshot(readonly_ipfw) != _expected_after(plan, index + 1):
            raise LegacyPredecessorRouteError("IPFW partial/foreign result after restore command")
    if held()["phase"] != "legacy-rollback-ipfw" or (
        _strict_snapshot(readonly_ipfw) != _expected_after(plan, total)
    ):
        raise LegacyPredecessorRouteError("old IPFW rollback incomplete")
    final = _expected_after(plan, total)
    if final != {
        "rules": dict(expected["rules"]), "targets": sorted(expected["targets"])
    }:
        raise LegacyPredecessorRouteError("restored kernel does not match sealed old owner")
    result = store.finish_legacy_ipfw_rollback(
        identity, lambda: (
            record["legacy_predecessor"] if (
                held()["phase"] == "legacy-rollback-ipfw" and
                _strict_snapshot(readonly_ipfw) == final
            ) else None
        )
    )
    if result["phase"] != "legacy-rollback-ipfw-restored":
        raise LegacyPredecessorRouteError("old IPFW recovery not sealed in common journal")
    return result



def restore_retired_common_legacy_marker(
    *, identity, store, work, config_path, config_fd, config_owner,
    active_runtime, marker_path, process_probe, readonly_ipfw,
    require_lifecycle_owner,
):
    """PRIVATE resumable exact old-marker restoration under the common FD9 WAL.

    Journal intent precedes all filesystem writes; a durable same-directory
    hardlink pins the provenance until the journal confirms restoration.
    A foreign target or stage is NEVER adopted or replaced. No engine start.
    """
    from shared_apply_operation import (
        SharedApplyOperation, fingerprint_legacy_predecessor,
    )
    from voice_native_legacy_ipfw_replay import _strict_snapshot, _expected_after
    from voice_native_legacy_reverse_wal import _stopped
    if not isinstance(store, SharedApplyOperation) or (
        not isinstance(process_probe, FreeBSDVoiceProcessProbe)
        or not isinstance(readonly_ipfw, FreeBSDIPFWAdapter)
        or readonly_ipfw.allow_mutations
        or (readonly_ipfw.rule_base, readonly_ipfw.rule_max) != (19000, 19010)
        or type(config_fd) is not int or config_fd < 0
        or not callable(require_lifecycle_owner)
    ):
        raise LegacyPredecessorRouteError("untrusted original marker rollback owner")
    work, marker_path = Path(work), Path(marker_path)
    root = work / "legacy-backup"
    if work.name != identity or not COMMON_ID.fullmatch(identity):
        raise LegacyPredecessorRouteError("marker rollback identity is foreign")
    require_lifecycle_owner()
    _locked_config(Path(config_path), config_fd, config_owner)
    record = store.read()
    phase = record["phase"] if record is not None else None
    if phase not in (
        "legacy-rollback-ipfw-restored", "legacy-rollback-marker",
        "legacy-rollback-marker-restored",
    ) or record["detail"]["id"] != identity or (
        "legacy_predecessor" not in record or "previous" in record
    ):
        raise LegacyPredecessorRouteError("old IPFW rollback must be sealed first")
    previous = inspect_legacy_previous(root)
    plan = inspect_legacy_restore_plan(root)
    saved = inspect_legacy_previous_live_identity(root)
    if plan["previous_five"] != previous["previous_five"] or (
        plan["marker_target"] != str(marker_path)
    ):
        raise LegacyPredecessorRouteError("old marker target differs from sealed plan")
    raw = _read_private_file(root / NAME / "marker.bin", 64)
    mode = saved["marker"]["mode"]
    if not raw or len(raw) != saved["marker"]["bytes"] or (
        hashlib.sha256(raw).hexdigest() != saved["marker"]["sha256"]
    ):
        raise LegacyPredecessorRouteError("untrusted sealed old marker content")
    stage_name = "." + marker_path.name + ".voice-old-" + identity[:16]
    if stage_name == marker_path.name or len(stage_name.encode("ascii")) > 255:
        raise LegacyPredecessorRouteError("untrusted fixed old marker stage name")
    expected_kernel = _expected_after(plan, len(plan["legacy_ipfw_commands"]))

    def attest(phases):
        require_lifecycle_owner()
        _locked_config(Path(config_path), config_fd, config_owner)
        current = store.read()
        if current is None or current["phase"] not in phases or (
            current["detail"] != record["detail"]
            or current.get("legacy_predecessor") != record["legacy_predecessor"]
        ):
            raise LegacyPredecessorRouteError("original marker rollback journal changed")
        if fingerprint_legacy_predecessor(work, owner=config_owner[0]) != (
            record["legacy_predecessor"]
        ) or inspect_legacy_previous(root) != previous or (
            inspect_legacy_restore_plan(root) != plan
        ):
            raise LegacyPredecessorRouteError("old marker evidence has changed")
        _verify_sources(
            Path(config_path), Path(active_runtime),
            inspect_previous(root / NAME / "previous"),
        )
        if _stopped(process_probe) != "exact-three-role-absence" or (
            _strict_snapshot(readonly_ipfw) != expected_kernel
        ):
            raise LegacyPredecessorRouteError("old engine/IPFW not in rollback state")
        return current["phase"]

    parent_fd = os.open(
        marker_path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        directory = os.fstat(parent_fd)
        if not stat.S_ISDIR(directory.st_mode) or (
            directory.st_uid != config_owner[0] or directory.st_mode & 0o022
        ):
            raise LegacyPredecessorRouteError("untrusted marker parent")
        def named(name):
            try:
                fd = os.open(
                    name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_NONBLOCK", 0), dir_fd=parent_fd,
                )
            except FileNotFoundError:
                return None
            try:
                opened = os.fstat(fd)
                on_path = os.stat(
                    name, dir_fd=parent_fd, follow_symlinks=False,
                )
                if not stat.S_ISREG(opened.st_mode) or (
                    opened.st_uid != config_owner[0]
                    or stat.S_IMODE(opened.st_mode) != mode
                    or opened.st_size != len(raw)
                    or (opened.st_dev, opened.st_ino) != (
                        on_path.st_dev, on_path.st_ino
                    ) or os.read(fd, len(raw) + 1) != raw
                ):
                    raise LegacyPredecessorRouteError("foreign staged/target marker")
                return opened
            finally:
                os.close(fd)

        if phase == "legacy-rollback-ipfw-restored":
            attest((phase,))
            if named(marker_path.name) is not None or named(stage_name) is not None:
                raise LegacyPredecessorRouteError("preexisting marker/stage not owned")
            store.begin_legacy_marker_rollback(
                identity, lambda: (
                    record["legacy_predecessor"] if (
                        attest((phase,)) == phase
                        and named(marker_path.name) is None
                        and named(stage_name) is None
                    ) else None
                )
            )
        else:
            attest((phase,))

        phase = store.read()["phase"]
        if phase == "legacy-rollback-marker-restored":
            # The target+stage may still be linked after journal fsync.
            # Clean up only our verified two-link staging inode, never a
            # preexisting marker without its provenance.
            target, stage = named(marker_path.name), named(stage_name)
            if target is None or target.st_nlink not in (1, 2):
                raise LegacyPredecessorRouteError("completed old marker missing")
        else:
            target, stage = named(marker_path.name), named(stage_name)
            if target is not None and stage is None:
                raise LegacyPredecessorRouteError("marker has no staging provenance")
            if target is None and stage is None:
                attest(("legacy-rollback-marker",))
                fd = os.open(
                    stage_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o600, dir_fd=parent_fd,
                )
                try:
                    if os.write(fd, raw) != len(raw):
                        raise LegacyPredecessorRouteError("short marker stage write")
                    os.fchmod(fd, mode)
                    os.fsync(fd)
                finally:
                    os.close(fd)
                os.fsync(parent_fd)
                stage = named(stage_name)
            if target is None:
                if stage is None or stage.st_nlink != 1:
                    raise LegacyPredecessorRouteError("unsafe marker stage link count")
                attest(("legacy-rollback-marker",))
                os.link(
                    stage_name, marker_path.name,
                    src_dir_fd=parent_fd, dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                os.fsync(parent_fd)
                target = named(marker_path.name)
                stage = named(stage_name)
            if target is None or stage is None or (
                target.st_nlink != 2 or stage.st_nlink != 2
                or (target.st_dev, target.st_ino) != (stage.st_dev, stage.st_ino)
            ):
                raise LegacyPredecessorRouteError("marker staging provenance changed")
            store.finish_legacy_marker_rollback(
                identity, lambda: (
                    record["legacy_predecessor"] if (
                        attest(("legacy-rollback-marker",)) == "legacy-rollback-marker"
                        and (lambda a, b: a is not None and b is not None
                             and a.st_nlink == b.st_nlink == 2
                             and (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino))(
                                 named(marker_path.name), named(stage_name)
                             )
                    ) else None
                )
            )

        attest(("legacy-rollback-marker-restored",))
        target, stage = named(marker_path.name), named(stage_name)
        if stage is not None:
            if target is None or target.st_nlink != 2 or (
                stage.st_nlink != 2 or
                (stage.st_dev, stage.st_ino) != (target.st_dev, target.st_ino)
            ):
                raise LegacyPredecessorRouteError("foreign lingering marker restore stage")
            os.unlink(stage_name, dir_fd=parent_fd)
            os.fsync(parent_fd)
        final = named(marker_path.name)
        if final is None or final.st_nlink != 1 or (
            named(stage_name) is not None
        ):
            raise LegacyPredecessorRouteError("restored marker inode not finalized")
        attest(("legacy-rollback-marker-restored",))
        result = store.read()
        if result["phase"] != "legacy-rollback-marker-restored":
            raise LegacyPredecessorRouteError("marker rollback not durably completed")
        return result
    finally:
        os.close(parent_fd)


def main(argv):
    candidate_id = argv[1] if (
        len(argv) == 2 and argv[0] == "capture-common"
        and COMMON_ID.fullmatch(argv[1])
    ) else None
    cancellation_id = argv[1] if (
        len(argv) == 2 and argv[0] == "cancel-common"
        and COMMON_ID.fullmatch(argv[1])
    ) else None
    begin_id = argv[1] if (
        len(argv) == 2 and argv[0] == "begin-common"
        and COMMON_ID.fullmatch(argv[1])
    ) else None
    if argv != ["capture-plan"] and candidate_id is None and cancellation_id is None and begin_id is None:
        print("usage: voice_native_legacy_predecessor_route.py capture-plan|capture-common ID|cancel-common ID|begin-common ID",
              file=sys.stderr)
        return 64
    fd=None
    try:
        native.require_native_lock()
        fd=os.open(native.CONFIG,os.O_RDWR| getattr(os,"O_NOFOLLOW",0))
        _pinned_regular(native.CONFIG,fd,owner=(0,0))
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if cancellation_id is not None or begin_id is not None:
            from shared_apply_operation import SharedApplyOperation
            operation_id = cancellation_id if cancellation_id is not None else begin_id
            from shared_apply_seal import WORK
            store = SharedApplyOperation(owner=0)
            root = WORK / operation_id / "legacy-backup"
            _private_dir(root)
            probe = FreeBSDVoiceProcessProbe(
                EXPECTED_SCRIPTS, PIDFILES, native.WHOLE / "previous",
            )
            result = cancel_unchanged_common_predecessor(
                identity=operation_id, store=store,
                work=WORK / operation_id, config_path=native.CONFIG,
                config_fd=fd, config_owner=(0,0),
                active_runtime=native.ACTIVE_ROOT,
                marker_path=native.LEGACY_MARKER, ledger_root=native.LEDGER,
                process_probe=probe, kernel_reader=FreeBSDKernelArgvReader(),
                readonly_ipfw=FreeBSDIPFWAdapter(19000,19010),
                require_lifecycle_owner=native.require_native_lock,
                begin=begin_id is not None,
            )
            wanted = "legacy-quiescing" if begin_id is not None else "restored"
            if result["phase"] != wanted or result["detail"]["id"] != operation_id:
                raise LegacyPredecessorRouteError("old owner transition incomplete")
            if begin_id is not None:
                print("legacy-quiescing-id="+operation_id)
                print("legacy-stop-executed=0")
            else:
                print("legacy-cancelled-id="+operation_id)
            print("legacy-handoff-authorized=0")
            return 0
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
