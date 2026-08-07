#!/bin/sh

STRATEGY_LAB_UDP_CATALOG="${STRATEGY_LAB_UDP_CATALOG:-${MODULE_DIR}/catalog/udp.tsv}"
STRATEGY_LAB_UDP_ARGS_DIR="${STRATEGY_LAB_UDP_ARGS_DIR:-${MODULE_DIR}/catalog/udp}"
STRATEGY_LAB_UDP_CANDIDATE_RUNNER="${STRATEGY_LAB_UDP_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_udp_candidate_runner.sh}"
STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT="${STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT:-5}"

strategy_lab_udp_initialize()
{
    "${STRATEGY_LAB_JQ}" -nc '{status:"pending",port:null,tested:[],working:null}' | strategy_lab_atomic_write "$1"
}

strategy_lab_udp_append()
{
    _slua_output="$1"; _slua_candidate="$2"; _slua_tmp=$(mktemp "$(dirname "${_slua_output}")/.udp.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_slua_candidate}" '
        .tested += $candidate | if $candidate[0].all_pass==true then .working=$candidate[0] | .status="working" else . end
    ' "${_slua_output}" > "${_slua_tmp}" || { rm -f "${_slua_tmp}"; return 1; }
    chmod 0644 "${_slua_tmp}"; mv -f "${_slua_tmp}" "${_slua_output}"
}

strategy_lab_udp_run()
{
    _slur_job="$1"; _slur_endpoints="$2"; _slur_output="$3"
    strategy_lab_udp_initialize "${_slur_output}" || return 1
    case "${STRATEGY_LAB_UDP_PORT:-}" in ''|*[!0-9]*) _slur_reason=udp_port_not_configured ;; *) _slur_reason= ;; esac
    [ -z "${_slur_reason}" ] && { [ "${STRATEGY_LAB_UDP_PORT}" -ge 1 ] 2>/dev/null && [ "${STRATEGY_LAB_UDP_PORT}" -le 65535 ] 2>/dev/null || _slur_reason=udp_port_invalid; }
    [ -z "${_slur_reason}" ] && { [ -r "${STRATEGY_LAB_UDP_PAYLOAD_FILE:-}" ] && [ -s "${STRATEGY_LAB_UDP_PAYLOAD_FILE}" ] || _slur_reason=udp_payload_not_configured; }
    if [ -n "${_slur_reason}" ]; then
        _slur_tmp="${_slur_output}.tmp.$$"
        "${STRATEGY_LAB_JQ}" --arg reason "${_slur_reason}" '.status="skipped"|.reason=$reason' "${_slur_output}" > "${_slur_tmp}" && mv -f "${_slur_tmp}" "${_slur_output}"
        return 0
    fi
    _slur_tmp="${_slur_output}.tmp.$$"
    "${STRATEGY_LAB_JQ}" --argjson port "${STRATEGY_LAB_UDP_PORT}" '.port=$port' "${_slur_output}" > "${_slur_tmp}" && mv -f "${_slur_tmp}" "${_slur_output}"
    _slur_work=$(strategy_lab_job_dir "${_slur_job}")/udp; mkdir -p "${_slur_work}" || return 1; _slur_tab=$(printf '\t')
    while IFS="${_slur_tab}" read -r _slur_id _slur_family _slur_args_name; do
        [ -n "${_slur_id}" ] || continue
        _slur_args="${STRATEGY_LAB_UDP_ARGS_DIR}/${_slur_args_name}"; _slur_candidate="${_slur_work}/${_slur_id}.json"
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_UDP_CANDIDATE_TIMEOUT}" "${STRATEGY_LAB_ENV_BIN:-/usr/bin/env}" \
            STRATEGY_LAB_UDP_PORT="${STRATEGY_LAB_UDP_PORT}" STRATEGY_LAB_UDP_PAYLOAD_FILE="${STRATEGY_LAB_UDP_PAYLOAD_FILE}" \
            "${STRATEGY_LAB_UDP_CANDIDATE_RUNNER}" "${_slur_job}" "${_slur_endpoints}" "${_slur_candidate}" "${_slur_id}" "${_slur_family}" "${_slur_args}"; then _slur_status=0; else _slur_status=$?; fi
        case "${_slur_status}" in
            0) [ -r "${_slur_candidate}" ] || return 1 ;;
            124) "${STRATEGY_LAB_JQ}" -nc --arg id "${_slur_id}" --arg family "${_slur_family}" --rawfile strategy "${_slur_args}" '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false,timeout:true}' > "${_slur_candidate}" ;;
            *) return "${_slur_status}" ;;
        esac
        strategy_lab_udp_append "${_slur_output}" "${_slur_candidate}" || return 1
        "${STRATEGY_LAB_JQ}" -e '.working != null' "${_slur_output}" >/dev/null && return 0
    done < "${STRATEGY_LAB_UDP_CATALOG}"
    _slur_tmp="${_slur_output}.tmp.$$"
    "${STRATEGY_LAB_JQ}" '.status="not_found"' "${_slur_output}" > "${_slur_tmp}" && mv -f "${_slur_tmp}" "${_slur_output}"
}

strategy_lab_set_udp_result()
{
    _slus_job="$1"; _slus_result="$2"
    if command -v strategy_lab_state_transform >/dev/null 2>&1; then
        strategy_lab_state_transform "${_slus_job}" '.udp=$udp[0]' --slurpfile udp "${_slus_result}"
        return $?
    fi
    _slus_status=$(strategy_lab_status_file "${_slus_job}"); _slus_tmp=$(mktemp "$(dirname "${_slus_status}")/.udp-state.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile udp "${_slus_result}" '.udp=$udp[0]' "${_slus_status}" > "${_slus_tmp}" || { rm -f "${_slus_tmp}"; return 1; }
    chmod 0644 "${_slus_tmp}"; mv -f "${_slus_tmp}" "${_slus_status}"
}
