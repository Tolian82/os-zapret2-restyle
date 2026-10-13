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
launcher_stop() { PROCESS=0; }
supervisor_stop() { MONITOR=0; }
launcher_start_once() {
    # Fail the replacement once, not the later restoration launch.
    if [ "$FAIL_LAUNCH" = 1 ]; then FAIL_LAUNCH=0; return 1; fi
    PROCESS=1
}
supervisor_start() { MONITOR=1; }
firewall_shared_runtime() {
    case "$1" in
        verify-staged)
            [ "$FW_STAGE" = 1 ] && [ "$FAIL_STAGE_CHECK" = 0 ] || return 1
            if [ "$3" = - ]; then [ "$FW" = empty ]; else [ "$FW" = active ]; fi ;;
        verify)
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
    if [ -d "$2" ]; then OLD="$3/previous"; mv "$2" "$OLD" || return 1; fi
    cp -R "$1" "$2" || return 1
    printf '%s\n' "$OLD"
}
atomic_restore_tree() {
    rm -rf "$1"
    [ -z "$2" ] || mv "$2" "$1"
}
BASE=$(CDPATH= cd -- "$(dirname -- "$0")/../src/opnsense/scripts/OPNsense/Zapret/backend" && pwd)
. "$BASE/apply_runtime.sh"
DVTWS_BIN="$ROOT/engine"; : > "$DVTWS_BIN"; chmod +x "$DVTWS_BIN"
ACTIVE_DIR="$ROOT/active"; BACKUP_ROOT="$ROOT/backup"
CHILD_PIDFILE="$ROOT/child"; SUPERVISOR_DAEMON_PIDFILE="$ROOT/sd"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/sm"; SUPERVISOR_LOOP="$ROOT/loop"
SERVICE_SCRIPT="$ROOT/service"; DVTWS_LOG="$ROOT/dvtws.log"
SUPERVISOR_LOG="$ROOT/supervisor.log"
for name in one two off; do
    mkdir -p "$ROOT/$name"
    echo "$name" > "$ROOT/$name/voice-plan.json"
    echo '--filter-tcp=443' > "$ROOT/$name/dvtws.args"
done
PROCESS=0 MONITOR=0 FW=empty FW_STAGE=0 FAIL_LAUNCH=0 FAIL_FW=0 FAIL_STAGE_CHECK=0 FW_PREPARE=0
apply_runtime_clear
apply_runtime_activate "$ROOT/one" 1 || fail "first activation"
[ "$APPLY_PHASE" = activated ] && [ "$PROCESS" = 1 ] &&
[ "$MONITOR" = 1 ] && [ "$FW_STAGE" = 1 ] || fail "first staged runtime"
apply_runtime_commit || fail "first commit"
[ "$APPLY_PHASE" = idle ] && [ "$FW_STAGE" = 0 ] || fail "first cleanup"
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
echo 'PASS: shared engine/IPFW activation, rollback, stopped mode and foreign-state refusal'
