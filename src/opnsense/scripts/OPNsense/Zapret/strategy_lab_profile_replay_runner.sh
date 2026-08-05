#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
umask 022

source_module()
{
    _slprr_path="${MODULE_DIR}/$1.sh"
    [ -r "${_slprr_path}" ] || exit 1
    . "${_slprr_path}"
}

for module in common target request result firewall runtime readiness interception candidate
do
    source_module "${module}"
done

JOB_ID="${1:-}"
ENDPOINTS_FILE="${2:-}"
RESULT_FILE="${3:-}"
CANDIDATE_ID="${4:-}"
FAMILY="${5:-}"
PROFILE_FILE="${6:-}"
TARGET="${7:-}"
TARGET_TYPE="${8:-}"
PROTOCOL="${9:-tls13}"
PORT="${10:-443}"
SELECTOR_ADDRESSES="${11:-}"

case "${PROTOCOL}" in
    tls13)
        ;;
    tls12|http)
        source_module extended_request
        source_module extended_runtime
        source_module extended_candidate
        ;;
    quic)
        source_module quic_request
        source_module quic_candidate
        ;;
    udp)
        source_module udp_request
        source_module udp_candidate
        ;;
    *) exit 64 ;;
esac
source_module profile
source_module profile_runtime
strategy_lab_require_jq
strategy_lab_job_id_valid "${JOB_ID}" || exit 64
[ -r "${ENDPOINTS_FILE}" ] && [ -r "${PROFILE_FILE}" ] && [ -n "${RESULT_FILE}" ] || exit 64
strategy_lab_profile_validate_protocol \
    "${TARGET}" "${TARGET_TYPE}" "${PROTOCOL}" "${PORT}" \
    "${SELECTOR_ADDRESSES}" "${PROFILE_FILE}" || exit 64

STRATEGY_LAB_PROFILE_TARGET="${TARGET}"
STRATEGY_LAB_PROFILE_TARGET_TYPE="${TARGET_TYPE}"
STRATEGY_LAB_PROFILE_PROTOCOL="${PROTOCOL}"
STRATEGY_LAB_PROFILE_PORT="${PORT}"
STRATEGY_LAB_PROFILE_SELECTOR_ADDRESSES="${SELECTOR_ADDRESSES}"
export STRATEGY_LAB_PROFILE_TARGET STRATEGY_LAB_PROFILE_TARGET_TYPE
export STRATEGY_LAB_PROFILE_PROTOCOL STRATEGY_LAB_PROFILE_PORT
export STRATEGY_LAB_PROFILE_SELECTOR_ADDRESSES

case "${PROTOCOL}" in
    tls12)
        STRATEGY_LAB_CANDIDATE_PROTOCOL=tls12
        STRATEGY_LAB_CANDIDATE_PORT=443
        STRATEGY_LAB_CANDIDATE_L7=tls
        export STRATEGY_LAB_CANDIDATE_PROTOCOL STRATEGY_LAB_CANDIDATE_PORT STRATEGY_LAB_CANDIDATE_L7
        ;;
    http)
        STRATEGY_LAB_CANDIDATE_PROTOCOL=http
        STRATEGY_LAB_CANDIDATE_PORT=80
        STRATEGY_LAB_CANDIDATE_L7=http
        export STRATEGY_LAB_CANDIDATE_PROTOCOL STRATEGY_LAB_CANDIDATE_PORT STRATEGY_LAB_CANDIDATE_L7
        ;;
    udp)
        STRATEGY_LAB_UDP_PORT="${PORT}"
        export STRATEGY_LAB_UDP_PORT
        [ -r "${STRATEGY_LAB_UDP_PAYLOAD_FILE:-}" ] && [ -s "${STRATEGY_LAB_UDP_PAYLOAD_FILE}" ] || exit 64
        ;;
esac

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
    --arg target "${TARGET}" --arg target_type "${TARGET_TYPE}" \
    --arg protocol "${PROTOCOL}" --argjson port "${PORT}" '
    .profile=$profile |
    .target=$target |
    .target_type=$target_type |
    .protocol=$protocol |
    .port=$port |
    .profile_exact=(.strategy==$profile)
' "${RESULT_FILE}" > "${tmp}" || {
    rm -f "${tmp}"
    exit 1
}
mv -f "${tmp}" "${RESULT_FILE}"
"${STRATEGY_LAB_JQ}" -e '.all_pass==true and .profile_exact==true' "${RESULT_FILE}" >/dev/null
