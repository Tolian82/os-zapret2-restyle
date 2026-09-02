#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
BACKEND_DIR="${BACKEND_DIR:-${SCRIPT_DIR}/backend}"

for module in common config parser registry storage targets telegram_voice target_mode \
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
LIFECYCLE_LOCK_FILE="${LIFECYCLE_LOCK_FILE:-/var/run/zapret2-lifecycle.lock}"
LIFECYCLE_LOCK_TIMEOUT=30
STRATEGY_LAB_LOCK_TIMEOUT=3
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
STRATEGY_LAB_WORKER="${STRATEGY_LAB_WORKER:-${SCRIPT_DIR}/strategy_lab_worker.sh}"
STRATEGY_LAB_CIRCULAR_WORKER="${STRATEGY_LAB_CIRCULAR_WORKER:-${SCRIPT_DIR}/strategy_lab_circular_worker.sh}"
STRATEGY_LAB_RECOVERY_WORKER="${STRATEGY_LAB_RECOVERY_WORKER:-${SCRIPT_DIR}/strategy_lab_recovery_worker.sh}"
STRATEGY_LAB_SEMANTIC_IPFW_BIN="${STRATEGY_LAB_SEMANTIC_IPFW_BIN:-${IPFW_BIN}}"
STRATEGY_LAB_SEMANTIC_PS_BIN="${STRATEGY_LAB_SEMANTIC_PS_BIN:-${ZAPRET_PROCESS_QUERY_BIN}}"
STRATEGY_LAB_SEMANTIC_SHA256_BIN="${STRATEGY_LAB_SEMANTIC_SHA256_BIN:-/sbin/sha256}"

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

prepare_firewall_prerequisites()
{
    if ! firewall_prepare; then
        echo "ERROR: firewall prerequisites could not be prepared before dvtws2 launch" >&2
        return 1
    fi
}

start_service()
{
    ensure_runtime_components || return 1
    refresh_generated_configuration || return 1
    prepare_firewall_prerequisites || return 1
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
    prepare_firewall_prerequisites || return 1
    orchestrator_native_reconfigure \
        "${CONFIG}" "${ZAPRET_DIR}" "${ACTIVE_DIR}" "${BACKUP_ROOT}" \
        "${DVTWS_BIN}" "${CHILD_PIDFILE}" \
        "${SUPERVISOR_DAEMON_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
        "${SUPERVISOR_LOOP}" "$0" \
        "${RULE_BASE}" "${RULE_MAX}" "${STAGE_FILE}" \
        "${DVTWS_LOG}" "${SUPERVISOR_LOG}"
}

telegram_voice_service_state()
{
    orchestrator_native_status \
        "${CHILD_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
        "${RULE_BASE}" "${RULE_MAX}" "${ACTIVE_DIR}" \
        >/dev/null 2>&1
    _telegram_voice_service_status=$?

    case "${_telegram_voice_service_status}" in
        0) printf '%s\n' running ;;
        1) printf '%s\n' stopped ;;
        *) printf '%s\n' incomplete ;;
    esac
}

telegram_voice_effective()
{
    [ "$(telegram_voice_service_state)" = running ] || return 1
    telegram_voice_state_is_enabled \
        "${ACTIVE_DIR}/${TELEGRAM_VOICE_STATE_FILE_NAME}" || return 1
    firewall_telegram_voice_runtime_complete \
        "${ACTIVE_DIR}/${TELEGRAM_VOICE_STATE_FILE_NAME}" \
        "${RULE_BASE}"
}

