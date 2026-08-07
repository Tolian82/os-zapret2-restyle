#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${ZAPRET_DIR}/strategy_lab"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-time-budget.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

JOB_ID=job.BUDGET
STRATEGY_LAB_RUN_DIR="${TEST_ROOT}/run"
STRATEGY_LAB_LOG_DIR="${TEST_ROOT}/log"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_RUN_DIR}/jobs"
STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_NOW_EPOCH_FILE="${TEST_ROOT}/clock"
STRATEGY_LAB_STANDARD_BUDGET=150
STRATEGY_LAB_EXTENDED_BUDGET=120
STRATEGY_LAB_STAGE80_TIMEOUT=120
STRATEGY_LAB_PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-${STRATEGY_LAB_PYTHON_BIN:-python3.13}}
STRATEGY_LAB_PYTHON_LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
export STRATEGY_LAB_RUN_DIR STRATEGY_LAB_LOG_DIR STRATEGY_LAB_JOBS_DIR STRATEGY_LAB_JQ
export STRATEGY_LAB_NOW_EPOCH_FILE STRATEGY_LAB_STANDARD_BUDGET STRATEGY_LAB_EXTENDED_BUDGET
export STRATEGY_LAB_STAGE80_TIMEOUT STRATEGY_LAB_PYTHON_BIN STRATEGY_LAB_PYTHON_LAUNCHER

. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/state.sh"
. "${MODULE_DIR}/worker_budget.sh"

strategy_lab_prepare_directories
JOB_DIR=$(strategy_lab_job_dir "${JOB_ID}")
STATUS_FILE=$(strategy_lab_status_file "${JOB_ID}")

set_clock()
{
    printf '%s\n' "$1" > "${STRATEGY_LAB_NOW_EPOCH_FILE}"
}

reset_status()
{
    _tb_mode="$1"
    rm -rf "${JOB_DIR}"
    strategy_lab_initialize_state "${JOB_ID}" budget.example "${_tb_mode}" en
}

MODE=standard
reset_status "${MODE}"
set_clock 1000
worker_budget_initialize || fail 'standard budget initialization failed'
"${STRATEGY_LAB_JQ}" -e '
    .started_at=="1970-01-01T00:16:40Z" and
    .standard_deadline_at=="1970-01-01T00:19:10Z" and
    .deadline_at=="1970-01-01T00:19:10Z" and
    .standard_budget_seconds==150 and
    .extended_budget_seconds==120 and
    .search_budget_seconds==150 and
    .stage80_budget_seconds==120
' "${STATUS_FILE}" >/dev/null || fail 'standard absolute deadline metadata is invalid'

set_clock 1110
[ "$(worker_budget_timeout_for 60 60)" = 40 ] ||
    fail 'standard operation was not clipped to the remaining overall budget'
set_clock 1149
[ "$(worker_budget_timeout_for 70 60)" = 1 ] ||
    fail 'one-second standard remainder was not preserved'
set_clock 1150
if worker_budget_timeout_for 70 60 >/dev/null 2>&1; then
    fail 'expired standard deadline still produced an operation timeout'
fi

MODE=extended
reset_status "${MODE}"
set_clock 2000
worker_budget_initialize || fail 'extended budget initialization failed'
"${STRATEGY_LAB_JQ}" -e '
    .started_at=="1970-01-01T00:33:20Z" and
    .standard_deadline_at=="1970-01-01T00:35:50Z" and
    .deadline_at=="1970-01-01T00:37:50Z" and
    .search_budget_seconds==270
' "${STATUS_FILE}" >/dev/null || fail 'extended absolute deadline metadata is invalid'

set_clock 2140
[ "$(worker_budget_timeout_for 70 60)" = 10 ] ||
    fail 'stage 70 did not remain bounded by the standard 150-second phase'
set_clock 2150
worker_budget_begin_stage80 || fail 'stage 80 did not begin at the extended allowance boundary'
"${STRATEGY_LAB_JQ}" -e '
    .stage80_started_at=="1970-01-01T00:35:50Z" and
    .stage80_deadline_at=="1970-01-01T00:37:50Z"
' "${STATUS_FILE}" >/dev/null || fail 'shared stage-80 deadline metadata is invalid'
[ "$(worker_budget_timeout_for 80 120)" = 120 ] ||
    fail 'first stage-80 branch did not receive the shared initial remainder'

set_clock 2220
[ "$(worker_budget_timeout_for 80 120)" = 50 ] ||
    fail 'second stage-80 branch received a fresh timeout instead of shared remainder'
set_clock 2269
[ "$(worker_budget_timeout_for 80 120)" = 1 ] ||
    fail 'final stage-80 branch did not receive the last shared second'
set_clock 2270
if worker_budget_timeout_for 80 120 >/dev/null 2>&1; then
    fail 'expired shared stage-80 deadline still produced a timeout'
fi
if worker_budget_require 85 >/dev/null 2>&1; then
    fail 'shortlist was allowed after the extended overall deadline'
fi

FLOW="${MODULE_DIR}/worker_flow.sh"
STAGE_MACHINE="${MODULE_DIR}/worker_stage_machine.sh"
WORKER="${ZAPRET_DIR}/strategy_lab_worker.sh"

grep -Fq 'worker_budget_initialize' "${FLOW}" || fail 'worker flow does not initialize the overall budget'
grep -Fq 'worker_budget_timeout_for 30' "${FLOW}" || fail 'stage 30 is not clipped by the overall budget'
grep -Fq 'worker_budget_timeout_for 50' "${FLOW}" || fail 'stage 50 is not clipped by the overall budget'
grep -Fq 'worker_budget_begin_stage80' "${STAGE_MACHINE}" || fail 'stage 80 does not establish one shared deadline'
grep -Fq 'worker_budget_timeout_for 80' "${STAGE_MACHINE}" || fail 'stage-80 branches do not consume a shared remainder'
grep -Fq 'worker_budget_require 85' "${STAGE_MACHINE}" || fail 'shortlist is not bounded by the overall deadline'
grep -Fq 'STRATEGY_LAB_STANDARD_BUDGET' "${WORKER}" || fail 'worker standard budget default is missing'
grep -Fq 'STRATEGY_LAB_EXTENDED_BUDGET' "${WORKER}" || fail 'worker extended budget default is missing'
grep -Fq 'strategy_lab_state_python set-budget' "${MODULE_DIR}/worker_budget.sh" ||
    fail 'budget metadata does not use the Python state owner'
grep -Fq 'strategy_lab_state_python set-stage80-budget' "${MODULE_DIR}/worker_budget.sh" ||
    fail 'stage-80 budget metadata does not use the Python state owner'

sh -n "${MODULE_DIR}/worker_budget.sh"
sh -n "${FLOW}"
sh -n "${STAGE_MACHINE}"
sh -n "${WORKER}"

echo 'PASS: Strategy Lab absolute overall deadline and shared stage-80 budget contract'
