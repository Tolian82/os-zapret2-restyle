#!/bin/sh

STRATEGY_LAB_EXPANSION_CATALOG="${STRATEGY_LAB_EXPANSION_CATALOG:-${MODULE_DIR}/catalog/tls13-expansion.tsv}"
STRATEGY_LAB_EXPANSION_ARGS_DIR="${STRATEGY_LAB_EXPANSION_ARGS_DIR:-${MODULE_DIR}/catalog/tls13-expansion}"
STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT="${STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT:-5}"
STRATEGY_LAB_EXPANSION_TARGET="${STRATEGY_LAB_EXPANSION_TARGET:-5}"

strategy_lab_expansion_family_accepted()
{
    "${STRATEGY_LAB_JQ}" -e --arg family "$2" '.accepted | index($family) != null' "$1" >/dev/null
}

strategy_lab_expansion_available_count()
{
    _slexpc_result="$1"; _slexpc_count=0; _slexpc_tab=$(printf '\t')
    while IFS="${_slexpc_tab}" read -r _slexpc_family _slexpc_id _slexpc_hostlist _slexpc_args; do
        [ -n "${_slexpc_id}" ] || continue
        if strategy_lab_expansion_family_accepted "${_slexpc_result}" "${_slexpc_family}"; then _slexpc_count=$((_slexpc_count + 1)); fi
    done < "${STRATEGY_LAB_EXPANSION_CATALOG}"
    printf '%s\n' "${_slexpc_count}"
}

strategy_lab_expansion_initialize()
{
    "${STRATEGY_LAB_JQ}" -nc --argjson total "$2" '{total_available:$total,completed:0,candidates:[],working:[],failed:[],stopped_reason:""}' |
        strategy_lab_atomic_write "$1"
}

strategy_lab_expansion_append()
{
    _slexpp_output="$1"; _slexpp_candidate="$2"; _slexpp_tmp=$(mktemp "$(dirname "${_slexpp_output}")/.expansion.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_slexpp_candidate}" '
        .candidates += $candidate | .completed=(.candidates|length) |
        .working=[.candidates[]|select(.all_pass==true)|.id] |
        .failed=[.candidates[]|select(.all_pass!=true)|.id]
    ' "${_slexpp_output}" > "${_slexpp_tmp}" || { rm -f "${_slexpp_tmp}"; return 1; }
    chmod 0644 "${_slexpp_tmp}"; mv -f "${_slexpp_tmp}" "${_slexpp_output}"
}

strategy_lab_expansion_set_reason()
{
    _slexpr_output="$1"; _slexpr_tmp=$(mktemp "$(dirname "${_slexpr_output}")/.expansion-reason.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg reason "$2" '.stopped_reason=$reason' "${_slexpr_output}" > "${_slexpr_tmp}" || { rm -f "${_slexpr_tmp}"; return 1; }
    chmod 0644 "${_slexpr_tmp}"; mv -f "${_slexpr_tmp}" "${_slexpr_output}"
}

strategy_lab_expansion_timeout_result()
{
    "${STRATEGY_LAB_JQ}" -nc --arg id "$1" --arg family "$2" --rawfile strategy "$3" \
        '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false,timeout:true}' > "$4"
}

strategy_lab_expansion_run()
{
    _slex_job="$1"; _slex_endpoints="$2"; _slex_family_result="$3"; _slex_output="$4"
    _slex_work=$(strategy_lab_job_dir "${_slex_job}")/parameter-expansion; _slex_tab=$(printf '\t')
    [ -r "${STRATEGY_LAB_EXPANSION_CATALOG}" ] || return 1
    [ -r "${_slex_family_result}" ] || return 1
    [ -x "${STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER}" ] || return 1
    mkdir -p "${_slex_work}" || return 1
    _slex_total=$(strategy_lab_expansion_available_count "${_slex_family_result}") || return 1
    strategy_lab_expansion_initialize "${_slex_output}" "${_slex_total}" || return 1
    if [ "${_slex_total}" -eq 0 ]; then strategy_lab_expansion_set_reason "${_slex_output}" no_accepted_family; return 0; fi

    while IFS="${_slex_tab}" read -r _slex_family _slex_id _slex_hostlist _slex_args_name; do
        [ -n "${_slex_id}" ] || continue
        strategy_lab_expansion_family_accepted "${_slex_family_result}" "${_slex_family}" || continue
        _slex_args="${STRATEGY_LAB_EXPANSION_ARGS_DIR}/${_slex_args_name}"; _slex_candidate="${_slex_work}/${_slex_id}.json"
        [ -r "${_slex_args}" ] || return 1
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT}" "${STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER}" \
            "${_slex_job}" "${_slex_endpoints}" "${_slex_candidate}" "${_slex_id}" "${_slex_family}" "${_slex_args}" "${_slex_hostlist}"; then _slex_status=0; else _slex_status=$?; fi
        case "${_slex_status}" in
            0) [ -r "${_slex_candidate}" ] || return 1 ;;
            124) strategy_lab_expansion_timeout_result "${_slex_id}" "${_slex_family}" "${_slex_args}" "${_slex_candidate}" || return 1 ;;
            *) return "${_slex_status}" ;;
        esac
        strategy_lab_expansion_append "${_slex_output}" "${_slex_candidate}" || return 1
        _slex_working=$("${STRATEGY_LAB_JQ}" -r '.working|length' "${_slex_output}")
        if [ "${_slex_working}" -ge "${STRATEGY_LAB_EXPANSION_TARGET}" ]; then strategy_lab_expansion_set_reason "${_slex_output}" enough_candidates; return 0; fi
    done < "${STRATEGY_LAB_EXPANSION_CATALOG}"
    strategy_lab_expansion_set_reason "${_slex_output}" catalog_exhausted
}

strategy_lab_set_parameter_expansion_result()
{
    _slexs_job="$1"; _slexs_result="$2"
    if command -v strategy_lab_state_transform >/dev/null 2>&1; then
        strategy_lab_state_transform "${_slexs_job}" '.parameter_expansion=$expansion[0]' --slurpfile expansion "${_slexs_result}"
        return $?
    fi
    _slexs_status=$(strategy_lab_status_file "${_slexs_job}"); _slexs_tmp=$(mktemp "$(dirname "${_slexs_status}")/.parameter-expansion.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile expansion "${_slexs_result}" '.parameter_expansion=$expansion[0]' "${_slexs_status}" > "${_slexs_tmp}" || { rm -f "${_slexs_tmp}"; return 1; }
    chmod 0644 "${_slexs_tmp}"; mv -f "${_slexs_tmp}" "${_slexs_status}"
}
