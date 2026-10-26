#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
BACKEND_DIR="${BACKEND_DIR:-${SCRIPT_DIR}/backend}"

for module in common config parser registry storage targets target_mode \
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
# Shared native Apply and recovery call supervisor_start() from apply_runtime.sh
# and require the absolute executable service callback. Ordinary Strategies
# passed "$0" via orchestrator, but the common path otherwise inherited an
# unset SERVICE_SCRIPT and could not start or restore the supervisor.
SERVICE_SCRIPT="${SCRIPT_DIR}/zapret_service.sh"
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
    # Cover all five destination-scoped Voice tables, not only old Telegram.
    for _strategy_lab_voice_name in telegram discord x sip custom; do
        _strategy_lab_voice_table="zapret2_voice_${_strategy_lab_voice_name}"
        if "${STRATEGY_LAB_SEMANTIC_IPFW_BIN}" table \
            "${_strategy_lab_voice_table}" info >/dev/null 2>&1; then
            printf 'table %s\n' "${_strategy_lab_voice_table}" \
                >> "${_strategy_lab_semantic_rules}"
            "${STRATEGY_LAB_SEMANTIC_IPFW_BIN}" table \
                "${_strategy_lab_voice_table}" list 2>/dev/null |
                LC_ALL=C sort >> "${_strategy_lab_semantic_rules}" || {
                    rm -f "${_strategy_lab_semantic_rules}"
                    return 1
                }
        fi
    done
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
            if shared_apply_has_record_service; then
                _lab_owner=$(shared_apply_inspect_service) || return 69
                case "$_lab_owner" in
                    committed\ *)
                        preflight_shared_apply_journal strategy-lab-native || return 69
                        shared_apply_stop_service "$_lab_owner"
                        return $?
                        ;;
                    none|restored) ;;
                    *) return 69 ;;
                esac
            fi
            preflight_shared_apply_journal || return 69
            stop_service
            ;;
        extra-resources-native-restore-previous)
            [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] &&
            [ "${EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE:-0}" = 1 ] || return 75
            extra_resources_native_restore_previous_service "${2:-}" "${3:-}" "${4:-}"
            ;;
        extra-resources-native-previous-owner)
            [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] || return 75
            extra_resources_native_previous_owner_service
            ;;
        extra-resources-native-trial)
            [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] &&
            [ "${EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL:-0}" = 1 ] || return 75
            extra_resources_native_trial_service
            ;;
        extra-resources-native-build-saved)
            # Original FD9 is INHERITED from the transaction worker. This
            # action stages a real saved Config common GUI release but does
            # not start the engine, save Config or touch IPFW.
            [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] &&
            [ "${EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL:-0}" = 1 ] || return 75
            extra_resources_native_build_saved_service
            ;;
        strategy-lab-start)
            if shared_apply_has_record_service; then
                _lab_owner=$(shared_apply_inspect_service) || return 69
                case "$_lab_owner" in
                    committed\ *)
                        preflight_shared_apply_journal strategy-lab-native || return 69
                        shared_apply_boot_service "$_lab_owner"
                        return $?
                        ;;
                    none|restored) ;;
                    *) return 69 ;;
                esac
            fi
            preflight_shared_apply_journal || return 69
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

