#!/bin/sh

strategy_lab_candidate_prepare_files()
{
    _sluc_job="$1"; _sluc_endpoints="$2"; _sluc_strategy="$3"; _sluc_use_hostlist="$4"
    _sluc_runtime=$(strategy_lab_candidate_runtime_dir "${_sluc_job}"); _sluc_args=$(strategy_lab_candidate_args_file "${_sluc_job}"); _sluc_tmp="${_sluc_args}.tmp.$$"
    _sluc_port="${STRATEGY_LAB_UDP_PORT}"
    [ -s "${_sluc_endpoints}" ] && [ -r "${_sluc_strategy}" ] || return 1
    mkdir -p "${_sluc_runtime}" || return 1
    : > "${_sluc_tmp}" || return 1
    printf '%s\n' "--port=${STRATEGY_LAB_DIVERT_PORT}" >> "${_sluc_tmp}"
    if [ -d "${STRATEGY_LAB_LUA_DIR}" ]; then find "${STRATEGY_LAB_LUA_DIR}" -maxdepth 1 -type f -name '*.lua' -print 2>/dev/null | sort | while IFS= read -r f; do printf '%s\n' "--lua-init=@${f}"; done >> "${_sluc_tmp}"; fi
    printf '%s\n' "--filter-udp=${_sluc_port}" '--out-range=-d10' >> "${_sluc_tmp}"
    cat "${_sluc_strategy}" >> "${_sluc_tmp}" || return 1
    mv -f "${_sluc_tmp}" "${_sluc_args}"; chmod 0644 "${_sluc_args}"
}

strategy_lab_firewall_install_ipv4_rules()
{
    _sluf_addresses="$1"; _sluf_wan="$2"; _sluf_port="${STRATEGY_LAB_UDP_PORT}"
    strategy_lab_firewall_require_ready || return 1
    strategy_lab_firewall_remove_rules; strategy_lab_firewall_range_empty || return 1
    _sluf_rule="${STRATEGY_LAB_RULE_BASE}"
    while IFS= read -r _sluf_address
    do
        [ -n "${_sluf_address}" ] || continue
        [ "${_sluf_rule}" -le "${STRATEGY_LAB_RULE_MAX}" ] || { strategy_lab_firewall_remove_rules; return 1; }
        "${STRATEGY_LAB_IPFW_BIN}" -qf add "${_sluf_rule}" divert "${STRATEGY_LAB_DIVERT_PORT}" udp from me to "${_sluf_address}" "${_sluf_port}" out not diverted not sockarg xmit "${_sluf_wan}" || { strategy_lab_firewall_remove_rules; return 1; }
        _sluf_rule=$((_sluf_rule + 1))
    done < "${_sluf_addresses}"
    strategy_lab_firewall_range_empty && return 1
    return 0
}

strategy_lab_candidate_endpoint_probe()
{
    _slup_endpoint="$1"; _slup_index="$2"; _slup_work="$3"; _slup_output="$4"
    _slup_raw="${_slup_work}/candidate-endpoint-${_slup_index}.log"
    _slup_state="${_slup_work}/candidate-endpoint-${_slup_index}.interception"
    strategy_lab_candidate_probe_begin "${_slup_work}" "${_slup_index}" "${_slup_state}" || return 1
    _slup_selected=$(sed -n '1p' "${_slup_state}")

    if strategy_lab_udp_response_request "${_slup_selected}" "${STRATEGY_LAB_UDP_PORT}" "${STRATEGY_LAB_UDP_PAYLOAD_FILE}" "${_slup_raw}"; then
        _slup_exit=0
    else
        _slup_exit=$?
    fi
    strategy_lab_candidate_endpoint_result_write \
        "${_slup_endpoint}" "${_slup_exit}" "udp-${STRATEGY_LAB_UDP_PORT}" \
        "${_slup_raw}" "${_slup_selected}" "${_slup_state}" "${_slup_output}"
}
