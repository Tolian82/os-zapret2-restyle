#!/bin/sh

STRATEGY_LAB_EXTENDED_CATALOG="${STRATEGY_LAB_EXTENDED_CATALOG:-${MODULE_DIR}/catalog/extended-tcp.tsv}"
STRATEGY_LAB_EXTENDED_ARGS_DIR="${STRATEGY_LAB_EXTENDED_ARGS_DIR:-${MODULE_DIR}/catalog/extended-tcp}"
STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER="${STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT="${STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT:-5}"

strategy_lab_extended_initialize()
{
    _slexti_output="$1"
    "${STRATEGY_LAB_JQ}" -nc '{protocols:{tls12:{tested:[],working:null},http:{tested:[],working:null}}}' |
        strategy_lab_atomic_write "${_slexti_output}"
}

strategy_lab_extended_append()
{
    _slexta_output="$1"; _slexta_protocol="$2"; _slexta_candidate="$3"
    _slexta_tmp=$(mktemp "$(dirname "${_slexta_output}")/.extended.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg protocol "${_slexta_protocol}" --slurpfile candidate "${_slexta_candidate}" '
        .protocols[$protocol].tested += $candidate |
        if $candidate[0].all_pass==true then .protocols[$protocol].working=$candidate[0] else . end
    ' "${_slexta_output}" > "${_slexta_tmp}" || { rm -f "${_slexta_tmp}"; return 1; }
    chmod 0644 "${_slexta_tmp}"; mv -f "${_slexta_tmp}" "${_slexta_output}"
}

strategy_lab_extended_timeout_result()
{
    _slextt_id="$1"; _slextt_family="$2"; _slextt_args="$3"; _slextt_output="$4"
    "${STRATEGY_LAB_JQ}" -nc --arg id "${_slextt_id}" --arg family "${_slextt_family}" --rawfile strategy "${_slextt_args}" \
        '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false,timeout:true}' > "${_slextt_output}"
}

strategy_lab_extended_run()
{
    _slextr_job="$1"; _slextr_endpoints="$2"; _slextr_output="$3"
    _slextr_work=$(strategy_lab_job_dir "${_slextr_job}")/extended-tcp
    _slextr_tab=$(printf '\t')
    mkdir -p "${_slextr_work}" || return 1
    strategy_lab_extended_initialize "${_slextr_output}" || return 1
    while IFS="${_slextr_tab}" read -r _slextr_protocol _slextr_id _slextr_family _slextr_port _slextr_l7 _slextr_hostlist _slextr_args_name
    do
        [ -n "${_slextr_id}" ] || continue
        if "${STRATEGY_LAB_JQ}" -e --arg p "${_slextr_protocol}" '.protocols[$p].working != null' "${_slextr_output}" >/dev/null; then continue; fi
        _slextr_args="${STRATEGY_LAB_EXTENDED_ARGS_DIR}/${_slextr_args_name}"
        _slextr_candidate="${_slextr_work}/${_slextr_id}.json"
        [ -r "${_slextr_args}" ] || return 1
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT}" \
            "${STRATEGY_LAB_ENV_BIN:-/usr/bin/env}" \
            STRATEGY_LAB_CANDIDATE_PROTOCOL="${_slextr_protocol}" \
            STRATEGY_LAB_CANDIDATE_PORT="${_slextr_port}" \
            STRATEGY_LAB_CANDIDATE_L7="${_slextr_l7}" \
            "${STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER}" "${_slextr_job}" "${_slextr_endpoints}" "${_slextr_candidate}" \
            "${_slextr_id}" "${_slextr_family}" "${_slextr_args}" "${_slextr_hostlist}"
        then _slextr_status=0; else _slextr_status=$?; fi
        case "${_slextr_status}" in
            0) [ -r "${_slextr_candidate}" ] || return 1 ;;
            124) strategy_lab_extended_timeout_result "${_slextr_id}" "${_slextr_family}" "${_slextr_args}" "${_slextr_candidate}" || return 1 ;;
            *) return "${_slextr_status}" ;;
        esac
        strategy_lab_extended_append "${_slextr_output}" "${_slextr_protocol}" "${_slextr_candidate}" || return 1
    done < "${STRATEGY_LAB_EXTENDED_CATALOG}"
}

