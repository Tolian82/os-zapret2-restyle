#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
PYTHON_LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
ORCHESTRATOR="${ZAPRET_DIR}/strategy_lab_py/orchestrator.py"
RESOURCES="${ZAPRET_DIR}/strategy_lab_py/resources.py"
WORKER="${ZAPRET_DIR}/strategy_lab_worker.sh"
ADAPTER="${ZAPRET_DIR}/strategy_lab_stage_adapter.sh"
COMMON="${ZAPRET_DIR}/strategy_lab/common.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-python-orchestration.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail "Python 3.13 test runtime is unavailable"
"${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)' ||
    fail "Python test runtime is not 3.13"
"${PYTHON_BIN}" -m py_compile "${ORCHESTRATOR}" "${RESOURCES}"
sh -n "${ADAPTER}"
sh -n "${WORKER}"

PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
from strategy_lab_py.orchestrator import DEFAULT_LIMITS, terminal_message, terminal_report_status, terminal_state

assert DEFAULT_LIMITS["STRATEGY_LAB_STAGE40_TIMEOUT"] == 20
assert terminal_state("SUCCESS") == "completed"
assert terminal_state("PARTIAL") == "completed"
assert terminal_state("TIMEOUT") == "error"
assert terminal_state("ERROR") == "error"
assert terminal_state("RESTORE_FAILED") == "error"
assert terminal_report_status("SUCCESS") == "PASS"
assert terminal_report_status("NO_CANDIDATE") == "PASS"
assert terminal_report_status("RESTORE_FAILED") == "FAIL"
assert terminal_message("en", "standard", "SUCCESS", False, 2) == "SUCCESS — Standard search completed with 2 stable working strategies."
assert terminal_message("ru", "extended", "NO_CANDIDATE", False) == "NO_CANDIDATE — Расширенный поиск завершён; стабильная рабочая стратегия не найдена."
assert terminal_message("en", "standard", "PARTIAL", True) == "PARTIAL — Test canceled; completed stage results were preserved."
PY

RUN_DIR="${TEST_ROOT}/run"
JOBS_DIR="${RUN_DIR}/jobs"
ACTIVE_FILE="${RUN_DIR}/active.job"
CLOCK_FILE="${TEST_ROOT}/clock"
LUA_DIR="${TEST_ROOT}/lua"
FAKE_DIR="${TEST_ROOT}/fake"
mkdir -p "${JOBS_DIR}" "${LUA_DIR}" "${FAKE_DIR}"
for lua in zapret-lib.lua zapret-antidpi.lua zapret-auto.lua inventory-only.lua
do
    printf '%s\n' '-- fixture' > "${LUA_DIR}/${lua}"
done
printf '%s\n' fake > "${FAKE_DIR}/inventory.bin"

budget_case()
{
    _job="$1"
    _mode="$2"
    _clock="$3"
    _jobdir="${JOBS_DIR}/${_job}"
    mkdir -p "${_jobdir}"
    STRATEGY_LAB_RUN_DIR="${RUN_DIR}" STRATEGY_LAB_JOBS_DIR="${JOBS_DIR}" \
    STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" \
        "${PYTHON_LAUNCHER}" state initialize "${_job}" \
        "${_jobdir}/status.json" "${_jobdir}/events.ndjson" budget.example "${_mode}" en
    printf '%s\n' "${_clock}" > "${CLOCK_FILE}"
}

budget_case job.BUDGETA standard 1000
PYTHONPATH="${ZAPRET_DIR}" STRATEGY_LAB_NOW_EPOCH_FILE="${CLOCK_FILE}" \
STRATEGY_LAB_RUN_DIR="${RUN_DIR}" STRATEGY_LAB_JOBS_DIR="${JOBS_DIR}" \
"${PYTHON_BIN}" - <<'PY'
import json, os
from pathlib import Path
from strategy_lab_py.orchestrator import Budget, StageTimedOut

state = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / "job.BUDGETA" / "status.json"
b = Budget("standard", state, "job.BUDGETA")
b.record_initial()
value = json.loads(state.read_text())
assert value["started_at"] == "1970-01-01T00:16:40Z"
assert value["standard_deadline_at"] == "1970-01-01T00:19:10Z"
assert value["deadline_at"] == "1970-01-01T00:19:10Z"
clock = Path(os.environ["STRATEGY_LAB_NOW_EPOCH_FILE"])
clock.write_text("1110\n")
assert b.timeout_for("60", 60) == 40
clock.write_text("1149\n")
assert b.timeout_for("70", 60) == 1
clock.write_text("1150\n")
try:
    b.timeout_for("70", 60)
except StageTimedOut as exc:
    assert exc.stage == "70"
else:
    raise AssertionError("expired standard deadline was accepted")
PY

budget_case job.BUDGETB extended 2000
PYTHONPATH="${ZAPRET_DIR}" STRATEGY_LAB_NOW_EPOCH_FILE="${CLOCK_FILE}" \
STRATEGY_LAB_RUN_DIR="${RUN_DIR}" STRATEGY_LAB_JOBS_DIR="${JOBS_DIR}" \
"${PYTHON_BIN}" - <<'PY'
import json, os
from pathlib import Path
from strategy_lab_py.orchestrator import Budget, StageTimedOut

state = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / "job.BUDGETB" / "status.json"
b = Budget("extended", state, "job.BUDGETB")
b.record_initial()
clock = Path(os.environ["STRATEGY_LAB_NOW_EPOCH_FILE"])
clock.write_text("2140\n")
assert b.timeout_for("70", 60) == 10
clock.write_text("2150\n")
b.begin_stage80()
value = json.loads(state.read_text())
assert value["stage80_started_at"] == "1970-01-01T00:35:50Z"
assert value["stage80_deadline_at"] == "1970-01-01T00:37:50Z"
assert b.timeout_for("80", 120) == 120
clock.write_text("2220\n")
assert b.timeout_for("80", 120) == 50
clock.write_text("2269\n")
assert b.timeout_for("80", 120) == 1
clock.write_text("2270\n")
try:
    b.require("85")
except StageTimedOut as exc:
    assert exc.stage == "85"
else:
    raise AssertionError("expired extended deadline was accepted")
PY

