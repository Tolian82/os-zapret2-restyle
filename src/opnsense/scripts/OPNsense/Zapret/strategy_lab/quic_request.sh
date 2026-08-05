#!/bin/sh

strategy_lab_quic_target_request()
{
    _slquicreq_host="$1"
    _slquicreq_ip="$2"
    _slquicreq_output="$3"
    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_OPENSSL_BIN}" || return 1
    "${STRATEGY_LAB_TIMEOUT_BIN}" 3 "${STRATEGY_LAB_OPENSSL_BIN}" s_client \
        -4 -quic -connect "${_slquicreq_ip}:443" -servername "${_slquicreq_host}" \
        -alpn h3 -verify_hostname "${_slquicreq_host}" -verify_return_error -brief -no-interactive \
        </dev/null > "${_slquicreq_output}" 2>&1
}
