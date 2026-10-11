#!/bin/sh
# Private, argument-free FreeBSD Voice process actuator.
# Intentionally NOT in zapret_service.sh dispatch/configd/GUI. Only the
# native locked Python coordinator may call this under the inherited FD9.
# Uses the existing ONE-engine launcher and supervisor, never 'daemon -r'.
set -eu

[ "$#" -eq 1 ] || exit 64
case "$1" in stop|start|start-candidate-engine|start-candidate-supervisor) ;; *) exit 64 ;; esac
[ "$(id -u)" -eq 0 ] || exit 69
# Fail closed when the Python coordinator did not inherit FD9.
: <&9 || exit 69

VOICE_SCRIPT_DIR=/usr/local/opnsense/scripts/OPNsense/Zapret
VOICE_BACKEND_DIR="${VOICE_SCRIPT_DIR}/backend"
for module in common launcher supervisor; do
    [ -r "${VOICE_BACKEND_DIR}/${module}.sh" ] || exit 69
    . "${VOICE_BACKEND_DIR}/${module}.sh"
done

DVTWS_BIN=/usr/local/etc/zapret2/binaries/my/dvtws2
SUPERVISOR_LOOP="${VOICE_SCRIPT_DIR}/supervisor_loop.sh"
CHILD_PIDFILE=/var/run/dvtws2.pid
SUPERVISOR_DAEMON_PIDFILE=/var/run/zapret2-supervisor-daemon.pid
SUPERVISOR_MONITOR_PIDFILE=/var/run/zapret2-supervisor-monitor.pid
ACTIVE_DIR=/usr/local/etc/zapret2/runtime-v2
DVTWS_LOG=/var/log/zapret2/dvtws2.log
SUPERVISOR_LOG=/var/log/zapret2/supervisor.log
VOICE_SERVICE="${VOICE_SCRIPT_DIR}/zapret_service.sh"

case "$1" in
    start-candidate-engine)
        # Native forward phase AFTER the old three-role stop and checked
        # candidate runtime rename, BEFORE IPFW/Config/supervisor switch.
        # All gates are enforced by the FD9+Config-flocked Python caller;
        # here we accept NO user path, argument or arbitrary PID.
        for file in "${CHILD_PIDFILE}" "${SUPERVISOR_DAEMON_PIDFILE}" \
            "${SUPERVISOR_MONITOR_PIDFILE}"; do
            [ ! -e "${file}" ] && [ ! -L "${file}" ] || exit 69
        done
        [ -r "${ACTIVE_DIR}/dvtws.args" ] || exit 69
        launcher_start_once "${DVTWS_BIN}" "${ACTIVE_DIR}/dvtws.args" \
            "${CHILD_PIDFILE}" "${DVTWS_LOG}" 5 || exit 1
        # Intentionally DO NOT start supervisor here. The next stage must
        # first transition the saved IPFW owner to desired native rules.
        ;;
    start-candidate-supervisor)
        # After _74 IPFW PRECOMMIT, NEVER relaunch the candidate engine.
        # Original FD9 + Config lock and kernel witnesses belong to Python.
        [ -e "${CHILD_PIDFILE}" ] && [ ! -L "${CHILD_PIDFILE}" ] || exit 69
        for file in "${SUPERVISOR_DAEMON_PIDFILE}" \
            "${SUPERVISOR_MONITOR_PIDFILE}"; do
            [ ! -e "${file}" ] && [ ! -L "${file}" ] || exit 69
        done
        supervisor_start "${SUPERVISOR_LOOP}" \
            "${SUPERVISOR_DAEMON_PIDFILE}" \
            "${SUPERVISOR_MONITOR_PIDFILE}" \
            "${CHILD_PIDFILE}" "${VOICE_SERVICE}" \
            "${DVTWS_BIN}" "${SUPERVISOR_LOG}" || exit 1
        ;;
    stop)
        # The Python adapter first pins all existing roles with native
        # FreeBSD /bin/ps, pidfiles and FD9/Config locks. No arbitrary PID
        # arguments or service paths can be supplied to this script.
        supervisor_stop "${SUPERVISOR_DAEMON_PIDFILE}" \
            "${SUPERVISOR_MONITOR_PIDFILE}" || exit 1
        launcher_stop "${CHILD_PIDFILE}" 5 || exit 1
        ;;
    start)
        # Called only after the sealed PREVIOUS runtime + Config and
        # previous owned IPFW are independently verified by the coordinator.
        # A stale pidfile must not be silently removed during start.
        for file in "${CHILD_PIDFILE}" "${SUPERVISOR_DAEMON_PIDFILE}" \
            "${SUPERVISOR_MONITOR_PIDFILE}"; do
            [ ! -e "${file}" ] && [ ! -L "${file}" ] || exit 69
        done
        [ -r "${ACTIVE_DIR}/dvtws.args" ] || exit 69
        launcher_start_once "${DVTWS_BIN}" "${ACTIVE_DIR}/dvtws.args" \
            "${CHILD_PIDFILE}" "${DVTWS_LOG}" 5 || exit 1
        supervisor_start "${SUPERVISOR_LOOP}" \
            "${SUPERVISOR_DAEMON_PIDFILE}" \
            "${SUPERVISOR_MONITOR_PIDFILE}" \
            "${CHILD_PIDFILE}" "${VOICE_SERVICE}" \
            "${DVTWS_BIN}" "${SUPERVISOR_LOG}" || exit 1
        ;;
esac
