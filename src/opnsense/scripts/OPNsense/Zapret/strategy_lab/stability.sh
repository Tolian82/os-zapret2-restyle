#!/bin/sh

STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER="${STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
STRATEGY_LAB_STABILITY_ATTEMPTS="${STRATEGY_LAB_STABILITY_ATTEMPTS:-3}"
STRATEGY_LAB_STABILITY_MAX_CANDIDATES="${STRATEGY_LAB_STABILITY_MAX_CANDIDATES:-5}"
STRATEGY_LAB_STABILITY_TARGET="${STRATEGY_LAB_STABILITY_TARGET:-3}"
STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT="${STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT:-5}"
STRATEGY_LAB_ENV_BIN="${STRATEGY_LAB_ENV_BIN:-/usr/bin/env}"

strategy_lab_stability_sources()
{
    _slsts_expansion="$1"
    _slsts_family="$2"
    _slsts_output="$3"
    "${STRATEGY_LAB_JQ}" -n \
        --slurpfile expansion "${_slsts_expansion}" \
        --slurpfile family "${_slsts_family}" '
        ([($expansion[0].candidates // [])[] | select(.all_pass == true)] +
         [($family[0].families // [])[] | select(.all_pass == true)]) |
        unique_by(.strategy) |
        map(. + {
            line_count: (.strategy | split("\n") | map(select(length > 0)) | length),
            character_count: (.strategy | length)
        }) |
        sort_by(.line_count, .character_count, .id)
    ' > "${_slsts_output}"
}

strategy_lab_stability_initialize()
{
    _slsti_output="$1"
    _slsti_total="$2"
    "${STRATEGY_LAB_JQ}" -nc --argjson total "${_slsti_total}" \
        '{total_candidates:$total,completed:0,candidates:[],stable:[],unstable:[],stopped_reason:""}' |
        strategy_lab_atomic_write "${_slsti_output}"
}

strategy_lab_stability_attempt_timeout()
{
    _slstat_id="$1"
    _slstat_family="$2"
    _slstat_strategy="$3"
    _slstat_attempt="$4"
    _slstat_output="$5"
    "${STRATEGY_LAB_JQ}" -nc \
        --arg id "${_slstat_id}" --arg family "${_slstat_family}" \
        --rawfile strategy "${_slstat_strategy}" --argjson attempt "${_slstat_attempt}" \
        '{id:$id,family:$family,strategy:$strategy,attempt:$attempt,endpoints:[],all_pass:false,timeout:true}' \
        > "${_slstat_output}"
}

strategy_lab_stability_append()
{
    _slstap_output="$1"
    _slstap_candidate="$2"
    _slstap_tmp=$(mktemp "$(dirname "${_slstap_output}")/.stability.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_slstap_candidate}" '
        .candidates += $candidate |
        .completed = (.candidates | length) |
        .stable = [.candidates[] | select(.stable == true) | .id] |
        .unstable = [.candidates[] | select(.stable != true) | .id]
    ' "${_slstap_output}" > "${_slstap_tmp}" || {
        rm -f "${_slstap_tmp}"
        return 1
    }
    chmod 0644 "${_slstap_tmp}"
    mv -f "${_slstap_tmp}" "${_slstap_output}"
}

strategy_lab_stability_set_reason()
{
    _slstr_output="$1"
    _slstr_reason="$2"
    _slstr_tmp=$(mktemp "$(dirname "${_slstr_output}")/.stability-reason.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg reason "${_slstr_reason}" '.stopped_reason=$reason' \
        "${_slstr_output}" > "${_slstr_tmp}" || {
        rm -f "${_slstr_tmp}"
        return 1
    }
    chmod 0644 "${_slstr_tmp}"
    mv -f "${_slstr_tmp}" "${_slstr_output}"
}

strategy_lab_stability_run()
{
    _slst_job="$1"
    _slst_endpoints="$2"
    _slst_expansion="$3"
    _slst_family="$4"
    _slst_output="$5"
    _slst_work=$(strategy_lab_job_dir "${_slst_job}")/stability
    _slst_sources="${_slst_work}/sources.json"
    mkdir -p "${_slst_work}" || return 1
    [ -x "${STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER}" ] || return 1
    [ -x "${STRATEGY_LAB_ENV_BIN}" ] || return 1
    strategy_lab_stability_sources "${_slst_expansion}" "${_slst_family}" "${_slst_sources}" || return 1
    _slst_total=$("${STRATEGY_LAB_JQ}" -r 'length' "${_slst_sources}")
    strategy_lab_stability_initialize "${_slst_output}" "${_slst_total}" || return 1
    [ "${_slst_total}" -gt 0 ] || {
        strategy_lab_stability_set_reason "${_slst_output}" no_working_candidate
        return 0
    }

    _slst_index=0
    while IFS= read -r _slst_source
    do
        [ -n "${_slst_source}" ] || continue
        _slst_index=$((_slst_index + 1))
        [ "${_slst_index}" -le "${STRATEGY_LAB_STABILITY_MAX_CANDIDATES}" ] || break
        _slst_id=$(printf '%s' "${_slst_source}" | "${STRATEGY_LAB_JQ}" -r '.id')
        _slst_family_name=$(printf '%s' "${_slst_source}" | "${STRATEGY_LAB_JQ}" -r '.family')
        _slst_strategy="${_slst_work}/${_slst_index}.args"
        printf '%s' "${_slst_source}" | "${STRATEGY_LAB_JQ}" -r '.strategy' > "${_slst_strategy}" || return 1
        _slst_attempt_dir="${_slst_work}/${_slst_index}-attempts"
        mkdir -p "${_slst_attempt_dir}" || return 1
        _slst_attempt=1
        while [ "${_slst_attempt}" -le "${STRATEGY_LAB_STABILITY_ATTEMPTS}" ]
        do
            _slst_attempt_result="${_slst_attempt_dir}/${_slst_attempt}.json"
            if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT}" \
                "${STRATEGY_LAB_ENV_BIN}" STRATEGY_LAB_ENDPOINT_PROBE_MODE=sequential \
                "${STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER}" \
                "${_slst_job}" "${_slst_endpoints}" "${_slst_attempt_result}" \
                "${_slst_id}" "${_slst_family_name}" "${_slst_strategy}" 1
            then
                _slst_attempt_status=0
            else
                _slst_attempt_status=$?
            fi
            case "${_slst_attempt_status}" in
                0) [ -r "${_slst_attempt_result}" ] || return 1 ;;
                124) strategy_lab_stability_attempt_timeout "${_slst_id}" "${_slst_family_name}" "${_slst_strategy}" "${_slst_attempt}" "${_slst_attempt_result}" || return 1 ;;
                *) return "${_slst_attempt_status}" ;;
            esac
            _slst_attempt=$((_slst_attempt + 1))
        done
        _slst_candidate_result="${_slst_work}/${_slst_index}.json"
        set -- "${_slst_attempt_dir}"/*.json
        "${STRATEGY_LAB_JQ}" -s \
            --arg id "${_slst_id}" --arg family "${_slst_family_name}" \
            --rawfile strategy "${_slst_strategy}" '
            {id:$id,family:$family,strategy:$strategy,attempts:.,
             stable:(length==3 and all(.all_pass==true)),
             pass_count:([.[] | select(.all_pass==true)] | length),
             line_count:($strategy | split("\n") | map(select(length>0)) | length),
             character_count:($strategy | length)}
        ' "$@" > "${_slst_candidate_result}" || return 1
        strategy_lab_stability_append "${_slst_output}" "${_slst_candidate_result}" || return 1
        _slst_stable_count=$("${STRATEGY_LAB_JQ}" -r '.stable | length' "${_slst_output}")
        if [ "${_slst_stable_count}" -ge "${STRATEGY_LAB_STABILITY_TARGET}" ]; then
            strategy_lab_stability_set_reason "${_slst_output}" enough_stable_candidates
            return 0
        fi
    done <<EOF
$("${STRATEGY_LAB_JQ}" -c '.[]' "${_slst_sources}")
EOF
    strategy_lab_stability_set_reason "${_slst_output}" candidates_exhausted
}

strategy_lab_shortlist_build()
{
    _slshort_stability="$1"
    _slshort_output="$2"
    "${STRATEGY_LAB_JQ}" '
        [.candidates[] | select(.stable==true)] |
        sort_by(.line_count, .character_count, .id) |
        .[0:5] as $items |
        {count:($items|length),items:$items,recommendation:($items[0] // null)}
    ' "${_slshort_stability}" > "${_slshort_output}"
}

strategy_lab_set_stability_result()
{
    _slsets_job="$1"
    _slsets_stability="$2"
    _slsets_shortlist="$3"
    _slsets_status=$(strategy_lab_status_file "${_slsets_job}")
    _slsets_tmp=$(mktemp "$(dirname "${_slsets_status}")/.stability-state.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile stability "${_slsets_stability}" --slurpfile shortlist "${_slsets_shortlist}" \
        '.stability=$stability[0] | .shortlist=$shortlist[0]' "${_slsets_status}" > "${_slsets_tmp}" || {
        rm -f "${_slsets_tmp}"
        return 1
    }
    chmod 0644 "${_slsets_tmp}"
    mv -f "${_slsets_tmp}" "${_slsets_status}"
}

strategy_lab_skip_unfinished()
{
    _slhook_job="$1"
    _slhook_message="$2"
    _slhook_status=$(strategy_lab_status_file "${_slhook_job}")
    _slhook_stage50=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="50")|.status' "${_slhook_status}" 2>/dev/null || true)
    _slhook_stage60=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="60")|.status' "${_slhook_status}" 2>/dev/null || true)

    if [ "${_slhook_stage50}" = PASS ] && [ "${_slhook_stage60}" = PENDING ] && [ ! -e "$(strategy_lab_cancel_file "${_slhook_job}")" ]; then
        strategy_lab_update_stage "${_slhook_job}" 60 RUNNING '' || return 1
        strategy_lab_append_event "${_slhook_job}" 60 RUNNING 'Expanding parameters inside accepted TLS 1.3 families' || return 1
        _slhook_dir=$(strategy_lab_job_dir "${_slhook_job}")
        _slhook_family="${_slhook_dir}/candidate-smoke.json"
        _slhook_endpoints="${_slhook_dir}/endpoints.txt"
        _slhook_expansion="${_slhook_dir}/parameter-expansion.json"
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE60_TIMEOUT}" "${EXPANSION_RUNNER}" \
            "${_slhook_job}" "${_slhook_endpoints}" "${_slhook_family}" "${_slhook_expansion}"; then _slhook_run=0; else _slhook_run=$?; fi
        [ -r "${_slhook_expansion}" ] && strategy_lab_set_parameter_expansion_result "${_slhook_job}" "${_slhook_expansion}" || true
        [ "${_slhook_run}" -ne 124 ] || worker_stage_timeout 60
        [ "${_slhook_run}" -eq 0 ] || worker_error 60 'Accepted-family parameter expansion failed internally.'
        [ -r "${_slhook_expansion}" ] || worker_error 60 'Parameter expansion result was not produced.'
        _slhook_working=$("${STRATEGY_LAB_JQ}" -r '.working|length' "${_slhook_expansion}")
        _slhook_completed=$("${STRATEGY_LAB_JQ}" -r '.completed' "${_slhook_expansion}")
        if [ "${LANGUAGE}" = ru ]; then _slhook_msg="PASS — Расширение параметров завершено: рабочих кандидатов ${_slhook_working}, проверено ${_slhook_completed}."; else _slhook_msg="PASS — Parameter expansion completed: ${_slhook_working} working candidates from ${_slhook_completed} tested."; fi
        strategy_lab_update_stage "${_slhook_job}" 60 PASS "${_slhook_msg}" || return 1
        strategy_lab_append_event "${_slhook_job}" 60 PASS "${_slhook_msg}" || return 1
    fi

    _slhook_status=$(strategy_lab_status_file "${_slhook_job}")
    _slhook_stage60=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="60")|.status' "${_slhook_status}")
    _slhook_stage70=$("${STRATEGY_LAB_JQ}" -r '.stages[]|select(.number=="70")|.status' "${_slhook_status}")
    if [ "${_slhook_stage60}" = PASS ] && [ "${_slhook_stage70}" = PENDING ] && [ ! -e "$(strategy_lab_cancel_file "${_slhook_job}")" ]; then
        strategy_lab_update_stage "${_slhook_job}" 70 RUNNING '' || return 1
        strategy_lab_append_event "${_slhook_job}" 70 RUNNING 'Confirming candidate stability with three sequential fresh-connection attempts' || return 1
        _slhook_dir=$(strategy_lab_job_dir "${_slhook_job}")
        _slhook_stability="${_slhook_dir}/stability.json"
        _slhook_shortlist="${_slhook_dir}/shortlist.json"
        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE70_TIMEOUT}" "${STABILITY_RUNNER}" \
            "${_slhook_job}" "${_slhook_dir}/endpoints.txt" "${_slhook_dir}/parameter-expansion.json" \
            "${_slhook_dir}/candidate-smoke.json" "${_slhook_stability}"; then _slhook_st=0; else _slhook_st=$?; fi
        [ "${_slhook_st}" -ne 124 ] || worker_stage_timeout 70
        [ "${_slhook_st}" -eq 0 ] || worker_error 70 'Stability confirmation failed internally.'
        [ -r "${_slhook_stability}" ] || worker_error 70 'Stability result was not produced.'
        strategy_lab_shortlist_build "${_slhook_stability}" "${_slhook_shortlist}" || worker_error 85 'Shortlist could not be constructed.'
        strategy_lab_set_stability_result "${_slhook_job}" "${_slhook_stability}" "${_slhook_shortlist}" || worker_error 70 'Stability state could not be recorded.'
        _slhook_stable=$("${STRATEGY_LAB_JQ}" -r '.stable|length' "${_slhook_stability}")
        _slhook_tested=$("${STRATEGY_LAB_JQ}" -r '.completed' "${_slhook_stability}")
        if [ "${LANGUAGE}" = ru ]; then _slhook_msg="PASS — Стабильность подтверждена: ${_slhook_stable} из ${_slhook_tested} кандидатов прошли 3 из 3 попыток."; else _slhook_msg="PASS — Stability confirmed: ${_slhook_stable} of ${_slhook_tested} candidates passed 3 of 3 attempts."; fi
        strategy_lab_update_stage "${_slhook_job}" 70 PASS "${_slhook_msg}" || return 1
        strategy_lab_append_event "${_slhook_job}" 70 PASS "${_slhook_msg}" || return 1
        strategy_lab_update_stage "${_slhook_job}" 85 RUNNING '' || return 1
        _slhook_count=$("${STRATEGY_LAB_JQ}" -r '.count' "${_slhook_shortlist}")
        _slhook_rec=$("${STRATEGY_LAB_JQ}" -r '.recommendation.id // "none"' "${_slhook_shortlist}")
        if [ "${LANGUAGE}" = ru ]; then _slhook_msg="PASS — Сформирован shortlist: ${_slhook_count}; рекомендация №1: ${_slhook_rec}."; else _slhook_msg="PASS — Shortlist created: ${_slhook_count}; recommendation #1: ${_slhook_rec}."; fi
        strategy_lab_update_stage "${_slhook_job}" 85 PASS "${_slhook_msg}" || return 1
        strategy_lab_append_event "${_slhook_job}" 85 PASS "${_slhook_msg}" || return 1
    fi
    strategy_lab_skip_remaining "${_slhook_job}" "${_slhook_message}"
}
