#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${STRATEGY_LAB_PYTHON_BIN:-/usr/local/bin/python3}
PYTHON_ENTRY="${SCRIPT_DIR}/strategy_lab_python.py"
EXPECTED_PYTHON=3.13

# Telemetry-derived containment defaults for Strategy Lab 0.4.0_6.
# Keep the 150/270-second search budgets unchanged while allowing a complete
# cold candidate lifecycle to finish instead of being cut off at five seconds.
: "${STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT:=8}"
: "${STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT:=8}"
: "${STRATEGY_LAB_CANDIDATE_TIMEOUT:=60}"
: "${STRATEGY_LAB_STAGE60_TIMEOUT:=70}"
export STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT \
    STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT \
    STRATEGY_LAB_CANDIDATE_TIMEOUT STRATEGY_LAB_STAGE60_TIMEOUT

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
