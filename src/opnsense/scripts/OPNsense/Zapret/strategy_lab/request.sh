#!/bin/sh

STRATEGY_LAB_TIMEOUT_BIN="${STRATEGY_LAB_TIMEOUT_BIN:-/usr/bin/timeout}"
STRATEGY_LAB_CURL_BIN="${STRATEGY_LAB_CURL_BIN:-/usr/local/bin/curl}"
STRATEGY_LAB_DRILL_BIN="${STRATEGY_LAB_DRILL_BIN:-/usr/bin/drill}"
STRATEGY_LAB_OPENSSL_BIN="${STRATEGY_LAB_OPENSSL_BIN:-/usr/bin/openssl}"
STRATEGY_LAB_NETSTAT_BIN="${STRATEGY_LAB_NETSTAT_BIN:-/usr/bin/netstat}"
STRATEGY_LAB_NC_BIN="${STRATEGY_LAB_NC_BIN:-/usr/bin/nc}"
STRATEGY_LAB_PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}/strategy_lab_python_launcher.sh}"

strategy_lab_require_executable()
{
    [ -x "$1" ] || {
        echo "ERROR: required Strategy Lab executable is unavailable: $1" >&2
        return 1
    }
}

strategy_lab_request_python()
{
    strategy_lab_require_executable "${STRATEGY_LAB_PYTHON_LAUNCHER}" || return 1
    "${STRATEGY_LAB_PYTHON_LAUNCHER}" request "$@"
}

strategy_lab_tls13_request()
{
    strategy_lab_request_python tls13 "$1" "$2" "$3"
}

strategy_lab_tls13_bound_request()
{
    strategy_lab_request_python tls13-bound "$1" "$2" "$3"
}

strategy_lab_dns_request()
{
    strategy_lab_request_python dns "$1" "$2" "$3"
}

strategy_lab_dns_first_answer()
{
    strategy_lab_request_python parse-dns "$1" "$2"
}

strategy_lab_ipv6_default_route_available()
{
    strategy_lab_request_python ipv6-route
}

strategy_lab_quic_ipv4_request()
{
    strategy_lab_request_python quic-ipv4 "$1"
}

strategy_lab_tcp_request()
{
    strategy_lab_request_python tcp "$1" "$2" "$3"
}
