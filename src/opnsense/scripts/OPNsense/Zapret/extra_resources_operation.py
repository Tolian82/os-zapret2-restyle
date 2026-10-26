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
    TransactionError, install, recover, remove_with_native_trial,
    _safe_state, _json_write,
)
from extra_resources_reconcile import make_plan, make_remove_plan
from extra_resources_inventory_cache import InventoryCacheError, refresh as refresh_inventory_cache

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

    def capture_previous_native_common_apply(self) -> dict:
        """Return only the attested, saved native common owner under FD9."""
        result = subprocess.run(
            [str(self.script), "extra-resources-native-previous-owner"],
            pass_fds=(9,), capture_output=True, text=True, timeout=180,
            check=False,
        )
        if result.returncode != 0:
            raise TransactionError("previous native common owner is not attested")
        match = re.fullmatch(
            r"native-owner=([a-f0-9]{32}):(strategies|voice):([a-f0-9]{64})\n?",
            result.stdout,
        )
        if match is None:
            raise TransactionError("malformed previous native common owner witness")
        return {"id": match[1], "page": match[2], "candidate": match[3]}

    def start_trial_native_common_apply(self) -> None:
        """Start the REAL freshly compiled unchanged Strategies+Voice Apply.

        The resource journal is already in 'restarting' after exact
        quarantine. The native service rechecks it and the old common owner
        under original inherited FD9 before any new engine/IPFW mutation.
        """
        environment = dict(os.environ)
        environment["EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL"] = "1"
        result = subprocess.run(
            [str(self.script), "extra-resources-native-trial"],
            env=environment, pass_fds=(9,),
            capture_output=True, text=True, timeout=300, check=False,
        )
        lines = result.stdout.strip().splitlines()
        if result.returncode != 0 or not lines or not re.fullmatch(
            r"native-remove-applied=[a-f0-9]{32}", lines[-1]
        ):
            raise TransactionError(
                "native common Remove trial not attested: " +
                (result.stderr or result.stdout).strip()[:300]
            )

    def recover_prepared_native_common_apply(self, owner: dict) -> bool:
        """Cold-complete ONLY a proven zero-mutation shared PREPARED trial.

        The original FD9 shell checks the pinned resource+common journals,
        original sealed Config and installed tree, no orphan processes and
        empty managed IPFW BEFORE calling existing recover-prepared.
        """
        from extra_resources_transaction import _validate_native_owner
        old = _validate_native_owner(owner)
        environment = dict(os.environ)
        environment["EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE"] = "1"
        result = subprocess.run(
            [str(self.script), "extra-resources-native-recover-prepared",
             old["id"], old["page"], old["candidate"]],
            env=environment, pass_fds=(9,), capture_output=True,
            text=True, timeout=180, check=False,
        )
        if result.returncode != 0:
            raise TransactionError("RESTORE_FAILED: prepared native trial not qualified")
        last = result.stdout.strip().splitlines()
        if not last:
            raise TransactionError("RESTORE_FAILED: missing prepared recovery receipt")
        if last[-1] == "native-remove-prepared=not-needed":
            return False
        if last[-1] == "native-remove-prepared-restored=" + old["id"]:
            return True
        raise TransactionError("RESTORE_FAILED: foreign prepared recovery receipt")

    def restore_previous_native_common_apply(self, owner: dict) -> None:
        """Return to the exact pinned native owner, never a generic Start.

        Only Remove recovery invokes this after restoring Lua/BIN bytes.
        The original FD9 service reuses the existing Apply runtime actuator,
        shared journal, sealed release and managed IPFW verification.
        """
        from extra_resources_transaction import _validate_native_owner
        old = _validate_native_owner(owner)
        environment = dict(os.environ)
        environment["EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE"] = "1"
        result = subprocess.run(
            [str(self.script), "extra-resources-native-restore-previous",
             old["id"], old["page"], old["candidate"]],
            env=environment, pass_fds=(9,),
            capture_output=True, text=True, timeout=180, check=False,
        )
        # The existing common boot prints its own receipt; so does the
        # shared journal rewind. The LAST line is the native verified owner.
        # Requiring a single line would falsely label a proven restoration
        # RESTORE_FAILED after the actual engine and IPFW were restored.
        lines = result.stdout.strip().splitlines()
        if result.returncode != 0 or not lines or lines[-1] != (
            "native-owner-restored=" + old["id"]
        ):
            raise TransactionError("RESTORE_FAILED: exact previous native common owner "
                                   "was not attested after rollback")

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
    operation = os.environ.get("EXTRA_RESOURCES_OPERATION_ID", "")
    if operation and re.fullmatch(r"[a-f0-9]{32}", operation) is None:
        raise TransactionError("invalid resource operation identity")
    _safe_state(STATE)
    _json_write(STATE / "status.json", {
        "schema": 1, "operation": operation, "phase": stage, **extra,
    })


