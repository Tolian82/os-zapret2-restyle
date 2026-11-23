#!/usr/bin/env python3
"""S03e3d original-FD9 lifecycle receipt SOURCE and inert shell contract.

Does not dispatch service, configd, PHP, IPFW or test-owned processes.
The genuine installed producer->PHP->GUI evidence is stage5 Chromium.
"""
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
ACTIONS = ROOT / "src/opnsense/service/conf/actions.d/actions_zapret.conf"
PHP = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php"
GUI = ROOT / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt"


class Refused(Exception):
    pass


def require(ok, label):
    if not ok:
        raise Refused(label)


def read_sources():
    shell = SHELL.read_text(encoding="utf-8")
    actions = ACTIONS.read_text(encoding="utf-8")
    php = PHP.read_text(encoding="utf-8")
    gui = GUI.read_text(encoding="utf-8")
    need = [
        "service_api_terminal_receipt()",
        "shared_apply_status_service >/dev/null 2>&1",
        "stop:1)", "restart:0)",
        "zapret-api-lifecycle-v1:stop:stopped",
        "zapret-api-lifecycle-v1:restart:running",
        '_service_receipt_action="$1"',
        'set -- "$1"',
        'if [ -n "$_service_receipt_action" ]; then',
        "service_with_lifecycle_lock",
    ]
    require(all(t in shell for t in need),
            "S03E3D_ORIGINAL_FD9_NATIVE_PROOF_ROUTE_MISSING")
    for verb in ("stop", "restart"):
        # The legacy public command stays in the SAME original FD9 owner.
        require(("[" + verb + "]\ncommand:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh " + verb) in actions,
                "S03E3D_LEGACY_ACTION_CHANGED_" + verb)
        require(("[" + verb + "_verified]\ncommand:/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh " +
                 verb + " --configd-receipt\nparameters:\ntype:script_output") in actions,
                "S03E3D_PRIVATE_ACTION_NOT_ORIGINAL_DISPATCHER_" + verb)
        require(("return $this->verifiedLifecycleAction('" + verb + "');") in php,
                "S03E3D_API_NOT_USING_TERMINAL_RECEIPT_" + verb)
    require("strlen($raw) <= 8192" in php and
            "substr_count($raw, 'zapret-api-lifecycle-v1:') === 1" in php and
            "preg_match(" in php and
            "throw new UserException(" in php and
            "'verified' => true" in php,
            "S03E3D_PHP_FAIL_CLOSED_PARSER_MISSING")
    require("receipt.verified !== true" in gui and
            "action === 'stop' ? ''" in gui and
            "Ошибка управления службой" in gui and
            "Service operation failed" in gui,
            "S03E3D_GUI_NO_WRONG_200_OR_LEAK_GUARD")
    require("RULE_BASE=19000" in shell and "RULE_MAX=19099" in shell and
            "service_with_lifecycle_lock" in shell,
            "S03E3D_ORIGINAL_IPFW_FD9_SCOPE_CHANGED")
    start = shell.find("service_api_terminal_receipt()\n{\n")
    end = shell.find("\n}\n\nservice_with_lifecycle_lock()", start)
    require(start >= 0 and end > start, "S03E3D_INERT_FUNCTION_EXTRACTION_CHANGED")
    return shell[start:end+2]


def inert_receipt_tests(body):
    for verb, rc, status, expected_rc, expected in (
        ("stop", 0, 1, 0, "zapret-api-lifecycle-v1:stop:stopped\n"),
        ("restart", 0, 0, 0, "zapret-api-lifecycle-v1:restart:running\n"),
        ("stop", 75, 1, 75, ""),
        ("restart", 69, 0, 69, ""),
        ("stop", 0, 0, 70, ""),
        ("stop", 0, 2, 70, ""),
        ("restart", 0, 1, 70, ""),
        ("restart", 0, 2, 70, ""),
    ):
        # Only the isolated receipt helper, with simulated status return. No
        # original service, no FD9, no system path and no kernel action.
        script = (body + "\nshared_apply_status_service() { return " +
                  str(status) + "; }\nservice_api_terminal_receipt " +
                  verb + " " + str(rc) + "\n")
        proc = subprocess.run(["/bin/sh"], input=script,
                              text=True, capture_output=True, timeout=5)
        require(proc.returncode == expected_rc and proc.stdout == expected,
                "S03E3D_INERT_RECEIPT_MISMATCH_" + verb + "_" +
                str(rc) + "_" + str(status))
    print("S03E3D_INERT_TERMINAL_RECEIPT_NEGATIVE_MATRIX=PASS")


def main():
    require(sys.argv[1:] == ["--self-test"], "S03E3D_INERT_SELFTEST_ONLY")
    body = read_sources()
    print("S03E3D_SOURCE_SINGLE_ORIGINAL_FD9_REVIEW=PASS")
    inert_receipt_tests(body)


if __name__ == "__main__":
    try:
        main()
    except (Refused, OSError, ValueError) as exc:
        print("S03E3D_INERT_REFUSED=" + str(exc)[:180], file=sys.stderr)
        raise SystemExit(2)
