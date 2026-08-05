#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"; MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
WORKER_HOLD_SECONDS="${WORKER_HOLD_SECONDS:-0}"
PROBE_RUNNER="${PROBE_RUNNER:-${SCRIPT_DIR}/strategy_lab_probe_runner.sh}"; CANDIDATE_RUNNER="${CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_family_runner.sh}"
EXPANSION_RUNNER="${EXPANSION_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_expansion_runner.sh}"; STABILITY_RUNNER="${STABILITY_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_stability_runner.sh}"
EXTENDED_RUNNER="${EXTENDED_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_extended_runner.sh}"; QUIC_RUNNER="${QUIC_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_quic_runner.sh}"; UDP_RUNNER="${UDP_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_udp_runner.sh}"
STRATEGY_LAB_STAGE30_TIMEOUT="${STRATEGY_LAB_STAGE30_TIMEOUT:-6}"; STRATEGY_LAB_STAGE40_TIMEOUT="${STRATEGY_LAB_STAGE40_TIMEOUT:-5}"; STRATEGY_LAB_CANDIDATE_TIMEOUT="${STRATEGY_LAB_CANDIDATE_TIMEOUT:-45}"
STRATEGY_LAB_STAGE60_TIMEOUT="${STRATEGY_LAB_STAGE60_TIMEOUT:-60}"; STRATEGY_LAB_STAGE70_TIMEOUT="${STRATEGY_LAB_STAGE70_TIMEOUT:-60}"; STRATEGY_LAB_STAGE80_TIMEOUT="${STRATEGY_LAB_STAGE80_TIMEOUT:-120}"
set -eu; umask 022
for module in common state firewall runtime candidate lifecycle target request result probe family expansion stability extended quic udp
do path="${MODULE_DIR}/${module}.sh"; [ -r "${path}" ] || exit 1; . "${path}"; done
JOB_ID="${1:-}"; strategy_lab_job_id_valid "${JOB_ID}" || exit 64; strategy_lab_require_jq
for runner in "${PROBE_RUNNER}" "${CANDIDATE_RUNNER}" "${EXPANSION_RUNNER}" "${STABILITY_RUNNER}" "${EXTENDED_RUNNER}" "${QUIC_RUNNER}" "${UDP_RUNNER}"; do [ -x "${runner}" ] || exit 1; done
STATUS_FILE=$(strategy_lab_status_file "${JOB_ID}"); CANCEL_FILE=$(strategy_lab_cancel_file "${JOB_ID}"); JOB_DIR=$(strategy_lab_job_dir "${JOB_ID}"); [ -r "${STATUS_FILE}" ] || exit 1
STRATEGY_LAB_WORKER_PID=$$; export CANCEL_FILE STRATEGY_LAB_WORKER_PID
LANGUAGE=$("${STRATEGY_LAB_JQ}" -r '.language' "${STATUS_FILE}"); TARGET=$("${STRATEGY_LAB_JQ}" -r '.target' "${STATUS_FILE}"); MODE=$("${STRATEGY_LAB_JQ}" -r '.mode' "${STATUS_FILE}"); WORKER_FINALIZING=0
for worker_module in worker_messages worker_control worker_expansion_messages worker_stability_messages worker_extended_messages worker_quic_messages worker_udp_messages worker_flow
do path="${MODULE_DIR}/${worker_module}.sh"; [ -r "${path}" ] || exit 1; . "${path}"; done
