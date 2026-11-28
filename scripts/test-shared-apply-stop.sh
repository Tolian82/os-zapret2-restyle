#!/bin/sh
set -eu
ROOT=$(mktemp -d /tmp/zapret-native-stop.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
RUNTIME=$(dirname "$SOURCE")/backend/apply_runtime.sh
sed -n '/^shared_apply_stop_service()$/,/^}$/p' "$SOURCE" > "$ROOT/stop.sh"
# Exercise the real preflight on an ordinary sealed (non-observer)
# runtime instead of bypassing its refusal semantics in a mock.
sed -n '/^apply_runtime_observer_retirement_preflight()$/,/^}$/p' "$RUNTIME" >> "$ROOT/stop.sh"
sh -n "$ROOT/stop.sh" || fail "shell syntax"
. "$ROOT/stop.sh"
ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
ACTIVE_DIR="$ROOT/active"
CHILD_PIDFILE="$ROOT/child.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
SUPERVISOR_DAEMON_PIDFILE="$ROOT/daemon.pid"
SUPERVISOR_LOOP="$ROOT/monitor-loop"
mkdir -p "$ROOT/work/release" "$ACTIVE_DIR"
printf '%s\n' '--port=989' > "$ACTIVE_DIR/dvtws.args"
LOG="$ROOT/events"
preflight_shared_apply_journal() { echo "guard:$1" >> "$LOG"; [ "$GUARD_OK" = 1 ]; }
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
supervisor_pidfile_read() { [ "$MONITOR_RUNNING" = 1 ] && printf '%s\n' 777; }
common_process_matches() {
    [ "$1" = 777 ] && [ "$2" = "$SUPERVISOR_LOOP" ] &&
    [ "$OLD_MONITOR_SURVIVED" = 1 ]
}
common_error() { echo "error:$*" >> "$LOG"; }
# This fixture models one exact registered engine; the separate real-census
# regression covers orphan/duplicate/surviving PID scenarios.
apply_runtime_attest_engine_inventory() {
    [ "$_apply_engine" = "$ENGINE_RUNNING" ] && [ "$ORPHAN_ENGINE" = 0 ]
}
supervisor_stop() {
    echo supervisor-stop >> "$LOG"
    [ "$STOP_OK" = 1 ] || return 1
    MONITOR_RUNNING=0
    [ "$STUCK_MONITOR" = 0 ] || OLD_MONITOR_SURVIVED=1
}
launcher_stop() {
    echo launcher-stop >> "$LOG"
    [ "$STOP_OK" = 1 ] || return 1
    ENGINE_RUNNING=0
}
common_pidfile_read() { [ -r "$1" ] && sed -n '1p' "$1"; }
firewall_shared_runtime() {
    echo "ipfw:$1:$2:$3" >> "$LOG"
    case "$1" in
        verify) [ "$KERNEL_OK" = 1 ] ;;
        install) [ "$INSTALL_OK" = 1 ] ;;
        commit)
            [ "$COMMIT_OK" = 1 ] || return 1
            [ "$POST_TREE_DRIFT" = 0 ] || TREE_OK=0
            [ "$POST_ENGINE_RESPAWN" = 0 ] || ENGINE_RUNNING=1
            [ "$POST_MONITOR_RESPAWN" = 0 ] || MONITOR_RUNNING=1
            [ "$POST_ORPHAN_ENGINE" = 0 ] || ORPHAN_ENGINE=1
            [ "$POST_OLD_MONITOR_SURVIVE" = 0 ] || OLD_MONITOR_SURVIVED=1
            [ "$POST_KERNEL_DRIFT" = 0 ] || KERNEL_OK=0
            ;;
        *) return 1 ;;
    esac
}
reset() {
    GUARD_OK=1; SEAL_OK=1; CONFIG_OK=1; TREE_OK=1
    ENGINE_RUNNING=1; MONITOR_RUNNING=1
    STOP_OK=1; KERNEL_OK=1; INSTALL_OK=1; COMMIT_OK=1
    OLD_MONITOR_SURVIVED=0; STUCK_MONITOR=0; ORPHAN_ENGINE=0
    POST_TREE_DRIFT=0; POST_ENGINE_RESPAWN=0
    POST_MONITOR_RESPAWN=0; POST_ORPHAN_ENGINE=0
    POST_OLD_MONITOR_SURVIVE=0; POST_KERNEL_DRIFT=0
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
check 0 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- tree-verify ipfw:verify:$ACTIVE_DIR:- "
grep -Fqx "native-common-stopped=$ID" "$ROOT/receipt" || fail "stop receipt"
[ "$ENGINE_RUNNING" = 0 ] && [ "$MONITOR_RUNNING" = 0 ] || fail "processes still alive"
reset; ENGINE_RUNNING=0; MONITOR_RUNNING=0
check 0 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:$ACTIVE_DIR:- "
# Native supervisor_stop_one may discard its PID file after a failed
# signal. The original monitor identity must still block IPFW removal.
reset; STUCK_MONITOR=1
check 70 "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop "
[ ! -s "$ROOT/receipt" ] || fail "surviving old monitor claimed Stop"
# COMMIT destroys the reversible stage. Every post-COMMIT check must
# fail closed rather than claim Stop if the active release or process/IPFW
# state changes at this precise boundary.
for fault in tree child monitor orphan old-monitor kernel; do
    reset
    case "$fault" in
        tree) POST_TREE_DRIFT=1 ;;
        child) POST_ENGINE_RESPAWN=1 ;;
        monitor) POST_MONITOR_RESPAWN=1 ;;
        orphan) POST_ORPHAN_ENGINE=1 ;;
        old-monitor) POST_OLD_MONITOR_SURVIVE=1 ;;
        kernel) POST_KERNEL_DRIFT=1 ;;
    esac
    case "$fault" in
        tree) expected="guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- tree-verify " ;;
        child|monitor|old-monitor)
            expected="guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- tree-verify error:native common Stop: process survived IPFW commit "
            ;;
        orphan) expected="guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- tree-verify " ;;
        kernel) expected="guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- tree-verify ipfw:verify:$ACTIVE_DIR:- " ;;
    esac
    check 70 "$expected"
    [ ! -s "$ROOT/receipt" ] || fail "$fault post-COMMIT drift claimed Stop"
