#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"

set -eu

[ -x "${PYTHON_LAUNCHER}" ] || {
    echo "ERROR: Strategy Lab Python launcher is unavailable: ${PYTHON_LAUNCHER}" >&2
    exit 70
}

exec "${PYTHON_LAUNCHER}" probe "$@"
