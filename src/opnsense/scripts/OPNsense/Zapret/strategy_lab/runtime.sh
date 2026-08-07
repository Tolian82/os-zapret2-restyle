#!/bin/sh

STRATEGY_LAB_DVTWS_BIN="${STRATEGY_LAB_DVTWS_BIN:-/usr/local/etc/zapret2/binaries/my/dvtws2}"
STRATEGY_LAB_DAEMON_BIN="${STRATEGY_LAB_DAEMON_BIN:-/usr/sbin/daemon}"
STRATEGY_LAB_CONFIG_FILE="${STRATEGY_LAB_CONFIG_FILE:-/usr/local/etc/zapret2/zapret.conf}"
STRATEGY_LAB_LUA_DIR="${STRATEGY_LAB_LUA_DIR:-/usr/local/etc/zapret2/lua}"
STRATEGY_LAB_PLUGINCTL_BIN="${STRATEGY_LAB_PLUGINCTL_BIN:-/usr/local/sbin/pluginctl}"
STRATEGY_LAB_IFCONFIG_BIN="${STRATEGY_LAB_IFCONFIG_BIN:-/sbin/ifconfig}"
STRATEGY_LAB_PS_BIN="${STRATEGY_LAB_PS_BIN:-/bin/ps}"
STRATEGY_LAB_SOCKSTAT_BIN="${STRATEGY_LAB_SOCKSTAT_BIN:-/usr/bin/sockstat}"
STRATEGY_LAB_NETSTAT_BIN="${STRATEGY_LAB_NETSTAT_BIN:-/usr/bin/netstat}"
STRATEGY_LAB_RUNTIME_START_TIMEOUT="${STRATEGY_LAB_RUNTIME_START_TIMEOUT:-3}"
STRATEGY_LAB_RUNTIME_STOP_TIMEOUT="${STRATEGY_LAB_RUNTIME_STOP_TIMEOUT:-3}"
STRATEGY_LAB_RUNTIME_KILL_TIMEOUT="${STRATEGY_LAB_RUNTIME_KILL_TIMEOUT:-3}"

strategy_lab_candidate_runtime_dir()
{
    printf '%s/candidate-runtime\n' "$(strategy_lab_job_dir "$1")"
}

strategy_lab_candidate_pid_file()
{
    printf '%s/dvtws2.pid\n' "$(strategy_lab_candidate_runtime_dir "$1")"
}

strategy_lab_candidate_log_file()
{
    printf '%s/dvtws2.log\n' "$(strategy_lab_candidate_runtime_dir "$1")"
}

strategy_lab_candidate_args_file()
{
    printf '%s/dvtws.args\n' "$(strategy_lab_candidate_runtime_dir "$1")"
}

strategy_lab_candidate_hostlist_file()
{
    printf '%s/hostlist.txt\n' "$(strategy_lab_candidate_runtime_dir "$1")"
}

strategy_lab_candidate_addresses_file()
{
    printf '%s/addresses-ipv4.txt\n' "$(strategy_lab_candidate_runtime_dir "$1")"
}

strategy_lab_candidate_result_file()
{
    printf '%s/candidate.json\n' "$(strategy_lab_candidate_runtime_dir "$1")"
}

strategy_lab_candidate_resolve_wan()
{
    if [ -n "${STRATEGY_LAB_WAN_DEVICE:-}" ]; then
        printf '%s\n' "${STRATEGY_LAB_WAN_DEVICE}"
        return 0
    fi

    [ -r "${STRATEGY_LAB_CONFIG_FILE}" ] || return 1
    # shellcheck disable=SC1090
    . "${STRATEGY_LAB_CONFIG_FILE}"
    [ -n "${WAN_IF:-}" ] || return 1

    if [ -x "${STRATEGY_LAB_IFCONFIG_BIN}" ] &&
        "${STRATEGY_LAB_IFCONFIG_BIN}" "${WAN_IF}" >/dev/null 2>&1; then
        printf '%s\n' "${WAN_IF}"
        return 0
    fi

    [ -x "${STRATEGY_LAB_PLUGINCTL_BIN}" ] || return 1
    strategy_lab_require_jq || return 1
    _strategy_lab_wan=$(
        "${STRATEGY_LAB_PLUGINCTL_BIN}" -4 "${WAN_IF}" 2>/dev/null |
            "${STRATEGY_LAB_JQ}" -r --arg logical "${WAN_IF}" '.[$logical][0].device // empty'
    )
    [ -n "${_strategy_lab_wan}" ] || return 1
    printf '%s\n' "${_strategy_lab_wan}"
}

