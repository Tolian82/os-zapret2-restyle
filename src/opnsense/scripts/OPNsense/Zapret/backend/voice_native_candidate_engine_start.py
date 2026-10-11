#!/usr/bin/env python3
"""Native Voice forward Apply: start ONLY candidate dvtws2, not supervisor.

PRIVATE composable segment after the old-three-role stop and candidate
runtime filesystem switch. Requires durable schema-4 MUTATING journal,
forward runtime redo, retained exact old runtime, unchanged original Config,
unchanged previously-owned kernel IPFW and fixed original FD9/Config flock.
The sole mutation is a fixed /bin/sh native actuator command that launches
one candidate dvtws2 using the already-installed dvtws.args. No supervisor,
Config save, IPFW ownership transition, commit or Voice ON occurs here.

After launch, require stable native ps PID/start, exact kernel NUL argv AND
kernel executable path on two complete reads; old IPFW and whole journal
must remain unchanged. On failure retain durable MUTATING recovery state.
No public CLI/configd/GUI call is exposed before full forward rollback exists.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA
from voice_firewall_ledger import VoiceOwnershipStore, fingerprint, canonical_manifest
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_native_ipfw_ownership import observe_owned_ipfw
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import _locked_config, EXPECTED_SCRIPTS, PIDFILES
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS
from voice_native_file_observer import observe_live_files
from voice_native_live_preflight import _current_engine_args
from voice_native_forward_runtime import _read_redo
from voice_native_process_actions import _secure_script, SHELL, SCRIPT, MAX_OUTPUT


class CandidateEngineError(RuntimeError):
    pass


def start_forward_candidate_engine(
    *,journal,ledger,previous_backup,active_runtime,staged_config,
    candidate_runtime,config_path,probe,kernel_reader,read_ipfw_adapter,
    config_fd,config_owner,require_lifecycle_owner,runner=None,
    actuator=SCRIPT,
):
    """Real engine-only process start, gated by the exact forward runtime redo."""
    if not isinstance(journal,VoiceCutoverJournal) or (
        not isinstance(ledger,VoiceOwnershipStore)
        or not isinstance(probe,FreeBSDVoiceProcessProbe)
        or probe.expected!=EXPECTED_SCRIPTS or probe.pidfiles!=PIDFILES
        or Path(probe.previous_backup)!=Path(previous_backup)
        or not isinstance(kernel_reader,FreeBSDKernelArgvReader)
        or not isinstance(read_ipfw_adapter,FreeBSDIPFWAdapter)
        or read_ipfw_adapter.allow_mutations is not False
        or read_ipfw_adapter.rule_base!=19000
        or read_ipfw_adapter.rule_max!=19010
        or not callable(require_lifecycle_owner)
        or type(config_fd) is not int or config_fd<0
    ):
        raise CandidateEngineError("untrusted forward candidate engine authorities")
    if runner is None and Path(actuator)!=SCRIPT:
        raise CandidateEngineError("production candidate actuator path is immutable")
    exec_runner=subprocess.run if runner is None else runner
    if not callable(exec_runner):
        raise CandidateEngineError("invalid native process runner")
    previous_backup,active_runtime,config_path=map(
        Path,(previous_backup,active_runtime,config_path)
    )
    staged_config,candidate_runtime=map(Path,(staged_config,candidate_runtime))
    script=Path(actuator)

    def gate():
        require_lifecycle_owner()
        _locked_config(config_path,config_fd,config_owner)
        _pinned_regular(config_path,config_fd,owner=config_owner)

    def proof():
        gate()
        record=journal.read()
        if record is None or record["schema"]!=RUNTIME_BOUND_SCHEMA or (
            record["phase"]!="mutating"
        ):
            raise CandidateEngineError("missing schema-4 MUTATING forward Voice cutover")
        original=bound_resource_fingerprints(previous_backup,record["previous"])
        current=observe_live_files(config_path,active_runtime)
        candidate=observe_live_files(staged_config,candidate_runtime)
        if current!={"config":original["config"],
                     "runtime":record["candidate"]["candidate_runtime_sha256"]} or (
            candidate["runtime"]!=current["runtime"]
            or candidate["config"]!=record["candidate"]["saved_xml_sha256"]
        ):
            raise CandidateEngineError("active or staged candidate runtime differs")
        retained=active_runtime.with_name(
            ".voice-forward-previous-"+record["check"][:20]
        )
        if not retained.is_dir() or retained.is_symlink() or (
            observe_live_files(staged_config,retained)["runtime"]!=original["runtime"]
        ):
            raise CandidateEngineError("previous runtime is missing or modified")
        redo=_read_redo(journal.directory)
        if redo is None or any((
            redo["whole_check"]!=record["check"],
            redo["candidate_sha256"]!=current["runtime"],
            redo["previous_sha256"]!=original["runtime"],
            redo["retained_name"]!=retained.name,
            redo["active_name"]!=active_runtime.name,
        )):
            raise CandidateEngineError("missing or foreign durable forward runtime redo")
        if os.path.lexists(active_runtime.with_name(redo["ready_name"])):
            raise CandidateEngineError("forward runtime ready stage not consumed")
        cfg=os.fstat(config_fd)
        par=os.lstat(active_runtime.parent)
        if (redo["config_dev"],redo["config_inode"])!=(cfg.st_dev,cfg.st_ino) or (
            redo["parent_dev"],redo["parent_inode"]
        )!=(par.st_dev,par.st_ino):
            raise CandidateEngineError("Config or runtime parent changed since swap")
        old_owner=ledger.owned()
        if old_owner is None or ledger.pending() is not None or (
            fingerprint(canonical_manifest(old_owner))!=record["previous"]["firewall"]
            or observe_owned_ipfw(ledger,read_ipfw_adapter)!=record["previous"]["firewall"]
        ):
            raise CandidateEngineError("original native IPFW owner changed")
        expected,args_sha,_,_=_current_engine_args(active_runtime)
        return record,expected,args_sha

    original,expected,arg_sha=proof()
    empty=probe.observe_candidate_engine_only()
    if empty!={"state":"stopped","pid":None,"start_ns":None} or (
        probe.observe_candidate_engine_only()!=empty
    ):
        raise CandidateEngineError("previous Voice process or supervisor is still present")
    if proof()!=(original,expected,arg_sha):
        raise CandidateEngineError("forward candidate evidence changed before engine start")
    gate()
    _secure_script(script)
    # Only fixed native action; Config fd MUST NOT be inherited. FD9 remains
    # owned by the calling coordinator for the entire transaction.
    argv=[SHELL,str(script),"start-candidate-engine"]
    result=exec_runner(
        argv,check=False,capture_output=True,text=True,timeout=45,
        pass_fds=(9,),
        env={"LC_ALL":"C","PATH":"/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin"},
    )
    if result.returncode!=0 or (
        not isinstance(result.stdout,str) or not isinstance(result.stderr,str)
        or len(result.stdout.encode("utf-8"))>MAX_OUTPUT
        or len(result.stderr.encode("utf-8"))>MAX_OUTPUT
    ):
        raise CandidateEngineError("candidate dvtws2 native launcher failed")
    initial=None
    for _ in range(2):
        gate()
        observed=probe.observe_candidate_engine_only()
        if observed["state"]!="engine-only" or (
            type(observed["pid"]) is not int or observed["pid"]<=1
            or type(observed["start_ns"]) is not int or observed["start_ns"]<=0
        ):
            raise CandidateEngineError("candidate engine did not become sole managed process")
        if initial is None:
            initial=observed
        elif observed!=initial:
            raise CandidateEngineError("candidate engine PID/start changed during audit")
        if kernel_reader.argv(observed["pid"])!=expected or (
            kernel_reader.binary(observed["pid"])!=SYSTEM_PATHS["engine"]
        ):
            raise CandidateEngineError("candidate kernel argv or executable mismatch")
        if proof()!=(original,expected,arg_sha):
            raise CandidateEngineError("Config/runtime/IPFW/whole intent changed after launch")
    return {
        "state":"candidate-engine-kernel-verified-supervisor-not-started",
        "engine_pid":initial["pid"],
        "engine_start_ns":initial["start_ns"],
        "phase":"mutating",
        "old_ipfw_unchanged":True,
        "previous_runtime_retained":True,
        "supervisor_started":False,
        "can_commit":False,
        "voice_on":False,
        "media_pass":False,
    }
