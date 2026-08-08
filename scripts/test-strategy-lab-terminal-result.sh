#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${ZAPRET_DIR}/strategy_lab"
ORCHESTRATOR="${ZAPRET_DIR}/strategy_lab_py/orchestrator.py"
RESULT="${ZAPRET_DIR}/strategy_lab_py/result.py"
WORKER="${ZAPRET_DIR}/strategy_lab_worker.sh"
PY_STAGE_ADAPTER="${ZAPRET_DIR}/strategy_lab_python_stage_adapter.sh"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-${STRATEGY_LAB_PYTHON_BIN:-python3.13}}

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail 'Python 3.13 runtime is unavailable'
PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
from strategy_lab_py.orchestrator import terminal_message, terminal_report_status, terminal_state

cases = [
    ("SUCCESS", "completed", "PASS"),
    ("NO_CANDIDATE", "completed", "PASS"),
    ("TARGET_ACCESSIBLE", "completed", "PASS"),
    ("PARTIAL", "completed", "PASS"),
    ("TIMEOUT", "error", "FAIL"),
    ("ERROR", "error", "FAIL"),
    ("RESTORE_FAILED", "error", "FAIL"),
]
for outcome, expected_state, expected_report in cases:
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

grep -Fq 'exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"' "${WORKER}" ||
    fail 'production worker does not delegate terminal policy to Python'
grep -Fq 'strategy_lab_python_stage_adapter.sh' "${WORKER}" ||
    fail 'production worker does not route final result actions through Python'
! grep -Fq 'worker_result' "${WORKER}" ||
    fail 'production worker still references the retired shell terminal-result owner'
[ ! -e "${MODULE_DIR}/worker_result.sh" ] ||
    fail 'retired shell terminal-result owner is still packaged'
[ ! -e "${MODULE_DIR}/worker_stage_machine.sh" ] ||
    fail 'retired shell stage-machine owner is still packaged'

grep -Fq 'def terminal_state(outcome: str)' "${ORCHESTRATOR}" ||
    fail 'Python terminal state mapping is missing'
grep -Fq 'def terminal_report_status(outcome: str)' "${ORCHESTRATOR}" ||
    fail 'Python terminal report mapping is missing'
grep -Fq 'def terminal_message(language: str, mode: str, outcome: str, canceled: bool, count: int = 0)' "${ORCHESTRATOR}" ||
    fail 'Python localized terminal message mapping is missing'
grep -Fq 'outcome = self._restore(outcome)' "${ORCHESTRATOR}" ||
    fail 'Python finalization does not enforce restoration before terminal persistence'
grep -Fq 'return "RESTORE_FAILED"' "${ORCHESTRATOR}" ||
    fail 'Python restoration failure does not override the prior outcome'
grep -Fq 'eligibility)' "${PY_STAGE_ADAPTER}" ||
    fail 'Python final-stage adapter does not own terminal automated eligibility'
grep -Fq 'def circular_eligibility(' "${RESULT}" ||
    fail 'Python final-result module does not own circular eligibility'

"${PYTHON_BIN}" -m py_compile "${ORCHESTRATOR}" "${RESULT}"
sh -n "${WORKER}"
sh -n "${PY_STAGE_ADAPTER}"

echo 'PASS: Python owns Strategy Lab terminal mapping/localization/finalization and final automated eligibility with no shell terminal-result fallback'