telegram_voice_status_service()
{
    if telegram_voice_marker_is_enabled "${TELEGRAM_VOICE_MARKER_FILE}"; then
        _telegram_voice_status_requested=on
    else
        _telegram_voice_status_requested=off
    fi
    if telegram_voice_state_is_enabled \
        "${ACTIVE_DIR}/${TELEGRAM_VOICE_STATE_FILE_NAME}"; then
        _telegram_voice_status_profile=on
    else
        _telegram_voice_status_profile=off
    fi
    _telegram_voice_status_service=$(telegram_voice_service_state)
    _telegram_voice_status_entries=$(firewall_telegram_voice_table_count)
    if firewall_table_exists "${TELEGRAM_VOICE_TABLE}"; then
        _telegram_voice_status_table_present=yes
    else
        _telegram_voice_status_table_present=no
    fi
    if firewall_table_exists "${TELEGRAM_VOICE_STAGE_TABLE}"; then
        _telegram_voice_status_stage_table_present=yes
    else
        _telegram_voice_status_stage_table_present=no
    fi
    _telegram_voice_status_rule=$(firewall_telegram_voice_rule_number \
        "${RULE_BASE}") || return 1
    _telegram_voice_status_packets=unavailable
    _telegram_voice_status_bytes=unavailable
    _telegram_voice_status_counters=$(firewall_telegram_voice_rule_counters \
        "${RULE_BASE}" 2>/dev/null || true)
    if [ -n "${_telegram_voice_status_counters}" ]; then
        _telegram_voice_status_packets=$(printf '%s\n' \
            "${_telegram_voice_status_counters}" | awk '{print $1}')
        _telegram_voice_status_bytes=$(printf '%s\n' \
            "${_telegram_voice_status_counters}" | awk '{print $2}')
    fi
    if telegram_voice_effective; then
        _telegram_voice_status_effective=on
    else
        _telegram_voice_status_effective=off
    fi

    printf '%s\n' \
        "telegram_voice_poc.requested=${_telegram_voice_status_requested}" \
        "telegram_voice_poc.effective=${_telegram_voice_status_effective}" \
        "telegram_voice_poc.service=${_telegram_voice_status_service}" \
        "telegram_voice_poc.active_profile=${_telegram_voice_status_profile}" \
        'telegram_voice_poc.strategy=stun-ipfrag-pos-8-ordered' \
        'telegram_voice_poc.scope=telegram-ipv4-all-udp-ports' \
        "telegram_voice_poc.table=${TELEGRAM_VOICE_TABLE}" \
        "telegram_voice_poc.table_present=${_telegram_voice_status_table_present}" \
        "telegram_voice_poc.table_entries=${_telegram_voice_status_entries}" \
        "telegram_voice_poc.stage_table=${TELEGRAM_VOICE_STAGE_TABLE}" \
        "telegram_voice_poc.stage_table_present=${_telegram_voice_status_stage_table_present}" \
        "telegram_voice_poc.rule=${_telegram_voice_status_rule}" \
        "telegram_voice_poc.rule_packets=${_telegram_voice_status_packets}" \
        "telegram_voice_poc.rule_bytes=${_telegram_voice_status_bytes}"

    if [ "${_telegram_voice_status_requested}" = on ]; then
        [ "${_telegram_voice_status_effective}" = on ] &&
        [ "${_telegram_voice_status_service}" = running ] || return 2
        return 0
    fi

    [ "${_telegram_voice_status_effective}" = off ] &&
    [ "${_telegram_voice_status_service}" != incomplete ] &&
    [ "${_telegram_voice_status_table_present}" = no ] &&
    [ "${_telegram_voice_status_stage_table_present}" = no ] &&
    ! firewall_telegram_voice_rule_present "${RULE_BASE}"
}

telegram_voice_enable_service()
{
    [ "$(telegram_voice_service_state)" = running ] || {
        echo "ERROR: Telegram Voice PoC requires a complete running zapret service" >&2
        return 1
    }

    if telegram_voice_marker_is_enabled "${TELEGRAM_VOICE_MARKER_FILE}" &&
       telegram_voice_effective; then
        telegram_voice_status_service
        return $?
    fi

    telegram_voice_marker_enable "${TELEGRAM_VOICE_MARKER_FILE}" || {
        echo "ERROR: cannot enable the Telegram Voice PoC request marker" >&2
        return 1
    }

    if reconfigure_service && telegram_voice_effective; then
        telegram_voice_status_service
        return $?
    fi

    telegram_voice_marker_disable "${TELEGRAM_VOICE_MARKER_FILE}" || true
    echo "ERROR: Telegram Voice PoC activation failed; previous runtime was kept" >&2
    return 1
}

telegram_voice_disable_service()
{
    _telegram_voice_disable_restore_marker=0
    if telegram_voice_marker_is_enabled "${TELEGRAM_VOICE_MARKER_FILE}" ||
       telegram_voice_effective; then
        _telegram_voice_disable_restore_marker=1
    else
        telegram_voice_status_service
        return $?
    fi

    telegram_voice_marker_disable "${TELEGRAM_VOICE_MARKER_FILE}" || {
        echo "ERROR: cannot disable the Telegram Voice PoC request marker" >&2
        return 1
    }

    if [ "$(telegram_voice_service_state)" = stopped ]; then
        firewall_remove_telegram_voice_tables
        telegram_voice_status_service
        return $?
    fi

    if reconfigure_service && ! telegram_voice_effective; then
        telegram_voice_status_service
        return $?
    fi

    if [ "${_telegram_voice_disable_restore_marker}" = 1 ]; then
        telegram_voice_marker_enable "${TELEGRAM_VOICE_MARKER_FILE}" || true
    fi
    echo "ERROR: Telegram Voice PoC rollback failed; request marker was restored" >&2
    return 1
}

strategy_lab_job_id_valid()
{
    printf '%s\n' "$1" | grep -Eq '^job\.[A-Za-z0-9]+$'
}

strategy_lab_lock_owner_valid()
{
    [ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] || return 1
    ( : >&9 ) 2>/dev/null
}

