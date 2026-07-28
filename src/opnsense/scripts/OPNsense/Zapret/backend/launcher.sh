#!/bin/sh

# Launcher public API
#
#   launcher_start_once BIN ARGS_FILE PIDFILE LOG_FILE STABILITY_SECONDS
#   launcher_stop PIDFILE [TIMEOUT]
#   launcher_is_running PIDFILE
#   launcher_status PIDFILE
#
# Launcher starts exactly one dvtws2 instance. It never uses daemon -r and
# never supervises or restarts a process.

launcher_pidfile_read()
{
    _launcher_pidfile="$1"

    [ -f "${_launcher_pidfile}" ] || return 1
    _launcher_pid=$(sed -n '1{s/[[:space:]]//g;p;}' "${_launcher_pidfile}")

    case "${_launcher_pid}" in
        ''|*[!0-9]*) return 1 ;;
    esac

    [ "${_launcher_pid}" -gt 1 ] 2>/dev/null || return 1
    printf '%s\n' "${_launcher_pid}"
}

launcher_is_running()
{
    _launcher_running_pid=$(launcher_pidfile_read "$1") || return 1
    kill -0 "${_launcher_running_pid}" 2>/dev/null
}

launcher_prepare_argv()
{
    _launcher_args_input="$1"
    _launcher_args_output="$2"
    _launcher_args_tmp="${_launcher_args_output}.tmp.$$"

    common_require_file "${_launcher_args_input}" "dvtws2 argument file" || return 1
    [ -s "${_launcher_args_input}" ] || {
        common_error "dvtws2 argument file is empty"
        return 1
    }

    awk '{
        for (i = 1; i <= NF; i++) {
            print $i
        }
    }' "${_launcher_args_input}" > "${_launcher_args_tmp}" || {
        rm -f "${_launcher_args_tmp}"
        return 1
    }

    [ -s "${_launcher_args_tmp}" ] || {
        rm -f "${_launcher_args_tmp}"
        common_error "dvtws2 argument file contains no arguments"
        return 1
    }

    mv -f "${_launcher_args_tmp}" "${_launcher_args_output}"
}

launcher_stop()
{
    _launcher_stop_pidfile="$1"
    _launcher_stop_timeout="${2:-5}"

    _launcher_stop_pid=$(launcher_pidfile_read "${_launcher_stop_pidfile}") || {
        rm -f "${_launcher_stop_pidfile}"
        return 0
    }

    kill "${_launcher_stop_pid}" 2>/dev/null || true

    _launcher_stop_wait=0
    while kill -0 "${_launcher_stop_pid}" 2>/dev/null &&
          [ "${_launcher_stop_wait}" -lt "${_launcher_stop_timeout}" ]; do
        sleep 1
        _launcher_stop_wait=$((_launcher_stop_wait + 1))
    done

    if kill -0 "${_launcher_stop_pid}" 2>/dev/null; then
        kill -KILL "${_launcher_stop_pid}" 2>/dev/null || true
    fi

    rm -f "${_launcher_stop_pidfile}"
}

launcher_start_once()
{
    _launcher_once_bin="$1"
    _launcher_once_args="$2"
    _launcher_once_pidfile="$3"
    _launcher_once_log="$4"
    _launcher_once_stability="${5:-5}"
    _launcher_once_daemon="${LAUNCHER_DAEMON_BIN:-/usr/sbin/daemon}"
    _launcher_once_argv=$(mktemp /tmp/zapret-launcher-argv.XXXXXX) ||
        return 1

    [ -x "${_launcher_once_bin}" ] || {
        rm -f "${_launcher_once_argv}"
        common_error "dvtws2 binary is not executable: ${_launcher_once_bin}"
        return 1
    }

    [ -x "${_launcher_once_daemon}" ] || {
        rm -f "${_launcher_once_argv}"
        common_error "daemon binary is not executable: ${_launcher_once_daemon}"
        return 1
    }

    case "${_launcher_once_stability}" in
        ''|*[!0-9]*)
            rm -f "${_launcher_once_argv}"
            common_error "invalid stability window '${_launcher_once_stability}'"
            return 1
            ;;
    esac

    [ "${_launcher_once_stability}" -ge 1 ] || {
        rm -f "${_launcher_once_argv}"
        common_error "stability window must be at least one second"
        return 1
    }

    launcher_prepare_argv "${_launcher_once_args}" "${_launcher_once_argv}" || {
        rm -f "${_launcher_once_argv}"
        return 1
    }

    mkdir -p "$(dirname "${_launcher_once_log}")" || {
        rm -f "${_launcher_once_argv}"
        return 1
    }
    : > "${_launcher_once_log}" || {
        rm -f "${_launcher_once_argv}"
        return 1
    }

    launcher_stop "${_launcher_once_pidfile}" 1

    set -- "${_launcher_once_bin}"
    while IFS= read -r _launcher_once_argument ||
          [ -n "${_launcher_once_argument}" ]; do
        set -- "$@" "${_launcher_once_argument}"
    done < "${_launcher_once_argv}"
    set -- "$@" "--sockarg=0x200" "--user=nobody"

    "${_launcher_once_daemon}" \
        -p "${_launcher_once_pidfile}" \
        -o "${_launcher_once_log}" \
        -f "$@" || {
            rm -f "${_launcher_once_argv}"
            common_error "failed to launch dvtws2"
            return 1
        }

    rm -f "${_launcher_once_argv}"

    _launcher_once_wait=0
    while [ "${_launcher_once_wait}" -lt 10 ]; do
        launcher_is_running "${_launcher_once_pidfile}" && break
        sleep 1
        _launcher_once_wait=$((_launcher_once_wait + 1))
    done

    launcher_is_running "${_launcher_once_pidfile}" || {
        common_error "dvtws2 did not create a live PID"
        [ ! -s "${_launcher_once_log}" ] || tail -20 "${_launcher_once_log}" >&2
        return 1
    }

    _launcher_once_stable=0
    while [ "${_launcher_once_stable}" -lt "${_launcher_once_stability}" ]; do
        launcher_is_running "${_launcher_once_pidfile}" || {
            common_error "dvtws2 exited during startup stability window"
            [ ! -s "${_launcher_once_log}" ] || tail -20 "${_launcher_once_log}" >&2
            launcher_stop "${_launcher_once_pidfile}" 1
            return 1
        }
        sleep 1
        _launcher_once_stable=$((_launcher_once_stable + 1))
    done
}

launcher_status()
{
    _launcher_status_pidfile="$1"

    if launcher_is_running "${_launcher_status_pidfile}"; then
        _launcher_status_pid=$(launcher_pidfile_read "${_launcher_status_pidfile}")
        echo "zapret is running as pid ${_launcher_status_pid}"
        return 0
    fi

    echo "zapret is not running"
    return 1
}
