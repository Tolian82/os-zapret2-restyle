#!/bin/sh

strategy_lab_candidate_endpoint_probe()
{
    _slext_probe_endpoint="$1"
    _slext_probe_index="$2"
    _slext_probe_workdir="$3"
    _slext_probe_output="$4"
    _slext_probe_raw="${_slext_probe_workdir}/candidate-endpoint-${_slext_probe_index}.log"
    _slext_probe_protocol="${STRATEGY_LAB_CANDIDATE_PROTOCOL:-tls13}"

    if strategy_lab_ipv4_valid "${_slext_probe_endpoint}"; then
        _slext_probe_port="${STRATEGY_LAB_CANDIDATE_PORT:-443}"
        if strategy_lab_tcp_request "${_slext_probe_endpoint}" "${_slext_probe_port}" "${_slext_probe_raw}"; then _slext_probe_status=PASS; _slext_probe_exit=0; else _slext_probe_exit=$?; _slext_probe_status=FAIL; fi
        strategy_lab_endpoint_result_write "${_slext_probe_endpoint}" "${_slext_probe_status}" "${_slext_probe_exit}" "tcp-${_slext_probe_port}" "${_slext_probe_raw}" "${_slext_probe_output}"
        return 0
    fi

    case "${_slext_probe_protocol}" in
        tls12) strategy_lab_tls12_request "${_slext_probe_endpoint}" "${_slext_probe_raw}" ;;
        http) strategy_lab_http_request "${_slext_probe_endpoint}" "${_slext_probe_raw}" ;;
        *) strategy_lab_tls13_request ipv4 "${_slext_probe_endpoint}" "${_slext_probe_raw}" ;;
    esac
    _slext_probe_exit=$?
    if [ "${_slext_probe_exit}" -eq 0 ]; then _slext_probe_status=PASS; else _slext_probe_status=FAIL; fi
    _slext_probe_reported=$(strategy_lab_request_exit_from_output "${_slext_probe_raw}" 2>/dev/null || true)
    [ -z "${_slext_probe_reported}" ] || _slext_probe_exit="${_slext_probe_reported}"
    strategy_lab_endpoint_result_write "${_slext_probe_endpoint}" "${_slext_probe_status}" "${_slext_probe_exit}" "${_slext_probe_protocol}-ipv4" "${_slext_probe_raw}" "${_slext_probe_output}"
}