strategy_lab_semantic_pid_matches()
{
    _strategy_lab_semantic_pidfile="$1"
    _strategy_lab_semantic_expected="$2"
    _strategy_lab_semantic_pid=$(common_pidfile_read \
        "${_strategy_lab_semantic_pidfile}") || return 1
    kill -0 "${_strategy_lab_semantic_pid}" 2>/dev/null || return 1
    [ -x "${STRATEGY_LAB_SEMANTIC_PS_BIN}" ] || return 1
    _strategy_lab_semantic_command=$("${STRATEGY_LAB_SEMANTIC_PS_BIN}" \
        -p "${_strategy_lab_semantic_pid}" -o command= 2>/dev/null || true)
    printf '%s\n' "${_strategy_lab_semantic_command}" | grep -Fq "${_strategy_lab_semantic_expected}"
}

strategy_lab_semantic_hash_file()
{
    _strategy_lab_semantic_file="$1"
    [ -r "${_strategy_lab_semantic_file}" ] || {
        printf '%s\n' missing
        return 0
    }
    if [ -x "${STRATEGY_LAB_SEMANTIC_SHA256_BIN}" ]; then
        "${STRATEGY_LAB_SEMANTIC_SHA256_BIN}" -q "${_strategy_lab_semantic_file}"
        return $?
    fi
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${_strategy_lab_semantic_file}" | awk '{print $1}'
        return $?
    fi
    return 1
}

strategy_lab_semantic_firewall_hash()
{
    [ -x "${STRATEGY_LAB_SEMANTIC_IPFW_BIN}" ] || return 1
    _strategy_lab_semantic_rules=$(mktemp "${TMPDIR:-/tmp}/zapret-rules.XXXXXX") || return 1
    : > "${_strategy_lab_semantic_rules}"
    _strategy_lab_semantic_rule="${RULE_BASE}"
    while [ "${_strategy_lab_semantic_rule}" -le "${RULE_MAX}" ]
    do
        "${STRATEGY_LAB_SEMANTIC_IPFW_BIN}" list "${_strategy_lab_semantic_rule}" 2>/dev/null |
            grep '^[0-9]' >> "${_strategy_lab_semantic_rules}" || true
        _strategy_lab_semantic_rule=$((_strategy_lab_semantic_rule + 1))
    done
    if "${STRATEGY_LAB_SEMANTIC_IPFW_BIN}" table \
        "${TELEGRAM_VOICE_TABLE}" info >/dev/null 2>&1; then
        printf 'table %s\n' "${TELEGRAM_VOICE_TABLE}" \
            >> "${_strategy_lab_semantic_rules}"
        "${STRATEGY_LAB_SEMANTIC_IPFW_BIN}" table \
            "${TELEGRAM_VOICE_TABLE}" list 2>/dev/null |
            LC_ALL=C sort >> "${_strategy_lab_semantic_rules}" || {
                rm -f "${_strategy_lab_semantic_rules}"
                return 1
            }
    fi
    if [ ! -s "${_strategy_lab_semantic_rules}" ]; then
        rm -f "${_strategy_lab_semantic_rules}"
        printf '%s\n' empty
        return 0
    fi
    _strategy_lab_semantic_hash=$(strategy_lab_semantic_hash_file \
        "${_strategy_lab_semantic_rules}") || {
            rm -f "${_strategy_lab_semantic_rules}"
            return 1
        }
    rm -f "${_strategy_lab_semantic_rules}"
    printf '%s\n' "${_strategy_lab_semantic_hash}"
}

strategy_lab_semantic_service_state()
{
    if service_dispatch status >/dev/null 2>&1; then
        printf '%s\n' RUNNING
        return 0
    else
        _strategy_lab_semantic_status=$?
    fi
    case "${_strategy_lab_semantic_status}" in
        1) printf '%s\n' STOPPED ;;
        *) printf '%s\n' INCOMPLETE ;;
    esac
}

strategy_lab_semantic_evidence()
{
    _strategy_lab_semantic_state=$(strategy_lab_semantic_service_state) || return 1
    if strategy_lab_semantic_pid_matches "${CHILD_PIDFILE}" "${DVTWS_BIN}"; then
        _strategy_lab_semantic_child=true
    else
        _strategy_lab_semantic_child=false
    fi
    if strategy_lab_semantic_pid_matches "${SUPERVISOR_MONITOR_PIDFILE}" "${SUPERVISOR_LOOP}"; then
        _strategy_lab_semantic_supervisor=true
    else
        _strategy_lab_semantic_supervisor=false
    fi
    _strategy_lab_semantic_args_hash=$(strategy_lab_semantic_hash_file \
        "${ACTIVE_DIR}/dvtws.args") || return 1
    _strategy_lab_semantic_config_hash=$(strategy_lab_semantic_hash_file \
        "${CONFIG}") || return 1
    _strategy_lab_semantic_firewall_hash=$(strategy_lab_semantic_firewall_hash) || return 1

    printf '{"schema":1,"source":"zapret_service","state":"%s",' \
        "${_strategy_lab_semantic_state}"
    printf '"child_running":%s,"supervisor_running":%s,' \
        "${_strategy_lab_semantic_child}" "${_strategy_lab_semantic_supervisor}"
    printf '"runtime_args_hash":"%s","effective_config_hash":"%s",' \
        "${_strategy_lab_semantic_args_hash}" "${_strategy_lab_semantic_config_hash}"
    printf '"normal_firewall_hash":"%s"}\n' \
        "${_strategy_lab_semantic_firewall_hash}"
}

