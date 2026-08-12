#!/bin/sh

set -eu
umask 022

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_BIN="${STRATEGY_LAB_PYTHON_BIN:-/usr/local/bin/python3.13}"
PYTHON_ENTRY="${SCRIPT_DIR}/strategy_lab_python.py"
SERVICE_SCRIPT="${STRATEGY_LAB_SERVICE_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"
ADAPTER="${STRATEGY_LAB_BLOB_MEASUREMENT_ADAPTER:-${SCRIPT_DIR}/strategy_lab_model_b_adapter.sh}"
OUTPUT="${1:-/tmp/strategy-lab-blob-startup-rss.json}"
TRIALS="${2:-9}"

[ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] || {
    echo "ERROR: BLOB measurement worker has no lifecycle-lock owner" >&2
    exit 77
}
( : >&9 ) 2>/dev/null || {
    echo "ERROR: BLOB measurement lifecycle descriptor is unavailable" >&2
    exit 77
}
[ -x "${PYTHON_BIN}" ] || { echo "ERROR: python313 is unavailable" >&2; exit 1; }
[ -r "${PYTHON_ENTRY}" ] || { echo "ERROR: Strategy Lab Python entry is unavailable" >&2; exit 1; }
[ -r "${SERVICE_SCRIPT}" ] || { echo "ERROR: Zapret service script is unavailable" >&2; exit 1; }
[ -r "${ADAPTER}" ] || { echo "ERROR: BLOB measurement adapter is unavailable" >&2; exit 1; }

SESSION=$(mktemp -d "${TMPDIR:-/var/run}/zapret2-blob-measure.XXXXXX") || exit 1
INITIAL="${SESSION}/initial-service.json"
FINAL="${SESSION}/final-service.json"
STRATEGY_LAB_MODEL_B_SESSION_DIR="${SESSION}"
STRATEGY_LAB_BLOB_MEASUREMENT_ADAPTER="${ADAPTER}"
STRATEGY_LAB_SERVICE_SCRIPT="${SERVICE_SCRIPT}"
export STRATEGY_LAB_MODEL_B_SESSION_DIR STRATEGY_LAB_BLOB_MEASUREMENT_ADAPTER STRATEGY_LAB_SERVICE_SCRIPT

cleanup()
{
    /bin/sh "${ADAPTER}" cleanup-all >/dev/null 2>&1 || true
    rm -rf "${SESSION}"
}
trap cleanup EXIT INT TERM HUP

/bin/sh "${SERVICE_SCRIPT}" strategy-lab-evidence > "${INITIAL}"

"${PYTHON_BIN}" "${PYTHON_ENTRY}" blob-startup-measure run "${OUTPUT}" "${TRIALS}"

cleanup_ok=false
if /bin/sh "${ADAPTER}" cleanup-all >/dev/null 2>&1 && /bin/sh "${ADAPTER}" preflight >/dev/null 2>&1; then
    cleanup_ok=true
fi
/bin/sh "${SERVICE_SCRIPT}" strategy-lab-evidence > "${FINAL}"

"${PYTHON_BIN}" "${PYTHON_ENTRY}" blob-startup-measure finalize \
    "${OUTPUT}" "${INITIAL}" "${FINAL}" "${cleanup_ok}"
