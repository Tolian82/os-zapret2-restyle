#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${STRATEGY_LAB_PYTHON_BIN:-/usr/local/bin/python3}
PYTHON_ENTRY="${SCRIPT_DIR}/strategy_lab_python.py"
EXPECTED_PYTHON=3.13

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

requested_python=${PYTHON_BIN}
case "${PYTHON_BIN}" in
    */*)
        ;;
    *)
        PYTHON_BIN=$(command -v "${PYTHON_BIN}" 2>/dev/null) ||
            runtime_error "interpreter is not executable: ${requested_python}"
        ;;
esac

[ -x "${PYTHON_BIN}" ] || runtime_error "interpreter is not executable: ${requested_python}"
[ -r "${PYTHON_ENTRY}" ] || runtime_error "entry point is not readable: ${PYTHON_ENTRY}"

python_version=$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null) ||
    runtime_error "interpreter execution failed: ${PYTHON_BIN}"

[ "${python_version}" = "${EXPECTED_PYTHON}" ] ||
    runtime_error "unsupported interpreter version ${python_version}; expected ${EXPECTED_PYTHON}"

exec "${PYTHON_BIN}" "${PYTHON_ENTRY}" "$@"