strategy_lab_set_extended_result()
{
    _slexts_job="$1"; _slexts_result="$2"
    _slexts_status=$(strategy_lab_status_file "${_slexts_job}")
    _slexts_tmp=$(mktemp "$(dirname "${_slexts_status}")/.extended-state.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile extended "${_slexts_result}" '.extended=$extended[0]' "${_slexts_status}" > "${_slexts_tmp}" || { rm -f "${_slexts_tmp}"; return 1; }
    chmod 0644 "${_slexts_tmp}"; mv -f "${_slexts_tmp}" "${_slexts_status}"
}

strategy_lab_skip_remaining()
{
    _slexth_job="$1"; _slexth_message="$2"
    _slexth_status=$(strategy_lab_status_file "${_slexth_job}")
    _slexth_stage80=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="80")|.status' "${_slexth_status}")
    _slexth_stage85=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="85")|.status' "${_slexth_status}")
    if [ "${MODE}" = extended ] && [ "${_slexth_stage85}" = PASS ] && [ "${_slexth_stage80}" = PENDING ] && [ ! -e "$(strategy_lab_cancel_file "${_slexth_job}")" ]; then
        strategy_lab_update_stage "${_slexth_job}" 80 RUNNING '' || return 1
        strategy_lab_append_event "${_slexth_job}" 80 RUNNING 'Testing extended TLS 1.2 and plain HTTP branches' || return 1
        _slexth_dir=$(strategy_lab_job_dir "${_slexth_job}")
        _slexth_result="${_slexth_dir}/extended-tcp.json"
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE80_TIMEOUT}" "${EXTENDED_RUNNER}" \
            "${_slexth_job}" "${_slexth_dir}/endpoints.txt" "${_slexth_result}"; then _slexth_run=0; else _slexth_run=$?; fi
        [ "${_slexth_run}" -ne 124 ] || worker_stage_timeout 80
        [ "${_slexth_run}" -eq 0 ] || worker_error 80 'Extended TLS/HTTP testing failed internally.'
        [ -r "${_slexth_result}" ] || worker_error 80 'Extended TLS/HTTP result was not produced.'
        strategy_lab_set_extended_result "${_slexth_job}" "${_slexth_result}" || worker_error 80 'Extended result could not be recorded.'
        _slexth_tls=$("${STRATEGY_LAB_JQ}" -r 'if .protocols.tls12.working then "yes" else "no" end' "${_slexth_result}")
        _slexth_http=$("${STRATEGY_LAB_JQ}" -r 'if .protocols.http.working then "yes" else "no" end' "${_slexth_result}")
        if [ "${LANGUAGE}" = ru ]; then _slexth_msg="PASS — Расширенная проверка завершена: TLS 1.2=${_slexth_tls}, HTTP=${_slexth_http}."; else _slexth_msg="PASS — Extended testing completed: TLS 1.2=${_slexth_tls}, HTTP=${_slexth_http}."; fi
        strategy_lab_update_stage "${_slexth_job}" 80 PASS "${_slexth_msg}" || return 1
        strategy_lab_append_event "${_slexth_job}" 80 PASS "${_slexth_msg}" || return 1
    fi
    _slexth_status=$(strategy_lab_status_file "${_slexth_job}")
    _slexth_tmp=$(mktemp "$(dirname "${_slexth_status}")/.skip.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg message "${_slexth_message}" '
        (.stages[] | select((.status=="PENDING" or .status=="RUNNING") and .number!="90" and .number!="99") | .status)="SKIPPED" |
        (.stages[] | select(.status=="SKIPPED" and .message=="") | .message)=$message
    ' "${_slexth_status}" > "${_slexth_tmp}" || { rm -f "${_slexth_tmp}"; return 1; }
    chmod 0644 "${_slexth_tmp}"; mv -f "${_slexth_tmp}" "${_slexth_status}"
}