strategy_lab_candidate_prepare_files()
{
    _strategy_lab_job="$1"
    _strategy_lab_endpoints="$2"
    _strategy_lab_strategy_file="$3"
    _strategy_lab_use_hostlist="$4"
    _strategy_lab_runtime=$(strategy_lab_candidate_runtime_dir "${_strategy_lab_job}")
    _strategy_lab_args=$(strategy_lab_candidate_args_file "${_strategy_lab_job}")
    _strategy_lab_hostlist=$(strategy_lab_candidate_hostlist_file "${_strategy_lab_job}")
    _strategy_lab_tmp="${_strategy_lab_args}.tmp.$$"

    [ -r "${_strategy_lab_endpoints}" ] || return 1
    [ -s "${_strategy_lab_endpoints}" ] || return 1
    [ -r "${_strategy_lab_strategy_file}" ] || return 1
    mkdir -p "${_strategy_lab_runtime}" || return 1
    cp "${_strategy_lab_endpoints}" "${_strategy_lab_hostlist}" || return 1
    chmod 0644 "${_strategy_lab_hostlist}"

    : > "${_strategy_lab_tmp}" || return 1
    printf '%s\n' "--port=${STRATEGY_LAB_DIVERT_PORT}" >> "${_strategy_lab_tmp}"
    if [ -d "${STRATEGY_LAB_LUA_DIR}" ]; then
        find "${STRATEGY_LAB_LUA_DIR}" -maxdepth 1 -type f -name '*.lua' -print 2>/dev/null |
            sort | while IFS= read -r _strategy_lab_lua
            do
                printf '%s\n' "--lua-init=@${_strategy_lab_lua}"
            done >> "${_strategy_lab_tmp}"
    fi
    printf '%s\n' '--filter-tcp=443' '--filter-l7=tls' >> "${_strategy_lab_tmp}"
    if [ "${_strategy_lab_use_hostlist}" = 1 ]; then
        printf '%s\n' "--hostlist=${_strategy_lab_hostlist}" >> "${_strategy_lab_tmp}"
    fi
    printf '%s\n' '--out-range=-d10' >> "${_strategy_lab_tmp}"
    cat "${_strategy_lab_strategy_file}" >> "${_strategy_lab_tmp}" || {
        rm -f "${_strategy_lab_tmp}"
        return 1
    }
    mv -f "${_strategy_lab_tmp}" "${_strategy_lab_args}"
    chmod 0644 "${_strategy_lab_args}"
}

strategy_lab_candidate_pid_read()
{
    _strategy_lab_pidfile="$1"
    _strategy_lab_pid=""
    [ -r "${_strategy_lab_pidfile}" ] || return 1
    IFS= read -r _strategy_lab_pid < "${_strategy_lab_pidfile}" || true
    case "${_strategy_lab_pid}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    printf '%s\n' "${_strategy_lab_pid}"
}

strategy_lab_candidate_command()
{
    "${STRATEGY_LAB_PS_BIN}" -p "$1" -o command= 2>/dev/null || true
}

strategy_lab_candidate_pid_identity()
{
    _strategy_lab_pid="$1"
    case "${_strategy_lab_pid}" in ''|*[!0-9]*) return 1 ;; esac
    kill -0 "${_strategy_lab_pid}" 2>/dev/null || return 1
    _strategy_lab_command=$(strategy_lab_candidate_command "${_strategy_lab_pid}")
    case " ${_strategy_lab_command} " in
        *" ${STRATEGY_LAB_DVTWS_BIN} "*) ;;
        *) return 1 ;;
    esac
    case " ${_strategy_lab_command} " in
        *" --port=${STRATEGY_LAB_DIVERT_PORT} "*) return 0 ;;
        *) return 1 ;;
    esac
}

strategy_lab_candidate_process_running()
{
    _strategy_lab_pid=$(strategy_lab_candidate_pid_read "$1" 2>/dev/null || true)
    [ -n "${_strategy_lab_pid}" ] || return 1
    strategy_lab_candidate_pid_identity "${_strategy_lab_pid}"
}

