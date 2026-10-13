#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
BACKEND_DIR="${BACKEND_DIR:-${SCRIPT_DIR}/backend}"

for module in common config parser registry storage targets telegram_voice target_mode \
    profile_normalizer profile_pipeline exclude blobs ports firewall generator validator atomic \
    stage launcher supervisor orchestrator apply_runtime
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

# Run the staged-only Voice ON refusal immediately after rendering the
# generated config and before firewall_prepare can load or change IPFW.
# Overall Zapret OFF is an exception: reconfigure must still be allowed to
# stop the existing service, even if a Voice checkbox was saved as ON.
preflight_native_voice_before_firewall()
{
    config_load "${CONFIG}" || return 1
    if [ "${ZAPRET_ENABLED:-0}" = 1 ]; then
        config_voice_staged_only_guard || {
            echo "ERROR: Voice ON requires native transactional runtime; firewall unchanged" >&2
            return 1
        }
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
    preflight_native_voice_before_firewall || return 1
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
    preflight_native_voice_before_firewall || return 1
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
        'telegram_voice_poc.strategy=stun-zero-fake-repeats-2' \
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

    # Strategy Lab already owns inherited lockf fd 9 and calls these
    # privileged internal actions directly. Do not let its stop/start
    # bypass the pending whole-runtime/IPFW journal guard simply because
    # no new service_with_lifecycle_lock invocation occurs.
    case "${1:-}" in
        strategy-lab-status)
            service_dispatch status
            ;;
        strategy-lab-evidence)
            strategy_lab_semantic_evidence
            ;;
        strategy-lab-stop)
            preflight_voice_cutover_journals || return 69
            stop_service
            ;;
        strategy-lab-start)
            preflight_voice_cutover_journals || return 69
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

# Native FreeBSD Voice IPFW owner is a production executable, not an
# independent daemon. The dispatcher invokes it ONLY beneath FD9 lockf.
# No GUI action is allowed to use this partial cutover path.
native_voice_ipfw_dispatch()
{
    _native_voice_ipfw_action="$1"
    _native_voice_ipfw_python="/usr/local/bin/python3.13"
    _native_voice_ipfw_script="${BACKEND_DIR}/voice_ipfw_runtime.py"

    [ -x "${_native_voice_ipfw_python}" ] &&
    [ -r "${_native_voice_ipfw_script}" ] || {
        echo "ERROR: native Voice IPFW runtime is not installed" >&2
        return 1
    }
    "${_native_voice_ipfw_python}" "${_native_voice_ipfw_script}" \
        "${_native_voice_ipfw_action}"
}

# Create a real, fsync'd previous Config/runtime checkpoint BEFORE any
# native Voice transaction takes ownership of IPFW. This action is private
# to the service lifecycle FD9, never available through Voice GUI Apply.
native_voice_checkpoint_service()
{
    orchestrator_runtime_is_complete \
        "${CHILD_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
        "${RULE_BASE}" "${RULE_MAX}" "${ACTIVE_DIR}" || {
            echo "ERROR: cannot checkpoint an incomplete previous Zapret runtime" >&2
            return 1
        }

    _native_voice_checkpoint_python="/usr/local/bin/python3.13"
    _native_voice_checkpoint_script="${BACKEND_DIR}/voice_cutover_checkpoint.py"
    [ -x "${_native_voice_checkpoint_python}" ] &&
    [ -r "${_native_voice_checkpoint_script}" ] || {
        echo "ERROR: native Voice checkpoint command is not installed" >&2
        return 1
    }
    "${_native_voice_checkpoint_python}" "${_native_voice_checkpoint_script}" prepare
}

# Prepare exact sealed previous Config/runtime bytes for a verified Voice
# rollback. Does NOT install them, restart dvtws2 or mutate firewall.
# The Python entrypoint requires an already-MUTATING whole journal and
# validates the original IPFW ownership under the existing lockf FD9.
native_voice_restore_stage_service()
{
    _native_voice_restore_python="/usr/local/bin/python3.13"
    _native_voice_restore_script="${BACKEND_DIR}/voice_cutover_restore_prepare.py"
    [ -x "${_native_voice_restore_python}" ] &&
    [ -r "${_native_voice_restore_script}" ] || {
        echo "ERROR: native Voice restore preparation is not installed" >&2
        return 1
    }
    "${_native_voice_restore_python}" "${_native_voice_restore_script}" prepare
}

