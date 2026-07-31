#!/bin/sh

SCRIPT_DIR="/usr/local/opnsense/scripts/OPNsense/Zapret"
BACKEND_DIR="${SCRIPT_DIR}/backend"

for module in common config parser registry storage targets target_mode \
    profile_normalizer profile_pipeline exclude blobs ports firewall generator validator atomic \
    stage launcher supervisor orchestrator
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
LIFECYCLE_LOCK_FILE="/var/run/zapret2-lifecycle.lock"
LIFECYCLE_LOCK_TIMEOUT=30
LOCKF_BIN="/usr/bin/lockf"

ensure_runtime_components()
{
    [ -x "${DVTWS_BIN}" ] && return 0

    echo "ERROR: zapret2 runtime is not installed or installation is incomplete" >&2
    echo "ERROR: reinstall the plugin and inspect /var/log/zapret2/setup.log" >&2
    return 1
}

refresh_generated_configuration()
{
    if ! config_reload_template OPNsense/Zapret; then
        orchestrator_fail_stage \
            "${STAGE_FILE}" 1 13 config \
            "template generation failed"
        return 1
    fi
}

start_service()
{
    ensure_runtime_components || return 1
    refresh_generated_configuration || return 1
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
    ensure_runtime_components || return 1
    refresh_generated_configuration || return 1
    orchestrator_native_reconfigure \
        "${CONFIG}" "${ZAPRET_DIR}" "${ACTIVE_DIR}" "${BACKUP_ROOT}" \
        "${DVTWS_BIN}" "${CHILD_PIDFILE}" \
        "${SUPERVISOR_DAEMON_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
        "${SUPERVISOR_LOOP}" "$0" \
        "${RULE_BASE}" "${RULE_MAX}" "${STAGE_FILE}" \
        "${DVTWS_LOG}" "${SUPERVISOR_LOG}"
}

service_dispatch()
{
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
            return 64
            ;;
    esac
}

service_with_lifecycle_lock()
{
    _service_lock_timeout="$1"
    shift

    [ -x "${LOCKF_BIN}" ] || {
        echo "ERROR: required lock utility is missing: ${LOCKF_BIN}" >&2
        return 1
    }

    (
        if ! "${LOCKF_BIN}" -s -t "${_service_lock_timeout}" 9; then
            return 75
        fi
        service_dispatch "$@"
    ) 9>"${LIFECYCLE_LOCK_FILE}"
}

case "${1:-}" in
    status)
        service_dispatch "$@"
        ;;
    runtime-failure)
        # A callback from the previous supervisor can arrive while stop or
        # reconfigure already owns the runtime. Do not queue stale cleanup
        # behind that operation and risk tearing down the replacement runtime.
        service_with_lifecycle_lock 0 "$@"
        _service_status=$?
        [ "${_service_status}" -ne 75 ] || exit 0
        exit "${_service_status}"
        ;;
    start|stop|restart|reconfigure)
        service_with_lifecycle_lock "${LIFECYCLE_LOCK_TIMEOUT}" "$@"
        _service_status=$?
        if [ "${_service_status}" -eq 75 ]; then
            echo "ERROR: another zapret lifecycle operation is already running" >&2
        fi
        exit "${_service_status}"
        ;;
    *)
        service_dispatch "$@"
        ;;
esac