strategy_lab_candidate_process_pids()
{
    "${STRATEGY_LAB_PS_BIN}" ax -o pid= -o command= 2>/dev/null |
        awk -v bin="${STRATEGY_LAB_DVTWS_BIN}" -v port="--port=${STRATEGY_LAB_DIVERT_PORT}" '
            index($0, bin) && index($0, port) { print $1 }
        '
}

strategy_lab_candidate_any_process_running()
{
    _strategy_lab_found=1
    for _strategy_lab_pid in $(strategy_lab_candidate_process_pids)
    do
        if strategy_lab_candidate_pid_identity "${_strategy_lab_pid}"; then
            _strategy_lab_found=0
            break
        fi
    done
    return "${_strategy_lab_found}"
}

strategy_lab_candidate_divert_port_in_use()
{
    if [ -x "${STRATEGY_LAB_SOCKSTAT_BIN}" ]; then
        "${STRATEGY_LAB_SOCKSTAT_BIN}" -4 -l 2>/dev/null |
            awk -v port="${STRATEGY_LAB_DIVERT_PORT}" '
                $0 ~ ("[:.]" port "([[:space:]]|$)") { found=1 }
                END { exit found ? 0 : 1 }
            ' && return 0
    fi
    if [ -x "${STRATEGY_LAB_NETSTAT_BIN}" ]; then
        "${STRATEGY_LAB_NETSTAT_BIN}" -an -f inet 2>/dev/null |
            awk -v port="${STRATEGY_LAB_DIVERT_PORT}" '
                tolower($0) ~ /divert/ && $0 ~ ("[.:]" port "([[:space:]]|$)") { found=1 }
                END { exit found ? 0 : 1 }
            ' && return 0
    fi
    strategy_lab_candidate_any_process_running
}

strategy_lab_candidate_runtime_absent()
{
    ! strategy_lab_candidate_any_process_running &&
        ! strategy_lab_candidate_divert_port_in_use
}

strategy_lab_candidate_job_runtime_absent()
{
    _strategy_lab_job="$1"
    _strategy_lab_pidfile=$(strategy_lab_candidate_pid_file "${_strategy_lab_job}")
    ! strategy_lab_candidate_process_running "${_strategy_lab_pidfile}" &&
        strategy_lab_candidate_runtime_absent
}

strategy_lab_candidate_wait_absent()
{
    _strategy_lab_limit="$1"
    _strategy_lab_wait=0
    while [ "${_strategy_lab_wait}" -lt "${_strategy_lab_limit}" ]
    do
        strategy_lab_candidate_runtime_absent && return 0
        sleep 1
        _strategy_lab_wait=$((_strategy_lab_wait + 1))
    done
    strategy_lab_candidate_runtime_absent
}

strategy_lab_candidate_wait_job_absent()
{
    _strategy_lab_job="$1"
    _strategy_lab_limit="$2"
    _strategy_lab_wait=0
    while [ "${_strategy_lab_wait}" -lt "${_strategy_lab_limit}" ]
    do
        strategy_lab_candidate_job_runtime_absent "${_strategy_lab_job}" && return 0
        sleep 1
        _strategy_lab_wait=$((_strategy_lab_wait + 1))
    done
    strategy_lab_candidate_job_runtime_absent "${_strategy_lab_job}"
}

strategy_lab_candidate_signal_owned_pid()
{
    _strategy_lab_pidfile="$1"
    _strategy_lab_signal="$2"
    _strategy_lab_owned_pid=$(strategy_lab_candidate_pid_read "${_strategy_lab_pidfile}" 2>/dev/null || true)
    [ -n "${_strategy_lab_owned_pid}" ] || return 0
    strategy_lab_candidate_pid_identity "${_strategy_lab_owned_pid}" || return 0
    kill -"${_strategy_lab_signal}" "${_strategy_lab_owned_pid}" 2>/dev/null || true
}

strategy_lab_candidate_signal_all()
{
    _strategy_lab_signal="$1"
    for _strategy_lab_pid in $(strategy_lab_candidate_process_pids)
    do
        strategy_lab_candidate_pid_identity "${_strategy_lab_pid}" || continue
        kill -"${_strategy_lab_signal}" "${_strategy_lab_pid}" 2>/dev/null || true
    done
}

