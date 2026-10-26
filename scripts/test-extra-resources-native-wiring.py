#!/usr/bin/env python3
"""Fail closed if resource installation drifts from the native FD9 lifecycle."""
from pathlib import Path
import py_compile
import subprocess

root = Path(__file__).resolve().parents[1]
src = root / "src/opnsense/scripts/OPNsense/Zapret"
for name in (
    "extra_resources_preflight.py",
    "extra_resources_reconcile.py",
    "extra_resources_transaction.py",
    "extra_resources_operation.py",
):
    py_compile.compile(str(src / name), doraise=True)
for name in ("extra_resources_launcher.sh", "setup_launcher.sh", "zapret_service.sh"):
    result = subprocess.run(["sh", "-n", str(src / name)], capture_output=True, text=True)
    assert result.returncode == 0, f"{name}: {result.stderr}"
launcher = (src / "extra_resources_launcher.sh").read_text()
service = (src / "zapret_service.sh").read_text()
setup = (src / "setup_launcher.sh").read_text()
actions = (root / "src/opnsense/service/conf/actions.d/actions_zapret.conf").read_text()
operation = (src / "extra_resources_operation.py").read_text()

def require(valid: bool, explanation: str) -> None:
    if not valid:
        raise AssertionError(explanation)

require('"$LOCKF_BIN" -s -t 60 "$LOCK_FILE"' in launcher,
        "setup lock not held for entire manual operation")
require(launcher.index('"$LOCKF_BIN" -s -t 60 "$LOCK_FILE"') <
        launcher.index('"$SERVICE_SCRIPT" "$_command"'),
        "setup lock must precede native FD9")
require('extra-resources-remove-plan)' in service and
        'extra-resources-remove-plan|' in service,
        "read-only Remove planning does not inherit original FD9 lifecycle")
require('exec "$LOCKF_BIN" -s -t 10 "$LOCK_FILE"' in launcher and
        '"$SERVICE_SCRIPT" extra-resources-remove-plan' in launcher,
        "read-only Remove plan bypasses original setup.lock")
require('"plan"' in operation and 'make_remove_plan(RUNTIME,' in operation and
        '"ready": False' in operation,
        "read-only Remove planner lacks source and no-authority receipt")
require('extra-resources-install|extra-resources-recover)' in service,
        "original FD9 service dispatch absent")
require('STRATEGY_LAB_LIFECYCLE_OWNER=1' in service,
        "native callbacks lost inherited FD9 owner")
require('service_with_lifecycle_lock "${LIFECYCLE_LOCK_TIMEOUT}" "$@"' in service,
        "new service actions are not serialized")
require('"strategy-lab-stop"' in operation and '"strategy-lab-start"' in operation,
        "native start/stop not used")
require('pass_fds=(9,)' in operation, "FD9 not inherited by child callbacks")
require('reconcile=True' in operation and 'make_plan(payloads' in operation,
        "production resource worker does not use exact reconciliation")
require('EXTRA_RESOURCES_PID_FILE' in setup and
        'pid_file_running "${EXTRA_RESOURCES_PID_FILE}"' in setup,
        "normal upstream launcher ignores active resource job")
for name in ("extra_resources_install", "extra_resources_status", "extra_resources_recover", "extra_resources_remove_plan"):
    require(f"[{name}]" in actions, "configd action absent: " + name)
require("extra_resources_preflight.py preflight" in actions,
        "read-only preflight unexpectedly removed")
require(all(f'"{m}"' in operation for m in
            ("remove-test", "remove-test-fail", "remove-test-interrupt",
             "recover-test")), "owner-console Remove routes are missing")
require('outcome["status"] in ("REMOVED", "NO_EXTRA_RESOURCES")' in operation,
        "empty native Remove must not report extras installed")
require("EXTRA_RESOURCES_REMOVE_OWNER_ACCEPTANCE" in operation and
        "os.geteuid() != 0" in operation,
        "owner-console Remove route is not root/explicitly gated")
require('"$SERVICE_SCRIPT" "$MODE" "$_witness"' in launcher and
        'extra-resources-recover-test' in launcher and
        '"$LOCKF_BIN" -s -t 60 "$LOCK_FILE"' in launcher,
        "owner-console Remove does not preserve original setup.lock")
require('remove-test|remove-test-fail|remove-test-interrupt' in service and
        'EXTRA_RESOURCES_REMOVE_OWNER_ACCEPTANCE' in service,
        "native FD9 owner acceptance dispatch is absent")
require("[extra_resources_remove]" not in actions and
        "[extra_resources_remove_test]" not in actions,
        "owner acceptance route must NOT expose destructive configd/GUI operation")
require('extra-resources-recover|extra-resources-recover-test)' in service and
        'the worker verifies the exact linked journals' in service,
        "recovery must remain reachable under FD9 while common Apply journal is pending")
transaction = (src / "extra_resources_transaction.py").read_text()
require('phase == "committing"' in transaction and
        'new_native_owner' in transaction and
        '_finish_committing_remove(' in transaction and
        'os.replace(work, retired)' in transaction,
        "native Remove must seal new owner before irreversible inode cleanup")

print("PASS: resource syntax and existing lifecycle/lock wiring")
