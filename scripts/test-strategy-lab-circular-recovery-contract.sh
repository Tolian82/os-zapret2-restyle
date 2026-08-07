#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
OWNER="${SCRIPT_DIR}/strategy_lab/circular_owner.sh"
RECOVERY="${SCRIPT_DIR}/strategy_lab_recovery_worker.sh"
SERVICE="${SCRIPT_DIR}/zapret_service.sh"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/CircularController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"

for file in "${OWNER}" "${RECOVERY}" "${SERVICE}" "${ACTIONS}" "${CONTROLLER}" "${VIEW}"
do
    [ -s "${file}" ] || { echo "FAIL: missing circular recovery contract file: ${file}" >&2; exit 1; }
done

! grep -Fq 'strategy_lab_restore_initial_service_state' "${OWNER}"
grep -Fq 'STRATEGY_LAB_CIRCULAR_RECOVERY_SCRIPT' "${OWNER}"
grep -Fq 'strategy-lab-recover "${_slco_session}"' "${OWNER}"
grep -Fq 'strategy_lab_circular_recovery_verified' "${OWNER}"
grep -Fq 'strategy_lab_circular_recovery_mark_unverified' "${OWNER}"

grep -Fq 'for module in common state firewall runtime candidate lifecycle circular' "${RECOVERY}"
grep -Fq 'STRATEGY_LAB_CIRCULAR_SESSIONS_DIR' "${RECOVERY}"
grep -Fq 'strategy_lab_circular_session_state_file' "${RECOVERY}"
grep -Fq 'strategy_lab_restore_initial_service_state' "${RECOVERY}"

grep -Fq 'strategy-lab|strategy-lab-circular|strategy-lab-recover)' "${SERVICE}"
grep -Fq 'STRATEGY_LAB_LIFECYCLE_OWNER=1' "${SERVICE}"

action_timeout()
{
    section="$1"
    awk -v target="[${section}]" '
        $0==target {inside=1; next}
        inside && /^\[/ {exit}
        inside && /^timeout:/ {sub(/^timeout:/, ""); print; exit}
    ' "${ACTIONS}"
}

for action in strategy_lab_circular_start strategy_lab_circular_status strategy_lab_circular_stop
do
    [ "$(action_timeout "${action}")" = 180 ] || {
        echo "FAIL: ${action} must contain the 180-second circular stale-recovery envelope" >&2
        exit 1
    }
done

grep -Fq 'private const BACKEND_TIMEOUT_SECONDS = 190;' "${CONTROLLER}"
grep -Fq 'self::BACKEND_TIMEOUT_SECONDS' "${CONTROLLER}"
grep -Fq 'timeout:200000' "${VIEW}"

sh -n "${OWNER}"
sh -n "${RECOVERY}"
echo 'PASS: circular stale recovery uses the lifecycle-owned semantic transaction, loads the automated-job state adapter, keeps private circular state shell-owned, and preserves the 180/190/200 second response envelope'
