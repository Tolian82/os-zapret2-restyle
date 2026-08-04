#!/bin/sh

STRATEGY_LAB_EXPANSION_CATALOG="${STRATEGY_LAB_EXPANSION_CATALOG:-${MODULE_DIR}/catalog/tls13-expansion.tsv}"
STRATEGY_LAB_EXPANSION_ARGS_DIR="${STRATEGY_LAB_EXPANSION_ARGS_DIR:-${MODULE_DIR}/catalog/tls13-expansion}"
STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT="${STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT:-5}"
STRATEGY_LAB_EXPANSION_TARGET="${STRATEGY_LAB_EXPANSION_TARGET:-5}"

strategy_lab_expansion_family_accepted()
{
    _slexpa_result="$1"
    _slexpa_family="$2"
    "${STRATEGY_LAB_JQ}" -e --arg family "${_slexpa_family}" \
        '.accepted | index($family) != null' "${_slexpa_result}" >/dev/null
}

strategy_lab_expansion_available_count()
{
    _slexpc_result="$1"
    _slexpc_count=0
    _slexpc_tab=$(printf '\t')
    while IFS="${_slexpc_tab}" read -r _slexpc_family _slexpc_id _slexpc_hostlist _slexpc_args
    do
        [ -n "${_slexpc_id}" ] || continue
        if strategy_lab_expansion_family_accepted "${_slexpc_result}" "${_slexpc_family}"; then
            _slexpc_count=$((_slexpc_count + 1))
        fi
    done < "${STRATEGY_LAB_EXPANSION_CATALOG}"
    printf '%s\n' "${_slexpc_count}"
}

strategy_lab_expansion_initialize()
{
    _slexpi_output="$1"
    _slexpi_total="$2"
    "${STRATEGY_LAB_JQ}" -nc --argjson total "${_slexpi_total}" \
        '{total_available:$total,completed:0,candidates:[],working:[],failed:[],stopped_reason:""}' |
        strategy_lab_atomic_write "${_slexpi_output}"
}

strategy_lab_expansion_append()
{
    _slexpp_output="$1"
    _slexpp_candidate="$2"
    _slexpp_tmp=$(mktemp "$(dirname "${_slexpp_output}")/.expansion.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_slexpp_candidate}" '
        .candidates += $candidate |
        .completed = (.candidates | length) |
        .working = [.candidates[] | select(.all_pass == true) | .id] |
        .failed = [.candidates[] | select(.all_pass != true) | .id]
    ' "${_slexpp_output}" > "${_slexpp_tmp}" || {
        rm -f "${_slexpp_tmp}"
        return 1
    }
    chmod 0644 "${_slexpp_tmp}"
    mv -f "${_slexpp_tmp}" "${_slexpp_output}"
}

strategy_lab_expansion_set_reason()
{
    _slexpr_output="$1"
    _slexpr_reason="$2"
    _slexpr_tmp=$(mktemp "$(dirname "${_slexpr_output}")/.expansion-reason.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg reason "${_slexpr_reason}" '.stopped_reason=$reason' \
        "${_slexpr_output}" > "${_slexpr_tmp}" || {
            rm -f "${_slexpr_tmp}"
            return 1
        }
    chmod 0644 "${_slexpr_tmp}"
    mv -f "${_slexpr_tmp}" "${_slexpr_output}"
}

strategy_lab_expansion_timeout_result()
{
    _slext_id="$1"
    _slext_family="$2"
    _slext_args="$3"
    _slext_output="$4"
    "${STRATEGY_LAB_JQ}" -nc \
        --arg id "${_slext_id}" \
        --arg family "${_slext_family}" \
        --rawfile strategy "${_slext_args}" \
        '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false,timeout:true}' \
        > "${_slext_output}"
}

strategy_lab_expansion_run()
{
    _slex_job="$1"
    _slex_endpoints="$2"
    _slex_family_result="$3"
    _slex_output="$4"
    _slex_work=$(strategy_lab_job_dir "${_slex_job}")/parameter-expansion
    _slex_tab=$(printf '\t')

    [ -r "${STRATEGY_LAB_EXPANSION_CATALOG}" ] || return 1
    [ -r "${_slex_family_result}" ] || return 1
    [ -x "${STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER}" ] || return 1
    mkdir -p "${_slex_work}" || return 1
    _slex_total=$(strategy_lab_expansion_available_count "${_slex_family_result}") || return 1
    strategy_lab_expansion_initialize "${_slex_output}" "${_slex_total}" || return 1
    if [ "${_slex_total}" -eq 0 ]; then
        strategy_lab_expansion_set_reason "${_slex_output}" no_accepted_family
        return 0
    fi

    while IFS="${_slex_tab}" read -r _slex_family _slex_id _slex_hostlist _slex_args_name
    do
        [ -n "${_slex_id}" ] || continue
        strategy_lab_expansion_family_accepted "${_slex_family_result}" "${_slex_family}" || continue
        _slex_args="${STRATEGY_LAB_EXPANSION_ARGS_DIR}/${_slex_args_name}"
        _slex_candidate="${_slex_work}/${_slex_id}.json"
        [ -r "${_slex_args}" ] || return 1

        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT}" \
            "${STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER}" \
            "${_slex_job}" "${_slex_endpoints}" "${_slex_candidate}" \
            "${_slex_id}" "${_slex_family}" "${_slex_args}" "${_slex_hostlist}"
        then
            _slex_status=0
        else
            _slex_status=$?
        fi
        case "${_slex_status}" in
            0) [ -r "${_slex_candidate}" ] || return 1 ;;
            124) strategy_lab_expansion_timeout_result "${_slex_id}" "${_slex_family}" "${_slex_args}" "${_slex_candidate}" || return 1 ;;
            *) return "${_slex_status}" ;;
        esac
        strategy_lab_expansion_append "${_slex_output}" "${_slex_candidate}" || return 1
        _slex_working=$("${STRATEGY_LAB_JQ}" -r '.working | length' "${_slex_output}")
        if [ "${_slex_working}" -ge "${STRATEGY_LAB_EXPANSION_TARGET}" ]; then
            strategy_lab_expansion_set_reason "${_slex_output}" enough_candidates
            return 0
        fi
    done < "${STRATEGY_LAB_EXPANSION_CATALOG}"

    strategy_lab_expansion_set_reason "${_slex_output}" catalog_exhausted
}

