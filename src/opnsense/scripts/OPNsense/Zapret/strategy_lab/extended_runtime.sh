#!/bin/sh

strategy_lab_candidate_prepare_files()
{
    _slext_rt_job="$1"
    _slext_rt_endpoints="$2"
    _slext_rt_strategy_file="$3"
    _slext_rt_use_hostlist="$4"
    _slext_rt_runtime=$(strategy_lab_candidate_runtime_dir "${_slext_rt_job}")
    _slext_rt_args=$(strategy_lab_candidate_args_file "${_slext_rt_job}")
    _slext_rt_hostlist=$(strategy_lab_candidate_hostlist_file "${_slext_rt_job}")
    _slext_rt_tmp="${_slext_rt_args}.tmp.$$"
    _slext_rt_port="${STRATEGY_LAB_CANDIDATE_PORT:-443}"
    _slext_rt_l7="${STRATEGY_LAB_CANDIDATE_L7:-tls}"
    [ -r "${_slext_rt_endpoints}" ] && [ -s "${_slext_rt_endpoints}" ] && [ -r "${_slext_rt_strategy_file}" ] || return 1
    mkdir -p "${_slext_rt_runtime}" || return 1
    cp "${_slext_rt_endpoints}" "${_slext_rt_hostlist}" || return 1
    chmod 0644 "${_slext_rt_hostlist}"
    : > "${_slext_rt_tmp}" || return 1
    printf '%s\n' "--port=${STRATEGY_LAB_DIVERT_PORT}" >> "${_slext_rt_tmp}"
    if [ -d "${STRATEGY_LAB_LUA_DIR}" ]; then
        find "${STRATEGY_LAB_LUA_DIR}" -maxdepth 1 -type f -name '*.lua' -print 2>/dev/null | sort |
        while IFS= read -r _slext_rt_lua; do printf '%s\n' "--lua-init=@${_slext_rt_lua}"; done >> "${_slext_rt_tmp}"
    fi
    printf '%s\n' "--filter-tcp=${_slext_rt_port}" "--filter-l7=${_slext_rt_l7}" >> "${_slext_rt_tmp}"
    [ "${_slext_rt_use_hostlist}" != 1 ] || printf '%s\n' "--hostlist=${_slext_rt_hostlist}" >> "${_slext_rt_tmp}"
    printf '%s\n' '--out-range=-d10' >> "${_slext_rt_tmp}"
    cat "${_slext_rt_strategy_file}" >> "${_slext_rt_tmp}" || { rm -f "${_slext_rt_tmp}"; return 1; }
    mv -f "${_slext_rt_tmp}" "${_slext_rt_args}"
    chmod 0644 "${_slext_rt_args}"
}

strategy_lab_firewall_install_ipv4_rules()
{
    _slext_fw_addresses="$1"
    _slext_fw_wan="$2"
    _slext_fw_port="${STRATEGY_LAB_CANDIDATE_PORT:-443}"
    strategy_lab_firewall_require_ready || return 1
    [ -s "${_slext_fw_addresses}" ] && [ -n "${_slext_fw_wan}" ] || return 1
    strategy_lab_firewall_remove_rules
    strategy_lab_firewall_range_empty || return 1
    _slext_fw_rule="${STRATEGY_LAB_RULE_BASE}"
    while IFS= read -r _slext_fw_address
    do
        [ -n "${_slext_fw_address}" ] || continue
        [ "${_slext_fw_rule}" -le "${STRATEGY_LAB_RULE_MAX}" ] || { strategy_lab_firewall_remove_rules; return 1; }
        "${STRATEGY_LAB_IPFW_BIN}" -qf add "${_slext_fw_rule}" divert "${STRATEGY_LAB_DIVERT_PORT}" \
            tcp from me to "${_slext_fw_address}" "${_slext_fw_port}" out not diverted not sockarg xmit "${_slext_fw_wan}" || {
            strategy_lab_firewall_remove_rules
            return 1
        }
        _slext_fw_rule=$((_slext_fw_rule + 1))
    done < "${_slext_fw_addresses}"
    strategy_lab_firewall_range_empty && return 1
    return 0
}
