#!/bin/sh

# Temporary Telegram Voice ordered-fragmentation proof-of-concept support.
#
# The request marker is intentionally stored under /var/run: the experiment is
# opt-in, survives ordinary service reconfigure operations, and returns to OFF
# after a reboot. The generated profile is prepended to the normal strategy,
# while firewall interception remains scoped to the managed Telegram IPv4 set.

TELEGRAM_VOICE_MARKER_FILE="${TELEGRAM_VOICE_MARKER_FILE:-/var/run/zapret2-telegram-voice-poc.enabled}"
TELEGRAM_VOICE_TABLE="${TELEGRAM_VOICE_TABLE:-zapret2_tgvoice}"
TELEGRAM_VOICE_STAGE_TABLE="${TELEGRAM_VOICE_STAGE_TABLE:-zapret2_tgvoice_stage}"
TELEGRAM_VOICE_STATE_FILE_NAME="telegram-voice-poc.state"
TELEGRAM_VOICE_USER_TRAFFIC_FILE_NAME="traffic-user.conf"
TELEGRAM_VOICE_PROFILE_NAME="telegram-voice-poc"

telegram_voice_state_is_enabled()
{
    _telegram_voice_state_file="$1"

    [ -r "${_telegram_voice_state_file}" ] &&
        grep -qx 'enabled' "${_telegram_voice_state_file}"
}

telegram_voice_marker_is_enabled()
{
    _telegram_voice_marker_file="${1:-${TELEGRAM_VOICE_MARKER_FILE}}"
    [ -f "${_telegram_voice_marker_file}" ]
}

telegram_voice_marker_enable()
{
    _telegram_voice_marker_file="${1:-${TELEGRAM_VOICE_MARKER_FILE}}"
    _telegram_voice_marker_parent=$(dirname "${_telegram_voice_marker_file}")
    _telegram_voice_marker_tmp="${_telegram_voice_marker_file}.tmp.$$"

    mkdir -p "${_telegram_voice_marker_parent}" || return 1
    ( umask 022 && printf '%s\n' enabled > "${_telegram_voice_marker_tmp}" ) || {
        rm -f "${_telegram_voice_marker_tmp}"
        return 1
    }
    mv -f "${_telegram_voice_marker_tmp}" "${_telegram_voice_marker_file}" || {
        rm -f "${_telegram_voice_marker_tmp}"
        return 1
    }
}

telegram_voice_marker_disable()
{
    _telegram_voice_marker_file="${1:-${TELEGRAM_VOICE_MARKER_FILE}}"
    rm -f "${_telegram_voice_marker_file}"
}

telegram_voice_build_effective_traffic()
{
    _telegram_voice_build_marker="$1"
    _telegram_voice_build_ipset_source="$2"
    _telegram_voice_build_ipset_reference="$3"
    _telegram_voice_build_user_traffic="$4"
    _telegram_voice_build_effective_traffic="$5"
    _telegram_voice_build_state="$6"
    _telegram_voice_build_traffic_tmp="${_telegram_voice_build_effective_traffic}.tmp.$$"
    _telegram_voice_build_state_tmp="${_telegram_voice_build_state}.tmp.$$"

    common_require_file \
        "${_telegram_voice_build_ipset_source}" \
        "managed Telegram IPv4 set" || return 1
    common_require_file \
        "${_telegram_voice_build_user_traffic}" \
        "resolved user traffic strategy" || return 1
    [ -s "${_telegram_voice_build_user_traffic}" ] || {
        common_error "resolved user traffic strategy is empty"
        return 1
    }
    case "${_telegram_voice_build_ipset_reference}" in
        /*) ;;
        *)
            common_error "Telegram Voice IP set reference must be absolute"
            return 1
            ;;
    esac

    if ! telegram_voice_marker_is_enabled \
        "${_telegram_voice_build_marker}"; then
        cp "${_telegram_voice_build_user_traffic}" \
            "${_telegram_voice_build_traffic_tmp}" || return 1
        printf '%s\n' disabled > "${_telegram_voice_build_state_tmp}" || {
            rm -f "${_telegram_voice_build_traffic_tmp}"
            return 1
        }
    else
        [ -s "${_telegram_voice_build_ipset_source}" ] || {
            common_error "Telegram Voice PoC requires at least one Telegram IPv4 target"
            return 1
        }

        {
            printf '%s\n' \
                "--name=${TELEGRAM_VOICE_PROFILE_NAME}" \
                '--filter-l3=ipv4' \
                '--filter-udp=*' \
                '--filter-l7=stun' \
                "--ipset=${_telegram_voice_build_ipset_reference}" \
                '--payload=stun' \
                '--lua-desync=send:ipfrag:ipfrag_pos_udp=8' \
                '--lua-desync=drop' \
                '--new'
            cat "${_telegram_voice_build_user_traffic}"
        } > "${_telegram_voice_build_traffic_tmp}" || {
            rm -f "${_telegram_voice_build_traffic_tmp}"
            return 1
        }
        printf '%s\n' enabled > "${_telegram_voice_build_state_tmp}" || {
            rm -f \
                "${_telegram_voice_build_traffic_tmp}" \
                "${_telegram_voice_build_state_tmp}"
            return 1
        }
    fi

    mv -f "${_telegram_voice_build_traffic_tmp}" \
        "${_telegram_voice_build_effective_traffic}" || {
            rm -f \
                "${_telegram_voice_build_traffic_tmp}" \
                "${_telegram_voice_build_state_tmp}"
            return 1
        }
    mv -f "${_telegram_voice_build_state_tmp}" \
        "${_telegram_voice_build_state}" || {
            rm -f "${_telegram_voice_build_state_tmp}"
            return 1
        }
}
