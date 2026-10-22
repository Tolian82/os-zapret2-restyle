#!/usr/local/bin/python3.13
"""Privileged Additional Resources worker entered only under setup.lock -> FD9.

Uses the existing native service's inherited FD9 Strategy Lab stop/start
callbacks. No independent Config writer, ipfw manager or service implementation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

from extra_resources_preflight import (
    PreflightError, obtain_revision, obtain_archive, unpack_verified_archive,
    verified_resources, inspect_collisions,
)
from extra_resources_transaction import (
    TransactionError, install, recover, _safe_state, _json_write,
)

SCRIPT = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
RUNTIME = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle/extra-resources")
CHILD_PID = Path("/var/run/dvtws2.pid")
MONITOR_PID = Path("/var/run/zapret2-supervisor-monitor.pid")


class NativeLifecycle:
    """Lifecycle already held by the original Zapret service under FD9."""

    def __init__(self, script: Path = SCRIPT, child: Path = CHILD_PID,
                 monitor: Path = MONITOR_PID):
        if os.environ.get("STRATEGY_LAB_LIFECYCLE_OWNER") != "1":
            raise TransactionError("missing original lifecycle lock owner")
        try:
            os.fstat(9)
        except OSError as exc:
            raise TransactionError("original lifecycle FD9 is not inherited") from exc
        if not script.is_file() or not os.access(script, os.X_OK):
            raise TransactionError("native service is unavailable")
        self.script = script
        self.child = child
        self.monitor = monitor

    def _invoke(self, operation: str) -> int:
        result = subprocess.run([str(self.script), operation], pass_fds=(9,),
                                capture_output=True, text=True, timeout=180,
                                check=False)
        if result.returncode not in (0, 1):
            raise TransactionError(
                f"native service {operation} returned {result.returncode}: "
                f"{(result.stderr or result.stdout).strip()[:300]}"
            )
        if operation != "strategy-lab-status" and result.returncode != 0:
            raise TransactionError(f"native {operation} was rejected: {result.stderr[:300]}")
        return result.returncode

    @staticmethod
    def _pid(path: Path) -> int:
        if path.is_symlink() or not path.is_file():
            raise TransactionError(f"native PID file missing/unsafe: {path.name}")
        raw = path.read_text().strip()
        if not re.fullmatch(r"[1-9][0-9]{0,8}", raw):
            raise TransactionError(f"invalid native PID file: {path.name}")
        pid = int(raw)
        try:
            os.kill(pid, 0)
        except OSError as exc:
            raise TransactionError(f"native process absent: {path.name}") from exc
        return pid

    def assert_started(self) -> str:
        if self._invoke("strategy-lab-status") != 0:
            raise TransactionError("Zapret2 is not running; start it before installing resources")
        child = self._pid(self.child)
        monitor = self._pid(self.monitor)
        if child == monitor:
            raise TransactionError("native process census is inconsistent")
        return f"{child}:{monitor}"

    def assert_stopped(self) -> None:
        if self._invoke("strategy-lab-status") != 1:
            raise TransactionError("native Stop did not reach Stopped")

    def stop(self) -> None:
        self._invoke("strategy-lab-stop")

    def start(self) -> None:
        self._invoke("strategy-lab-start")


def _status(stage: str, **extra) -> None:
    _safe_state(STATE)
    _json_write(STATE / "status.json", {"schema": 1, "phase": stage, **extra})


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"install", "recover"}:
        print("usage: extra_resources_operation.py {install|recover}", file=sys.stderr)
        return 64
    mode = argv[1]
    try:
        lifecycle = NativeLifecycle()
        if mode == "recover":
            _status("recovering")
            status = recover(RUNTIME, STATE, lifecycle)
            _status(status.lower())
            print(status)
            return 0

        # Reject Stopped/unknown service before network access or state changes.
        lifecycle.assert_started()
        if (STATE / "transaction").exists() or (STATE / "transaction").is_symlink():
            raise TransactionError("RECOVERY_REQUIRED: unresolved resource transaction")
        _status("downloading")
        revision = obtain_revision()
        archive = obtain_archive(revision)
        _status("verifying", source_commit=revision)
        files = unpack_verified_archive(archive, revision)
        payloads, capabilities_count = verified_resources(files)
        inspect_collisions(payloads, RUNTIME, STATE / "installed.json")
        catalog = json.loads(files["inventory/capabilities.json"].decode("utf-8"))
        _status("installing", source_commit=revision)
        result = install(payloads, revision, RUNTIME, STATE, lifecycle, capabilities=catalog)
        _status("ready", **result, described_capabilities=capabilities_count)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (TransactionError, PreflightError, OSError, ValueError,
            TimeoutError, subprocess.TimeoutExpired) as exc:
        code = "RESTORE_FAILED" if "RESTORE_FAILED" in str(exc) else (
            "RECOVERY_REQUIRED" if "RECOVERY_REQUIRED" in str(exc) else "FAILED")
        try:
            _status(code.lower(), detail=str(exc)[:450])
        except Exception:
            pass
        print(f"EXTRA_RESOURCES_{code}: {exc}", file=sys.stderr)
        return 70 if code == "RESTORE_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
