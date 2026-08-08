#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMMON_UNDER_TEST="${COMMON_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/common.sh}"
STATE_UNDER_TEST="${STATE_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/state.sh}"
RETIRED_STAGE_MACHINE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_stage_machine.sh"
ORCHESTRATOR_UNDER_TEST="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/orchestrator.py"
PYTHON_LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python_launcher.sh"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
ROOT=$(mktemp -d /tmp/strategy-lab-state-race.XXXXXX)
trap 'rm -rf "${ROOT}"' EXIT HUP INT TERM

STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_RUN_DIR="${ROOT}/run"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_RUN_DIR}/jobs"
STRATEGY_LAB_LOG_DIR="${ROOT}/log"
STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}"
STRATEGY_LAB_PYTHON_LAUNCHER="${PYTHON_LAUNCHER}"
export STRATEGY_LAB_JQ STRATEGY_LAB_RUN_DIR STRATEGY_LAB_JOBS_DIR
export STRATEGY_LAB_LOG_DIR STRATEGY_LAB_PYTHON_BIN STRATEGY_LAB_PYTHON_LAUNCHER

. "${COMMON_UNDER_TEST}"
. "${STATE_UNDER_TEST}"

strategy_lab_prepare_directories
strategy_lab_initialize_state job.race example.com standard en
status=$(strategy_lab_status_file job.race)

iteration=1
while [ "${iteration}" -le 20 ]
do
    strategy_lab_set_initial_service_state job.race "RUNNING-${iteration}" &
    iteration=$((iteration + 1))
done
wait
[ "$("${STRATEGY_LAB_JQ}" -r '.revision' "${status}")" -eq 20 ]

strategy_lab_update_stage job.race 60 RUNNING active
[ "$("${STRATEGY_LAB_JQ}" -r '.revision' "${status}")" -eq 21 ]

# Cancel persistence and unfinished-stage skipping mutate the same status document
# concurrently and must therefore share the Python state lock and revision owner.
strategy_lab_request_cancel job.race cancel &
strategy_lab_skip_unfinished job.race skipped &
wait

"${STRATEGY_LAB_JQ}" -e '
    .state=="cancel_requested" and
    .cancel_requested==true and
    ((.cancel_requested_at // "")|length)>0 and
    (.stages[] | select(.number=="60") | .status)=="SKIPPED" and
    (.stages[] | select(.number=="90") | .status)=="PENDING" and
    (.stages[] | select(.number=="99") | .status)=="PENDING" and
    .revision==23
' "${status}" >/dev/null
cancel_at=$("${STRATEGY_LAB_JQ}" -r '.cancel_requested_at' "${status}")

# Repeated cancel is idempotent in value while still being a serialized revisioned write.
strategy_lab_skip_unfinished job.race skipped-again &
strategy_lab_request_cancel job.race cancel-again &
wait
"${STRATEGY_LAB_JQ}" -e --arg requested_at "${cancel_at}" '
    .state=="cancel_requested" and
    .cancel_requested==true and
    .cancel_requested_at==$requested_at and
    .revision==25
' "${status}" >/dev/null

strategy_lab_update_job job.race completed PARTIAL 99 true done
"${STRATEGY_LAB_JQ}" -e --arg requested_at "${cancel_at}" '
    .state=="completed" and
    .outcome=="PARTIAL" and
    .current_stage=="99" and
    .cancel_requested==true and
    .cancel_requested_at==$requested_at and
    .revision==26
' "${status}" >/dev/null

strategy_lab_request_cancel job.race late
strategy_lab_update_stage job.race 50 RUNNING late
"${STRATEGY_LAB_JQ}" -e --arg requested_at "${cancel_at}" '
    .state=="completed" and
    .outcome=="PARTIAL" and
    .current_stage=="99" and
    .cancel_requested_at==$requested_at and
    (.stages[] | select(.number=="50") | .status)!="RUNNING" and
    .revision==28
' "${status}" >/dev/null

# Migration Patch 7 removed the shell stage-machine owner. Unfinished-stage persistence
# is now reached directly through the shell state compatibility adapter into Python.
[ ! -e "${RETIRED_STAGE_MACHINE}" ]
grep -Fq 'strategy_lab_state_python skip-unfinished' "${STATE_UNDER_TEST}"
! grep -Fq 'strategy_lab_state_transform' "${STATE_UNDER_TEST}"
grep -Fq 'self._skip(' "${ORCHESTRATOR_UNDER_TEST}"

"${STRATEGY_LAB_JQ}" -e . "${status}" >/dev/null
"${PYTHON_BIN}" -m py_compile "${ORCHESTRATOR_UNDER_TEST}"

echo 'PASS: cancel, skip, and finalization state updates share the Python lock/revision owner after shell stage-machine retirement'
