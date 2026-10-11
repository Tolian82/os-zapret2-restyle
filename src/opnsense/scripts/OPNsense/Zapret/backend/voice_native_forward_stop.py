#!/usr/bin/env python3
"""Native forward Voice Apply: verified previous stop -> candidate runtime swap.

Real forward coordinator segment, NOT a public GUI/configd/service command.
Under one already-held FD9 lifecycle lease and original Config flock, re-open
the immutable five-resource previous evidence, confirm the still-running
engine/supervisor PIDs AND their exact FreeBSD kernel argv/executable images,
and match old Config/runtime + owned kernel IPFW. Then durably transition
the schema-4 prepared whole-intent to MUTATING BEFORE first process change,
stop the old single engine/supervisor via the previously bounded native shell
actuator, independently confirm all three roles stopped, and call the real
crash-resumable forward runtime installer.

The IPFW/Config/supervisor new-start stages and full automatic rollback are
NOT wired. Any error after the mutating journal transition leaves a durable
blocked manual-recovery state; it must never restart the old service from an
unverified state. Production use is forbidden pending full five-resource
executor plus actual FreeBSD/on-appliance qualification.
"""
from __future__ import annotations

from pathlib import Path

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import (
    VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA, BOUND_FIELD,
)
from voice_firewall_ledger import (
    VoiceOwnershipStore, canonical_manifest, fingerprint,
)
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_process_actions import FreeBSDVoiceProcessActions
from voice_native_kernel_argv import (
    FreeBSDKernelArgvReader, SYSTEM_PATHS, _live_instances, ROLE_NAMES,
)
from voice_native_recovery_quiescence import (
    _locked_config, EXPECTED_SCRIPTS, PIDFILES,
)
from voice_native_file_observer import observe_live_files
from voice_native_forward_runtime import install_forward_runtime
from voice_process_recovery_evidence import (
    inspect_process_evidence, _normalize, _runtime_args_digest,
)
from voice_cutover_backup import inspect_previous
from voice_restart_argv_attestation import expected_engine_argv
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_security_policy_evidence import (
    inspect_security_policy, SUPERVISOR_BOUND_POLICY_SCHEMA,
)


class ForwardStopError(RuntimeError):
    pass


