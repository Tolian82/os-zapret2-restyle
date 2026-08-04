#!/bin/sh

strategy_lab_candidate_resolve_addresses()
{
    _slcand_resolve_endpoints="$1"
    _slcand_resolve_output="$2"
    _slcand_resolve_workdir="$3"
    : > "${_slcand_resolve_output}" || return 1
    _slcand_resolve_index=0
    while IFS= read -r _slcand_resolve_endpoint
    do
        [ -n "${_slcand_resolve_endpoint}" ] || continue
        _slcand_resolve_index=$((_slcand_resolve_index + 1))
        if strategy_lab_ipv4_valid "${_slcand_resolve_endpoint}"; then
            printf '%s\n' "${_slcand_resolve_endpoint}" >> "${_slcand_resolve_output}"
            continue
        fi
        _slcand_resolve_dns="${_slcand_resolve_workdir}/candidate-${_slcand_resolve_index}.a.log"
        strategy_lab_dns_request "${_slcand_resolve_endpoint}" A "${_slcand_resolve_dns}" || return 1
        awk '$0 ~ /[[:space:]]IN[[:space:]]+A[[:space:]]/ {print $NF}' "${_slcand_resolve_dns}" |
            grep -E '^[0-9]+(\.[0-9]+){3}$' >> "${_slcand_resolve_output}"
    done < "${_slcand_resolve_endpoints}"
    sort -u "${_slcand_resolve_output}" -o "${_slcand_resolve_output}"
    [ -s "${_slcand_resolve_output}" ]
}

strategy_lab_candidate_endpoint_probe()
{
    _slcand_probe_endpoint="$1"
    _slcand_probe_index="$2"
    _slcand_probe_workdir="$3"
    _slcand_probe_output="$4"
    _slcand_probe_raw="${_slcand_probe_workdir}/candidate-endpoint-${_slcand_probe_index}.log"
    if strategy_lab_ipv4_valid "${_slcand_probe_endpoint}"; then
        if strategy_lab_tcp_request "${_slcand_probe_endpoint}" 443 "${_slcand_probe_raw}"; then
            _slcand_probe_status=PASS
            _slcand_probe_exit=0
        else
            _slcand_probe_exit=$?
            _slcand_probe_status=FAIL
        fi
        strategy_lab_endpoint_result_write "${_slcand_probe_endpoint}" "${_slcand_probe_status}" \
            "${_slcand_probe_exit}" tcp-443 "${_slcand_probe_raw}" "${_slcand_probe_output}"
        return 0
    fi
    if strategy_lab_tls13_request ipv4 "${_slcand_probe_endpoint}" "${_slcand_probe_raw}"; then
        _slcand_probe_status=PASS
        _slcand_probe_exit=0
    else
        _slcand_probe_exit=$?
        _slcand_probe_status=FAIL
    fi
    _slcand_probe_reported=$(strategy_lab_request_exit_from_output "${_slcand_probe_raw}" 2>/dev/null || true)
    [ -z "${_slcand_probe_reported}" ] || _slcand_probe_exit="${_slcand_probe_reported}"
    strategy_lab_endpoint_result_write "${_slcand_probe_endpoint}" "${_slcand_probe_status}" \
        "${_slcand_probe_exit}" tls13-ipv4 "${_slcand_probe_raw}" "${_slcand_probe_output}"
}

