#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
WORKER_HOLD_SECONDS="${WORKER_HOLD_SECONDS:-0}"
PROBE_RUNNER="${PROBE_RUNNER:-${SCRIPT_DIR}/strategy_lab_probe_runner.sh}"
CANDIDATE_RUNNER="${CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_family_runner.sh}"
EXPANSION_RUNNER="${EXPANSION_RUNNER:-${SCRIPT_DIR}/strategy_lab_expansion_runner.sh}"
STABILITY_RUNNER="${STABILITY_RUNNER:-${SCRIPT_DIR}/strategy_lab_stability_runner.sh}"
STRATEGY_LAB_STAGE30_TIMEOUT="${STRATEGY_LAB_STAGE30_TIMEOUT:-6}"
STRATEGY_LAB_STAGE40_TIMEOUT="${STRATEGY_LAB_STAGE40_TIMEOUT:-5}"
STRATEGY_LAB_CANDIDATE_TIMEOUT="${STRATEGY_LAB_CANDIDATE_TIMEOUT:-45}"
STRATEGY_LAB_STAGE60_TIMEOUT="${STRATEGY_LAB_STAGE60_TIMEOUT:-60}"
STRATEGY_LAB_STAGE70_TIMEOUT="${STRATEGY_LAB_STAGE70_TIMEOUT:-60}"

set -eu
umask 022

for module in common state firewall runtime candidate lifecycle target request result probe family expansion stability
do
    module_path="${MODULE_DIR}/${module}.sh"
    [ -r "${module_path}" ] || { echo "ERROR: required Strategy Lab module is missing: ${module_path}" >&2; exit 1; }
    . "${module_path}"
done

JOB_ID="${1:-}"
strategy_lab_job_id_valid "${JOB_ID}" || { echo "ERROR: invalid Strategy Lab job id" >&2; exit 64; }
strategy_lab_require_jq
for runner in "${PROBE_RUNNER}" "${CANDIDATE_RUNNER}" "${EXPANSION_RUNNER}" "${STABILITY_RUNNER}"
do
    [ -x "${runner}" ] || { echo "ERROR: Strategy Lab runner is unavailable: ${runner}" >&2; exit 1; }
done

STATUS_FILE=$(strategy_lab_status_file "${JOB_ID}")
CANCEL_FILE=$(strategy_lab_cancel_file "${JOB_ID}")
JOB_DIR=$(strategy_lab_job_dir "${JOB_ID}")
[ -r "${STATUS_FILE}" ] || { echo "ERROR: Strategy Lab job state is missing: ${JOB_ID}" >&2; exit 1; }
LANGUAGE=$("${STRATEGY_LAB_JQ}" -r '.language' "${STATUS_FILE}")
TARGET=$("${STRATEGY_LAB_JQ}" -r '.target' "${STATUS_FILE}")
MODE=$("${STRATEGY_LAB_JQ}" -r '.mode' "${STATUS_FILE}")
WORKER_FINALIZING=0

for worker_module in worker_messages worker_control worker_expansion_messages worker_stability_messages worker_flow
do
    worker_module_path="${MODULE_DIR}/${worker_module}.sh"
    [ -r "${worker_module_path}" ] || { echo "ERROR: required Strategy Lab worker module is missing: ${worker_module_path}" >&2; exit 1; }
    . "${worker_module_path}"
done
