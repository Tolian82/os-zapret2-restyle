#!/bin/sh

strategy_lab_candidate_endpoint_probe()
{
    _slext_probe_endpoint="$1"
    _slext_probe_index="$2"
    _slext_probe_workdir="$3"
    _slext_probe_output="$4"
    _slext_probe_raw="${_slext_probe_workdir}/candidate-endpoint-${_slext_probe_index}.log"
    _slext_probe_state="${_slext_probe_workdir}/candidate-endpoint-${_slext_probe_index}.interception"
    _slext_probe_protocol="${STRATEGY_LAB_CANDIDATE_PROTOCOL:-tls13}"
    _slext_probe_port="${STRATEGY_LAB_CANDIDATE_PORT:-443}"

    strategy_lab_candidate_probe_begin \
        "${_slext_probe_workdir}" "${_slext_probe_index}" "${_slext_probe_state}" || return 1
    _slext_probe_selected=$(sed -n '1p' "${_slext_probe_state}")

    if strategy_lab_ipv4_valid "${_slext_probe_endpoint}"; then
        if strategy_lab_tcp_request "${_slext_probe_selected}" "${_slext_probe_port}" "${_slext_probe_raw}"; then
            _slext_probe_exit=0
        else
            _slext_probe_exit=$?
        fi
        _slext_probe_remote="${_slext_probe_selected}"
        _slext_probe_transport="tcp-${_slext_probe_port}"
    else
        case "${_slext_probe_protocol}" in
            tls12)
                strategy_lab_tls12_bound_request \
                    "${_slext_probe_endpoint}" "${_slext_probe_selected}" "${_slext_probe_raw}"
                ;;
            http)
                strategy_lab_http_bound_request \
                    "${_slext_probe_endpoint}" "${_slext_probe_selected}" "${_slext_probe_raw}"
                ;;
            *)
                strategy_lab_tls13_bound_request \
                    "${_slext_probe_endpoint}" "${_slext_probe_selected}" "${_slext_probe_raw}"
                ;;
        esac
        _slext_probe_exit=$?
        _slext_probe_reported=$(strategy_lab_request_exit_from_output "${_slext_probe_raw}" 2>/dev/null || true)
        [ -z "${_slext_probe_reported}" ] || _slext_probe_exit="${_slext_probe_reported}"
        _slext_probe_remote=$(strategy_lab_request_remote_ip_from_output "${_slext_probe_raw}" 2>/dev/null || true)
        _slext_probe_transport="${_slext_probe_protocol}-ipv4"
    fi

    strategy_lab_candidate_endpoint_result_write \
        "${_slext_probe_endpoint}" "${_slext_probe_exit}" "${_slext_probe_transport}" \
        "${_slext_probe_raw}" "${_slext_probe_remote}" "${_slext_probe_state}" \
        "${_slext_probe_output}"
}
