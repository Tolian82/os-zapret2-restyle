#!/bin/sh
# Stage-3 shared runtime integration with injected engine/kernel adapters.
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/shared-apply.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
common_error() { echo "$*" >&2; }
validator_validate_runtime_modes() { [ -f "$1/voice-plan.json" ]; }
validator_validate_engine_mapped() { [ -f "$2" ]; }
firewall_prepare() { FW_PREPARE=1; }
launcher_is_running() { [ "$PROCESS" = 1 ]; }
supervisor_is_running() { [ "$MONITOR" = 1 ]; }
supervisor_pidfile_read() { echo 24680; }
common_process_matches() { [ "$SURVIVING_MONITOR" = 1 ]; }
launcher_stop() { [ "$SURVIVING_ENGINE" = 1 ] || PROCESS=0; }
supervisor_stop() { MONITOR=0; }
launcher_start_once() {
    LAUNCH_CALLS=$((LAUNCH_CALLS + 1))
    # Fail the replacement once, not the later restoration launch.
    if [ "$FAIL_LAUNCH" = 1 ]; then FAIL_LAUNCH=0; return 1; fi
    PROCESS=1
}
supervisor_start() {
    [ -n "${5:-}" ] && [ "$5" = "$SERVICE_SCRIPT" ] && [ -x "$5" ] ||
        fail "runtime activation/recovery handed supervisor a missing callback"
    MONITOR=1
}
firewall_shared_runtime() {
    case "$1" in
        verify-cleanup)
            # Real post-COMMIT reconciliation accepts missing or owned
            # remnants, but rejects unrelated/modified stage contents.
            [ "$FW" = active ] || return 1
            case "$FW_STAGE" in 0|1) ;; *) return 1 ;; esac ;;
        verify-staged)
            [ "$FW_STAGE" = 1 ] && [ "$FAIL_STAGE_CHECK" = 0 ] || return 1
            if [ "$3" = - ]; then [ "$FW" = empty ]; else [ "$FW" = active ]; fi ;;
        verify)
            # The real shared IPFW adapter refuses ALL staging tables after
            # native commit. The mock must not hide an orphan stage.
            [ "$FW_STAGE" = 0 ] || return 1
            if [ "$3" = - ]; then [ "$FW" = empty ]; else [ "$FW" = active ]; fi ;;
        install)
            [ "$FAIL_FW" = 0 ] || return 1
            if [ "$3" = - ]; then FW=empty; else FW=active; fi
            FW_STAGE=1 ;;
        rollback)
            if [ "$2" = - ]; then FW=empty; else FW=active; fi
            FW_STAGE=0 ;;
        commit) FW_STAGE=0 ;;
        *) return 1 ;;
    esac
}
atomic_install_tree() {
    mkdir -p "$3"
    OLD=
    if [ -d "$2" ]; then
        if [ "$#" -eq 4 ]; then
            OLD="$3/$(basename "$2")-$4"
        else
            OLD="$3/previous"
        fi
        mv "$2" "$OLD" || return 1
    fi
    cp -R "$1" "$2" || return 1
    printf '%s\n' "$OLD"
}
atomic_restore_tree() {
    rm -rf "$1"
    [ -z "$2" ] || mv "$2" "$1"
}
atomic_verify_tree() {
    cmp -s "$1/voice-plan.json" "$2/voice-plan.json" &&
    cmp -s "$1/dvtws.args" "$2/dvtws.args"
}
BASE=$(CDPATH= cd -- "$(dirname -- "$0")/../src/opnsense/scripts/OPNsense/Zapret/backend" && pwd)
. "$BASE/apply_runtime.sh"
# Exercise the real service entrypoint header: mocks must never silently
# supply SERVICE_SCRIPT when production leaves it unset (the owner-live _19
# failure). Do not source the full CLI dispatcher or touch any real runtime.
SERVICE_SOURCE="$BASE/../zapret_service.sh"
# Git stores the root service script as a source file (0644); its installed
# OPNsense package path is executable. Mirror ONLY that packaging mode in a
# disposable test tree, rather than asserting the Git checkout is executable.
NATIVE_INSTALL="$ROOT/installed"
mkdir -p "$NATIVE_INSTALL"
cp "$SERVICE_SOURCE" "$NATIVE_INSTALL/zapret_service.sh"
# Production header now resolves the validated Python runtime; stage the same
# source and single manifest so the mock installation mirrors real packaging.
cp "$BASE/../python_runtime.sh" "$BASE/../python_runtime.conf" "$NATIVE_INSTALL/"
chmod 0755 "$NATIVE_INSTALL/zapret_service.sh"
awk '/^ensure_runtime_components\(\)$/ { exit } { print }' "$SERVICE_SOURCE" > "$ROOT/service-header.sh"
[ -s "$ROOT/service-header.sh" ] || fail "native service entrypoint header unavailable"
(
    unset SERVICE_SCRIPT
    SCRIPT_DIR="$NATIVE_INSTALL"
    BACKEND_DIR="$BASE"
    ZAPRET_PYTHON_BIN=$(command -v python3.13)
    export ZAPRET_PYTHON_BIN
    . "$ROOT/service-header.sh"
    [ "$SERVICE_SCRIPT" = "$SCRIPT_DIR/zapret_service.sh" ] &&
    [ -x "$SERVICE_SCRIPT" ] ||
        fail "shared Apply has no executable supervisor callback in real service"
) || fail "production shared Apply service callback initialization"
# Separate census regression exercises the REAL production function.
# This process-less activation harness injects only its process witness.
apply_runtime_attest_engine_inventory() {
    # The real process census must also refuse dvtws2 without a live PID
    # even after launcher_stop() deletes the previous PID file.
    [ "$_apply_engine" = 1 ] || [ "$ORPHAN_AFTER_STOP" = 0 ]
}
DVTWS_BIN="$ROOT/engine"; : > "$DVTWS_BIN"; chmod +x "$DVTWS_BIN"
ACTIVE_DIR="$ROOT/active"; BACKUP_ROOT="$ROOT/backup"
CHILD_PIDFILE="$ROOT/child"; SUPERVISOR_DAEMON_PIDFILE="$ROOT/sd"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/sm"; SUPERVISOR_LOOP="$ROOT/loop"
SERVICE_SCRIPT="$NATIVE_INSTALL/zapret_service.sh"; DVTWS_LOG="$ROOT/dvtws.log"
SUPERVISOR_LOG="$ROOT/supervisor.log"
for name in one two off; do
    mkdir -p "$ROOT/$name"
    echo "$name" > "$ROOT/$name/voice-plan.json"
    echo '--filter-tcp=443' > "$ROOT/$name/dvtws.args"
