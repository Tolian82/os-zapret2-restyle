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
# Separate census regression exercises the REAL production function.
# This process-less activation harness injects only its process witness.
apply_runtime_attest_engine_inventory() { return 0; }
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
FW_PREPARE=0
MONITOR=0
if apply_runtime_probe "$ROOT/one" 1; then fail "partial supervisor passed non-mutating gate"; fi
[ "$FW_PREPARE" = 0 ] || fail "read-only probe touched firewall"
MONITOR=1
FW=empty
if apply_runtime_probe "$ROOT/one" 1; then fail "foreign IPFW passed non-mutating gate"; fi
[ "$FW_PREPARE" = 0 ] || fail "foreign rules triggered firewall preparation"
FW=active
mkdir -p "$ROOT/legacy"
if apply_runtime_probe "$ROOT/legacy" 1; then fail "legacy runtime was accepted"; fi
[ "$FW_PREPARE" = 0 ] || fail "legacy refusal modified firewall"
# A fully QUIESCENT legacy runtime is a supported one-FD9 migration
# candidate. Keep the old directory in the existing atomic backup so
# a pre-Config failure can restore it exactly, without starting a legacy
# process or changing persisted native Config.
PROCESS=0 MONITOR=0 FW=empty FW_STAGE=0 FW_PREPARE=0
rm -rf "$ACTIVE_DIR" "$BACKUP_ROOT/previous"
mkdir -p "$ACTIVE_DIR"
printf "%s\n" original-legacy > "$ACTIVE_DIR/old-runtime-marker"
printf "%s\n" --filter-tcp=443 > "$ACTIVE_DIR/dvtws.args"
apply_runtime_clear
apply_runtime_activate "$ROOT/one" 1 || fail "stopped legacy to native ON failed"
[ "$APPLY_OLD_RUNNING" = 0 ] &&
[ -f "$APPLY_BACKUP/old-runtime-marker" ] &&
[ "$PROCESS" = 1 ] && [ "$MONITOR" = 1 ] ||
    fail "legacy backup or shared replacement missing"
apply_runtime_restore || fail "stopped legacy rollback did not restore"
[ -f "$ACTIVE_DIR/old-runtime-marker" ] &&
[ "$PROCESS" = 0 ] && [ "$MONITOR" = 0 ] && [ "$FW" = empty ] ||
    fail "old stopped legacy release or clean kernel lost"
apply_runtime_activate "$ROOT/one" 1 || fail "stopped legacy second ON failed"
_legacy_previous="$APPLY_BACKUP"
apply_runtime_commit || fail "stopped legacy native commit failed"
[ "$(cat "$ACTIVE_DIR/voice-plan.json")" = one ] &&
[ -f "$_legacy_previous/old-runtime-marker" ] &&
[ "$PROCESS" = 1 ] && [ "$MONITOR" = 1 ] && [ "$FW_STAGE" = 0 ] ||
    fail "native release did not commit while preserving old legacy backup"
# A LIVE legacy runtime must still be refused prior to journal mutation.
PROCESS=1 MONITOR=1 FW=active
rm -f "$ACTIVE_DIR/voice-plan.json"
if apply_runtime_probe "$ROOT/two" 1; then
    fail "live legacy runtime unexpectedly passed native ownership check"
fi
[ "$FW_PREPARE" = 1 ] || fail "foreign check modified fixture unexpectedly"

# First live legacy audit remains read-only: no Config, process, kernel or
# durable journal writer. Legacy IPFW presence is NOT a cutover permit.
orchestrator_runtime_is_complete() {
    [ "$#" -eq 5 ] && [ "$4" = "$RULE_MAX" ] &&
    [ "$5" = "$ACTIVE_DIR" ] && [ "$LEGACY_RULES" = 1 ]
}
RULE_BASE=19000 RULE_MAX=19010 LEGACY_RULES=1
PROCESS=1 MONITOR=1 FW=active FW_PREPARE=0 FW_STAGE=0
rm -rf "$ACTIVE_DIR"
mkdir "$ACTIVE_DIR"
for field in dvtws.args tcp-ports.txt udp-ports.txt; do
    printf '%s\n' legacy > "$ACTIVE_DIR/$field"
done
apply_runtime_clear
apply_runtime_observe_live_legacy || fail "running old owner not observed"
[ "$PROCESS" = 1 ] && [ "$MONITOR" = 1 ] &&
[ "$FW_PREPARE" = 0 ] || fail "read-only old owner probe touched runtime"
LEGACY_RULES=0
if apply_runtime_observe_live_legacy; then fail "missing old IPFW accepted"; fi
LEGACY_RULES=1 MONITOR=0
if apply_runtime_observe_live_legacy; then fail "missing old supervisor accepted"; fi
MONITOR=1 PROCESS=0
if apply_runtime_observe_live_legacy; then fail "missing old engine accepted"; fi
PROCESS=1
printf '%s\n' '{}' > "$ACTIVE_DIR/voice-plan.json"
if apply_runtime_observe_live_legacy; then fail "native common classified as legacy"; fi
rm "$ACTIVE_DIR/voice-plan.json"
rm "$ACTIVE_DIR/tcp-ports.txt"
if apply_runtime_observe_live_legacy; then fail "incomplete old tree accepted"; fi
printf '%s\n' legacy > "$ACTIVE_DIR/tcp-ports.txt"
ln -s udp-ports.txt "$ACTIVE_DIR/voice-plan.json"
if apply_runtime_observe_live_legacy; then fail "symlinked common plan accepted"; fi
rm "$ACTIVE_DIR/voice-plan.json"
[ "$FW_PREPARE" = 0 ] && [ "$FW_STAGE" = 0 ] || fail "old audit modified firewall"
echo 'PASS: live old owner observer remains read-only and never authorizes handoff'


