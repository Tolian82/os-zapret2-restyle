#!/bin/sh

strategy_lab_control_ipv4()
{
    _strategy_lab_output="$1"
    _strategy_lab_state="$2"
    if strategy_lab_tls13_request ipv4 yandex.ru "${_strategy_lab_output}"; then
        printf '%s\n' available > "${_strategy_lab_state}"
    else
        printf '%s\n' unavailable > "${_strategy_lab_state}"
    fi
}

strategy_lab_control_ipv6()
{
    _strategy_lab_output="$1"
    _strategy_lab_state="$2"
    if strategy_lab_ipv6_default_route_available &&
        strategy_lab_tls13_request ipv6 one.one.one.one "${_strategy_lab_output}"
    then
        printf '%s\n' available > "${_strategy_lab_state}"
    else
        printf '%s\n' unavailable > "${_strategy_lab_state}"
    fi
}

strategy_lab_control_quic_ipv4()
{
    _strategy_lab_output="$1"
    _strategy_lab_state="$2"

    # The approved QUIC contract uses only the command exit status. Output is retained
    # for diagnostics but never overrides the status.
    if strategy_lab_quic_ipv4_request "${_strategy_lab_output}"; then
        printf '%s\n' available > "${_strategy_lab_state}"
    else
        printf '%s\n' closed > "${_strategy_lab_state}"
    fi
}

strategy_lab_run_network_precheck()
{
    _strategy_lab_result="$1"
    _strategy_lab_workdir="$2"
    _strategy_lab_ipv4_output="${_strategy_lab_workdir}/control-ipv4.log"
    _strategy_lab_ipv6_output="${_strategy_lab_workdir}/control-ipv6.log"
    _strategy_lab_quic_output="${_strategy_lab_workdir}/control-quic-ipv4.log"
    _strategy_lab_ipv4_state="${_strategy_lab_workdir}/control-ipv4.state"
    _strategy_lab_ipv6_state="${_strategy_lab_workdir}/control-ipv6.state"
    _strategy_lab_quic_state="${_strategy_lab_workdir}/control-quic-ipv4.state"

    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_CURL_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_NETSTAT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_OPENSSL_BIN}" || return 1

    rm -f "${_strategy_lab_ipv4_state}" "${_strategy_lab_ipv6_state}" "${_strategy_lab_quic_state}"

    strategy_lab_control_ipv4 "${_strategy_lab_ipv4_output}" "${_strategy_lab_ipv4_state}" &
    _strategy_lab_ipv4_pid=$!
    strategy_lab_control_ipv6 "${_strategy_lab_ipv6_output}" "${_strategy_lab_ipv6_state}" &
    _strategy_lab_ipv6_pid=$!
    strategy_lab_control_quic_ipv4 "${_strategy_lab_quic_output}" "${_strategy_lab_quic_state}" &
    _strategy_lab_quic_pid=$!

    _strategy_lab_control_failed=0
    wait "${_strategy_lab_ipv4_pid}" || _strategy_lab_control_failed=1
    wait "${_strategy_lab_ipv6_pid}" || _strategy_lab_control_failed=1
    wait "${_strategy_lab_quic_pid}" || _strategy_lab_control_failed=1
    [ "${_strategy_lab_control_failed}" -eq 0 ] || return 1

    [ -r "${_strategy_lab_ipv4_state}" ] || return 1
    [ -r "${_strategy_lab_ipv6_state}" ] || return 1
    [ -r "${_strategy_lab_quic_state}" ] || return 1
    IFS= read -r _strategy_lab_ipv4 < "${_strategy_lab_ipv4_state}" || return 1
    IFS= read -r _strategy_lab_ipv6 < "${_strategy_lab_ipv6_state}" || return 1
    IFS= read -r _strategy_lab_quic_ipv4 < "${_strategy_lab_quic_state}" || return 1

    if [ "${_strategy_lab_quic_ipv4}" = available ] && [ "${_strategy_lab_ipv6}" = available ]; then
        _strategy_lab_quic_ipv6=eligible
    else
        _strategy_lab_quic_ipv6=skipped
    fi

    "${STRATEGY_LAB_JQ}" -nc \
        --arg ipv4 "${_strategy_lab_ipv4}" \
        --arg ipv6 "${_strategy_lab_ipv6}" \
        --arg quic_ipv4 "${_strategy_lab_quic_ipv4}" \
        --arg quic_ipv6 "${_strategy_lab_quic_ipv6}" \
        '{ipv4:$ipv4,ipv6:$ipv6,quic_ipv4:$quic_ipv4,quic_ipv6:$quic_ipv6}' \
        > "${_strategy_lab_result}"

    [ "${_strategy_lab_ipv4}" = available ] || return 2
    return 0
}

strategy_lab_dns_answer_present()
{
    _strategy_lab_type="$1"
    _strategy_lab_output="$2"
    grep -Eq "[[:space:]]IN[[:space:]]+${_strategy_lab_type}[[:space:]]" "${_strategy_lab_output}"
}

