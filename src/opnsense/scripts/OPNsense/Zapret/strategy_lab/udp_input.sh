#!/bin/sh

STRATEGY_LAB_UDP_PAYLOAD_MAX_BYTES="${STRATEGY_LAB_UDP_PAYLOAD_MAX_BYTES:-4096}"
STRATEGY_LAB_BASE64_BIN="${STRATEGY_LAB_BASE64_BIN:-/usr/bin/base64}"
STRATEGY_LAB_UDP_INPUT_ERROR=''

strategy_lab_udp_input_fail()
{
    STRATEGY_LAB_UDP_INPUT_ERROR="$1"
    export STRATEGY_LAB_UDP_INPUT_ERROR
    return 1
}

strategy_lab_udp_port_file()
{
    printf '%s/udp-port\n' "$(strategy_lab_job_dir "$1")"
}

strategy_lab_udp_payload_file()
{
    printf '%s/udp-payload.bin\n' "$(strategy_lab_job_dir "$1")"
}

strategy_lab_udp_input_record()
{
    _sluir_job="$1"
    _sluir_configured="$2"
    _sluir_port="$3"
    _sluir_bytes="$4"

    strategy_lab_state_python set-udp-request \
        "${_sluir_job}" "$(strategy_lab_status_file "${_sluir_job}")" \
        "${_sluir_configured}" "${_sluir_port}" "${_sluir_bytes}"
}

strategy_lab_udp_input_cleanup()
{
    _sluic_job="$1"
    rm -f "$(strategy_lab_udp_port_file "${_sluic_job}")" \
          "$(strategy_lab_udp_payload_file "${_sluic_job}")"
}

