#!/bin/sh

STRATEGY_LAB_PROFILE_REPLAY_RUNNER="${STRATEGY_LAB_PROFILE_REPLAY_RUNNER:-${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh}"
STRATEGY_LAB_PROFILE_REPLAY_ATTEMPTS=3
STRATEGY_LAB_PROFILE_REPLAY_ATTEMPT_TIMEOUT="${STRATEGY_LAB_PROFILE_REPLAY_ATTEMPT_TIMEOUT:-45}"
STRATEGY_LAB_PROFILE_ENV_BIN="${STRATEGY_LAB_PROFILE_ENV_BIN:-/usr/bin/env}"
STRATEGY_LAB_SHORTLIST_LIMIT="${STRATEGY_LAB_SHORTLIST_LIMIT:-5}"

strategy_lab_profile_port_valid()
{
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 65535 ] 2>/dev/null
}

strategy_lab_profile_addresses_valid()
{
    _slpav_value="$1"
    [ -n "${_slpav_value}" ] || return 1
    printf '%s\n' "${_slpav_value}" | awk -F ',' '
        NF < 1 { exit 1 }
        {
            for (i=1; i<=NF; i++) {
                if ($i !~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/) exit 1
                split($i, octet, ".")
                if (length(octet) != 4) exit 1
                for (j=1; j<=4; j++) {
                    if (octet[j] < 0 || octet[j] > 255) exit 1
                }
            }
        }
    '
}

strategy_lab_profile_contract()
{
    _slpc_protocol="$1"
    _slpc_port="$2"
    case "${_slpc_protocol}" in
        tls13|tls12)
            [ "${_slpc_port}" = 443 ] || return 1
            printf '%s\t%s\t%s\n' tcp 443 tls
            ;;
        http)
            [ "${_slpc_port}" = 80 ] || return 1
            printf '%s\t%s\t%s\n' tcp 80 http
            ;;
        quic)
            [ "${_slpc_port}" = 443 ] || return 1
            printf '%s\t%s\t%s\n' udp 443 quic
            ;;
        udp)
            strategy_lab_profile_port_valid "${_slpc_port}" || return 1
            printf '%s\t%s\t%s\n' udp "${_slpc_port}" ''
            ;;
        *) return 1 ;;
    esac
}

strategy_lab_profile_selector_for()
{
    _slpsf_target="$1"
    _slpsf_type="$2"
    _slpsf_protocol="$3"
    _slpsf_addresses="${4:-}"
    case "${_slpsf_type}" in
        ip)
            strategy_lab_ipv4_valid "${_slpsf_target}" || return 1
            printf '%s\n' "--ipset-ip=${_slpsf_target}"
            ;;
        domain)
            strategy_lab_domain_valid "${_slpsf_target}" || return 1
            if [ "${_slpsf_protocol}" = udp ]; then
                strategy_lab_profile_addresses_valid "${_slpsf_addresses}" || return 1
                printf '%s\n' "--ipset-ip=${_slpsf_addresses}"
            else
                printf '%s\n' "--hostlist-domains=${_slpsf_target}"
            fi
            ;;
        *) return 1 ;;
    esac
}

strategy_lab_profile_selector()
{
    strategy_lab_profile_selector_for "$1" "$2" tls13 ''
}

strategy_lab_profile_fragment_line_allowed()
{
    case "$1" in
        ''|--new|--filter-*|--out-range=*) return 1 ;;
        --port=*|--lua-init=*|--sockarg=*|--user=*|--uid=*|--gid=*|\
        --daemon*|--pidfile=*|--qnum=*|--bind-*|--socket=*|\
        --hostlist*|--ipset*|\
        '<HOSTLIST:'*|' <HOSTLIST:'*|'<IPSET:'*|' <IPSET:'*)
            return 1
            ;;
    esac
    return 0
}