strategy_lab_endpoint_dns_a()
{
    _strategy_lab_endpoint="$1"
    _strategy_lab_output="$2"
    strategy_lab_dns_request "${_strategy_lab_endpoint}" A "${_strategy_lab_output}" || return 1
    strategy_lab_dns_answer_present A "${_strategy_lab_output}"
}

strategy_lab_endpoint_dns_aaaa()
{
    _strategy_lab_endpoint="$1"
    _strategy_lab_output="$2"
    strategy_lab_dns_request "${_strategy_lab_endpoint}" AAAA "${_strategy_lab_output}" || return 1
    strategy_lab_dns_answer_present AAAA "${_strategy_lab_output}"
}

strategy_lab_domain_endpoint_probe()
{
    _strategy_lab_endpoint="$1"
    _strategy_lab_index="$2"
    _strategy_lab_workdir="$3"
    _strategy_lab_result_file="$4"
    _strategy_lab_ipv6_enabled="$5"
    _strategy_lab_ipv4_raw="${_strategy_lab_workdir}/endpoint-${_strategy_lab_index}.tls-ipv4.log"
    _strategy_lab_ipv6_raw=""
    _strategy_lab_ipv6_status=SKIPPED
    _strategy_lab_ipv6_exit=""

    if strategy_lab_tls13_request ipv4 "${_strategy_lab_endpoint}" "${_strategy_lab_ipv4_raw}"; then
        _strategy_lab_ipv4_request_status=0
    else
        _strategy_lab_ipv4_request_status=$?
    fi
    _strategy_lab_ipv4_exit=$(strategy_lab_request_exit_from_output "${_strategy_lab_ipv4_raw}" 2>/dev/null || true)
    [ -n "${_strategy_lab_ipv4_exit}" ] || _strategy_lab_ipv4_exit="${_strategy_lab_ipv4_request_status}"
    if [ "${_strategy_lab_ipv4_request_status}" -eq 0 ]; then
        _strategy_lab_ipv4_status=PASS
    else
        _strategy_lab_ipv4_status=FAIL
    fi

    if [ "${_strategy_lab_ipv6_enabled}" = available ]; then
        _strategy_lab_ipv6_raw="${_strategy_lab_workdir}/endpoint-${_strategy_lab_index}.tls-ipv6.log"
        if strategy_lab_tls13_request ipv6 "${_strategy_lab_endpoint}" "${_strategy_lab_ipv6_raw}"; then
            _strategy_lab_ipv6_request_status=0
        else
            _strategy_lab_ipv6_request_status=$?
        fi
        _strategy_lab_ipv6_exit=$(strategy_lab_request_exit_from_output "${_strategy_lab_ipv6_raw}" 2>/dev/null || true)
        [ -n "${_strategy_lab_ipv6_exit}" ] || _strategy_lab_ipv6_exit="${_strategy_lab_ipv6_request_status}"
        if [ "${_strategy_lab_ipv6_request_status}" -eq 0 ]; then
            _strategy_lab_ipv6_status=PASS
        else
            _strategy_lab_ipv6_status=FAIL
        fi
    fi

    strategy_lab_domain_endpoint_result_write \
        "${_strategy_lab_endpoint}" \
        "${_strategy_lab_ipv4_status}" "${_strategy_lab_ipv4_exit}" "${_strategy_lab_ipv4_raw}" \
        "${_strategy_lab_ipv6_status}" "${_strategy_lab_ipv6_exit}" "${_strategy_lab_ipv6_raw}" \
        "${_strategy_lab_result_file}"
}

strategy_lab_ip_endpoint_probe()
{
    _strategy_lab_endpoint="$1"
    _strategy_lab_index="$2"
    _strategy_lab_workdir="$3"
    _strategy_lab_result_file="$4"
    _strategy_lab_raw="${_strategy_lab_workdir}/endpoint-${_strategy_lab_index}.tcp.log"

    if strategy_lab_tcp_request "${_strategy_lab_endpoint}" 443 "${_strategy_lab_raw}"; then
        _strategy_lab_request_status=0
        _strategy_lab_status=PASS
    else
        _strategy_lab_request_status=$?
        _strategy_lab_status=FAIL
    fi
    strategy_lab_endpoint_result_write \
        "${_strategy_lab_endpoint}" "${_strategy_lab_status}" \
        "${_strategy_lab_request_status}" tcp-443 \
        "${_strategy_lab_raw}" "${_strategy_lab_result_file}"
}

