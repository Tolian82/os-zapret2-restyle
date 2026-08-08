#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-${STRATEGY_LAB_PYTHON_BIN:-python3.13}}
ORCHESTRATOR="${ZAPRET_DIR}/strategy_lab_py/orchestrator.py"
WORKER="${ZAPRET_DIR}/strategy_lab_worker.sh"
STATE_MODULE="${ZAPRET_DIR}/strategy_lab_py/state.py"
LEGACY_STAGE_MACHINE="${ZAPRET_DIR}/strategy_lab/worker_stage_machine.sh"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail 'Python 3.13 runtime is unavailable'
"${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)' ||
    fail 'Strategy Lab stage-machine test requires Python 3.13'

PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
from strategy_lab_py import orchestrator
from strategy_lab_py import state

expected = ("00", "10", "20", "30", "40", "50", "60", "70", "80", "85", "90", "99")
actual = tuple(number for number, _key in state.STAGES)
assert actual == expected, (actual, expected)
assert tuple(orchestrator.RUNNING_EVENTS) == expected[:-1]
assert orchestrator.RUNNING_EVENTS["90"]
PY

grep -Fq 'for stage in ("00", "10", "20", "30", "40", "50", "60", "70"):' "${ORCHESTRATOR}" ||
    fail 'Python orchestrator does not own the ordered pre-search stage sequence'
grep -Fq 'outcome = self._run_stage80()' "${ORCHESTRATOR}" ||
    fail 'Python orchestrator does not own stage 80 progression'
grep -Fq 'outcome = self._run_regular_stage("85")' "${ORCHESTRATOR}" ||
    fail 'Python orchestrator does not own stage 85 progression'
grep -Fq 'self.current_stage = "90"' "${ORCHESTRATOR}" ||
    fail 'Python finalizer does not own mandatory stage 90 progression'
grep -Fq 'self.current_stage = "99"' "${ORCHESTRATOR}" ||
    fail 'Python finalizer does not own terminal stage 99 progression'
grep -Fq 'self._skip("80", _message(self.language, "stage80_skip"))' "${ORCHESTRATOR}" ||
    fail 'standard mode does not preserve explicit stage-80 skip semantics'

grep -Fq 'exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"' "${WORKER}" ||
    fail 'production worker does not delegate the explicit stage machine to Python'
! grep -Fq 'worker_stage_machine' "${WORKER}" ||
    fail 'production worker still loads the retired shell stage-machine owner'
! grep -Fq 'worker_run_search_stages' "${WORKER}" ||
    fail 'production worker still calls the retired shell stage-machine entry point'
[ ! -e "${LEGACY_STAGE_MACHINE}" ] ||
    fail 'retired shell stage-machine owner is still packaged after Migration Patch 7'

"${PYTHON_BIN}" -m py_compile "${ORCHESTRATOR}" "${STATE_MODULE}"
sh -n "${WORKER}"

echo 'PASS: Python Strategy Lab owns the explicit monotonic stage machine and the retired shell owner is absent'