strategy_lab_internal_dispatch()
{
    strategy_lab_lock_owner_valid || {
        echo "ERROR: Strategy Lab internal lifecycle action has no lock owner" >&2
        return 77
    }

    case "${1:-}" in
        strategy-lab-status)
            service_dispatch status
            ;;
        strategy-lab-evidence)
            strategy_lab_semantic_evidence
            ;;
        strategy-lab-stop)
            stop_service
            ;;
        strategy-lab-start)
            start_service
            ;;
        *)
            return 64
            ;;
    esac
}

run_strategy_lab_worker()
{
    _strategy_lab_worker="$1"
    _strategy_lab_job_id="$2"
    strategy_lab_job_id_valid "${_strategy_lab_job_id}" || {
        echo "ERROR: invalid Strategy Lab job id" >&2
        return 64
    }
    [ -x "${_strategy_lab_worker}" ] || {
        echo "ERROR: Strategy Lab worker is unavailable: ${_strategy_lab_worker}" >&2
        return 1
    }

    STRATEGY_LAB_LIFECYCLE_OWNER=1
    STRATEGY_LAB_SERVICE_SCRIPT="$0"
    export STRATEGY_LAB_LIFECYCLE_OWNER STRATEGY_LAB_SERVICE_SCRIPT
    exec "${_strategy_lab_worker}" "${_strategy_lab_job_id}"
}

strategy_lab_report_lock_failure()
{
    _strategy_lab_action="$1"
    _strategy_lab_job_id="$2"
    case "${_strategy_lab_action}" in
        strategy-lab)
            _strategy_lab_failure_worker="${STRATEGY_LAB_WORKER}"
            ;;
        strategy-lab-circular)
            _strategy_lab_failure_worker="${STRATEGY_LAB_CIRCULAR_WORKER}"
            ;;
        *)
            return 0
            ;;
    esac
    if [ -x "${_strategy_lab_failure_worker}" ] &&
        strategy_lab_job_id_valid "${_strategy_lab_job_id}"; then
        STRATEGY_LAB_LIFECYCLE_LOCK_FAILED=1 \
        STRATEGY_LAB_SERVICE_SCRIPT="$0" \
            "${_strategy_lab_failure_worker}" "${_strategy_lab_job_id}" || true
    fi
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
                "${RULE_BASE}" "${RULE_MAX}" "${ACTIVE_DIR}"
            ;;
        telegram-voice-enable)
            telegram_voice_enable_service
            ;;
        telegram-voice-disable)
            telegram_voice_disable_service
            ;;
        telegram-voice-status)
            telegram_voice_status_service
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
        strategy-lab)
            run_strategy_lab_worker "${STRATEGY_LAB_WORKER}" "${2:-}"
            ;;
        strategy-lab-circular)
            run_strategy_lab_worker "${STRATEGY_LAB_CIRCULAR_WORKER}" "${2:-}"
            ;;
        strategy-lab-recover)
            run_strategy_lab_worker "${STRATEGY_LAB_RECOVERY_WORKER}" "${2:-}"
            ;;
        *)
            echo "usage: zapret_service.sh {start|stop|restart|status|reconfigure|telegram-voice-enable|telegram-voice-disable|telegram-voice-status}" >&2
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
    status|telegram-voice-status)
        service_dispatch "$@"
        ;;
    strategy-lab-status|strategy-lab-evidence|strategy-lab-stop|strategy-lab-start)
        strategy_lab_internal_dispatch "$@"
        ;;
    strategy-lab|strategy-lab-circular|strategy-lab-recover)
        service_with_lifecycle_lock "${STRATEGY_LAB_LOCK_TIMEOUT}" "$@"
        _service_status=$?
        if [ "${_service_status}" -eq 75 ]; then
            echo "ERROR: Strategy Lab could not acquire the zapret lifecycle lock" >&2
            strategy_lab_report_lock_failure "${1}" "${2:-}"
        fi
        exit "${_service_status}"
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
    start|stop|restart|reconfigure|telegram-voice-enable|telegram-voice-disable)
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
