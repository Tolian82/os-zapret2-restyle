#!/bin/sh

# Explicit entry point for the experiment-only Model-B coexistence measurement.  It uses
# the same lifecycle lock file and ownership contract as normal Strategy Lab without
# adding a production service action.

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
WORKER="${STRATEGY_LAB_MODEL_B_WORKER:-${SCRIPT_DIR}/strategy_lab_model_b_worker.sh}"
SERVICE_SCRIPT="${STRATEGY_LAB_SERVICE_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
LIFECYCLE_LOCK_FILE="${LIFECYCLE_LOCK_FILE:-/var/run/zapret2-lifecycle.lock}"
LOCK_TIMEOUT="${STRATEGY_LAB_MODEL_B_LOCK_TIMEOUT:-3}"
REFERENCE_JOB="${1:-}"
OUTPUT="${2:-}"

set -eu

case "${REFERENCE_JOB}" in job.*) ;; *) echo 'ERROR: invalid Model B reference job id' >&2; exit 64 ;; esac
[ -n "${OUTPUT}" ] || { echo 'usage: strategy_lab_model_b.sh REFERENCE_JOB OUTPUT' >&2; exit 64; }
[ -x "${WORKER}" ] || { echo "ERROR: Model B worker is unavailable: ${WORKER}" >&2; exit 70; }
[ -x "${SERVICE_SCRIPT}" ] || { echo "ERROR: Zapret2 service control is unavailable: ${SERVICE_SCRIPT}" >&2; exit 70; }
[ -x "${LOCKF_BIN}" ] || { echo "ERROR: lifecycle lock utility is unavailable: ${LOCKF_BIN}" >&2; exit 70; }

(
    if ! "${LOCKF_BIN}" -s -t "${LOCK_TIMEOUT}" 9; then
        echo 'ERROR: Model B could not acquire the Zapret2 lifecycle lock' >&2
        exit 75
    fi
    STRATEGY_LAB_LIFECYCLE_OWNER=1
    STRATEGY_LAB_SERVICE_SCRIPT="${SERVICE_SCRIPT}"
    export STRATEGY_LAB_LIFECYCLE_OWNER STRATEGY_LAB_SERVICE_SCRIPT
    exec "${WORKER}" "${REFERENCE_JOB}" "${OUTPUT}"
) 9>"${LIFECYCLE_LOCK_FILE}"
