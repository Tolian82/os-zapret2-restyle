#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"
SERVICE_SOURCE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-lifecycle-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

MOCK_BIN="${TMP_ROOT}/bin"
RUN_DIR="${TMP_ROOT}/run"
LOG_DIR="${TMP_ROOT}/log"
STATE_FILE="${TMP_ROOT}/service.state"
CALLS_FILE="${TMP_ROOT}/service.calls"
START_FAIL_FILE="${TMP_ROOT}/start.fail"
STOP_FAIL_FILE="${TMP_ROOT}/stop.fail"
mkdir -p "${MOCK_BIN}" "${RUN_DIR}" "${LOG_DIR}"

cat > "${MOCK_BIN}/lockf" <<'MOCK'
#!/bin/sh
exit 0
MOCK

cat > "${MOCK_BIN}/daemon" <<'MOCK'
#!/bin/sh
log_file=""
pid_file=""
while [ "$#" -gt 0 ]
do
    case "$1" in
        -f) shift ;;
        -o) log_file="$2"; shift 2 ;;
        -p) pid_file="$2"; shift 2 ;;
        *) break ;;
    esac
done
"$@" >> "${log_file}" 2>&1 &
pid=$!
printf '%s\n' "${pid}" > "${pid_file}"
exit 0
MOCK

cat > "${MOCK_BIN}/service" <<'MOCK'
#!/bin/sh
state=$(cat "${MOCK_STATE_FILE}")
case "${1:-}" in
    strategy-lab)
        STRATEGY_LAB_LIFECYCLE_OWNER=1
        STRATEGY_LAB_SERVICE_SCRIPT="$0"
        export STRATEGY_LAB_LIFECYCLE_OWNER STRATEGY_LAB_SERVICE_SCRIPT
        exec "${MOCK_WORKER}" "${2:-}"
        ;;
    strategy-lab-status)
        case "${state}" in
            RUNNING) exit 0 ;;
            STOPPED) exit 1 ;;
            *) exit 2 ;;
        esac
        ;;
    strategy-lab-stop)
        printf '%s\n' stop >> "${MOCK_CALLS_FILE}"
        [ ! -e "${MOCK_STOP_FAIL_FILE}" ] || exit 1
        printf '%s\n' STOPPED > "${MOCK_STATE_FILE}"
        exit 0
        ;;
    strategy-lab-start)
        printf '%s\n' start >> "${MOCK_CALLS_FILE}"
        [ ! -e "${MOCK_START_FAIL_FILE}" ] || exit 1
        printf '%s\n' RUNNING > "${MOCK_STATE_FILE}"
        exit 0
        ;;
    *)
        exit 64
        ;;
esac
MOCK
chmod +x "${MOCK_BIN}/lockf" "${MOCK_BIN}/daemon" "${MOCK_BIN}/service"

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
    TRANSACTION_SCRIPT="${MOCK_BIN}/service" \
    DAEMON_BIN="${MOCK_BIN}/daemon" \
    LOCKF_BIN="${MOCK_BIN}/lockf" \
    STRATEGY_LAB_TIMEOUT_BIN="$(command -v timeout)" \
    MOCK_WORKER="${WORKER}" \
    MOCK_STATE_FILE="${STATE_FILE}" \
    MOCK_CALLS_FILE="${CALLS_FILE}" \
    MOCK_START_FAIL_FILE="${START_FAIL_FILE}" \
    MOCK_STOP_FAIL_FILE="${STOP_FAIL_FILE}" \
    WORKER_HOLD_SECONDS="${WORKER_HOLD_SECONDS:-1}" \
    "${LAUNCHER}" "$@"
}

wait_for_state()
{
    job_id="$1"
    expected="$2"
    attempts=0
    while [ "${attempts}" -lt 40 ]
    do
        state=$(launcher status "${job_id}" | jq -r '.state // ""')
        [ "${state}" != "${expected}" ] || return 0
        sleep 1
        attempts=$((attempts + 1))
    done
    fail "job ${job_id} did not reach ${expected}"
}

start_job()
{
    target="$1"
    language="$2"
    output=$(launcher start "${target}" standard "${language}")
    printf '%s\n' "${output}" | jq -e '.status=="ok" and .state=="queued"' >/dev/null ||
        fail "job start failed"
    printf '%s\n' "${output}" | jq -r '.job_id'
}

