#!/usr/bin/env python3
"""Private native Voice stage after IPFW PRECOMMIT: start and prove supervisor.

Only the future five-resource coordinator holding ORIGINAL FD9+Config flock
may invoke this. No GUI/configd/CLI/boot routing, no automatic recovery and
no whole COMMIT/Voice ON. Ambiguous errors preserve both durable journals.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess

from voice_cutover_backup import bound_resource_fingerprints
from voice_cutover_config_restore import _pinned_regular
from voice_cutover_journal import VoiceCutoverJournal, RUNTIME_BOUND_SCHEMA, BOUND_FIELD
from voice_firewall_ledger import VoiceOwnershipStore, canonical_manifest, fingerprint
from voice_firewall_transaction import plan_postcommit_cleanup
from voice_ipfw_adapter import FreeBSDIPFWAdapter
from voice_ipfw_runtime import require_no_legacy
from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_kernel_argv import FreeBSDKernelArgvReader, SYSTEM_PATHS, _live_instances
from voice_native_supervisor_launch import canonical_supervisor_argv
from voice_native_process_actions import _secure_script, SHELL, SCRIPT, MAX_OUTPUT
from voice_native_live_preflight import _current_engine_args
from voice_native_file_observer import observe_live_files
from voice_native_forward_runtime import _read_redo
from voice_native_recovery_quiescence import EXPECTED_SCRIPTS, PIDFILES, _locked_config


class ForwardSupervisorError(RuntimeError):
    pass


def start_forward_voice_supervisor(
    *, journal, ledger, previous_backup, active_runtime, staged_config,
    candidate_runtime, config_path, desired_manifest, probe, kernel_reader,
    readonly_adapter, config_fd, config_owner, require_lifecycle_owner,
    runner=None, actuator=SCRIPT,
):
    """Fixed supervisor-only actuator, independently attested before and after."""
    if not isinstance(journal, VoiceCutoverJournal) or (
        not isinstance(ledger, VoiceOwnershipStore)
        or not isinstance(probe, FreeBSDVoiceProcessProbe)
        or probe.expected != EXPECTED_SCRIPTS or probe.pidfiles != PIDFILES
        or Path(probe.previous_backup) != Path(previous_backup)
        or not isinstance(kernel_reader, FreeBSDKernelArgvReader)
        or not isinstance(readonly_adapter, FreeBSDIPFWAdapter)
        or readonly_adapter.allow_mutations is not False
        or readonly_adapter.rule_base != 19000 or readonly_adapter.rule_max != 19010
        or not callable(require_lifecycle_owner)
        or type(config_fd) is not int or config_fd < 0
        or (runner is None and Path(actuator) != SCRIPT)
    ):
        raise ForwardSupervisorError("untrusted forward supervisor owner")
    execute = subprocess.run if runner is None else runner
    if not callable(execute):
        raise ForwardSupervisorError("untrusted actuator runner")
    previous_backup, active_runtime, config_path = map(
        Path, (previous_backup, active_runtime, config_path)
    )
    staged_config, candidate_runtime = map(Path, (staged_config, candidate_runtime))
    desired = canonical_manifest(desired_manifest)
    desired_sha = fingerprint(desired)
    if not desired_manifest["rules"] or not desired_manifest["tables"]:
        raise ForwardSupervisorError("empty Voice IPFW manifest")
    ports = {rule[1] for rule in desired_manifest["rules"].values()}
    if len(ports) != 1:
        raise ForwardSupervisorError("inconsistent desired divert port")

    def owner():
        require_lifecycle_owner()
        _locked_config(config_path, config_fd, config_owner)
        _pinned_regular(config_path, config_fd, owner=config_owner)

    def sealed():
        owner()
        record = journal.read()
        if record is None or record["schema"] != RUNTIME_BOUND_SCHEMA or (
            record["phase"] != "mutating"
            or record["candidate"][BOUND_FIELD] != desired_sha
        ):
            raise ForwardSupervisorError("missing whole schema-4 MUTATING intent")
        old = bound_resource_fingerprints(previous_backup, record["previous"])
        current = observe_live_files(config_path, active_runtime)
        staged = observe_live_files(staged_config, candidate_runtime)
        if current != {
            "config": old["config"],
            "runtime": record["candidate"]["candidate_runtime_sha256"],
        } or staged != {
            "config": record["candidate"]["saved_xml_sha256"],
            "runtime": current["runtime"],
        }:
            raise ForwardSupervisorError("Config or candidate runtime drift")
        retained = active_runtime.with_name(
            ".voice-forward-previous-" + record["check"][:20]
        )
        if retained.is_symlink() or not retained.is_dir() or (
            observe_live_files(staged_config, retained)["runtime"] != old["runtime"]
        ):
            raise ForwardSupervisorError("retained old runtime not intact")
        redo = _read_redo(journal.directory)
        if redo is None or (
            redo["whole_check"] != record["check"]
            or redo["previous_sha256"] != old["runtime"]
            or redo["candidate_sha256"] != current["runtime"]
            or redo["retained_name"] != retained.name
            or redo["active_name"] != active_runtime.name
            or os.path.lexists(active_runtime.with_name(redo["ready_name"]))
        ):
            raise ForwardSupervisorError("forward runtime redo not intact")
        cfg, parent = os.fstat(config_fd), os.lstat(active_runtime.parent)
        if (cfg.st_dev, cfg.st_ino) != (
            redo["config_dev"], redo["config_inode"]
        ) or (parent.st_dev, parent.st_ino) != (
            redo["parent_dev"], redo["parent_inode"]
        ):
            raise ForwardSupervisorError("Config or runtime parent inode changed")
        argv, argv_sha, _, _ = _current_engine_args(active_runtime)
        if argv_sha != record["candidate"]["native_argv_sha256"] or (
            {part.split("=", 1)[1] for part in argv if part.startswith("--port=")}
            != ports
        ):
            raise ForwardSupervisorError("engine args/port mismatch desired IPFW")
        prior, pending = ledger.owned(), ledger.pending()
        if prior is None or pending is None or (
            fingerprint(canonical_manifest(prior)) != record["previous"]["firewall"]
            or pending["phase"] != "mutating"
            or pending["previous_sha256"] != record["previous"]["firewall"]
            or pending["desired_sha256"] != desired_sha
            or pending["previous"] != canonical_manifest(prior)
            or pending["desired"] != desired
        ):
            raise ForwardSupervisorError("separate IPFW PRECOMMIT is not intact")
        require_no_legacy(readonly_adapter)
        # Read-only exact kernel rule/table/stage verification; NO cleanup.
        plan_postcommit_cleanup(readonly_adapter, prior, desired_manifest)
        return record, pending, argv, argv_sha

    def engine(argv):
        owner()
        observed = probe.observe_candidate_engine_only()
        if observed["state"] != "engine-only" or (
            type(observed["pid"]) is not int or observed["pid"] <= 1
            or type(observed["start_ns"]) is not int or observed["start_ns"] <= 0
        ):
            raise ForwardSupervisorError("exactly one candidate engine required")
        if kernel_reader.argv(observed["pid"]) != argv or (
            kernel_reader.binary(observed["pid"]) != SYSTEM_PATHS["engine"]
        ):
            raise ForwardSupervisorError("candidate kernel argv/binary mismatch")
        return observed

    before = sealed()
    first_engine = engine(before[2])
    if engine(before[2]) != first_engine or sealed() != before:
        raise ForwardSupervisorError("engine or journals raced before supervisor")
    owner()
    _secure_script(Path(actuator))
    outcome = execute(
        [SHELL, str(actuator), "start-candidate-supervisor"],
        check=False, capture_output=True, text=True, timeout=45,
        pass_fds=(9,),
        env={"LC_ALL": "C", "PATH": "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin"},
    )
    if outcome.returncode != 0 or (
        not isinstance(outcome.stdout, str) or not isinstance(outcome.stderr, str)
        or len(outcome.stdout.encode("utf-8")) > MAX_OUTPUT
        or len(outcome.stderr.encode("utf-8")) > MAX_OUTPUT
    ):
        raise ForwardSupervisorError("native supervisor actuator failed")
    expected = {
        "engine": before[2],
        **canonical_supervisor_argv(EXPECTED_SCRIPTS),
    }
    instances_before = None
    for _ in range(2):
        if sealed() != before:
            raise ForwardSupervisorError("whole state changed after supervisor start")
        owner()
        instances = _live_instances(probe.observe_processes())
        if instances["engine"] != {
            "pid": first_engine["pid"], "start_ns": first_engine["start_ns"]
        }:
            raise ForwardSupervisorError("candidate engine replaced during supervisor launch")
        if instances_before is None:
            instances_before = instances
        elif instances != instances_before:
            raise ForwardSupervisorError("daemon/monitor PID epochs raced")
        for role in ("engine", "daemon", "monitor"):
            pid = instances[role]["pid"]
            if kernel_reader.argv(pid) != expected[role] or (
                kernel_reader.binary(pid) != SYSTEM_PATHS[role]
            ):
                raise ForwardSupervisorError("supervisor FreeBSD kernel argv/image differs")
    if sealed() != before:
        raise ForwardSupervisorError("IPFW/Config/whole intent changed at final witness")
    return {
        "state": "candidate-engine-ipfw-supervisor-kernel-verified",
        "phase": "mutating",
        "engine_pid": first_engine["pid"],
        "daemon_pid": instances_before["daemon"]["pid"],
        "monitor_pid": instances_before["monitor"]["pid"],
        "previous_ipfw_ownership_retained": True,
        "ipfw_precommit_retained": True,
        "previous_runtime_retained": True,
        "supervisor_started": True,
        "can_commit": False,
        "voice_on": False,
        "media_pass": False,
    }
