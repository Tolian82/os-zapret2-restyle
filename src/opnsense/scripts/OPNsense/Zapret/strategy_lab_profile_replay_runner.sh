#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
umask 022
for module in common target request result firewall runtime readiness interception candidate profile profile_runtime
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 1
    . "${path}"
done
strategy_lab_require_jq
JOB_ID="${1:-}"
ENDPOINTS_FILE="${2:-}"
RESULT_FILE="${3:-}"
CANDIDATE_ID="${4:-}"
FAMILY="${5:-}"
PROFILE_FILE="${6:-}"
TARGET="${7:-}"
TARGET_TYPE="${8:-}"
strategy_lab_job_id_valid "${JOB_ID}" || exit 64
[ -r "${ENDPOINTS_FILE}" ] && [ -r "${PROFILE_FILE}" ] && [ -n "${RESULT_FILE}" ] || exit 64
strategy_lab_profile_validate "${TARGET}" "${TARGET_TYPE}" "${PROFILE_FILE}" || exit 64
STRATEGY_LAB_PROFILE_TARGET="${TARGET}"
STRATEGY_LAB_PROFILE_TARGET_TYPE="${TARGET_TYPE}"
export STRATEGY_LAB_PROFILE_TARGET STRATEGY_LAB_PROFILE_TARGET_TYPE
cleanup()
{
    strategy_lab_candidate_cleanup "${JOB_ID}" || true
}
trap cleanup EXIT HUP INT TERM
strategy_lab_run_candidate "${JOB_ID}" "${ENDPOINTS_FILE}" "${RESULT_FILE}" \
    "${CANDIDATE_ID}" "${FAMILY}" "${PROFILE_FILE}" 1
strategy_lab_candidate_attach_runtime_evidence "${JOB_ID}" "${RESULT_FILE}"
tmp="${RESULT_FILE}.tmp.$$"
"${STRATEGY_LAB_JQ}" --rawfile profile "${PROFILE_FILE}" \
    --arg target "${TARGET}" --arg target_type "${TARGET_TYPE}" '
    .profile=$profile |
    .target=$target |
    .target_type=$target_type |
    .profile_exact=(.strategy==$profile)
' "${RESULT_FILE}" > "${tmp}" || {
    rm -f "${tmp}"
    exit 1
}
mv -f "${tmp}" "${RESULT_FILE}"
"${STRATEGY_LAB_JQ}" -e '.all_pass==true and .profile_exact==true' "${RESULT_FILE}" >/dev/null
