#!/bin/sh
set -eu
ROOT=$(mktemp -d /tmp/zapret-native-stop.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^shared_apply_stop_service()$/,/^}$/p' "$SOURCE" > "$ROOT/stop.sh"
sh -n "$ROOT/stop.sh" || fail "shell syntax"
. "$ROOT/stop.sh"
ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
ACTIVE_DIR="$ROOT/active"
CHILD_PIDFILE="$ROOT/child.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
SUPERVISOR_DAEMON_PIDFILE="$ROOT/daemon.pid"
mkdir -p "$ROOT/work/release" "$ACTIVE_DIR"
LOG="$ROOT/events"
preflight_voice_cutover_journals() { echo "guard:$1" >> "$LOG"; [ "$GUARD_OK" = 1 ]; }
shared_apply_require_tools() { return 0; }
shared_apply_bundle_service() { echo "seal:$1" >> "$LOG"; [ "$SEAL_OK" = 1 ]; }
shared_apply_native_config() {
    echo "config:$1" >> "$LOG"
    [ "$CONFIG_OK" = 1 ] || return 69
    echo '{"result":"committed","enabled":"1"}'
}
shared_apply_json_field() { echo committed; }
shared_apply_workspace() { echo "$ROOT/work"; }
atomic_verify_tree() { echo tree-verify >> "$LOG"; [ "$TREE_OK" = 1 ]; }
launcher_is_running() { [ "$ENGINE_RUNNING" = 1 ]; }
supervisor_is_running() { [ "$MONITOR_RUNNING" = 1 ]; }
supervisor_stop() {
    echo supervisor-stop >> "$LOG"
    [ "$STOP_OK" = 1 ] || return 1
    MONITOR_RUNNING=0
}
launcher_stop() {
    echo launcher-stop >> "$LOG"
    [ "$STOP_OK" = 1 ] || return 1
    ENGINE_RUNNING=0
}
firewall_shared_runtime() {
    echo "ipfw:$1:$2:$3" >> "$LOG"
    case "$1" in
        verify) [ "$KERNEL_OK" = 1 ] ;;
        install) [ "$INSTALL_OK" = 1 ] ;;
        commit) [ "$COMMIT_OK" = 1 ] ;;
        *) return 1 ;;
    esac
}
reset() {
    GUARD_OK=1; SEAL_OK=1; CONFIG_OK=1; TREE_OK=1
    ENGINE_RUNNING=1; MONITOR_RUNNING=1
    STOP_OK=1; KERNEL_OK=1; INSTALL_OK=1; COMMIT_OK=1
    : > "$LOG"
}
check() {
    expected="$1"; shift
    set +e
    shared_apply_stop_service "committed $ID voice" > "$ROOT/receipt"
    status=$?
    set -e
    [ "$status" -eq "$expected" ] || fail "status $status, expected $expected"
    got=$(tr '\n' ' ' < "$LOG")
    [ "$got" = "$*" ] || fail "steps: $got"
}
reset
check 0 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- ipfw:verify:$ACTIVE_DIR:- "
grep -Fqx "native-common-stopped=$ID" "$ROOT/receipt" || fail "stop receipt"
[ "$ENGINE_RUNNING" = 0 ] && [ "$MONITOR_RUNNING" = 0 ] || fail "processes still alive"
reset; ENGINE_RUNNING=0; MONITOR_RUNNING=0
check 0 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:$ACTIVE_DIR:- "
reset; GUARD_OK=0
check 69 "guard:common-apply "
reset; SEAL_OK=0
check 69 "guard:common-apply seal:verify "
reset; CONFIG_OK=0
check 69 "guard:common-apply seal:verify config:saved "
reset; TREE_OK=0
check 69 "guard:common-apply seal:verify config:saved tree-verify "
reset; ENGINE_RUNNING=1; MONITOR_RUNNING=0
check 69 "guard:common-apply seal:verify config:saved tree-verify "
reset; KERNEL_OK=0
check 69 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR "
reset; STOP_OK=0
check 70 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop "
reset; INSTALL_OK=0
check 70 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- "
reset; COMMIT_OK=0
check 70 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- "
reset
if shared_apply_stop_service "restored $ID voice" >/dev/null; then fail "unowned stop"; fi
if shared_apply_stop_service "committed /tmp/invalid voice" >/dev/null; then fail "path injection"; fi
echo 'PASS: common native stop validates active release and owned kernel lifecycle'
