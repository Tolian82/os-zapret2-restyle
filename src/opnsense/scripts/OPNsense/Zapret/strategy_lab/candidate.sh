#!/bin/sh

strategy_lab_candidate_resolve_addresses()
{
    _slcand_resolve_endpoints="$1"
    _slcand_resolve_output="$2"
    _slcand_resolve_workdir="$3"
    _slcand_resolve_bindings=$(strategy_lab_candidate_bindings_file "${_slcand_resolve_workdir}")
    : > "${_slcand_resolve_output}" || return 1
    : > "${_slcand_resolve_bindings}" || return 1
    _slcand_resolve_index=0

    while IFS= read -r _slcand_resolve_endpoint
    do
        [ -n "${_slcand_resolve_endpoint}" ] || continue
        _slcand_resolve_index=$((_slcand_resolve_index + 1))
        _slcand_resolve_selected=""

        if strategy_lab_ipv4_valid "${_slcand_resolve_endpoint}"; then
            _slcand_resolve_selected="${_slcand_resolve_endpoint}"
        else
            _slcand_resolve_dns="${_slcand_resolve_workdir}/candidate-${_slcand_resolve_index}.a.log"
            strategy_lab_dns_request "${_slcand_resolve_endpoint}" A "${_slcand_resolve_dns}" || return 1
            _slcand_resolve_selected=$(strategy_lab_dns_first_answer A "${_slcand_resolve_dns}") || return 1
        fi
        strategy_lab_ipv4_valid "${_slcand_resolve_selected}" || return 1

        _slcand_resolve_line=$(awk -v selected="${_slcand_resolve_selected}" '
            $0 == selected { print NR; exit }
        ' "${_slcand_resolve_output}")
        if [ -z "${_slcand_resolve_line}" ]; then
            printf '%s\n' "${_slcand_resolve_selected}" >> "${_slcand_resolve_output}" || return 1
            _slcand_resolve_line=$(wc -l < "${_slcand_resolve_output}" | tr -d '[:space:]')
        fi
        _slcand_resolve_rule=$((STRATEGY_LAB_RULE_BASE + _slcand_resolve_line - 1))
        [ "${_slcand_resolve_rule}" -le "${STRATEGY_LAB_RULE_MAX}" ] || return 1
        printf '%s\t%s\t%s\t%s\n' \
            "${_slcand_resolve_index}" "${_slcand_resolve_endpoint}" \
            "${_slcand_resolve_selected}" "${_slcand_resolve_rule}" \
            >> "${_slcand_resolve_bindings}" || return 1
    done < "${_slcand_resolve_endpoints}"

    [ -s "${_slcand_resolve_output}" ] && [ -s "${_slcand_resolve_bindings}" ]
}

strategy_lab_candidate_endpoint_probe()
{
    _slcand_probe_endpoint="$1"
    _slcand_probe_index="$2"
    _slcand_probe_workdir="$3"
    _slcand_probe_output="$4"
    _slcand_probe_raw="${_slcand_probe_workdir}/candidate-endpoint-${_slcand_probe_index}.log"
    _slcand_probe_state="${_slcand_probe_workdir}/candidate-endpoint-${_slcand_probe_index}.interception"
    strategy_lab_candidate_probe_begin \
        "${_slcand_probe_workdir}" "${_slcand_probe_index}" "${_slcand_probe_state}" || return 1
    _slcand_probe_selected=$(sed -n '1p' "${_slcand_probe_state}")

    if strategy_lab_ipv4_valid "${_slcand_probe_endpoint}"; then
        if strategy_lab_tcp_request "${_slcand_probe_selected}" 443 "${_slcand_probe_raw}"; then
            _slcand_probe_exit=0
        else
            _slcand_probe_exit=$?
        fi
        _slcand_probe_remote="${_slcand_probe_selected}"
        _slcand_probe_transport=tcp-443
    else
        if strategy_lab_tls13_bound_request \
            "${_slcand_probe_endpoint}" "${_slcand_probe_selected}" "${_slcand_probe_raw}"; then
            _slcand_probe_exit=0
        else
            _slcand_probe_exit=$?
        fi
        _slcand_probe_reported=$(strategy_lab_request_exit_from_output "${_slcand_probe_raw}" 2>/dev/null || true)
        [ -z "${_slcand_probe_reported}" ] || _slcand_probe_exit="${_slcand_probe_reported}"
        _slcand_probe_remote=$(strategy_lab_request_remote_ip_from_output "${_slcand_probe_raw}" 2>/dev/null || true)
        _slcand_probe_transport=tls13-ipv4
    fi

    strategy_lab_candidate_endpoint_result_write \
        "${_slcand_probe_endpoint}" "${_slcand_probe_exit}" "${_slcand_probe_transport}" \
        "${_slcand_probe_raw}" "${_slcand_probe_remote}" "${_slcand_probe_state}" \
        "${_slcand_probe_output}"
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
    _slcand_run_index=0

    while IFS= read -r _slcand_run_endpoint
    do
        [ -n "${_slcand_run_endpoint}" ] || continue
        _slcand_run_index=$((_slcand_run_index + 1))
        strategy_lab_candidate_endpoint_probe \
            "${_slcand_run_endpoint}" "${_slcand_run_index}" \
            "${_slcand_run_workdir}" "${_slcand_run_results}/${_slcand_run_index}.json" ||
            return 1
    done < "${_slcand_run_endpoints}"

    [ "${_slcand_run_index}" -ge 1 ] || return 1
    set -- "${_slcand_run_results}"/*.json
    [ -e "$1" ] || return 1
    "${STRATEGY_LAB_JQ}" -s \
        --arg id "${_slcand_run_id}" \
        --arg family "${_slcand_run_family}" \
        --rawfile strategy "${_slcand_strategy_file}" \
        '{id:$id,family:$family,strategy:$strategy,endpoints:.,all_pass:(length>0 and all(.status=="PASS"))}' \
        "$@" > "${_slcand_run_result}"
}

strategy_lab_candidate_jobdir_allow_hostlist_access()
{
    _slcand_access_job="$1"
    _slcand_access_jobdir=$(strategy_lab_job_dir "${_slcand_access_job}")
    _slcand_access_runtime=$(strategy_lab_candidate_runtime_dir "${_slcand_access_job}")
    [ -d "${_slcand_access_jobdir}" ] && [ -d "${_slcand_access_runtime}" ] || return 1

    # Job directories are created by mktemp(1) as private 0700 directories. dvtws2
    # deliberately drops to nobody and then reopens its hostlist, so grant search-only
    # traversal on the random job directory while the hostlist-backed candidate is alive.
    # The runtime directory remains listable only behind that random search-only parent.
    chmod 0711 "${_slcand_access_jobdir}" || return 1
    chmod 0755 "${_slcand_access_runtime}" || {
        chmod 0700 "${_slcand_access_jobdir}" || true
        return 1
    }
}

strategy_lab_candidate_jobdir_restore_private()
{
    _slcand_private_jobdir=$(strategy_lab_job_dir "$1")
    [ ! -d "${_slcand_private_jobdir}" ] || chmod 0700 "${_slcand_private_jobdir}"
}

strategy_lab_candidate_cleanup()
{
    _slcand_cleanup_job="$1"
    _slcand_cleanup_status=0
    strategy_lab_candidate_stop "${_slcand_cleanup_job}" || _slcand_cleanup_status=1
    strategy_lab_firewall_remove_rules || _slcand_cleanup_status=1
    strategy_lab_firewall_range_empty || _slcand_cleanup_status=1
    strategy_lab_candidate_jobdir_restore_private "${_slcand_cleanup_job}" || _slcand_cleanup_status=1
    return "${_slcand_cleanup_status}"
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
    strategy_lab_candidate_resolve_addresses \
        "${_slcand_endpoints}" "${_slcand_addresses}" "${_slcand_runtime}" || return 1
    strategy_lab_candidate_prepare_files \
        "${_slcand_job}" "${_slcand_endpoints}" "${_slcand_strategy_file}" \
        "${_slcand_use_hostlist}" || return 1
    strategy_lab_firewall_install_ipv4_rules "${_slcand_addresses}" "${_slcand_wan}" || return 1
    if [ "${_slcand_use_hostlist}" = 1 ]; then
        strategy_lab_candidate_jobdir_allow_hostlist_access "${_slcand_job}" || {
            strategy_lab_candidate_cleanup "${_slcand_job}" || true
            return 1
        }
    fi
    strategy_lab_candidate_start "${_slcand_job}" || {
        strategy_lab_candidate_cleanup "${_slcand_job}" || true
        return 1
    }
    if ! strategy_lab_candidate_run_probes \
        "${_slcand_endpoints}" "${_slcand_runtime}" "${_slcand_result}" \
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