# RUNNING -> STOPPED during the job -> RUNNING after mandatory stage 90.
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job telegram.org en)
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.outcome=="PARTIAL" and .initial_service_state=="RUNNING"' >/dev/null ||
    fail "running-state snapshot was not recorded"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="10" and .status=="PASS")' >/dev/null ||
    fail "snapshot stage did not pass"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="20" and .status=="PASS")' >/dev/null ||
    fail "service-stop stage did not pass"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="PASS")' >/dev/null ||
    fail "restore stage did not pass"
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail "running service was not restored"
[ "$(cat "${CALLS_FILE}")" = "stop
start" ] || fail "running lifecycle did not stop then start exactly once"

# STOPPED -> STOPPED, without an accidental start.
printf '%s\n' STOPPED > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job stopped.example en)
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.initial_service_state=="STOPPED"' >/dev/null ||
    fail "stopped-state snapshot was not recorded"
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail "stopped service was promoted"
[ ! -s "${CALLS_FILE}" ] || fail "stopped service received lifecycle mutations"

# Cancel after service stop: skipped stages retain exact Russian text, stage 90 restores.
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
WORKER_HOLD_SECONDS=10
export WORKER_HOLD_SECONDS
job=$(start_job cancel.example ru)
attempts=0
while [ "$(cat "${STATE_FILE}")" != STOPPED ] && [ "${attempts}" -lt 20 ]
do
    sleep 1
    attempts=$((attempts + 1))
done
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail "cancel test never reached stopped state"
busy=$(launcher start second.example standard en)
printf '%s\n' "${busy}" | jq -e '.status=="busy" and .job_id=="'"${job}"'"' >/dev/null ||
    fail "second start did not report the active job"
launcher cancel "${job}" >/dev/null
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.outcome=="PARTIAL" and .cancel_requested==true' >/dev/null ||
    fail "cancel did not return a partial result"
printf '%s\n' "${result}" | jq -e '[.stages[] | select(.number=="30" or .number=="40" or .number=="50" or .number=="60" or .number=="70" or .number=="80" or .number=="85")] | all(.status=="SKIPPED" and .message=="SKIPPED — отменено")' >/dev/null ||
    fail "canceled unexecuted stages do not use the approved Russian text"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="PASS")' >/dev/null ||
    fail "cancel did not execute mandatory restoration"
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail "cancel did not restore running state"

# English cancellation uses the exact approved spelling and still restores.
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job english-cancel.example en)
attempts=0
while [ "$(cat "${STATE_FILE}")" != STOPPED ] && [ "${attempts}" -lt 20 ]
do
    sleep 1
    attempts=$((attempts + 1))
done
launcher cancel "${job}" >/dev/null
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '[.stages[] | select(.number=="30" or .number=="40" or .number=="50" or .number=="60" or .number=="70" or .number=="80" or .number=="85")] | all(.status=="SKIPPED" and .message=="SKIPPED — canseled")' >/dev/null ||
    fail "canceled unexecuted stages do not use the approved English text"
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail "English cancel did not restore running state"

# Restore failure is explicit and never presented as a normal partial result.
unset WORKER_HOLD_SECONDS
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
: > "${START_FAIL_FILE}"
job=$(start_job restore-failure.example en)
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.outcome=="RESTORE_FAILED"' >/dev/null ||
    fail "restore failure was not explicit"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="FAIL")' >/dev/null ||
    fail "restore stage did not fail"
rm -f "${START_FAIL_FILE}"

# Incomplete initial state aborts before mutation and leaves stage 90 as a no-op success.
printf '%s\n' INCOMPLETE > "${STATE_FILE}"
: > "${CALLS_FILE}"
job=$(start_job incomplete.example en)
wait_for_state "${job}" completed
result=$(launcher result "${job}")
printf '%s\n' "${result}" | jq -e '.outcome=="ERROR" and .initial_service_state==""' >/dev/null ||
    fail "incomplete initial state did not fail closed"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="10" and .status=="FAIL")' >/dev/null ||
    fail "incomplete snapshot stage did not fail"
[ ! -s "${CALLS_FILE}" ] || fail "incomplete initial state was mutated"

# The real service entry point owns the shared fd 9 transaction and permits only
# inherited internal lifecycle calls. Backend behavior is mocked, not the lock path.
SERVICE_ROOT="${TMP_ROOT}/service-root"
SERVICE_BACKEND="${SERVICE_ROOT}/backend"
SERVICE_WORKER="${SERVICE_ROOT}/strategy_lab_worker.sh"
SERVICE_LOCK="${TMP_ROOT}/real-service.lock"
mkdir -p "${SERVICE_BACKEND}"
for module in common config parser registry storage targets target_mode profile_normalizer profile_pipeline exclude blobs ports firewall generator validator atomic stage launcher supervisor
do
    : > "${SERVICE_BACKEND}/${module}.sh"
