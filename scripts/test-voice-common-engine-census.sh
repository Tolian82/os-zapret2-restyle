#!/bin/sh
# Exact production engine census; fake process query only, no router writes.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh"
TMP=$(mktemp -d /tmp/zapret-census.XXXXXXXX) || exit 1
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
sed -n '/^apply_runtime_attest_engine_inventory()$/,/^}$/p' "$SOURCE" > "$TMP/census.sh"
sh -n "$TMP/census.sh" || fail "invalid census syntax"
. "$TMP/census.sh"
DVTWS_BIN=/usr/local/etc/zapret2/binaries/my/dvtws2
CHILD_PIDFILE="$TMP/child.pid"
COMMON_PS_BIN="$TMP/native-ps"
cat > "$COMMON_PS_BIN" <<'SH'
#!/bin/sh
[ "$1" = ax ] && [ "$2" = -o ] && [ "$3" = pid= ] &&
[ "$4" = -o ] && [ "$5" = command= ] || exit 1
[ "${QUERY_FAIL:-0}" = 0 ] || exit 1
cat "$FIXTURE"
SH
chmod 700 "$COMMON_PS_BIN"
FIXTURE="$TMP/ps.txt"
QUERY_FAIL=0
export FIXTURE QUERY_FAIL
common_error() { :; }
common_pidfile_read() { cat "$1" 2>/dev/null; }
check() {
    expected="$1"
    set +e
    apply_runtime_attest_engine_inventory
    status="$?"
    set -e
    [ "$status" -eq "$expected" ] || fail "status $status expected $expected"
}
: > "$FIXTURE"
_apply_engine=0
check 0
printf "%s\n" " 542 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
check 69
printf "%s\n" 542 > "$CHILD_PIDFILE"
_apply_engine=1
check 0
printf "%s\n" " 999 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
check 69
{
    printf "%s\n" " 542 $DVTWS_BIN --filter-udp=443"
    printf "%s\n" " 999 $DVTWS_BIN --filter-udp=555"
} > "$FIXTURE"
check 69
printf "%s\n" 555 > "$CHILD_PIDFILE"
check 69
# A similarly named application must not match the exact binary token.
printf "%s\n" " 999 ${DVTWS_BIN}-other --filter-udp=555" > "$FIXTURE"
_apply_engine=0
check 0
QUERY_FAIL=1; export QUERY_FAIL
check 69
echo 'PASS: orphan, duplicate, stale and missing-process-inventory refusal'


# Exercise the actual committed-common Stop route with the same census,
# not a text grep or an independent reimplementation of the decision.
SERVICE="$ROOT/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
sed -n '/^shared_apply_stop_service()$/,/^}$/p' "$SERVICE" > "$TMP/stop.sh"
sh -n "$TMP/stop.sh" || fail "invalid common Stop function"
. "$TMP/stop.sh"
QUERY_FAIL=0; export QUERY_FAIL
mkdir -p "$TMP/owner/release" "$TMP/active"
ACTIVE_DIR="$TMP/active"
SUPERVISOR_MONITOR_PIDFILE="$TMP/monitor.pid"
SUPERVISOR_DAEMON_PIDFILE="$TMP/daemon.pid"
SUPERVISOR_LOOP="$TMP/supervisor_loop.sh"
UNTRACKED_MONITOR=0
# The production Stop retains the old monitor PID even if its helper
# unlinks the PID file. Model both a clean stop and an orphan survivor.
supervisor_pidfile_read() { [ "$MONITOR" = 1 ] && printf '777\n'; }
common_process_matches() {
    [ "$1" = 777 ] && [ "$2" = "$SUPERVISOR_LOOP" ] &&
    [ "$UNTRACKED_MONITOR" = 1 ]
}
preflight_voice_cutover_journals() { :; }
shared_apply_require_tools() { :; }
shared_apply_bundle_service() { :; }
shared_apply_native_config() { printf '%s\n' '{"result":"committed"}'; }
shared_apply_json_field() { printf '%s\n' committed; }
shared_apply_workspace() { printf '%s\n' "$TMP/owner"; }
atomic_verify_tree() { :; }
launcher_is_running() { [ "$PROCESS" = 1 ]; }
supervisor_is_running() { [ "$MONITOR" = 1 ]; }
supervisor_stop() { MONITOR=0; }
launcher_stop() { PROCESS=0; : > "$FIXTURE"; }
firewall_shared_runtime() { printf '%s %s %s\n' "$1" "$2" "$3" >> "$TMP/firewall.log"; }
STOP_OWNER="committed 0123456789abcdef0123456789abcdef voice"