# Read-only native evidence for a future complete Voice rollback. It is
# accessible only under the existing lockf FD9; unlike file restore it never
# stops processes, alters IPFW or writes the Config/runtime tree.
native_voice_quiescence_service()
{
    _native_voice_check_python="/usr/local/bin/python3.13"
    _native_voice_check_script="${BACKEND_DIR}/voice_native_recovery_quiescence.py"
    [ -x "${_native_voice_check_python}" ] &&
    [ -r "${_native_voice_check_script}" ] || {
        echo "ERROR: native Voice recovery inspector is not installed" >&2
        return 1
    }
    "${_native_voice_check_python}" "${_native_voice_check_script}" inspect
}


# Manual-only emergency restoration of a MUTATING schema-4 Voice cutover.
# The existing lockf FD9 remains owned throughout IPFW, real Config/runtime
# writes and one-engine/supervisor stop/restart. Never GUI/configd or boot.
native_voice_five_restore_service()
{
    _native_voice_five_python="/usr/local/bin/python3.13"
    _native_voice_five_script="${BACKEND_DIR}/voice_native_five_resource_recovery.py"
    [ -x "${_native_voice_five_python}" ] &&
    [ -r "${_native_voice_five_script}" ] || {
        echo "ERROR: native Voice five-resource recovery is not installed" >&2
        return 1
    }
    "${_native_voice_five_python}" "${_native_voice_five_script}" rollback
}

# Native read-only cold-boot/crash recovery triage.
# Called through the existing FD9 lifecycle lock. This does NOT resume a
# stopped process, restore IPFW or close the whole Voice journal.
native_voice_boot_review_service()
{
    _native_voice_boot_python="/usr/local/bin/python3.13"
    _native_voice_boot_script="${BACKEND_DIR}/voice_native_boot_recovery_review.py"
    [ -x "${_native_voice_boot_python}" ] &&
    [ -r "${_native_voice_boot_script}" ] || {
        echo "ERROR: native Voice boot review is not installed" >&2
        return 1
    }
    "${_native_voice_boot_python}" "${_native_voice_boot_script}" inspect
}

# Operator-only read-only old PoC rollback *disk* boot review under the same FD9.
# Pending Voice journals remain blocked for every lifecycle mutation.
native_voice_legacy_boot_review_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_script="${BACKEND_DIR}/voice_native_legacy_boot_review.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_script}" ] || {
        echo "ERROR: old Voice rollback boot inspector unavailable" >&2
        return 69
    }
    "${_voice_python}" "${_voice_script}" inspect
}

# Manual-only live IPFW/three-role evidence after a sealed old rollback.
# Deliberately no boot hook, configd, Apply, or process startup.
native_voice_legacy_boot_live_review_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_script="${BACKEND_DIR}/voice_native_legacy_boot_review.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_script}" ] || return 69
    "${_voice_python}" "${_voice_script}" inspect-live
}

# Operator-only previous Telegram PoC Config/runtime/marker/IPFW evidence,
# plus an immutable reverse plan; old processes and kernel remain untouched.
native_voice_legacy_capture_plan_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_script="${BACKEND_DIR}/voice_native_legacy_predecessor_route.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_script}" ] || return 69
    "${_voice_python}" "${_voice_script}" capture-plan
}

# Manual old-PoC STOP intent only. No process/marker/IPFW mutation;
# original FD9 comes from this service and Config flock from Python route.
native_voice_legacy_arm_stop_intent_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_script="${BACKEND_DIR}/voice_native_legacy_quiescence_intent.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_script}" ] || return 69
    "${_voice_python}" "${_voice_script}" arm-stop-intent
}

# Operator-only sealed reverse WAL of an ALREADY stopped old Telegram PoC.
# Records exact no-process/no-old-IPFW/marker-OFF state without actuating them.
native_voice_legacy_seal_clean_wal_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_script="${BACKEND_DIR}/voice_native_legacy_clean_wal_route.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_script}" ] || {
        echo "ERROR: legacy Voice clean-WAL inspector not installed" >&2
        return 69
    }
    "${_voice_python}" "${_voice_script}" seal-clean-wal
}

