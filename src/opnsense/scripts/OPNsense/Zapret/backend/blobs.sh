#!/bin/sh

# Public API:
#   blobs_resolve_file INPUT OUTPUT ARGS_FILE LOADED_FILE FAKE_DIR
#
# Shorthand declarations:
#   --blob=tls7
#
# are removed from the strategy and registered once as:
#   --blob=tls7:@/path/to/files/fake/tls7.bin
#
# Native upstream declarations containing ":" remain in place:
#   --blob=name:@/path/file.bin
#   --blob=name:0x00112233

blobs_validate_name()
{
    _blobs_name="$1"

    [ -n "${_blobs_name}" ] || {
        common_error "empty blob name"
        return 1
    }

    case "${_blobs_name}" in
        *[!A-Za-z0-9_.-]*)
            common_error "invalid blob name '${_blobs_name}'"
            return 1
            ;;
    esac
}

blobs_is_loaded()
{
    _blobs_name="$1"
    _blobs_loaded_file="$2"

    [ -f "${_blobs_loaded_file}" ] &&
        grep -Fxq "${_blobs_name}" "${_blobs_loaded_file}"
}

blobs_register()
{
    _blobs_name="$1"
    _blobs_args_file="$2"
    _blobs_loaded_file="$3"
    _blobs_fake_dir="$4"

    blobs_validate_name "${_blobs_name}" || return 1

    _blobs_file="${_blobs_fake_dir}/${_blobs_name}.bin"
    common_require_file "${_blobs_file}" "blob '${_blobs_name}'" || return 1

    if blobs_is_loaded "${_blobs_name}" "${_blobs_loaded_file}"; then
        return 0
    fi

    printf '%s\n' "${_blobs_name}" >> "${_blobs_loaded_file}" || return 1
    printf '%s\n' "--blob=${_blobs_name}:@${_blobs_file}" >> "${_blobs_args_file}" || return 1
}

blobs_resolve_line()
{
    _blobs_line="$1"
    _blobs_args_file="$2"
    _blobs_loaded_file="$3"
    _blobs_fake_dir="$4"
    _blobs_result=""
    _blobs_separator=""

    # dvtws2 arguments are whitespace-delimited. Rebuilding one line with
    # single spaces changes formatting only around argument boundaries and
    # leaves argument values untouched.
    for _blobs_token in ${_blobs_line}; do
        case "${_blobs_token}" in
            --blob=*)
                _blobs_spec=${_blobs_token#--blob=}

                [ -n "${_blobs_spec}" ] || {
                    common_error "empty blob declaration '--blob='"
                    return 1
                }

                case "${_blobs_spec}" in
                    *:*)
                        _blobs_result="${_blobs_result}${_blobs_separator}${_blobs_token}"
                        _blobs_separator=" "
                        ;;
                    *)
                        blobs_register \
                            "${_blobs_spec}" \
                            "${_blobs_args_file}" \
                            "${_blobs_loaded_file}" \
                            "${_blobs_fake_dir}" || return 1
                        ;;
                esac
                ;;
            *)
                _blobs_result="${_blobs_result}${_blobs_separator}${_blobs_token}"
                _blobs_separator=" "
                ;;
        esac
    done

    printf '%s\n' "${_blobs_result}"
}

blobs_resolve_file()
{
    _blobs_input="$1"
    _blobs_output="$2"
    _blobs_args_file="$3"
    _blobs_loaded_file="$4"
    _blobs_fake_dir="$5"
    _blobs_tmp="${_blobs_output}.tmp.$$"

    common_require_file "${_blobs_input}" "blob resolver input" || return 1
    [ -d "${_blobs_fake_dir}" ] || {
        common_error "blob directory does not exist: ${_blobs_fake_dir}"
        return 1
    }

    : > "${_blobs_args_file}" 2>/dev/null || {
        common_error "cannot write blob argument file: ${_blobs_args_file}"
        return 1
    }
    : > "${_blobs_loaded_file}" 2>/dev/null || {
        common_error "cannot write loaded blob index: ${_blobs_loaded_file}"
        return 1
    }
    : > "${_blobs_tmp}" || return 1

    while IFS= read -r _blobs_line || [ -n "${_blobs_line}" ]; do
        if [ -z "${_blobs_line}" ]; then
            printf '\n' >> "${_blobs_tmp}" || {
                rm -f "${_blobs_tmp}"
                return 1
            }
            continue
        fi

        _blobs_resolved=$(blobs_resolve_line \
            "${_blobs_line}" \
            "${_blobs_args_file}" \
            "${_blobs_loaded_file}" \
            "${_blobs_fake_dir}") || {
                rm -f "${_blobs_tmp}"
                return 1
            }

        printf '%s\n' "${_blobs_resolved}" >> "${_blobs_tmp}" || {
            rm -f "${_blobs_tmp}"
            return 1
        }
    done < "${_blobs_input}"

    mv -f "${_blobs_tmp}" "${_blobs_output}" || {
        rm -f "${_blobs_tmp}"
        return 1
    }
}

# Resolve another text artifact while preserving the shared blob registry
# created by an earlier blobs_resolve_file call.
blobs_resolve_file_append()
{
    _blobs_append_input="$1"
    _blobs_append_output="$2"
    _blobs_append_args_file="$3"
    _blobs_append_loaded_file="$4"
    _blobs_append_fake_dir="$5"
    _blobs_append_tmp="${_blobs_append_output}.tmp.$$"

    common_require_file "${_blobs_append_input}" "blob resolver input" || return 1
    common_require_file "${_blobs_append_args_file}" "blob argument list" || return 1
    common_require_file "${_blobs_append_loaded_file}" "loaded blob index" || return 1

    [ -d "${_blobs_append_fake_dir}" ] || {
        common_error "blob directory does not exist: ${_blobs_append_fake_dir}"
        return 1
    }

    : > "${_blobs_append_tmp}" || return 1

    while IFS= read -r _blobs_append_line ||
          [ -n "${_blobs_append_line}" ]; do
        if [ -z "${_blobs_append_line}" ]; then
            printf '\n' >> "${_blobs_append_tmp}" || {
                rm -f "${_blobs_append_tmp}"
                return 1
            }
            continue
        fi

        _blobs_append_resolved=$(blobs_resolve_line \
            "${_blobs_append_line}" \
            "${_blobs_append_args_file}" \
            "${_blobs_append_loaded_file}" \
            "${_blobs_append_fake_dir}") || {
                rm -f "${_blobs_append_tmp}"
                return 1
            }

        printf '%s\n' "${_blobs_append_resolved}" \
            >> "${_blobs_append_tmp}" || {
                rm -f "${_blobs_append_tmp}"
                return 1
            }
    done < "${_blobs_append_input}"

    mv -f "${_blobs_append_tmp}" "${_blobs_append_output}" || {
        rm -f "${_blobs_append_tmp}"
        return 1
    }
}
