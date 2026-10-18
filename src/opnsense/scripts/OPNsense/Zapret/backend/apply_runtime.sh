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

# Independent, read-only census of the ONE shared engine. A stale,
# absent or replaced PID file cannot make a live dvtws2 process disappear.
# Use the established process_query.sh wrapper (FreeBSD -xww / ax adapter),
# not a new daemon, lock or process owner.
apply_runtime_attest_engine_inventory()
{
    _apply_census_bin="${COMMON_PS_BIN:-/bin/ps}"
    [ -x "$_apply_census_bin" ] || return 69
    _apply_census_processes=$("$_apply_census_bin" ax -o pid= -o command=) || return 69
    _apply_census_pids=$(printf '%s\n' "$_apply_census_processes" |
        awk -v expected="$DVTWS_BIN" '
            {
                for (i = 2; i <= NF; i++) {
                    if ($i == expected) {
                        print $1
                        break
                    }
                }
            }') || return 69
    if [ "$_apply_engine" = 1 ]; then
        _apply_census_pid=$(common_pidfile_read "$CHILD_PIDFILE") || return 69
        [ -n "$_apply_census_pids" ] &&
        [ "$_apply_census_pids" = "$_apply_census_pid" ] || {
            common_error "shared Apply: unexpected or untracked dvtws2 process"
            return 69
        }
    else
        [ -z "$_apply_census_pids" ] || {
            common_error "shared Apply: dvtws2 process without valid PID owner"
            return 69
        }
    fi
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
    apply_runtime_attest_engine_inventory || return 69
    if [ "$_apply_engine" = 1 ]; then
        if [ -f "$ACTIVE_DIR/voice-plan.json" ]; then
            firewall_shared_runtime verify - "$ACTIVE_DIR" || return 69
        else
            # First common Strategies/Voice Apply from a live ordinary
            # Strategies runtime. Require BOTH exact process/supervisor
            # identity and the old-owned TCP/UDP divert rules. The adapter
            # reconstructs that bounded old manifest from installed files
            # and rejects foreign rules/tables before the durable journal.
            # The same FD9 owns the later atomic handoff and IPFW rollback.
            apply_runtime_observe_live_legacy || return 69
            firewall_shared_runtime verify-legacy "$ACTIVE_DIR" "$1" || return 69
        fi
    else
        firewall_shared_runtime verify "$1" - || return 69
    fi
}


# Read-only legacy observation for a future reversible native handoff.
# This verifies registered engine/supervisor, one complete old runtime and
# old kernel presence. It is NOT exact IPFW ownership or stop authorization.
apply_runtime_observe_live_legacy()
{
    [ "$#" -eq 0 ] || return 64
    [ "${APPLY_PHASE:-idle}" = idle ] || return 69
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69
    [ ! -e "$ACTIVE_DIR/voice-plan.json" ] &&
    [ ! -L "$ACTIVE_DIR/voice-plan.json" ] || return 69
    for _legacy_item in dvtws.args tcp-ports.txt udp-ports.txt; do
        [ -f "$ACTIVE_DIR/$_legacy_item" ] &&
        [ ! -L "$ACTIVE_DIR/$_legacy_item" ] || return 69
    done
    launcher_is_running "$CHILD_PIDFILE" || return 69
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" || return 69
    _apply_engine=1
    apply_runtime_attest_engine_inventory || return 69
    orchestrator_runtime_is_complete \
        "$CHILD_PIDFILE" "$SUPERVISOR_MONITOR_PIDFILE" \
        "$RULE_BASE" "$RULE_MAX" "$ACTIVE_DIR" || return 69
    launcher_is_running "$CHILD_PIDFILE" &&
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"
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
    [ "$#" -eq 2 ] || [ "$#" -eq 3 ] || return 64
    # The optional third argument is already recorded in the durable shared
    # Apply journal before this invocation. Keep normal boot/legacy callers
    # on their original 2-argument API and original PID layout.
    if [ "$#" -eq 3 ]; then
        case "$3" in ""|*[!a-f0-9]*) return 64 ;; esac
        [ "${#3}" -eq 32 ] || return 64
    fi
    apply_runtime_preflight "$1" "$2" || return $?
    if [ "$#" -eq 3 ]; then
        APPLY_BACKUP=$(atomic_install_tree "$APPLY_CANDIDATE" "$ACTIVE_DIR" "$BACKUP_ROOT" "$3") || {
            apply_runtime_clear
            return 1
        }
    else
        APPLY_BACKUP=$(atomic_install_tree "$APPLY_CANDIDATE" "$ACTIVE_DIR" "$BACKUP_ROOT") || {
            apply_runtime_clear
            return 1
        }
    fi
    APPLY_PHASE=installed
    if [ "$APPLY_OLD_RUNNING" = 1 ]; then
        [ -n "$APPLY_BACKUP" ] || {
            apply_runtime_abort "missing previous release backup"
            return $?
        }
        APPLY_OLD="$APPLY_BACKUP"
        # supervisor_stop removes its PID files even after an unsuccessful
        # signal. Keep the original monitor PID so an untracked survivor
        # cannot coexist with the new native engine after ON -> ON reapply.
        _apply_old_monitor_pid=$(supervisor_pidfile_read "$SUPERVISOR_MONITOR_PIDFILE") || {
            common_error "shared Apply: old monitor identity disappeared"
            return 70
        }
        supervisor_stop "$SUPERVISOR_DAEMON_PIDFILE" "$SUPERVISOR_MONITOR_PIDFILE" || return 70
        launcher_stop "$CHILD_PIDFILE" 5 || return 70
        if common_process_matches "$_apply_old_monitor_pid" "$SUPERVISOR_LOOP" ||
           supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" ||
           launcher_is_running "$CHILD_PIDFILE"; then
            # The installed candidate and exact old release backup remain
            # available for the journal's requires-review path. Do not
            # auto-restore or start a second engine while ownership is mixed.
            common_error "shared Apply: old engine or monitor survived stop"
            return 70
        fi
        # A missing child PID file is not evidence of no live engine.
        # Reuse the existing exact-binary process census before restarting.
        _apply_engine=0
        apply_runtime_attest_engine_inventory || {
            common_error "shared Apply: orphan engine after previous stop"
            return 70
        }
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


# Private forward seam from a VERIFIED, FULLY RETIRED old Telegram PoC.
# Its caller must have fsynced legacy-common-activating in the ONE shared
# journal under original FD9 and pinned native Config. There is no route
# from GUI/configd/boot to this helper until Config commit + reversible
# old-owner rollback are connected. Do not create an alternate engine:
# execute the EXACT existing common runtime activation once.
apply_runtime_activate_retired_legacy()
{
    [ "$#" -eq 2 ] || return 64
    _apply_legacy_candidate="$1"
    _apply_legacy_id="$2"
    case "$_apply_legacy_id" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#_apply_legacy_id}" -eq 32 ] || return 64
    [ "${APPLY_PHASE:-idle}" = idle ] || return 69

    # The old ACTIVE_DIR must be the original stopped PoC, never a native
    # release adopted as a legacy predecessor. A symlink or missing original
    # runtime manifest is not sufficient rollback evidence.
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] &&
    [ ! -e "$ACTIVE_DIR/voice-plan.json" ] &&
    [ ! -L "$ACTIVE_DIR/voice-plan.json" ] || return 69
    for _apply_legacy_file in dvtws.args tcp-ports.txt udp-ports.txt; do
        [ -f "$ACTIVE_DIR/$_apply_legacy_file" ] &&
        [ ! -L "$ACTIVE_DIR/$_apply_legacy_file" ] || return 69
    done
    # This ordinary probe proves a stopped engine/supervisor, independent
    # engine census and EMPTY owned IPFW. It runs before any installation.
    apply_runtime_probe "$_apply_legacy_candidate" 1 || return 69

    _apply_legacy_expected_backup="$BACKUP_ROOT/$(basename "$ACTIVE_DIR")-$_apply_legacy_id"
    apply_runtime_activate "$_apply_legacy_candidate" 1 "$_apply_legacy_id" || return 70

    # The old Config and full old runtime have not been discarded. The
    # precise deterministic atomic backup must be available for the SAME
    # original operation before we can attest common native activation.
    if [ "$APPLY_PHASE" != activated ] ||
       [ "$APPLY_OLD_RUNNING" != 0 ] ||
       [ "$APPLY_NEW_RUNNING" != 1 ] ||
       [ "$APPLY_IPFW_INSTALLED" != 1 ] ||
       [ "$APPLY_OLD" != - ] ||
       [ "$APPLY_NEW" != "$ACTIVE_DIR" ] ||
       [ "$APPLY_BACKUP" != "$_apply_legacy_expected_backup" ] ||
       [ ! -d "$APPLY_BACKUP" ] ||
       [ -L "$APPLY_BACKUP" ] ||
       ! apply_runtime_attest_activated; then
        # No optimistic second start/automatic old restore. The original
        # shared journal remains pending, preserving reverse evidence.
        common_error "shared Apply: retired legacy forward requires review"
        return 70
    fi
}