# Explicit root-only OPERATOR recovery of a fully sealed old Telegram PoC.
# This invokes REAL old IPFW/file/marker/process rollback under the same FD9.
# NOT registered with configd, GUI, boot, normal start or runtime-failure.
native_voice_legacy_rollback_five_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_script="${BACKEND_DIR}/voice_native_legacy_rollback_route.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_script}" ] || {
        echo "ERROR: native Voice old rollback executor unavailable" >&2
        return 69
    }
    "${_voice_python}" "${_voice_script}" rollback
}

# Owner-only, READ-ONLY physical appliance baseline BEFORE any Voice journal.
# This observes the already-running ordinary service; does not generate
# Config, touch IPFW, stop/start a process, or authorize Voice ON.
native_voice_lifecycle_inspect_service()
{
    # One read-only lifecycle classifier shares the existing FD9 route.
    # It NEVER bypasses the legacy cutover guard or activates Voice ON.
    _native_voice_router_python="/usr/local/bin/python3.13"
    _native_voice_router_script="${BACKEND_DIR}/voice_native_lifecycle_router.py"
    [ -x "${_native_voice_router_python}" ] &&
    [ -r "${_native_voice_router_script}" ] || {
        echo "ERROR: native Voice lifecycle router is unavailable" >&2
        return 69
    }
    "${_native_voice_router_python}" "${_native_voice_router_script}" inspect
}

# Compatibility guard: before either old PoC mutation, refuse coexistence
# with saved native Voice ON or any pending native cutover, under EXISTING FD9.
# This does not migrate or clean up legacy PoC state; status remains readable.
native_voice_legacy_poc_preflight_service()
{
    _native_voice_router_python="/usr/local/bin/python3.13"
    _native_voice_router_script="${BACKEND_DIR}/voice_native_lifecycle_router.py"
    [ -x "${_native_voice_router_python}" ] &&
    [ -r "${_native_voice_router_script}" ] || {
        echo "ERROR: native Voice compatibility guard is unavailable" >&2
        return 69
    }
    "${_native_voice_router_python}" "${_native_voice_router_script}" legacy-poc-preflight
}

# Read-only saved-model -> native compiler bridge, under the same FD9.
# This MUST NOT invoke the private five-resource actuator.
native_voice_candidate_preflight_service()
{
    _native_voice_router_python="/usr/local/bin/python3.13"
    _native_voice_router_script="${BACKEND_DIR}/voice_native_lifecycle_router.py"
    [ -x "${_native_voice_router_python}" ] &&
    [ -r "${_native_voice_router_script}" ] || {
        echo "ERROR: native Voice candidate preflight is unavailable" >&2
        return 69
    }
    "${_native_voice_router_python}" "${_native_voice_router_script}" candidate-preflight
}

# Owner-only presealed schema-4 forward Apply; NO GUI/configd/boot call.
# Operator-only; accepts an already-qualified DETACHED input tree, not a
# GUI POST or an independent candidate generator. Inherited FD9 is unchanged.
native_voice_prepare_prebuilt_service()
{
    _voice_action="${1:-prepare-prebuilt}"
    case "${_voice_action}" in
        prepare-prebuilt|prepare-from-release|prepare-from-saved|prepare-from-xml|prepare-from-draft|prepare-from-draft-and-apply) ;;
        *) return 64 ;;
    esac
    _voice_python="/usr/local/bin/python3.13"
    _voice_route="${BACKEND_DIR}/voice_native_prepare_route.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_route}" ] || {
        echo "ERROR: native Voice prepare router unavailable" >&2
        return 69
    }
    config_load "${CONFIG}" || return 69
    _voice_resolved_wan=$(config_resolve_interface "${WAN_IF}") || return 69
    [ -n "${_voice_resolved_wan}" ] && [ -n "${DIVERT_PORT}" ] || return 69
    if [ "${_voice_action}" = prepare-from-draft ] ||
       [ "${_voice_action}" = prepare-from-draft-and-apply ]; then
        # No Config bytes, browser XML, strategy or arbitrary file path may
        # cross the operator command line; only a fixed mask + SHA-256.
        _voice_mask="${2:-}"
        _voice_sha="${3:-}"
        case "${_voice_mask}" in
            [01][01][01][01][01]) ;;
            *) return 64 ;;
        esac
        [ "${_voice_mask}" != 00000 ] || return 64
        printf '%s\n' "${_voice_sha}" | grep -Eq '^[0-9a-f]{64}$' || return 64
        "${_voice_python}" "${_voice_route}" "${_voice_action}" \
            "${_voice_resolved_wan}" "${DIVERT_PORT}" "${_voice_mask}" "${_voice_sha}"
    else
        "${_voice_python}" "${_voice_route}" "${_voice_action}" \
            "${_voice_resolved_wan}" "${DIVERT_PORT}"
    fi
}

