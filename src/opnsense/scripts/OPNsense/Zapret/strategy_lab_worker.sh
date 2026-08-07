#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
JOB_ID="${1:-}"

set -eu
umask 022

printf '%s\n' "${JOB_ID}" | grep -Eq '^job\.[A-Za-z0-9]+$' || exit 64
[ -x "${PYTHON_LAUNCHER}" ] || {
    echo "ERROR: Strategy Lab Python launcher is unavailable: ${PYTHON_LAUNCHER}" >&2
    exit 70
}

exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"
