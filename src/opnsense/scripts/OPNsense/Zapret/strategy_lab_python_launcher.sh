#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${STRATEGY_LAB_PYTHON_BIN:-/usr/local/bin/python3}
PYTHON_ENTRY="${SCRIPT_DIR}/strategy_lab_python.py"
EXPECTED_PYTHON=3.13

runtime_error()
{
    echo "ERROR: Strategy Lab Python runtime could not start: $*" >&2
    exit 70
}

[ -x "${PYTHON_BIN}" ] || runtime_error "interpreter is not executable: ${PYTHON_BIN}"
[ -r "${PYTHON_ENTRY}" ] || runtime_error "entry point is not readable: ${PYTHON_ENTRY}"

python_version=$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null) ||
    runtime_error "interpreter execution failed: ${PYTHON_BIN}"

[ "${python_version}" = "${EXPECTED_PYTHON}" ] ||
    runtime_error "unsupported interpreter version ${python_version}; expected ${EXPECTED_PYTHON}"

exec "${PYTHON_BIN}" "${PYTHON_ENTRY}" "$@"