# Read-only saved Voice model / compiled candidate under common FD9 and Config.
# This observes the already-running ordinary service; does not generate
# Config, touch IPFW, stop/start a process, or authorize Voice ON.
native_voice_lifecycle_inspect_service()
{
    # One read-only lifecycle classifier shares the existing FD9 route.
    # It never mutates the common owner or activates Voice ON.
    _native_voice_router_python="/usr/local/bin/python3.13"
    _native_voice_router_script="${BACKEND_DIR}/voice_native_lifecycle_router.py"
    [ -x "${_native_voice_router_python}" ] &&
    [ -r "${_native_voice_router_script}" ] || {
        echo "ERROR: native Voice lifecycle router is unavailable" >&2
        return 69
    }
    "${_native_voice_router_python}" "${_native_voice_router_script}" inspect
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

# Root-only native preview of saved ordinary Strategies. setup.lock is held
# by the existing extra_resources_launcher.sh BEFORE this FD9 owner enters.
# This only proves saved Config and future Git HEAD input provenance; it
# never compiles engine Lua exports or authorizes removal.
extra_resources_preview_saved_service()
{
    [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] || return 75
    [ -x /usr/local/bin/python3.13 ] || return 69
    [ -r "${SCRIPT_DIR}/extra_resources_saved_route.py" ] || return 69
    /usr/local/bin/python3.13 "${SCRIPT_DIR}/extra_resources_saved_route.py" preview-saved
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
# Cold reconciliation for a completed native Config save whose final common
# IPFW/runtime commit was interrupted by power loss. This is NOT generic
# crash recovery: no engine, monitor, plugin IPFW rules or tables may remain.
shared_apply_recover_saved_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in config-saved\ *) ;; *) return 69 ;; esac
    _shared_saved_id=$(printf "%s\n" "$1" | cut -d " " -f 2)
    _shared_saved_page=$(printf "%s\n" "$1" | cut -d " " -f 3)
    [ "$1" = "config-saved $_shared_saved_id $_shared_saved_page" ] || return 69
    [ "${#_shared_saved_id}" -eq 32 ] || return 69
    case "$_shared_saved_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    case "$_shared_saved_page" in voice|strategies) ;; *) return 69 ;; esac
    # Guard accepts only this exact phase and only original root FD9.
    preflight_shared_apply_journal common-recover-saved || return 69
    shared_apply_bundle_service verify "$_shared_saved_id" || return 69
    _shared_saved_config=$(shared_apply_native_config saved "$_shared_saved_id" "$_shared_saved_page") || return 69
    _shared_saved_mode=$(printf "%s\n" "$_shared_saved_config" |
        shared_apply_json_field '.enabled | select(.=="0" or .=="1")') || return 69
    _shared_saved_ok=$(printf "%s\n" "$_shared_saved_config" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _shared_saved_root=$(shared_apply_workspace "$_shared_saved_id") || return 69
    [ -d "$_shared_saved_root/release" ] && [ ! -L "$_shared_saved_root/release" ] || return 69
    # Existing processes or IPFW indicate a non-cold/partial transaction.
    # No guessed cleanup or old-PoC fallback is permitted in this state.
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then
        return 69
    fi
    firewall_shared_runtime verify "$_shared_saved_root/release" - || return 69
    # Reuse the SAME sealed operation ID for native atomic stage/park
    # artifacts. PID-scoped names in a power-cut recovery cannot be tied
    # back to the one durable shared Apply record.
    apply_runtime_activate "$_shared_saved_root/release" "$_shared_saved_mode" \
        "$_shared_saved_id" || return 70
    # Native Config save is already durable in this phase. Never destroy
    # the IPFW rollback stages until BOTH actual runtime and a freshly
    # reread native Config still attest the exact same committed owner.
    shared_apply_bundle_service verify "$_shared_saved_id" || return 70
    apply_runtime_attest_activated || return 70
    _shared_saved_again=$(shared_apply_native_config saved \
        "$_shared_saved_id" "$_shared_saved_page") || return 70
    if ! {
        _shared_saved_again_result=$(printf "%s\n" "$_shared_saved_again" | \
            shared_apply_json_field '.result | select(.=="committed")') &&
        _shared_saved_again_mode=$(printf "%s\n" "$_shared_saved_again" | \
            shared_apply_json_field '.enabled | select(.=="0" or .=="1")') &&
        _shared_saved_again_digest=$(printf "%s\n" "$_shared_saved_again" | \
            shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') &&
        _shared_saved_initial_digest=$(printf "%s\n" "$_shared_saved_config" | \
            shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') &&
        [ "$_shared_saved_again_result" = committed ] &&
        [ "$_shared_saved_again_mode" = "$_shared_saved_mode" ] &&
        [ "$_shared_saved_again_digest" = "$_shared_saved_initial_digest" ] &&
        apply_runtime_attest_activated
    }; then
        # Config may have changed independently while the stopped owner
        # was starting. Do not roll back a saved Config or delete stages.
        return 70
    fi
    apply_runtime_commit || return 70
    # This terminal transition is made ONLY after physical runtime/IPFW
    # completion. If this write fails, Config-saved evidence remains pending.
    [ -x /usr/local/bin/python3.13 ] || return 70
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \
        finish-saved "$_shared_saved_id" || return 70
    printf "recovered-saved-id=%s\n" "$_shared_saved_id"
}
# An interrupted ACTIVATING can be closed only when every observed
# resource is still the previous *sealed common* release, i.e. no mutation
# took effect. Never infer safety from empty IPFW/processes alone.
shared_apply_recover_activating_pristine_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in activating\ *) ;; *) return 69 ;; esac
    _shared_pristine_id=$(printf "%s\n" "$1" | cut -d " " -f 2)
    _shared_pristine_page=$(printf "%s\n" "$1" | cut -d " " -f 3)
    _shared_pristine_old=$(printf "%s\n" "$1" | cut -d " " -f 4)
    _shared_pristine_old_page=$(printf "%s\n" "$1" | cut -d " " -f 5)
    [ "$1" = "activating $_shared_pristine_id $_shared_pristine_page $_shared_pristine_old $_shared_pristine_old_page" ] || return 69
    for _shared_pristine_value in "$_shared_pristine_id" "$_shared_pristine_old"; do
        [ "${#_shared_pristine_value}" -eq 32 ] || return 69
        case "$_shared_pristine_value" in ""|*[!a-f0-9]*) return 69 ;; esac
    done
    case "$_shared_pristine_page" in voice|strategies) ;; *) return 69 ;; esac
    case "$_shared_pristine_old_page" in voice|strategies) ;; *) return 69 ;; esac
    [ "$_shared_pristine_id" != "$_shared_pristine_old" ] || return 69
    preflight_shared_apply_journal common-recover-activating || return 69
    shared_apply_bundle_service verify "$_shared_pristine_id" || return 69
    shared_apply_bundle_service verify "$_shared_pristine_old" || return 69
    _shared_pristine_config=$(shared_apply_native_config saved         "$_shared_pristine_old" "$_shared_pristine_old_page") || return 69
    _shared_pristine_saved=$(printf "%s\n" "$_shared_pristine_config" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _shared_pristine_dir=$(shared_apply_workspace "$_shared_pristine_old") || return 69
    [ -d "$_shared_pristine_dir/release" ] && [ ! -L "$_shared_pristine_dir/release" ] || return 69
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
    atomic_verify_tree "$_shared_pristine_dir/release" "$ACTIVE_DIR" || return 69
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then
        return 69
    fi
    # A lost PID file must not hide an orphan running dvtws2.
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 69
    firewall_shared_runtime verify "$_shared_pristine_dir/release" - || return 69
    # Crash during the operation-ID atomic copy can leave a *complete* new
    # stage even though the previous active release was never displaced.
    # A partial stage is NOT an authorized rollback target and stays for
    # manual inspection. Reject unexpected parked/backup old owners.
    _shared_pristine_parent=$(dirname "$ACTIVE_DIR") || return 69
    _shared_pristine_name=$(basename "$ACTIVE_DIR") || return 69
    _shared_pristine_stage="$_shared_pristine_parent/.$_shared_pristine_name.stage.$_shared_pristine_id"
    _shared_pristine_parked="$_shared_pristine_parent/.$_shared_pristine_name.old.$_shared_pristine_id"
    _shared_pristine_backup="$BACKUP_ROOT/$_shared_pristine_name-$_shared_pristine_id"
    [ ! -e "$_shared_pristine_parked" ] && [ ! -L "$_shared_pristine_parked" ] &&
    [ ! -e "$_shared_pristine_backup" ] && [ ! -L "$_shared_pristine_backup" ] || return 69
    if [ -e "$_shared_pristine_stage" ] || [ -L "$_shared_pristine_stage" ]; then
        [ -d "$_shared_pristine_stage" ] && [ ! -L "$_shared_pristine_stage" ] || return 69
        _shared_pristine_new_dir=$(shared_apply_workspace "$_shared_pristine_id") || return 69
        [ -d "$_shared_pristine_new_dir/release" ] &&
        [ ! -L "$_shared_pristine_new_dir/release" ] || return 69
        atomic_verify_tree "$_shared_pristine_new_dir/release" "$_shared_pristine_stage" || return 69
        shared_apply_bundle_service verify "$_shared_pristine_id" || return 69
        atomic_remove_tree "$_shared_pristine_stage" || return 70
        [ ! -e "$_shared_pristine_stage" ] && [ ! -L "$_shared_pristine_stage" ] || return 70
    fi
    # Re-check all native owners after removing only an exact sealed stage.
    # A power cut after deletion is idempotent: the existing journal remains
    # activating until the durable recover-activating terminal command.
    shared_apply_bundle_service verify "$_shared_pristine_old" || return 69
    atomic_verify_tree "$_shared_pristine_dir/release" "$ACTIVE_DIR" || return 69
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then
        return 69
    fi
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 69
    firewall_shared_runtime verify "$_shared_pristine_dir/release" - || return 69
    [ -x /usr/local/bin/python3.13 ] || return 69
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \
        recover-activating "$_shared_pristine_id" "$_shared_pristine_old" || return 69
    printf "recovered-pristine-id=%s\n" "$_shared_pristine_id"
}
# Recover a cold pre-save ACTIVATED or interrupted ACTIVATING in which the
# atomic rename already installed the *whole* new common release. Old saved
# Config, sealed bundles, no engine and empty IPFW are attested under FD9.
# The pristine-activating path remains separate; no partial tree is trusted.
shared_apply_recover_activated_cold_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in activated\ *|activating\ *) ;; *) return 69 ;; esac
    _shared_cold_phase=$(printf "%s\n" "$1" | cut -d " " -f 1)
    _shared_cold_id=$(printf "%s\n" "$1" | cut -d " " -f 2)
    _shared_cold_page=$(printf "%s\n" "$1" | cut -d " " -f 3)
    _shared_cold_old=$(printf "%s\n" "$1" | cut -d " " -f 4)
    _shared_cold_old_page=$(printf "%s\n" "$1" | cut -d " " -f 5)
    [ "$1" = "$_shared_cold_phase $_shared_cold_id $_shared_cold_page $_shared_cold_old $_shared_cold_old_page" ] || return 69
    for _shared_cold_value in "$_shared_cold_id" "$_shared_cold_old"; do
        [ "${#_shared_cold_value}" -eq 32 ] || return 69
        case "$_shared_cold_value" in ""|*[!a-f0-9]*) return 69 ;; esac
    done
    case "$_shared_cold_page" in voice|strategies) ;; *) return 69 ;; esac
    case "$_shared_cold_old_page" in voice|strategies) ;; *) return 69 ;; esac
    [ "$_shared_cold_id" != "$_shared_cold_old" ] || return 69
    preflight_shared_apply_journal "common-recover-$_shared_cold_phase" || return 69
    shared_apply_bundle_service verify "$_shared_cold_id" || return 69
    shared_apply_bundle_service verify "$_shared_cold_old" || return 69
    _shared_cold_saved=$(shared_apply_native_config saved \
        "$_shared_cold_old" "$_shared_cold_old_page") || return 69
    _shared_cold_ok=$(printf "%s\n" "$_shared_cold_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _shared_cold_new_root=$(shared_apply_workspace "$_shared_cold_id") || return 69
    _shared_cold_old_root=$(shared_apply_workspace "$_shared_cold_old") || return 69
    for _shared_cold_tree in "$_shared_cold_new_root/release" "$_shared_cold_old_root/release" "$ACTIVE_DIR"; do
        [ -d "$_shared_cold_tree" ] && [ ! -L "$_shared_cold_tree" ] || return 69
    done
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then
        return 69
    fi
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 69
    # On power loss before native Config save, ACTIVATED may contain a whole
    # new release and its exact uncommitted IPFW rules/stage tables. No
    # process may be live. Recover only a verified common predecessor: first
    # roll back its staged tables/rules, then quiesce its kernel range so that
    # ordinary committed-owner boot can safely start it again. A restart in
    # either verified intermediate state resumes; unknown state stays blocked.
    if ! firewall_shared_runtime verify "$_shared_cold_old_root/release" -; then
        # An interrupted activation may have completed runtime/IPFW mutation
        # before its journal advanced from activating to activated. Both
        # phases require the SAME exact installed-new/cold-owner witnesses.
        # The phase-specific terminal CLI still enforces the durable journal.
        atomic_verify_tree "$_shared_cold_new_root/release" "$ACTIVE_DIR" || return 69
        shared_apply_bundle_service verify "$_shared_cold_id" || return 69
        shared_apply_bundle_service verify "$_shared_cold_old" || return 69
        _shared_cold_saved=$(shared_apply_native_config saved \
            "$_shared_cold_old" "$_shared_cold_old_page") || return 69
        _shared_cold_ok=$(printf "%s\n" "$_shared_cold_saved" |
            shared_apply_json_field '.result | select(.=="committed")') || return 69
        if launcher_is_running "$CHILD_PIDFILE" ||
           supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then return 69; fi
        _apply_engine=0
        apply_runtime_attest_engine_inventory || return 69
        if firewall_shared_runtime verify-staged \
            "$_shared_cold_old_root/release" "$_shared_cold_new_root/release"; then
            # The existing IPFW transaction proves exact active new rules,
            # tables and old stage snapshots before any kernel mutation.
            firewall_shared_runtime rollback \
                "$_shared_cold_old_root/release" "$_shared_cold_new_root/release" || return 70
            firewall_shared_runtime verify \
                "$_shared_cold_old_root/release" "$_shared_cold_old_root/release" || return 70
        elif ! firewall_shared_runtime verify \
            "$_shared_cold_old_root/release" "$_shared_cold_old_root/release" &&
             ! firewall_shared_runtime verify-staged \
            "$_shared_cold_old_root/release" -; then
            return 69
        fi
        # A power cut after rollback leaves exact old IPFW; one after the
        # empty install may leave verified retired tables awaiting commit.
        if ! firewall_shared_runtime verify-staged "$_shared_cold_old_root/release" -; then
            firewall_shared_runtime install "$_shared_cold_old_root/release" - || return 70
        fi
        firewall_shared_runtime verify-staged "$_shared_cold_old_root/release" - || return 70
        firewall_shared_runtime commit "$_shared_cold_old_root/release" - || return 70
        firewall_shared_runtime verify "$_shared_cold_old_root/release" - || return 70
    fi
    # Idempotent completion if the previous tree was already restored.
    # Otherwise only an EXACT new sealed release may be replaced.
    if ! atomic_verify_tree "$_shared_cold_old_root/release" "$ACTIVE_DIR"; then
        atomic_verify_tree "$_shared_cold_new_root/release" "$ACTIVE_DIR" || return 69
        shared_apply_bundle_service verify "$_shared_cold_old" || return 69
        # Existing common atomic helper preserves failed candidate in BACKUP_ROOT.
        atomic_install_tree "$_shared_cold_old_root/release" "$ACTIVE_DIR" "$BACKUP_ROOT" >/dev/null || return 70
    fi
    atomic_verify_tree "$_shared_cold_old_root/release" "$ACTIVE_DIR" || return 70
    shared_apply_bundle_service verify "$_shared_cold_old" || return 70
    shared_apply_bundle_service verify "$_shared_cold_id" || return 70
    _shared_cold_saved=$(shared_apply_native_config saved \
        "$_shared_cold_old" "$_shared_cold_old_page") || return 70
    _shared_cold_ok=$(printf "%s\n" "$_shared_cold_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || return 70
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then
        return 70
    fi
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 70
    firewall_shared_runtime verify "$_shared_cold_old_root/release" - || return 70
    [ -x /usr/local/bin/python3.13 ] || return 70
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \
        "finish-$_shared_cold_phase" "$_shared_cold_id" "$_shared_cold_old" || return 70
    printf "recovered-%s-id=%s\n" "$_shared_cold_phase" "$_shared_cold_id"
}
# Cold rescue of an operation-ID-scoped atomic rename gap. PID-only
# stage/backup names from older installs are intentionally NOT recoverable.
# Original root FD9 and the existing shared journal are the only owners.
shared_apply_recover_activating_parked_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in activating\ *) ;; *) return 69 ;; esac
    _parked_id=$(printf "%s\n" "$1" | cut -d " " -f 2)
    _parked_page=$(printf "%s\n" "$1" | cut -d " " -f 3)
    _parked_old=$(printf "%s\n" "$1" | cut -d " " -f 4)
    _parked_old_page=$(printf "%s\n" "$1" | cut -d " " -f 5)
    [ "$1" = "activating $_parked_id $_parked_page $_parked_old $_parked_old_page" ] || return 69
    for _parked_value in "$_parked_id" "$_parked_old"; do
        case "$_parked_value" in ""|*[!a-f0-9]*) return 69 ;; esac
        [ "${#_parked_value}" -eq 32 ] || return 69
    done
    [ "$_parked_id" != "$_parked_old" ] || return 69
    case "$_parked_page" in voice|strategies) ;; *) return 69 ;; esac
    case "$_parked_old_page" in voice|strategies) ;; *) return 69 ;; esac
    preflight_shared_apply_journal common-recover-activating || return 69
    shared_apply_bundle_service verify "$_parked_id" || return 69
    shared_apply_bundle_service verify "$_parked_old" || return 69
    _parked_config=$(shared_apply_native_config saved "$_parked_old" "$_parked_old_page") || return 69
    _parked_ok=$(printf "%s\n" "$_parked_config" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _parked_new_root=$(shared_apply_workspace "$_parked_id") || return 69
    _parked_old_root=$(shared_apply_workspace "$_parked_old") || return 69
    _parked_parent=$(dirname "$ACTIVE_DIR") || return 69
    _parked_name=$(basename "$ACTIVE_DIR") || return 69
    _parked_stage="$_parked_parent/.$_parked_name.stage.$_parked_id"
    _parked_hold="$_parked_parent/.$_parked_name.old.$_parked_id"
    _parked_backup="$BACKUP_ROOT/$_parked_name-$_parked_id"
    # Positive evidence: exact new stage and ONE exact old hold/backup.
    [ ! -e "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
    [ -d "$_parked_stage" ] && [ ! -L "$_parked_stage" ] || return 69
    atomic_verify_tree "$_parked_new_root/release" "$_parked_stage" || return 69
    if [ -d "$_parked_hold" ] && [ ! -L "$_parked_hold" ] &&
       [ ! -e "$_parked_backup" ] && [ ! -L "$_parked_backup" ]; then
        _parked_previous="$_parked_hold"
    elif [ -d "$_parked_backup" ] && [ ! -L "$_parked_backup" ] &&
         [ ! -e "$_parked_hold" ] && [ ! -L "$_parked_hold" ]; then
        _parked_previous="$_parked_backup"
    else
        return 69
    fi
    atomic_verify_tree "$_parked_old_root/release" "$_parked_previous" || return 69
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then return 69; fi
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 69
    firewall_shared_runtime verify "$_parked_old_root/release" - || return 69
    # Re-attest before mutation. Never consume/remove parked artifacts.
    [ ! -e "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
    shared_apply_bundle_service verify "$_parked_id" || return 69
    shared_apply_bundle_service verify "$_parked_old" || return 69
    atomic_verify_tree "$_parked_new_root/release" "$_parked_stage" || return 69
    atomic_verify_tree "$_parked_old_root/release" "$_parked_previous" || return 69
    atomic_install_tree "$_parked_old_root/release" "$ACTIVE_DIR" "$BACKUP_ROOT" >/dev/null || return 70
    atomic_verify_tree "$_parked_old_root/release" "$ACTIVE_DIR" || return 70
    atomic_verify_tree "$_parked_new_root/release" "$_parked_stage" || return 70
    atomic_verify_tree "$_parked_old_root/release" "$_parked_previous" || return 70
    shared_apply_bundle_service verify "$_parked_id" || return 70
    shared_apply_bundle_service verify "$_parked_old" || return 70
    _parked_config=$(shared_apply_native_config saved "$_parked_old" "$_parked_old_page") || return 70
    _parked_ok=$(printf "%s\n" "$_parked_config" |
        shared_apply_json_field '.result | select(.=="committed")') || return 70
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then return 70; fi
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 70
    firewall_shared_runtime verify "$_parked_old_root/release" - || return 70
    [ -x /usr/local/bin/python3.13 ] || return 70
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \
        finish-activating "$_parked_id" "$_parked_old" || return 70
    printf "recovered-parked-id=%s\n" "$_parked_id"
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

# Stop exactly the committed common owner, using the original FD9 lifecycle.
# Native Config and the durable committed owner stay unchanged: start can
# bring the same sealed release back, without legacy fallback or a new Apply.
shared_apply_stop_service()
{
    [ "$#" -eq 1 ] || [ "$#" -eq 2 ] || return 64
    # A supervisor callback carries the PID it originally monitored. A
    # delayed callback must NEVER stop a newer shared dvtws2 incarnation.
    _shared_stop_failed_pid=
    if [ "$#" -eq 2 ]; then
        _shared_stop_failed_pid="$2"
        case "$_shared_stop_failed_pid" in ""|*[!0-9]*) return 69 ;; esac
        _shared_stop_recorded_pid=$(common_pidfile_read "$CHILD_PIDFILE") || return 69
        [ "$_shared_stop_failed_pid" = "$_shared_stop_recorded_pid" ] || return 69
    fi
    case "$1" in committed\ *) ;; *) return 69 ;; esac
    _shared_stop_id=$(printf "%s\n" "$1" | cut -d " " -f 2)
    _shared_stop_page=$(printf "%s\n" "$1" | cut -d " " -f 3)
    [ "$1" = "committed $_shared_stop_id $_shared_stop_page" ] || return 69
    case "$_shared_stop_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_shared_stop_id}" -eq 32 ] || return 69
    case "$_shared_stop_page" in voice|strategies) ;; *) return 69 ;; esac
    preflight_shared_apply_journal common-apply || return 69
    shared_apply_require_tools || return 69
    shared_apply_bundle_service verify "$_shared_stop_id" || return 69
    _shared_stop_saved=$(shared_apply_native_config saved \
        "$_shared_stop_id" "$_shared_stop_page") || return 69
    _shared_stop_confirmed=$(printf "%s\n" "$_shared_stop_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _shared_stop_dir=$(shared_apply_workspace "$_shared_stop_id") || return 69
    [ -d "$_shared_stop_dir/release" ] && [ ! -L "$_shared_stop_dir/release" ] || return 69
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
    # Check the entire installed tree, not merely the managed IPFW manifest.
    atomic_verify_tree "$_shared_stop_dir/release" "$ACTIVE_DIR" || return 69
    _shared_stop_engine=0
    _shared_stop_monitor=0
    launcher_is_running "$CHILD_PIDFILE" && _shared_stop_engine=1
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _shared_stop_monitor=1
    if [ -n "$_shared_stop_failed_pid" ]; then
        # Exact old PID no longer runs. The monitor may still be delivering
        # the callback, but a healthy/replaced engine invalidates it.
        [ "$_shared_stop_engine" = 0 ] || return 69
    else
        [ "$_shared_stop_engine" = "$_shared_stop_monitor" ] || return 69
    fi
    # A missing PID file is not evidence of an empty engine inventory.
    # The same exact-binary census already protects common Apply.
    _apply_engine="$_shared_stop_engine"
    apply_runtime_attest_engine_inventory || return 69
    if [ "$_shared_stop_engine" = 0 ] && [ -z "$_shared_stop_failed_pid" ]; then
        # An already stopped common runtime is idempotent only with an
        # empty, independently verified plugin-owned kernel range.
        firewall_shared_runtime verify "$ACTIVE_DIR" - || return 69
        printf "native-common-stopped=%s\n" "$_shared_stop_id"
        return 0
    fi
    # Verify the exact installed owner BEFORE stopping its process.
    firewall_shared_runtime verify - "$ACTIVE_DIR" || return 69
    # supervisor_stop_one unlinks a PID file after signaling even if the
    # original process remains alive. Pin its exact old identity so Stop
    # cannot silently strand the monitor after losing its PID file.
    _shared_stop_old_monitor_pid=
    if [ "$_shared_stop_monitor" = 1 ]; then
        _shared_stop_old_monitor_pid=$(supervisor_pidfile_read "$SUPERVISOR_MONITOR_PIDFILE") || return 69
    fi
    supervisor_stop "$SUPERVISOR_DAEMON_PIDFILE" "$SUPERVISOR_MONITOR_PIDFILE" || return 70
    launcher_stop "$CHILD_PIDFILE" 5 || return 70
    if supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" ||
       launcher_is_running "$CHILD_PIDFILE" ||
       { [ -n "$_shared_stop_old_monitor_pid" ] &&
         common_process_matches "$_shared_stop_old_monitor_pid" "$SUPERVISOR_LOOP"; }; then
        return 70
    fi
    # Do not remove the firewall and announce STOP when another dvtws2
    # survived the PID-based stop (or appeared as an orphan).
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 70
    # Common IPFW transaction installs an empty rule set, then commits
    # removal only for objects attested to this precise common release.
    # Failure retains committed ownership; no blind rule/table sweep.
    firewall_shared_runtime install "$ACTIVE_DIR" - || return 70
    firewall_shared_runtime commit "$ACTIVE_DIR" - || return 70
    # COMMIT removed the reversible kernel stage; do not report successful
    # Stop if an old monitor survives, a child respawns, the installed
    # traffic/IPSET release drifts, or IPFW changes at this boundary.
    # No blind retry or fabricated rollback after the irreversible commit.
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 70
    atomic_verify_tree "$_shared_stop_dir/release" "$ACTIVE_DIR" || return 70
    if supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" ||
       launcher_is_running "$CHILD_PIDFILE" ||
       { [ -n "$_shared_stop_old_monitor_pid" ] &&
         common_process_matches "$_shared_stop_old_monitor_pid" "$SUPERVISOR_LOOP"; }; then
        common_error "native common Stop: process survived IPFW commit"
        return 70
    fi
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 70
    firewall_shared_runtime verify "$ACTIVE_DIR" - || return 70
    printf "native-common-stopped=%s\n" "$_shared_stop_id"
}
# Reapply the saved COMMON candidate after reboot, without changing Config.
# Every boot must prove the same completed journal, release and native saved
# model. The original apply_runtime code owns dvtws2, supervisor and IPFW.
# Only exact cold-kernel ENOPROTOOPT is eligible; no rules are removed.
shared_apply_ipfw_kernel_absent_service()
{
    _kldstat_bin="${SHARED_APPLY_KLDSTAT_BIN:-/sbin/kldstat}"
    _ipfw_bin="${SHARED_APPLY_IPFW_BIN:-/sbin/ipfw}"
    [ -x "$_kldstat_bin" ] && [ -x "$_ipfw_bin" ] || return 1
    "$_kldstat_bin" -q -m ipfw >/dev/null 2>&1
    _ipfw_absence_rc=$?
    [ "$_ipfw_absence_rc" -eq 1 ] || return 1
    "$_kldstat_bin" -q -m ipdivert >/dev/null 2>&1
    _ipdivert_absence_rc=$?
    [ "$_ipdivert_absence_rc" -eq 1 ] || return 1
    _absent_message=$(LC_ALL=C "$_ipfw_bin" -q list 2>&1)
    _absent_rc=$?
    [ "$_absent_rc" = 71 ] || return 1
    case "$_absent_message" in
        *"Protocol not available"*) return 0 ;;
        *) return 1 ;;
    esac
}

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
    preflight_shared_apply_journal common-apply || return 69
    shared_apply_bundle_service verify "$_shared_boot_id" || return 69
    _shared_boot_saved=$(shared_apply_native_config saved "$_shared_boot_id" "$_shared_boot_page") || return 69
    _shared_boot_mode=$(printf "%s\n" "$_shared_boot_saved" |
        shared_apply_json_field '.enabled | select(.=="0" or .=="1")') || return 69
    _shared_boot_check=$(printf "%s\n" "$_shared_boot_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _shared_boot_dir=$(shared_apply_workspace "$_shared_boot_id") || return 69
    [ -d "$_shared_boot_dir/release" ] &&
    [ ! -L "$_shared_boot_dir/release" ] || return 69
    # Start/reconfigure are idempotent when the sealed common engine is
    # already running. An unconditional activate() otherwise stops dvtws2,
    # swaps its release and rewrites IPFW on every ordinary 'start'.
    # This is an inspection only: an unknown process/kernel or mixed
    # supervisor state is never treated as a healthy previous owner.
    _shared_boot_engine=0
    _shared_boot_monitor=0
    launcher_is_running "$CHILD_PIDFILE" && _shared_boot_engine=1
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _shared_boot_monitor=1
    [ "$_shared_boot_engine" = "$_shared_boot_monitor" ] || return 69
    if [ "$_shared_boot_engine" = 1 ]; then
        [ "$_shared_boot_mode" = 1 ] || return 69
        [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
        atomic_verify_tree "$_shared_boot_dir/release" "$ACTIVE_DIR" || return 69
        # Reuse the authoritative non-mutating Apply probe for engine
        # census, mapped native argv and exact installed IPFW ownership.
        apply_runtime_probe "$_shared_boot_dir/release" 1 || return 69
        printf "native-common-boot=%s\n" "$_shared_boot_id"
        return 0
    fi
    # After verifying the sealed owner and absence of an engine/monitor,
    # FreeBSD may have no IPFW module loaded after a cold boot. First attest
    # that there are no untracked engines. Only then prepare native firewall
    # prerequisites under original FD9; the normal adapter still verifies
    # exact IPFW ownership before startup. No legacy fallback or reset.
    if shared_apply_ipfw_kernel_absent_service; then
        _apply_engine=0
        apply_runtime_attest_engine_inventory || return 69
        if [ "$_shared_boot_mode" = 0 ]; then
            printf "native-common-boot-stopped=%s\n" "$_shared_boot_id"
            return 0
        fi
        prepare_firewall_prerequisites || return 70
    fi

    # A partial failure is never a successful boot.
    apply_runtime_activate "$_shared_boot_dir/release" "$_shared_boot_mode" || return 70
    apply_runtime_commit || return 70
    # A successful IPFW commit is not a running service receipt. The
    # cold-boot path must meet the same post-COMMIT guarantee as normal
    # Voice/Strategies Apply: the installed profile/traffic.conf/IPSET
    # match the sealed release, the exact process census is correct, and
    # kernel rules are still owned. Check both global ON and OFF.
    _shared_boot_final_engine=0
    _shared_boot_final_monitor=0
    launcher_is_running "$CHILD_PIDFILE" && _shared_boot_final_engine=1
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _shared_boot_final_monitor=1
    if ! {
        [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] &&
        atomic_verify_tree "$_shared_boot_dir/release" "$ACTIVE_DIR" &&
        apply_runtime_probe "$_shared_boot_dir/release" "$_shared_boot_mode" &&
        [ "$_shared_boot_final_engine" = "$_shared_boot_mode" ] &&
        [ "$_shared_boot_final_monitor" = "$_shared_boot_mode" ]
    }; then
        # Config and committed IPFW have already changed. Do not claim
        # rollback or print a successful boot receipt after uncertain state.
        common_error "native common boot: committed runtime or IPFW not verified"
        return 70
    fi
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
    preflight_shared_apply_journal common-apply || return 69
    shared_apply_require_tools || return 69
    _shared_apply_id="$1"
    _shared_apply_page="$2"
    _shared_apply_root=$(shared_apply_workspace "$_shared_apply_id") || return 69
    [ -d "$_shared_apply_root/release" ] &&
    [ -f "$_shared_apply_root/candidate.xml" ] &&
    [ -f "$_shared_apply_root/plan.json" ] || return 69
    # These gates run before the first durable Apply record and mutate
    # neither Config nor runtime/IPFW. Report their exact bounded stage
    # instead of mislabelling them as uncertain post-activation results.
    if ! shared_apply_bundle_service verify "$_shared_apply_id"; then
        printf '%s\n' preflight-rejected=bundle-verify
        return 0
    fi
    _shared_apply_preview=$(shared_apply_native_config preflight \
        "$_shared_apply_id" "$_shared_apply_page") || {
        printf '%s\n' preflight-rejected=config-preflight
        return 0
    }
    _shared_apply_mode=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.enabled | select(.=="0" or .=="1")') || return 69
    _shared_apply_base=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.base | select(test("^[a-f0-9]{64}$"))') || return 69
    _shared_apply_candidate=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.candidate | select(test("^[a-f0-9]{64}$"))') || return 69
    _shared_apply_fields=$(printf "%s\n" "$_shared_apply_preview" |
        shared_apply_json_field '.fields | if length==0 then "-" else join(",") end') || return 69
    # Reject an active old/legacy owner, partial monitor, foreign IPFW, or
    # invalid candidate BEFORE any durable phase is recorded. This must be
    # purely read-only. The mutating activation repeats the exact probe.
    # A failed transition must not permanently poison the common journal
    # when no kernel or Config change has even been attempted.
    if ! apply_runtime_probe "$_shared_apply_root/release" "$_shared_apply_mode"; then
        printf '%s\n' preflight-rejected=runtime-preflight
        return 0
    fi
    # The journal records only a fixed operation identity and owned-fields
    # proof. It never contains private Config XML or untrusted shell strings.
    shared_apply_record_service prepared "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 69
    shared_apply_record_service activating "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 69
    if ! apply_runtime_activate "$_shared_apply_root/release" "$_shared_apply_mode" "$_shared_apply_id"; then
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
    # Independent post-activation proof for both Strategies and Voice Apply.
    # Reject dead/replaced engine, changed active tree or unexpected IPFW
    # BEFORE native Config::save. Never claim rollback on ambiguous drift.
    if ! apply_runtime_attest_activated; then
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
    # Native Config::save releases its own lock. Reacquire/read the saved
    # model before DISCARDING IPFW rollback stages. No Config XML writer is
    # introduced here: the same OPNsense worker handles the readback.
    _shared_apply_saved=$(shared_apply_native_config saved \
        "$_shared_apply_id" "$_shared_apply_page") || {
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    }
    if ! {
        _shared_apply_saved_result=$(printf "%s\n" "$_shared_apply_saved" | \
            shared_apply_json_field '.result | select(.=="committed")') &&
        _shared_apply_saved_digest=$(printf "%s\n" "$_shared_apply_saved" | \
            shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') &&
        _shared_apply_saved_mode=$(printf "%s\n" "$_shared_apply_saved" | \
            shared_apply_json_field '.enabled | select(.=="0" or .=="1")') &&
        [ "$_shared_apply_saved_result" = committed ] &&
        [ "$_shared_apply_saved_digest" = "$_shared_apply_candidate" ] &&
        [ "$_shared_apply_saved_mode" = "$_shared_apply_mode" ] &&
        apply_runtime_attest_activated
    }; then
        # A changed native Config, a dead common engine or foreign IPFW
        # AFTER save cannot be undone by merely restoring the old release.
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    if ! apply_runtime_commit; then
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    # COMMIT discarded the reversible IPFW stage. Only now can the final
    # exact installed state (not verify-staged) be inspected. A dead process,
    # changed traffic.conf/IPSET, or modified scoped rules after Config save
    # MUST NOT be reported to the GUI as a successful Apply.
    _shared_apply_final_engine=0
    _shared_apply_final_monitor=0
    launcher_is_running "$CHILD_PIDFILE" && _shared_apply_final_engine=1
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _shared_apply_final_monitor=1
    if ! {
        shared_apply_bundle_service verify "$_shared_apply_id" &&
        atomic_verify_tree "$_shared_apply_root/release" "$ACTIVE_DIR" &&
        apply_runtime_probe "$_shared_apply_root/release" "$_shared_apply_mode" &&
        [ "$_shared_apply_final_engine" = "$_shared_apply_mode" ] &&
        [ "$_shared_apply_final_monitor" = "$_shared_apply_mode" ]
    }; then
        # No rollback after IPFW COMMIT / native Config::save: retain the
        # durable transaction and force review instead of false success.
        shared_apply_record_service requires-review "$_shared_apply_id" "$_shared_apply_page" \
            "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || true
        return 70
    fi
    shared_apply_record_service committed "$_shared_apply_id" "$_shared_apply_page" \
        "$_shared_apply_base" "$_shared_apply_candidate" "$_shared_apply_fields" || return 70
    printf "applied-id=%s\n" "$_shared_apply_id"
}
# One indivisible FD9 entrypoint for the EXISTING Voice and Strategies
# Apply buttons: stage → installed native template → full release →
# seal → native Config/runtime/IPFW transaction, all under the same lock.
# Both operations still revalidate native Config and bundle content.
shared_apply_run_service()
{
    [ "$#" -eq 2 ] || return 64
    case "$1" in voice|strategies) ;; *) return 64 ;; esac
    _shared_run_page="$1"
    _shared_run_encoded="$2"
    [ -n "$_shared_run_encoded" ] || return 64
    preflight_shared_apply_journal common-apply || return 69
    _shared_run_report=$(shared_apply_build_service "$_shared_run_encoded") || return $?
    _shared_run_receipt=$(printf "%s\n" "$_shared_run_report" | tail -n 1)
    case "$_shared_run_receipt" in
        preflight-rejected=root-gate|preflight-rejected=bootstrap|preflight-rejected=model|preflight-rejected=decode|preflight-rejected=candidate|preflight-rejected=candidate-plan|preflight-rejected=candidate-validation|preflight-rejected=candidate-xml|preflight-rejected=candidate-size|preflight-rejected=workspace|preflight-rejected=render|preflight-rejected=runtime-build|preflight-rejected=seal)
            # Nothing reached shared_apply_execute_service: no Config save,
            # runtime handoff, IPFW mutation or durable operation was started.
            printf '%s\n' "$_shared_run_receipt"
            return 0
            ;;
        prepared-id=*) ;;
        *) return 69 ;;
    esac
    _shared_run_id="${_shared_run_receipt#prepared-id=}"
    case "$_shared_run_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_shared_run_id}" -eq 32 ] || return 69
    # The root PHP worker verifies plan.page against the requested page
    # BEFORE checking the candidate snapshot, and again before Config::save.
    shared_apply_execute_service "$_shared_run_id" "$_shared_run_page"
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
    preflight_shared_apply_journal common-apply || return 69
    [ -x /usr/local/bin/php ] || return 69
    _shared_stage_result=$(/usr/local/bin/php \
        "${SCRIPT_DIR}/shared_apply_request.php" stage "$1") || return 69
    case "$_shared_stage_result" in
        prepared-id=*) _shared_stage_id="${_shared_stage_result#prepared-id=}" ;;
        preflight-rejected=root-gate|preflight-rejected=bootstrap|preflight-rejected=model|preflight-rejected=decode|preflight-rejected=candidate|preflight-rejected=candidate-plan|preflight-rejected=candidate-validation|preflight-rejected=candidate-xml|preflight-rejected=candidate-size|preflight-rejected=workspace)
            printf '%s\n' "$_shared_stage_result"
            return 0
            ;;
        *) return 69 ;;
    esac
    case "$_shared_stage_id" in
        *[!a-f0-9]*|"") return 69 ;;
    esac
    [ "${#_shared_stage_id}" -eq 32 ] || return 69
    _shared_build_result=$(shared_apply_prepare_service "$_shared_stage_id") || return $?
    _shared_build_last=$(printf '%s\n' "$_shared_build_result" | tail -n 1)
    case "$_shared_build_last" in
        preflight-rejected=render|preflight-rejected=runtime-build|preflight-rejected=seal)
            printf '%s\n' "$_shared_build_last"
            return 0
            ;;
    esac
    printf "prepared-id=%s\n" "$_shared_stage_id"
}
# Finalize only the public runtime root before sealing this private FD9 bundle.
# The parent shared-work directory, candidate.xml and plan remain root-only.
shared_apply_finalize_release_modes()
{
    [ "$#" -eq 1 ] || return 64
    [ -d "$1" ] && [ ! -L "$1" ] || return 69
    common_set_directory_mode "$1" 0755 || return 69
    validator_validate_runtime_modes "$1" || return 69
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
    preflight_shared_apply_journal common-apply || return 69
    [ -x /usr/local/bin/python3.13 ] || return 69
    _shared_work="/var/db/zapret2/shared-work/$1"
    [ -d "$_shared_work" ] && [ ! -L "$_shared_work" ] || return 69
    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_render.py" render "$1" || {
        printf '%s\n' preflight-rejected=render
        return 0
    }
    _shared_template="$_shared_work/templates/usr/local/etc/zapret2/zapret.conf"
    [ -f "$_shared_template" ] && [ ! -L "$_shared_template" ] || return 69
    orchestrator_build_release \
        "$_shared_template" "$ZAPRET_DIR" "$ACTIVE_DIR" \
        "$_shared_work" "$_shared_work/release" "$STAGE_FILE" \
        shared-candidate "$_shared_work/candidate.xml" || {
        printf '%s\n' preflight-rejected=runtime-build
        return 0
    }
    # Normal Start/Reconfigure make their release 0755 before activation.
    # The native shared candidate needs the same normalization BEFORE SEAL.
    shared_apply_finalize_release_modes "$_shared_work/release" || {
        printf '%s\n' preflight-rejected=runtime-build
        return 0
    }
    shared_apply_bundle_service seal "$1" || {
        printf '%s\n' preflight-rejected=seal
        return 0
    }
}
# Original common owner is defined by the one shared Apply journal. Before
# Remove Stop, independently attest saved Config, sealed release, exact active
# tree, processes and managed IPFW. Observation only under the inherited FD9.
extra_resources_native_previous_owner_service()
{
    [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] || return 75
    preflight_shared_apply_journal strategy-lab-native || return 69
    _extra_owner_line=$(/usr/local/bin/python3.13 \
        "${BACKEND_DIR}/shared_apply_operation.py" owner-witness) || return 69
    set -- $_extra_owner_line
    [ "$#" -eq 4 ] && [ "$1" = owner-witness ] || return 69
    _extra_old_id="$2"
    _extra_old_page="$3"
    _extra_old_digest="$4"
    case "$_extra_old_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_extra_old_id}" -eq 32 ] || return 69
    case "$_extra_old_page" in strategies|voice) ;; *) return 69 ;; esac
    case "$_extra_old_digest" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_extra_old_digest}" -eq 64 ] || return 69
    [ "$_extra_owner_line" = "owner-witness $_extra_old_id $_extra_old_page $_extra_old_digest" ] || return 69
    _extra_live_owner=$(shared_apply_inspect_service) || return 69
    [ "$_extra_live_owner" = "committed $_extra_old_id $_extra_old_page" ] || return 69
    shared_apply_bundle_service verify "$_extra_old_id" || return 69
    _extra_old_saved=$(shared_apply_native_config saved \
        "$_extra_old_id" "$_extra_old_page") || return 69
    _extra_old_result=$(printf '%s\n' "$_extra_old_saved" | \
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _extra_old_mode=$(printf '%s\n' "$_extra_old_saved" | \
        shared_apply_json_field '.enabled | select(.=="1")') || return 69
    _extra_old_snapshot=$(printf '%s\n' "$_extra_old_saved" | \
        shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') || return 69
    [ "$_extra_old_result" = committed ] &&
    [ "$_extra_old_mode" = 1 ] &&
    [ "$_extra_old_snapshot" = "$_extra_old_digest" ] || return 69
    _extra_old_work=$(shared_apply_workspace "$_extra_old_id") || return 69
    [ -d "$_extra_old_work/release" ] &&
    [ ! -L "$_extra_old_work/release" ] &&
    [ -d "$ACTIVE_DIR" ] &&
    [ ! -L "$ACTIVE_DIR" ] || return 69
    atomic_verify_tree "$_extra_old_work/release" "$ACTIVE_DIR" || return 69
    apply_runtime_probe "$_extra_old_work/release" 1 || return 69
    _extra_old_status=$(shared_apply_status_observe_service) || return 69
    [ "$_extra_old_status" = ready ] || return 69
    printf 'native-owner=%s:%s:%s\n' "$_extra_old_id" "$_extra_old_page" "$_extra_old_digest"
}

# Internal staging seam for Remove Additional Resources. This uses the
# SAME PHP native saved-Config planner and common GUI candidate compiler
# as ordinary Strategies/Voice Apply. No alternate placeholder resolution,
# engine start, Config save, or private activation machinery.
extra_resources_native_build_saved_service()
{
    [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] &&
    [ "${EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL:-0}" = 1 ] || return 75
    preflight_shared_apply_journal common-apply || return 69
    [ -x /usr/local/bin/php ] || return 69
    _extra_saved_report=$(/usr/local/bin/php \
        "${SCRIPT_DIR}/shared_apply_request.php" saved-unchanged) || return 69
    case "$_extra_saved_report" in
        prepared-id=*) _extra_saved_id="${_extra_saved_report#prepared-id=}" ;;
        *) return 69 ;;
    esac
    case "$_extra_saved_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_extra_saved_id}" -eq 32 ] || return 69
    _extra_build_report=$(shared_apply_prepare_service "$_extra_saved_id") || return $?
    _extra_build_last=$(printf '%s\n' "$_extra_build_report" | tail -n 1)
    case "$_extra_build_last" in preflight-rejected=*) return 69 ;; esac
    shared_apply_bundle_service verify "$_extra_saved_id" || return 69
    _extra_saved_preflight=$(shared_apply_native_config preflight \
        "$_extra_saved_id" strategies) || return 69
    _extra_saved_fields=$(printf '%s\n' "$_extra_saved_preflight" | \
        shared_apply_json_field '.changes | select(.==0)') || return 69
    _extra_saved_mode=$(printf '%s\n' "$_extra_saved_preflight" | \
        shared_apply_json_field '.enabled | select(.=="1")') || return 69
    [ "$_extra_saved_fields" = 0 ] && [ "$_extra_saved_mode" = 1 ] || return 69
    printf 'prepared-id=%s\n' "$_extra_saved_id"
}

