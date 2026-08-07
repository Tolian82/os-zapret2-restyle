#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${ZAPRET_DIR}/strategy_lab"
ORCHESTRATOR="${ZAPRET_DIR}/strategy_lab_py/orchestrator.py"
WORKER="${ZAPRET_DIR}/strategy_lab_worker.sh"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-${STRATEGY_LAB_PYTHON_BIN:-python3.13}}
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-terminal-result.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

# Keep the retired shell terminal helper under compatibility coverage until Patch 7
# removes obsolete shell orchestration modules. It is no longer the production owner.
run_legacy_case()
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
        strategy_lab_set_circular_eligibility(){ :; }
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
        "${_case_dir}/result.json" >/dev/null || fail "${_case}: legacy terminal state mapping is invalid"
    "$(command -v jq)" -r '.message' "${_case_dir}/result.json" |
        grep -Fq "${_message_fragment}" || fail "${_case}: legacy terminal message is not truthful"
    grep -Fq "99|${_expected_report}|" "${_case_dir}/stages" ||
        fail "${_case}: legacy stage 99 status is invalid"
}

run_legacy_case standard-success en standard SEARCH false true 2 completed SUCCESS \
    'Standard search completed with 2 stable working strategies' PASS
run_legacy_case extended-success en extended SEARCH false true 1 completed SUCCESS \
    'Extended search completed with 1 stable working strategies' PASS
run_legacy_case standard-no-candidate en standard SEARCH false true 0 completed NO_CANDIDATE \
    'no stable working strategy was found' PASS
run_legacy_case accessible ru standard TARGET_ACCESSIBLE false true 0 completed TARGET_ACCESSIBLE \
    'Цель доступна без обхода' PASS
run_legacy_case canceled en standard PARTIAL true true 0 completed PARTIAL \
    'Test canceled' PASS
run_legacy_case prerequisite ru standard PARTIAL false true 0 completed PARTIAL \
    'Поиск завершён не полностью' PASS
run_legacy_case timeout en extended TIMEOUT false true 0 error TIMEOUT \
    'time limit was reached' FAIL
run_legacy_case internal-error ru standard ERROR false true 0 error ERROR \
    'Внутренняя ошибка Strategy Lab' FAIL
run_legacy_case restore-failed en standard SUCCESS false false 2 error RESTORE_FAILED \
    'original Zapret2 state could not be restored' FAIL

# Patch 3 production authority: terminal mapping and localized terminal messages are Python-owned.
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail 'Python 3.13 runtime is unavailable'
PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
from strategy_lab_py.orchestrator import terminal_message, terminal_report_status, terminal_state

cases = [
    ("SUCCESS", False, "completed", "PASS"),
    ("NO_CANDIDATE", False, "completed", "PASS"),
    ("TARGET_ACCESSIBLE", False, "completed", "PASS"),
    ("PARTIAL", True, "completed", "PASS"),
    ("TIMEOUT", False, "error", "FAIL"),
    ("ERROR", False, "error", "FAIL"),
    ("RESTORE_FAILED", False, "error", "FAIL"),
]
for outcome, _canceled, expected_state, expected_report in cases:
    assert terminal_state(outcome) == expected_state
    assert terminal_report_status(outcome) == expected_report

assert "Standard search completed with 2 stable working strategies" in terminal_message("en", "standard", "SUCCESS", False, 2)
assert "Extended search completed with 1 stable working strategies" in terminal_message("en", "extended", "SUCCESS", False, 1)
assert "no stable working strategy was found" in terminal_message("en", "standard", "NO_CANDIDATE", False, 0)
assert "Цель доступна без обхода" in terminal_message("ru", "standard", "TARGET_ACCESSIBLE", False, 0)
assert "Test canceled" in terminal_message("en", "standard", "PARTIAL", True, 0)
assert "Поиск завершён не полностью" in terminal_message("ru", "standard", "PARTIAL", False, 0)
assert "time limit was reached" in terminal_message("en", "extended", "TIMEOUT", False, 0)
assert "Внутренняя ошибка Strategy Lab" in terminal_message("ru", "standard", "ERROR", False, 0)
assert "original Zapret2 state could not be restored" in terminal_message("en", "standard", "RESTORE_FAILED", False, 0)
PY

FLOW="${MODULE_DIR}/worker_flow.sh"
CONTROL="${MODULE_DIR}/worker_control.sh"

grep -Fq 'worker_finish_search' "${FLOW}" || fail 'legacy worker flow does not retain result-classification compatibility'
! grep -Fq 'PARTIAL_FINAL_MESSAGE' "${FLOW}" || fail 'legacy worker flow still uses load-order final message'
! grep -Fq 'PARTIAL_FINAL_MESSAGE' "${CONTROL}" || fail 'legacy worker control still uses the partial final-message override'
! grep -Fq 'ERROR_FINAL_MESSAGE' "${CONTROL}" || fail 'legacy worker control still uses the error final-message override'
! grep -Fq 'TIMEOUT_FINAL_MESSAGE' "${CONTROL}" || fail 'legacy worker control still uses the timeout final-message override'
! grep -Fq 'CANCEL_FINAL_MESSAGE' "${CONTROL}" || fail 'legacy worker control still uses the cancel final-message override'

grep -Fq 'exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"' "${WORKER}" ||
    fail 'production worker does not delegate terminal policy to Python'
! grep -Fq 'worker_result' "${WORKER}" ||
    fail 'production worker still loads the retired shell terminal-result owner'
grep -Fq 'def terminal_state(outcome: str)' "${ORCHESTRATOR}" ||
    fail 'Python terminal state mapping is missing'
grep -Fq 'def terminal_report_status(outcome: str)' "${ORCHESTRATOR}" ||
    fail 'Python terminal report mapping is missing'
grep -Fq 'def terminal_message(language: str, mode: str, outcome: str, canceled: bool, count: int = 0)' "${ORCHESTRATOR}" ||
    fail 'Python localized terminal message mapping is missing'
grep -Fq 'outcome = self._restore(outcome)' "${ORCHESTRATOR}" ||
    fail 'Python finalization does not enforce restoration before terminal persistence'
grep -Fq 'outcome = "RESTORE_FAILED"' "${ORCHESTRATOR}" ||
    fail 'Python restoration failure does not override the prior outcome'
grep -Fq 'strategy_lab_udp_input_cleanup(){ :; }' "$0" || fail 'legacy terminal fixture does not mock UDP cleanup explicitly'
grep -Fq 'strategy_lab_set_circular_eligibility(){ :; }' "$0" || fail 'legacy terminal fixture does not mock circular eligibility persistence explicitly'

"${PYTHON_BIN}" -m py_compile "${ORCHESTRATOR}"
sh -n "${WORKER}"

echo 'PASS: Python owns Strategy Lab terminal state/outcome/report/localization/finalization while legacy shell result helpers remain compatibility-only'