FAKE_ADAPTER="${TEST_ROOT}/adapter.sh"
cat > "${FAKE_ADAPTER}" <<'ADAPTER'
#!/bin/sh
set -eu
action="$1"
job="$2"
jobdir="${STRATEGY_LAB_JOBS_DIR}/${job}"
status="${jobdir}/status.json"
result="${STRATEGY_LAB_STAGE_RESULT_FILE}"
launcher="${STRATEGY_LAB_PYTHON_LAUNCHER}"
python="${STRATEGY_LAB_PYTHON_BIN}"
mode=$(cat "${jobdir}/test-mode" 2>/dev/null || printf '%s\n' success)
printf '%s\n' "${action}" >> "${jobdir}/adapter-order"
state()
{
    STRATEGY_LAB_PYTHON_BIN="${python}" "${launcher}" state "$@"
}
emit()
{
    printf '{"kind":"%s","message":"%s","initial_state":"%s"}\n' "$1" "${2:-}" "${3:-}" > "${result}"
}
case "${action}" in
    00)
        printf '%s\n' example.com > "${jobdir}/endpoints.txt"
        state set-target "${job}" "${status}" example.com domain "${jobdir}/endpoints.txt"
        emit pass 'PASS — target'
        ;;
    10)
        printf '%s\n' '{"source":"test","state":"RUNNING"}' > "${jobdir}/snapshot.json"
        state set-json-field "${job}" "${status}" lifecycle_snapshot "${jobdir}/snapshot.json"
        state set-initial-service-state "${job}" "${status}" RUNNING
        emit pass 'PASS — snapshot' RUNNING
        ;;
    20) emit pass 'PASS — stopped' ;;
    30)
        if [ "${mode}" = cancel ] || [ "${mode}" = timeout ]; then sleep 20; fi
        printf '%s\n' '{"ipv4":"available","ipv6":"unavailable","quic_ipv4":"closed"}' > "${jobdir}/network.json"
        state set-json-field "${job}" "${status}" network "${jobdir}/network.json"
        emit pass 'PASS — network'
        ;;
    40)
        printf '%s\n' '{"total":1,"failed":1}' > "${jobdir}/baseline.json"
        state set-json-field "${job}" "${status}" baseline "${jobdir}/baseline.json"
        emit pass 'PASS — baseline'
        ;;
    50)
        printf '%s\n' '{"all_pass":true}' > "${jobdir}/candidate.json"
        state set-candidate "${job}" "${status}" "${jobdir}/candidate.json"
        emit pass 'PASS — candidate'
        ;;
    60)
        printf '%s\n' '{"working":[1],"completed":1}' > "${jobdir}/expansion.json"
        state set-json-field "${job}" "${status}" parameter_expansion "${jobdir}/expansion.json"
        emit pass 'PASS — expansion'
        ;;
    70)
        printf '%s\n' '{"stable":[1],"completed":1}' > "${jobdir}/stability.json"
        emit pass 'PASS — stability'
        ;;
    80-tcp)
        printf '%s\n' '{"protocols":{}}' > "${jobdir}/extended.json"
        state set-json-field "${job}" "${status}" extended "${jobdir}/extended.json"
        emit pass ''
        ;;
    80-quic)
        printf '%s\n' '{"status":"skipped"}' > "${jobdir}/quic.json"
        state set-json-field "${job}" "${status}" quic "${jobdir}/quic.json"
        emit pass ''
        ;;
    80-udp)
        printf '%s\n' '{"status":"skipped"}' > "${jobdir}/udp.json"
        state set-json-field "${job}" "${status}" udp "${jobdir}/udp.json"
        emit pass ''
        ;;
    85)
        printf '%s\n' '{"count":1,"items":[{"id":"x"}]}' > "${jobdir}/shortlist.json"
        state set-stability "${job}" "${status}" "${jobdir}/stability.json" "${jobdir}/shortlist.json"
        emit pass 'PASS — shortlist'
        ;;
    restore)
        if [ "${mode}" = restore-fail ]; then emit error ''; exit 0; fi
        printf '%s\n' '{"verified":true,"source":"test","initial_state":"RUNNING","final_state":"RUNNING","strategy_unchanged":true,"temporary_runtime_clean":true}' > "${jobdir}/restoration.json"
        state set-json-field "${job}" "${status}" restoration "${jobdir}/restoration.json"
        emit pass '' RUNNING
        ;;
    eligibility) emit pass '' ;;
    clear-active)
        rm -f "${STRATEGY_LAB_ACTIVE_FILE}"
        emit pass ''
        ;;
    *) exit 64 ;;
esac
ADAPTER
chmod 0755 "${FAKE_ADAPTER}"

new_job()
{
    _job="$1"
    _mode="$2"
    _test_mode="$3"
    _jobdir="${JOBS_DIR}/${_job}"
    mkdir -p "${_jobdir}"
    STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" "${PYTHON_LAUNCHER}" state initialize \
        "${_job}" "${_jobdir}/status.json" "${_jobdir}/events.ndjson" example.com "${_mode}" en
    printf '%s\n' "${_test_mode}" > "${_jobdir}/test-mode"
    printf '%s\n' "${_job}" > "${ACTIVE_FILE}"
}

run_job()
{
    _job="$1"
    shift
    STRATEGY_LAB_RUN_DIR="${RUN_DIR}" \
    STRATEGY_LAB_JOBS_DIR="${JOBS_DIR}" \
    STRATEGY_LAB_ACTIVE_FILE="${ACTIVE_FILE}" \
    STRATEGY_LAB_STAGE_ADAPTER="${FAKE_ADAPTER}" \
    STRATEGY_LAB_LUA_DIR="${LUA_DIR}" \
    STRATEGY_LAB_FAKE_DIR="${FAKE_DIR}" \
    STRATEGY_LAB_PYTHON_LAUNCHER="${PYTHON_LAUNCHER}" \
    STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" \
    PYTHONPATH="${ZAPRET_DIR}" \
        "$@" "${PYTHON_LAUNCHER}" orchestrate "${_job}"
}

new_job job.SUCCESS standard success
run_job job.SUCCESS env
SUCCESS_STATUS="${JOBS_DIR}/job.SUCCESS/status.json"
"$(command -v jq)" -e '
    .state=="completed" and .outcome=="SUCCESS" and .current_stage=="99" and
    .progress.percent==100 and
    ([.stages[].number]==["00","10","20","30","40","50","60","70","80","85","90","99"]) and
    ([.stages[].status]==["PASS","PASS","PASS","PASS","PASS","PASS","PASS","PASS","SKIPPED","PASS","PASS","PASS"])