strategy_lab_udp_input_prepare()
{
    _sluip_job="$1"
    _sluip_mode="$2"
    _sluip_port="$3"
    _sluip_payload="$4"
    _sluip_jobdir=$(strategy_lab_job_dir "${_sluip_job}")
    STRATEGY_LAB_UDP_INPUT_ERROR=''
    export STRATEGY_LAB_UDP_INPUT_ERROR

    [ -d "${_sluip_jobdir}" ] || { strategy_lab_udp_input_fail job_directory_unavailable; return 1; }
    [ -w "${_sluip_jobdir}" ] || { strategy_lab_udp_input_fail job_directory_not_writable; return 1; }
    case "${STRATEGY_LAB_UDP_PAYLOAD_MAX_BYTES}" in
        ''|*[!0-9]*) strategy_lab_udp_input_fail payload_limit_invalid; return 1 ;;
    esac
    [ "${STRATEGY_LAB_UDP_PAYLOAD_MAX_BYTES}" -ge 1 ] || { strategy_lab_udp_input_fail payload_limit_invalid; return 1; }

    if [ "${_sluip_port}" = '-' ] && [ "${_sluip_payload}" = '-' ]; then
        strategy_lab_udp_input_cleanup "${_sluip_job}"
        if ! strategy_lab_udp_input_record "${_sluip_job}" false 0 0; then
            strategy_lab_udp_input_fail state_record_failed
            return 1
        fi
        return 0
    fi

    [ "${_sluip_mode}" = extended ] || { strategy_lab_udp_input_fail mode_invalid; return 1; }
    [ "${_sluip_port}" != '-' ] && [ "${_sluip_payload}" != '-' ] || { strategy_lab_udp_input_fail port_payload_pair_invalid; return 1; }

    case "${_sluip_port}" in
        ''|*[!0-9]*) strategy_lab_udp_input_fail port_invalid; return 1 ;;
    esac
    [ "${_sluip_port}" -ge 1 ] 2>/dev/null &&
        [ "${_sluip_port}" -le 65535 ] 2>/dev/null || { strategy_lab_udp_input_fail port_invalid; return 1; }

    printf '%s\n' "${_sluip_payload}" |
        grep -Eq '^[A-Za-z0-9+/]+={0,2}$' || { strategy_lab_udp_input_fail base64_invalid; return 1; }
    _sluip_encoded_length=${#_sluip_payload}
    [ $((_sluip_encoded_length % 4)) -eq 0 ] || { strategy_lab_udp_input_fail base64_invalid; return 1; }
    [ -x "${STRATEGY_LAB_BASE64_BIN}" ] || { strategy_lab_udp_input_fail base64_decoder_unavailable; return 1; }

    _sluip_payload_file=$(strategy_lab_udp_payload_file "${_sluip_job}")
    _sluip_port_file=$(strategy_lab_udp_port_file "${_sluip_job}")
    _sluip_payload_tmp=$(mktemp "${_sluip_jobdir}/.udp-payload.XXXXXX") || {
        strategy_lab_udp_input_fail payload_temp_create_failed
        return 1
    }
    _sluip_port_tmp=$(mktemp "${_sluip_jobdir}/.udp-port.XXXXXX") || {
        rm -f "${_sluip_payload_tmp}"
        strategy_lab_udp_input_fail port_temp_create_failed
        return 1
    }

    if ! printf '%s' "${_sluip_payload}" |
        "${STRATEGY_LAB_BASE64_BIN}" -d > "${_sluip_payload_tmp}" 2>/dev/null
    then
        rm -f "${_sluip_payload_tmp}" "${_sluip_port_tmp}"
        strategy_lab_udp_input_fail base64_decode_failed
        return 1
    fi

    _sluip_bytes=$(wc -c < "${_sluip_payload_tmp}" | tr -d '[:space:]')
    case "${_sluip_bytes}" in
        ''|*[!0-9]*|0)
            rm -f "${_sluip_payload_tmp}" "${_sluip_port_tmp}"
            strategy_lab_udp_input_fail payload_size_invalid
            return 1
            ;;
    esac
    if [ "${_sluip_bytes}" -gt "${STRATEGY_LAB_UDP_PAYLOAD_MAX_BYTES}" ]; then
        rm -f "${_sluip_payload_tmp}" "${_sluip_port_tmp}"
        strategy_lab_udp_input_fail payload_size_invalid
        return 1
    fi

    printf '%s\n' "${_sluip_port}" > "${_sluip_port_tmp}" || {
        rm -f "${_sluip_payload_tmp}" "${_sluip_port_tmp}"
        strategy_lab_udp_input_fail port_write_failed
        return 1
    }
    chmod 0600 "${_sluip_payload_tmp}" "${_sluip_port_tmp}" || {
        rm -f "${_sluip_payload_tmp}" "${_sluip_port_tmp}"
        strategy_lab_udp_input_fail chmod_failed
        return 1
    }
    mv -f "${_sluip_payload_tmp}" "${_sluip_payload_file}" || {
        rm -f "${_sluip_payload_tmp}" "${_sluip_port_tmp}"
        strategy_lab_udp_input_fail payload_move_failed
        return 1
    }
    mv -f "${_sluip_port_tmp}" "${_sluip_port_file}" || {
        rm -f "${_sluip_port_tmp}" "${_sluip_payload_file}"
        strategy_lab_udp_input_fail port_move_failed
        return 1
    }

    if ! strategy_lab_udp_input_record "${_sluip_job}" true \
        "${_sluip_port}" "${_sluip_bytes}"
    then
        strategy_lab_udp_input_cleanup "${_sluip_job}"
        strategy_lab_udp_input_fail state_record_failed
        return 1
    fi
    return 0
}

strategy_lab_udp_input_export()
{
    _sluie_job="$1"
    _sluie_status=$(strategy_lab_status_file "${_sluie_job}")
    _sluie_port_file=$(strategy_lab_udp_port_file "${_sluie_job}")
    _sluie_payload_file=$(strategy_lab_udp_payload_file "${_sluie_job}")
    [ -r "${_sluie_status}" ] || return 1

    _sluie_configured=$("${STRATEGY_LAB_JQ}" -r \
        '.udp_request.configured // false' "${_sluie_status}") || return 1
    if [ "${_sluie_configured}" != true ]; then
        unset STRATEGY_LAB_UDP_PORT STRATEGY_LAB_UDP_PAYLOAD_FILE
        return 0
    fi

    [ -r "${_sluie_port_file}" ] && [ -r "${_sluie_payload_file}" ] &&
        [ -s "${_sluie_payload_file}" ] || return 1
    _sluie_port=$(cat "${_sluie_port_file}")
    case "${_sluie_port}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "${_sluie_port}" -ge 1 ] 2>/dev/null &&
        [ "${_sluie_port}" -le 65535 ] 2>/dev/null || return 1

    STRATEGY_LAB_UDP_PORT="${_sluie_port}"
    STRATEGY_LAB_UDP_PAYLOAD_FILE="${_sluie_payload_file}"
    export STRATEGY_LAB_UDP_PORT STRATEGY_LAB_UDP_PAYLOAD_FILE
}