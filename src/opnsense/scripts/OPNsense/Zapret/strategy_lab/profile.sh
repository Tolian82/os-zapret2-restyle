#!/bin/sh

STRATEGY_LAB_PROFILE_REPLAY_RUNNER="${STRATEGY_LAB_PROFILE_REPLAY_RUNNER:-${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh}"
STRATEGY_LAB_PROFILE_REPLAY_ATTEMPTS=3
STRATEGY_LAB_PROFILE_REPLAY_ATTEMPT_TIMEOUT="${STRATEGY_LAB_PROFILE_REPLAY_ATTEMPT_TIMEOUT:-45}"
STRATEGY_LAB_PROFILE_ENV_BIN="${STRATEGY_LAB_PROFILE_ENV_BIN:-/usr/bin/env}"

strategy_lab_profile_selector()
{
    _slpsel_target="$1"
    _slpsel_type="$2"
    case "${_slpsel_type}" in
        domain)
            strategy_lab_domain_valid "${_slpsel_target}" || return 1
            printf '%s\n' "--hostlist-domains=${_slpsel_target}"
            ;;
        ip)
            strategy_lab_ipv4_valid "${_slpsel_target}" || return 1
            printf '%s\n' "--ipset-ip=${_slpsel_target}"
            ;;
        *) return 1 ;;
    esac
}

strategy_lab_profile_fragment_line_allowed()
{
    case "$1" in
        ''|--new) return 1 ;;
        --port=*|--lua-init=*|--sockarg=*|--user=*|--uid=*|--gid=*|\
        --daemon*|--pidfile=*|--qnum=*|--bind-*|--socket=*|\
        --hostlist*|--ipset*|\
        '<HOSTLIST:'*|' <HOSTLIST:'*|'<IPSET:'*|' <IPSET:'*)
            return 1
            ;;
    esac
    return 0
}

strategy_lab_profile_build()
{
    _slpb_target="$1"
    _slpb_type="$2"
    _slpb_fragment="$3"
    _slpb_output="$4"
    [ -r "${_slpb_fragment}" ] && [ -s "${_slpb_fragment}" ] || return 1
    _slpb_selector=$(strategy_lab_profile_selector "${_slpb_target}" "${_slpb_type}") || return 1
    _slpb_tmp="${_slpb_output}.tmp.$$"
    (
        printf '%s\n' '--filter-tcp=443' '--filter-l7=tls' "${_slpb_selector}" '--out-range=-d10'
        _slpb_lines=0
        while IFS= read -r _slpb_line || [ -n "${_slpb_line}" ]
        do
            [ -n "${_slpb_line}" ] || continue
            strategy_lab_profile_fragment_line_allowed "${_slpb_line}" || exit 1
            printf '%s\n' "${_slpb_line}"
            _slpb_lines=$((_slpb_lines + 1))
        done < "${_slpb_fragment}"
        [ "${_slpb_lines}" -gt 0 ] || exit 1
    ) > "${_slpb_tmp}" || {
        rm -f "${_slpb_tmp}"
        return 1
    }
    strategy_lab_profile_validate "${_slpb_target}" "${_slpb_type}" "${_slpb_tmp}" || {
        rm -f "${_slpb_tmp}"
        return 1
    }
    chmod 0644 "${_slpb_tmp}"
    mv -f "${_slpb_tmp}" "${_slpb_output}"
}

strategy_lab_profile_validate()
{
    _slpv_target="$1"
    _slpv_type="$2"
    _slpv_file="$3"
    [ -r "${_slpv_file}" ] && [ -s "${_slpv_file}" ] || return 1
    _slpv_selector=$(strategy_lab_profile_selector "${_slpv_target}" "${_slpv_type}") || return 1
    [ "$(grep -Fxc -- "${_slpv_selector}" "${_slpv_file}")" -eq 1 ] || return 1
    [ "$(grep -Ec '^--(hostlist-domains|ipset-ip)=' "${_slpv_file}")" -eq 1 ] || return 1
    grep -Fqx -- '--filter-tcp=443' "${_slpv_file}" || return 1
    grep -Fqx -- '--filter-l7=tls' "${_slpv_file}" || return 1
    grep -Fqx -- '--out-range=-d10' "${_slpv_file}" || return 1
    grep -Eq '^--lua-desync=' "${_slpv_file}" || return 1
    if grep -Eq '^--(port|lua-init|sockarg|user|uid|gid|daemon|pidfile|qnum|bind-|socket)=' "${_slpv_file}"; then
        return 1
    fi
    awk -v selector="${_slpv_selector}" '
        /^--(hostlist|ipset)/ && $0 != selector { exit 1 }
        /^[[:space:]]*<(HOSTLIST|IPSET):/ { exit 1 }
    ' "${_slpv_file}" || return 1
}

strategy_lab_profile_attempt_failure()
{
    _slpa_id="$1"
    _slpa_family="$2"
    _slpa_profile="$3"
    _slpa_attempt="$4"
    _slpa_status="$5"
    _slpa_output="$6"
    "${STRATEGY_LAB_JQ}" -nc \
        --arg id "${_slpa_id}" --arg family "${_slpa_family}" \
        --rawfile profile "${_slpa_profile}" --argjson attempt "${_slpa_attempt}" \
        --arg status "${_slpa_status}" \
        '{id:$id,family:$family,strategy:$profile,profile:$profile,attempt:$attempt,
          runner_status:$status,endpoints:[],all_pass:false,profile_exact:false}' \
        > "${_slpa_output}"
}

