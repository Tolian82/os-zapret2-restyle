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
             "remove-test-commit-interrupt", "recover-test")), "owner-console Remove routes are missing")
require('outcome["status"] in ("REMOVED", "NO_EXTRA_RESOURCES")' in operation,
        "empty native Remove must not report extras installed")
require("EXTRA_RESOURCES_REMOVE_OWNER_ACCEPTANCE" in operation and
        "os.geteuid() != 0" in operation,
        "owner-console Remove route is not root/explicitly gated")
require('"$SERVICE_SCRIPT" "$MODE" "$_witness"' in launcher and
        'extra-resources-recover-test' in launcher and
        '"$LOCKF_BIN" -s -t 60 "$LOCK_FILE"' in launcher,
        "owner-console Remove does not preserve original setup.lock")
require('remove-test|remove-test-fail|remove-test-interrupt|remove-test-commit-interrupt' in service and
        'EXTRA_RESOURCES_REMOVE_OWNER_ACCEPTANCE' in service,
        "native FD9 owner acceptance dispatch is absent")
require("remove-test-commit-interrupt" in launcher and
        "remove-test-commit-interrupt" in operation,
        "R4 console mode not consistently routed")
require("[extra_resources_remove]" in actions and
        "parameters:%s %s %s" in actions.split("[extra_resources_remove]", 1)[1].split("[", 1)[0],
        "production Remove configd action must receive ID, witness and confirmation")
require("[extra_resources_remove_test]" not in actions and
        "[extra_resources_recover_test]" not in actions,
        "destructive owner fault-injection routes cannot be available in configd")

require('extra-resources-recover|extra-resources-recover-test)' in service and
        'the worker verifies the exact linked journals' in service,
        "recovery must remain reachable under FD9 while common Apply journal is pending")
transaction = (src / "extra_resources_transaction.py").read_text()
require('phase == "committing"' in transaction and
        'new_native_owner' in transaction and
        '_finish_committing_remove(' in transaction and
        'os.replace(work, retired)' in transaction,
        "native Remove must seal new owner before irreversible inode cleanup")

require("interrupt-after-first-committed-inode" in transaction and
        "OWNER_ACCEPTANCE_INTERRUPTED_AFTER_FIRST_COMMITTED_INODE" in transaction,
        "R4 post-commit first-inode fault point absent")

# Regression: R4 must traverse the ACTUAL top-level owner FD9 lock wrapper,
# not merely exist in service_dispatch() or the nested native dispatcher.
top = service.rsplit('\ncase "${1:-}" in\n', 1)
require(len(top) == 2, "could not locate original top-level service dispatch")
outer_case = top[1]
outer_branch = next(
    (line.strip() for line in outer_case.splitlines()
     if line.strip().startswith("start|stop|restart|reconfigure|")),
    "",
)
require("remove-test-commit-interrupt" in outer_branch.rstrip(")").split("|"),
        "R4 must acquire original service_with_lifecycle_lock FD9")
require('service_with_lifecycle_lock "${LIFECYCLE_LOCK_TIMEOUT}" "$@"' in outer_case,
        "top-level lifecycle FD9 owner call missing")
wrapper = service.split("service_with_lifecycle_lock()\n", 1)
require(len(wrapper) == 2, "original lifecycle lock wrapper not found")
wrapper_case = wrapper[1].split('\ncase "${1:-}" in\n', 1)[0]
preflight_branch = next(
    (line.strip() for line in wrapper_case.splitlines()
     if line.strip().startswith("strategy-lab|strategy-lab-circular|strategy-lab-recover|")),
    "",
)
require("remove-test-commit-interrupt" in preflight_branch.rstrip(")").split("|"),
        "R4 must pass native shared-Apply owner preflight under FD9")
require("remove-test-commit-interrupt" not in outer_case.split('    *)\n', 1)[-1],
        "R4 must not be explicitly sent to unlocked fallback")

