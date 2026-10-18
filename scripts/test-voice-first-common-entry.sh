#!/bin/sh
# First Voice ON must attest existing running ordinary Strategies before
# it records the one native transaction. No kernel, Config or process changes.
set -eu
ROOT=$(mktemp -d /tmp/zapret-first-common.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
SRC=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh
sed -n '/^apply_runtime_probe()$/,/^}$/p' "$SRC" > "$ROOT/functions.sh"
sed -n '/^apply_runtime_observe_live_legacy()$/,/^}$/p' "$SRC" >> "$ROOT/functions.sh"
sh -n "$ROOT/functions.sh"
. "$ROOT/functions.sh"
fail() { echo "FAIL: $*" >&2; exit 1; }
APPLY_PHASE=idle
DVTWS_BIN="$ROOT/engine"
: > "$DVTWS_BIN"
chmod +x "$DVTWS_BIN"
ACTIVE_DIR="$ROOT/active"
mkdir -p "$ACTIVE_DIR" "$ROOT/new"
: > "$ROOT/new/voice-plan.json"
for file in dvtws.args tcp-ports.txt udp-ports.txt; do : > "$ACTIVE_DIR/$file"; done
CHILD_PIDFILE="$ROOT/engine.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
RULE_BASE=19000 RULE_MAX=19010
LOG="$ROOT/actions"
validator_validate_runtime_modes() { return 0; }
validator_validate_engine_mapped() { return 0; }
launcher_is_running() { [ "$RUNNING" = 1 ]; }
supervisor_is_running() { [ "$MONITOR" = 1 ]; }
apply_runtime_attest_engine_inventory() { [ "$_apply_engine" = "$RUNNING" ]; }
orchestrator_runtime_is_complete() { [ "$RUNNING" = 1 ] && [ "$MONITOR" = 1 ]; }
firewall_shared_runtime() {
    printf '%s:%s:%s\n' "$1" "$2" "$3" >> "$LOG"
    [ "$ACCEPT" = 1 ]
}
check() {
    expected="$1"; shift
    : > "$LOG"
    set +e
    apply_runtime_probe "$ROOT/new" 1
    actual=$?
    set -e
    [ "$actual" -eq "$expected" ] || fail "got status $actual expected $expected"
    got=$(cat "$LOG")
    [ "$got" = "$*" ] || fail "wrong IPFW call: $got"
}
RUNNING=1 MONITOR=1 ACCEPT=1
check 0 "verify-legacy:$ACTIVE_DIR:$ROOT/new"
RUNNING=1 MONITOR=1 ACCEPT=0
check 69 "verify-legacy:$ACTIVE_DIR:$ROOT/new"
RUNNING=1 MONITOR=0 ACCEPT=1
check 69 ""
RUNNING=0 MONITOR=0
check 0 "verify:$ROOT/new:-"
RUNNING=1 MONITOR=1
: > "$ACTIVE_DIR/voice-plan.json"
check 0 "verify:-:$ACTIVE_DIR"
echo 'PASS: first common Apply safely attests legacy Strategies owner'
