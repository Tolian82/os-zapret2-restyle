#!/bin/sh

strategy_lab_udp_response_request()
{
    _sludpreq_host="$1"; _sludpreq_port="$2"; _sludpreq_payload="$3"; _sludpreq_output="$4"
    strategy_lab_require_executable "${STRATEGY_LAB_TIMEOUT_BIN}" || return 1
    strategy_lab_require_executable "${STRATEGY_LAB_NC_BIN}" || return 1
    [ -r "${_sludpreq_payload}" ] && [ -s "${_sludpreq_payload}" ] || return 1
    "${STRATEGY_LAB_TIMEOUT_BIN}" 4 "${STRATEGY_LAB_NC_BIN}" -u -w 2 "${_sludpreq_host}" "${_sludpreq_port}" \
        < "${_sludpreq_payload}" > "${_sludpreq_output}" 2>&1 || return $?
    [ -s "${_sludpreq_output}" ]
}
