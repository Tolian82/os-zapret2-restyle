#!/bin/sh

# Production Stage-60 owner for controlled-parallel warm candidates. The normal Strategy
# Lab orchestrator already owns the lifecycle lock and has stopped the normal Zapret2 service;
# this wrapper owns only the dedicated warm-worker session and guarantees cleanup on exit.

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
PARALLEL_ADAPTER="${STRATEGY_LAB_STAGE60_PARALLEL_ADAPTER:-${SCRIPT_DIR}/strategy_lab_model_b_parallel_adapter.sh}"
STRATEGY_LAB_RUN_DIR="${STRATEGY_LAB_RUN_DIR:-/var/run/zapret2-restyle/strategy-lab}"
JOB_ID="${1:-}"

set -u
umask 022

[ "$#" -eq 4 ] || exit 64
case "${JOB_ID}" in job.*) ;; *) exit 64 ;; esac
[ -x "${PYTHON_LAUNCHER}" ] || exit 69

SESSION_ROOT="${STRATEGY_LAB_RUN_DIR}/stage60-parallel"
SESSION_DIR="${SESSION_ROOT}/${JOB_ID}.$$"
STRATEGY_LAB_MODEL_B_SESSION_DIR="${SESSION_DIR}"
STRATEGY_LAB_MODEL_B_SYSTEM_ADAPTER="${PARALLEL_ADAPTER}"
export STRATEGY_LAB_MODEL_B_SESSION_DIR STRATEGY_LAB_MODEL_B_SYSTEM_ADAPTER

mkdir -p "${SESSION_DIR}/workers" || exit 70
chmod 0711 "${SESSION_ROOT}" "${SESSION_DIR}" "${SESSION_DIR}/workers" 2>/dev/null || exit 70

child=''
cleaned=0

cleanup()
{
    [ "${cleaned}" -eq 0 ] || return 0
    cleaned=1
    if [ -x "${PARALLEL_ADAPTER}" ]; then
        "${PARALLEL_ADAPTER}" cleanup-all >/dev/null 2>&1 || true
    fi
    chmod 0700 "${SESSION_DIR}" "${SESSION_ROOT}" 2>/dev/null || true
    rm -rf "${SESSION_DIR}" 2>/dev/null || true
}

on_signal()
{
    trap - HUP INT TERM EXIT
    if [ -n "${child}" ]; then
        kill -TERM "${child}" 2>/dev/null || true
    fi
    cleanup
    exit 125
}

on_exit()
{
    _status=$?
    trap - HUP INT TERM EXIT
    cleanup
    exit "${_status}"
}

trap on_signal HUP INT TERM
trap on_exit EXIT

"${PYTHON_LAUNCHER}" stage60-parallel expand "$1" "$2" "$3" "$4" &
child=$!
if wait "${child}"; then
    status=0
else
    status=$?
fi
child=''
exit "${status}"
