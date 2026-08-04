#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"

set -eu
umask 022

for module in common result family
do
    module_path="${MODULE_DIR}/${module}.sh"
    [ -r "${module_path}" ] || {
        echo "ERROR: required Strategy Lab family module is missing: ${module_path}" >&2
        exit 1
    }
    . "${module_path}"
done

strategy_lab_require_jq
JOB_ID="${1:-}"
ENDPOINTS_FILE="${2:-}"
RESULT_FILE="${3:-}"
strategy_lab_job_id_valid "${JOB_ID}" || exit 64
[ -r "${ENDPOINTS_FILE}" ] || exit 64
[ -n "${RESULT_FILE}" ] || exit 64

strategy_lab_family_screen "${JOB_ID}" "${ENDPOINTS_FILE}" "${RESULT_FILE}"