strategy_lab_candidate_stop()
{
    _strategy_lab_job="$1"
    _strategy_lab_pidfile=$(strategy_lab_candidate_pid_file "${_strategy_lab_job}")

    if strategy_lab_candidate_job_runtime_absent "${_strategy_lab_job}"; then
        rm -f "${_strategy_lab_pidfile}"
        return 0
    fi

    # The pidfile is the ownership proof used to accept this candidate at startup.
    # Signal that verified child first. A global ps scan is only a secondary sweep
    # for duplicate/stale candidates and must not be the sole termination path.
    strategy_lab_candidate_signal_owned_pid "${_strategy_lab_pidfile}" TERM
    strategy_lab_candidate_signal_all TERM
    if ! strategy_lab_candidate_wait_job_absent "${_strategy_lab_job}" "${STRATEGY_LAB_RUNTIME_STOP_TIMEOUT}"; then
        strategy_lab_candidate_signal_owned_pid "${_strategy_lab_pidfile}" KILL
        strategy_lab_candidate_signal_all KILL
        strategy_lab_candidate_wait_job_absent "${_strategy_lab_job}" "${STRATEGY_LAB_RUNTIME_KILL_TIMEOUT}" || return 1
    fi

    strategy_lab_candidate_job_runtime_absent "${_strategy_lab_job}" || return 1
    rm -f "${_strategy_lab_pidfile}"
}

strategy_lab_candidate_log_clean()
{
    _strategy_lab_log="$1"
    [ -r "${_strategy_lab_log}" ] || return 1
    ! grep -Eqi '(^|[^a-z])(fatal|panic|syntax error|unknown option|invalid (argument|option)|cannot (bind|open|load)|failed to (bind|load))([^a-z]|$)' \
        "${_strategy_lab_log}"
}

strategy_lab_candidate_ready()
{
    _strategy_lab_job="$1"
    _strategy_lab_pidfile=$(strategy_lab_candidate_pid_file "${_strategy_lab_job}")
    _strategy_lab_log=$(strategy_lab_candidate_log_file "${_strategy_lab_job}")
    strategy_lab_candidate_process_running "${_strategy_lab_pidfile}" || return 1
    strategy_lab_candidate_divert_port_in_use || return 1
    strategy_lab_candidate_log_clean "${_strategy_lab_log}"
}

strategy_lab_candidate_start()
{
    _strategy_lab_job="$1"
    _strategy_lab_args=$(strategy_lab_candidate_args_file "${_strategy_lab_job}")
    _strategy_lab_pidfile=$(strategy_lab_candidate_pid_file "${_strategy_lab_job}")
    _strategy_lab_log=$(strategy_lab_candidate_log_file "${_strategy_lab_job}")

    [ -x "${STRATEGY_LAB_DVTWS_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_DAEMON_BIN}" ] || return 1
    [ -r "${_strategy_lab_args}" ] || return 1
    [ -s "${_strategy_lab_args}" ] || return 1
    strategy_lab_candidate_stop "${_strategy_lab_job}" || return 1
    : > "${_strategy_lab_log}" || return 1

    set -- "${STRATEGY_LAB_DVTWS_BIN}"
    while IFS= read -r _strategy_lab_argument || [ -n "${_strategy_lab_argument}" ]
    do
        [ -n "${_strategy_lab_argument}" ] || continue
        set -- "$@" "${_strategy_lab_argument}"
    done < "${_strategy_lab_args}"
    set -- "$@" '--sockarg=0x200' '--user=nobody'

    "${STRATEGY_LAB_DAEMON_BIN}" -p "${_strategy_lab_pidfile}" -o "${_strategy_lab_log}" -f "$@" 9>&- || return 1
    _strategy_lab_wait=0
    while [ "${_strategy_lab_wait}" -lt "${STRATEGY_LAB_RUNTIME_START_TIMEOUT}" ]
    do
        if strategy_lab_candidate_ready "${_strategy_lab_job}"; then
            sleep 1
            strategy_lab_candidate_ready "${_strategy_lab_job}" && return 0
        fi
        sleep 1
        _strategy_lab_wait=$((_strategy_lab_wait + 1))
    done
    strategy_lab_candidate_stop "${_strategy_lab_job}" || true
    return 1
}
