#!/usr/bin/env python3
"""Original-lock old Telegram three-role restart with durable single-shot intent.

This is an INTERNAL real fixed-actuator caller; no CLI, service, GUI or boot
dispatch. It never declares the five-domain rollback complete or enables Voice.
The previous marker/Config/runtime/IPFW must ALREADY be restored and attested.
A sealed schema-2 supervisor argv + UID/GID/kernel-image policy is mandatory.

Before calling the fixed one-engine lifecycle script, persist a write-once,
fsynced restart intent. A crash MAY leave running processes: retry NEVER calls
start again. Instead it requires independently matched three-role PID/start,
FreeBSD kernel argv and kernel-image/UID/GID and seals a separate observation.
Any partial, stopped, foreign or unstable post-intent process state fails
closed for manual review. No automatic stop or teardown is attempted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from voice_cutover_backup import (
    _private_dir, _read_private_file, _sync_dir, inspect_previous,
)
from voice_native_legacy_previous_seal import (
    NAME, _digest, _write_once, inspect_legacy_previous,
)
from voice_native_legacy_restore_plan import PLAN_NAME, inspect_legacy_restore_plan
from voice_native_legacy_reverse_wal import (
    WAL_NAME, inspect_legacy_reverse_wal, _ledger_clear, _stopped,
)
from voice_native_legacy_files_ready import (
    FILES_NAME, inspect_legacy_files_ready,
)
from voice_native_legacy_ipfw_replay import (
    REPLAY_NAME, _strict_snapshot, _expected_after, _steps,
)
from voice_native_legacy_runtime_restore import (
    NAME_RESTORE, _intent_data, _read_intent,
)
from voice_native_legacy_config_restore import (
    CONFIG_NAME, _record as config_record, _read_intent_config,
)
from voice_native_legacy_marker_restore import (
    MARKER_NAME, _read_intent_marker, _marker_stat,
)
from voice_cutover_runtime_restore import _safe_parent, _fingerprint
from voice_cutover_config_restore import _pinned_regular, _sha_fd
from voice_native_recovery_quiescence import (
    _locked_config, EXPECTED_SCRIPTS, PIDFILES,
)
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_process_recovery_evidence import (
    inspect_process_evidence, _runtime_args_digest, _normalize,
)
from voice_security_policy_evidence import (
    SUPERVISOR_BOUND_POLICY_SCHEMA, inspect_security_policy,
    verify_current_security,
)
from voice_freebsd_process_security import FreeBSDProcessSecurityReader
from voice_freebsd_kernel_argv import FreeBSDKernelArgvReader
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_restart_argv_attestation import inspect_restarted_argv
from voice_native_process_actions import (
    _secure_script, SHELL, SCRIPT,
)

PROCESS_NAME = "legacy-process-restart"
SCHEMA = 1
LIMIT = 16384
BASE_FILES = frozenset((
    NAME, PLAN_NAME, WAL_NAME, REPLAY_NAME, FILES_NAME, NAME_RESTORE,
    CONFIG_NAME, MARKER_NAME,
))
START_FILES = frozenset(("intent.json", "intent.sha256"))
FINAL_FILES = START_FILES | {"verified.json", "verified.sha256"}
ROLES = ("engine", "daemon", "monitor")


class LegacyProcessRestartError(RuntimeError):
    pass


def _canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")


def _read_record(directory, stem, limit=LIMIT):
    raw=_read_private_file(directory/(stem+".json"),limit)
    seal=_read_private_file(directory/(stem+".sha256"),65)
    if seal!=(_digest(raw)+"\n").encode("ascii"):
        raise LegacyProcessRestartError("corrupt durable restart record")
    return json.loads(raw)


def _write_record(directory, stem, row):
    raw=_canonical(row)
    if len(raw)>LIMIT:
        raise LegacyProcessRestartError("oversized restart record")
    _write_once(directory/(stem+".json"),raw)
    _write_once(directory/(stem+".sha256"),(_digest(raw)+"\n").encode("ascii"))
    _sync_dir(directory)


def restart_legacy_processes(
    *, root, config_path, config_fd, config_owner, active_runtime,
    marker_path, ledger_root, process_probe, readonly_ipfw,
    security_reader, argv_reader, require_lifecycle_owner,
    runner=None, actuator=SCRIPT,
):
    """Start exactly once; only verified all-running processes can be adopted."""
    if (not callable(require_lifecycle_owner) or
        type(config_fd) is not int or config_fd<0 or
        not isinstance(process_probe,FreeBSDVoiceProcessProbe) or
        process_probe.expected!=EXPECTED_SCRIPTS or
        process_probe.pidfiles!=PIDFILES or
        not isinstance(security_reader,FreeBSDProcessSecurityReader) or
        not isinstance(argv_reader,FreeBSDKernelArgvReader) or
        security_reader.probe is not process_probe or
        argv_reader.process_probe is not process_probe or
        security_reader.expected_scripts!=EXPECTED_SCRIPTS or
        argv_reader.expected_paths!=EXPECTED_SCRIPTS or
        (runner is None and Path(actuator)!=SCRIPT)):
        raise LegacyProcessRestartError("missing fixed FreeBSD restart policy/owner")
    root,config_path,active,marker=map(Path,(
        root,config_path,active_runtime,marker_path,
    ))
    def held():
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        return _pinned_regular(config_path,config_fd,owner=config_owner)

    held()
    _private_dir(root)
    entries=set(os.listdir(root))
    if entries not in (BASE_FILES, BASE_FILES|{PROCESS_NAME}):
        raise LegacyProcessRestartError("foreign or missing legacy rollback evidence")
    resumed=PROCESS_NAME in entries
    plan=inspect_legacy_restore_plan(root)
    wal=inspect_legacy_reverse_wal(
        root,allow_ipfw_replay=True,allow_files_stage=FILES_NAME,
        allow_runtime_restore=True,allow_config_restore=True,
        allow_marker_restore=True,allow_process_restart=resumed,
    )
    ready=inspect_legacy_files_ready(
        root,allow_runtime_restore=True,allow_config_restore=True,
        allow_marker_restore=True,allow_process_restart=resumed,
    )
    old=inspect_legacy_previous(root)
    if (ready["previous_five"]!=plan["previous_five"] or
        old["previous_five"]!=plan["previous_five"]):
        raise LegacyProcessRestartError("old process policy previous-five mismatch")
    source=root/NAME/"previous"
    original=inspect_previous(source)
    image=root/FILES_NAME/"install-image"
    policy=inspect_security_policy(
        root/NAME/"process-security-policy",source,
        root/NAME/"process-evidence",expected_scripts=EXPECTED_SCRIPTS,
    )
    if (policy["schema"]!=SUPERVISOR_BOUND_POLICY_SCHEMA or
        policy["policy_sha256"]!=wal["process_security_policy_sha256"] or
        policy["policy"]["previous"]!=plan["previous_five"] or
        policy["policy"]["supervisor_argv"]!=canonical_supervisor_argv(EXPECTED_SCRIPTS) or
        security_reader.kernel_images!=policy["policy"]["images"] or
        security_reader.credentials!=policy["policy"]["credentials"]):
        raise LegacyProcessRestartError("untrusted old three-role security/argv policy")
    earlier=inspect_process_evidence(
        root/NAME/"process-evidence",source,EXPECTED_SCRIPTS,
        plan["previous_five"],
    )
    if earlier["observation"]["engine"]["state"]!="running":
        raise LegacyProcessRestartError("old process snapshot was not running")
    parent=_safe_parent(active.parent)
    rename=_intent_data(plan,wal,active,parent)
    _read_intent(root,rename)
    retired=active.with_name(rename["retired_name"])
    other=active.with_name(rename["ready_name"])
    saved_info=config_record(plan,wal,held(),original)
    _read_intent_config(root,saved_info)
    stage=marker.with_name(
        "."+marker.name+".voice-legacy-"+wal["restore_plan_sha256"][:20]
    )
    mp=_safe_parent(marker.parent)
    marker_record={
        "schema":1,"phase":"marker-restoring-three-processes-not-started",
        "restore_plan_sha256":wal["restore_plan_sha256"],
        "previous_marker_sha256":plan["marker"]["sha256"],
        "previous_marker_bytes":plan["marker"]["bytes"],
        "previous_marker_mode":plan["marker"]["mode"],
        "marker_path":str(marker),"stage_name":stage.name,
        "parent_dev":mp.st_dev,"parent_ino":mp.st_ino,
        "config_dev":saved_info["device"],"config_ino":saved_info["inode"],
        "safe_to_start":False,"safe_to_enable_voice":False,
        "whole_rollback_complete":False,
    }
    _read_intent_marker(root,marker_record)
    old_marker=_read_private_file(root/NAME/"marker.bin",64)
    intent={
        "schema":SCHEMA,
        "phase":"legacy-three-role-restart-attempt-needs-independent-check",
        "restore_plan_sha256":wal["restore_plan_sha256"],
        "process_security_policy_sha256":policy["policy_sha256"],
        "previous_five":plan["previous_five"],
        "marker_sha256":plan["marker"]["sha256"],
        "actuator":str(SCRIPT),
        "safe_to_retry_start":False,"safe_to_enable_voice":False,
        "whole_rollback_complete":False,
    }

    def gate():
        held()
        if _ledger_clear(ledger_root) not in (
            "no-native-ledger","empty-private-ledger"
        ):
            raise LegacyProcessRestartError("native kernel ledger has owner")
        if _strict_snapshot(readonly_ipfw)!=_expected_after(
            plan,len(plan["legacy_ipfw_commands"])
        ):
            raise LegacyProcessRestartError("old IPFW kernel is no longer restored")
        n,pending=_steps(root/REPLAY_NAME,plan)
        if pending or n!=len(plan["legacy_ipfw_commands"]):
            raise LegacyProcessRestartError("old IPFW replay incomplete")
        if (_sha_fd(config_fd)!=(
            plan["previous_five"]["config"],original["config"]["bytes"]
        ) or
            (os.fstat(config_fd).st_mode & 0o777)!=original["config"]["mode"]):
            raise LegacyProcessRestartError("old Config changed after same-inode restore")
        if other.exists() or other.is_symlink() or (
            _fingerprint(image/"config.xml",active,source,
                         must_match_previous_modes=True)!=
            plan["previous_five"]["runtime"]
        ) or (
            _fingerprint(image/"config.xml",retired,source,
                         must_match_previous_modes=False)!=
            wal["candidate_runtime_sha256"]
        ):
            raise LegacyProcessRestartError("old runtime or retired candidate drift")
        if (parent.st_dev,parent.st_ino)!=(
            _safe_parent(active.parent).st_dev,
            _safe_parent(active.parent).st_ino
        ):
            raise LegacyProcessRestartError("active runtime parent inode changed")
        if stage.exists() or stage.is_symlink():
            raise LegacyProcessRestartError("old marker hardlink stage still present")
        _marker_stat(marker,old_marker,plan["marker"]["mode"],links=1)
        if inspect_legacy_reverse_wal(
            root,allow_ipfw_replay=True,allow_files_stage=FILES_NAME,
            allow_runtime_restore=True,allow_config_restore=True,
            allow_marker_restore=True,allow_process_restart=resumed,
        )!=wal or inspect_legacy_files_ready(
            root,allow_runtime_restore=True,allow_config_restore=True,
            allow_marker_restore=True,allow_process_restart=resumed,
        )!=ready:
            raise LegacyProcessRestartError("old rollback evidence changed")
        _read_intent(root,rename)
        _read_intent_config(root,saved_info)
        _read_intent_marker(root,marker_record)
        if resumed and _read_record(root/PROCESS_NAME,"intent")!=intent:
            raise LegacyProcessRestartError("old process restart intent altered")

    def attest():
        if (security_reader.kernel_images!=policy["policy"]["images"] or
            security_reader.credentials!=policy["policy"]["credentials"] or
            argv_reader.expected_paths!=EXPECTED_SCRIPTS):
            raise LegacyProcessRestartError("native kernel witness policy changed")
        # Two independent FreeBSD readers share the EXACT process probe.
        first=_normalize(
            process_probe.probe(),EXPECTED_SCRIPTS,
            _runtime_args_digest(original),
        )
        if first["engine"]["state"]!="running" or (
            first["supervisor"]["state"]!="running"
        ):
            raise LegacyProcessRestartError("not all three roles running after restart")
        security=security_reader.inspect_twice()
        if not verify_current_security(security,policy):
            raise LegacyProcessRestartError("old process image/UID/GID mismatch")
        argv=inspect_restarted_argv(
            source,root/NAME/"process-evidence",EXPECTED_SCRIPTS,
            policy["policy"]["supervisor_argv"],argv_reader,
        )
        if (argv["state"]!="review-required" or
            argv["reason"]!="new-process-argv-matches-sealed-launcher-plan"):
            raise LegacyProcessRestartError("old process kernel argv mismatch")
        instances=argv["instances"]
        for role in ROLES:
            row=first["engine"]["process"] if role=="engine" else first["supervisor"][role]
            expected={"pid":row["pid"],"start_ns":row["start_ns"]}
            if (instances[role]!=expected or
                {k:security["roles"][role][k] for k in ("pid","start_ns")}!=expected):
                raise LegacyProcessRestartError("PID/start epochs differ across witnesses")
        gate()
        if _normalize(
            process_probe.probe(),EXPECTED_SCRIPTS,
            _runtime_args_digest(original),
        )!=first or security_reader.inspect_twice()!=security or (
            inspect_restarted_argv(
                source,root/NAME/"process-evidence",EXPECTED_SCRIPTS,
                policy["policy"]["supervisor_argv"],argv_reader,
            )["instances"]!=instances
        ):
            raise LegacyProcessRestartError("restarted process identity unstable")
        return {
            "schema":SCHEMA, "phase":"three-roles-observed-not-accepted",
            "intent_sha256":_digest(_canonical(intent)),
            "process_security_policy_sha256":policy["policy_sha256"],
            "engine_argv_sha256":argv["engine_argv_sha256"],
            "instances":instances,
            "safe_to_enable_voice":False,
            "whole_rollback_complete":False,
        }

    gate()
    if not resumed:
        if _stopped(process_probe)!="exact-three-role-absence":
            raise LegacyProcessRestartError("old three-role set not fully stopped")
        # Explicitly require no stale original pidfiles via the existing probe.
        _normalize(process_probe.probe(),EXPECTED_SCRIPTS,_runtime_args_digest(original))
        _secure_script(Path(actuator))
        os.mkdir(root/PROCESS_NAME,0o700)
        _sync_dir(root)
        _write_record(root/PROCESS_NAME,"intent",intent)
        resumed=True
        gate()
        result=(runner or subprocess.run)(
            [SHELL,str(actuator),"start"],
            check=False,capture_output=True,text=True,timeout=45,
            pass_fds=(9,),
            env={"LC_ALL":"C",
                 "PATH":"/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin"},
        )
        if (result.returncode!=0 or
            len(result.stdout.encode("utf-8"))>8192 or
            len(result.stderr.encode("utf-8"))>8192):
            raise LegacyProcessRestartError("fixed one-engine process actuator failed")
        # Never auto-repeat this command, even if only one role came up.
    directory=root/PROCESS_NAME
    _private_dir(directory)
    entries=set(os.listdir(directory))
    if entries not in (START_FILES,FINAL_FILES):
        raise LegacyProcessRestartError("foreign or incomplete process restart record")
    report=attest()
    if entries==START_FILES:
        _write_record(directory,"verified",report)
    elif _read_record(directory,"verified")!=report:
        raise LegacyProcessRestartError("old process epochs changed after restart receipt")
    gate()
    if _read_record(directory,"verified")!=report:
        raise LegacyProcessRestartError("old restart proof altered")
    return {
        "state":"legacy-three-roles-restarted-needs-whole-owner-acceptance",
        "instances":report["instances"],
        "process_security_policy_sha256":report["process_security_policy_sha256"],
        "kernel_argv_sha256":report["engine_argv_sha256"],
        "safe_to_enable_voice":False,"whole_rollback_complete":False,
        "public_voice_apply":False, "boot_recovery_validated":False,
        "media_pass":False,
    }
