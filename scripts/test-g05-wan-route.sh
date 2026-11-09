#!/bin/sh
# LC-06: the ORIGINAL shared FD9 service routing, extracted from product,
# verified with inert process/kernel/Config mocks. No host changes.
set -eu
ROOT=$(mktemp -d /tmp/g05-wan-route.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
BASE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$BASE/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
sed -n '/^shared_apply_wan_save_service()$/,/^}$/p' "$SOURCE" |
    sed "s@/usr/local/bin/php@$ROOT/php@g" > "$ROOT/functions"
[ -s "$ROOT/functions" ] || exit 1
sh -n "$ROOT/functions"
. "$ROOT/functions"
SCRIPT_DIR="$ROOT"
: > "$ROOT/shared_apply_wan.php"
TRACE="$ROOT/trace"
export TRACE
cat > "$ROOT/php" <<'MOCK'
#!/bin/sh
case "$2" in
    probe)
        echo probe >> "$TRACE"
        echo 'wan-eligible=1' ;;
    commit)
        echo commit >> "$TRACE"
        echo 'wan-saved=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' ;;
    *) exit 69 ;;
esac
MOCK
cat > "$ROOT/ps" <<'MOCK'
#!/bin/sh
[ "$TEST_SUPERVISOR" != 1 ] ||
    echo "67890 /usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"
exit 0
MOCK
cat > "$ROOT/kldstat" <<'MOCK'
#!/bin/sh
[ "$TEST_MODULES" = loaded ] && exit 0
[ "$TEST_MODULES" = partial ] && [ "$3" = ipfw ] && exit 0
exit 1
MOCK
cat > "$ROOT/ipfw" <<'MOCK'
#!/bin/sh
[ "$TEST_IPFW_FAIL" != 1 ] || exit 71
printf '%s\n' "$TEST_IPFW_RULES"
MOCK
chmod +x "$ROOT/php" "$ROOT/ps" "$ROOT/kldstat" "$ROOT/ipfw"
COMMON_PS_BIN="$ROOT/ps"
SHARED_APPLY_KLDSTAT_BIN="$ROOT/kldstat"
SHARED_APPLY_IPFW_BIN="$ROOT/ipfw"
CHILD_PIDFILE="$ROOT/engine.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
SUPERVISOR_DAEMON_PIDFILE="$ROOT/daemon.pid"
SUPERVISOR_LOOP=/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh
ACTIVE_DIR="$ROOT/runtime"
RULE_BASE=19000 RULE_MAX=19010
export COMMON_PS_BIN SHARED_APPLY_KLDSTAT_BIN SHARED_APPLY_IPFW_BIN
fail() { echo "FAIL G05: $*" >&2; exit 1; }
preflight_shared_apply_journal() { [ "$JOURNAL_OK" = 1 ]; }
extra_resources_block_pending_start_service() { [ "$RESOURCES_OK" = 1 ]; }
shared_apply_has_record_service() { [ "$RECORD" = 1 ]; }
orchestrator_native_status() { return "$RUNTIME_STATUS"; }
apply_runtime_attest_engine_inventory() { [ "$ORPHAN" = 0 ]; }
shared_apply_ipfw_kernel_absent_service() { [ "$KERNEL_COLD" = 1 ]; }
shared_apply_run_service() {
    echo full >> "$TRACE"
    case "${FULL_RESULT:-ok}" in
        ok) printf 'applied-id=%s\n' bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb ;;
        preflight) printf '%s\n' preflight-rejected=runtime-preflight ;;
        uncertain) return 70 ;;
        *) return 69 ;;
    esac
}
reset() {
    JOURNAL_OK=1 RESOURCES_OK=1 RECORD=0 RUNTIME_STATUS=1 ORPHAN=0
    FULL_RESULT=ok
    KERNEL_COLD=1 TEST_SUPERVISOR=0 TEST_MODULES=none TEST_IPFW_FAIL=0
    TEST_IPFW_RULES="65535 allow ip from any to any"
    export TEST_SUPERVISOR TEST_MODULES TEST_IPFW_FAIL TEST_IPFW_RULES
    rm -f "$CHILD_PIDFILE" "$SUPERVISOR_MONITOR_PIDFILE" "$SUPERVISOR_DAEMON_PIDFILE"
    : > "$TRACE"
}
check() {
    label="$1"; expected="$2"; trace="$3"
    got=$(shared_apply_wan_save_service encoded) || fail "$label failed without receipt"
    [ "$got" = "$expected" ] || fail "$label: got $got expected $expected"
    [ "$(paste -sd, "$TRACE")" = "$trace" ] || fail "$label incorrect subprocess ordering"
}
SAVED=wan-saved=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
APPLIED=applied-id=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
reset; check cold "$SAVED" "probe,commit"
reset; RECORD=1; check committed-owner "$APPLIED" "probe,full"
reset; RUNTIME_STATUS=0; check running-old-owner "$APPLIED" "probe,full"
# A RUNNING or sealed original owner MUST NEVER take the Config-only commit
# branch even when full Apply refuses or its rollback outcome is uncertain.
# Propagate the full FD9 result; the GUI must not report a WAN Save.
assert_full_refusal() {
    label="$1"; expected_rc="$2"; expected_output="$3"
    _full_rc=0
    _full_output=$(shared_apply_wan_save_service encoded) || _full_rc=$?
    [ "$_full_rc" -eq "$expected_rc" ] ||
        fail "$label lost full Apply error: rc=$_full_rc expected=$expected_rc"
    [ "$_full_output" = "$expected_output" ] ||
        fail "$label emitted false WAN success receipt: $_full_output"
    [ "$(paste -sd, "$TRACE")" = "probe,full" ] ||
        fail "$label called Config-only commit or skipped full Apply"
}
reset; RECORD=1; FULL_RESULT=uncertain
assert_full_refusal sealed-owner-uncertain 70 ""
reset; RUNTIME_STATUS=0; FULL_RESULT=uncertain
assert_full_refusal running-old-owner-uncertain 70 ""
reset; RECORD=1; FULL_RESULT=preflight
assert_full_refusal sealed-owner-preflight 0 preflight-rejected=runtime-preflight
reset; RUNTIME_STATUS=0; FULL_RESULT=preflight
assert_full_refusal running-old-owner-preflight 0 preflight-rejected=runtime-preflight
reset; RECORD=1; RESOURCES_OK=0
check pending-resources-with-owner preflight-rejected=wan-lifecycle probe

