#!/bin/sh

STRATEGY_LAB_EXTENDED_CATALOG="${STRATEGY_LAB_EXTENDED_CATALOG:-${MODULE_DIR}/catalog/extended-tcp.tsv}"
STRATEGY_LAB_EXTENDED_ARGS_DIR="${STRATEGY_LAB_EXTENDED_ARGS_DIR:-${MODULE_DIR}/catalog/extended-tcp}"
STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER="${STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT="${STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT:-5}"

strategy_lab_extended_initialize()
{
    "${STRATEGY_LAB_JQ}" -nc '{protocols:{tls12:{tested:[],working:null},http:{tested:[],working:null}}}' | strategy_lab_atomic_write "$1"
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
    "${STRATEGY_LAB_JQ}" -nc --arg id "$1" --arg family "$2" --rawfile strategy "$3" \
        '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false,timeout:true}' > "$4"
}

strategy_lab_extended_run()
{
    _slextr_job="$1"; _slextr_endpoints="$2"; _slextr_output="$3"
    _slextr_work=$(strategy_lab_job_dir "${_slextr_job}")/extended-tcp; _slextr_tab=$(printf '\t')
    mkdir -p "${_slextr_work}" || return 1
    strategy_lab_extended_initialize "${_slextr_output}" || return 1
    while IFS="${_slextr_tab}" read -r _slextr_protocol _slextr_id _slextr_family _slextr_port _slextr_l7 _slextr_hostlist _slextr_args_name; do
        [ -n "${_slextr_id}" ] || continue
        if "${STRATEGY_LAB_JQ}" -e --arg p "${_slextr_protocol}" '.protocols[$p].working != null' "${_slextr_output}" >/dev/null; then continue; fi
        _slextr_args="${STRATEGY_LAB_EXTENDED_ARGS_DIR}/${_slextr_args_name}"; _slextr_candidate="${_slextr_work}/${_slextr_id}.json"
        [ -r "${_slextr_args}" ] || return 1
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_EXTENDED_CANDIDATE_TIMEOUT}" "${STRATEGY_LAB_ENV_BIN:-/usr/bin/env}" \
            STRATEGY_LAB_CANDIDATE_PROTOCOL="${_slextr_protocol}" STRATEGY_LAB_CANDIDATE_PORT="${_slextr_port}" STRATEGY_LAB_CANDIDATE_L7="${_slextr_l7}" \
            "${STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER}" "${_slextr_job}" "${_slextr_endpoints}" "${_slextr_candidate}" \
            "${_slextr_id}" "${_slextr_family}" "${_slextr_args}" "${_slextr_hostlist}"; then _slextr_status=0; else _slextr_status=$?; fi
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
    strategy_lab_set_json_field "$1" extended "$2"
}