def _refresh_help_cache() -> None:
    # Display-only derivative. Never turn a successfully restored native
    # transaction into a failure because the optional help cache is unavailable.
    try:
        refresh_inventory_cache(RUNTIME, STATE)
    except (InventoryCacheError, OSError, ValueError, RuntimeError) as exc:
        print(f"WARNING: Strategies resource help cache unavailable: {exc}", file=sys.stderr)


def main(argv: list[str]) -> int:
    modes = {"install", "recover", "plan", "remove-test", "remove-test-fail",
             "remove-test-interrupt", "remove-test-commit-interrupt", "recover-test"}
    if (len(argv) < 2 or argv[1] not in modes or
            (len(argv) != 3 if argv[1].startswith("remove-test") else len(argv) != 2)):
        print("usage: extra_resources_operation.py {install|recover|plan|remove-test*|recover-test} [confirmed_sha256]", file=sys.stderr)
        return 64
    mode = argv[1]
    owner_test = mode.startswith("remove-test") or mode == "recover-test"
    if owner_test and (os.geteuid() != 0 or
                       os.environ.get("EXTRA_RESOURCES_REMOVE_OWNER_ACCEPTANCE") != "1"):
        print("owner-only Remove acceptance route is disabled", file=sys.stderr)
        return 75
    if mode == "install" and re.fullmatch(
        r"[a-f0-9]{32}", os.environ.get("EXTRA_RESOURCES_OPERATION_ID", "")
    ) is None:
        print("missing or invalid resource operation identity", file=sys.stderr)
        return 64
    try:
        if os.environ.get("EXTRA_RESOURCES_SETUP_LOCK_OWNER") != "1":
            raise TransactionError("missing original setup.lock owner")
        lifecycle = NativeLifecycle()
        if mode == "plan":
            # This is the original Git HEAD planner, not a second catalogue.
            lifecycle.assert_started()
            if (STATE / "transaction").exists() or (STATE / "transaction").is_symlink():
                raise TransactionError("RECOVERY_REQUIRED: pending resource transaction")
            plan = make_remove_plan(RUNTIME, STATE / "installed.json", Path("/conf/config.xml"))
            summary = {"status": "dry_run_only", "ready": False,
                       "lua": plan["counts"]["lua"], "bin": plan["counts"]["bin"],
                       "total": plan["counts"]["total"],
                       "inventory_sha256": plan["witness"]["inventory_sha256"]}
            print("extra-resources-remove-plan=" +
                  json.dumps(summary, sort_keys=True, separators=(",", ":")))
            return 0
        if mode in ("recover", "recover-test"):
            _status("recovering")
            status = recover(RUNTIME, STATE, lifecycle)
            _refresh_help_cache()
            _status("not_installed" if status == "REMOVED" else status.lower())
            print(status)
            return 0
        if mode.startswith("remove-test"):
            witness = argv[2]
            if not re.fullmatch(r"[0-9a-f]{64}", witness):
                raise TransactionError("invalid confirmed Remove plan SHA-256")
            fault = {
                "remove-test": None,
                "remove-test-fail": "fail-after-quarantine",
                "remove-test-interrupt": "interrupt-after-quarantine",
                "remove-test-commit-interrupt": "interrupt-after-first-committed-inode",
            }[mode]
            # Root console only, no GUI/configd/public dispatch. The full
            # live plan, unchanged Config and owner remain re-attested under
            # the original inherited setup.lock -> FD9.
            _status("removing")
            outcome = remove_with_native_trial(
                witness, RUNTIME, STATE, lifecycle, acceptance_fault=fault)
            _refresh_help_cache()
            _status("not_installed" if outcome["status"] in ("REMOVED", "NO_EXTRA_RESOURCES")
                    else "ready",
                    **outcome)
            print(json.dumps(outcome, sort_keys=True))
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
        make_plan(payloads, RUNTIME, STATE / "installed.json")
        catalog = json.loads(files["inventory/capabilities.json"].decode("utf-8"))
        _status("installing", source_commit=revision)
        result = install(payloads, revision, RUNTIME, STATE, lifecycle,
                         capabilities=catalog, reconcile=True)
        _refresh_help_cache()
        _status("ready", **result, described_capabilities=capabilities_count)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (TransactionError, PreflightError, OSError, ValueError,
            TimeoutError, subprocess.TimeoutExpired) as exc:
        code = "RESTORE_FAILED" if (
            "RESTORE_FAILED" in str(exc) or "REMOVE_COMMIT_PENDING" in str(exc)
        ) else ("RECOVERY_REQUIRED" if "RECOVERY_REQUIRED" in str(exc) else "FAILED")
        # A read-only plan, including its refusal path, must never write the
        # shared install/status receipt or poison a working installation.
        if mode != "plan":
            try:
                _status(code.lower(), detail=str(exc)[:450])
            except Exception:
                pass
        print(f"EXTRA_RESOURCES_{code}: {exc}", file=sys.stderr)
        return 70 if code == "RESTORE_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