# Test the REAL root service function's binding to the existing strict
# FreeBSD legacy kernel witness. Only the absolute Python call is replaced
# by a fixture: no second process/kernel writer or independent parser.
SERVICE_SOURCE="$(CDPATH= cd -- "$(dirname -- "$0")/../src/opnsense/scripts/OPNsense/Zapret" && pwd)/zapret_service.sh"
AUDIT_SCRIPT="$ROOT/common-legacy-audit.sh"
sed -n '/^shared_apply_legacy_audit_service()$/,/^}$/p' "$SERVICE_SOURCE" > "$AUDIT_SCRIPT"
python3 - "$AUDIT_SCRIPT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
original='    [ -x /usr/local/bin/python3.13 ] &&\n    [ -r "${BACKEND_DIR}/voice_native_legacy_live_preflight.py" ] || return 69'
assert original in s, "native strict Python runtime path must be fixed"
s=s.replace(original,'    [ "$AUDIT_PY_AVAILABLE" = 1 ] || return 69')
original='    _legacy_exact_report=$(/usr/local/bin/python3.13 \\\n        "${BACKEND_DIR}/voice_native_legacy_live_preflight.py" inspect) || return 69'
assert original in s, "production audit must call strict legacy live inspector"
s=s.replace(original,'    _legacy_exact_report=$(legacy_exact_fixture) || return 69')
p.write_text(s)
PY
. "$AUDIT_SCRIPT"
shared_apply_has_record_service() { [ "$HAS_COMMON_RECORD" = 1 ]; }
shared_apply_inspect_service() { echo none; }
preflight_voice_cutover_journals() { [ "$PENDING_OLD" = 0 ]; }
legacy_exact_fixture() {
    [ "$EXACT_OK" = 1 ] || return 69
    if [ "$EXACT_BAD" = 1 ]; then
        printf '%s\n' 'legacy-voice-preflight=wrong' 'voice-on=blocked'
    else
        printf '%s\n' \
            'legacy-voice-preflight=legacy-poc-full-live-baseline-observed-not-owned' \
            'legacy-voice-ipfw-sha256=8a9b' \
            'legacy-voice-managed-sha256=0123' \
            'legacy-voice-ownership=not-adopted' \
            'voice-on=blocked'
    fi
}
HAS_COMMON_RECORD=0 PENDING_OLD=0 AUDIT_PY_AVAILABLE=1 EXACT_OK=1 EXACT_BAD=0
PROCESS=1 MONITOR=1 LEGACY_RULES=1 FW_PREPARE=0 FW_STAGE=0
AUDIT_OK=$(shared_apply_legacy_audit_service) || fail "strict read-only legacy audit"
printf '%s\n' "$AUDIT_OK" | grep -Fqx 'legacy-exact-ipfw-argv-observed=1' ||
    fail "exact kernel witness was not reported"
printf '%s\n' "$AUDIT_OK" | grep -Fqx 'legacy-handoff-authorized=0' ||
    fail "audit incorrectly authorized a cutover"
[ "$PROCESS" = 1 ] && [ "$MONITOR" = 1 ] &&
[ "$FW_PREPARE" = 0 ] && [ "$FW_STAGE" = 0 ] ||
    fail "strict audit modified running legacy processes/IPFW"
EXACT_OK=0
if shared_apply_legacy_audit_service >/dev/null; then
    fail "strict kernel witness failure was ignored"
fi
EXACT_OK=1 EXACT_BAD=1
if shared_apply_legacy_audit_service >/dev/null; then
    fail "unexpected strict inspector result was accepted"
fi
EXACT_BAD=0 HAS_COMMON_RECORD=1
if shared_apply_legacy_audit_service >/dev/null; then
    fail "committed/pending shared owner was adopted as legacy"
fi
HAS_COMMON_RECORD=0 PENDING_OLD=1
if shared_apply_legacy_audit_service >/dev/null; then
    fail "old Voice recovery evidence was bypassed"
fi
PENDING_OLD=0 AUDIT_PY_AVAILABLE=0
if shared_apply_legacy_audit_service >/dev/null; then
    fail "missing strict interpreter was bypassed"
fi
AUDIT_PY_AVAILABLE=1
echo 'PASS: common FD9 legacy audit uses existing exact kernel/IPFW/argv witness without handoff'

echo 'PASS: shared engine/IPFW, stopped legacy rollback and live legacy refusal'
