#!/bin/sh

STRATEGY_LAB_IPFW_BIN="${STRATEGY_LAB_IPFW_BIN:-/sbin/ipfw}"
STRATEGY_LAB_KLDSTAT_BIN="${STRATEGY_LAB_KLDSTAT_BIN:-/sbin/kldstat}"
STRATEGY_LAB_SYSCTL_BIN="${STRATEGY_LAB_SYSCTL_BIN:-/sbin/sysctl}"
STRATEGY_LAB_RULE_BASE="${STRATEGY_LAB_RULE_BASE:-19100}"
STRATEGY_LAB_RULE_MAX="${STRATEGY_LAB_RULE_MAX:-19131}"
STRATEGY_LAB_DIVERT_PORT="${STRATEGY_LAB_DIVERT_PORT:-9989}"

strategy_lab_firewall_rule_number_valid()
{
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 65534 ] 2>/dev/null
}

strategy_lab_firewall_contract_valid()
{
    strategy_lab_firewall_rule_number_valid "${STRATEGY_LAB_RULE_BASE}" || return 1
    strategy_lab_firewall_rule_number_valid "${STRATEGY_LAB_RULE_MAX}" || return 1
    [ "${STRATEGY_LAB_RULE_BASE}" -le "${STRATEGY_LAB_RULE_MAX}" ] || return 1
    case "${STRATEGY_LAB_DIVERT_PORT}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "${STRATEGY_LAB_DIVERT_PORT}" -ge 1 ] 2>/dev/null &&
        [ "${STRATEGY_LAB_DIVERT_PORT}" -le 65535 ] 2>/dev/null
}

strategy_lab_firewall_require_ready()
{
    strategy_lab_firewall_contract_valid || return 1
    [ -x "${STRATEGY_LAB_IPFW_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_KLDSTAT_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_SYSCTL_BIN}" ] || return 1
    "${STRATEGY_LAB_KLDSTAT_BIN}" -q -m ipfw || return 1
    "${STRATEGY_LAB_KLDSTAT_BIN}" -q -m ipdivert || return 1
    [ "$("${STRATEGY_LAB_SYSCTL_BIN}" -n net.inet.ip.fw.enable 2>/dev/null || true)" = 1 ]
}

strategy_lab_firewall_remove_rules()
{
    _strategy_lab_rule="${STRATEGY_LAB_RULE_BASE}"
    while [ "${_strategy_lab_rule}" -le "${STRATEGY_LAB_RULE_MAX}" ]
    do
        "${STRATEGY_LAB_IPFW_BIN}" -q delete "${_strategy_lab_rule}" 2>/dev/null || true
        _strategy_lab_rule=$((_strategy_lab_rule + 1))
    done
}

strategy_lab_firewall_range_empty()
{
    _strategy_lab_rule="${STRATEGY_LAB_RULE_BASE}"
    while [ "${_strategy_lab_rule}" -le "${STRATEGY_LAB_RULE_MAX}" ]
    do
        if "${STRATEGY_LAB_IPFW_BIN}" list "${_strategy_lab_rule}" 2>/dev/null |
            grep -q '^[0-9]'; then
            return 1
        fi
        _strategy_lab_rule=$((_strategy_lab_rule + 1))
    done
    return 0
}

strategy_lab_firewall_install_ipv4_rules()
{
    _strategy_lab_addresses="$1"
    _strategy_lab_wan="$2"

    strategy_lab_firewall_require_ready || return 1
    [ -r "${_strategy_lab_addresses}" ] || return 1
    [ -s "${_strategy_lab_addresses}" ] || return 1
    [ -n "${_strategy_lab_wan}" ] || return 1

    strategy_lab_firewall_remove_rules
    strategy_lab_firewall_range_empty || return 1

    _strategy_lab_rule="${STRATEGY_LAB_RULE_BASE}"
    while IFS= read -r _strategy_lab_address
    do
        [ -n "${_strategy_lab_address}" ] || continue
        [ "${_strategy_lab_rule}" -le "${STRATEGY_LAB_RULE_MAX}" ] || {
            strategy_lab_firewall_remove_rules
            return 1
        }
        "${STRATEGY_LAB_IPFW_BIN}" -qf add "${_strategy_lab_rule}" \
            divert "${STRATEGY_LAB_DIVERT_PORT}" \
            tcp from me to "${_strategy_lab_address}" 443 \
            out not diverted not sockarg xmit "${_strategy_lab_wan}" || {
                strategy_lab_firewall_remove_rules
                return 1
            }
        _strategy_lab_rule=$((_strategy_lab_rule + 1))
    done < "${_strategy_lab_addresses}"

    strategy_lab_firewall_range_empty && return 1
    return 0
}