strategy_lab_profile_build_protocol()
{
    _slpb_target="$1"
    _slpb_type="$2"
    _slpb_protocol="$3"
    _slpb_port="$4"
    _slpb_addresses="$5"
    _slpb_fragment="$6"
    _slpb_output="$7"
    [ -r "${_slpb_fragment}" ] && [ -s "${_slpb_fragment}" ] || return 1
    _slpb_contract=$(strategy_lab_profile_contract "${_slpb_protocol}" "${_slpb_port}") || return 1
    _slpb_transport=$(printf '%s\n' "${_slpb_contract}" | awk -F '\t' '{print $1}')
    _slpb_l7=$(printf '%s\n' "${_slpb_contract}" | awk -F '\t' '{print $3}')
    _slpb_selector=$(strategy_lab_profile_selector_for \
        "${_slpb_target}" "${_slpb_type}" "${_slpb_protocol}" "${_slpb_addresses}") || return 1
    _slpb_tmp="${_slpb_output}.tmp.$$"
    (
        printf '%s\n' "--filter-${_slpb_transport}=${_slpb_port}"
        [ -z "${_slpb_l7}" ] || printf '%s\n' "--filter-l7=${_slpb_l7}"
        printf '%s\n' "${_slpb_selector}" '--out-range=-d10'
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
    strategy_lab_profile_validate_protocol \
        "${_slpb_target}" "${_slpb_type}" "${_slpb_protocol}" "${_slpb_port}" \
        "${_slpb_addresses}" "${_slpb_tmp}" || {
        rm -f "${_slpb_tmp}"
        return 1
    }
    chmod 0644 "${_slpb_tmp}"
    mv -f "${_slpb_tmp}" "${_slpb_output}"
}

strategy_lab_profile_build()
{
    strategy_lab_profile_build_protocol "$1" "$2" tls13 443 '' "$3" "$4"
}

strategy_lab_profile_validate_protocol()
{
    _slpv_target="$1"
    _slpv_type="$2"
    _slpv_protocol="$3"
    _slpv_port="$4"
    _slpv_addresses="$5"
    _slpv_file="$6"
    [ -r "${_slpv_file}" ] && [ -s "${_slpv_file}" ] || return 1
    _slpv_contract=$(strategy_lab_profile_contract "${_slpv_protocol}" "${_slpv_port}") || return 1
    _slpv_transport=$(printf '%s\n' "${_slpv_contract}" | awk -F '\t' '{print $1}')
    _slpv_l7=$(printf '%s\n' "${_slpv_contract}" | awk -F '\t' '{print $3}')
    _slpv_selector=$(strategy_lab_profile_selector_for \
        "${_slpv_target}" "${_slpv_type}" "${_slpv_protocol}" "${_slpv_addresses}") || return 1
    [ "$(grep -Fxc -- "${_slpv_selector}" "${_slpv_file}")" -eq 1 ] || return 1
    [ "$(grep -Ec '^--(hostlist-domains|ipset-ip)=' "${_slpv_file}")" -eq 1 ] || return 1
    [ "$(grep -Fxc -- "--filter-${_slpv_transport}=${_slpv_port}" "${_slpv_file}")" -eq 1 ] || return 1
    [ "$(grep -Ec '^--filter-(tcp|udp)=' "${_slpv_file}")" -eq 1 ] || return 1
    if [ -n "${_slpv_l7}" ]; then
        [ "$(grep -Fxc -- "--filter-l7=${_slpv_l7}" "${_slpv_file}")" -eq 1 ] || return 1
        [ "$(grep -Ec '^--filter-l7=' "${_slpv_file}")" -eq 1 ] || return 1
    else
        ! grep -Eq '^--filter-l7=' "${_slpv_file}" || return 1
    fi
    [ "$(grep -Fxc -- '--out-range=-d10' "${_slpv_file}")" -eq 1 ] || return 1
    grep -Eq '^--lua-desync=' "${_slpv_file}" || return 1
    if grep -Eq '^--(port|lua-init|sockarg|user|uid|gid|daemon|pidfile|qnum|bind-|socket)=' "${_slpv_file}"; then
        return 1
    fi
    ! grep -Fqx -- '--new' "${_slpv_file}" || return 1
    awk -v selector="${_slpv_selector}" '
        /^--(hostlist|ipset)/ && $0 != selector { exit 1 }
        /^[[:space:]]*<(HOSTLIST|IPSET):/ { exit 1 }
    ' "${_slpv_file}" || return 1
}

strategy_lab_profile_validate()
{
    strategy_lab_profile_validate_protocol "$1" "$2" tls13 443 '' "$3"
}

strategy_lab_profile_attempt_failure()
{
    _slpa_id="$1"
    _slpa_family="$2"
    _slpa_profile="$3"
    _slpa_attempt="$4"
    _slpa_status="$5"
    _slpa_output="$6"
    _slpa_protocol="$7"
    _slpa_port="$8"
    "${STRATEGY_LAB_JQ}" -nc \
        --arg id "${_slpa_id}" --arg family "${_slpa_family}" \
        --rawfile profile "${_slpa_profile}" --argjson attempt "${_slpa_attempt}" \
        --arg status "${_slpa_status}" --arg protocol "${_slpa_protocol}" \
        --argjson port "${_slpa_port}" \
        '{id:$id,family:$family,strategy:$profile,profile:$profile,protocol:$protocol,
          port:$port,attempt:$attempt,runner_status:$status,endpoints:[],
          all_pass:false,profile_exact:false}' > "${_slpa_output}"
}

