#!/bin/sh
# G04/LC-08: source-mounted read-only native Apply probe for cold IPFW.
# All kernel/engine operations are mocked. No host firewall is touched.
set -eu
ROOT=$(mktemp -d /tmp/g04-first-cold-probe.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL G04 cold Apply: $*" >&2; exit 1; }
BASE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
RUNTIME="$BASE/src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh"
SERVICE="$BASE/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
sed -n '/^apply_runtime_probe()$/,/^}$/p' "$RUNTIME" > "$ROOT/functions.sh"
sed -n '/^shared_apply_ipfw_kernel_absent_service()$/,/^}$/p' "$SERVICE" >> "$ROOT/functions.sh"
sh -n "$ROOT/functions.sh" || fail "actual production function syntax"
. "$ROOT/functions.sh"
mkdir "$ROOT/candidate" "$ROOT/active"
: > "$ROOT/candidate/voice-plan.json"
: > "$ROOT/candidate/dvtws.args"
DVTWS_BIN="$ROOT/dvtws2"
: > "$DVTWS_BIN"
chmod +x "$DVTWS_BIN"
ACTIVE_DIR="$ROOT/active"
CHILD_PIDFILE="$ROOT/engine.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
LOG="$ROOT/adapter.log"
KERNEL_LOG="$ROOT/kernel.log"
cat > "$ROOT/kldstat" <<'MOCK'
#!/bin/sh
[ "$MOCK_KLD_ERROR" -eq 0 ] || exit 70
[ "$1" = -q ] && [ "$2" = -m ] || exit 70
[ "$MOCK_LOADED_MODULE" = "$3" ] && exit 0
exit 1
MOCK
cat > "$ROOT/ipfw" <<'MOCK'
#!/bin/sh
[ "$1" = -q ] && [ "$2" = list ] || exit 70
case "$MOCK_IPFW_RC" in
  0) echo '65535 allow ip from any to any'; exit 0 ;;
  71) echo 'ipfw: retrieving config failed: Protocol not available' >&2; exit 71 ;;
  *) echo 'ipfw: unexpected error' >&2; exit "$MOCK_IPFW_RC" ;;
esac
MOCK
chmod +x "$ROOT/kldstat" "$ROOT/ipfw"
SHARED_APPLY_KLDSTAT_BIN="$ROOT/kldstat"
SHARED_APPLY_IPFW_BIN="$ROOT/ipfw"
export SHARED_APPLY_KLDSTAT_BIN SHARED_APPLY_IPFW_BIN
validator_validate_runtime_modes() { [ -f "$1/voice-plan.json" ]; }
validator_validate_engine_mapped() { [ -f "$2" ]; }
launcher_is_running() { [ "$PROCESS" -eq 1 ]; }
supervisor_is_running() { [ "$MONITOR" -eq 1 ]; }
apply_runtime_attest_engine_inventory() {
    [ "$UNTRACKED" -eq 0 ] && [ "$_apply_engine" -eq "$PROCESS" ]
}
firewall_shared_runtime() {
    echo "$1:$2:$3" >> "$LOG"
    [ "$ADAPTER_SAFE" -eq 1 ]
}
firewall_prepare() { echo mutation >> "$KERNEL_LOG"; return 99; }
common_error() { :; }
reset() {
    APPLY_PHASE=idle PROCESS=0 MONITOR=0 UNTRACKED=0 ADAPTER_SAFE=0
    MOCK_KLD_ERROR=0 MOCK_LOADED_MODULE=none MOCK_IPFW_RC=71
    export MOCK_KLD_ERROR MOCK_LOADED_MODULE MOCK_IPFW_RC
    : > "$LOG"
    : > "$KERNEL_LOG"
}
check() {
    expected="$1"
    expected_adapter="$2"
    label="$3"
    set +e
    apply_runtime_probe "$ROOT/candidate" 1 >/dev/null 2>"$ROOT/last.err"
    actual=$?
    set -e
    [ "$actual" -eq "$expected" ] ||
        fail "$label: status=$actual expected=$expected"
    observed=$(cat "$LOG")
    [ "$observed" = "$expected_adapter" ] ||
        fail "$label: adapter='$observed' expected='$expected_adapter'"
    [ ! -s "$KERNEL_LOG" ] || fail "$label: read-only probe mutated firewall"
}
# Only both absent modules + the exact ipfw(8) error may skip a rule query.
reset
check 0 '' "first pristine HTTPS Apply"
[ "$APPLY_PHASE" = idle ] || fail "cold probe advanced lifecycle"
# Every initialized/ambiguous kernel must go through exact adapter.
reset; MOCK_LOADED_MODULE=ipfw; MOCK_IPFW_RC=0; ADAPTER_SAFE=1
export MOCK_LOADED_MODULE MOCK_IPFW_RC
check 0 "verify:$ROOT/candidate:-" "loaded kernel with verified rule manifest"
reset; MOCK_LOADED_MODULE=ipfw; MOCK_IPFW_RC=0
export MOCK_LOADED_MODULE MOCK_IPFW_RC
check 69 "verify:$ROOT/candidate:-" "foreign live IPFW rule"
reset; MOCK_LOADED_MODULE=ipdivert
export MOCK_LOADED_MODULE
check 69 "verify:$ROOT/candidate:-" "partially loaded ipdivert"
reset; MOCK_KLD_ERROR=1
export MOCK_KLD_ERROR
check 69 "verify:$ROOT/candidate:-" "module query error"
reset; MOCK_IPFW_RC=70
export MOCK_IPFW_RC
check 69 "verify:$ROOT/candidate:-" "ambiguous ipfw error"
reset; MOCK_IPFW_RC=0
export MOCK_IPFW_RC
check 69 "verify:$ROOT/candidate:-" "ipfw unexpectedly readable"
# Process and transaction ownership always take priority over cold kernel.
reset; UNTRACKED=1
check 69 '' "orphaned dvtws2 census"
reset; PROCESS=1; MONITOR=0
check 69 '' "incomplete supervisor"
reset; PROCESS=1; MONITOR=1; UNTRACKED=1
check 69 '' "untracked running owner"
reset; APPLY_PHASE=activating
check 69 '' "already active transaction"
reset
set +e
apply_runtime_probe "$ACTIVE_DIR/nested" 1 >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] && [ ! -s "$LOG" ] && [ ! -s "$KERNEL_LOG" ] ||
    fail "unsafe candidate inside active runtime"
echo 'PASS: G04 first HTTPS Apply cold IPFW preflight read-only and fail-closed'