done
cat > "${SERVICE_BACKEND}/orchestrator.sh" <<'MOCK'
orchestrator_native_status()
{
    case "$(cat "${MOCK_STATE_FILE}")" in
        RUNNING) return 0 ;;
        STOPPED) return 1 ;;
        *) return 2 ;;
    esac
}
orchestrator_native_stop()
{
    printf '%s\n' service-stop >> "${MOCK_CALLS_FILE}"
    printf '%s\n' STOPPED > "${MOCK_STATE_FILE}"
}
orchestrator_native_start() { return 1; }
orchestrator_native_reconfigure() { return 1; }
orchestrator_runtime_failure() { return 0; }
MOCK
cat > "${SERVICE_WORKER}" <<'MOCK'
#!/bin/sh
[ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] || exit 91
( : >&9 ) 2>/dev/null || exit 92
"${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status || exit 93
"${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-stop || exit 94
exit 0
MOCK
chmod +x "${SERVICE_WORKER}"
printf '%s\n' RUNNING > "${STATE_FILE}"
: > "${CALLS_FILE}"
SCRIPT_DIR="${SERVICE_ROOT}" \
BACKEND_DIR="${SERVICE_BACKEND}" \
LOCKF_BIN="${MOCK_BIN}/lockf" \
LIFECYCLE_LOCK_FILE="${SERVICE_LOCK}" \
STRATEGY_LAB_WORKER="${SERVICE_WORKER}" \
MOCK_STATE_FILE="${STATE_FILE}" \
MOCK_CALLS_FILE="${CALLS_FILE}" \
    "${SERVICE_SOURCE}" strategy-lab job.ServiceLock
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail "service-owned transaction did not run under inherited lock"
grep -Fqx service-stop "${CALLS_FILE}" || fail "internal stop action was not dispatched"
set +e
SCRIPT_DIR="${SERVICE_ROOT}" BACKEND_DIR="${SERVICE_BACKEND}" \
LOCKF_BIN="${MOCK_BIN}/lockf" LIFECYCLE_LOCK_FILE="${SERVICE_LOCK}" \
STRATEGY_LAB_WORKER="${SERVICE_WORKER}" MOCK_STATE_FILE="${STATE_FILE}" \
MOCK_CALLS_FILE="${CALLS_FILE}" \
    "${SERVICE_SOURCE}" strategy-lab-stop >/dev/null 2>&1
unauthorized_status=$?
set -e
[ "${unauthorized_status}" -eq 77 ] || fail "internal lifecycle action worked without inherited lock ownership"

idle=$(launcher status)
printf '%s\n' "${idle}" | jq -e '.status=="idle"' >/dev/null || fail "idle state was not reported"
set +e
invalid=$(launcher start 'bad/target' standard en 2>&1)
invalid_status=$?
set -e
[ "${invalid_status}" -eq 64 ] || fail "unsafe target was not rejected"
printf '%s\n' "${invalid}" | grep -Fq 'invalid target' || fail "invalid target reason is missing"

sh -n "${LAUNCHER}"
sh -n "${WORKER}"
sh -n "${MODULE_DIR}/lifecycle.sh"
sh -n "${MODULE_DIR}/state.sh"
sh -n "${SERVICE_SOURCE}"

grep -Fq 'TRANSACTION_SCRIPT="${TRANSACTION_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"' "${LAUNCHER}" ||
    fail "launcher does not enter the service-owned lifecycle transaction"
grep -Fq 'service_with_lifecycle_lock "${STRATEGY_LAB_LOCK_TIMEOUT}"' "${SERVICE_SOURCE}" ||
    fail "Strategy Lab is not protected by the shared lifecycle lock"
grep -Fq 'strategy-lab-status|strategy-lab-stop|strategy-lab-start' "${SERVICE_SOURCE}" ||
    fail "internal lock-owned service actions are missing"
grep -Fq 'STRATEGY_LAB_LIFECYCLE_OWNER=1' "${SERVICE_SOURCE}" ||
    fail "inherited lifecycle ownership is not marked"
grep -Fq '( : >&9 ) 2>/dev/null' "${SERVICE_SOURCE}" ||
    fail "internal service actions do not require inherited lock descriptor 9"
grep -Fq 'RESTORE_FAILED' "${WORKER}" || fail "worker has no explicit restore failure result"

echo 'PASS: Strategy Lab lifecycle snapshot, stop, cancel, cleanup, and restoration contract'