strategy_lab_run_clean_baseline()
{
    _strategy_lab_target="$1"
    _strategy_lab_type="$2"
    _strategy_lab_endpoints="$3"
    _strategy_lab_network="$4"
    _strategy_lab_workdir="$5"
    _strategy_lab_result="$6"
    _strategy_lab_results_dir="${_strategy_lab_workdir}/baseline-results"
    _strategy_lab_dns_a=SKIPPED
    _strategy_lab_dns_aaaa=SKIPPED
    _strategy_lab_dns_failed=0
    _strategy_lab_probe_pids=""
    _strategy_lab_ipv6_enabled=$("${STRATEGY_LAB_JQ}" -r '.ipv6' "${_strategy_lab_network}")

    mkdir -p "${_strategy_lab_results_dir}"
    rm -f "${_strategy_lab_results_dir}"/*.json 2>/dev/null || true

    if [ "${_strategy_lab_type}" = domain ]; then
        strategy_lab_require_executable "${STRATEGY_LAB_DRILL_BIN}" || return 1
        _strategy_lab_dns_a=PASS
        if [ "$("${STRATEGY_LAB_JQ}" -r '.ipv6' "${_strategy_lab_network}")" = available ]; then
            _strategy_lab_dns_aaaa=PASS
        fi

        _strategy_lab_index=0
        while IFS= read -r _strategy_lab_endpoint
        do
            [ -n "${_strategy_lab_endpoint}" ] || continue
            _strategy_lab_index=$((_strategy_lab_index + 1))
            _strategy_lab_dns_a_output="${_strategy_lab_workdir}/endpoint-${_strategy_lab_index}.a.log"
            if ! strategy_lab_endpoint_dns_a "${_strategy_lab_endpoint}" "${_strategy_lab_dns_a_output}"; then
                _strategy_lab_dns_a=FAIL
                _strategy_lab_dns_failed=1
                strategy_lab_endpoint_result_write \
                    "${_strategy_lab_endpoint}" FAIL 1 dns-a \
                    "${_strategy_lab_dns_a_output}" \
                    "${_strategy_lab_results_dir}/${_strategy_lab_index}.json"
                continue
            fi

            if [ "${_strategy_lab_dns_aaaa}" = PASS ]; then
                _strategy_lab_dns_aaaa_output="${_strategy_lab_workdir}/endpoint-${_strategy_lab_index}.aaaa.log"
                if ! strategy_lab_endpoint_dns_aaaa "${_strategy_lab_endpoint}" "${_strategy_lab_dns_aaaa_output}"; then
                    _strategy_lab_dns_aaaa=PARTIAL
                fi
            fi

            strategy_lab_domain_endpoint_probe \
                "${_strategy_lab_endpoint}" "${_strategy_lab_index}" \
                "${_strategy_lab_workdir}" \
                "${_strategy_lab_results_dir}/${_strategy_lab_index}.json" \
                "${_strategy_lab_ipv6_enabled}" &
            _strategy_lab_probe_pids="${_strategy_lab_probe_pids:-} $!"
        done < "${_strategy_lab_endpoints}"
        _strategy_lab_probe_failed=0
        for _strategy_lab_probe_pid in ${_strategy_lab_probe_pids:-}
        do
            wait "${_strategy_lab_probe_pid}" || _strategy_lab_probe_failed=1
        done
        [ "${_strategy_lab_probe_failed}" -eq 0 ] || return 1
    else
        _strategy_lab_index=0
        while IFS= read -r _strategy_lab_endpoint
        do
            [ -n "${_strategy_lab_endpoint}" ] || continue
            _strategy_lab_index=$((_strategy_lab_index + 1))
            strategy_lab_ip_endpoint_probe \
                "${_strategy_lab_endpoint}" "${_strategy_lab_index}" \
                "${_strategy_lab_workdir}" \
                "${_strategy_lab_results_dir}/${_strategy_lab_index}.json" &
            _strategy_lab_probe_pids="${_strategy_lab_probe_pids:-} $!"
        done < "${_strategy_lab_endpoints}"
        _strategy_lab_probe_failed=0
        for _strategy_lab_probe_pid in ${_strategy_lab_probe_pids:-}
        do
            wait "${_strategy_lab_probe_pid}" || _strategy_lab_probe_failed=1
        done
        [ "${_strategy_lab_probe_failed}" -eq 0 ] || return 1
    fi

    set -- "${_strategy_lab_results_dir}"/*.json
    [ -e "$1" ] || return 1
    "${STRATEGY_LAB_JQ}" -s '.' "$@" > "${_strategy_lab_workdir}/baseline-endpoints.json"
    "${STRATEGY_LAB_JQ}" -nc \
        --arg target "${_strategy_lab_target}" \
        --arg target_type "${_strategy_lab_type}" \
        --arg dns_a "${_strategy_lab_dns_a}" \
        --arg dns_aaaa "${_strategy_lab_dns_aaaa}" \
        --slurpfile endpoints "${_strategy_lab_workdir}/baseline-endpoints.json" \
        '{
            target:$target,
            target_type:$target_type,
            dns_a:$dns_a,
            dns_aaaa:$dns_aaaa,
            endpoints:$endpoints[0],
            all_accessible:($endpoints[0] | length > 0 and all(.status == "PASS"))
        }' > "${_strategy_lab_result}"

    [ "${_strategy_lab_dns_failed}" -eq 0 ] || return 2
    return 0
}
