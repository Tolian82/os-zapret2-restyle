#!/bin/sh

# Stage module public API
#
#   stage_write FILE INDEX TOTAL NAME STATE [MESSAGE]
#   stage_fail  FILE INDEX TOTAL NAME MESSAGE
#   stage_read  FILE
#   stage_clear FILE
#
# This module is the only owner of Execution Pipeline state. It has no
# knowledge of Launcher, Firewall, Supervisor, GUI, or configuration internals.

stage_sanitize()
{
    _stage_sanitize_value="$1"

    # A status record uses "|" as a delimiter and one physical line.
    printf '%s' "${_stage_sanitize_value}" |
        tr '\t\r\n|' '    '
}

stage_validate_position()
{
    _stage_position_index="$1"
    _stage_position_total="$2"

    case "${_stage_position_index}:${_stage_position_total}" in
        *[!0-9:]*|:*|*:)
            common_error "invalid execution stage position"
            return 1
            ;;
    esac

    [ "${_stage_position_index}" -ge 1 ] 2>/dev/null &&
    [ "${_stage_position_total}" -ge "${_stage_position_index}" ] \
        2>/dev/null || {
            common_error "invalid execution stage position ${_stage_position_index}/${_stage_position_total}"
            return 1
        }
}

stage_validate_state()
{
    _stage_state_value="$1"

    case "${_stage_state_value}" in
        running|ok|failed|stopped) return 0 ;;
        *)
            common_error "invalid execution stage state '${_stage_state_value}'"
            return 1
            ;;
    esac
}

stage_write()
{
    _stage_write_file="$1"
    _stage_write_index="$2"
    _stage_write_total="$3"
    _stage_write_name="$4"
    _stage_write_state="$5"
    _stage_write_message="${6:-}"
    _stage_write_tmp="${_stage_write_file}.tmp.$$"

    [ -n "${_stage_write_file}" ] || {
        common_error "execution stage file path is empty"
        return 1
    }

    stage_validate_position \
        "${_stage_write_index}" "${_stage_write_total}" || return 1
    stage_validate_state "${_stage_write_state}" || return 1

    _stage_write_parent=$(dirname "${_stage_write_file}")
    mkdir -p "${_stage_write_parent}" || {
        common_error "cannot create execution stage directory"
        return 1
    }

    _stage_write_safe_name=$(stage_sanitize "${_stage_write_name}") ||
        return 1
    _stage_write_safe_message=$(stage_sanitize "${_stage_write_message}") ||
        return 1
    _stage_write_timestamp=$(date '+%Y-%m-%dT%H:%M:%S%z')

    printf '%s|%s|%s|%s|%s|%s\n' \
        "${_stage_write_index}" \
        "${_stage_write_total}" \
        "${_stage_write_safe_name}" \
        "${_stage_write_state}" \
        "${_stage_write_timestamp}" \
        "${_stage_write_safe_message}" \
        > "${_stage_write_tmp}" || {
            rm -f "${_stage_write_tmp}"
            return 1
        }

    mv -f "${_stage_write_tmp}" "${_stage_write_file}" || {
        rm -f "${_stage_write_tmp}"
        common_error "cannot install execution stage record"
        return 1
    }
}

stage_fail()
{
    stage_write "$1" "$2" "$3" "$4" failed "$5"
}

stage_read()
{
    _stage_read_file="$1"

    [ -f "${_stage_read_file}" ] || return 1
    cat "${_stage_read_file}"
}

stage_clear()
{
    _stage_clear_file="$1"

    [ -n "${_stage_clear_file}" ] || return 1
    rm -f "${_stage_clear_file}" "${_stage_clear_file}.tmp."*
}
