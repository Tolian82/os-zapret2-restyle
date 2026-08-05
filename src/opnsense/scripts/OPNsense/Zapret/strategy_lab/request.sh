#!/bin/sh

STRATEGY_LAB_TIMEOUT_BIN="${STRATEGY_LAB_TIMEOUT_BIN:-/usr/bin/timeout}"
STRATEGY_LAB_CURL_BIN="${STRATEGY_LAB_CURL_BIN:-/usr/local/bin/curl}"
STRATEGY_LAB_DRILL_BIN="${STRATEGY_LAB_DRILL_BIN:-/usr/bin/drill}"
STRATEGY_LAB_OPENSSL_BIN="${STRATEGY_LAB_OPENSSL_BIN:-/usr/bin/openssl}"
STRATEGY_LAB_NETSTAT_BIN="${STRATEGY_LAB_NETSTAT_BIN:-/usr/bin/netstat}"
STRATEGY_LAB_NC_BIN="${STRATEGY_LAB_NC_BIN:-/usr/bin/nc}"

strategy_lab_require_executable()
{
    [ -x "$1" ] || {
        echo "ERROR: required Strategy Lab executable is unavailable: $1" >&2
        return 1
    }
}

strategy_lab_tls13_request()
{
    _strategy_lab_family="$1"
    _strategy_lab_host="$2"
    _strategy_lab_output="$3"

    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_CURL_BIN}" || return 1

    "${STRATEGY_LAB_TIMEOUT_BIN}" 4 \
        "${STRATEGY_LAB_CURL_BIN}" \
        "--${_strategy_lab_family}" \
        --proto '=https' \
        --tlsv1.3 \
        --tls-max 1.3 \
        --http1.1 \
        --request GET \
        --location \
        --max-redirs 2 \
        --connect-timeout 2 \
        --max-time 3 \
        --retry 0 \
        --silent \
        --show-error \
        --header 'Connection: close' \
        --range 0-65535 \
        --output /dev/null \
        --write-out 'exit=%{exitcode} remote_ip=%{remote_ip} http=%{http_version} code=%{response_code} bytes=%{size_download}\n' \
        "https://${_strategy_lab_host}/" > "${_strategy_lab_output}" 2>&1
}

strategy_lab_tls13_bound_request()
{
    _slreq_host="$1"
    _slreq_ip="$2"
    _slreq_output="$3"

    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_CURL_BIN}" || return 1

    "${STRATEGY_LAB_TIMEOUT_BIN}" 4 \
        "${STRATEGY_LAB_CURL_BIN}" \
        --ipv4 \
        --proto '=https' \
        --tlsv1.3 \
        --tls-max 1.3 \
        --http1.1 \
        --request GET \
        --max-redirs 0 \
        --resolve "${_slreq_host}:443:${_slreq_ip}" \
        --connect-timeout 2 \
        --max-time 3 \
        --retry 0 \
        --silent \
        --show-error \
        --header 'Connection: close' \
        --range 0-65535 \
        --output /dev/null \
        --write-out 'exit=%{exitcode} remote_ip=%{remote_ip} http=%{http_version} code=%{response_code} bytes=%{size_download}\n' \
        "https://${_slreq_host}/" > "${_slreq_output}" 2>&1
}

strategy_lab_dns_request()
{
    _strategy_lab_host="$1"
    _strategy_lab_type="$2"
    _strategy_lab_output="$3"

    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_DRILL_BIN}" || return 1

    "${STRATEGY_LAB_TIMEOUT_BIN}" 2 \
        "${STRATEGY_LAB_DRILL_BIN}" "${_strategy_lab_host}" "${_strategy_lab_type}" \
        > "${_strategy_lab_output}" 2>&1
}

strategy_lab_ipv6_default_route_available()
{
    strategy_lab_require_executable "${STRATEGY_LAB_NETSTAT_BIN}" || return 1
    "${STRATEGY_LAB_NETSTAT_BIN}" -rn -f inet6 2>/dev/null |
        grep -Eq '^default[[:space:]]'
}

strategy_lab_quic_ipv4_request()
{
    _strategy_lab_output="$1"

    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_OPENSSL_BIN}" || return 1

    "${STRATEGY_LAB_TIMEOUT_BIN}" 2 \
        "${STRATEGY_LAB_OPENSSL_BIN}" s_client \
        -4 \
        -quic \
        -connect yandex.ru:443 \
        -servername yandex.ru \
        -alpn h3 \
        -verify_hostname yandex.ru \
        -verify_return_error \
        -brief \
        -no-interactive \
        </dev/null > "${_strategy_lab_output}" 2>&1
}

strategy_lab_tcp_request()
{
    _strategy_lab_host="$1"
    _strategy_lab_port="$2"
    _strategy_lab_output="$3"

    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_NC_BIN}" || return 1

    "${STRATEGY_LAB_TIMEOUT_BIN}" 3 \
        "${STRATEGY_LAB_NC_BIN}" -z -w 2 "${_strategy_lab_host}" "${_strategy_lab_port}" \
        > "${_strategy_lab_output}" 2>&1
}
