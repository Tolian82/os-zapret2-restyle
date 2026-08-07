#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-${STRATEGY_LAB_PYTHON_BIN:-python3.13}}
PYTHON_LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
ORCHESTRATOR="${ZAPRET_DIR}/strategy_lab_py/orchestrator.py"
WORKER="${ZAPRET_DIR}/strategy_lab_worker.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-time-budget.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail 'Python 3.13 runtime is unavailable'
"${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)' ||
    fail 'Strategy Lab time-budget test requires Python 3.13'

RUN_DIR="${TEST_ROOT}/run"
JOBS_DIR="${RUN_DIR}/jobs"
CLOCK_FILE="${TEST_ROOT}/clock"
mkdir -p "${JOBS_DIR}"
export STRATEGY_LAB_RUN_DIR="${RUN_DIR}"
export STRATEGY_LAB_JOBS_DIR="${JOBS_DIR}"
export STRATEGY_LAB_NOW_EPOCH_FILE="${CLOCK_FILE}"
export STRATEGY_LAB_STANDARD_BUDGET=150
export STRATEGY_LAB_EXTENDED_BUDGET=120
export STRATEGY_LAB_STAGE80_TIMEOUT=120

initialize_job()
{
    _job="$1"
    _mode="$2"
    _jobdir="${JOBS_DIR}/${_job}"
    mkdir -p "${_jobdir}"
    STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" "${PYTHON_LAUNCHER}" state initialize \
        "${_job}" "${_jobdir}/status.json" "${_jobdir}/events.ndjson" budget.example "${_mode}" en
}

initialize_job job.BUDGET standard
printf '%s\n' 1000 > "${CLOCK_FILE}"
PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path
from strategy_lab_py.orchestrator import Budget, StageTimedOut

state = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / "job.BUDGET" / "status.json"
clock = Path(os.environ["STRATEGY_LAB_NOW_EPOCH_FILE"])
budget = Budget("standard", state, "job.BUDGET")
budget.record_initial()
value = json.loads(state.read_text(encoding="utf-8"))
assert value["started_at"] == "1970-01-01T00:16:40Z"
assert value["standard_deadline_at"] == "1970-01-01T00:19:10Z"
assert value["deadline_at"] == "1970-01-01T00:19:10Z"
assert value["standard_budget_seconds"] == 150
assert value["extended_budget_seconds"] == 120
assert value["search_budget_seconds"] == 150
assert value["stage80_budget_seconds"] == 120
clock.write_text("1110\n", encoding="utf-8")
assert budget.timeout_for("60", 60) == 40
clock.write_text("1149\n", encoding="utf-8")
assert budget.timeout_for("70", 60) == 1
clock.write_text("1150\n", encoding="utf-8")
try:
    budget.timeout_for("70", 60)
except StageTimedOut as exc:
    assert exc.stage == "70"
else:
    raise AssertionError("expired standard deadline still produced an operation timeout")
PY

rm -rf "${JOBS_DIR}/job.BUDGET"
initialize_job job.BUDGET extended
printf '%s\n' 2000 > "${CLOCK_FILE}"
PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path
from strategy_lab_py.orchestrator import Budget, StageTimedOut

state = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / "job.BUDGET" / "status.json"
clock = Path(os.environ["STRATEGY_LAB_NOW_EPOCH_FILE"])
budget = Budget("extended", state, "job.BUDGET")
budget.record_initial()
value = json.loads(state.read_text(encoding="utf-8"))
assert value["started_at"] == "1970-01-01T00:33:20Z"
assert value["standard_deadline_at"] == "1970-01-01T00:35:50Z"
assert value["deadline_at"] == "1970-01-01T00:37:50Z"
assert value["search_budget_seconds"] == 270
clock.write_text("2140\n", encoding="utf-8")
assert budget.timeout_for("70", 60) == 10
clock.write_text("2150\n", encoding="utf-8")
budget.begin_stage80()
value = json.loads(state.read_text(encoding="utf-8"))
assert value["stage80_started_at"] == "1970-01-01T00:35:50Z"
assert value["stage80_deadline_at"] == "1970-01-01T00:37:50Z"
assert budget.timeout_for("80", 120) == 120
clock.write_text("2220\n", encoding="utf-8")
assert budget.timeout_for("80", 120) == 50
clock.write_text("2269\n", encoding="utf-8")
assert budget.timeout_for("80", 120) == 1
clock.write_text("2270\n", encoding="utf-8")
try:
    budget.timeout_for("80", 120)
except StageTimedOut as exc:
    assert exc.stage == "80"
else:
    raise AssertionError("expired shared stage-80 deadline still produced a timeout")
try:
    budget.require("85")
except StageTimedOut as exc:
    assert exc.stage == "85"
else:
    raise AssertionError("shortlist was allowed after the extended overall deadline")
PY

grep -Fq '"STRATEGY_LAB_STANDARD_BUDGET": 150' "${ORCHESTRATOR}" ||
    fail 'Python standard budget default is missing'
grep -Fq '"STRATEGY_LAB_EXTENDED_BUDGET": 120' "${ORCHESTRATOR}" ||
    fail 'Python extended budget default is missing'
grep -Fq 'self.stage80_deadline = min(now + self.stage80_limit, self.overall_deadline)' "${ORCHESTRATOR}" ||
    fail 'Python stage 80 does not establish one shared bounded deadline'
grep -Fq 'return min(operation_limit, remaining)' "${ORCHESTRATOR}" ||
    fail 'Python operation timeout is not clipped to the remaining absolute deadline'
grep -Fq 'exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"' "${WORKER}" ||
    fail 'production worker does not delegate budget ownership to Python'
! grep -Fq 'worker_budget' "${WORKER}" ||
    fail 'production worker still loads the retired shell budget owner'

"${PYTHON_BIN}" -m py_compile "${ORCHESTRATOR}"
sh -n "${WORKER}"

echo 'PASS: Python Strategy Lab owns the absolute overall deadline and shared stage-80 budget contract'
