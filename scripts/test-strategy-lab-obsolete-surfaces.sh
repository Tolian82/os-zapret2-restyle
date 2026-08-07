#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
STATE="${MODULE_DIR}/state.sh"
EXPANSION="${MODULE_DIR}/expansion.sh"
STABILITY="${MODULE_DIR}/stability.sh"
EXTENDED="${MODULE_DIR}/extended.sh"
QUIC="${MODULE_DIR}/quic.sh"
UDP="${MODULE_DIR}/udp.sh"
PROFILE="${MODULE_DIR}/profile.sh"
RESULT="${MODULE_DIR}/worker_result.sh"
STAGE_MACHINE="${MODULE_DIR}/worker_stage_machine.sh"
CONTROL="${MODULE_DIR}/worker_control.sh"
E2E="${ROOT_DIR}/scripts/test-strategy-lab-e2e.sh"

# Circular lifecycle state and stop control are private session artifacts only.
! grep -Fq 'circular_install_legacy_aliases' "${LAUNCHER}"
! grep -Fq '${STRATEGY_LAB_CIRCULAR_DIR}/state.json' "${LAUNCHER}"
! grep -Fq '${STRATEGY_LAB_CIRCULAR_DIR}/stop' "${LAUNCHER}"
grep -Fq 'strategy_lab_circular_session_state_file' "${LAUNCHER}"
grep -Fq 'strategy_lab_circular_session_stop_file' "${LAUNCHER}"

# Transitional load-order hooks and the serialization override module are gone.
[ ! -e "${MODULE_DIR}/worker_state_serialization.sh" ]
! grep -Fq 'worker_state_serialization' "${WORKER}"
for file in "${STATE}" "${EXPANSION}" "${STABILITY}"
do
    ! grep -Eq '^[[:space:]]*strategy_lab_skip_unfinished[[:space:]]*\(\)' "${file}"
done
for file in "${EXPANSION}" "${STABILITY}" "${EXTENDED}" "${QUIC}" "${UDP}"
do
    ! grep -Eq '^[[:space:]]*strategy_lab_skip_remaining[[:space:]]*\(\)' "${file}"
done

# One canonical owner remains for shortlist and circular eligibility semantics.
[ "$(grep -R -E -l '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${MODULE_DIR}"/*.sh | wc -l | tr -d ' ')" -eq 1 ]
grep -Eq '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${PROFILE}"
[ "$(grep -R -E -l '^[[:space:]]*worker_result_set_circular_eligibility[[:space:]]*\(\)' "${MODULE_DIR}"/*.sh | wc -l | tr -d ' ')" -eq 1 ]
grep -Eq '^[[:space:]]*worker_result_set_circular_eligibility[[:space:]]*\(\)' "${RESULT}"

# Explicit worker orchestration remains authoritative.
grep -Fq 'worker_skip_unfinished()' "${STAGE_MACHINE}"
grep -Fq 'worker_skip_unfinished "${JOB_ID}" "${CANCEL_MESSAGE}"' "${CONTROL}"
grep -Fq 'worker_skip_unfinished "${JOB_ID}" "${ERROR_SKIP_MESSAGE}"' "${CONTROL}"
grep -Fq 'worker_skip_unfinished "${JOB_ID}" "${TIMEOUT_SKIP_MESSAGE}"' "${CONTROL}"

# End-to-end coverage uses the private circular-session contract and rejects aliases.
grep -Fq 'circular_dir="${STRATEGY_LAB_RUN_DIR}/circular"' "${E2E}"
grep -Fq 'active.session' "${E2E}"
grep -Fq 'sessions/${session}' "${E2E}"
grep -Fq 'stop.request' "${E2E}"
grep -Fq "legacy circular state alias remains" "${E2E}"
grep -Fq "legacy circular stop alias remains" "${E2E}"
grep -Fq "circular validation did not complete" "${E2E}"

for file in "${WORKER}" "${LAUNCHER}" "${STATE}" "${EXPANSION}" "${STABILITY}" "${EXTENDED}" "${QUIC}" "${UDP}" "${PROFILE}" "${RESULT}" "${STAGE_MACHINE}" "${CONTROL}" "${E2E}"
do
    sh -n "${file}"
done

echo 'PASS: obsolete Strategy Lab aliases, hooks, and load-order override surfaces are removed while explicit worker orchestration remains authoritative'