reset; RUNTIME_STATUS=2; check incomplete-owner preflight-rejected=wan-runtime-owner probe
reset; ORPHAN=1; check orphan-dvtws preflight-rejected=wan-runtime-owner probe
reset; TEST_SUPERVISOR=1; export TEST_SUPERVISOR
check orphan-supervisor preflight-rejected=wan-runtime-owner probe
reset; touch "$CHILD_PIDFILE"
check stale-pid preflight-rejected=wan-runtime-owner probe
reset; RESOURCES_OK=0
check resource-transaction preflight-rejected=wan-lifecycle probe
reset; KERNEL_COLD=0; TEST_MODULES=loaded; export TEST_MODULES
check warm-empty "$SAVED" "probe,commit"
reset; KERNEL_COLD=0; TEST_MODULES=loaded; TEST_IPFW_RULES="10000 deny ip from any to any"; export TEST_MODULES TEST_IPFW_RULES
check foreign-outside-range "$SAVED" "probe,commit"
reset; KERNEL_COLD=0; TEST_MODULES=loaded; TEST_IPFW_RULES="19000 allow ip from any to any"; export TEST_MODULES TEST_IPFW_RULES
check colliding-native-rule preflight-rejected=wan-kernel probe
reset; KERNEL_COLD=0; TEST_MODULES=loaded; TEST_IPFW_RULES="19100 allow ip from any to any"; export TEST_MODULES TEST_IPFW_RULES
check active-lab-rule preflight-rejected=wan-kernel probe
reset; KERNEL_COLD=0; TEST_MODULES=partial; export TEST_MODULES
check partial-kernel preflight-rejected=wan-kernel probe
reset; KERNEL_COLD=0; TEST_MODULES=loaded; TEST_IPFW_FAIL=1; export TEST_MODULES TEST_IPFW_FAIL
check unreadable-kernel preflight-rejected=wan-kernel probe
grep -Fq 'shared-apply-run|shared-apply-wan|' "$SOURCE" ||
    fail "WAN-only action not routed through original FD9"
grep -Fq '[shared_apply_wan]' "$BASE/src/opnsense/service/conf/actions.d/actions_zapret.conf" ||
    fail "configd WAN-only action unavailable"
echo 'PASS: G05 WAN-only native FD9 Config mode; RUNNING/committed full Apply refusal propagates without Config-only fallback'
