#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"; MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
for module in common udp; do path="${MODULE_DIR}/${module}.sh"; [ -r "${path}" ] || exit 1; . "${path}"; done
strategy_lab_require_jq
JOB_ID="$1"; ENDPOINTS_FILE="$2"; RESULT_FILE="$3"
strategy_lab_job_id_valid "${JOB_ID}" || exit 64
[ -r "${ENDPOINTS_FILE}" ] || exit 64
strategy_lab_udp_run "${JOB_ID}" "${ENDPOINTS_FILE}" "${RESULT_FILE}"
