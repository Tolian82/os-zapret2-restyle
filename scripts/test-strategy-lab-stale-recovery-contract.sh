#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SERVICE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
RECOVERY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_recovery_worker.sh"
LAUNCH="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/launch.sh"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"

for file in "${SERVICE}" "${RECOVERY}" "${LAUNCH}" "${ACTIONS}" "${CONTROLLER}" "${VIEW}"
do
    [ -s "${file}" ] || { echo "FAIL: missing stale-recovery contract file: ${file}" >&2; exit 1; }
done

grep -Fq 'STRATEGY_LAB_RECOVERY_WORKER=' "${SERVICE}"
grep -Fq 'strategy-lab-recover)' "${SERVICE}"
grep -Fq 'strategy-lab|strategy-lab-circular|strategy-lab-recover)' "${SERVICE}"
grep -Fq 'run_strategy_lab_worker "${STRATEGY_LAB_RECOVERY_WORKER}"' "${SERVICE}"
grep -Fq 'strategy_lab_restore_initial_service_state' "${RECOVERY}"
grep -Fq 'lifecycle-snapshot.json' "${RECOVERY}" || grep -Fq 'strategy_lab_lifecycle_snapshot_file' "${RECOVERY}"
grep -Fq '"${TRANSACTION_SCRIPT}" strategy-lab-recover "${_strategy_lab_job}"' "${LAUNCH}"
grep -Fq '.restoration.strategy_unchanged // false' "${LAUNCH}"
grep -Fq '.restoration.temporary_runtime_clean // false' "${LAUNCH}"
! grep -Fq 'strategy_lab_recovery_restore_service' "${LAUNCH}"
! grep -Fq 'strategy_lab_recovery_service_status' "${LAUNCH}"

action_timeout()
{
    section="$1"
    awk -v target="[${section}]" '
        $0==target {inside=1; next}
        inside && /^\[/ {exit}
        inside && /^timeout:/ {sub(/^timeout:/, ""); print; exit}
    ' "${ACTIONS}"
}

for action in strategy_lab_start strategy_lab_status strategy_lab_cancel strategy_lab_result
do
    [ "$(action_timeout "${action}")" = 180 ] || {
        echo "FAIL: ${action} must contain the 180-second stale-recovery envelope" >&2
        exit 1
    }
done

grep -Fq 'private const BACKEND_TIMEOUT_SECONDS = 190;' "${CONTROLLER}"
grep -Fq 'self::BACKEND_TIMEOUT_SECONDS' "${CONTROLLER}"
grep -Fq "timeout:200000" "${VIEW}"

configd_seconds=180
mvc_seconds=190
browser_seconds=200
[ "${configd_seconds}" -lt "${mvc_seconds}" ]
[ "${mvc_seconds}" -lt "${browser_seconds}" ]
[ "${configd_seconds}" -gt 120 ] || {
    echo 'FAIL: stale recovery envelope does not contain two bounded starts plus stop normalization' >&2
    exit 1
}

sh -n "${RECOVERY}"
sh -n "${LAUNCH}"

echo 'PASS: ordinary stale recovery is lifecycle-owned, semantic-proof based, and enclosed by monotonic configd/MVC/browser timeouts'