# Read-only GUI native Voice saved-draft candidate preview. This is NOT
# prepare-from-draft, does NOT seal PREPARED, and changes no persisted state.
native_voice_preview_draft_service()
{
    _voice_mask="${1:-}"
    _voice_sha="${2:-}"
    case "${_voice_mask}" in
        [01][01][01][01][01]) ;;
        *) return 64 ;;
    esac
    [ "${_voice_mask}" != 00000 ] || return 64
    printf '%s\n' "${_voice_sha}" | grep -Eq '^[0-9a-f]{64}$' || return 64
    _voice_python="/usr/local/bin/python3.13"
    _voice_route="${BACKEND_DIR}/voice_native_draft_preview_route.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_route}" ] || {
        echo "ERROR: native Voice read-only preview unavailable" >&2
        return 69
    }
    "${_voice_python}" "${_voice_route}" preview-draft "${_voice_mask}" "${_voice_sha}"
}

native_voice_apply_prepared_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_route="${BACKEND_DIR}/voice_native_apply_route.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_route}" ] || {
        echo "ERROR: native Voice forward router unavailable" >&2
        return 69
    }
    "${_voice_python}" "${_voice_route}" execute-prepared
}

native_voice_legacy_live_preflight_service()
{
    _voice_python="/usr/local/bin/python3.13"
    _voice_script="${BACKEND_DIR}/voice_native_legacy_live_preflight.py"
    [ -x "${_voice_python}" ] && [ -r "${_voice_script}" ] || {
        echo "ERROR: legacy Voice read-only preflight is not installed" >&2
        return 69
    }
    "${_voice_python}" "${_voice_script}" inspect
}

native_voice_live_preflight_service()
{
    _native_voice_live_python="/usr/local/bin/python3.13"
    _native_voice_live_script="${BACKEND_DIR}/voice_native_live_preflight.py"
    [ -x "${_native_voice_live_python}" ] &&
    [ -r "${_native_voice_live_script}" ] || {
        echo "ERROR: native Voice live preflight is not installed" >&2
        return 1
    }
    "${_native_voice_live_python}" "${_native_voice_live_script}" inspect
}

# One actual runtime/Config Apply owner: the existing service process holds
# FD9 for the ENTIRE operation; Python journal and PHP Config worker run as
# children inheriting that ownership. No nested configd/lockf acquisition,
# no second Voice daemon, no old Config XML file replacement.
shared_apply_require_tools()
{
    [ -x /usr/local/bin/php ] && [ -x /usr/local/bin/jq ]
}
shared_apply_workspace()
{
    printf "/var/db/zapret2/shared-work/%s\n" "$1"
}
shared_apply_native_config()
{
    /usr/local/bin/php "${SCRIPT_DIR}/shared_apply_config.php" "$@"
}
shared_apply_json_field()
{
    /usr/local/bin/jq -er "$1"
}
# Only a PREPARED journal (before any mutation) can be auto-closed at boot.
# The root FD9 Python command rechecks the sealed candidate and journal.
shared_apply_recover_prepared_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in prepared\ *) ;; *) return 69 ;; esac
    _shared_recover_id=$(printf "%s\n" "$1" | cut -d " " -f 2)
    _shared_recover_page=$(printf "%s\n" "$1" | cut -d " " -f 3)
    [ "$1" = "prepared $_shared_recover_id $_shared_recover_page" ] || return 69
    [ "${#_shared_recover_id}" -eq 32 ] || return 69
    case "$_shared_recover_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    case "$_shared_recover_page" in voice|strategies) ;; *) return 69 ;; esac
    [ -x /usr/local/bin/python3.13 ] || return 69
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \
        recover-prepared "$_shared_recover_id"
}
# Read the durable owner only under the existing FreeBSD FD9. This is a
# tiny native boot dispatcher, not a second runtime or Config persistence.
shared_apply_inspect_service()
{
    [ -x /usr/local/bin/python3.13 ] || return 69
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" inspect
}

