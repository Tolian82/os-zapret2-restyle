#!/bin/sh
# Shared Strategies/Voice runtime activation in the existing FD9 lifecycle.
# Source from zapret_service.sh. The native Config worker will own commit.
# This is not a standalone executor or a public GUI/configd Apply route.

apply_runtime_clear()
{
    APPLY_PHASE=idle
    APPLY_CANDIDATE=
    APPLY_BACKUP=
    APPLY_OLD=-
    APPLY_NEW=-
    APPLY_OLD_RUNNING=0
    APPLY_NEW_RUNNING=0
    APPLY_IPFW_INSTALLED=0
}

apply_runtime_probe()
{
    [ "$#" -eq 2 ] || return 64
    [ "${APPLY_PHASE:-idle}" = idle ] || return 69
    case "$1" in /*) ;; *) return 64 ;; esac
    case "$2" in 0|1) ;; *) return 64 ;; esac
    case "$1" in "$ACTIVE_DIR"/*) common_error "candidate inside active runtime"; return 69 ;; esac
    [ -d "$1" ] && [ ! -L "$1" ] &&
    [ -f "$1/voice-plan.json" ] &&
    [ "$1" != "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
    validator_validate_runtime_modes "$1" || return 1
    if [ "$2" = 1 ]; then
        [ -x "$DVTWS_BIN" ] || return 1
        validator_validate_engine_mapped "$DVTWS_BIN" "$1/dvtws.args" \
            "$ACTIVE_DIR" "$1" "${PYTHON_BIN:-/usr/local/bin/python3.13}" || return 1
    fi
    _apply_engine=0
    _apply_supervisor=0
    launcher_is_running "$CHILD_PIDFILE" && _apply_engine=1
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _apply_supervisor=1
    [ "$_apply_engine" = "$_apply_supervisor" ] || {
        common_error "shared Apply: incomplete previous engine/supervisor"
        return 69
    }
    if [ "$_apply_engine" = 1 ]; then
        [ -f "$ACTIVE_DIR/voice-plan.json" ] || {
            common_error "running legacy release requires explicit migration"
            return 69
        }
        firewall_shared_runtime verify - "$ACTIVE_DIR" || return 69
    else
        firewall_shared_runtime verify "$1" - || return 69
    fi
}

# Read-only refusal gate shared by the FD9 executor and the actual runtime
# preflight. It never acquires a lock, writes Config, starts a process,
# prepares pf/ipfw, or touches the durable Apply journal.
apply_runtime_preflight()
{
    apply_runtime_probe "$@" || return $?
    # The actual engine activation still repeats all observations after
    # the durable "activating" record (an external actor may change IPFW).
    # Only this second phase is permitted to initialize firewall modules.
    if [ "$2" = 1 ]; then firewall_prepare || return 1; fi
    APPLY_CANDIDATE="$1"
    APPLY_NEW_RUNNING="$2"
    APPLY_OLD_RUNNING="$_apply_engine"
    APPLY_PHASE=prepared
    APPLY_BACKUP=
    APPLY_OLD=-
    APPLY_NEW=-
    APPLY_IPFW_INSTALLED=0
}

apply_runtime_restore()
{
    [ "${APPLY_PHASE:-idle}" != idle ] || return 69
    supervisor_stop "$SUPERVISOR_DAEMON_PIDFILE" "$SUPERVISOR_MONITOR_PIDFILE"
    launcher_stop "$CHILD_PIDFILE" 5
    if [ "$APPLY_IPFW_INSTALLED" = 1 ]; then
        firewall_shared_runtime rollback "$APPLY_OLD" "$APPLY_NEW" || {
            common_error "RESTORE_FAILED: IPFW rollback"
            return 70
        }
    fi
    firewall_shared_runtime verify "$APPLY_CANDIDATE" "$APPLY_OLD" || {
        common_error "RESTORE_FAILED: previous IPFW state"
        return 70
    }
    if [ "$APPLY_PHASE" != prepared ]; then
        atomic_restore_tree "$ACTIVE_DIR" "$APPLY_BACKUP" || {
            common_error "RESTORE_FAILED: runtime tree"
            return 70
        }
    fi
    if [ "$APPLY_OLD_RUNNING" = 1 ]; then
        launcher_start_once "$DVTWS_BIN" "$ACTIVE_DIR/dvtws.args" \
            "$CHILD_PIDFILE" "$DVTWS_LOG" 5 || {
            common_error "RESTORE_FAILED: previous engine"
            return 70
        }
        supervisor_start "$SUPERVISOR_LOOP" "$SUPERVISOR_DAEMON_PIDFILE" \
            "$SUPERVISOR_MONITOR_PIDFILE" "$CHILD_PIDFILE" \
            "$SERVICE_SCRIPT" "$DVTWS_BIN" "$SUPERVISOR_LOG" || {
            common_error "RESTORE_FAILED: previous supervisor"
            return 70
        }
    fi
    apply_runtime_clear
}

apply_runtime_abort()
{
    _apply_reason="$1"
    if apply_runtime_restore; then
        common_error "$_apply_reason; previous runtime restored"
        return 1
    fi
    common_error "RESTORE_FAILED: $_apply_reason; rollback artifacts retained"
    return 70
}

apply_runtime_activate()
{
    apply_runtime_preflight "$@" || return $?
    APPLY_BACKUP=$(atomic_install_tree "$APPLY_CANDIDATE" "$ACTIVE_DIR" "$BACKUP_ROOT") || {
        apply_runtime_clear
        return 1
    }
    APPLY_PHASE=installed
    if [ "$APPLY_OLD_RUNNING" = 1 ]; then
        [ -n "$APPLY_BACKUP" ] || {
            apply_runtime_abort "missing previous release backup"
            return $?
        }
        APPLY_OLD="$APPLY_BACKUP"
        supervisor_stop "$SUPERVISOR_DAEMON_PIDFILE" "$SUPERVISOR_MONITOR_PIDFILE"
        launcher_stop "$CHILD_PIDFILE" 5
        if launcher_is_running "$CHILD_PIDFILE"; then
            apply_runtime_abort "previous engine remained live"
            return $?
        fi
    fi
    if [ "$APPLY_NEW_RUNNING" = 1 ]; then
        APPLY_NEW="$ACTIVE_DIR"
        launcher_start_once "$DVTWS_BIN" "$ACTIVE_DIR/dvtws.args" \
            "$CHILD_PIDFILE" "$DVTWS_LOG" 5 || {
            apply_runtime_abort "replacement engine failed"
            return $?
        }
    fi
    if [ "$APPLY_OLD_RUNNING" = 1 ] || [ "$APPLY_NEW_RUNNING" = 1 ]; then
        firewall_shared_runtime install "$APPLY_OLD" "$APPLY_NEW" || {
            # Install is self-rolling-back, but an incomplete rollback must
            # preserve both trees instead of announcing restored state.
            firewall_shared_runtime verify "$APPLY_CANDIDATE" "$APPLY_OLD" || {
                common_error "RESTORE_FAILED: shared IPFW install"
                return 70
            }
            apply_runtime_abort "IPFW activation failed"
            return $?
        }
        APPLY_IPFW_INSTALLED=1
    fi
    # Before native Config commit, the staged old IPFW table values are
    # intentional. Ordinary verify is only valid after commit or rollback.
    if [ "$APPLY_IPFW_INSTALLED" = 1 ]; then
        firewall_shared_runtime verify-staged "$APPLY_OLD" "$APPLY_NEW" || {
            apply_runtime_abort "uncommitted IPFW verification failed"
            return $?
        }
    else
        firewall_shared_runtime verify "$APPLY_CANDIDATE" "$APPLY_NEW" || {
            apply_runtime_abort "IPFW verification failed"
            return $?
        }
    fi
    if [ "$APPLY_NEW_RUNNING" = 1 ]; then
        supervisor_start "$SUPERVISOR_LOOP" "$SUPERVISOR_DAEMON_PIDFILE" \
            "$SUPERVISOR_MONITOR_PIDFILE" "$CHILD_PIDFILE" \
            "$SERVICE_SCRIPT" "$DVTWS_BIN" "$SUPERVISOR_LOG" || {
            apply_runtime_abort "replacement supervisor failed"
            return $?
        }
    fi
    APPLY_PHASE=activated
    # Not yet committed: previous tree and stage tables remain available.
}

apply_runtime_commit()
{
    [ "${APPLY_PHASE:-idle}" = activated ] || return 69
    # ONLY after native Config save and post-save consistency check.
    if [ "$APPLY_IPFW_INSTALLED" = 1 ]; then
        firewall_shared_runtime commit "$APPLY_OLD" "$APPLY_NEW" || return 70
    fi
    firewall_shared_runtime verify "$APPLY_CANDIDATE" "$APPLY_NEW" || return 70
    apply_runtime_clear
}
