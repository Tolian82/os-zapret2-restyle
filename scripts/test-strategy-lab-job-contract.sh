#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
STRATEGY_CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
SHELL_VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/strategy_lab_shell.volt"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-job-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

MOCK_BIN="${TMP_ROOT}/bin"
RUN_DIR="${TMP_ROOT}/run"
LOG_DIR="${TMP_ROOT}/log"
mkdir -p "${MOCK_BIN}" "${RUN_DIR}" "${LOG_DIR}"

cat > "${MOCK_BIN}/lockf" <<'MOCK'
#!/bin/sh
exit "${MOCK_LOCKF_STATUS:-0}"
MOCK

cat > "${MOCK_BIN}/daemon" <<'MOCK'
#!/bin/sh
log_file=""
pid_file=""
while [ "$#" -gt 0 ]
do
    case "$1" in
        -f)
            shift
            ;;
        -o)
            log_file="$2"
            shift 2
            ;;
        -p)
            pid_file="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done
"$@" >> "${log_file}" 2>&1 &
worker_pid=$!
printf '%s\n' "${worker_pid}" > "${pid_file}"
exit 0
MOCK
chmod +x "${MOCK_BIN}/lockf" "${MOCK_BIN}/daemon"

launcher()
{
    STRATEGY_LAB_JQ="$(command -v jq)" \
    STRATEGY_LAB_RUN_DIR="${RUN_DIR}" \
    STRATEGY_LAB_LOG_DIR="${LOG_DIR}" \
    STRATEGY_LAB_JOBS_DIR="${RUN_DIR}/jobs" \
    STRATEGY_LAB_ACTIVE_FILE="${RUN_DIR}/active.job" \
    STRATEGY_LAB_LOCK_FILE="${RUN_DIR}/launcher.lock" \
    SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret" \
    MODULE_DIR="${MODULE_DIR}" \
    WORKER_SCRIPT="${WORKER}" \
    DAEMON_BIN="${MOCK_BIN}/daemon" \
    LOCKF_BIN="${MOCK_BIN}/lockf" \
    WORKER_HOLD_SECONDS="${WORKER_HOLD_SECONDS:-1}" \
    "${LAUNCHER}" "$@"
}

wait_for_state()
{
    job_id="$1"
    expected="$2"
    attempts=0
    while [ "${attempts}" -lt 30 ]
    do
        state=$(launcher status "${job_id}" | jq -r '.state // ""')
        [ "${state}" != "${expected}" ] || return 0
        sleep 1
        attempts=$((attempts + 1))
    done
    fail "job ${job_id} did not reach ${expected}"
}

START_OUTPUT=$(WORKER_HOLD_SECONDS=1 launcher start telegram.org standard en)
printf '%s\n' "${START_OUTPUT}" | jq -e '.status=="ok" and .state=="queued"' >/dev/null ||
    fail "start did not return an accepted asynchronous job"
JOB_ID=$(printf '%s\n' "${START_OUTPUT}" | jq -r '.job_id')
printf '%s\n' "${JOB_ID}" | grep -Eq '^job\.[A-Za-z0-9]+$' || fail "invalid job id"
wait_for_state "${JOB_ID}" completed
RESULT=$(launcher result "${JOB_ID}")
printf '%s\n' "${RESULT}" | jq -e '.outcome=="PARTIAL" and .cancel_requested==false' >/dev/null ||
    fail "framework job did not complete as an honest partial result"
printf '%s\n' "${RESULT}" | jq -e '.stages[] | select(.number=="00" and .status=="PASS")' >/dev/null ||
    fail "target initialization did not pass"
printf '%s\n' "${RESULT}" | jq -e '.stages[] | select(.number=="10" and .status=="SKIPPED")' >/dev/null ||
    fail "unimplemented stages were not skipped"
[ ! -e "${RUN_DIR}/active.job" ] || fail "completed job remained active"

WORKER_HOLD_SECONDS=10
export WORKER_HOLD_SECONDS
START_OUTPUT=$(launcher start example.org standard ru)
CANCEL_JOB=$(printf '%s\n' "${START_OUTPUT}" | jq -r '.job_id')
sleep 1
BUSY_OUTPUT=$(launcher start second.example standard en)
printf '%s\n' "${BUSY_OUTPUT}" | jq -e '.status=="busy" and .job_id=="'"${CANCEL_JOB}"'"' >/dev/null ||
    fail "busy response did not identify the active job"