# Restore the original sealed, STOPPED common runtime after a pre-commit
# trial failure. Parent transaction must restore original Lua/BIN bytes and
# restart the old owner only after this returns. Never report restoration
# merely because apply_runtime_restore() returned success.
extra_resources_native_trial_abort_service()
{
    [ "$#" -eq 1 ] || return 64
    _extra_trial_failure="$1"
    if [ "${APPLY_PHASE:-idle}" != idle ]; then
        if ! apply_runtime_restore; then
            common_error "RESTORE_FAILED: native trial runtime rollback: $_extra_trial_failure"
            return 70
        fi
    fi
    if ! {
        shared_apply_bundle_service verify "$_extra_trial_old_id" &&
        atomic_verify_tree "$_extra_trial_old_release" "$ACTIVE_DIR" &&
        ! launcher_is_running "$CHILD_PIDFILE" &&
        ! supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" &&
        _apply_engine=0 &&
        apply_runtime_attest_engine_inventory &&
        firewall_shared_runtime verify "$_extra_trial_old_release" - &&
        shared_apply_record_service restored "$_extra_trial_id" strategies \
            "$_extra_trial_base" "$_extra_trial_candidate" -
    }; then
        shared_apply_record_service requires-review "$_extra_trial_id" strategies \
            "$_extra_trial_base" "$_extra_trial_candidate" - || true
        common_error "RESTORE_FAILED: native trial cannot prove original stopped owner"
        return 70
    fi
    common_error "native trial rejected: $_extra_trial_failure; original stopped common owner restored"
    return 69
}