# Reapply the saved COMMON candidate after reboot, without changing Config.
# Every boot must prove the same completed journal, release and native saved
# model. The original apply_runtime code owns dvtws2, supervisor and IPFW.
shared_apply_boot_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in committed\ *) ;; *) return 69 ;; esac
    _shared_boot_id=$(printf "%s\n" "$1" | cut -d " " -f 2)
    _shared_boot_page=$(printf "%s\n" "$1" | cut -d " " -f 3)
    [ "$1" = "committed $_shared_boot_id $_shared_boot_page" ] || return 69
    case "$_shared_boot_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_shared_boot_id}" -eq 32 ] || return 69
    case "$_shared_boot_page" in voice|strategies) ;; *) return 69 ;; esac
    preflight_voice_cutover_journals common-apply || return 69
    shared_apply_bundle_service verify "$_shared_boot_id" || return 69
    _shared_boot_saved=$(shared_apply_native_config saved "$_shared_boot_id" "$_shared_boot_page") || return 69
    _shared_boot_mode=$(printf "%s\n" "$_shared_boot_saved" |
        shared_apply_json_field '.enabled | select(.=="0" or .=="1")') || return 69
    _shared_boot_check=$(printf "%s\n" "$_shared_boot_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _shared_boot_dir=$(shared_apply_workspace "$_shared_boot_id") || return 69
    [ -d "$_shared_boot_dir/release" ] &&
    [ ! -L "$_shared_boot_dir/release" ] || return 69
    # A kernel rebuilt after reboot has no durable IPFW tables; the existing
    # common runtime adapter validates the kernel owner before any mutation.
    # A partial failure is NOT a successful boot and never falls back to
    # legacy Telegram Voice service.
    apply_runtime_activate "$_shared_boot_dir/release" "$_shared_boot_mode" || return 70
    apply_runtime_commit || return 70
    printf "native-common-boot=%s\n" "$_shared_boot_id"
}
# Seal/attest the exact native XML, plan and all generated release bytes.
# This is one evidence bundle inside the same FD9 operation, NOT a new WAL.
shared_apply_bundle_service()
{
    [ "$#" -eq 2 ] || return 64
    case "$1" in seal|verify) ;; *) return 64 ;; esac
    [ -x /usr/local/bin/python3.13 ] || return 69
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_seal.py" "$1" "$2"
}
shared_apply_execute_service()
{
    [ "$#" -eq 2 ] || return 64
    case "$1" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#1}" -eq 32 ] || return 64
    case "$2" in voice|strategies) ;; *) return 64 ;; esac
    preflight_voice_cutover_journals common-apply || return 69
    shared_apply_require_tools || return 69
    _shared_apply_id="$1"
    _shared_apply_page="$2"
    _shared_apply_root=$(shared_apply_workspace "$_shared_apply_id") || return 69
    [ -d "$_shared_apply_root/release" ] &&
    [ -f "$_shared_apply_root/candidate.xml" ] &&
    [ -f "$_shared_apply_root/plan.json" ] || return 69
    shared_apply_bundle_service verify "$_shared_apply_id" || return 69
    _shared_apply_preview=$(shared_apply_native_config preflight \
        "$_shared_apply_id" "$_shared_apply_page") || return 69
    _shared_apply_mode=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.enabled | select(.=="0" or .=="1")') || return 69
    _shared_apply_base=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.base | select(test("^[a-f0-9]{64}$"))') || return 69
    _shared_apply_candidate=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.candidate | select(test("^[a-f0-9]{64}$"))') || return 69
    _shared_apply_fields=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.fields | if length==0 then "-" else join(",") end') || return 69
    # The journal records only a fixed operation identity and owned-fields
    # proof. It never contains private Config XML or untrusted shell strings.
    shared_apply_record_service prepared "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 69
    shared_apply_record_service activating "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 69
    if ! apply_runtime_activate "$_shared_apply_root/release" "$_shared_apply_mode"; then
        # activate() may have restored internally, or may have failed between
        # irreversible observations. Never claim a verified rollback merely
        # because a shell status is zero or APPLY_PHASE was reset.
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    if ! shared_apply_record_service activated "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields"; then
        if apply_runtime_restore; then
            shared_apply_record_service restored "$_shared_apply_id" "$_shared_apply_page" \
                "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 70
            return 69
        fi
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    # Independent proof against a swap between preflight and kernel install.
    # A failed proof is still pre-Config; restore only if fully attested.
    if ! shared_apply_bundle_service verify "$_shared_apply_id"; then
        if apply_runtime_restore; then
            shared_apply_record_service restored "$_shared_apply_id" "$_shared_apply_page" \
                "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 70
            return 69
        fi
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    # Native Config::save is performed by the SAME existing model writer.
    # Only explicit 69 means no save was attempted; every other nonzero
    # status could be a mid-save crash and MUST preserve runtime/evidence.
    shared_apply_native_config save "$_shared_apply_id" "$_shared_apply_page"
    _shared_apply_save_status=$?
    if [ "$_shared_apply_save_status" -ne 0 ]; then
        if [ "$_shared_apply_save_status" -eq 69 ]; then
            if apply_runtime_restore; then
                shared_apply_record_service restored "$_shared_apply_id" "$_shared_apply_page" \
                    "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 70
                return 69
            fi
        fi
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    shared_apply_record_service config-saved "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 70
    if ! apply_runtime_commit; then
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    shared_apply_record_service committed "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 70
    printf "applied-id=%s\n" "$_shared_apply_id"
}
# One FD9 operation now stages a submitted native request AND builds its
# entire detached shared runtime. No kernel, Config save, or engine changes.
shared_apply_build_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in
        ""|*[!A-Za-z0-9_-]*) return 64 ;;
    esac
    [ "${#1}" -le 65536 ] || return 64
    preflight_voice_cutover_journals common-apply || return 69
    [ -x /usr/local/bin/php ] || return 69
    _shared_stage_result=$(/usr/local/bin/php \
        "${SCRIPT_DIR}/shared_apply_request.php" stage "$1") || return 69
    case "$_shared_stage_result" in
        prepared-id=*) _shared_stage_id="${_shared_stage_result#prepared-id=}" ;;
        *) return 69 ;;
    esac
    case "$_shared_stage_id" in
        *[!a-f0-9]*|"") return 69 ;;
    esac
    [ "${#_shared_stage_id}" -eq 32 ] || return 69
    shared_apply_prepare_service "$_shared_stage_id" || return $?
    printf "prepared-id=%s\n" "$_shared_stage_id"
}
# Prepare one complete Voice+Strategies release from the detached OPNsense
# candidate. This is an INTERNAL FD9 operation, not a Config/runtime Apply.
# Caller must have placed its root-owned candidate.xml in the fixed private
# shared-work directory; no arbitrary file paths can reach this command.
shared_apply_prepare_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in
        *[!a-f0-9]*|"") return 64 ;;
    esac
    [ "${#1}" -eq 32 ] || return 64
    preflight_voice_cutover_journals common-apply || return 69
    [ -x /usr/local/bin/python3.13 ] || return 69
    _shared_work="/var/db/zapret2/shared-work/$1"
    [ -d "$_shared_work" ] && [ ! -L "$_shared_work" ] || return 69
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_render.py" render "$1" || return 69
    _shared_template="$_shared_work/templates/usr/local/etc/zapret2/zapret.conf"
    [ -f "$_shared_template" ] && [ ! -L "$_shared_template" ] || return 69
    orchestrator_build_release \
        "$_shared_template" "$ZAPRET_DIR" "$ACTIVE_DIR" \
        "$_shared_work" "$_shared_work/release" "$STAGE_FILE" \
        shared-candidate "$_shared_work/candidate.xml" || return $?
    shared_apply_bundle_service seal "$1"
}
# Internal root-only Apply phases; service_with_lifecycle_lock supplies FD9.
shared_apply_record_service()
{
    [ "$#" -eq 6 ] || return 64
    [ -x /usr/local/bin/python3.13 ] || return 69
    [ -r "${BACKEND_DIR}/shared_apply_operation.py" ] || return 69
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \
        record "$1" "$2" "$3" "$4" "$5" "$6"
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
            native_voice_legacy_poc_preflight_service || return 69
            telegram_voice_enable_service
            ;;
        telegram-voice-disable)
            native_voice_legacy_poc_preflight_service || return 69
            telegram_voice_disable_service
            ;;
        telegram-voice-status)
            telegram_voice_status_service
            ;;
        reconfigure)
            reconfigure_service
            ;;
        shared-apply-execute)
            shared_apply_execute_service "${2:-}" "${3:-}"
            ;;
        shared-apply-build)
            shared_apply_build_service "${2:-}"
            ;;
        shared-apply-prepare)
            shared_apply_prepare_service "${2:-}"
            ;;
        shared-apply-record)
            shift
            shared_apply_record_service "$@"
            ;;
        native-voice-checkpoint)
            native_voice_checkpoint_service
            ;;
        native-voice-restore-stage)
            native_voice_restore_stage_service
            ;;
        native-voice-recovery-quiescence)
            native_voice_quiescence_service
            ;;
        native-voice-rollback-five)
            native_voice_five_restore_service
            ;;
        native-voice-boot-review)
            native_voice_boot_review_service
            ;;
        native-voice-live-preflight)
            native_voice_live_preflight_service
            ;;
        native-voice-legacy-boot-review)
            native_voice_legacy_boot_review_service
            ;;
        native-voice-legacy-boot-live-review)
            native_voice_legacy_boot_live_review_service
            ;;
        native-voice-legacy-capture-plan)
            native_voice_legacy_capture_plan_service
            ;;
        native-voice-legacy-arm-stop-intent)
            native_voice_legacy_arm_stop_intent_service
            ;;
        native-voice-legacy-seal-clean-wal)
            native_voice_legacy_seal_clean_wal_service
            ;;
        native-voice-legacy-rollback-five)
            native_voice_legacy_rollback_five_service
            ;;
        native-voice-legacy-live-preflight)
            native_voice_legacy_live_preflight_service
            ;;
        native-voice-lifecycle-inspect)
            native_voice_lifecycle_inspect_service
            ;;
        native-voice-candidate-preflight)
            native_voice_candidate_preflight_service
            ;;
        native-voice-prepare-prebuilt)
            native_voice_prepare_prebuilt_service
            ;;
        native-voice-prepare-release)
            native_voice_prepare_prebuilt_service prepare-from-release
            ;;
        native-voice-prepare-saved)
            native_voice_prepare_prebuilt_service prepare-from-saved
            ;;
        native-voice-prepare-xml)
            native_voice_prepare_prebuilt_service prepare-from-xml
            ;;
        native-voice-prepare-draft)
            native_voice_prepare_prebuilt_service prepare-from-draft "${2:-}" "${3:-}"
            ;;
        native-voice-prepare-apply-draft)
            # Operator-only, same original FD9 and original Config inode
            # from saved OFF draft through PREPARED and guarded COMMIT/rollback.
            native_voice_prepare_prebuilt_service prepare-from-draft-and-apply "${2:-}" "${3:-}"
            ;;
        native-voice-preview-draft)
            native_voice_preview_draft_service "${2:-}" "${3:-}"
            ;;
        native-voice-apply-prepared)
            native_voice_apply_prepared_service
            ;;
        native-voice-ipfw-seed)
            native_voice_ipfw_dispatch seed
            ;;
        native-voice-ipfw-activate)
            native_voice_ipfw_dispatch activate
            ;;
        native-voice-ipfw-commit)
            native_voice_ipfw_dispatch commit
            ;;
        native-voice-ipfw-rollback)
            native_voice_ipfw_dispatch rollback
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

