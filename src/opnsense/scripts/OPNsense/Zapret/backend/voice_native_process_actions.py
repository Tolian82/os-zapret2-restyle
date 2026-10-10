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
from voice_native_file_observer import observe_live_files
from voice_cutover_journal import VoiceCutoverJournal
from voice_process_recovery_evidence import _normalize, _runtime_args_digest
from voice_cutover_backup import inspect_previous


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
                 runner=None, actuator: Path = SCRIPT):
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
        if action not in ("start", "stop"):
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

    def stop_candidate(self) -> str:
        initial = self._gate()
        before = self._sample()
        if before["engine"]["state"] == "stopped":
            return "already-stopped"
        if before["engine"]["state"] != "running" or \
           before["supervisor"]["state"] != "running":
            raise NativeVoiceProcessActionError("ambiguous candidate process ownership")
        self._run("stop", initial)
        after = self._sample()
        if after["engine"]["state"] != "stopped" or \
           after["supervisor"]["state"] != "stopped":
            raise NativeVoiceProcessActionError(
                "native candidate/supervisor still running after stop"
            )
        return "stopped"

    def start_previous(self) -> str:
        initial = self._gate()
        previous = bound_resource_fingerprints(
            self.previous_backup, initial["previous"]
        )
        if observe_live_files(
            self.config_path, self.active_runtime,
            previous_backup=self.previous_backup,
        ) != previous:
            raise NativeVoiceProcessActionError(
                "previous Config and runtime must be live before process restart"
            )
        before = self._sample()
        if before["engine"]["state"] != "stopped" or \
           before["supervisor"]["state"] != "stopped":
            raise NativeVoiceProcessActionError(
                "one-engine/supervisor not fully stopped before restart"
            )
        self._run("start", initial)
        after = self._sample()
        if after["engine"]["state"] != "running" or \
           after["supervisor"]["state"] != "running":
            raise NativeVoiceProcessActionError(
                "previous one-engine/supervisor failed to restart"
            )
        if observe_live_files(
            self.config_path, self.active_runtime,
            previous_backup=self.previous_backup,
        ) != previous:
            raise NativeVoiceProcessActionError(
                "previous Config/runtime changed during restart"
            )
        return "running"