strategy_lab_shortlist_build()
{
    _slps_stability="$1"
    _slps_output="$2"
    _slps_job_dir=$(dirname "${_slps_stability}")
    _slps_job=$(basename "${_slps_job_dir}")
    _slps_status=$(strategy_lab_status_file "${_slps_job}")
    _slps_endpoints="${_slps_job_dir}/endpoints.txt"
    [ -r "${_slps_stability}" ] && [ -r "${_slps_status}" ] &&
        [ -s "${_slps_endpoints}" ] || return 1
    [ -x "${STRATEGY_LAB_PROFILE_REPLAY_RUNNER}" ] || return 1
    [ -x "${STRATEGY_LAB_PROFILE_ENV_BIN}" ] || return 1

    _slps_target=$("${STRATEGY_LAB_JQ}" -r '.target // empty' "${_slps_status}") || return 1
    _slps_type=$("${STRATEGY_LAB_JQ}" -r '.target_type // empty' "${_slps_status}") || return 1
    strategy_lab_profile_selector "${_slps_target}" "${_slps_type}" >/dev/null || return 1

    _slps_work="${_slps_job_dir}/profile-replay"
    _slps_sources="${_slps_work}/sources.json"
    _slps_items="${_slps_work}/items"
    rm -rf "${_slps_work}"
    mkdir -p "${_slps_items}" || return 1
    "${STRATEGY_LAB_JQ}" '
        [.candidates[] | select(.stable==true)] |
        sort_by(.line_count, .character_count, .id) |
        .[0:5]
    ' "${_slps_stability}" > "${_slps_sources}" || return 1

    _slps_index=0
    while IFS= read -r _slps_source
    do
        [ -n "${_slps_source}" ] || continue
        _slps_index=$((_slps_index + 1))
        _slps_id=$(printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.id')
        _slps_family=$(printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.family')
        _slps_fragment="${_slps_work}/${_slps_index}.fragment.args"
        _slps_profile="${_slps_work}/${_slps_index}.profile.args"
        printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.strategy' > "${_slps_fragment}" || return 1
        strategy_lab_profile_build "${_slps_target}" "${_slps_type}" \
            "${_slps_fragment}" "${_slps_profile}" || return 1
        _slps_attempt_dir="${_slps_work}/${_slps_index}-attempts"
        mkdir -p "${_slps_attempt_dir}" || return 1

        _slps_attempt=1
        while [ "${_slps_attempt}" -le "${STRATEGY_LAB_PROFILE_REPLAY_ATTEMPTS}" ]
        do
            _slps_attempt_result="${_slps_attempt_dir}/${_slps_attempt}.json"
            if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_PROFILE_REPLAY_ATTEMPT_TIMEOUT}" \
                "${STRATEGY_LAB_PROFILE_ENV_BIN}" STRATEGY_LAB_ENDPOINT_PROBE_MODE=sequential \
                "${STRATEGY_LAB_PROFILE_REPLAY_RUNNER}" \
                "${_slps_job}" "${_slps_endpoints}" "${_slps_attempt_result}" \
                "${_slps_id}" "${_slps_family}" "${_slps_profile}" \
                "${_slps_target}" "${_slps_type}"
            then
                _slps_runner_status=0
            else
                _slps_runner_status=$?
            fi
            if [ ! -r "${_slps_attempt_result}" ]; then
                strategy_lab_profile_attempt_failure "${_slps_id}" "${_slps_family}" \
                    "${_slps_profile}" "${_slps_attempt}" "${_slps_runner_status}" \
                    "${_slps_attempt_result}" || return 1
            else
                _slps_attempt_tmp="${_slps_attempt_result}.tmp.$$"
                "${STRATEGY_LAB_JQ}" --argjson attempt "${_slps_attempt}" \
                    --arg runner_status "${_slps_runner_status}" \
                    '.attempt=$attempt | .runner_status=$runner_status' \
                    "${_slps_attempt_result}" > "${_slps_attempt_tmp}" || {
                        rm -f "${_slps_attempt_tmp}"
                        return 1
                    }
                mv -f "${_slps_attempt_tmp}" "${_slps_attempt_result}"
            fi
            _slps_attempt=$((_slps_attempt + 1))
        done

        _slps_item="${_slps_items}/${_slps_index}.json"
        set -- "${_slps_attempt_dir}"/*.json
        "${STRATEGY_LAB_JQ}" -s \
            --argjson source "${_slps_source}" \
            --arg target "${_slps_target}" --arg target_type "${_slps_type}" \
            --rawfile profile "${_slps_profile}" '
            $source + {
                target:$target,
                target_type:$target_type,
                protocol:"tls13",
                port:443,
                profile:$profile,
                resolved_addresses:([.[]?.endpoints[]?.selected_ip // empty] | unique),
                profile_replay:{
                    attempt_count:length,
                    pass_count:([.[] | select(.all_pass==true and .profile_exact==true)] | length),
                    verified:(length==3 and all(.[]; .all_pass==true and .profile_exact==true)),
                    results:.
                }
            }
        ' "$@" > "${_slps_item}" || return 1
    done <<EOF
$("${STRATEGY_LAB_JQ}" -c '.[]' "${_slps_sources}")
EOF

    set -- "${_slps_items}"/*.json
    if [ ! -e "$1" ]; then
        printf '%s\n' '{"count":0,"items":[],"recommendation":null}' > "${_slps_output}"
        return 0
    fi
    "${STRATEGY_LAB_JQ}" -s '
        map(select(.profile_replay.verified==true)) as $items |
        {count:($items|length),items:$items,recommendation:($items[0] // null)}
    ' "$@" > "${_slps_output}"
}
