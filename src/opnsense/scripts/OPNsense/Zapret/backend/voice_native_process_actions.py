#!/usr/bin/env python3
"""Bounded FreeBSD adapter for the existing one-engine Voice launcher/supervisor.

NO CLI/GUI/boot caller. Operates only as the stop/start callback of the future
native five-resource rollback coordinator. The parent holds the same OPNsense
Config flock throughout and the existing Zapret lifecycle FD9. Neither a PID
nor arbitrary process command, path, environment or backend script may be
provided by an OPNsense user. Tests inject a fake shell subprocess runner.

Shell actuator only calls existing launcher_stop/launcher_start_once and
supervisor_stop/supervisor_start with fixed paths. The adapter samples the
global FreeBSD process table twice before and after and refuses stale/orphan
or duplicate engines. It does not authorize a whole intent commit.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess

from voice_native_process_probe import FreeBSDVoiceProcessProbe
from voice_native_recovery_quiescence import (
    EXPECTED_SCRIPTS, PIDFILES, _locked_config,
)
from voice_cutover_backup import bound_resource_fingerprints
from voice_native_file_observer import observe_live_files, LiveFileEvidenceError
from voice_cutover_journal import VoiceCutoverJournal
from voice_process_recovery_evidence import _normalize, _runtime_args_digest
from voice_cutover_backup import inspect_previous
from voice_cutover_journal import SECURITY_BOUND_SCHEMA, RUNTIME_BOUND_SCHEMA
from voice_security_policy_evidence import (inspect_security_policy,
    SUPERVISOR_BOUND_POLICY_SCHEMA)
from voice_native_restart_integrity import attest_previous_restart
from voice_native_kernel_argv import (
    FreeBSDKernelArgvReader, SYSTEM_PATHS, ROLE_NAMES, _live_instances,
)


SHELL = "/bin/sh"
SCRIPT = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend/voice_native_process_lifecycle.sh")
MAX_OUTPUT = 8192


class NativeVoiceProcessActionError(RuntimeError):
    pass


def _secure_script(path: Path) -> None:
    """Reject symlink/replaced/foreign-writable root-controlled shell code."""
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or \
       before.st_uid != os.geteuid() or before.st_mode & 0o022:
        raise NativeVoiceProcessActionError("untrusted installed process actuator")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        now = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size,
            before.st_mtime_ns, before.st_ctime_ns) != (
                now.st_dev, now.st_ino, now.st_size,
                now.st_mtime_ns, now.st_ctime_ns
        ):
            raise NativeVoiceProcessActionError("actuator changed during pinning")
    finally:
        os.close(fd)


class FreeBSDVoiceProcessActions:
    """Native stop/start callbacks, never a self-authorizing recovery entry."""

    def __init__(self, *, probe: FreeBSDVoiceProcessProbe,
                 journal: VoiceCutoverJournal, previous_backup: Path,
                 active_runtime: Path, config_path: Path, config_owner: tuple[int,int],
                 config_fd: int, require_lifecycle_owner,
                 runner=None, actuator: Path = SCRIPT,
                 process_evidence: Path | None = None,
                 security_evidence: Path | None = None,
                 security_reader=None, argv_reader=None):
        if not isinstance(probe, FreeBSDVoiceProcessProbe) or \
           probe.expected != EXPECTED_SCRIPTS or \
           probe.pidfiles != PIDFILES or \
           Path(probe.previous_backup) != Path(previous_backup) or \
           not isinstance(journal, VoiceCutoverJournal) or \
           not callable(require_lifecycle_owner) or \
           type(config_fd) is not int or config_fd < 0 or \
           type(config_owner) is not tuple or len(config_owner) != 2 or \
           any(type(x) is not int or x < 0 for x in config_owner):
            raise NativeVoiceProcessActionError("native probe, journal and locks required")
        if runner is None and Path(actuator) != SCRIPT:
            raise NativeVoiceProcessActionError("production actuator path is fixed")
        integrity_fields = (process_evidence, security_evidence,
                            security_reader, argv_reader)
        if any(field is not None for field in integrity_fields) and not all(
            field is not None for field in integrity_fields
        ):
            raise NativeVoiceProcessActionError(
                "incomplete native kernel image/credential/argv restart verifier"
            )
        # The actual FreeBSD runner MUST have schema-3 kernel integrity
        # verification. Only explicitly injected CI simulation can omit it.
        if runner is None and not all(field is not None for field in integrity_fields):
            raise NativeVoiceProcessActionError(
                "production restart requires bound native integrity witnesses"
            )
        self.probe = probe
        self.journal = journal
        self.previous_backup = Path(previous_backup)
        self.active_runtime = Path(active_runtime)
        self.config_path = Path(config_path)
        self.owner = config_owner
        self.config_fd = config_fd
        self.require_lock = require_lifecycle_owner
        self.runner = runner or subprocess.run
        self.script = Path(actuator)
        self.expected = dict(EXPECTED_SCRIPTS)
        self.process_evidence = (None if process_evidence is None
                                 else Path(process_evidence))
        self.security_evidence = (None if security_evidence is None
                                  else Path(security_evidence))
        self.security_reader = security_reader
        self.argv_reader = argv_reader

    def _gate(self) -> dict:
        self.require_lock()
        _locked_config(self.config_path, self.config_fd, self.owner)
        record = self.journal.read()
        if record is None or record.get("phase") != "mutating" or \
           record.get("schema", 0) < 2:
            raise NativeVoiceProcessActionError("missing bound mutating Voice intent")
        bound_resource_fingerprints(self.previous_backup, record["previous"])
        return record

    def _sample(self):
        saved = inspect_previous(self.previous_backup)
        args_sha = _runtime_args_digest(saved)
        result = _normalize(self.probe.probe(), self.expected, args_sha)
        if _normalize(self.probe.probe(), self.expected, args_sha) != result:
            raise NativeVoiceProcessActionError("unstable Voice native process identities")
        return result

    def _run(self, action: str, before_journal: dict):
        if action not in ("start", "stop", "stop-candidate-engine"):
            raise NativeVoiceProcessActionError("unknown private Voice actuator action")
        self._gate()
        _secure_script(self.script)
        # No shell=True, never accept a PID, config path or arbitrary command.
        # The fixed shell helper inherits FD9 only (never the Config fd).
        argv = [SHELL, str(self.script), action]
        result = self.runner(
            argv, check=False, capture_output=True, text=True,
            timeout=45 if action == "start" else 20,
            pass_fds=(9,),
            env={"LC_ALL":"C", "PATH":"/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin"},
        )
        if result.returncode != 0 or \
           len(result.stdout.encode("utf-8")) > MAX_OUTPUT or \
           len(result.stderr.encode("utf-8")) > MAX_OUTPUT:
            raise NativeVoiceProcessActionError(
                "native Voice process actuator failed or exceeded output limit"
            )
        if self._gate() != before_journal:
            raise NativeVoiceProcessActionError(
                "Voice journal changed during native process action"
            )

    def stop_candidate(self, *, expected_instances=None, kernel_reader=None,
                       expected_argv=None) -> str:
        """Pin ALL three PID/start epochs + actual FreeBSD kernel argv/image.

        Forward Apply and its same-FD failed-forward rollback supply the
        exact full topology observed before this action. The native actuator
        must independently resample it IMMEDIATELY before the fixed stop
        command. Legacy manual callers with no pinned proof keep their
        existing independent process-ownership checks; mixed/partial proof
        is never accepted.
        """
        pinned = expected_instances is not None or kernel_reader is not None or (
            expected_argv is not None
        )
        if pinned and (
            not isinstance(kernel_reader, FreeBSDKernelArgvReader)
            or not isinstance(expected_instances, dict)
            or set(expected_instances) != set(ROLE_NAMES)
            or not isinstance(expected_argv, dict)
            or set(expected_argv) != set(ROLE_NAMES)
        ):
            raise NativeVoiceProcessActionError(
                "incomplete candidate three-role stop proof"
            )
        initial = self._gate()
        before = self._sample()
        if before["engine"]["state"] == "stopped":
            if pinned:
                raise NativeVoiceProcessActionError(
                    "candidate stopped before pinned stop"
                )
            return "already-stopped"
        if before["engine"]["state"] != "running" or \
           before["supervisor"]["state"] != "running":
            raise NativeVoiceProcessActionError("ambiguous candidate process ownership")
        if pinned:
            running = _live_instances({
                "engine": before["engine"],
                "supervisor": before["supervisor"],
            })
            if running != expected_instances:
                raise NativeVoiceProcessActionError(
                    "candidate process PID/start changed before native stop"
                )
            for role in ROLE_NAMES:
                pid = running[role]["pid"]
                if kernel_reader.argv(pid) != expected_argv[role] or (
                    kernel_reader.binary(pid) != SYSTEM_PATHS[role]
                ):
                    raise NativeVoiceProcessActionError(
                        "candidate FreeBSD kernel argv/image changed before native stop"
                    )
            if self._gate() != initial or self._sample() != before:
                raise NativeVoiceProcessActionError(
                    "candidate process or Voice intent raced before stop"
                )
        self._run("stop", initial)
        after = self._sample()
        if after["engine"]["state"] != "stopped" or \
           after["supervisor"]["state"] != "stopped":
            raise NativeVoiceProcessActionError(
                "native candidate/supervisor still running after stop"
            )
        return "stopped"

    def stop_forward_engine_only(self, *, kernel_reader, expected_argv,
                                 expected_pid, expected_start_ns) -> str:
        """Stop exactly one fully attested forward dvtws2, no supervisor.

        Only the upper schema-4 MUTATING same-FD recovery coordinator can
        supply the candidate argv/epoch it just witnessed. A separate
        native ps snapshot and actual kernel image/argv are checked again
        here, before calling the fixed zero-PID actuator. The normal
        stop_candidate path remains unchanged for all-three-role state.
        """
        if not isinstance(kernel_reader, FreeBSDKernelArgvReader) or (
            not isinstance(expected_argv, (list, tuple))
            or not expected_argv
            or any(type(part) is not str or not part for part in expected_argv)
            or type(expected_pid) is not int or expected_pid <= 1
            or type(expected_start_ns) is not int or expected_start_ns <= 0
        ):
            raise NativeVoiceProcessActionError("untrusted engine-only stop identity")
        original = self._gate()
        if original["schema"] != RUNTIME_BOUND_SCHEMA:
            raise NativeVoiceProcessActionError("engine-only stop requires schema-4 intent")
        first = self.probe.observe_candidate_engine_only()
        second = self.probe.observe_candidate_engine_only()
        if first != second or first != {
            "state": "engine-only", "pid": expected_pid,
            "start_ns": expected_start_ns,
        }:
            raise NativeVoiceProcessActionError("candidate engine-only epoch changed")
        if kernel_reader.argv(expected_pid) != list(expected_argv) or (
            kernel_reader.binary(expected_pid) != SYSTEM_PATHS["engine"]
        ):
            raise NativeVoiceProcessActionError("foreign candidate engine kernel image")
        if self._gate() != original or (
            self.probe.observe_candidate_engine_only() != first
        ):
            raise NativeVoiceProcessActionError("candidate identity raced before stop")
        self._run("stop-candidate-engine", original)
        a = self.probe.observe_candidate_engine_only()
        b = self.probe.observe_candidate_engine_only()
        if a != {"state": "stopped", "pid": None, "start_ns": None} or b != a:
            raise NativeVoiceProcessActionError("candidate dvtws2 still running")
        if self._sample()["engine"]["state"] != "stopped":
            raise NativeVoiceProcessActionError("native full process table not stopped")
        return "stopped"

    def start_previous(self) -> str:
        initial = self._gate()
        previous = bound_resource_fingerprints(
            self.previous_backup, initial["previous"]
        )
        try:
            observed = observe_live_files(
                self.config_path, self.active_runtime,
                previous_backup=self.previous_backup,
            )
        except (LiveFileEvidenceError, OSError) as exc:
            raise NativeVoiceProcessActionError(
                "unsafe previous Config/runtime; refusing process restart"
            ) from exc
        if observed != previous:
            raise NativeVoiceProcessActionError(
                "previous Config and runtime must be live before process restart"
            )
        before = self._sample()
        if before["engine"]["state"] != "stopped" or \
           before["supervisor"]["state"] != "stopped":
            raise NativeVoiceProcessActionError(
                "one-engine/supervisor not fully stopped before restart"
            )
        if self.security_evidence is not None:
            # Inspect the SEALED previous policy BEFORE starting an engine,
            # so schema-2 or foreign policy cannot start any process.
            if initial["schema"] not in (SECURITY_BOUND_SCHEMA, RUNTIME_BOUND_SCHEMA):
                raise NativeVoiceProcessActionError(
                    "native restart needs durable schema-3 process policy"
                )
            trusted = inspect_security_policy(
                self.security_evidence, self.previous_backup,
                self.process_evidence, journal_record=initial,
                expected_scripts=self.expected,
            )
            if trusted["schema"] != SUPERVISOR_BOUND_POLICY_SCHEMA:
                raise NativeVoiceProcessActionError(
                    "previous security policy lacks sealed supervisor launch argv"
                )
        self._run("start", initial)
        after = self._sample()
        if after["engine"]["state"] != "running" or \
           after["supervisor"]["state"] != "running":
            raise NativeVoiceProcessActionError(
                "previous one-engine/supervisor failed to restart"
            )
        try:
            observed = observe_live_files(
                self.config_path, self.active_runtime,
                previous_backup=self.previous_backup,
            )
        except (LiveFileEvidenceError, OSError) as exc:
            raise NativeVoiceProcessActionError(
                "unsafe previous Config/runtime after native restart"
            ) from exc
        if observed != previous:
            raise NativeVoiceProcessActionError(
                "previous Config/runtime changed during restart"
            )
        if self.security_evidence is not None:
            report = attest_previous_restart(
                journal=self.journal, previous_backup=self.previous_backup,
                process_evidence=self.process_evidence,
                security_evidence=self.security_evidence,
                expected_scripts=self.expected,
                security_reader=self.security_reader,
                argv_reader=self.argv_reader,
                require_lifecycle_owner=self.require_lock,
                require_config_owner=lambda: _locked_config(
                    self.config_path, self.config_fd, self.owner,
                ),
            )
            if (
                report["state"] != "previous-restart-integrity-observed"
                or report["safe_to_enable_voice"] is not False
                or report["safe_to_finish_intent"] is not False
            ):
                raise NativeVoiceProcessActionError(
                    "native previous restart attestation did not match"
                )
        return "running"