' "${SUCCESS_STATUS}" >/dev/null || fail 'Python standard stage machine or terminal result is invalid'
"$(command -v jq)" -e '
    .schema==1 and (.inventory_id|startswith("ri1-")) and
    [.lua[].name]==["inventory-only.lua","zapret-antidpi.lua","zapret-auto.lua","zapret-lib.lua"] and
    [.external_blobs[].name]==["inventory.bin"] and
    .builtin_blobs==["fake_default_tls","fake_default_http","fake_default_quic"]
' "${JOBS_DIR}/job.SUCCESS/resource-inventory.json" >/dev/null ||
    fail 'Python orchestrator did not persist the job-scoped installed resource inventory'
cat > "${TEST_ROOT}/expected-order" <<'EXPECTED'
00
10
20
30
40
50
60
70
85
restore
eligibility
clear-active
EXPECTED
cmp -s "${TEST_ROOT}/expected-order" "${JOBS_DIR}/job.SUCCESS/adapter-order" ||
    fail 'Python orchestrator did not own the expected standard action order'
[ ! -e "${ACTIVE_FILE}" ] || fail 'terminal success left active-job ownership behind'

new_job job.RESTORE extended restore-fail
run_job job.RESTORE env
"$(command -v jq)" -e '.state=="error" and .outcome=="RESTORE_FAILED" and (.stages[]|select(.number=="90")|.status)=="FAIL" and (.stages[]|select(.number=="99")|.status)=="FAIL"' \
    "${JOBS_DIR}/job.RESTORE/status.json" >/dev/null || fail 'restoration failure did not override the terminal outcome'

new_job job.TIMEOUT standard timeout
run_job job.TIMEOUT env STRATEGY_LAB_STAGE30_TIMEOUT=1
"$(command -v jq)" -e '.state=="error" and .outcome=="TIMEOUT" and (.stages[]|select(.number=="30")|.status)=="TIMEOUT" and (.stages[]|select(.number=="90")|.status)=="PASS" and (.stages[]|select(.number=="99")|.status)=="FAIL"' \
    "${JOBS_DIR}/job.TIMEOUT/status.json" >/dev/null || fail 'Python stage timeout did not preserve mandatory restoration/finalization'

new_job job.CANCEL standard cancel
(
    run_job job.CANCEL env STRATEGY_LAB_STAGE30_TIMEOUT=30
) &
runner=$!
CANCEL_STATUS="${JOBS_DIR}/job.CANCEL/status.json"
attempt=0
while [ "$("$(command -v jq)" -r '.current_stage' "${CANCEL_STATUS}")" != 30 ] && [ "${attempt}" -lt 100 ]
do
    sleep 0.05
    attempt=$((attempt + 1))
done
[ "${attempt}" -lt 100 ] || fail 'cancel fixture did not reach stage 30'
STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" "${PYTHON_LAUNCHER}" state request-cancel job.CANCEL "${CANCEL_STATUS}" cancel
: > "${JOBS_DIR}/job.CANCEL/cancel.request"
wait "${runner}" || fail 'Python cancellation did not finalize cleanly'
"$(command -v jq)" -e '.state=="completed" and .outcome=="PARTIAL" and .cancel_requested==true and (.stages[]|select(.number=="90")|.status)=="PASS" and (.stages[]|select(.number=="99")|.status)=="PASS"' \
    "${CANCEL_STATUS}" >/dev/null || fail 'Python cancellation did not converge through mandatory restoration/finalization'

grep -Fq 'exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"' "${WORKER}" ||
    fail 'production worker does not delegate orchestration to Python'
! grep -Fq 'worker_stage_machine' "${WORKER}" || fail 'production worker still loads the shell stage machine'
! grep -Fq 'worker_budget' "${WORKER}" || fail 'production worker still loads the shell budget owner'
grep -Fq 'strategy_lab_python\.py[[:space:]]+orchestrate' "${COMMON}" ||
    fail 'active-job ownership does not recognize the Python orchestrator process'

echo 'PASS: Python 3.13 owns Strategy Lab stage order, budgets, cancellation, timeout, and mandatory terminal restoration/finalization'
