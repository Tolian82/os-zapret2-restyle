#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"; MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
for module in common target request udp_request result firewall runtime readiness candidate udp_candidate
do path="${MODULE_DIR}/${module}.sh"; [ -r "${path}" ] || exit 1; . "${path}"; done
strategy_lab_require_jq
JOB_ID="$1"; ENDPOINTS_FILE="$2"; RESULT_FILE="$3"; CANDIDATE_ID="$4"; FAMILY="$5"; STRATEGY_FILE="$6"
strategy_lab_job_id_valid "${JOB_ID}" || exit 64
case "${STRATEGY_LAB_UDP_PORT:-}" in ''|*[!0-9]*) exit 64 ;; esac
[ -r "${STRATEGY_LAB_UDP_PAYLOAD_FILE:-}" ] || exit 64
cleanup(){ strategy_lab_candidate_cleanup "${JOB_ID}" || true; }; trap cleanup EXIT HUP INT TERM
strategy_lab_run_candidate "${JOB_ID}" "${ENDPOINTS_FILE}" "${RESULT_FILE}" "${CANDIDATE_ID}" "${FAMILY}" "${STRATEGY_FILE}" 0
strategy_lab_candidate_attach_runtime_evidence "${JOB_ID}" "${RESULT_FILE}"