# Actual Remove startup: run the SAME original saved Config candidate compiler,
# native Apply journal, apply_runtime actuator and full process/IPFW probes.
# The resource transaction has ALREADY stopped the old service and quarantined
# extras under setup.lock -> original inherited FD9. A Config save is NEVER
# necessary/allowed: both full snapshots and all changed fields are identical.
extra_resources_native_trial_service()
{
    [ "$#" -eq 0 ] || return 64
    [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] &&
    [ "${EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL:-0}" = 1 ] || return 75
    preflight_shared_apply_journal common-apply || return 69
    shared_apply_require_tools || return 69
    _extra_trial_context=$(/usr/local/bin/python3.13 \
        "${BACKEND_DIR}/shared_apply_operation.py" remove-trial-context) || return 69
    set -- $_extra_trial_context
    [ "$#" -eq 4 ] && [ "$1" = remove-trial-owner ] || return 69
    _extra_trial_old_id="$2"
    _extra_trial_old_page="$3"
    _extra_trial_old_digest="$4"
    case "$_extra_trial_old_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_extra_trial_old_id}" -eq 32 ] || return 69
    case "$_extra_trial_old_page" in strategies|voice) ;; *) return 69 ;; esac
    case "$_extra_trial_old_digest" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_extra_trial_old_digest}" -eq 64 ] || return 69
    [ "$_extra_trial_context" = "remove-trial-owner $_extra_trial_old_id $_extra_trial_old_page $_extra_trial_old_digest" ] || return 69
    shared_apply_bundle_service verify "$_extra_trial_old_id" || return 69
    _extra_trial_old_saved=$(shared_apply_native_config saved \
        "$_extra_trial_old_id" "$_extra_trial_old_page") || return 69
    _extra_trial_old_mode=$(printf '%s\n' "$_extra_trial_old_saved" |
        shared_apply_json_field '.enabled | select(.=="1")') || return 69
    _extra_trial_old_result=$(printf '%s\n' "$_extra_trial_old_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _extra_trial_old_actual=$(printf '%s\n' "$_extra_trial_old_saved" |
        shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') || return 69
    [ "$_extra_trial_old_mode" = 1 ] &&
    [ "$_extra_trial_old_result" = committed ] &&
    [ "$_extra_trial_old_actual" = "$_extra_trial_old_digest" ] || return 69
    _extra_trial_old_work=$(shared_apply_workspace "$_extra_trial_old_id") || return 69
    _extra_trial_old_release="$_extra_trial_old_work/release"
    [ -d "$_extra_trial_old_release" ] &&
    [ ! -L "$_extra_trial_old_release" ] &&
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
    atomic_verify_tree "$_extra_trial_old_release" "$ACTIVE_DIR" || return 69
    # Parent Stop must have retired the original process and managed IPFW.
    ! launcher_is_running "$CHILD_PIDFILE" &&
    ! supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" || return 69
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 69
    firewall_shared_runtime verify "$_extra_trial_old_release" - || return 69

    _extra_trial_build=$(extra_resources_native_build_saved_service) || return 69
    case "$_extra_trial_build" in prepared-id=*) ;; *) return 69 ;; esac
    _extra_trial_id="${_extra_trial_build#prepared-id=}"
    case "$_extra_trial_id" in ""|*[!a-f0-9]*) return 69 ;; esac
    [ "${#_extra_trial_id}" -eq 32 ] &&
    [ "$_extra_trial_id" != "$_extra_trial_old_id" ] || return 69
    _extra_trial_root=$(shared_apply_workspace "$_extra_trial_id") || return 69
    [ -d "$_extra_trial_root/release" ] &&
    [ ! -L "$_extra_trial_root/release" ] || return 69
    shared_apply_bundle_service verify "$_extra_trial_id" || return 69
    _extra_trial_preview=$(shared_apply_native_config preflight \
        "$_extra_trial_id" strategies) || return 69
    _extra_trial_base=$(printf '%s\n' "$_extra_trial_preview" |
        shared_apply_json_field '.base | select(test("^[a-f0-9]{64}$"))') || return 69
    _extra_trial_candidate=$(printf '%s\n' "$_extra_trial_preview" |
        shared_apply_json_field '.candidate | select(test("^[a-f0-9]{64}$"))') || return 69
    _extra_trial_changes=$(printf '%s\n' "$_extra_trial_preview" |
        shared_apply_json_field '.changes | select(.==0)') || return 69
    _extra_trial_fields=$(printf '%s\n' "$_extra_trial_preview" |
        shared_apply_json_field '.fields | select(length==0) | length') || return 69
    _extra_trial_mode=$(printf '%s\n' "$_extra_trial_preview" |
        shared_apply_json_field '.enabled | select(.=="1")') || return 69
    [ "$_extra_trial_base" = "$_extra_trial_old_digest" ] &&
    [ "$_extra_trial_candidate" = "$_extra_trial_old_digest" ] &&
    [ "$_extra_trial_changes" = 0 ] &&
    [ "$_extra_trial_fields" = 0 ] &&
    [ "$_extra_trial_mode" = 1 ] || return 69
    apply_runtime_probe "$_extra_trial_root/release" 1 || return 69
    # Only the original Apply's single durable journal can own new dvtws2.
    shared_apply_record_service prepared "$_extra_trial_id" strategies \
        "$_extra_trial_base" "$_extra_trial_candidate" - || return 69
    if ! shared_apply_record_service activating "$_extra_trial_id" strategies \
        "$_extra_trial_base" "$_extra_trial_candidate" -; then
        shared_apply_record_service restored "$_extra_trial_id" strategies \
            "$_extra_trial_base" "$_extra_trial_candidate" - || return 70
        return 69
    fi
    if ! apply_runtime_activate "$_extra_trial_root/release" 1 "$_extra_trial_id"; then
        extra_resources_native_trial_abort_service activation
        return $?
    fi
    if ! shared_apply_record_service activated "$_extra_trial_id" strategies \
        "$_extra_trial_base" "$_extra_trial_candidate" -; then
        extra_resources_native_trial_abort_service journal-activated
        return $?
    fi
    if ! {
        shared_apply_bundle_service verify "$_extra_trial_id" &&
        apply_runtime_attest_activated
    }; then
        extra_resources_native_trial_abort_service activated-witness
        return $?
    fi
    _extra_trial_saved=$(shared_apply_native_config saved \
        "$_extra_trial_id" strategies) || {
        extra_resources_native_trial_abort_service saved-config-readback
        return $?
    }
    _extra_trial_saved_result=$(printf '%s\n' "$_extra_trial_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || {
        extra_resources_native_trial_abort_service saved-result
        return $?
    }
    _extra_trial_saved_hash=$(printf '%s\n' "$_extra_trial_saved" |
        shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') || {
        extra_resources_native_trial_abort_service saved-digest
        return $?
    }
    _extra_trial_saved_mode=$(printf '%s\n' "$_extra_trial_saved" |
        shared_apply_json_field '.enabled | select(.=="1")') || {
        extra_resources_native_trial_abort_service saved-mode
        return $?
    }
    if ! {
        [ "$_extra_trial_saved_result" = committed ] &&
        [ "$_extra_trial_saved_hash" = "$_extra_trial_old_digest" ] &&
        [ "$_extra_trial_saved_mode" = 1 ] &&
        apply_runtime_attest_activated
    }; then
        extra_resources_native_trial_abort_service native-config-drift
        return $?
    fi
    # Config was already persisted and unchanged before the trial. This
    # phase records that attested fact, NOT a second native Config::save.
    shared_apply_record_service config-saved "$_extra_trial_id" strategies \
        "$_extra_trial_base" "$_extra_trial_candidate" - || return 70
    apply_runtime_commit || return 70
    _extra_trial_final_engine=0
    _extra_trial_final_monitor=0
    launcher_is_running "$CHILD_PIDFILE" && _extra_trial_final_engine=1
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _extra_trial_final_monitor=1
    if ! {
        shared_apply_bundle_service verify "$_extra_trial_id" &&
        atomic_verify_tree "$_extra_trial_root/release" "$ACTIVE_DIR" &&
        apply_runtime_probe "$_extra_trial_root/release" 1 &&
        [ "$_extra_trial_final_engine" = 1 ] &&
        [ "$_extra_trial_final_monitor" = 1 ]
    }; then
        common_error "RESTORE_FAILED: committed native trial state not attested"
        return 70
    fi
    shared_apply_record_service committed "$_extra_trial_id" strategies \
        "$_extra_trial_base" "$_extra_trial_candidate" - || return 70
    _extra_trial_status=$(shared_apply_status_observe_service) || return 70
    [ "$_extra_trial_status" = ready ] || return 70
    printf 'native-remove-applied=%s\n' "$_extra_trial_id"
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