launcher cancel "${CANCEL_JOB}" >/dev/null
wait_for_state "${CANCEL_JOB}" completed
CANCEL_RESULT=$(launcher result "${CANCEL_JOB}")
printf '%s\n' "${CANCEL_RESULT}" | jq -e '.outcome=="PARTIAL" and .cancel_requested==true' >/dev/null ||
    fail "canceled job was not a partial normal result"
printf '%s\n' "${CANCEL_RESULT}" | jq -e '.stages | all(.status=="SKIPPED")' >/dev/null ||
    fail "interrupted and remaining stages were not skipped"
printf '%s\n' "${CANCEL_RESULT}" | jq -e '.stages | all(.message=="SKIPPED — отменено")' >/dev/null ||
    fail "Russian canceled-stage text is not exact"
[ ! -e "${RUN_DIR}/active.job" ] || fail "canceled job remained active"

START_OUTPUT=$(launcher start english.example standard en)
EN_CANCEL_JOB=$(printf '%s\n' "${START_OUTPUT}" | jq -r '.job_id')
sleep 1
launcher cancel "${EN_CANCEL_JOB}" >/dev/null
wait_for_state "${EN_CANCEL_JOB}" completed
EN_CANCEL_RESULT=$(launcher result "${EN_CANCEL_JOB}")
printf '%s\n' "${EN_CANCEL_RESULT}" | jq -e '.stages | all(.message=="SKIPPED — canseled")' >/dev/null ||
    fail "English canceled-stage text is not exact"

IDLE=$(launcher status)
printf '%s\n' "${IDLE}" | jq -e '.status=="idle"' >/dev/null || fail "idle state was not reported"

set +e
INVALID=$(launcher start 'bad/target' standard en 2>&1)
INVALID_STATUS=$?
set -e
[ "${INVALID_STATUS}" -eq 64 ] || fail "unsafe target was not rejected"
printf '%s\n' "${INVALID}" | grep -Fq 'invalid target' || fail "invalid target reason is missing"

sh -n "${LAUNCHER}"
sh -n "${WORKER}"
sh -n "${MODULE_DIR}/common.sh"
sh -n "${MODULE_DIR}/state.sh"
php -l "${STRATEGY_CONTROLLER}" >/dev/null

grep -Fq '[strategy_lab_start]' "${ACTIONS}" || fail "start action is missing"
grep -Fq '[strategy_lab_status]' "${ACTIONS}" || fail "status action is missing"
grep -Fq '[strategy_lab_cancel]' "${ACTIONS}" || fail "cancel action is missing"
grep -Fq '[strategy_lab_result]' "${ACTIONS}" || fail "result action is missing"
grep -Fq "startAction" "${STRATEGY_CONTROLLER}" || fail "start API is missing"
grep -Fq "statusAction" "${STRATEGY_CONTROLLER}" || fail "status API is missing"
grep -Fq "cancelAction" "${STRATEGY_CONTROLLER}" || fail "cancel API is missing"
grep -Fq "resultAction" "${STRATEGY_CONTROLLER}" || fail "result API is missing"
grep -Fq 'id="strategyLabShell"' "${SHELL_VIEW}" || fail "Strategy Lab GUI shell is missing"
grep -Fq 'style="display: none;"' "${SHELL_VIEW}" || fail "Strategy Lab shell is not dormant"
grep -Fq 'SKIPPED — canseled' "${SHELL_VIEW}" || fail "English canceled-stage message is missing"
grep -Fq 'SKIPPED — отменено' "${SHELL_VIEW}" || fail "Russian canceled-stage message is missing"
grep -Fq "'/api/zapret/diagnostics/blockcheck'" "${VIEW}" || fail "legacy Blockcheck was switched prematurely"
grep -Fq "'/api/zapret/strategylab/start'" "${SHELL_VIEW}" || fail "Strategy Lab start helper is missing"

echo 'PASS: asynchronous Strategy Lab job and dormant GUI shell contract'