# Reconstruct only the verified pre-Config context after Python's fixed
# native child exited. Its shell variables cannot survive subprocess exit.
# Private legacy→common ONLY, never for generic Apply or unsealed rollback.
# Must run under original FD9; the Python owner also holds the original
# Config flock and verifies the sealed old predecessor independently.
apply_runtime_rehydrate_retired_legacy()
{
    [ "$#" -eq 2 ] || return 64
    _apply_rehydrate_candidate="$1"
    _apply_rehydrate_id="$2"
    case "$_apply_rehydrate_id" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#_apply_rehydrate_id}" -eq 32 ] || return 64
    [ "${APPLY_PHASE:-idle}" = idle ] || return 69
    case "$_apply_rehydrate_candidate" in /*) ;; *) return 64 ;; esac
    [ -d "$_apply_rehydrate_candidate" ] &&
    [ ! -L "$_apply_rehydrate_candidate" ] &&
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 69

    _apply_rehydrate_backup="$BACKUP_ROOT/$(basename "$ACTIVE_DIR")-$_apply_rehydrate_id"
    [ -d "$_apply_rehydrate_backup" ] &&
    [ ! -L "$_apply_rehydrate_backup" ] &&
    [ ! -e "$_apply_rehydrate_backup/voice-plan.json" ] &&
    [ ! -L "$_apply_rehydrate_backup/voice-plan.json" ] || return 69
    for _apply_rehydrate_file in dvtws.args tcp-ports.txt udp-ports.txt; do
        [ -f "$_apply_rehydrate_backup/$_apply_rehydrate_file" ] &&
        [ ! -L "$_apply_rehydrate_backup/$_apply_rehydrate_file" ] || return 69
    done
    _apply_rehydrate_stage="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").stage.$_apply_rehydrate_id"
    _apply_rehydrate_park="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").old.$_apply_rehydrate_id"
    [ ! -e "$_apply_rehydrate_stage" ] && [ ! -L "$_apply_rehydrate_stage" ] &&
    [ ! -e "$_apply_rehydrate_park" ] && [ ! -L "$_apply_rehydrate_park" ] ||
        return 69

    # All checks are read-only until the original context can be proven.
    validator_validate_runtime_modes "$_apply_rehydrate_candidate" || return 70
    atomic_verify_tree "$_apply_rehydrate_candidate" "$ACTIVE_DIR" || return 70
    launcher_is_running "$CHILD_PIDFILE" &&
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" || return 70
    _apply_engine=1
    apply_runtime_attest_engine_inventory || return 70
    firewall_shared_runtime verify-staged - "$ACTIVE_DIR" || return 70

    APPLY_CANDIDATE="$_apply_rehydrate_candidate"
    APPLY_BACKUP="$_apply_rehydrate_backup"
    APPLY_OLD=-
    APPLY_NEW="$ACTIVE_DIR"
    APPLY_OLD_RUNNING=0
    APPLY_NEW_RUNNING=1
    APPLY_IPFW_INSTALLED=1
    APPLY_PHASE=activated
    if ! apply_runtime_attest_activated; then
        # The parent journal remains pending; this only clears ephemeral
        # child-process variables, NEVER old/native files or IPFW objects.
        apply_runtime_clear
        return 70
    fi
}

# Private READ-ONLY witness after native IPFW has committed. This is the
# physical counterpart to rehydrate_retired_legacy(), which expects staged
# tables and must NEVER be used as a post-commit success witness.
apply_runtime_verify_retired_legacy_committed()
{
    [ "$#" -eq 2 ] || return 64
    _apply_done_candidate="$1"
    _apply_done_id="$2"
    case "$_apply_done_id" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#_apply_done_id}" -eq 32 ] || return 64
    [ "${APPLY_PHASE:-idle}" = idle ] || return 69
    case "$_apply_done_candidate" in /*) ;; *) return 64 ;; esac
    _apply_done_backup="$BACKUP_ROOT/$(basename "$ACTIVE_DIR")-$_apply_done_id"
    [ -d "$_apply_done_candidate" ] &&
    [ ! -L "$_apply_done_candidate" ] &&
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] &&
    [ -d "$_apply_done_backup" ] && [ ! -L "$_apply_done_backup" ] &&
    [ ! -e "$_apply_done_backup/voice-plan.json" ] || return 69
    for _apply_done_file in dvtws.args tcp-ports.txt udp-ports.txt; do
        [ -f "$_apply_done_backup/$_apply_done_file" ] &&
        [ ! -L "$_apply_done_backup/$_apply_done_file" ] || return 69
    done
    validator_validate_runtime_modes "$_apply_done_candidate" || return 70
    atomic_verify_tree "$_apply_done_candidate" "$ACTIVE_DIR" || return 70
    launcher_is_running "$CHILD_PIDFILE" &&
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" || return 70
    _apply_engine=1
    apply_runtime_attest_engine_inventory || return 70
    # Final verify rejects ALL staging tables as well as foreign rules.
    firewall_shared_runtime verify "$_apply_done_candidate" "$ACTIVE_DIR" || return 70
}

# Explicit operator-only completion of EXACT partial native IPFW staging.
# Caller has already fsynced the common COMMIT intent and saved Config.
# No engine activation, native Config save or general IPFW rule sweep here.
apply_runtime_resume_retired_legacy_cleanup()
{
    [ "$#" -eq 2 ] || return 64
    _apply_done_candidate="$1"
    _apply_done_id="$2"
    case "$_apply_done_id" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#_apply_done_id}" -eq 32 ] || return 64
    [ "${APPLY_PHASE:-idle}" = idle ] || return 69
    case "$_apply_done_candidate" in /*) ;; *) return 64 ;; esac
    _apply_done_backup="$BACKUP_ROOT/$(basename "$ACTIVE_DIR")-$_apply_done_id"
    [ -d "$_apply_done_candidate" ] &&
    [ ! -L "$_apply_done_candidate" ] &&
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] &&
    [ -d "$_apply_done_backup" ] && [ ! -L "$_apply_done_backup" ] &&
    [ ! -e "$_apply_done_backup/voice-plan.json" ] || return 69
    for _apply_done_file in dvtws.args tcp-ports.txt udp-ports.txt; do
        [ -f "$_apply_done_backup/$_apply_done_file" ] &&
        [ ! -L "$_apply_done_backup/$_apply_done_file" ] || return 69
    done
    validator_validate_runtime_modes "$_apply_done_candidate" || return 70
    atomic_verify_tree "$_apply_done_candidate" "$ACTIVE_DIR" || return 70
    launcher_is_running "$CHILD_PIDFILE" &&
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" || return 70
    _apply_engine=1
    apply_runtime_attest_engine_inventory || return 70
    # No pending operation-ID atomic rename may be silently adopted.
    _apply_stage="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").stage.$_apply_done_id"
    _apply_park="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").old.$_apply_done_id"
    [ ! -e "$_apply_stage" ] && [ ! -L "$_apply_stage" ] &&
    [ ! -e "$_apply_park" ] && [ ! -L "$_apply_park" ] || return 70
    # READ ONLY classification first. A subset of correctly EMPTY initial
    # stage tables may remain after power interruption; foreign content,
    # divergent rules or active address sets must fail before any mutation.
    firewall_shared_runtime verify-cleanup - "$ACTIVE_DIR" || return 70
    # Exact existing common postcommit cleanup is idempotent and internally
    # rechecks the manifest before deleting each verified stage.
    firewall_shared_runtime commit - "$ACTIVE_DIR" || return 70
    apply_runtime_verify_retired_legacy_committed "$_apply_done_candidate" "$_apply_done_id" || return 70
}

# Strict read-only cold witness before adopting a persisted native Config.
# The entire common IPFW range must be empty, with no engine, monitor or
# atomic staging gap. The sealed previous legacy backup remains untouched.
apply_runtime_verify_retired_legacy_cold()
{
    [ "$#" -eq 2 ] || return 64
    _cold_release="$1"
    _cold_id="$2"
    case "$_cold_id" in ""|*[!a-f0-9]*) return 64 ;; esac
    [ "${#_cold_id}" -eq 32 ] || return 64
    [ "${APPLY_PHASE:-idle}" = idle ] || return 69
    case "$_cold_release" in /*) ;; *) return 64 ;; esac
    _cold_backup="$BACKUP_ROOT/$(basename "$ACTIVE_DIR")-$_cold_id"
    [ -d "$_cold_release" ] && [ ! -L "$_cold_release" ] &&
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] &&
    [ -d "$_cold_backup" ] && [ ! -L "$_cold_backup" ] &&
    [ ! -e "$_cold_backup/voice-plan.json" ] &&
    [ ! -L "$_cold_backup/voice-plan.json" ] || return 69
    for _cold_file in dvtws.args tcp-ports.txt udp-ports.txt; do
        [ -f "$_cold_backup/$_cold_file" ] &&
        [ ! -L "$_cold_backup/$_cold_file" ] || return 69
    done
    _cold_stage="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").stage.$_cold_id"
    _cold_park="$(dirname "$ACTIVE_DIR")/.$(basename "$ACTIVE_DIR").old.$_cold_id"
    [ ! -e "$_cold_stage" ] && [ ! -L "$_cold_stage" ] &&
    [ ! -e "$_cold_park" ] && [ ! -L "$_cold_park" ] || return 70
    validator_validate_runtime_modes "$_cold_release" || return 70
    atomic_verify_tree "$_cold_release" "$ACTIVE_DIR" || return 70
    if launcher_is_running "$CHILD_PIDFILE" ||
       supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE"; then
        return 70
    fi
    _apply_engine=0
    apply_runtime_attest_engine_inventory || return 70
    firewall_shared_runtime verify "$_cold_release" - || return 70
}

# Post-activation proof for the ACTUAL shared Strategies/Voice Apply.
# Invoke under original FD9, after native activation and immediately before
# Config::save. Never return success based on the launcher/adapter exit code
# alone: confirm installed bytes, one process owner and precommit firewall.
# This helper is read-only and is reused by either page's same executor.
apply_runtime_attest_activated()
{
    [ "$#" -eq 0 ] || return 64
    [ "${APPLY_PHASE:-idle}" = activated ] || return 69
    [ -d "$APPLY_CANDIDATE" ] && [ ! -L "$APPLY_CANDIDATE" ] &&
    [ -d "$ACTIVE_DIR" ] && [ ! -L "$ACTIVE_DIR" ] || return 70
    case "$APPLY_NEW_RUNNING" in 0|1) ;; *) return 70 ;; esac

    # The atomic installer verifies its copy BEFORE the rename. A later
    # alteration of the live tree must not slip into persisted native Config.
    atomic_verify_tree "$APPLY_CANDIDATE" "$ACTIVE_DIR" || return 70

    _apply_engine=0
    _apply_monitor=0
    launcher_is_running "$CHILD_PIDFILE" && _apply_engine=1
    supervisor_is_running "$SUPERVISOR_MONITOR_PIDFILE" && _apply_monitor=1
    [ "$_apply_engine" = "$APPLY_NEW_RUNNING" ] &&
    [ "$_apply_monitor" = "$APPLY_NEW_RUNNING" ] || return 70
    apply_runtime_attest_engine_inventory || return 70

    if [ "$APPLY_NEW_RUNNING" = 1 ]; then
        [ "$APPLY_NEW" = "$ACTIVE_DIR" ] || return 70
    else
        [ "$APPLY_NEW" = - ] || return 70
    fi
    if [ "$APPLY_IPFW_INSTALLED" = 1 ]; then
        firewall_shared_runtime verify-staged "$APPLY_OLD" "$APPLY_NEW" || return 70
    else
        firewall_shared_runtime verify "$APPLY_CANDIDATE" "$APPLY_NEW" || return 70
    fi
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