strategy_lab_set_parameter_expansion_result()
{
    _slexs_job="$1"
    _slexs_result="$2"
    _slexs_status=$(strategy_lab_status_file "${_slexs_job}")
    _slexs_tmp=$(mktemp "$(dirname "${_slexs_status}")/.parameter-expansion.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile expansion "${_slexs_result}" \
        '.parameter_expansion=$expansion[0]' "${_slexs_status}" > "${_slexs_tmp}" || {
            rm -f "${_slexs_tmp}"
            return 1
        }
    chmod 0644 "${_slexs_tmp}"
    mv -f "${_slexs_tmp}" "${_slexs_status}"
}

strategy_lab_skip_remaining()
{
    _slexk_job="$1"
    _slexk_message="$2"
    _slexk_status=$(strategy_lab_status_file "${_slexk_job}")
    _slexk_tmp=$(mktemp "$(dirname "${_slexk_status}")/.skip.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg message "${_slexk_message}" '
        (.stages[] | select((.status=="PENDING" or .status=="RUNNING") and .number!="90" and .number!="99") | .status)="SKIPPED" |
        (.stages[] | select(.status=="SKIPPED" and .message=="") | .message)=$message
    ' "${_slexk_status}" > "${_slexk_tmp}" || {
        rm -f "${_slexk_tmp}"
        return 1
    }
    chmod 0644 "${_slexk_tmp}"
    mv -f "${_slexk_tmp}" "${_slexk_status}"
}

strategy_lab_skip_unfinished()
{
    _slexu_job="$1"
    _slexu_message="$2"
    _slexu_status=$(strategy_lab_status_file "${_slexu_job}")
    _slexu_stage50=$("${STRATEGY_LAB_JQ}" -r '.stages[] | select(.number=="50") | .status' "${_slexu_status}" 2>/dev/null || true)
    _slexu_stage60=$("${STRATEGY_LAB_JQ}" -r '.stages[] | select(.number=="60") | .status' "${_slexu_status}" 2>/dev/null || true)

    if [ "${_slexu_stage50}" = PASS ] && [ "${_slexu_stage60}" = PENDING ] &&
        [ ! -e "$(strategy_lab_cancel_file "${_slexu_job}")" ]; then
        strategy_lab_update_stage "${_slexu_job}" 60 RUNNING '' || return 1
        strategy_lab_append_event "${_slexu_job}" 60 RUNNING 'Expanding parameters inside accepted TLS 1.3 families' || return 1
        _slexu_jobdir=$(strategy_lab_job_dir "${_slexu_job}")
        _slexu_family="${_slexu_jobdir}/candidate-smoke.json"
        _slexu_endpoints="${_slexu_jobdir}/endpoints.txt"
        _slexu_result="${_slexu_jobdir}/parameter-expansion.json"
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE60_TIMEOUT}" \
            "${EXPANSION_RUNNER}" "${_slexu_job}" "${_slexu_endpoints}" "${_slexu_family}" "${_slexu_result}"
        then
            _slexu_run_status=0
        else
            _slexu_run_status=$?
        fi
        if [ -r "${_slexu_result}" ]; then
            strategy_lab_set_parameter_expansion_result "${_slexu_job}" "${_slexu_result}" || return 1
        fi
        [ "${_slexu_run_status}" -ne 124 ] || worker_stage_timeout 60
        [ "${_slexu_run_status}" -eq 0 ] || worker_error 60 'Accepted-family parameter expansion failed internally.'
        [ -r "${_slexu_result}" ] || worker_error 60 'Parameter expansion result was not produced.'
        _slexu_working=$("${STRATEGY_LAB_JQ}" -r '.working | length' "${_slexu_result}")
        _slexu_completed=$("${STRATEGY_LAB_JQ}" -r '.completed' "${_slexu_result}")
        if [ "${LANGUAGE}" = ru ]; then
            _slexu_stage_message="PASS — Расширение параметров завершено: рабочих кандидатов ${_slexu_working}, проверено ${_slexu_completed}."
        else
            _slexu_stage_message="PASS — Parameter expansion completed: ${_slexu_working} working candidates from ${_slexu_completed} tested."
        fi
        strategy_lab_update_stage "${_slexu_job}" 60 PASS "${_slexu_stage_message}" || return 1
        strategy_lab_append_event "${_slexu_job}" 60 PASS "${_slexu_stage_message}" || return 1
    fi

    strategy_lab_skip_remaining "${_slexu_job}" "${_slexu_message}"
}