# Native committed owners need the existing read-only full-runtime/IPFW
# witness, never legacy PID-plus-any-divert status.

# Restore ONLY the previous saved common owner pinned in the existing
# resource and shared Apply journals. Called after the original extra Lua/BIN
# bytes are back; never recompile or invent any Strategies/Voice arguments.
# The SAME native apply_runtime actuator performs a committed new->old
# transition, while the original shared journal returns to its predecessor.
extra_resources_native_restore_previous_service()
{
    [ "$#" -eq 3 ] || return 64
    [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] &&
    [ "${EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE:-0}" = 1 ] || return 75
    shared_apply_require_tools || return 69
    _extra_restore_id="$1"
    _extra_restore_page="$2"
    _extra_restore_hash="$3"
    case "$_extra_restore_id" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#_extra_restore_id}" -eq 32 ] || return 64
    case "$_extra_restore_page" in strategies|voice) ;; *) return 64 ;; esac
    case "$_extra_restore_hash" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#_extra_restore_hash}" -eq 64 ] || return 64
    # This CLI checks exact old witness in the original fsynced resource
    # journal and the existing committed/restored shared Apply predecessor.
    _extra_pair=$(/usr/local/bin/python3.13 \
        "${BACKEND_DIR}/shared_apply_operation.py" remove-rollback-pair) || return 69
    set -- $_extra_pair
    [ "$#" -eq 6 ] && [ "$1" = remove-rollback ] || return 69
    _extra_restore_state="$2"
    [ "$3" = "$_extra_restore_id" ] &&
    [ "$4" = "$_extra_restore_page" ] &&
    [ "$5" = "$_extra_restore_hash" ] || return 69
    _extra_trial_id="$6"
    case "$_extra_restore_state:$_extra_trial_id" in
        old:-) ;;
        trial:*) case "$_extra_trial_id" in ""|-|*[!a-f0-9]*) return 69 ;; esac
                 [ "${#_extra_trial_id}" -eq 32 ] || return 69 ;;
        *) return 69 ;;
    esac
    shared_apply_bundle_service verify "$_extra_restore_id" || return 69
    _extra_restore_saved=$(shared_apply_native_config saved \
        "$_extra_restore_id" "$_extra_restore_page") || return 69
    _extra_restore_ok=$(printf '%s\n' "$_extra_restore_saved" |
        shared_apply_json_field '.result | select(.=="committed")') || return 69
    _extra_restore_mode=$(printf '%s\n' "$_extra_restore_saved" |
        shared_apply_json_field '.enabled | select(.=="1")') || return 69
    _extra_restore_digest=$(printf '%s\n' "$_extra_restore_saved" |
        shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') || return 69
    [ "$_extra_restore_ok" = committed ] &&
    [ "$_extra_restore_mode" = 1 ] &&
    [ "$_extra_restore_digest" = "$_extra_restore_hash" ] || return 69
    _extra_restore_work=$(shared_apply_workspace "$_extra_restore_id") || return 69
    [ -d "$_extra_restore_work/release" ] &&
    [ ! -L "$_extra_restore_work/release" ] || return 69
    if [ "$_extra_restore_state" = old ]; then
        # No committed trial took ownership. Only the exact previous sealed
        # active tree may be brought back using the normal common boot path.
        [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
        atomic_verify_tree "$_extra_restore_work/release" "$ACTIVE_DIR" || return 69
        shared_apply_boot_service "committed $_extra_restore_id $_extra_restore_page" || return 70
    else
        # A completed trial may already have stopped. Verify its exact
        # release BEFORE the existing actuator touches processes or IPFW.
        shared_apply_bundle_service verify "$_extra_trial_id" || return 69
        _extra_trial_work=$(shared_apply_workspace "$_extra_trial_id") || return 69
        [ -d "$_extra_trial_work/release" ] &&
        [ ! -L "$_extra_trial_work/release" ] &&
        [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
        atomic_verify_tree "$_extra_trial_work/release" "$ACTIVE_DIR" || return 69
        apply_runtime_activate "$_extra_restore_work/release" 1 || return 70
        apply_runtime_attest_activated || return 70
        shared_apply_bundle_service verify "$_extra_restore_id" || return 70
        _extra_restore_again=$(shared_apply_native_config saved \
            "$_extra_restore_id" "$_extra_restore_page") || return 70
        _extra_restore_again_digest=$(printf '%s\n' "$_extra_restore_again" |
            shared_apply_json_field '.snapshot | select(test("^[a-f0-9]{64}$"))') || return 70
        [ "$_extra_restore_again_digest" = "$_extra_restore_hash" ] || return 70
        apply_runtime_commit || return 70
        # This independent post-commit proof is required BEFORE the one
        # journal is atomically reverted. No other config or owner writer.
        atomic_verify_tree "$_extra_restore_work/release" "$ACTIVE_DIR" || return 70
        apply_runtime_probe "$_extra_restore_work/release" 1 || return 70
        /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \
            remove-revert-committed "$_extra_trial_id" "$_extra_restore_id" || return 70
    fi
    shared_apply_bundle_service verify "$_extra_restore_id" || return 70
    atomic_verify_tree "$_extra_restore_work/release" "$ACTIVE_DIR" || return 70
    apply_runtime_probe "$_extra_restore_work/release" 1 || return 70
    _extra_restored_state=$(shared_apply_status_observe_service) || return 70
    [ "$_extra_restored_state" = ready ] || return 70
    printf 'native-owner-restored=%s\n' "$_extra_restore_id"
}

# Explicit operator-only closure of the FIRST failed Voice handoff.
# No Config, IPFW or engine restart; only the missing monitor is reattached
# and only after all old ownership has been attested under original root FD9.
shared_apply_reviewed_legacy_attest_service()
{
    [ "$#" -eq 4 ] || return 64
    _review_id="$1"
    _review_base="$2"
    _review_candidate="$3"
    _review_monitor="$4"
    case "$_review_monitor" in 0|1) ;; *) return 64 ;; esac

    shared_apply_bundle_service verify "$_review_id" || return 69
    # Native mergeForCommit revalidates the LIVE Config dependency snapshot.
    _review_config=$(shared_apply_native_config preflight "$_review_id" voice) || return 69
    _review_config_base=$(printf '%s\n' "$_review_config" |
        shared_apply_json_field '.base | select(test("^[a-f0-9]{64}$"))') || return 69
    _review_config_candidate=$(printf '%s\n' "$_review_config" |
        shared_apply_json_field '.candidate | select(test("^[a-f0-9]{64}$"))') || return 69
    [ "$_review_config_base" = "$_review_base" ] &&
    [ "$_review_config_candidate" = "$_review_candidate" ] || return 69

    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] &&
    [ ! -e "$ACTIVE_DIR/voice-plan.json" ] &&
    [ ! -L "$ACTIVE_DIR/voice-plan.json" ] || return 69
    _review_stage="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").stage.$_review_id"
    _review_park="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").old.$_review_id"
    _review_backup="$BACKUP_ROOT/$(basename "$ACTIVE_DIR")-$_review_id"
    for _review_artifact in "$_review_stage" "$_review_park" "$_review_backup"; do
        [ ! -e "$_review_artifact" ] && [ ! -L "$_review_artifact" ] || return 69
    done
    # Verify the exact old-owned Strategies rules from the root-owned old
    # runtime artifacts, WAN of sealed candidate, and all ten absent tables.
    _review_work=$(shared_apply_workspace "$_review_id") || return 69
    firewall_shared_runtime verify-legacy "$ACTIVE_DIR" "$_review_work/release" || return 69
    launcher_is_running "$CHILD_PIDFILE" || return 69
    _apply_engine=1
    apply_runtime_attest_engine_inventory || return 69

    _review_processes=$("$COMMON_PS_BIN" ax -o pid= -o command=) || return 69
    _review_loop_pids=$(printf '%s\n' "$_review_processes" | awk -v target="$SUPERVISOR_LOOP" '
        $1 ~ /^[0-9]+$/ &&
        ($2 == target || (($2 == "/bin/sh" || $2 == "sh") && $3 == target)) {
            print $1
        }') || return 69
    if [ "$_review_monitor" = 1 ]; then
        supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" || return 69
        _review_supervisor_pid=$(supervisor_pidfile_read "$SUPERVISOR_MONITOR_PIDFILE") || return 69
        [ "$_review_loop_pids" = "$_review_supervisor_pid" ] || return 69
    else
        supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && return 69
        [ -z "$_review_loop_pids" ] &&
        [ ! -e "$SUPERVISOR_MONITOR_PIDFILE" ] &&
        [ ! -L "$SUPERVISOR_MONITOR_PIDFILE" ] &&
        [ ! -e "$SUPERVISOR_DAEMON_PIDFILE" ] &&
        [ ! -L "$SUPERVISOR_DAEMON_PIDFILE" ] || return 69
    fi
}

