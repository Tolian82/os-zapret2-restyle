#!/bin/sh

SCRIPT_DIR="/usr/local/opnsense/scripts/OPNsense/Zapret"
BACKEND_DIR="${SCRIPT_DIR}/backend"

for module in common config parser registry storage targets target_mode exclude \
    blobs ports firewall generator validator atomic stage launcher supervisor orchestrator
do
    module_path="${BACKEND_DIR}/${module}.sh"
    [ -r "${module_path}" ] || {
        echo "ERROR: required backend module is missing: ${module_path}" >&2
        exit 1
    }
    . "${module_path}"
done

ZAPRET_DIR="/usr/local/etc/zapret2"
CONFIG="${ZAPRET_DIR}/zapret.conf"
DVTWS_BIN="${ZAPRET_DIR}/binaries/my/dvtws2"
ACTIVE_DIR="${ZAPRET_DIR}/runtime-v2"
BACKUP_ROOT="${ZAPRET_DIR}/runtime-v2-backups"
CHILD_PIDFILE="/var/run/dvtws2.pid"
SUPERVISOR_DAEMON_PIDFILE="/var/run/zapret2-supervisor-daemon.pid"
SUPERVISOR_MONITOR_PIDFILE="/var/run/zapret2-supervisor-monitor.pid"
SUPERVISOR_LOOP="${SCRIPT_DIR}/supervisor_loop.sh"
STAGE_FILE="/var/run/zapret2-execution.status"
DVTWS_LOG="/var/log/zapret2/dvtws2.log"
SUPERVISOR_LOG="/var/log/zapret2/supervisor.log"
RULE_BASE=19000
RULE_MAX=$((RULE_BASE + 10))

start_service()
{
    orchestrator_native_start \
        "${CONFIG}" "${ZAPRET_DIR}" "${ACTIVE_DIR}" "${BACKUP_ROOT}" \
        "${DVTWS_BIN}" "${CHILD_PIDFILE}" \
        "${SUPERVISOR_DAEMON_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
        "${SUPERVISOR_LOOP}" "$0" \
        "${RULE_BASE}" "${RULE_MAX}" "${STAGE_FILE}" \
        "${DVTWS_LOG}" "${SUPERVISOR_LOG}"
}

stop_service()
{
    orchestrator_native_stop \
        "${CHILD_PIDFILE}" \
        "${SUPERVISOR_DAEMON_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
        "${RULE_BASE}" "${RULE_MAX}" "${STAGE_FILE}"
}

reconfigure_service()
{
    if ! config_reload_template OPNsense/Zapret; then
        orchestrator_fail_stage \
            "${STAGE_FILE}" 1 13 config \
            "template generation failed"
        return 1
    fi
    orchestrator_native_reconfigure \
        "${CONFIG}" "${ZAPRET_DIR}" "${ACTIVE_DIR}" "${BACKUP_ROOT}" \
        "${DVTWS_BIN}" "${CHILD_PIDFILE}" \
        "${SUPERVISOR_DAEMON_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
        "${SUPERVISOR_LOOP}" "$0" \
        "${RULE_BASE}" "${RULE_MAX}" "${STAGE_FILE}" \
        "${DVTWS_LOG}" "${SUPERVISOR_LOG}"
}

case "${1:-}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        reconfigure_service
        ;;
    status)
        orchestrator_native_status \
            "${CHILD_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
            "${RULE_BASE}" "${RULE_MAX}"
        ;;
    reconfigure)
        reconfigure_service
        ;;
    runtime-failure)
        orchestrator_runtime_failure \
            "${CHILD_PIDFILE}" \
            "${SUPERVISOR_DAEMON_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
            "${RULE_BASE}" "${RULE_MAX}" "${STAGE_FILE}" \
            "${2:-dvtws2 runtime failure}"
        ;;
    *)
        echo "usage: zapret_service.sh {start|stop|restart|status|reconfigure}" >&2
        exit 1
        ;;
esac
