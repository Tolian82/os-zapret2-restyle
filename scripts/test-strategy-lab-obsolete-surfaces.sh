#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
STATE="${MODULE_DIR}/state.sh"
STAGE_MACHINE="${MODULE_DIR}/worker_stage_machine.sh"
CONTROL="${MODULE_DIR}/worker_control.sh"
E2E="${ROOT_DIR}/scripts/test-strategy-lab-e2e.sh"

# Circular lifecycle state and stop control are private session artifacts only.
! grep -Fq 'circular_install_legacy_aliases' "${LAUNCHER}"
! grep -Fq '${STRATEGY_LAB_CIRCULAR_DIR}/state.json' "${LAUNCHER}"
! grep -Fq '${STRATEGY_LAB_CIRCULAR_DIR}/stop' "${LAUNCHER}"
grep -Fq 'strategy_lab_circular_session_state_file' "${LAUNCHER}"
grep -Fq 'strategy_lab_circular_session_stop_file' "${LAUNCHER}"

# The old state-level hook is gone. Explicit worker orchestration remains authoritative.
! grep -Fq 'strategy_lab_skip_unfinished()' "${STATE}"
grep -Fq 'worker_skip_unfinished()' "${STAGE_MACHINE}"
grep -Fq 'worker_skip_unfinished "${JOB_ID}" "${CANCEL_MESSAGE}"' "${CONTROL}"
grep -Fq 'worker_skip_unfinished "${JOB_ID}" "${ERROR_SKIP_MESSAGE}"' "${CONTROL}"
grep -Fq 'worker_skip_unfinished "${JOB_ID}" "${TIMEOUT_SKIP_MESSAGE}"' "${CONTROL}"

# End-to-end coverage uses the same private-session contract and rejects aliases.
grep -Fq 'circular/active.session' "${E2E}"
grep -Fq 'sessions/${session}' "${E2E}"
grep -Fq 'stop.request' "${E2E}"
grep -Fq "legacy circular state alias remains" "${E2E}"
grep -Fq "legacy circular stop alias remains" "${E2E}"
grep -Fq "circular validation did not complete" "${E2E}"

sh -n "${LAUNCHER}"
sh -n "${STATE}"
sh -n "${STAGE_MACHINE}"
sh -n "${CONTROL}"
sh -n "${E2E}"
echo 'PASS: obsolete circular aliases and duplicate state hook are removed without weakening worker cleanup'
