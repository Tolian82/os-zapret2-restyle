#!/bin/sh

CHILD_PIDFILE="$1"
SERVICE_SCRIPT="$2"
EXPECTED_CHILD="$3"

read_pid()
{
    [ -f "${CHILD_PIDFILE}" ] || return 1
    pid=$(sed -n '1{s/[[:space:]]//g;p;}' "${CHILD_PIDFILE}")
    case "${pid}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    printf '%s\n' "${pid}"
}

child_pid=$(read_pid) || exit 2

process_matches()
{
    [ -n "${EXPECTED_CHILD}" ] || return 1
    kill -0 "${child_pid}" 2>/dev/null || return 1
    child_command=$(/bin/ps -p "${child_pid}" -o command= 2>/dev/null) ||
        return 1
    [ -n "${child_command}" ] || return 1

    case " ${child_command} " in
        *" ${EXPECTED_CHILD} "*) return 0 ;;
    esac

    return 1
}

while process_matches; do
    sleep 2
done

"${SERVICE_SCRIPT}" runtime-failure \
    "dvtws2 exited after the service reached ready state" >/dev/null 2>&1
exit 0
