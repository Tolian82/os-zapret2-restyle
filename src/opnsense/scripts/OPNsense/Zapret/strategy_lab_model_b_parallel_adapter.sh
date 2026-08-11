#!/bin/sh

# Narrow extension of the accepted Model-B adapter for the experiment-only parallel probe.
# All existing worker/cleanup/counter actions delegate unchanged to the proven adapter.
# Only controlled TCP source-port availability and source-port-qualified route creation live here.

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
BASE_ADAPTER="${STRATEGY_LAB_MODEL_B_BASE_ADAPTER:-${SCRIPT_DIR}/strategy_lab_model_b_adapter.sh}"
IPFW_BIN="${STRATEGY_LAB_MODEL_B_IPFW_BIN:-/sbin/ipfw}"
SOCKSTAT_BIN="${STRATEGY_LAB_MODEL_B_SOCKSTAT_BIN:-/usr/bin/sockstat}"
NETSTAT_BIN="${STRATEGY_LAB_MODEL_B_NETSTAT_BIN:-/usr/bin/netstat}"
MODEL_B_RULES="19128 19129 19130"
MODEL_B_PORTS="9990 9991 9992"

set -eu

valid_number_port()
{
    case "$1" in ''|*[!0-9]*) return 1 ;; esac
    [ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 65535 ] 2>/dev/null
}

valid_source_port()
{
    valid_number_port "$1" || return 1
    [ "$1" -ge 1024 ] 2>/dev/null
}

valid_rule()
{
    case " ${MODEL_B_RULES} " in *" $1 "*) return 0 ;; esac
    return 1
}

valid_divert_port()
{
    case " ${MODEL_B_PORTS} " in *" $1 "*) return 0 ;; esac
    return 1
}

valid_protocol()
{
    [ "$1" = tcp ]
}

valid_ipv4()
{
    case "$1" in
        ''|*[!0-9.]*) return 1 ;;
        *.*.*.*) return 0 ;;
    esac
    return 1
}

source_port_in_use()
{
    _mb_source_port="$1"
    valid_source_port "${_mb_source_port}" || return 1
    if [ -x "${SOCKSTAT_BIN}" ]; then
        if "${SOCKSTAT_BIN}" -4 -P tcp 2>/dev/null |
            awk -v port="${_mb_source_port}" '
                NR > 1 && $6 ~ ("[.:]" port "$") { found=1 }
                END { exit found ? 0 : 1 }
            '
        then
            return 0
        fi
    fi
    if [ -x "${NETSTAT_BIN}" ]; then
        if "${NETSTAT_BIN}" -an -p tcp 2>/dev/null |
            awk -v port="${_mb_source_port}" '
                tolower($1) ~ /^tcp/ && $4 ~ ("[.:]" port "$") { found=1 }
                END { exit found ? 0 : 1 }
            '
        then
            return 0
        fi
    fi
    return 1
}

route_add_source()
{
    _mb_rule="$1"; _mb_divert_port="$2"; _mb_address="$3"; _mb_wan="$4"
    _mb_transport="$5"; _mb_dport="$6"; _mb_source_port="$7"
    valid_rule "${_mb_rule}" || return 1
    valid_divert_port "${_mb_divert_port}" || return 1
    valid_ipv4 "${_mb_address}" || return 1
    [ -n "${_mb_wan}" ] || return 1
    valid_protocol "${_mb_transport}" || return 1
    valid_number_port "${_mb_dport}" || return 1
    valid_source_port "${_mb_source_port}" || return 1
    [ -x "${IPFW_BIN}" ] || return 1
    [ -x "${BASE_ADAPTER}" ] || return 1
    if "${BASE_ADAPTER}" rule-present "${_mb_rule}" >/dev/null 2>&1; then
        return 1
    fi
    "${IPFW_BIN}" -qf add "${_mb_rule}" divert "${_mb_divert_port}" \
        "${_mb_transport}" from me "${_mb_source_port}" to "${_mb_address}" "${_mb_dport}" \
        out not diverted not sockarg xmit "${_mb_wan}"
}

action="${1:-}"
case "${action}" in
    source-port-free)
        [ "$#" -eq 2 ] || exit 64
        source_port_in_use "$2" && exit 1
        exit 0
        ;;
    route-add-source)
        [ "$#" -eq 8 ] || exit 64
        route_add_source "$2" "$3" "$4" "$5" "$6" "$7" "$8"
        exit $?
        ;;
    '')
        exit 64
        ;;
    *)
        [ -x "${BASE_ADAPTER}" ] || exit 70
        exec "${BASE_ADAPTER}" "$@"
        ;;
esac
