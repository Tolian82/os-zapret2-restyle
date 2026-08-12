#!/bin/sh

set -eu
umask 022

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
WORKER="${STRATEGY_LAB_BLOB_MEASUREMENT_WORKER:-${SCRIPT_DIR}/strategy_lab_blob_measurement_worker.sh}"
LOCK_FILE="${LIFECYCLE_LOCK_FILE:-/var/run/zapret2-lifecycle.lock}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
OUTPUT="${1:-/tmp/strategy-lab-blob-startup-rss.json}"
TRIALS="${2:-9}"

case "${TRIALS}" in ''|*[!0-9]*) echo "ERROR: trials must be an integer" >&2; exit 64 ;; esac
[ "${TRIALS}" -ge 3 ] 2>/dev/null && [ "${TRIALS}" -le 15 ] 2>/dev/null || {
    echo "ERROR: trials must be between 3 and 15" >&2
    exit 64
}
[ -x "${LOCKF_BIN}" ] || { echo "ERROR: lockf is unavailable" >&2; exit 1; }
[ -r "${WORKER}" ] || { echo "ERROR: BLOB measurement worker is unavailable: ${WORKER}" >&2; exit 1; }

(
    if ! "${LOCKF_BIN}" -s -t 3 9; then
        echo "ERROR: BLOB measurement could not acquire the Zapret lifecycle lock" >&2
        exit 75
    fi
    STRATEGY_LAB_LIFECYCLE_OWNER=1
    export STRATEGY_LAB_LIFECYCLE_OWNER
    exec /bin/sh "${WORKER}" "${OUTPUT}" "${TRIALS}"
) 9>"${LOCK_FILE}"
