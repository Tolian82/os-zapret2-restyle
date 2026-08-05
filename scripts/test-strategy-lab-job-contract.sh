#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"
PROBE_RUNNER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_probe_runner.sh"
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
STRATEGY_CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

sh "${ROOT_DIR}/scripts/test-strategy-lab-lifecycle.sh"
sh "${ROOT_DIR}/scripts/test-strategy-lab-precheck.sh"
sh "${ROOT_DIR}/scripts/test-strategy-lab-cancel-state.sh"
sh "${ROOT_DIR}/scripts/test-strategy-lab-active-cancel.sh"
sh "${ROOT_DIR}/scripts/test-strategy-lab-stage-machine.sh"
sh "${ROOT_DIR}/scripts/test-strategy-lab-terminal-result.sh"

sh -n "${LAUNCHER}"
sh -n "${WORKER}"
sh -n "${PROBE_RUNNER}"
sh -n "${MODULE_DIR}/common.sh"
sh -n "${MODULE_DIR}/state.sh"
sh -n "${MODULE_DIR}/lifecycle.sh"
sh -n "${MODULE_DIR}/launch.sh"
sh -n "${MODULE_DIR}/query.sh"
sh -n "${MODULE_DIR}/target.sh"
sh -n "${MODULE_DIR}/request.sh"
sh -n "${MODULE_DIR}/result.sh"
sh -n "${MODULE_DIR}/probe.sh"
php -l "${STRATEGY_CONTROLLER}" >/dev/null

grep -Fq '[strategy_lab_start]' "${ACTIONS}" || fail "start action is missing"
grep -Fq '[strategy_lab_status]' "${ACTIONS}" || fail "status action is missing"
grep -Fq '[strategy_lab_cancel]' "${ACTIONS}" || fail "cancel action is missing"
grep -Fq '[strategy_lab_result]' "${ACTIONS}" || fail "result action is missing"
grep -Fq 'startAction' "${STRATEGY_CONTROLLER}" || fail "start API is missing"
grep -Fq 'statusAction' "${STRATEGY_CONTROLLER}" || fail "status API is missing"
grep -Fq 'cancelAction' "${STRATEGY_CONTROLLER}" || fail "cancel API is missing"
grep -Fq 'resultAction' "${STRATEGY_CONTROLLER}" || fail "result API is missing"
grep -Fq 'id="strategyLabBtn"' "${VIEW}" || fail "active Strategy Lab controls are missing"
grep -Fq "'/api/zapret/strategy_lab/start'" "${VIEW}" || fail "active Strategy Lab start call is missing"
grep -Fq "'/api/zapret/strategy_lab/status'" "${VIEW}" || fail "active Strategy Lab status call is missing"
grep -Fq "'/api/zapret/strategy_lab/cancel'" "${VIEW}" || fail "active Strategy Lab cancel call is missing"
grep -Fq "'/api/zapret/strategy_lab/result'" "${VIEW}" || fail "active Strategy Lab result call is missing"
! grep -Fq "'/api/zapret/diagnostics/blockcheck'" "${VIEW}" || fail "legacy Blockcheck call remains active"
grep -Fq 'TRANSACTION_SCRIPT="${TRANSACTION_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"' "${LAUNCHER}" ||
    fail "Strategy Lab launcher does not use the service-owned lifecycle transaction"

echo 'PASS: asynchronous Strategy Lab job, lifecycle, and active Diagnostics GUI contract'
