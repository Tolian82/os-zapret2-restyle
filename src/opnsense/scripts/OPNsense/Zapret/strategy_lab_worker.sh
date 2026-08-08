#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
STRATEGY_LAB_STAGE_ADAPTER="${STRATEGY_LAB_STAGE_ADAPTER:-${SCRIPT_DIR}/strategy_lab_python_stage_adapter.sh}"
JOB_ID="${1:-}"

set -eu
umask 022

printf '%s\n' "${JOB_ID}" | grep -Eq '^job\.[A-Za-z0-9]+$' || exit 64
[ -x "${PYTHON_LAUNCHER}" ] || {
    echo "ERROR: Strategy Lab Python launcher is unavailable: ${PYTHON_LAUNCHER}" >&2
    exit 70
}
[ -f "${STRATEGY_LAB_STAGE_ADAPTER}" ] || {
    echo "ERROR: Strategy Lab stage adapter is unavailable: ${STRATEGY_LAB_STAGE_ADAPTER}" >&2
    exit 70
}
export STRATEGY_LAB_STAGE_ADAPTER

exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"
