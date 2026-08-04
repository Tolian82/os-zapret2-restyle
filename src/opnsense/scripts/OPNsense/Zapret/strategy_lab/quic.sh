#!/bin/sh

STRATEGY_LAB_QUIC_CATALOG="${STRATEGY_LAB_QUIC_CATALOG:-${MODULE_DIR}/catalog/quic.tsv}"
STRATEGY_LAB_QUIC_ARGS_DIR="${STRATEGY_LAB_QUIC_ARGS_DIR:-${MODULE_DIR}/catalog/quic}"
STRATEGY_LAB_QUIC_CANDIDATE_RUNNER="${STRATEGY_LAB_QUIC_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_quic_candidate_runner.sh}"
STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT="${STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT:-5}"

strategy_lab_quic_initialize()
{
    _slqi_output="$1"; _slqi_capability="$2"
    "${STRATEGY_LAB_JQ}" -nc --arg capability "${_slqi_capability}" '{capability:$capability,status:"pending",tested:[],working:null}' |
        strategy_lab_atomic_write "${_slqi_output}"
}

strategy_lab_quic_append()
{
    _slqa_output="$1"; _slqa_candidate="$2"
    _slqa_tmp=$(mktemp "$(dirname "${_slqa_output}")/.quic.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_slqa_candidate}" '.tested += $candidate | if $candidate[0].all_pass==true then .working=$candidate[0] | .status="working" else . end' "${_slqa_output}" > "${_slqa_tmp}" || { rm -f "${_slqa_tmp}"; return 1; }
    chmod 0644 "${_slqa_tmp}"; mv -f "${_slqa_tmp}" "${_slqa_output}"
}

strategy_lab_quic_run()
{
    _slqr_job="$1"; _slqr_endpoints="$2"; _slqr_network="$3"; _slqr_output="$4"
    _slqr_capability=$("${STRATEGY_LAB_JQ}" -r '.quic_ipv4 // "unknown"' "${_slqr_network}")
    strategy_lab_quic_initialize "${_slqr_output}" "${_slqr_capability}" || return 1
    if [ "${_slqr_capability}" != available ]; then
        _slqr_tmp="${_slqr_output}.tmp.$$"
        "${STRATEGY_LAB_JQ}" --arg reason "quic_ipv4_${_slqr_capability}" '.status="skipped"|.reason=$reason' "${_slqr_output}" > "${_slqr_tmp}" || return 1
        mv -f "${_slqr_tmp}" "${_slqr_output}"
        return 0
    fi
    _slqr_work=$(strategy_lab_job_dir "${_slqr_job}")/quic; mkdir -p "${_slqr_work}" || return 1
    _slqr_tab=$(printf '\t')
    while IFS="${_slqr_tab}" read -r _slqr_id _slqr_family _slqr_hostlist _slqr_args_name
    do
        [ -n "${_slqr_id}" ] || continue
        _slqr_args="${STRATEGY_LAB_QUIC_ARGS_DIR}/${_slqr_args_name}"; _slqr_candidate="${_slqr_work}/${_slqr_id}.json"
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_QUIC_CANDIDATE_TIMEOUT}" "${STRATEGY_LAB_QUIC_CANDIDATE_RUNNER}" \
            "${_slqr_job}" "${_slqr_endpoints}" "${_slqr_candidate}" "${_slqr_id}" "${_slqr_family}" "${_slqr_args}" "${_slqr_hostlist}"; then _slqr_status=0; else _slqr_status=$?; fi
        case "${_slqr_status}" in
            0) [ -r "${_slqr_candidate}" ] || return 1 ;;
            124) "${STRATEGY_LAB_JQ}" -nc --arg id "${_slqr_id}" --arg family "${_slqr_family}" --rawfile strategy "${_slqr_args}" '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false,timeout:true}' > "${_slqr_candidate}" ;;
            *) return "${_slqr_status}" ;;
        esac
        strategy_lab_quic_append "${_slqr_output}" "${_slqr_candidate}" || return 1
        "${STRATEGY_LAB_JQ}" -e '.working != null' "${_slqr_output}" >/dev/null && return 0
    done < "${STRATEGY_LAB_QUIC_CATALOG}"
    _slqr_tmp="${_slqr_output}.tmp.$$"; "${STRATEGY_LAB_JQ}" '.status="not_found"' "${_slqr_output}" > "${_slqr_tmp}" && mv -f "${_slqr_tmp}" "${_slqr_output}"
}

