#!/bin/sh

strategy_lab_tls12_request()
{
    _slextreq_host="$1"
    _slextreq_output="$2"
    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_CURL_BIN}" || return 1
    "${STRATEGY_LAB_TIMEOUT_BIN}" 4 "${STRATEGY_LAB_CURL_BIN}" \
        --ipv4 --proto '=https' --tlsv1.2 --tls-max 1.2 --http1.1 \
        --request GET --location --max-redirs 2 --connect-timeout 2 --max-time 3 \
        --retry 0 --silent --show-error --header 'Connection: close' \
        --range 0-65535 --output /dev/null \
        --write-out 'exit=%{exitcode} remote_ip=%{remote_ip} http=%{http_version} code=%{response_code} bytes=%{size_download}\n' \
        "https://${_slextreq_host}/" > "${_slextreq_output}" 2>&1
}

strategy_lab_http_request()
{
    _slextreq_host="$1"
    _slextreq_output="$2"
    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_CURL_BIN}" || return 1
    "${STRATEGY_LAB_TIMEOUT_BIN}" 4 "${STRATEGY_LAB_CURL_BIN}" \
        --ipv4 --proto '=http' --http1.1 --request GET --location --max-redirs 2 \
        --connect-timeout 2 --max-time 3 --retry 0 --silent --show-error \
        --header 'Connection: close' --range 0-65535 --output /dev/null \
        --write-out 'exit=%{exitcode} remote_ip=%{remote_ip} http=%{http_version} code=%{response_code} bytes=%{size_download}\n' \
        "http://${_slextreq_host}/" > "${_slextreq_output}" 2>&1
}
