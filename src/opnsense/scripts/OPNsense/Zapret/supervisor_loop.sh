#!/bin/sh

CHILD_PIDFILE="$1"
SERVICE_SCRIPT="$2"

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

while kill -0 "${child_pid}" 2>/dev/null; do
    sleep 2
done

"${SERVICE_SCRIPT}" runtime-failure \
    "dvtws2 exited after the service reached ready state" >/dev/null 2>&1
exit 0
