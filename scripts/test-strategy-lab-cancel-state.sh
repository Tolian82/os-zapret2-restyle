#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-cancel-state.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_RUN_DIR="${TEST_ROOT}/run"
STRATEGY_LAB_LOG_DIR="${TEST_ROOT}/log"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_RUN_DIR}/jobs"
STRATEGY_LAB_ACTIVE_FILE="${STRATEGY_LAB_RUN_DIR}/active.job"
export STRATEGY_LAB_JQ STRATEGY_LAB_RUN_DIR STRATEGY_LAB_LOG_DIR
export STRATEGY_LAB_JOBS_DIR STRATEGY_LAB_ACTIVE_FILE

. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/state.sh"

usage_error()
{
    echo "ERROR: $1" >&2
    return 64
}

emit_error_json()
{
    "${STRATEGY_LAB_JQ}" -nc --arg message "$1" '{status:"error",message:$message}'
}

cleanup_stale_active()
{
    :
}

. "${MODULE_DIR}/query.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

assert_cancelled()
{
    _status="$1"
    _message="$2"
    "${STRATEGY_LAB_JQ}" -e \
        --arg message "${_message}" \
        '.state=="cancel_requested" and
         .cancel_requested==true and
         ((.cancel_requested_at | type)=="string") and
         ((.cancel_requested_at | length)>0) and
         .message==$message' \
        "${_status}" >/dev/null || fail "persisted cancellation state is invalid"
}

strategy_lab_prepare_directories

job=job.CANCEL
strategy_lab_initialize_state "${job}" example.com standard en
strategy_lab_update_job "${job}" running '' 60 false 'Expansion is running'
status=$(strategy_lab_status_file "${job}")
cancel_file=$(strategy_lab_cancel_file "${job}")

cancel_job cancel "${job}" > "${TEST_ROOT}/first.json"
[ -f "${cancel_file}" ] || fail "cancel control file was not created"
assert_cancelled "${status}" 'Cancellation requested'
cmp -s "${TEST_ROOT}/first.json" "${status}" || fail "cancel response is not the persisted snapshot"
first_timestamp=$("${STRATEGY_LAB_JQ}" -r '.cancel_requested_at' "${status}")

cancel_job cancel "${job}" > "${TEST_ROOT}/second.json"
cmp -s "${TEST_ROOT}/second.json" "${status}" || fail "repeated cancel response is not persisted state"
[ "$("${STRATEGY_LAB_JQ}" -r '.cancel_requested_at' "${status}")" = "${first_timestamp}" ] ||
    fail "repeated cancel changed the original request timestamp"

strategy_lab_update_job "${job}" running '' 70 false 'Late worker update'
read_job_json "${job}" > "${TEST_ROOT}/refreshed.json"
assert_cancelled "${status}" 'Cancellation requested'
cmp -s "${TEST_ROOT}/refreshed.json" "${status}" || fail "polling did not return refreshed persisted state"

(
    _iteration=0
    while [ "${_iteration}" -lt 20 ]
    do
        read_job_json "${job}" | "${STRATEGY_LAB_JQ}" -e . >/dev/null
        _iteration=$((_iteration + 1))
    done
) &
reader_pid=$!
_iteration=0
while [ "${_iteration}" -lt 20 ]
do
    cancel_job cancel "${job}" | "${STRATEGY_LAB_JQ}" -e . >/dev/null
    _iteration=$((_iteration + 1))
done
wait "${reader_pid}"
assert_cancelled "${status}" 'Cancellation requested'

ru_job=job.RUS
strategy_lab_initialize_state "${ru_job}" example.org standard ru
strategy_lab_update_job "${ru_job}" running '' 40 false 'Работает'
ru_status=$(strategy_lab_status_file "${ru_job}")
cancel_job cancel "${ru_job}" > "${TEST_ROOT}/ru.json"
assert_cancelled "${ru_status}" 'Запрошена остановка'
cmp -s "${TEST_ROOT}/ru.json" "${ru_status}" || fail "Russian cancel response is not persisted state"

done_job=job.DONE
strategy_lab_initialize_state "${done_job}" example.net standard en
strategy_lab_update_job "${done_job}" completed SUCCESS 99 false 'Done'
done_status=$(strategy_lab_status_file "${done_job}")
done_cancel=$(strategy_lab_cancel_file "${done_job}")
cancel_job cancel "${done_job}" > "${TEST_ROOT}/done.json"
[ ! -e "${done_cancel}" ] || fail "terminal job received a cancel control file"
"${STRATEGY_LAB_JQ}" -e \
    '.state=="completed" and .outcome=="SUCCESS" and
     .cancel_requested==false and .cancel_requested_at=="" and .message=="Done"' \
    "${done_status}" >/dev/null || fail "terminal job was mutated by cancel"
cmp -s "${TEST_ROOT}/done.json" "${done_status}" || fail "terminal cancel did not return unchanged state"

if find "${STRATEGY_LAB_JOBS_DIR}" -type f \
    \( -name '.cancel-state.*' -o -name '.strategy-lab.*' \) | grep -q .
then
    fail "temporary cancellation state file was left behind"
fi

echo 'PASS: Strategy Lab cancellation is persistent, localized, atomic, and idempotent'
