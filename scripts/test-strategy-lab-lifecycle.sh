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


. "${ROOT_DIR}/scripts/lib/test-strategy-lab-lifecycle-mocks.sh"

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
    STRATEGY_LAB_CURL_BIN="${MOCK_BIN}/curl" \
    STRATEGY_LAB_DRILL_BIN="${MOCK_BIN}/drill" \
    STRATEGY_LAB_NETSTAT_BIN="${MOCK_BIN}/netstat" \
    STRATEGY_LAB_OPENSSL_BIN="${MOCK_BIN}/openssl" \
    STRATEGY_LAB_NC_BIN="${MOCK_BIN}/nc" \
    CANDIDATE_RUNNER="${MOCK_BIN}/candidate" \
    STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${MOCK_BIN}/candidate" \
    MOCK_IPV6_ROUTE="${MOCK_IPV6_ROUTE:-0}" \
    MOCK_QUIC_STATUS="${MOCK_QUIC_STATUS:-124}" \
    MOCK_NC_STATUS="${MOCK_NC_STATUS:-1}" \
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
        status=$(launcher status "${job_id}")
        state=$(printf '%s\n' "${status}" | jq -r '.state // ""')
        [ "${state}" != "${expected}" ] || return 0
        case "${state}" in
            completed|error)
                printf '%s\n' "${status}" >&2
                log_file="${LOG_DIR}/${job_id}.log"
                if [ -r "${log_file}" ]; then
                    echo "--- ${log_file} ---" >&2
                    cat "${log_file}" >&2
                fi
                fail "job ${job_id} reached unexpected terminal state ${state}; expected ${expected}"
                ;;
        esac
        sleep 1
        attempts=$((attempts + 1))
    done
    status=$(launcher status "${job_id}" || true)
    printf '%s\n' "${status}" >&2
    log_file="${LOG_DIR}/${job_id}.log"
    if [ -r "${log_file}" ]; then
        echo "--- ${log_file} ---" >&2
        cat "${log_file}" >&2
    fi
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


. "${ROOT_DIR}/scripts/lib/test-strategy-lab-lifecycle-cases.sh"
