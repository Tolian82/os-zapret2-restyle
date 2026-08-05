#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMMON_UNDER_TEST="${COMMON_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/common.sh}"
LAUNCH_UNDER_TEST="${LAUNCH_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/launch.sh}"
ROOT=$(mktemp -d /tmp/strategy-lab-stale.XXXXXX)
trap 'rm -rf "${ROOT}"' EXIT HUP INT TERM

STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_RUN_DIR="${ROOT}/run"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_RUN_DIR}/jobs"
STRATEGY_LAB_ACTIVE_FILE="${STRATEGY_LAB_RUN_DIR}/active.job"
STRATEGY_LAB_LOG_DIR="${ROOT}/log"
export STRATEGY_LAB_JQ STRATEGY_LAB_RUN_DIR STRATEGY_LAB_JOBS_DIR
export STRATEGY_LAB_ACTIVE_FILE STRATEGY_LAB_LOG_DIR

mkdir -p "${STRATEGY_LAB_JOBS_DIR}/job.dead" "${STRATEGY_LAB_LOG_DIR}"
printf '%s\n' job.dead > "${STRATEGY_LAB_ACTIVE_FILE}"
printf '%s\n' 999999 > "${STRATEGY_LAB_JOBS_DIR}/job.dead/worker.pid"
printf '%s\n' '{"state":"running","outcome":"","initial_service_state":"STOPPED","stages":[{"number":"00","status":"PASS","message":""},{"number":"90","status":"PENDING","message":""},{"number":"99","status":"PENDING","message":""}]}' > "${STRATEGY_LAB_JOBS_DIR}/job.dead/status.json"

strategy_lab_candidate_stop() { return 0; }
strategy_lab_firewall_remove_rules() { return 0; }
strategy_lab_firewall_range_empty() { return 0; }
strategy_lab_candidate_runtime_absent() { return 0; }

TRANSACTION_SCRIPT="${ROOT}/service"
cat > "${TRANSACTION_SCRIPT}" <<'EOS'
#!/bin/sh
case "$1" in
    status) exit 1 ;;
    stop) exit 0 ;;
    *) exit 1 ;;
esac
EOS
chmod +x "${TRANSACTION_SCRIPT}"

. "${COMMON_UNDER_TEST}"
. "${LAUNCH_UNDER_TEST}"

strategy_lab_reconcile_stale_job job.dead
jq -e '.state=="error" and .outcome=="ERROR" and .stale_worker_recovered==true and .restoration.verified==true' \
    "${STRATEGY_LAB_JOBS_DIR}/job.dead/status.json" >/dev/null
[ ! -e "${STRATEGY_LAB_ACTIVE_FILE}" ]
[ ! -e "${STRATEGY_LAB_JOBS_DIR}/job.dead/worker.pid" ]

echo 'PASS: a missing Strategy Lab worker is reconciled into a terminal restored result'