done
PROCESS=0 MONITOR=0 FW=empty FW_STAGE=0 FAIL_LAUNCH=0 FAIL_FW=0 FAIL_STAGE_CHECK=0 FW_PREPARE=0
SURVIVING_MONITOR=0 SURVIVING_ENGINE=0 ORPHAN_AFTER_STOP=0 LAUNCH_CALLS=0
apply_runtime_clear
apply_runtime_activate "$ROOT/one" 1 || fail "first activation"
[ "$APPLY_PHASE" = activated ] && [ "$PROCESS" = 1 ] &&
[ "$MONITOR" = 1 ] && [ "$FW_STAGE" = 1 ] || fail "first staged runtime"
apply_runtime_attest_activated || fail "shared Apply rejected its actual live candidate"
MONITOR=0
if apply_runtime_attest_activated; then fail "missing supervisor reached Config save"; fi
MONITOR=1
PROCESS=0
if apply_runtime_attest_activated; then fail "missing engine reached Config save"; fi
PROCESS=1
FW_STAGE=0
if apply_runtime_attest_activated; then fail "missing IPFW snapshot reached Config save"; fi
FW_STAGE=1
printf '%s\n' broken-live-args > "$ACTIVE_DIR/dvtws.args"
if apply_runtime_attest_activated; then fail "changed active tree reached Config save"; fi
cp "$ROOT/one/dvtws.args" "$ACTIVE_DIR/dvtws.args"
apply_runtime_attest_activated || fail "restored staged owner rejected"
apply_runtime_commit || fail "first commit"
[ "$APPLY_PHASE" = idle ] && [ "$FW_STAGE" = 0 ] || fail "first cleanup"
# ON -> ON is a full replacement, but must NEVER start the new engine
# if the old monitor survives its PID file removal, old engine survives,
# or the independent binary inventory sees an orphan after stop.
for failure in monitor engine orphan; do
    _before_launches=$LAUNCH_CALLS
    case "$failure" in
        monitor) SURVIVING_MONITOR=1 ;;
        engine) SURVIVING_ENGINE=1 ;;
        orphan) ORPHAN_AFTER_STOP=1 ;;
    esac
    if apply_runtime_activate "$ROOT/two" 1; then
        fail "$failure survivor allowed a replacement Voice engine"
    fi
    [ "$LAUNCH_CALLS" -eq "$_before_launches" ] ||
        fail "$failure survivor started a second dvtws2"
    [ "$APPLY_PHASE" = installed ] && [ "$APPLY_OLD_RUNNING" = 1 ] &&
    [ -d "$APPLY_BACKUP" ] &&
    [ "$FW" = active ] && [ "$FW_STAGE" = 0 ] ||
        fail "$failure survivor erased evidence or modified IPFW"
    SURVIVING_MONITOR=0 SURVIVING_ENGINE=0 ORPHAN_AFTER_STOP=0
    apply_runtime_restore ||
        fail "$failure previous sealed release could not be manually restored"
    [ "$(cat "$ACTIVE_DIR/voice-plan.json")" = one ] &&
    [ "$PROCESS" = 1 ] && [ "$MONITOR" = 1 ] ||
        fail "$failure did not restore original ON service"
