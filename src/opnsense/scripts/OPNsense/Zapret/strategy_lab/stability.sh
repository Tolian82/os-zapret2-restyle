#!/bin/sh

STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER="${STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
STRATEGY_LAB_STABILITY_ATTEMPTS="${STRATEGY_LAB_STABILITY_ATTEMPTS:-3}"
STRATEGY_LAB_STABILITY_MAX_CANDIDATES="${STRATEGY_LAB_STABILITY_MAX_CANDIDATES:-5}"
STRATEGY_LAB_STABILITY_TARGET="${STRATEGY_LAB_STABILITY_TARGET:-3}"
STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT="${STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT:-5}"
STRATEGY_LAB_ENV_BIN="${STRATEGY_LAB_ENV_BIN:-/usr/bin/env}"

strategy_lab_stability_sources()
{
    _slsts_expansion="$1"; _slsts_family="$2"; _slsts_output="$3"
    "${STRATEGY_LAB_JQ}" -n --slurpfile expansion "${_slsts_expansion}" --slurpfile family "${_slsts_family}" '
        ([($expansion[0].candidates // [])[] | select(.all_pass == true)] +
         [($family[0].families // [])[] | select(.all_pass == true)]) |
        unique_by(.strategy) |
        map(. + {line_count:(.strategy|split("\n")|map(select(length>0))|length),character_count:(.strategy|length)}) |
        sort_by(.line_count,.character_count,.id)
    ' > "${_slsts_output}"
}

strategy_lab_stability_initialize()
{
    "${STRATEGY_LAB_JQ}" -nc --argjson total "$2" '{total_candidates:$total,completed:0,candidates:[],stable:[],unstable:[],stopped_reason:""}' |
        strategy_lab_atomic_write "$1"
}

strategy_lab_stability_attempt_timeout()
{
    "${STRATEGY_LAB_JQ}" -nc --arg id "$1" --arg family "$2" --rawfile strategy "$3" --argjson attempt "$4" \
        '{id:$id,family:$family,strategy:$strategy,attempt:$attempt,endpoints:[],all_pass:false,timeout:true}' > "$5"
}

strategy_lab_stability_append()
{
    _slstap_output="$1"; _slstap_candidate="$2"; _slstap_tmp=$(mktemp "$(dirname "${_slstap_output}")/.stability.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_slstap_candidate}" '
        .candidates += $candidate | .completed=(.candidates|length) |
        .stable=[.candidates[]|select(.stable==true)|.id] |
        .unstable=[.candidates[]|select(.stable!=true)|.id]
    ' "${_slstap_output}" > "${_slstap_tmp}" || { rm -f "${_slstap_tmp}"; return 1; }
    chmod 0644 "${_slstap_tmp}"; mv -f "${_slstap_tmp}" "${_slstap_output}"
}

strategy_lab_stability_set_reason()
{
    _slstr_output="$1"; _slstr_tmp=$(mktemp "$(dirname "${_slstr_output}")/.stability-reason.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg reason "$2" '.stopped_reason=$reason' "${_slstr_output}" > "${_slstr_tmp}" || { rm -f "${_slstr_tmp}"; return 1; }
    chmod 0644 "${_slstr_tmp}"; mv -f "${_slstr_tmp}" "${_slstr_output}"
}

strategy_lab_stability_run()
{
    _slst_job="$1"; _slst_endpoints="$2"; _slst_expansion="$3"; _slst_family="$4"; _slst_output="$5"
    _slst_work=$(strategy_lab_job_dir "${_slst_job}")/stability; _slst_sources="${_slst_work}/sources.json"
    mkdir -p "${_slst_work}" || return 1
    [ -x "${STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER}" ] || return 1
    [ -x "${STRATEGY_LAB_ENV_BIN}" ] || return 1
    strategy_lab_stability_sources "${_slst_expansion}" "${_slst_family}" "${_slst_sources}" || return 1
    _slst_total=$("${STRATEGY_LAB_JQ}" -r 'length' "${_slst_sources}")
    strategy_lab_stability_initialize "${_slst_output}" "${_slst_total}" || return 1
    [ "${_slst_total}" -gt 0 ] || { strategy_lab_stability_set_reason "${_slst_output}" no_working_candidate; return 0; }

    _slst_index=0
    while IFS= read -r _slst_source; do
        [ -n "${_slst_source}" ] || continue
        _slst_index=$((_slst_index + 1)); [ "${_slst_index}" -le "${STRATEGY_LAB_STABILITY_MAX_CANDIDATES}" ] || break
        _slst_id=$(printf '%s' "${_slst_source}" | "${STRATEGY_LAB_JQ}" -r '.id')
        _slst_family_name=$(printf '%s' "${_slst_source}" | "${STRATEGY_LAB_JQ}" -r '.family')
        _slst_strategy="${_slst_work}/${_slst_index}.args"
        printf '%s' "${_slst_source}" | "${STRATEGY_LAB_JQ}" -r '.strategy' > "${_slst_strategy}" || return 1
        _slst_attempt_dir="${_slst_work}/${_slst_index}-attempts"; mkdir -p "${_slst_attempt_dir}" || return 1
        _slst_attempt=1
        while [ "${_slst_attempt}" -le "${STRATEGY_LAB_STABILITY_ATTEMPTS}" ]; do
            _slst_attempt_result="${_slst_attempt_dir}/${_slst_attempt}.json"
            if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT}" "${STRATEGY_LAB_ENV_BIN}" STRATEGY_LAB_ENDPOINT_PROBE_MODE=sequential \
                "${STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER}" "${_slst_job}" "${_slst_endpoints}" "${_slst_attempt_result}" \
                "${_slst_id}" "${_slst_family_name}" "${_slst_strategy}" 1; then _slst_attempt_status=0; else _slst_attempt_status=$?; fi
            case "${_slst_attempt_status}" in
                0) [ -r "${_slst_attempt_result}" ] || return 1 ;;
                124) strategy_lab_stability_attempt_timeout "${_slst_id}" "${_slst_family_name}" "${_slst_strategy}" "${_slst_attempt}" "${_slst_attempt_result}" || return 1 ;;
                *) return "${_slst_attempt_status}" ;;
            esac
            _slst_attempt=$((_slst_attempt + 1))
        done
        _slst_candidate_result="${_slst_work}/${_slst_index}.json"; set -- "${_slst_attempt_dir}"/*.json
        "${STRATEGY_LAB_JQ}" -s --arg id "${_slst_id}" --arg family "${_slst_family_name}" --rawfile strategy "${_slst_strategy}" '
            {id:$id,family:$family,strategy:$strategy,attempts:.,stable:(length==3 and all(.all_pass==true)),
             pass_count:([.[]|select(.all_pass==true)]|length),line_count:($strategy|split("\n")|map(select(length>0))|length),character_count:($strategy|length)}
        ' "$@" > "${_slst_candidate_result}" || return 1
        strategy_lab_stability_append "${_slst_output}" "${_slst_candidate_result}" || return 1
        _slst_stable_count=$("${STRATEGY_LAB_JQ}" -r '.stable|length' "${_slst_output}")
        if [ "${_slst_stable_count}" -ge "${STRATEGY_LAB_STABILITY_TARGET}" ]; then strategy_lab_stability_set_reason "${_slst_output}" enough_stable_candidates; return 0; fi
    done <<EOF
$("${STRATEGY_LAB_JQ}" -c '.[]' "${_slst_sources}")
EOF
    strategy_lab_stability_set_reason "${_slst_output}" candidates_exhausted
}

strategy_lab_set_stability_result()
{
    strategy_lab_state_python set-stability \
        "$1" "$(strategy_lab_status_file "$1")" "$2" "$3"
}