# A pending full Voice cutover or per-IPFW journal is stronger than the
# legacy service's ordinary start/stop/reconfigure semantics. In particular,
# boot must NOT clean old resources before an interrupted transaction has
# been reviewed. This check is read-only and MUST run *under* the same lockf
# handle held by all existing Zapret2 lifecycle operations.
preflight_voice_cutover_journals()
{
    _voice_cutover_guard_script="${BACKEND_DIR}/voice_cutover_guard.py"
    _voice_cutover_guard_python=/usr/local/bin/python3.13

    # FreeBSD production uses only the trusted, absolute pkg interpreter.
    # The repository's Linux integration tests run from a non-installed
    # BACKEND_DIR; there alone resolve the versioned CI interpreter on PATH.
    # Never permit an environment-supplied interpreter or bypass in a live
    # OPNsense installation.
    if [ ! -x "${_voice_cutover_guard_python}" ]; then
        case "${BACKEND_DIR}" in
            /usr/local/opnsense/scripts/OPNsense/Zapret/backend)
                ;;
            *)
                _voice_cutover_guard_python=$(command -v python3.13 2>/dev/null || true)
                ;;
        esac
    fi

    if [ ! -r "${_voice_cutover_guard_script}" ] ||
       [ -z "${_voice_cutover_guard_python}" ] ||
       [ ! -x "${_voice_cutover_guard_python}" ]; then
        echo "ERROR: native Voice journal inspection is unavailable; refusing lifecycle mutation" >&2
        return 69
    fi
    "${_voice_cutover_guard_python}" "${_voice_cutover_guard_script}" "$@"
}