done
apply_runtime_activate "$ROOT/two" 1 || fail "ON edit"
[ "$FW_STAGE" = 1 ] || fail "precommit IPFW tables prematurely removed"
apply_runtime_restore || fail "failed Config save rollback"
[ "$(cat "$ACTIVE_DIR/voice-plan.json")" = one ] &&
[ "$PROCESS" = 1 ] && [ "$FW_STAGE" = 0 ] || fail "previous runtime rollback"
FAIL_LAUNCH=1
if apply_runtime_activate "$ROOT/two" 1; then fail "invalid engine accepted"; fi
FAIL_LAUNCH=0
[ "$(cat "$ACTIVE_DIR/voice-plan.json")" = one ] &&
[ "$PROCESS" = 1 ] || fail "launcher rollback"
FAIL_STAGE_CHECK=1
if apply_runtime_activate "$ROOT/two" 1; then fail "invalid precommit IPFW accepted"; fi
FAIL_STAGE_CHECK=0
[ "$(cat "$ACTIVE_DIR/voice-plan.json")" = one ] || fail "stage failure did not restore old release"
apply_runtime_activate "$ROOT/off" 0 || fail "global OFF"
[ "$PROCESS" = 0 ] && [ "$MONITOR" = 0 ] && [ "$FW" = empty ] || fail "OFF was not clean"
apply_runtime_commit || fail "OFF commit"
apply_runtime_activate "$ROOT/two" 1 || fail "OFF to ON"
apply_runtime_commit || fail "OFF to ON commit"
MONITOR=0
if apply_runtime_activate "$ROOT/one" 1; then fail "partial process accepted"; fi
MONITOR=1
FW=empty
FW_PREPARE=0
if apply_runtime_activate "$ROOT/one" 1; then fail "foreign kernel accepted"; fi
[ "$FW_PREPARE" = 0 ] || fail "foreign state modified kernel prerequisites"
mkdir "$ACTIVE_DIR/nested"
cp "$ROOT/one/voice-plan.json" "$ACTIVE_DIR/nested/voice-plan.json"
if apply_runtime_activate "$ACTIVE_DIR/nested" 1; then fail "nested release accepted"; fi
[ "$(cat "$ACTIVE_DIR/voice-plan.json")" = two ] || fail "foreign state changed runtime"
FW_PREPARE=0
MONITOR=0
if apply_runtime_probe "$ROOT/one" 1; then fail "partial supervisor passed non-mutating gate"; fi
[ "$FW_PREPARE" = 0 ] || fail "read-only probe touched firewall"
MONITOR=1
FW=empty
if apply_runtime_probe "$ROOT/one" 1; then fail "foreign IPFW passed non-mutating gate"; fi
[ "$FW_PREPARE" = 0 ] || fail "foreign rules triggered firewall preparation"
FW=active
# The old Telegram PoC migration/rollback harness is intentionally absent.
# Voice/Strategies share the tested native runtime and normal error handling.
SERVICE_SOURCE="$BASE/../zapret_service.sh"
if grep -Fq 'shared-apply-legacy-' "$SERVICE_SOURCE"; then
    fail "retired private legacy migration commands remain in service"
fi
if grep -Fq 'voice_native_legacy_' "$SERVICE_SOURCE"; then
    fail "retired Telegram PoC backend is still called"
fi
echo 'PASS: shared runtime activation, failure cleanup and single-owner paths'