strategy_lab_set_quic_result()
{
    _slqs_job="$1"; _slqs_result="$2"; _slqs_status=$(strategy_lab_status_file "${_slqs_job}"); _slqs_tmp=$(mktemp "$(dirname "${_slqs_status}")/.quic-state.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile quic "${_slqs_result}" '.quic=$quic[0]' "${_slqs_status}" > "${_slqs_tmp}" || { rm -f "${_slqs_tmp}"; return 1; }
    chmod 0644 "${_slqs_tmp}"; mv -f "${_slqs_tmp}" "${_slqs_status}"
}

strategy_lab_skip_remaining()
{
    _slqh_job="$1"; _slqh_message="$2"; _slqh_status=$(strategy_lab_status_file "${_slqh_job}")
    _slqh_stage80=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="80")|.status' "${_slqh_status}"); _slqh_stage85=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="85")|.status' "${_slqh_status}")
    if [ "${MODE}" = extended ] && [ "${_slqh_stage85}" = PASS ] && [ "${_slqh_stage80}" = PENDING ] && [ ! -e "$(strategy_lab_cancel_file "${_slqh_job}")" ]; then
        strategy_lab_update_stage "${_slqh_job}" 80 RUNNING '' || return 1
        strategy_lab_append_event "${_slqh_job}" 80 RUNNING 'Testing extended TLS 1.2, HTTP, and QUIC branches' || return 1
        _slqh_dir=$(strategy_lab_job_dir "${_slqh_job}"); _slqh_ext="${_slqh_dir}/extended-tcp.json"; _slqh_quic="${_slqh_dir}/quic.json"
        "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE80_TIMEOUT}" "${EXTENDED_RUNNER}" "${_slqh_job}" "${_slqh_dir}/endpoints.txt" "${_slqh_ext}" || worker_error 80 'Extended TLS/HTTP testing failed internally.'
        "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE80_TIMEOUT}" "${QUIC_RUNNER}" "${_slqh_job}" "${_slqh_dir}/endpoints.txt" "${_slqh_dir}/network.json" "${_slqh_quic}" || worker_error 80 'QUIC testing failed internally.'
        strategy_lab_set_extended_result "${_slqh_job}" "${_slqh_ext}" || worker_error 80 'Extended result could not be recorded.'
        strategy_lab_set_quic_result "${_slqh_job}" "${_slqh_quic}" || worker_error 80 'QUIC result could not be recorded.'
        _slqh_qstatus=$("${STRATEGY_LAB_JQ}" -r '.status' "${_slqh_quic}")
        if [ "${LANGUAGE}" = ru ]; then _slqh_msg="PASS — Расширенная проверка завершена; QUIC=${_slqh_qstatus}."; else _slqh_msg="PASS — Extended testing completed; QUIC=${_slqh_qstatus}."; fi
        strategy_lab_update_stage "${_slqh_job}" 80 PASS "${_slqh_msg}" || return 1; strategy_lab_append_event "${_slqh_job}" 80 PASS "${_slqh_msg}" || return 1
    fi
    _slqh_status=$(strategy_lab_status_file "${_slqh_job}"); _slqh_tmp=$(mktemp "$(dirname "${_slqh_status}")/.skip.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg message "${_slqh_message}" '(.stages[]|select((.status=="PENDING" or .status=="RUNNING") and .number!="90" and .number!="99")|.status)="SKIPPED"|(.stages[]|select(.status=="SKIPPED" and .message=="")|.message)=$message' "${_slqh_status}" > "${_slqh_tmp}" || return 1
    chmod 0644 "${_slqh_tmp}"; mv -f "${_slqh_tmp}" "${_slqh_status}"
}