shared_apply_recover_reviewed_legacy_service()
{
    [ "$#" -eq 0 ] || return 64
    preflight_shared_apply_journal common-recover-reviewed-legacy || return 69
    _review_identity=$(/usr/local/bin/python3.13 \
        "$BACKEND_DIR/shared_apply_operation.py" review-legacy) || return 69
    set -- $_review_identity
    [ "$#" -eq 4 ] && [ "$1" = review-legacy ] || return 69
    _review_id="$2"
    _review_base="$3"
    _review_candidate="$4"
    _review_has_monitor=0
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _review_has_monitor=1
    shared_apply_reviewed_legacy_attest_service "$_review_id" \
        "$_review_base" "$_review_candidate" "$_review_has_monitor" || return 70
    if [ "$_review_has_monitor" = 0 ]; then
        supervisor_start "$SUPERVISOR_LOOP" "$SUPERVISOR_DAEMON_PIDFILE" \
            "$SUPERVISOR_MONITOR_PIDFILE" "$CHILD_PIDFILE" \
            "$SERVICE_SCRIPT" "$DVTWS_BIN" "$SUPERVISOR_LOG" || return 70
    fi
    shared_apply_reviewed_legacy_attest_service "$_review_id" \
        "$_review_base" "$_review_candidate" 1 || return 70
    # Root FD9 CLI rechecks sealed bundle, operation ID and phase.
    /usr/local/bin/python3.13 "$BACKEND_DIR/shared_apply_operation.py" \
        finish-reviewed-legacy "$_review_id" || return 70
    printf 'reviewed-legacy-restored=%s\n' "$_review_id"
}