done
reset; GUARD_OK=0
check 69 "guard:common-apply guard:common-bound-auto-stop "
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
# The supervisor reports the PID it watched, even after that engine died.
# Only that exact dead incarnation may retire an attested common IPFW owner.
printf '542\n' > "$CHILD_PIDFILE"
reset; ENGINE_RUNNING=0; MONITOR_RUNNING=1
: > "$LOG"
set +e
shared_apply_stop_service "committed $ID voice" 542 > "$ROOT/receipt"
code=$?
set -e
[ "$code" -eq 0 ] || fail "dead common engine callback could not retire exact owner: $code"
[ "$ENGINE_RUNNING" = 0 ] && [ "$MONITOR_RUNNING" = 0 ] || fail "callback left native monitor running"
[ "$(tr '\n' ' ' < "$LOG")" = "guard:common-apply seal:verify config:saved tree-verify ipfw:verify:-:$ACTIVE_DIR supervisor-stop launcher-stop ipfw:install:$ACTIVE_DIR:- ipfw:commit:$ACTIVE_DIR:- tree-verify ipfw:verify:$ACTIVE_DIR:- " ] ||
    fail "callback did not use the verified common Stop transaction"
reset; ENGINE_RUNNING=0; MONITOR_RUNNING=1
if shared_apply_stop_service "committed $ID voice" 541 > /dev/null; then
    fail "stale supervisor callback accepted for newer common engine"
fi
[ "$MONITOR_RUNNING" = 1 ] || fail "stale callback stopped the newer owner"
reset
if shared_apply_stop_service "committed $ID voice" 542 > /dev/null; then
    fail "healthy common engine was killed by supervisor callback"
fi
[ "$ENGINE_RUNNING" = 1 ] || fail "healthy engine stopped by callback"
reset; ENGINE_RUNNING=0; MONITOR_RUNNING=1; KERNEL_OK=0
if shared_apply_stop_service "committed $ID voice" 542 > /dev/null; then
    fail "callback removed unverified kernel state"
fi
[ "$MONITOR_RUNNING" = 1 ] || fail "unknown kernel callback stopped supervisor"
rm -f "$CHILD_PIDFILE"
reset
if shared_apply_stop_service "committed $ID voice" 542 >/dev/null; then
    fail "callback without original PID evidence accepted"
