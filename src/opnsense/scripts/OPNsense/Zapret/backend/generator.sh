#!/bin/sh

# Public API:
#   generator_build_args OUTPUT DIVERT_PORT TRAFFIC_FILE EXTRA_FILE
#                        BLOB_ARGS_FILE EXCLUDE_FILE [LUA_FILE ...]
#
# Assembly order:
#   1. divert socket
#   2. Lua initializers
#   3. globally loaded blobs
#   4. resolved traffic strategy
#   5. global hostlist exclusion, when non-empty
#   6. extra arguments
#
# POSIX sh has no portable local variables. Every function therefore uses a
# function-specific variable prefix so helper calls cannot overwrite caller
# state.

generator_validate_port()
{
    _generator_validate_port_value="$1"

    case "${_generator_validate_port_value}" in
        ''|*[!0-9]*)
            common_error "invalid divert port '${_generator_validate_port_value}'"
            return 1
            ;;
    esac

    [ "${_generator_validate_port_value}" -ge 1 ] 2>/dev/null &&
    [ "${_generator_validate_port_value}" -le 65535 ] 2>/dev/null || {
        common_error "divert port outside valid range: ${_generator_validate_port_value}"
        return 1
    }
}

generator_append_file()
{
    _generator_append_source="$1"
    _generator_append_destination="$2"
    _generator_append_label="$3"
    _generator_append_required="$4"

    common_require_file \
        "${_generator_append_source}" \
        "${_generator_append_label}" || return 1

    if [ ! -s "${_generator_append_source}" ]; then
        if [ "${_generator_append_required}" = "1" ]; then
            common_error "${_generator_append_label} is empty: ${_generator_append_source}"
            return 1
        fi
        return 0
    fi

    cat "${_generator_append_source}" >> "${_generator_append_destination}" ||
        return 1

    # Ensure the next generated argument starts on a fresh line even when an
    # upstream artifact lacks a trailing newline.
    if [ -n "$(tail -c 1 "${_generator_append_source}" 2>/dev/null)" ]; then
        printf '\n' >> "${_generator_append_destination}" || return 1
    fi
}

generator_build_args()
{
    _generator_build_output="$1"
    _generator_build_divert="$2"
    _generator_build_traffic="$3"
    _generator_build_extra="$4"
    _generator_build_blob_args="$5"
    _generator_build_exclude="$6"
    shift 6

    _generator_build_tmp="${_generator_build_output}.tmp.$$"

    generator_validate_port "${_generator_build_divert}" || return 1
    common_require_file \
        "${_generator_build_traffic}" "resolved traffic strategy" || return 1
    common_require_file \
        "${_generator_build_extra}" "resolved extra arguments" || return 1
    common_require_file \
        "${_generator_build_blob_args}" "blob argument list" || return 1
    common_require_file \
        "${_generator_build_exclude}" "Exclude Domains list" || return 1

    [ -s "${_generator_build_traffic}" ] || {
        common_error "resolved traffic strategy is empty"
        return 1
    }

    : > "${_generator_build_tmp}" || {
        common_error "cannot create generated argument file: ${_generator_build_tmp}"
        return 1
    }

    printf '%s\n' "--port=${_generator_build_divert}" \
        >> "${_generator_build_tmp}" || {
            rm -f "${_generator_build_tmp}"
            return 1
        }

    for _generator_build_lua in "$@"; do
        common_require_file \
            "${_generator_build_lua}" "Lua initializer" || {
                rm -f "${_generator_build_tmp}"
                return 1
            }
        [ -s "${_generator_build_lua}" ] || {
            common_error "Lua initializer is empty: ${_generator_build_lua}"
            rm -f "${_generator_build_tmp}"
            return 1
        }
        printf '%s\n' "--lua-init=@${_generator_build_lua}" \
            >> "${_generator_build_tmp}" || {
                rm -f "${_generator_build_tmp}"
                return 1
            }
    done

    generator_append_file \
        "${_generator_build_blob_args}" "${_generator_build_tmp}" \
        "blob argument list" 0 || {
            rm -f "${_generator_build_tmp}"
            return 1
        }

    generator_append_file \
        "${_generator_build_traffic}" "${_generator_build_tmp}" \
        "resolved traffic strategy" 1 || {
            rm -f "${_generator_build_tmp}"
            return 1
        }

    if [ -s "${_generator_build_exclude}" ]; then
        printf '%s\n' \
            "--hostlist-exclude=${_generator_build_exclude}" \
            >> "${_generator_build_tmp}" || {
                rm -f "${_generator_build_tmp}"
                return 1
            }
    fi

    generator_append_file \
        "${_generator_build_extra}" "${_generator_build_tmp}" \
        "resolved extra arguments" 0 || {
            rm -f "${_generator_build_tmp}"
            return 1
        }

    mv -f "${_generator_build_tmp}" "${_generator_build_output}" || {
        rm -f "${_generator_build_tmp}"
        common_error \
            "cannot install generated argument file: ${_generator_build_output}"
        return 1
    }
}

# Generate arguments from a staged exclusion file while emitting its stable
# post-install path.
generator_build_args_mapped()
{
    _generator_mapped_output="$1"
    _generator_mapped_divert="$2"
    _generator_mapped_traffic="$3"
    _generator_mapped_extra="$4"
    _generator_mapped_blob_args="$5"
    _generator_mapped_exclude_source="$6"
    _generator_mapped_exclude_reference="$7"
    shift 7

    _generator_mapped_empty=$(mktemp /tmp/zapret-generator-empty.XXXXXX) ||
        return 1
    : > "${_generator_mapped_empty}"

    generator_build_args \
        "${_generator_mapped_output}" \
        "${_generator_mapped_divert}" \
        "${_generator_mapped_traffic}" \
        "${_generator_mapped_extra}" \
        "${_generator_mapped_blob_args}" \
        "${_generator_mapped_empty}" \
        "$@" || {
            rm -f "${_generator_mapped_empty}"
            return 1
        }

    rm -f "${_generator_mapped_empty}"

    if [ -s "${_generator_mapped_exclude_source}" ]; then
        _generator_mapped_tmp="${_generator_mapped_output}.mapped.$$"
        cat "${_generator_mapped_output}" > "${_generator_mapped_tmp}" || {
            rm -f "${_generator_mapped_tmp}"
            return 1
        }
        printf '%s\n' \
            "--hostlist-exclude=${_generator_mapped_exclude_reference}" \
            >> "${_generator_mapped_tmp}" || {
                rm -f "${_generator_mapped_tmp}"
                return 1
            }
        mv -f "${_generator_mapped_tmp}" \
            "${_generator_mapped_output}" || {
                rm -f "${_generator_mapped_tmp}"
                return 1
            }
    fi
}
