#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_ENTRY="${SCRIPT_DIR}/strategy_lab_python.py"
PYTHON_RUNTIME_LAUNCHER="${SCRIPT_DIR}/python_runtime.sh"

# Telemetry-derived containment defaults retained from Strategy Lab 0.4.0_8.
# `_33` keeps the 150/270-second search budgets and the bounded cold lifecycle,
# uses a small bounded GET for discovery/stability, stops 3/3 stability as soon
# as one failure makes success impossible, and reserves a larger bounded GET for
# the final two-to-three publication finalists. Warm/parallel runtime models stay
# behind the separate A/B/C experiment gate.
: "${STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT:=8}"
: "${STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_CANDIDATE_TIMEOUT:=60}"
: "${STRATEGY_LAB_STAGE60_TIMEOUT:=120}"
: "${STRATEGY_LAB_STAGE70_TIMEOUT:=60}"
: "${STRATEGY_LAB_STAGE80_TIMEOUT:=120}"
: "${STRATEGY_LAB_STAGE85_TIMEOUT:=120}"
: "${STRATEGY_LAB_RESTORE_PARENT_TIMEOUT:=180}"
: "${STRATEGY_LAB_DISCOVERY_RANGE_BYTES:=4096}"
: "${STRATEGY_LAB_DISCOVERY_MAX_TIME:=3}"
: "${STRATEGY_LAB_FINALIST_TARGET_BYTES:=16384}"
: "${STRATEGY_LAB_FINALIST_RANGE_BYTES:=65536}"
: "${STRATEGY_LAB_FINALIST_MAX_TIME:=6}"
: "${STRATEGY_LAB_FINALIST_CANDIDATE_TIMEOUT:=15}"
export STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT \
    STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_CANDIDATE_TIMEOUT STRATEGY_LAB_STAGE60_TIMEOUT \
    STRATEGY_LAB_STAGE70_TIMEOUT STRATEGY_LAB_STAGE80_TIMEOUT \
    STRATEGY_LAB_STAGE85_TIMEOUT STRATEGY_LAB_RESTORE_PARENT_TIMEOUT \
    STRATEGY_LAB_DISCOVERY_RANGE_BYTES STRATEGY_LAB_DISCOVERY_MAX_TIME \
    STRATEGY_LAB_FINALIST_TARGET_BYTES STRATEGY_LAB_FINALIST_RANGE_BYTES \
    STRATEGY_LAB_FINALIST_MAX_TIME STRATEGY_LAB_FINALIST_CANDIDATE_TIMEOUT

runtime_error()
{
    echo "ERROR: Strategy Lab Python runtime could not start: $*" >&2
    exit 70
}

[ -r "${PYTHON_ENTRY}" ] || runtime_error "entry point is not readable: ${PYTHON_ENTRY}"
[ -r "${PYTHON_RUNTIME_LAUNCHER}" ] || runtime_error "runtime launcher unavailable"

if [ "${STRATEGY_LAB_PYTHON_BIN+x}" = x ]; then
    requested_python="${STRATEGY_LAB_PYTHON_BIN}"
    case "${requested_python}" in
        */*) ;;
        *) requested_python=$(command -v "${requested_python}" 2>/dev/null) ||
            runtime_error "interpreter not found" ;;
    esac
    ZAPRET_PYTHON_BIN="${requested_python}"
    export ZAPRET_PYTHON_BIN
fi
PYTHON_BIN=$(/bin/sh "${PYTHON_RUNTIME_LAUNCHER}" --resolve) ||
    runtime_error "installed Python runtime is unavailable or incompatible"

exec "${PYTHON_BIN}" "${PYTHON_ENTRY}" "$@"