fi
reset
if shared_apply_stop_service "restored $ID voice" >/dev/null; then fail "unowned stop"; fi
if shared_apply_stop_service "committed /tmp/invalid voice" >/dev/null; then fail "path injection"; fi
echo 'PASS: common native stop validates active release and owned kernel lifecycle'
# Join-only first ACTIVATED Stop, never a public committed Stop.
sed -n '/^shared_apply_first_running_base_stop_service()$/,/^}$/p' "$SOURCE" > "$ROOT/first-running-base-stop.sh"
[ -s "$ROOT/first-running-base-stop.sh" ] || fail "first running base private Stop missing"
sh -n "$ROOT/first-running-base-stop.sh" || fail "first running base Stop syntax"
(
    . "$ROOT/first-running-base-stop.sh"
    ROOT="$ROOT/first-running-base"
    mkdir -p "$ROOT"
    ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    BASE=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    BACKEND_DIR="$ROOT"
    PYTHON_RUNTIME="$ROOT/python-stub"
    CHILD_PIDFILE="$ROOT/child.pid"
    SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
    SUPERVISOR_DAEMON_PIDFILE="$ROOT/daemon.pid"
    LOG="$ROOT/log"
    cat > "$PYTHON_RUNTIME" <<'PY'
#!/bin/sh
printf 'guard:%s\n' "$2" >> "$LOG"
[ "${GUARD_FAIL:-0}" = 0 ] || exit 69
case "$2" in
 guard-first-running-base-shell)
   if [ "${SECOND_GUARD_FAIL:-0}" = 1 ]; then
      [ -e "$LOG.guardcall" ] && exit 69
      : > "$LOG.guardcall"
   fi
   printf '%s\n' "${OWNER_WIRE:-first-running-base-shell=qualified:321:654}" ;;
 guard-first-running-base-stopped) printf '%s\n' "${AFTER_WIRE:-first-running-base-stopped=qualified}" ;;
 *) exit 69 ;;
esac
PY
    chmod +x "$PYTHON_RUNTIME"
    export LOG GUARD_FAIL OWNER_WIRE AFTER_WIRE SECOND_GUARD_FAIL
    common_pidfile_read() { cat "$1"; }
    supervisor_pidfile_read() { cat "$1"; }
    supervisor_stop() { printf 'stop:supervisor\n' >> "$LOG"; [ "$STOP_SUP_FAIL" = 0 ]; }
    launcher_stop() { printf 'stop:launcher\n' >> "$LOG"; [ "$STOP_LAUNCH_FAIL" = 0 ]; }
    reset() { printf '321\n' > "$CHILD_PIDFILE"; printf '654\n' > "$SUPERVISOR_MONITOR_PIDFILE"; : > "$LOG"; GUARD_FAIL=0; SECOND_GUARD_FAIL=0; rm -f "$LOG.guardcall"; OWNER_WIRE=first-running-base-shell=qualified:321:654; AFTER_WIRE=first-running-base-stopped=qualified; STOP_SUP_FAIL=0; STOP_LAUNCH_FAIL=0; export GUARD_FAIL OWNER_WIRE AFTER_WIRE SECOND_GUARD_FAIL; }
    fail() { echo "FAIL: $1" >&2; exit 1; }
    reset
    shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out" || fail positive
    [ "$(cat "$ROOT/out")" = first-running-base-physical=stopped ] || fail receipt
    [ "$(grep -c '^stop:' "$LOG")" = 2 ] || fail positive-stops
    reset; GUARD_FAIL=1
    if shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out"; then fail guard; fi
    ! grep -q '^stop:' "$LOG" || fail guard-stop
    reset; OWNER_WIRE=first-running-base-shell=qualified:322:654; export OWNER_WIRE
    if shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out"; then fail replaced-child; fi
    ! grep -q '^stop:' "$LOG" || fail replaced-child-stop
    reset; OWNER_WIRE=first-running-base-shell=qualified:321:655; export OWNER_WIRE
    if shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out"; then fail replaced-monitor; fi
    ! grep -q '^stop:' "$LOG" || fail replaced-monitor-stop
    reset; SECOND_GUARD_FAIL=1; export SECOND_GUARD_FAIL
    if shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out"; then fail guard-window; fi
    ! grep -q '^stop:' "$LOG" || fail guard-window-signalled
    reset; STOP_SUP_FAIL=1
    if shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out"; then fail supervisor; fi
    ! grep -q 'stop:launcher' "$LOG" || fail supervisor-launcher
    reset; STOP_LAUNCH_FAIL=1
    if shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out"; then fail launcher; fi
    ! grep -q '^guard:guard-first-running-base-stopped' "$LOG" || fail launcher-after
    reset; AFTER_WIRE=first-running-base-stopped=unverified; export AFTER_WIRE
    if shared_apply_first_running_base_stop_service "$ID" "$BASE" > "$ROOT/out"; then fail post; fi
    [ ! -s "$ROOT/out" ] || fail post-receipt
    reset
    if shared_apply_first_running_base_stop_service "$ID" "${BASE}x" > "$ROOT/out"; then fail args; fi
    ! grep -q '^guard:' "$LOG" || fail malformed-guard
    printf 'PASS: first running base shell stop cases (including guard race)\n'
)
