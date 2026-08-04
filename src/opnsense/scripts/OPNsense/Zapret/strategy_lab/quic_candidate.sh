#!/bin/sh

strategy_lab_candidate_prepare_files()
{
    _slqc_job="$1"; _slqc_endpoints="$2"; _slqc_strategy="$3"; _slqc_use_hostlist="$4"
    _slqc_runtime=$(strategy_lab_candidate_runtime_dir "${_slqc_job}")
    _slqc_args=$(strategy_lab_candidate_args_file "${_slqc_job}")
    _slqc_hostlist=$(strategy_lab_candidate_hostlist_file "${_slqc_job}")
    _slqc_tmp="${_slqc_args}.tmp.$$"
    [ -s "${_slqc_endpoints}" ] && [ -r "${_slqc_strategy}" ] || return 1
    mkdir -p "${_slqc_runtime}" || return 1
    cp "${_slqc_endpoints}" "${_slqc_hostlist}" || return 1
    : > "${_slqc_tmp}" || return 1
    printf '%s\n' "--port=${STRATEGY_LAB_DIVERT_PORT}" >> "${_slqc_tmp}"
    if [ -d "${STRATEGY_LAB_LUA_DIR}" ]; then
        find "${STRATEGY_LAB_LUA_DIR}" -maxdepth 1 -type f -name '*.lua' -print 2>/dev/null | sort |
        while IFS= read -r _slqc_lua; do printf '%s\n' "--lua-init=@${_slqc_lua}"; done >> "${_slqc_tmp}"
    fi
    printf '%s\n' '--filter-udp=443' '--filter-l7=quic' >> "${_slqc_tmp}"
    [ "${_slqc_use_hostlist}" != 1 ] || printf '%s\n' "--hostlist=${_slqc_hostlist}" >> "${_slqc_tmp}"
    printf '%s\n' '--out-range=-d10' >> "${_slqc_tmp}"
    cat "${_slqc_strategy}" >> "${_slqc_tmp}" || { rm -f "${_slqc_tmp}"; return 1; }
    mv -f "${_slqc_tmp}" "${_slqc_args}"; chmod 0644 "${_slqc_args}"
}

strategy_lab_firewall_install_ipv4_rules()
{
    _slqf_addresses="$1"; _slqf_wan="$2"
    strategy_lab_firewall_require_ready || return 1
    [ -s "${_slqf_addresses}" ] && [ -n "${_slqf_wan}" ] || return 1
    strategy_lab_firewall_remove_rules; strategy_lab_firewall_range_empty || return 1
    _slqf_rule="${STRATEGY_LAB_RULE_BASE}"
    while IFS= read -r _slqf_address
    do
        [ -n "${_slqf_address}" ] || continue
        "${STRATEGY_LAB_IPFW_BIN}" -qf add "${_slqf_rule}" divert "${STRATEGY_LAB_DIVERT_PORT}" \
            udp from any to "${_slqf_address}" 443 out not diverted not sockarg xmit "${_slqf_wan}" || { strategy_lab_firewall_remove_rules; return 1; }
        _slqf_rule=$((_slqf_rule + 1))
    done < "${_slqf_addresses}"
    strategy_lab_firewall_range_empty && return 1
    return 0
}

strategy_lab_candidate_endpoint_probe()
{
    _slqp_endpoint="$1"; _slqp_index="$2"; _slqp_work="$3"; _slqp_output="$4"
    _slqp_raw="${_slqp_work}/candidate-endpoint-${_slqp_index}.log"
    if strategy_lab_ipv4_valid "${_slqp_endpoint}"; then
        _slqp_status=FAIL; _slqp_exit=64
    else
        if strategy_lab_quic_target_request "${_slqp_endpoint}" "${_slqp_raw}"; then _slqp_status=PASS; _slqp_exit=0; else _slqp_exit=$?; _slqp_status=FAIL; fi
    fi
    strategy_lab_endpoint_result_write "${_slqp_endpoint}" "${_slqp_status}" "${_slqp_exit}" quic-ipv4 "${_slqp_raw}" "${_slqp_output}"
}
