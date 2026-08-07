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
TEST_JOBS_DIR="${STRATEGY_LAB_JOBS_DIR}"
TEST_SERVICE_LOG="${ROOT}/service.log"
export STRATEGY_LAB_JQ STRATEGY_LAB_RUN_DIR STRATEGY_LAB_JOBS_DIR
export STRATEGY_LAB_ACTIVE_FILE STRATEGY_LAB_LOG_DIR TEST_JOBS_DIR TEST_SERVICE_LOG

mkdir -p "${STRATEGY_LAB_JOBS_DIR}" "${STRATEGY_LAB_LOG_DIR}"

make_job()
{
    job="$1"
    initial="$2"
    mkdir -p "${STRATEGY_LAB_JOBS_DIR}/${job}"
    printf '%s\n' 999999 > "${STRATEGY_LAB_JOBS_DIR}/${job}/worker.pid"
    "${STRATEGY_LAB_JQ}" -nc --arg state "${initial}" '
        {state:"running",outcome:"",initial_service_state:$state,
         stages:[{number:"00",status:"PASS",message:""},
                 {number:"90",status:"PENDING",message:""},
                 {number:"99",status:"PENDING",message:""}]}
    ' > "${STRATEGY_LAB_JOBS_DIR}/${job}/status.json"
    printf '%s\n' "${job}" > "${STRATEGY_LAB_ACTIVE_FILE}"
}

strategy_lab_udp_input_cleanup() { :; }

TRANSACTION_SCRIPT="${ROOT}/service"
cat > "${TRANSACTION_SCRIPT}" <<'EOS'
#!/bin/sh
set -eu
printf '%s\n' "$*" >> "${TEST_SERVICE_LOG}"
[ "${1:-}" = strategy-lab-recover ] || exit 91
job="${2:-}"
status="${TEST_JOBS_DIR}/${job}/status.json"
tmp="${status}.tmp.$$"
case "${TEST_RECOVERY_MODE:-}" in
    verified)
        jq '.restoration={verified:true,source:"zapret_service",initial_state:.initial_service_state,
             final_state:.initial_service_state,strategy_unchanged:true,temporary_runtime_clean:true}' \
            "${status}" > "${tmp}"
        mv -f "${tmp}" "${status}"
        exit 0
        ;;
    inconsistent)
        jq '.restoration={verified:true,source:"zapret_service",initial_state:.initial_service_state,
             final_state:.initial_service_state,strategy_unchanged:false,temporary_runtime_clean:true}' \
            "${status}" > "${tmp}"
        mv -f "${tmp}" "${status}"
        exit 0
        ;;
    failed)
        jq '.restoration={verified:false,source:"zapret_service",initial_state:.initial_service_state,
             final_state:"unknown",strategy_unchanged:false,temporary_runtime_clean:true}' \
            "${status}" > "${tmp}"
        mv -f "${tmp}" "${status}"
        exit 1
        ;;
    *) exit 92 ;;
esac
EOS
chmod +x "${TRANSACTION_SCRIPT}"

. "${COMMON_UNDER_TEST}"
. "${LAUNCH_UNDER_TEST}"

make_job job.good STOPPED
TEST_RECOVERY_MODE=verified
export TEST_RECOVERY_MODE
strategy_lab_reconcile_stale_job job.good
"${STRATEGY_LAB_JQ}" -e '
    .state=="error" and .outcome=="ERROR" and .stale_worker_recovered==true and
    .restoration.verified==true and .restoration.strategy_unchanged==true and
    .restoration.temporary_runtime_clean==true and
    any(.stages[]; .number=="90" and .status=="PASS")
' "${STRATEGY_LAB_JOBS_DIR}/job.good/status.json" >/dev/null
[ ! -e "${STRATEGY_LAB_ACTIVE_FILE}" ]
[ ! -e "${STRATEGY_LAB_JOBS_DIR}/job.good/worker.pid" ]

make_job job.bad RUNNING
TEST_RECOVERY_MODE=inconsistent
export TEST_RECOVERY_MODE
strategy_lab_reconcile_stale_job job.bad
"${STRATEGY_LAB_JQ}" -e '
    .state=="error" and .outcome=="RESTORE_FAILED" and .stale_worker_recovered==true and
    .restoration.verified==false and .restoration.strategy_unchanged==false and
    any(.stages[]; .number=="90" and .status=="FAIL")
' "${STRATEGY_LAB_JOBS_DIR}/job.bad/status.json" >/dev/null

make_job job.fail RUNNING
TEST_RECOVERY_MODE=failed
export TEST_RECOVERY_MODE
strategy_lab_reconcile_stale_job job.fail
"${STRATEGY_LAB_JQ}" -e '
    .state=="error" and .outcome=="RESTORE_FAILED" and
    .restoration.verified==false and
    any(.stages[]; .number=="90" and .status=="FAIL")
' "${STRATEGY_LAB_JOBS_DIR}/job.fail/status.json" >/dev/null

[ "$(wc -l < "${TEST_SERVICE_LOG}" | tr -d ' ')" -eq 3 ]
if grep -Ev '^strategy-lab-recover job\.(good|bad|fail)$' "${TEST_SERVICE_LOG}" | grep -q .; then
    echo 'FAIL: stale launcher used a public start/stop/status lifecycle shortcut' >&2
    exit 1
fi

grep -Fq 'strategy_lab_udp_input_cleanup() { :; }' "$0"

echo 'PASS: stale-worker reconciliation delegates to lifecycle-owned recovery and accepts only complete semantic restoration proof'