# Owner R4 read-only audit must traverse original setup.lock -> FD9, reuse the
# existing native owner and semantic IPFW witnesses, and stay OFF configd/GUI.
require('    audit-native)' in launcher and
        '"$SERVICE_SCRIPT" extra-resources-native-audit' in launcher and
        '"$LOCKF_BIN" -s -t 10 "$LOCK_FILE"' in launcher,
        "native owner audit launcher is not serialized under setup.lock")
require('extra-resources-native-audit)' in service and
        'extra_resources_native_audit_service()' in service and
        'extra_resources_native_previous_owner_service' in service and
        'strategy_lab_semantic_evidence' in service,
        "native owner audit does not reuse existing common-owner and semantic evidence")
outer_audit = next(
    (line.strip() for line in outer_case.splitlines()
     if line.strip().startswith("start|stop|restart|reconfigure|")), "",
)
require("extra-resources-native-audit" in outer_audit.rstrip(")").split("|"),
        "native audit must acquire original lifecycle FD9 at top-level dispatch")
require("extra-resources-native-audit" in preflight_branch.rstrip(")").split("|"),
        "native audit omitted original shared-Apply owner preflight")
auditor = service.split("extra_resources_native_audit_service()\n", 1)
require(len(auditor) == 2, "native audit function missing")
audit_body = auditor[1].split("\n}\n", 1)[0]
require(all(k in audit_body for k in (
    "strategy_lab_lock_owner_valid", "extra_resources_native_previous_owner_service",
    "strategy_lab_semantic_evidence", "normal_firewall_hash",
    "child_running", "supervisor_running", "return 69",
    "transaction", ".extra-resources-remove-quarantine",
)), "native audit does not fail closed on owner, IPFW, or pending transaction")
require("audit-native" not in actions and
        "extra-resources-native-audit" not in actions,
        "private owner audit must not create a configd/GUI action")

# Production Remove must use the one existing daemon/lock/native transaction,
# while owner fault-injection modes remain isolated from GUI/configd.
require('install|recover|remove)' in launcher and
        '"$SERVICE_SCRIPT" extra-resources-remove "$_confirmed_witness"' in launcher and
        'EXTRA_RESOURCES_REMOVE_CONFIRMED=1' in launcher and
        '"$LOCKF_BIN" -s -t 0 "$LOCK_FILE"' in launcher,
        "production Remove launcher has no nonqueueing original setup.lock")
require('        extra-resources-remove)' in service and
        'extra-resources-remove|' in service,
        "production Remove not dispatched through original native FD9")
require('"remove": None' in operation and
        'EXTRA_RESOURCES_REMOVE_CONFIRMED' in operation and
        'mode in ("install", "remove")' in operation and
        'remove_with_native_trial(' in operation,
        "production Remove bypasses explicit native authorization or accepted fault-free path")
controller = (root / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php").read_text()
require('public function resourcesRemoveAction(): array' in controller and
        "if (!$this->request->isPost())" in controller and
        "$confirmation !== 'REMOVE ' . (string)$plan['total']" in controller and
        "($plan['inventory_sha256'] ?? '') !== $witness" in controller and
        "'zapret extra_resources_remove'" in controller and
        "'status' => 'uncertain'" in controller,
        "API Remove lacks POST, exact fresh plan, explicit count confirmation, or honest async receipt")
view = (root / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
# Stage 7 supersedes the earlier backend-only gate. GUI may invoke ONLY the
# previously accepted exact-plan production API after deliberate typed consent.
require(view.count("url: '/api/zapret/service/resourcesRemove',") == 1 and
        "url: '/api/zapret/service/resourcesRemovePlan'," in view and
        "const phrase = 'REMOVE ' + plan.total" in view and
        "inventory_sha256: plan.inventory_sha256" in view and
        "confirmation: phrase" in view and
        "extraRemoveTerminal(data, extraRemoveOperation)" in view and
        "extraNeedsReview = true" in view,
        "Stage 7 Remove GUI bypasses the exact-plan native API or correlated status")
print("PASS: resource syntax and existing lifecycle/lock wiring")
