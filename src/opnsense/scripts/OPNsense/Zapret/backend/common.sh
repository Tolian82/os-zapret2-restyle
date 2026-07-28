#!/bin/sh

common_error()
{
    echo "ERROR: $*" >&2
}

common_cleanup_dir()
{
    _common_dir="$1"
    [ -n "${_common_dir}" ] && [ -d "${_common_dir}" ] && rm -rf "${_common_dir}"
}

common_require_file()
{
    _common_path="$1"
    _common_label="$2"
    if [ ! -f "${_common_path}" ]; then
        common_error "${_common_label} does not exist:"
        echo "       ${_common_path}" >&2
        return 1
    fi
}

# Compatible Milestone 5 extensions.

common_create_workspace()
{
    _common_workspace_prefix="$1"

    case "${_common_workspace_prefix}" in
        ''|*[!A-Za-z0-9_.-]*)
            common_error "invalid workspace prefix '${_common_workspace_prefix}'"
            return 1
            ;;
    esac

    mktemp -d "/tmp/${_common_workspace_prefix}.XXXXXX"
}

common_require_dir()
{
    _common_require_dir_path="$1"
    _common_require_dir_label="$2"

    [ -d "${_common_require_dir_path}" ] || {
        common_error "${_common_require_dir_label} does not exist:"
        echo "       ${_common_require_dir_path}" >&2
        return 1
    }
}

common_prepare_dir()
{
    _common_prepare_dir_path="$1"

    [ -n "${_common_prepare_dir_path}" ] || {
        common_error "common_prepare_dir requires a path"
        return 1
    }

    mkdir -p "${_common_prepare_dir_path}"
}

common_write_text_file()
{
    _common_write_path="$1"
    _common_write_value="$2"
    _common_write_parent=$(dirname "${_common_write_path}")
    _common_write_tmp="${_common_write_path}.tmp.$$"

    mkdir -p "${_common_write_parent}" || return 1
    printf '%s\n' "${_common_write_value}" > "${_common_write_tmp}" || {
        rm -f "${_common_write_tmp}"
        return 1
    }
    mv -f "${_common_write_tmp}" "${_common_write_path}" || {
        rm -f "${_common_write_tmp}"
        return 1
    }
}

# Milestone 5 Commit 4 public runtime helpers.

common_set_directory_mode()
{
    _common_mode_dir="$1"
    _common_mode_value="$2"

    [ -d "${_common_mode_dir}" ] || {
        common_error "directory does not exist: ${_common_mode_dir}"
        return 1
    }

    chmod "${_common_mode_value}" "${_common_mode_dir}" || {
        common_error "cannot set mode ${_common_mode_value} on ${_common_mode_dir}"
        return 1
    }
}

common_set_file_mode()
{
    _common_mode_file="$1"
    _common_mode_value="$2"

    [ -f "${_common_mode_file}" ] || {
        common_error "file does not exist: ${_common_mode_file}"
        return 1
    }

    chmod "${_common_mode_value}" "${_common_mode_file}" || {
        common_error "cannot set mode ${_common_mode_value} on ${_common_mode_file}"
        return 1
    }
}