strategy_lab_candidate_run_probes()
{
    _slcand_run_endpoints="$1"
    _slcand_run_workdir="$2"
    _slcand_run_result="$3"
    _slcand_run_id="$4"
    _slcand_run_family="$5"
    _slcand_run_strategy_file="$6"
    _slcand_run_results="${_slcand_run_workdir}/candidate-results"
    mkdir -p "${_slcand_run_results}" || return 1
    rm -f "${_slcand_run_results}"/*.json 2>/dev/null || true
    _slcand_run_pids=""
    _slcand_run_index=0
    _slcand_run_failed=0
    while IFS= read -r _slcand_run_endpoint
    do
        [ -n "${_slcand_run_endpoint}" ] || continue
        _slcand_run_index=$((_slcand_run_index + 1))
        if [ "${STRATEGY_LAB_ENDPOINT_PROBE_MODE:-parallel}" = sequential ]; then
            strategy_lab_candidate_endpoint_probe "${_slcand_run_endpoint}" "${_slcand_run_index}" \
                "${_slcand_run_workdir}" "${_slcand_run_results}/${_slcand_run_index}.json" ||
                _slcand_run_failed=1
        else
            strategy_lab_candidate_endpoint_probe "${_slcand_run_endpoint}" "${_slcand_run_index}" \
                "${_slcand_run_workdir}" "${_slcand_run_results}/${_slcand_run_index}.json" &
            _slcand_run_pids="${_slcand_run_pids} $!"
        fi
    done < "${_slcand_run_endpoints}"
    [ "${_slcand_run_index}" -ge 1 ] || return 1
    if [ "${STRATEGY_LAB_ENDPOINT_PROBE_MODE:-parallel}" != sequential ]; then
        for _slcand_run_pid in ${_slcand_run_pids}
        do
            wait "${_slcand_run_pid}" || _slcand_run_failed=1
        done
    fi
    [ "${_slcand_run_failed}" -eq 0 ] || return 1
    set -- "${_slcand_run_results}"/*.json
    [ -e "$1" ] || return 1
    "${STRATEGY_LAB_JQ}" -s \
        --arg id "${_slcand_run_id}" \
        --arg family "${_slcand_run_family}" \
        --rawfile strategy "${_slcand_run_strategy_file}" \
        '{id:$id,family:$family,strategy:$strategy,endpoints:.,all_pass:(length>0 and all(.status=="PASS"))}' \
        "$@" > "${_slcand_run_result}"
}

strategy_lab_candidate_cleanup()
{
    _slcand_cleanup_job="$1"
    strategy_lab_candidate_stop "${_slcand_cleanup_job}" || return 1
    strategy_lab_firewall_remove_rules
    strategy_lab_firewall_range_empty || return 1
    return 0
}

strategy_lab_run_candidate()
{
    _slcand_job="$1"
    _slcand_endpoints="$2"
    _slcand_result="$3"
    _slcand_id="$4"
    _slcand_family="$5"
    _slcand_strategy_file="$6"
    _slcand_use_hostlist="$7"
    _slcand_runtime=$(strategy_lab_candidate_runtime_dir "${_slcand_job}")
    _slcand_addresses=$(strategy_lab_candidate_addresses_file "${_slcand_job}")
    _slcand_wan=$(strategy_lab_candidate_resolve_wan) || return 1
    mkdir -p "${_slcand_runtime}" || return 1
    strategy_lab_candidate_cleanup "${_slcand_job}" || return 1
    strategy_lab_candidate_resolve_addresses "${_slcand_endpoints}" "${_slcand_addresses}" "${_slcand_runtime}" || return 1
    strategy_lab_candidate_prepare_files "${_slcand_job}" "${_slcand_endpoints}" "${_slcand_strategy_file}" "${_slcand_use_hostlist}" || return 1
    strategy_lab_firewall_install_ipv4_rules "${_slcand_addresses}" "${_slcand_wan}" || return 1
    strategy_lab_candidate_start "${_slcand_job}" || {
        strategy_lab_candidate_cleanup "${_slcand_job}" || true
        return 1
    }
    if ! strategy_lab_candidate_run_probes "${_slcand_endpoints}" "${_slcand_runtime}" "${_slcand_result}" \
        "${_slcand_id}" "${_slcand_family}" "${_slcand_strategy_file}"; then
        strategy_lab_candidate_cleanup "${_slcand_job}" || true
        return 1
    fi
    strategy_lab_candidate_cleanup "${_slcand_job}"
}

strategy_lab_run_smoke_candidate()
{
    _slcand_smoke_strategy="${MODULE_DIR}/catalog/tls13/01-multisplit.args"
    strategy_lab_run_candidate "$1" "$2" "$3" smoke-multisplit multisplit "${_slcand_smoke_strategy}" 1
}
