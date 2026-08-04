#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
umask 022
for module in common stability
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 1
    . "${path}"
done
strategy_lab_require_jq
JOB_ID="${1:-}"
ENDPOINTS_FILE="${2:-}"
EXPANSION_FILE="${3:-}"
FAMILY_FILE="${4:-}"
RESULT_FILE="${5:-}"
strategy_lab_job_id_valid "${JOB_ID}" || exit 64
[ -r "${ENDPOINTS_FILE}" ] && [ -r "${EXPANSION_FILE}" ] && [ -r "${FAMILY_FILE}" ] || exit 64
strategy_lab_stability_run "${JOB_ID}" "${ENDPOINTS_FILE}" "${EXPANSION_FILE}" "${FAMILY_FILE}" "${RESULT_FILE}"
