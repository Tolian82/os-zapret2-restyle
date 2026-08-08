#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
PY_STAGE_ADAPTER="${SCRIPT_DIR}/strategy_lab_python_stage_adapter.sh"
PY_RESULT="${SCRIPT_DIR}/strategy_lab_py/result.py"
RESULT_RUNNER="${SCRIPT_DIR}/strategy_lab_result_runner.sh"
PROFILE_ADAPTER="${SCRIPT_DIR}/strategy_lab_profile_candidate_adapter.sh"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
LEGACY_REPLAY="${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh"
LEGACY_RESULT="${MODULE_DIR}/worker_result.sh"
LEGACY_STAGE_MACHINE="${MODULE_DIR}/worker_stage_machine.sh"
STATE="${MODULE_DIR}/state.sh"
E2E="${ROOT_DIR}/scripts/test-strategy-lab-e2e.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }

# Circular lifecycle state and stop control remain private session artifacts only.
! grep -Fq 'circular_install_legacy_aliases' "${LAUNCHER}" || fail 'legacy circular alias installer returned'
! grep -Fq '${STRATEGY_LAB_CIRCULAR_DIR}/state.json' "${LAUNCHER}" || fail 'global circular state alias returned'
! grep -Fq '${STRATEGY_LAB_CIRCULAR_DIR}/stop' "${LAUNCHER}" || fail 'global circular stop alias returned'
grep -Fq 'strategy_lab_circular_session_state_file' "${LAUNCHER}" || fail 'private circular session state owner is missing'
grep -Fq 'strategy_lab_circular_session_stop_file' "${LAUNCHER}" || fail 'private circular stop owner is missing'

# Transitional automated-worker owners must be physically absent after Patch 7.
[ ! -e "${LEGACY_REPLAY}" ] || fail 'legacy shell final profile replay owner remains packaged'
[ ! -e "${LEGACY_RESULT}" ] || fail 'legacy shell automated result/eligibility owner remains packaged'
[ ! -e "${LEGACY_STAGE_MACHINE}" ] || fail 'legacy shell automated stage machine remains packaged'
[ ! -e "${MODULE_DIR}/worker_state_serialization.sh" ] || fail 'legacy state serialization override remains packaged'

# The production automated path has one Python owner for orchestration and final results.
grep -Fq 'strategy_lab_python_stage_adapter.sh' "${WORKER}" || fail 'production worker does not select the Python final-stage adapter'
grep -Fq 'exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"' "${WORKER}" || fail 'production worker does not enter the Python orchestrator'
grep -Fq '85)' "${PY_STAGE_ADAPTER}" || fail 'Python final-stage adapter does not intercept Stage 85'
grep -Fq 'eligibility)' "${PY_STAGE_ADAPTER}" || fail 'Python final-stage adapter does not intercept automated eligibility'
grep -Fq 'result "$@"' "${RESULT_RUNNER}" || fail 'final result runner is not a thin Python launcher'
grep -Fq 'def build_shortlist(' "${PY_RESULT}" || fail 'Python final-result owner does not define shortlist construction'
grep -Fq 'def circular_eligibility(' "${PY_RESULT}" || fail 'Python final-result owner does not define automated circular eligibility'
grep -Fq 'candidate.run_candidate(' "${PY_RESULT}" || fail 'Python final replay does not reuse the unified Python candidate owner'
grep -Fq 'exec /bin/sh "${BASE_ADAPTER}" "$@"' "${PROFILE_ADAPTER}" || fail 'profile adapter does not delegate system actions to the canonical candidate adapter'
! grep -Fq 'worker_result' "${WORKER}" || fail 'production worker still references retired shell result ownership'
! grep -Fq 'worker_stage_machine' "${WORKER}" || fail 'production worker still references retired shell stage-machine ownership'

# Shell state remains a compatibility adapter; private circular remains deliberately shell-owned.
! grep -Fq 'worker_state_serialization' "${WORKER}" || fail 'production worker regained a shell state serialization override'
grep -Fq 'strategy_lab_state_python' "${STATE}" || fail 'shell state compatibility layer no longer delegates automated persistence to Python'

# End-to-end coverage continues to prove the private circular-session contract and rejects aliases.
grep -Fq 'circular_dir="${STRATEGY_LAB_RUN_DIR}/circular"' "${E2E}" || fail 'e2e no longer covers circular storage'
grep -Fq 'active.session' "${E2E}" || fail 'e2e no longer covers circular ownership'
grep -Fq 'sessions/${session}' "${E2E}" || fail 'e2e no longer covers private circular sessions'
grep -Fq 'stop.request' "${E2E}" || fail 'e2e no longer covers private circular stop requests'
grep -Fq "legacy circular state alias remains" "${E2E}" || fail 'e2e no longer rejects legacy circular state aliases'
grep -Fq "legacy circular stop alias remains" "${E2E}" || fail 'e2e no longer rejects legacy circular stop aliases'

for file in "${WORKER}" "${PY_STAGE_ADAPTER}" "${RESULT_RUNNER}" "${PROFILE_ADAPTER}" "${LAUNCHER}" "${STATE}" "${E2E}"
do
    sh -n "${file}"
done

echo 'PASS: obsolete automated shell owners are removed, Python owns automated orchestration/final results, and private circular remains isolated shell state'
