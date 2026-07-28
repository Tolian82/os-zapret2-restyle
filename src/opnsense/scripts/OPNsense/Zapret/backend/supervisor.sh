#!/bin/sh

# Supervisor public API
#
#   supervisor_start LOOP SUPERVISOR_PIDFILE MONITOR_PIDFILE CHILD_PIDFILE
#                    SERVICE_SCRIPT LOG_FILE
#   supervisor_stop SUPERVISOR_PIDFILE MONITOR_PIDFILE
#   supervisor_is_running MONITOR_PIDFILE
#
# SUPERVISOR_LOOP must contain the expected absolute supervisor loop path.
#
# Supervisor starts only after Launcher and Firewall have succeeded. It does
# not launch or restart dvtws2. If the ready process disappears, it asks the
# service entry point to perform the common runtime-failure cleanup.

supervisor_pidfile_read()
{
    _supervisor_pidfile="$1"
    [ -f "${_supervisor_pidfile}" ] || return 1

    _supervisor_pid=$(sed -n '1{s/[[:space:]]//g;p;}' "${_supervisor_pidfile}")
    case "${_supervisor_pid}" in
        ''|*[!0-9]*) return 1 ;;
    esac

    [ "${_supervisor_pid}" -gt 1 ] 2>/dev/null || return 1
    printf '%s\n' "${_supervisor_pid}"
}

supervisor_is_running()
{
    _supervisor_running_pid=$(supervisor_pidfile_read "$1") || return 1
    common_process_matches "${_supervisor_running_pid}" "${SUPERVISOR_LOOP:-}"
}

supervisor_stop_one()
{
    _supervisor_stop_file="$1"
    _supervisor_stop_pid=$(supervisor_pidfile_read "${_supervisor_stop_file}") || {
        rm -f "${_supervisor_stop_file}"
        return 0
    }

    if ! common_process_matches "${_supervisor_stop_pid}" "${SUPERVISOR_LOOP:-}"; then
        rm -f "${_supervisor_stop_file}"
        return 0
    fi

    kill "${_supervisor_stop_pid}" 2>/dev/null || true
    sleep 1
    if common_process_matches "${_supervisor_stop_pid}" "${SUPERVISOR_LOOP:-}"; then
        kill -KILL "${_supervisor_stop_pid}" 2>/dev/null || true
    fi
    rm -f "${_supervisor_stop_file}"
}

supervisor_stop()
{
    supervisor_stop_one "$1"
    supervisor_stop_one "$2"
}

supervisor_start()
{
    _supervisor_loop="$1"
    _supervisor_daemon_pidfile="$2"
    _supervisor_monitor_pidfile="$3"
    _supervisor_child_pidfile="$4"
    _supervisor_service_script="$5"
    _supervisor_log="$6"
    _supervisor_daemon="${SUPERVISOR_DAEMON_BIN:-/usr/sbin/daemon}"

    [ -x "${_supervisor_loop}" ] || {
        common_error "supervisor loop is not executable: ${_supervisor_loop}"
        return 1
    }
    [ -x "${_supervisor_service_script}" ] || {
        common_error "service entry point is not executable"
        return 1
    }
    [ -x "${_supervisor_daemon}" ] || {
        common_error "daemon binary is not executable"
        return 1
    }

    supervisor_stop \
        "${_supervisor_daemon_pidfile}" \
        "${_supervisor_monitor_pidfile}"

    mkdir -p "$(dirname "${_supervisor_log}")" || return 1

    "${_supervisor_daemon}" \
        -P "${_supervisor_daemon_pidfile}" \
        -p "${_supervisor_monitor_pidfile}" \
        -o "${_supervisor_log}" \
        -f "${_supervisor_loop}" \
        "${_supervisor_child_pidfile}" \
        "${_supervisor_service_script}" || {
            common_error "failed to start runtime supervisor"
            return 1
        }

    _supervisor_wait=0
    while [ "${_supervisor_wait}" -lt 5 ]; do
        supervisor_is_running "${_supervisor_monitor_pidfile}" && return 0
        sleep 1
        _supervisor_wait=$((_supervisor_wait + 1))
    done

    common_error "runtime supervisor did not become active"
    return 1
}