shared_apply_status_observe_service()
{
    _status_python=/usr/local/bin/python3.13
    _status_inspector="${BACKEND_DIR}/voice_live_inspect.py"
    [ -x "$_status_python" ] && [ -r "$_status_inspector" ] || return 69
    if _status_json=$("$_status_python" "$_status_inspector" 2>/dev/null); then
        _status_rc=0
    else
        _status_rc=$?
    fi
    case "$_status_rc" in 0|2) ;; *) return 69 ;; esac
    _status_state=$(printf '%s\n' "$_status_json" | "$_status_python" -c '
import json, sys
try:
    x = json.load(sys.stdin)
except (TypeError, ValueError):
    sys.exit(69)
if not isinstance(x, dict) or x.get("source") != "native-common":
    sys.exit(69)
s = x.get("state")
if s not in ("ready", "stopped"):
    sys.exit(69)
print(s)
' 2>/dev/null) || return 69
    case "$_status_state:$_status_rc" in
        ready:0|stopped:2) printf '%s\n' "$_status_state" ;;
        *) return 69 ;;
    esac
}

shared_apply_status_service()
{
    if shared_apply_has_record_service; then
        _status_owner=$(shared_apply_inspect_service) || {
            echo "zapret is in an incomplete runtime state"
            return 2
        }
        case "$_status_owner" in
            committed\ *)
                _status_verified=$(shared_apply_status_observe_service) || {
                    echo "zapret is in an incomplete runtime state"
                    return 2
                }
                case "$_status_verified" in
                    ready) echo "zapret is running"; return 0 ;;
                    stopped) echo "zapret is not running"; return 1 ;;
                    *) echo "zapret is in an incomplete runtime state"; return 2 ;;
                esac
                ;;
            none|restored) ;;
            *) echo "zapret is in an incomplete runtime state"; return 2 ;;
        esac
    fi
    if [ -e "$ACTIVE_DIR/voice-plan.json" ] ||
       [ -L "$ACTIVE_DIR/voice-plan.json" ]; then
        echo "zapret is in an incomplete runtime state"
        return 2
    fi
    orchestrator_native_status \
        "$CHILD_PIDFILE" "$SUPERVISOR_MONITOR_PIDFILE" \
        "$RULE_BASE" "$RULE_MAX" "$ACTIVE_DIR"
}

# The historical configctl names now select Telegram in the SAME native
# shared Apply transaction, under the ORIGINAL caller's FD9. The root PHP
# request worker loads locked Config and preserves all other Voice fields.
telegram_voice_compat_apply_service()
{
    [ "$#" -eq 1 ] || return 64
    case "$1" in enable|disable) ;; *) return 64 ;; esac
    preflight_shared_apply_journal common-apply || return 69
    shared_apply_require_tools || return 69
    # Always forget the previous shell invocation's shared owner first.
    _compat_owner=
    if shared_apply_has_record_service; then
        _compat_owner=$(shared_apply_inspect_service) || return 69
        case "$_compat_owner" in committed\ *|none|restored) ;; *) return 69 ;; esac
    fi
    if [ -e "$ACTIVE_DIR/voice-plan.json" ] ||
       [ -L "$ACTIVE_DIR/voice-plan.json" ]; then
        case "${_compat_owner:-}" in committed\ *) ;; *) return 69 ;; esac
    fi
    _compat_encoded=$(/usr/local/bin/php \
        "$SCRIPT_DIR/shared_apply_request.php" telegram-envelope "$1") || return 69
    case "$_compat_encoded" in ""|*[!A-Za-z0-9_-]*) return 69 ;; esac
    shared_apply_run_service voice "$_compat_encoded"
}

# Preserve the old key names while reporting the *real*, already-sealed
# native Telegram profile. Read-only Config preference and runtime witness
# must agree bit-for-bit before this command may claim effective=on.
telegram_voice_native_status_service()
{
    shared_apply_require_tools || return 2
    [ -x /usr/local/bin/python3.13 ] || return 2
    _compat_saved=$(/usr/local/bin/php \
        "$SCRIPT_DIR/shared_apply_request.php" telegram-saved) || return 2
    _compat_requested=$(printf '%s\n' "$_compat_saved" |
        shared_apply_json_field '.requested|select(.=="on" or .=="off")') || return 2
    _compat_digest=$(printf '%s\n' "$_compat_saved" |
        shared_apply_json_field '.snapshot|select(test("^[a-f0-9]{64}$"))') || return 2
    if _compat_report=$(/usr/local/bin/python3.13 \
        "$BACKEND_DIR/voice_live_inspect.py" 2>/dev/null); then
        _compat_rc=0
    else
        _compat_rc=$?
    fi
    case "$_compat_rc" in 0|2) ;; *) return 2 ;; esac
    _compat_state=$(printf '%s\n' "$_compat_report" |
        shared_apply_json_field '.state|select(.=="ready" or .=="stopped")') || return 2
    _compat_source=$(printf '%s\n' "$_compat_report" |
        shared_apply_json_field '.source|select(.=="native-common")') || return 2
    _compat_runtime_digest=$(printf '%s\n' "$_compat_report" |
        shared_apply_json_field '.config_digest|select(test("^[a-f0-9]{64}$"))') || return 2
    [ "$_compat_digest" = "$_compat_runtime_digest" ] || return 2
    case "$_compat_state:$_compat_rc" in ready:0|stopped:2) ;; *) return 2 ;; esac
    _compat_profile=$(printf '%s\n' "$_compat_report" |
        shared_apply_json_field '
            if .runtime.services.telegram.configured == true then "on"
            elif .runtime.services.telegram.configured == false then "off"
            else empty end') || return 2
    [ "$_compat_requested" = "$_compat_profile" ] || return 2
    _compat_revision=none
    _compat_ports=none
    _compat_wan=none
    _compat_entries=0
    _compat_rule=unavailable
    _compat_rule_packets=unavailable
    _compat_rule_bytes=unavailable
    if [ "$_compat_profile" = on ]; then
        _compat_revision=$(printf '%s\n' "$_compat_report" |
            shared_apply_json_field '.runtime.services.telegram.profile_revision|
                                     select(test("^[a-f0-9]{12}$"))') || return 2
        _compat_ports=$(printf '%s\n' "$_compat_report" |
            shared_apply_json_field '.runtime.services.telegram.udp_ports|
                                     select(test("^[0-9,-]+$"))') || return 2
        _compat_wan=$(printf '%s\n' "$_compat_report" |
            shared_apply_json_field '.runtime.services.telegram.wan|
                                     select(test("^[A-Za-z][A-Za-z0-9_.:-]{0,63}$"))') || return 2
        _compat_entries=$(printf '%s\n' "$_compat_report" |
            shared_apply_json_field '.runtime.services.telegram.ipset_entries|
                                     select(type=="number" and .>=1 and .<=4096)') || return 2
        if [ "$_compat_state" = ready ]; then
            _compat_rule=$(printf '%s\n' "$_compat_report" |
                shared_apply_json_field '.runtime.services.telegram.rule|
                                         select(type=="number" and .>=1 and .<=65534)') || return 2
            _compat_rule_packets=$(printf '%s\n' "$_compat_report" |
                shared_apply_json_field '.runtime.services.telegram.rule_packets|
                                         select(type=="number" and .>=0)' ||
                printf 'unavailable\n')
            _compat_rule_bytes=$(printf '%s\n' "$_compat_report" |
                shared_apply_json_field '.runtime.services.telegram.rule_bytes|
                                         select(type=="number" and .>=0)' ||
                printf 'unavailable\n')
        fi
    fi
    _compat_effective=off
    _compat_table_present=no
    _compat_table_entries=0
    _compat_service=stopped
    if [ "$_compat_state" = ready ]; then
        _compat_service=running
        if [ "$_compat_profile" = on ]; then
            _compat_effective=on
            _compat_table_present=yes
            _compat_table_entries=$_compat_entries
        fi
    fi
    printf '%s\n' \
        "telegram_voice_poc.requested=$_compat_requested" \
        "telegram_voice_poc.effective=$_compat_effective" \
        "telegram_voice_poc.service=$_compat_service" \
        "telegram_voice_poc.active_profile=$_compat_profile" \
        "telegram_voice_poc.strategy=voice-telegram@$_compat_revision" \
        "telegram_voice_poc.scope=$_compat_ports" \
        "telegram_voice_poc.table=zapret2_voice_telegram" \
        "telegram_voice_poc.table_present=$_compat_table_present" \
        "telegram_voice_poc.table_entries=$_compat_table_entries" \
        "telegram_voice_poc.stage_table=zapret2_voice_telegram_stage" \
        "telegram_voice_poc.stage_table_present=no" \
        "telegram_voice_poc.rule=$_compat_rule" \
        "telegram_voice_poc.rule_packets=$_compat_rule_packets" \
        "telegram_voice_poc.rule_bytes=$_compat_rule_bytes" \
        "telegram_voice_poc.source=native-common" \
        "telegram_voice_poc.wan=$_compat_wan" \
        "telegram_voice_poc.udp_ports=$_compat_ports" \
        "telegram_voice_poc.profile_revision=$_compat_revision"
    if [ "$_compat_requested" = on ] && [ "$_compat_effective" != on ]; then
        return 2
    fi
    return 0
}

telegram_voice_compat_status_service()
{
    if shared_apply_has_record_service; then
        _compat_status_owner=$(shared_apply_inspect_service) || return 2
        case "$_compat_status_owner" in
            committed\ *) telegram_voice_native_status_service; return $? ;;
            none|restored) ;;
            *) echo "telegram_voice_poc.service=incomplete"; return 2 ;;
        esac
    fi
    if [ -e "$ACTIVE_DIR/voice-plan.json" ] ||
       [ -L "$ACTIVE_DIR/voice-plan.json" ]; then
        echo "telegram_voice_poc.service=incomplete"
        return 2
    fi
    # Native saved Config and shared Apply are the sole preference sources.
    telegram_voice_native_status_service
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
            shared_apply_status_service
            ;;
        telegram-voice-enable)
            telegram_voice_compat_apply_service enable
            ;;
        telegram-voice-disable)
            telegram_voice_compat_apply_service disable
            ;;
        telegram-voice-status)
            telegram_voice_compat_status_service
            ;;
        reconfigure)
            reconfigure_service
            ;;
        shared-apply-recover-reviewed-legacy)
            shared_apply_recover_reviewed_legacy_service
            ;;
        shared-apply-run)
            shared_apply_run_service "${2:-}" "${3:-}"
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
        extra-resources-preview-saved)
            extra_resources_preview_saved_service
            ;;
        extra-resources-remove-plan)
            [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] || return 75
            [ -r "${SCRIPT_DIR}/extra_resources_operation.py" ] || return 69
            STRATEGY_LAB_LIFECYCLE_OWNER=1
            export STRATEGY_LAB_LIFECYCLE_OWNER
            /usr/local/bin/python3.13 "${SCRIPT_DIR}/extra_resources_operation.py" plan
            ;;
        native-voice-lifecycle-inspect)
            native_voice_lifecycle_inspect_service
            ;;
        native-voice-candidate-preflight)
            native_voice_candidate_preflight_service
            ;;
        native-voice-preview-draft)
            native_voice_preview_draft_service "${2:-}" "${3:-}"
            ;;
        runtime-failure)
            orchestrator_runtime_failure \
                "${CHILD_PIDFILE}" \
                "${SUPERVISOR_DAEMON_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" \
                "${RULE_BASE}" "${RULE_MAX}" "${STAGE_FILE}" \
                "${2:-dvtws2 runtime failure}"
            ;;
        upstream-install)
            # Setup lock is acquired before the original FD9. The worker
            # inherits FD9 over all old/target bytes and native Stop/Start.
            [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] || return 75
            [ -x "${SCRIPT_DIR}/setup_transaction.sh" ] || return 69
            STRATEGY_LAB_LIFECYCLE_OWNER=1 UPSTREAM_RUNTIME_LIFECYCLE_OWNER=1 \
                "${SCRIPT_DIR}/setup_transaction.sh" install-under-native-lock "${2:-}"
            ;;
        upstream-recover-mutating)
            # setup_transaction acquired setup.lock first, and the native
            # service owns the original FD9. Never start a second firewall
            # implementation or hide a Stop inside the setup shell script.
            [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] || return 75
            [ -x "${SCRIPT_DIR}/setup_transaction.sh" ] || return 69
            STRATEGY_LAB_LIFECYCLE_OWNER=1 UPSTREAM_RECOVERY_LIFECYCLE_OWNER=1 \
                "${SCRIPT_DIR}/setup_transaction.sh" recover-mutating-under-parent-lock
            ;;
        extra-resources-install|extra-resources-recover)
            # Launcher owns setup.lock before acquiring original FD9.
            # Native lifecycle callbacks never acquire a second lock.
            [ "${EXTRA_RESOURCES_SETUP_LOCK_OWNER:-0}" = 1 ] || return 75
            [ -x /usr/local/bin/python3.13 ] || return 69
            [ -r "${SCRIPT_DIR}/extra_resources_operation.py" ] || return 69
            STRATEGY_LAB_LIFECYCLE_OWNER=1
            export STRATEGY_LAB_LIFECYCLE_OWNER
            case "$1" in
                extra-resources-install) _extra_mode=install ;;
                *) _extra_mode=recover ;;
            esac
            /usr/local/bin/python3.13 "${SCRIPT_DIR}/extra_resources_operation.py" "$_extra_mode"
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