def stop_previous_and_install_forward_runtime(
    *,journal,ledger,previous_backup,process_evidence,security_evidence,
    active_runtime,config_path,staged_config,candidate_runtime,
    probe,actions,kernel_reader,ipfw_adapter,config_fd,config_owner,
    require_lifecycle_owner,
):
    """Actually stop previous process roles then install candidate runtime.

    No arbitrary subprocess shell command/path injected by this coordinator.
    All process mutation is delegated to FreeBSDVoiceProcessActions.stop_candidate,
    whose underlying shell actuator must be separately integrity-pinned.
    """
    from voice_native_process_probe import FreeBSDVoiceProcessProbe

    if not isinstance(journal,VoiceCutoverJournal) or (
        not isinstance(ledger,VoiceOwnershipStore)
        or not isinstance(probe,FreeBSDVoiceProcessProbe)
        or probe.expected!=EXPECTED_SCRIPTS or probe.pidfiles!=PIDFILES
        or Path(probe.previous_backup)!=Path(previous_backup)
        or not isinstance(actions,FreeBSDVoiceProcessActions)
        or actions.probe is not probe or actions.journal is not journal
        or actions.previous_backup!=Path(previous_backup)
        or actions.config_path!=Path(config_path)
        or actions.active_runtime!=Path(active_runtime)
        or actions.config_fd!=config_fd or actions.owner!=config_owner
        or not isinstance(kernel_reader,FreeBSDKernelArgvReader)
        or not isinstance(ipfw_adapter,FreeBSDIPFWAdapter)
        or ipfw_adapter.allow_mutations is not False
        or ipfw_adapter.rule_base!=19000 or ipfw_adapter.rule_max!=19010
        or not callable(require_lifecycle_owner)
    ):
        raise ForwardStopError("untrusted native forward process and firewall owners")
    config_path,active_runtime=Path(config_path),Path(active_runtime)
    previous_backup=Path(previous_backup)
    staged_config,candidate_runtime=Path(staged_config),Path(candidate_runtime)

    def owner():
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        _pinned_regular(config_path,config_fd,owner=config_owner)

    owner()
    record=journal.read()
    if record is None or record["schema"]!=RUNTIME_BOUND_SCHEMA or (
        record["phase"]!="prepared"
    ):
        raise ForwardStopError("native forward requires existing PREPARED schema-4 intent")
    prior=bound_resource_fingerprints(previous_backup,record["previous"])
    if observe_live_files(
        config_path,active_runtime,previous_backup=previous_backup,
    )!=prior:
        raise ForwardStopError("old Config/runtime not unchanged after PREPARED")
    saved=inspect_previous(previous_backup)
    sealed=inspect_process_evidence(
        process_evidence,previous_backup,EXPECTED_SCRIPTS,record["previous"],
    )
    policy=inspect_security_policy(
        security_evidence,previous_backup,process_evidence,
        journal_record=record,expected_scripts=EXPECTED_SCRIPTS,
    )
    if policy["schema"]!=SUPERVISOR_BOUND_POLICY_SCHEMA or (
        policy["policy"]["supervisor_argv"]!=canonical_supervisor_argv(
            EXPECTED_SCRIPTS
        )
    ):
        raise ForwardStopError("sealable previous supervisor launch plan required")
    old_ipfw=ledger.owned()
    if old_ipfw is None or ledger.pending() is not None or (
        fingerprint(canonical_manifest(old_ipfw))!=record["previous"]["firewall"]
        or observe_owned_ipfw(ledger,ipfw_adapter)!=record["previous"]["firewall"]
    ):
        raise ForwardStopError("previous kernel IPFW ownership changed")
    candidate=observe_live_files(staged_config,candidate_runtime)
    if candidate["runtime"]!=record["candidate"]["candidate_runtime_sha256"] or (
        candidate["config"]!=record["candidate"]["saved_xml_sha256"]
    ):
        raise ForwardStopError("candidate Config/runtime drifted after PREPARED")

    saved_observation=sealed["observation"]
    expected={
        "engine":expected_engine_argv(previous_backup,EXPECTED_SCRIPTS["engine"]),
        **canonical_supervisor_argv(EXPECTED_SCRIPTS),
    }
    args_sha=_runtime_args_digest(saved)
    before=None
    for _ in range(2):
        owner()
        probe_row=probe.probe()
        normalized=_normalize(probe_row,EXPECTED_SCRIPTS,args_sha)
        if normalized!=saved_observation:
            raise ForwardStopError("previous Voice PID/start epoch no longer sealed")
        running=_live_instances(probe_row)
        if before is None:
            before=running
        elif running!=before:
            raise ForwardStopError("previous Voice PID or process epoch changed")
        for role in ROLE_NAMES:
            pid=running[role]["pid"]
            if kernel_reader.argv(pid)!=expected[role] or (
                kernel_reader.binary(pid)!=SYSTEM_PATHS[role]
            ):
                raise ForwardStopError("foreign native kernel argv/executable")
    owner()
    if journal.read()!=record or ledger.owned()!=old_ipfw or (
        ledger.pending() is not None
        or observe_owned_ipfw(ledger,ipfw_adapter)!=record["previous"]["firewall"]
        or observe_live_files(
            config_path,active_runtime,previous_backup=previous_backup,
        )!=prior
        or observe_live_files(staged_config,candidate_runtime)!=candidate
    ):
        raise ForwardStopError("previous or candidate state changed before stop")

    # The only irreversible pre-stop action: fsync the whole MUTATING journal.
    # Any subsequent failure keeps that record for explicit recovery.
    journal.mark_mutating()
    owner()
    mutating=journal.read()
    if mutating is None or mutating["phase"]!="mutating" or (
        mutating["previous"]!=record["previous"] or
        mutating["candidate"]!=record["candidate"]
    ):
        raise ForwardStopError("mutating Voice journal not durably confirmed")

    result=actions.stop_candidate()
    if result!="stopped":
        raise ForwardStopError("old Voice service was not stopped by native actuator")
    owner()
    stopped=actions._sample()
    if stopped["engine"]["state"]!="stopped" or (
        stopped["supervisor"]["state"]!="stopped"
    ):
        raise ForwardStopError("old Voice process roles still present")

    def all_stopped():
        owner()
        state=actions._sample()
        return state["engine"]["state"]=="stopped" and (
            state["supervisor"]["state"]=="stopped"
        )

    if observe_owned_ipfw(ledger,ipfw_adapter)!=record["previous"]["firewall"]:
        raise ForwardStopError("IPFW changed while stopping old engine")
    installed=install_forward_runtime(
        active_runtime=active_runtime,staged_config=staged_config,
        candidate_runtime=candidate_runtime,previous_backup=previous_backup,
        journal=journal,config_path=config_path,locked_config_fd=config_fd,
        config_owner=config_owner,require_lifecycle_owner=require_lifecycle_owner,
        require_all_processes_stopped=all_stopped,
    )
    owner()
    if installed["state"]!="native-voice-forward-runtime-installed" or (
        journal.read()!=mutating
        or observe_owned_ipfw(ledger,ipfw_adapter)!=record["previous"]["firewall"]
        or all_stopped() is not True
    ):
        raise ForwardStopError("forward runtime stop/install not safely sealed")
    return {
        "state":"native-forward-previous-stopped-runtime-installed",
        "phase":"mutating",
        "whole_check":mutating["check"],
        "previous_processes_stopped":True,
        "old_kernel_ipfw_unchanged":True,
        "previous_runtime_preserved":True,
        "can_activate":False,
        "voice_on":False,
    }