# Fixed native journal locator (mockable only by isolated shell extraction).
shared_apply_has_record_service()
{
    [ -e /var/db/zapret2/shared-apply ] ||
    [ -L /var/db/zapret2/shared-apply ]
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
        # Do not permit ANY legacy lifecycle action to overwrite the
        # evidence of an interrupted Voice cutover. Status/inspection remain
        # available, and no journal is created during normal operation.
        case "${1:-}" in
            start|reconfigure)
                # A committed common owner gets the common native boot path,
                # never the old template/engine builder. Pending/foreign
                # evidence still blocks start before any kernel mutation.
                if shared_apply_has_record_service; then
                    _shared_owner=$(shared_apply_inspect_service) || return 69
                    case "$_shared_owner" in
                        committed\ *)
                            shared_apply_boot_service "$_shared_owner"
                            return $?
                            ;;
                        prepared\ *)
                            shared_apply_recover_prepared_service "$_shared_owner" || return 69
                            # Recovery may uncover a previous committed
                            # common owner. Reinspect and boot that owner;
                            # NEVER fall through to legacy after restoring a
                            # second Apply over an already committed engine.
                            _shared_owner=$(shared_apply_inspect_service) || return 69
                            case "$_shared_owner" in
                                committed\ *)
                                    shared_apply_boot_service "$_shared_owner"
                                    return $?
                                    ;;
                                restored) ;;
                                *) return 69 ;;
                            esac
                            ;;
                        none|restored) ;;
                        *) return 69 ;;
                    esac
                fi
                preflight_voice_cutover_journals || return 69
                ;;
            stop|restart|native-voice-checkpoint|telegram-voice-enable|telegram-voice-disable|runtime-failure|strategy-lab|strategy-lab-circular|strategy-lab-recover)
                preflight_voice_cutover_journals || return 69
                ;;
        esac
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
    start|stop|restart|reconfigure|native-voice-checkpoint|native-voice-restore-stage|native-voice-recovery-quiescence|native-voice-rollback-five|native-voice-boot-review|native-voice-live-preflight|native-voice-legacy-live-preflight|native-voice-legacy-boot-review|native-voice-legacy-boot-live-review|native-voice-legacy-capture-plan|native-voice-legacy-arm-stop-intent|native-voice-legacy-seal-clean-wal|native-voice-legacy-rollback-five|native-voice-lifecycle-inspect|native-voice-candidate-preflight|native-voice-prepare-prebuilt|native-voice-apply-prepared|native-voice-prepare-release|native-voice-prepare-saved|native-voice-prepare-xml|native-voice-prepare-draft|native-voice-prepare-apply-draft|native-voice-preview-draft|native-voice-ipfw-seed|native-voice-ipfw-activate|native-voice-ipfw-commit|native-voice-ipfw-rollback|telegram-voice-enable|telegram-voice-disable|shared-apply-record|shared-apply-prepare|shared-apply-build|shared-apply-execute)
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
