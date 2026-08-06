#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-terminal-result.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

run_case()
{
    _case="$1"
    _language="$2"
    _mode="$3"
    _requested_outcome="$4"
    _canceled="$5"
    _restore_ok="$6"
    _count="$7"
    _expected_state="$8"
    _expected_outcome="$9"
    shift 9
    _message_fragment="$1"
    _expected_report="$2"

    _case_dir="${TEST_ROOT}/${_case}"
    mkdir -p "${_case_dir}/job"
    printf '{"count":%s,"items":[]}\n' "${_count}" > "${_case_dir}/job/shortlist.json"

    (
        LANGUAGE="${_language}"
        MODE="${_mode}"
        JOB_ID=job.TEST
        JOB_DIR="${_case_dir}/job"
        STRATEGY_LAB_JQ=$(command -v jq)
        STRATEGY_LAB_INITIAL_SERVICE_STATE=RUNNING
        WORKER_FINALIZING=0
        export LANGUAGE MODE JOB_ID JOB_DIR STRATEGY_LAB_JQ

        . "${MODULE_DIR}/worker_messages.sh"
        . "${MODULE_DIR}/worker_result.sh"

        strategy_lab_restore_initial_service_state()
        {
            [ "${_restore_ok}" = true ]
        }
        strategy_lab_update_stage()
        {
            printf '%s|%s|%s\n' "$2" "$3" "$4" >> "${_case_dir}/stages"
        }
        strategy_lab_append_event(){ :; }
        strategy_lab_update_job()
        {
            "${STRATEGY_LAB_JQ}" -nc \
                --arg state "$2" --arg outcome "$3" --arg stage "$4" \
                --argjson canceled "$5" --arg message "$6" \
                '{state:$state,outcome:$outcome,current_stage:$stage,cancel_requested:$canceled,message:$message}' \
                > "${_case_dir}/result.json"
        }
        strategy_lab_status_file()
        {
            printf '%s\n' "${_case_dir}/result.json"
        }
        strategy_lab_clear_active_job(){ :; }
        strategy_lab_udp_input_cleanup(){ :; }
        worker_skip_unfinished(){ :; }

        . "${MODULE_DIR}/worker_control.sh"

        if [ "${_requested_outcome}" = SEARCH ]; then
            worker_finish_search
        else
            worker_finish "${_requested_outcome}" "${_canceled}"
        fi
    )

    "$(command -v jq)" -e \
        --arg state "${_expected_state}" \
        --arg outcome "${_expected_outcome}" \
        --argjson canceled "${_canceled}" \
        '.state==$state and .outcome==$outcome and .current_stage=="99" and .cancel_requested==$canceled' \
        "${_case_dir}/result.json" >/dev/null || fail "${_case}: terminal state mapping is invalid"
    "$(command -v jq)" -r '.message' "${_case_dir}/result.json" |
        grep -Fq "${_message_fragment}" || fail "${_case}: terminal message is not truthful"
    grep -Fq "99|${_expected_report}|" "${_case_dir}/stages" ||
        fail "${_case}: stage 99 status is invalid"
}

run_case standard-success en standard SEARCH false true 2 completed SUCCESS \
    'Standard search completed with 2 stable working strategies' PASS
run_case extended-success en extended SEARCH false true 1 completed SUCCESS \
    'Extended search completed with 1 stable working strategies' PASS
run_case standard-no-candidate en standard SEARCH false true 0 completed NO_CANDIDATE \
    'no stable working strategy was found' PASS
run_case accessible ru standard TARGET_ACCESSIBLE false true 0 completed TARGET_ACCESSIBLE \
    'Цель доступна без обхода' PASS
run_case canceled en standard PARTIAL true true 0 completed PARTIAL \
    'Test canceled' PASS
run_case prerequisite ru standard PARTIAL false true 0 completed PARTIAL \
    'Поиск завершён не полностью' PASS
run_case timeout en extended TIMEOUT false true 0 error TIMEOUT \
    'time limit was reached' FAIL
run_case internal-error ru standard ERROR false true 0 error ERROR \
    'Внутренняя ошибка Strategy Lab' FAIL
run_case restore-failed en standard SUCCESS false false 2 error RESTORE_FAILED \
    'original Zapret2 state could not be restored' FAIL

FLOW="${MODULE_DIR}/worker_flow.sh"
CONTROL="${MODULE_DIR}/worker_control.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"

grep -Fq 'worker_finish_search' "${FLOW}" || fail 'normal worker flow does not classify search results'
! grep -Fq 'PARTIAL_FINAL_MESSAGE' "${FLOW}" || fail 'worker flow still uses load-order final message'
! grep -Fq 'PARTIAL_FINAL_MESSAGE' "${CONTROL}" || fail 'worker control still uses the partial final-message override'
! grep -Fq 'ERROR_FINAL_MESSAGE' "${CONTROL}" || fail 'worker control still uses the error final-message override'
! grep -Fq 'TIMEOUT_FINAL_MESSAGE' "${CONTROL}" || fail 'worker control still uses the timeout final-message override'
! grep -Fq 'CANCEL_FINAL_MESSAGE' "${CONTROL}" || fail 'worker control still uses the cancel final-message override'
grep -Fq 'worker_result' "${WORKER}" || fail 'worker does not load the result contract'
grep -Fq 'strategy_lab_udp_input_cleanup(){ :; }' "$0" || fail 'terminal fixture does not mock UDP cleanup explicitly'

echo 'PASS: Strategy Lab terminal state, outcome, report status, localized messages, and cleanup fixture are truthful'