# The original Stop used to claim success here, despite an orphan dvtws2.
PROCESS=0 MONITOR=0
printf '%s\n' " 542 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
: > "$TMP/firewall.log"
if shared_apply_stop_service "$STOP_OWNER" > "$TMP/stop.out"; then
    fail "Stop accepted an orphan engine without PID ownership"
fi
[ ! -s "$TMP/firewall.log" ] && [ ! -s "$TMP/stop.out" ] ||
    fail "orphan Stop mutated firewall or reported success"

# Genuine empty already-stopped runtime remains idempotent.
: > "$FIXTURE"
shared_apply_stop_service "$STOP_OWNER" > "$TMP/stop.out" ||
    fail "clean already-stopped common owner refused"
grep -q '^native-common-stopped=' "$TMP/stop.out" ||
    fail "clean Stop lacked confirmation"

# Duplicate dvtws2 blocks the stop before touching the kernel.
PROCESS=1 MONITOR=1
printf '%s\n' 542 > "$CHILD_PIDFILE"
{
    printf '%s\n' " 542 $DVTWS_BIN --filter-udp=443"
    printf '%s\n' " 999 $DVTWS_BIN --filter-udp=555"
} > "$FIXTURE"
: > "$TMP/firewall.log"
if shared_apply_stop_service "$STOP_OWNER" > "$TMP/stop.out"; then
    fail "Stop accepted duplicate engine process"
fi
[ ! -s "$TMP/firewall.log" ] ||
    fail "duplicate engine reached firewall"

# An unexpected process surviving the PID-owned stop prevents IPFW cleanup.
printf '%s\n' " 542 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
launcher_stop() {
    PROCESS=0
    printf '%s\n' " 999 $DVTWS_BIN --filter-udp=555" > "$FIXTURE"
}
: > "$TMP/firewall.log"
if shared_apply_stop_service "$STOP_OWNER" > "$TMP/stop.out"; then
    fail "Stop claimed success with an untracked survivor"
fi
if grep -q '^install ' "$TMP/firewall.log"; then
    fail "firewall removed despite live process"
fi

# Supervisor may vanish from its PID file but remain alive. The common
# Stop must refuse to remove IPFW based on the pinned original monitor PID.
launcher_stop() { PROCESS=0; : > "$FIXTURE"; }
PROCESS=1 MONITOR=1 UNTRACKED_MONITOR=1
printf '%s\n' " 542 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
: > "$TMP/firewall.log"
if shared_apply_stop_service "$STOP_OWNER" > "$TMP/stop.out"; then
    fail "Stop accepted orphan previous supervisor after PID unlink"
fi
if grep -q '^install ' "$TMP/firewall.log"; then
    fail "orphan supervisor incorrectly removed IPFW"
fi
UNTRACKED_MONITOR=0

# Exact previous owner with no survivor still takes normal Stop path.
launcher_stop() { PROCESS=0; : > "$FIXTURE"; }
PROCESS=1 MONITOR=1
printf '%s\n' " 542 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
: > "$TMP/firewall.log"
shared_apply_stop_service "$STOP_OWNER" > "$TMP/stop.out" ||
    fail "valid common Stop refused"
grep -q '^native-common-stopped=' "$TMP/stop.out" ||
    fail "valid Stop lacked confirmation"
grep -q '^install ' "$TMP/firewall.log" ||
    fail "valid Stop skipped scoped IPFW transition"
echo 'PASS: common Stop refuses orphan/duplicate/survivor, preserves valid Stop'