# Before mutation the existing FD9 owner checks the ONE shared Apply journal.
# Historical Telegram PoC journals/markers are never consulted for runtime
# authority. Common recovery exceptions remain scoped to their exact phase.
preflight_shared_apply_journal()
{
    _shared_gate_script="${BACKEND_DIR}/shared_apply_operation.py"
    _shared_gate_python=/usr/local/bin/python3.13
    if [ ! -x "${_shared_gate_python}" ]; then
        case "${BACKEND_DIR}" in
            /usr/local/opnsense/scripts/OPNsense/Zapret/backend) ;;
            *) _shared_gate_python=$(command -v python3.13 2>/dev/null || true) ;;
        esac
    fi
    if [ ! -r "${_shared_gate_script}" ] ||
       [ -z "${_shared_gate_python}" ] ||
       [ ! -x "${_shared_gate_python}" ]; then
        echo "ERROR: shared Apply journal gate is unavailable" >&2
        return 69
    fi
    "${_shared_gate_python}" "${_shared_gate_script}" native-gate "$@"
}

# Fixed native journal locator (mockable only by isolated shell extraction).
# A live unclosed resource transaction and an ordinary start/reconfigure
# cannot share the engine/IPFW owner. This is only a FAIL-CLOSED observation,
# not a new lock and not a substitute for setup.lock -> original FD9 recovery.
extra_resources_block_pending_start_service()
{
    _extra_pending=/var/db/zapret2-restyle/extra-resources/transaction
    if [ -e "$_extra_pending" ] || [ -L "$_extra_pending" ]; then
        echo "ERROR: unresolved Additional Resources transaction blocks ordinary Start; recover it first" >&2
        return 69
    fi
    return 0
}
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
                extra_resources_block_pending_start_service || return 69
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
                        config-saved\ *)
                            # Cold recovery proves Config was persisted and
                            # the kernel contains NO active Zapret2 owner.
                            # Never invoke legacy start after native save.
                            shared_apply_recover_saved_service "$_shared_owner"
                            return $?
                            ;;
                        activated\ *)
                            shared_apply_recover_activated_cold_service "$_shared_owner" || return 69
                            _shared_owner=$(shared_apply_inspect_service) || return 69
                            case "$_shared_owner" in
                                committed\ *)
                                    shared_apply_boot_service "$_shared_owner"
                                    return $?
                                    ;;
                                *) return 69 ;;
                            esac
                            ;;
                        activating\ *)
                            # Two *exclusive* post-crash layouts: full old
                            # release unchanged, or full new release installed
                            # before the phase record reached ACTIVATED.
                            # Each path independently proves Config, owner,
                            # installed tree, process census and scoped IPFW.
                            if ! shared_apply_recover_activating_pristine_service "$_shared_owner"; then
                                if ! shared_apply_recover_activated_cold_service "$_shared_owner"; then
                                    shared_apply_recover_activating_parked_service "$_shared_owner" || return 69
                                fi
                            fi
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
                preflight_shared_apply_journal || return 69
                ;;
            stop|restart)
                if [ "${1:-}" = restart ]; then
                    extra_resources_block_pending_start_service || return 69
                fi
                # A committed common owner has the same native stop/restart
                # behavior whether it was applied now or restored at boot.
                # A pending record never falls through to the legacy engine.
                if shared_apply_has_record_service; then
                    _shared_owner=$(shared_apply_inspect_service) || return 69
                    case "$_shared_owner" in
                        committed\ *)
                            shared_apply_stop_service "$_shared_owner" || return $?
                            if [ "${1:-}" = restart ]; then
                                shared_apply_boot_service "$_shared_owner"
                            fi
                            return $?
                            ;;
                        none|restored) ;;
                        *) return 69 ;;
                    esac
                fi
                preflight_shared_apply_journal || return 69
                ;;
            runtime-failure)
                # Common committed runtime must NOT execute the old blind
                # orchestrator cleanup. Bind the callback to its original
                # child PID; stale callbacks after a new Apply are rejected.
                if shared_apply_has_record_service; then
                    _shared_owner=$(shared_apply_inspect_service) || return 69
                    case "$_shared_owner" in
                        committed\ *)
                            [ "$#" -eq 3 ] || return 69
                            shared_apply_stop_service "$_shared_owner" "$3"
                            return $?
                            ;;
                        none|restored) ;;
                        *) return 69 ;;
                    esac
                fi
                preflight_shared_apply_journal || return 69
                ;;
            telegram-voice-enable|telegram-voice-disable)
                # Compatibility names are common native Apply, not old PoC.
                preflight_shared_apply_journal common-apply || return 69
                ;;
            strategy-lab|strategy-lab-circular|strategy-lab-recover|extra-resources-install|extra-resources-recover|extra-resources-preview-saved|extra-resources-remove-plan|upstream-recover-mutating|upstream-install)
                # Under the inherited FD9, a committed native owner can be
                # temporarily stopped/restored only by native common service
                # actions. Pending or foreign owners remain fail-closed.
                if shared_apply_has_record_service; then
                    _lab_launch_owner=$(shared_apply_inspect_service) || return 69
                    case "$_lab_launch_owner" in
                        committed\ *)
                            preflight_shared_apply_journal strategy-lab-native || return 69
                            ;;
                        none|restored) preflight_shared_apply_journal || return 69 ;;
                        *) return 69 ;;
                    esac
                else
                    preflight_shared_apply_journal || return 69
                fi
                ;;
        esac
        service_dispatch "$@"
    ) 9>"${LIFECYCLE_LOCK_FILE}"
}

case "${1:-}" in
    status)
        # Status may inspect the persisted shared-Apply journal, whose
        # read-only Python owner validates the ORIGINAL held FD9. Previous
        # direct dispatch omitted it, falsely classifying restored/common
        # owners as "incomplete" even when engine, supervisor and IPFW pass.
        service_with_lifecycle_lock "${LIFECYCLE_LOCK_TIMEOUT}" "$@"
        ;;
    strategy-lab-status|strategy-lab-evidence|strategy-lab-stop|strategy-lab-start|extra-resources-native-build-saved|extra-resources-native-trial|extra-resources-native-previous-owner|extra-resources-native-restore-previous)
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
    start|stop|restart|reconfigure|telegram-voice-status|native-voice-lifecycle-inspect|native-voice-candidate-preflight|native-voice-preview-draft|telegram-voice-enable|telegram-voice-disable|shared-apply-record|shared-apply-prepare|shared-apply-build|shared-apply-execute|shared-apply-run|shared-apply-recover-reviewed-legacy|extra-resources-install|extra-resources-recover|extra-resources-remove-plan|upstream-recover-mutating|upstream-install)
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