strategy_lab_shortlist_source_append()
{
    _slssa_output="$1"
    _slssa_source="$2"
    _slssa_protocol="$3"
    _slssa_rank="$4"
    _slssa_transport="$5"
    _slssa_port="$6"
    _slssa_l7="$7"
    "${STRATEGY_LAB_JQ}" -nc \
        --argjson source "${_slssa_source}" \
        --arg protocol "${_slssa_protocol}" --argjson protocol_rank "${_slssa_rank}" \
        --arg transport "${_slssa_transport}" --argjson port "${_slssa_port}" \
        --arg l7 "${_slssa_l7}" '
        ([($source.endpoints // [])[]?.selected_ip,
          ($source.attempts // [])[]?.endpoints[]?.selected_ip] |
          map(select(type=="string" and length>0)) | unique | join(",")) as $addresses |
        $source + {
            protocol:$protocol,
            protocol_rank:$protocol_rank,
            transport:$transport,
            port:$port,
            l7:(if $l7=="" then null else $l7 end),
            selector_addresses:$addresses,
            line_count:($source.line_count // ($source.strategy | split("\n") | map(select(length>0)) | length)),
            character_count:($source.character_count // ($source.strategy | length))
        }
    ' >> "${_slssa_output}"
}

strategy_lab_shortlist_collect_sources()
{
    _slsc_stability="$1"
    _slsc_mode="$2"
    _slsc_job_dir="$3"
    _slsc_output="$4"
    : > "${_slsc_output}" || return 1

    while IFS= read -r _slsc_source
    do
        [ -n "${_slsc_source}" ] || continue
        strategy_lab_shortlist_source_append \
            "${_slsc_output}" "${_slsc_source}" tls13 0 tcp 443 tls || return 1
    done <<EOF_TLS13
$("${STRATEGY_LAB_JQ}" -c '[.candidates[] | select(.stable==true)] | sort_by(.line_count,.character_count,.id) | .[0:5][]' "${_slsc_stability}")
EOF_TLS13

    [ "${_slsc_mode}" = extended ] || return 0
    _slsc_extended="${_slsc_job_dir}/extended-tcp.json"
    if [ -r "${_slsc_extended}" ]; then
        _slsc_source=$("${STRATEGY_LAB_JQ}" -c '.protocols.tls12.working // empty' "${_slsc_extended}")
        [ -z "${_slsc_source}" ] || strategy_lab_shortlist_source_append \
            "${_slsc_output}" "${_slsc_source}" tls12 1 tcp 443 tls || return 1
        _slsc_source=$("${STRATEGY_LAB_JQ}" -c '.protocols.http.working // empty' "${_slsc_extended}")
        [ -z "${_slsc_source}" ] || strategy_lab_shortlist_source_append \
            "${_slsc_output}" "${_slsc_source}" http 2 tcp 80 http || return 1
    fi
    _slsc_quic="${_slsc_job_dir}/quic.json"
    if [ -r "${_slsc_quic}" ]; then
        _slsc_source=$("${STRATEGY_LAB_JQ}" -c '.working // empty' "${_slsc_quic}")
        [ -z "${_slsc_source}" ] || strategy_lab_shortlist_source_append \
            "${_slsc_output}" "${_slsc_source}" quic 3 udp 443 quic || return 1
    fi
    _slsc_udp="${_slsc_job_dir}/udp.json"
    if [ -r "${_slsc_udp}" ]; then
        _slsc_port=$("${STRATEGY_LAB_JQ}" -r '.port // empty' "${_slsc_udp}")
        if strategy_lab_profile_port_valid "${_slsc_port}"; then
            _slsc_source=$("${STRATEGY_LAB_JQ}" -c '.working // empty' "${_slsc_udp}")
            [ -z "${_slsc_source}" ] || strategy_lab_shortlist_source_append \
                "${_slsc_output}" "${_slsc_source}" udp 4 udp "${_slsc_port}" '' || return 1
        fi
    fi
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
    _slps_mode=$("${STRATEGY_LAB_JQ}" -r '.mode // "standard"' "${_slps_status}") || return 1
    strategy_lab_profile_selector_for "${_slps_target}" "${_slps_type}" tls13 '' >/dev/null || return 1

    _slps_work="${_slps_job_dir}/profile-replay"
    _slps_sources_ndjson="${_slps_work}/sources.ndjson"
    _slps_sources="${_slps_work}/sources.json"
    _slps_items="${_slps_work}/items"
    rm -rf "${_slps_work}"
    mkdir -p "${_slps_items}" || return 1
    strategy_lab_shortlist_collect_sources \
        "${_slps_stability}" "${_slps_mode}" "${_slps_job_dir}" "${_slps_sources_ndjson}" || return 1
    if [ -s "${_slps_sources_ndjson}" ]; then
        "${STRATEGY_LAB_JQ}" -s \
            'unique_by([.protocol,.port,.strategy]) | sort_by(.protocol_rank,.line_count,.character_count,.id)' \
            "${_slps_sources_ndjson}" > "${_slps_sources}" || return 1
    else
        printf '%s\n' '[]' > "${_slps_sources}"
    fi

    _slps_index=0
    while IFS= read -r _slps_source
    do
        [ -n "${_slps_source}" ] || continue
        _slps_index=$((_slps_index + 1))
        _slps_id=$(printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.id')
        _slps_family=$(printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.family')
        _slps_protocol=$(printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.protocol')
        _slps_port=$(printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.port')
        _slps_addresses=$(printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.selector_addresses // ""')
        if [ "${_slps_protocol}" = udp ] && [ "${_slps_type}" = domain ] &&
           ! strategy_lab_profile_addresses_valid "${_slps_addresses}"; then
            continue
        fi
        _slps_fragment="${_slps_work}/${_slps_index}.fragment.args"
        _slps_profile="${_slps_work}/${_slps_index}.profile.args"
        printf '%s' "${_slps_source}" | "${STRATEGY_LAB_JQ}" -r '.strategy' > "${_slps_fragment}" || return 1
        strategy_lab_profile_build_protocol \
            "${_slps_target}" "${_slps_type}" "${_slps_protocol}" "${_slps_port}" \
            "${_slps_addresses}" "${_slps_fragment}" "${_slps_profile}" || return 1
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
                "${_slps_target}" "${_slps_type}" "${_slps_protocol}" \
                "${_slps_port}" "${_slps_addresses}"
            then
                _slps_runner_status=0
            else
                _slps_runner_status=$?
            fi
            if [ ! -r "${_slps_attempt_result}" ]; then
                strategy_lab_profile_attempt_failure "${_slps_id}" "${_slps_family}" \
                    "${_slps_profile}" "${_slps_attempt}" "${_slps_runner_status}" \
                    "${_slps_attempt_result}" "${_slps_protocol}" "${_slps_port}" || return 1
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
                profile:$profile,
                resolved_addresses:([.[]?.endpoints[]?.selected_ip // empty] | unique),
                profile_replay:{
                    attempt_count:length,
                    pass_count:([.[] | select(.all_pass==true and .profile_exact==true)] | length),
                    verified:(length==3 and all(.[]; .all_pass==true and .profile_exact==true)),
                    results:.
                },
                circular_eligible:($source.protocol=="tls13")
            }
        ' "$@" > "${_slps_item}" || return 1
    done <<EOF_SOURCES
$("${STRATEGY_LAB_JQ}" -c '.[]' "${_slps_sources}")
EOF_SOURCES

    set -- "${_slps_items}"/*.json
    if [ ! -e "$1" ]; then
        printf '%s\n' '{"count":0,"items":[],"recommendation":null,"circular_count":0,"circular_items":[]}' > "${_slps_output}"
        return 0
    fi
    "${STRATEGY_LAB_JQ}" -s --arg mode "${_slps_mode}" --argjson limit "${STRATEGY_LAB_SHORTLIST_LIMIT}" '
        map(select(.profile_replay.verified==true)) |
        sort_by(.protocol_rank,.line_count,.character_count,.id) as $verified |
        ([$verified[] | select(.protocol=="tls13")][0:$limit]) as $tls13 |
        (if $mode=="extended" then
            [$verified | group_by(.protocol)[] | .[0]] | sort_by(.protocol_rank,.line_count,.character_count,.id) | .[0:$limit]
         else $tls13 end) as $items |
        {
            count:($items|length),
            items:$items,
            recommendation:($items[0] // null),
            circular_count:($tls13|length),
            circular_items:$tls13
        }
    ' "$@" > "${_slps_output}"
}
