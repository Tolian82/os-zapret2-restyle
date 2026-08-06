#!/bin/sh

ZAPRET_PROCESS_QUERY_BIN="${ZAPRET_PROCESS_QUERY_BIN:-${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}/process_query.sh}"
COMMON_PS_BIN="${COMMON_PS_BIN:-${ZAPRET_PROCESS_QUERY_BIN}}"
STRATEGY_LAB_SEMANTIC_PS_BIN="${STRATEGY_LAB_SEMANTIC_PS_BIN:-${ZAPRET_PROCESS_QUERY_BIN}}"
STRATEGY_LAB_PS_BIN="${STRATEGY_LAB_PS_BIN:-${ZAPRET_PROCESS_QUERY_BIN}}"
export ZAPRET_PROCESS_QUERY_BIN COMMON_PS_BIN STRATEGY_LAB_SEMANTIC_PS_BIN STRATEGY_LAB_PS_BIN

common_error()
{
    echo "ERROR: $*" >&2
}

common_cleanup_dir()
{
    _common_dir="$1"
    [ -n "${_common_dir}" ] && [ -d "${_common_dir}" ] && rm -rf "${_common_dir}"
}

common_pidfile_read()
{
    _common_pidfile="$1"
    [ -r "${_common_pidfile}" ] || return 1

    _common_pid=$(sed -n '1{s/[[:space:]]//g;p;}' "${_common_pidfile}")
    case "${_common_pid}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "${_common_pid}" -gt 1 ] 2>/dev/null || return 1

    printf '%s\n' "${_common_pid}"
}

common_process_matches()
{
    _common_process_pid="$1"
    _common_process_expected="$2"
    _common_process_ps="${COMMON_PS_BIN:-/bin/ps}"

    case "${_common_process_pid}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "${_common_process_pid}" -gt 1 ] 2>/dev/null || return 1
    [ -n "${_common_process_expected}" ] || return 1
    [ -x "${_common_process_ps}" ] || return 1
    kill -0 "${_common_process_pid}" 2>/dev/null || return 1

    _common_process_command=$(
        "${_common_process_ps}" -p "${_common_process_pid}" -o command= 2>/dev/null
    ) || return 1
    [ -n "${_common_process_command}" ] || return 1

    case " ${_common_process_command} " in
        *" ${_common_process_expected} "*) return 0 ;;
    esac

    return 1
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
