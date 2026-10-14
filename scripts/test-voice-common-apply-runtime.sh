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
# Native private forward uses the REAL production apply_runtime_activate
# after the old PoC process, marker and IPFW have been retired by the sole
# journal owner. No second engine, firewall, backup writer or Config saver.
ACTIVE_DIR="$ROOT/retired-active"
BACKUP_ROOT="$ROOT/retired-backups"
mkdir "$ACTIVE_DIR"
printf '%s\n' old-release > "$ACTIVE_DIR/old-owner-marker"
for field in dvtws.args tcp-ports.txt udp-ports.txt; do
    printf '%s\n' old > "$ACTIVE_DIR/$field"
done
PROCESS=0 MONITOR=0 FW=empty FW_STAGE=0
apply_runtime_clear
RETIRE_ID=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
if apply_runtime_activate_retired_legacy "$ROOT/one" invalid; then
    fail "unsealed retired predecessor ID accepted"
fi
[ "$(cat "$ACTIVE_DIR/old-owner-marker")" = old-release ] &&
[ "$PROCESS" = 0 ] && [ "$FW" = empty ] ||
    fail "invalid private forward modified live old resources"
PROCESS=1 MONITOR=1
if apply_runtime_activate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "live old process bypassed common runtime"
fi
PROCESS=0 MONITOR=0 FW=active
if apply_runtime_activate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "non-retired old IPFW bypassed common runtime"
fi
FW=empty
apply_runtime_activate_retired_legacy "$ROOT/one" "$RETIRE_ID" ||
    fail "private retired old owner did not use common activation"
EXPECTED_RETIRE_BACKUP="$BACKUP_ROOT/$(basename "$ACTIVE_DIR")-$RETIRE_ID"
[ "$APPLY_BACKUP" = "$EXPECTED_RETIRE_BACKUP" ] &&
[ -f "$EXPECTED_RETIRE_BACKUP/old-owner-marker" ] &&
[ "$APPLY_OLD_RUNNING" = 0 ] && [ "$APPLY_NEW_RUNNING" = 1 ] &&
[ "$PROCESS" = 1 ] && [ "$MONITOR" = 1 ] &&
[ "$FW" = active ] && [ "$FW_STAGE" = 1 ] ||
    fail "retired forward lost original backup or kernel precommit"
# The original activation ran in a child shell. The next child has
# NO APPLY_* globals: it must reconstruct only physically attested state.
apply_runtime_clear
FW_STAGE=0
if apply_runtime_rehydrate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "missing staged IPFW accepted after child exited"
fi
FW_STAGE=1
MONITOR=0
if apply_runtime_rehydrate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "dead supervisor accepted by reconstructed owner"
fi
MONITOR=1
mv "$EXPECTED_RETIRE_BACKUP/tcp-ports.txt" "$EXPECTED_RETIRE_BACKUP/tcp-ports.tmp"
if apply_runtime_rehydrate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "corrupt old rollback backup accepted by reconstructed owner"
fi
mv "$EXPECTED_RETIRE_BACKUP/tcp-ports.tmp" "$EXPECTED_RETIRE_BACKUP/tcp-ports.txt"
mkdir "$ROOT/.retired-active.stage.$RETIRE_ID"
if apply_runtime_rehydrate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "interrupted atomic stage adopted as complete native owner"
fi
rmdir "$ROOT/.retired-active.stage.$RETIRE_ID"
apply_runtime_rehydrate_retired_legacy "$ROOT/one" "$RETIRE_ID" ||
    fail "verified installed native owner could not be rehydrated"
[ "$APPLY_PHASE" = activated ] && [ "$APPLY_OLD" = - ] &&
[ "$APPLY_BACKUP" = "$EXPECTED_RETIRE_BACKUP" ] &&
[ "$APPLY_IPFW_INSTALLED" = 1 ] ||
    fail "reconstructed owner lost exact precommit context"
if apply_runtime_rehydrate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "duplicate native activation context accepted"
fi
if apply_runtime_activate_retired_legacy "$ROOT/one" "$RETIRE_ID"; then
    fail "same private forward started a second engine"
fi
apply_runtime_restore || fail "retired original runtime rollback failed"
[ "$(cat "$ACTIVE_DIR/old-owner-marker")" = old-release ] &&
[ "$PROCESS" = 0 ] && [ "$MONITOR" = 0 ] && [ "$FW" = empty ] &&
[ "$FW_STAGE" = 0 ] ||
    fail "retired previous runtime not restored exactly"
apply_runtime_activate_retired_legacy "$ROOT/one" "$RETIRE_ID" ||
    fail "retired common forward could not restart after verified manual restore"
apply_runtime_clear
apply_runtime_rehydrate_retired_legacy "$ROOT/one" "$RETIRE_ID" ||
    fail "second child could not reconstruct context for future Config commit"
apply_runtime_commit || fail "native common commit from retired legacy failed"
apply_runtime_verify_retired_legacy_committed "$ROOT/one" "$RETIRE_ID" ||
    fail "new shared owner failed post-commit read-only attestation"
FW_STAGE=1
if apply_runtime_verify_retired_legacy_committed "$ROOT/one" "$RETIRE_ID"; then
    fail "stale native IPFW rollback stage accepted after commit"
fi
FW_STAGE=0
MONITOR=0
if apply_runtime_verify_retired_legacy_committed "$ROOT/one" "$RETIRE_ID"; then
    fail "dead supervisor accepted as committed native owner"
fi
MONITOR=1
[ "$FW_STAGE" = 0 ] && [ "$PROCESS" = 1 ] &&
[ -f "$EXPECTED_RETIRE_BACKUP/old-owner-marker" ] ||
    fail "native common completion prematurely destroyed old runtime backup"

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


# The outer production CLI MUST route both diagnostic actions through the
# original FD9 lifecycle. Merely adding service_dispatch is not enough.
grep -Fq '|shared-apply-run|shared-apply-legacy-audit|shared-apply-legacy-qualify|shared-apply-legacy-capture|' "$SERVICE_SOURCE" ||
    fail "legacy diagnostic commands bypass original FD9 lifecycle lock"
grep -Fq 'shared-apply-legacy-qualify)' "$SERVICE_SOURCE" ||
    fail "candidate qualification is not dispatched"
QUAL_SCRIPT="$ROOT/legacy-qualify.sh"
sed -n '/^shared_apply_legacy_candidate_service()$/,/^}$/p' "$SERVICE_SOURCE" > "$QUAL_SCRIPT"
sh -n "$QUAL_SCRIPT" || fail "production legacy qualifier is not valid sh"
. "$QUAL_SCRIPT"
QUAL_ID=11111111111111111111111111111111
QUAL_BASE=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
QUAL_CANDIDATE=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
QUAL_MODE=1
QUAL_SEAL=1 QUAL_CONFIG=1 QUAL_VALID=1 QUAL_RACE=0
DVTWS_BIN="$ROOT/engine"
# These mocks are scoped to the extracted service function: old IPFW/argv
# still comes only from the strict Python witness (mocked above).
shared_apply_require_tools() { return 0; }
shared_apply_workspace() { echo "$ROOT/qual-work"; }
shared_apply_bundle_service() { [ "$1" = verify ] && [ "$2" = "$QUAL_ID" ] && [ "$QUAL_SEAL" = 1 ]; }
shared_apply_native_config() {
    [ "$1" = preflight ] && [ "$2" = "$QUAL_ID" ] && [ "$3" = voice ] &&
    [ "$QUAL_CONFIG" = 1 ] || return 69
    if [ "$QUAL_RACE" = 1 ]; then
        QUAL_RACE=2
        printf '%s\n' '{"mode":"changed"}'
    else
        printf '%s\n' '{"mode":"stable"}'
    fi
}
shared_apply_json_field() {
    case "$1" in
       *'.enabled'*) echo "$QUAL_MODE" ;;
       *'.base'*) echo "$QUAL_BASE" ;;
       *'.candidate'*) echo "$QUAL_CANDIDATE" ;;
       *) return 69 ;;
    esac
}
validator_validate_runtime_modes() { [ "$1" = "$ROOT/qual-work/release" ] && [ "$QUAL_VALID" = 1 ]; }
validator_validate_engine_mapped() {
    [ "$1" = "$DVTWS_BIN" ] &&
    [ "$2" = "$ROOT/qual-work/release/dvtws.args" ] &&
    [ "$3" = "$ACTIVE_DIR" ] &&
    [ "$4" = "$ROOT/qual-work/release" ] &&
    [ "$QUAL_VALID" = 1 ]
}
mkdir -p "$ROOT/qual-work/release"
printf '%s\n' '--port=989' > "$ROOT/qual-work/release/dvtws.args"
# Ensure fixture outputs canonical full digest lengths, not placeholders.
legacy_exact_fixture() {
    [ "$EXACT_OK" = 1 ] || return 69
    printf '%s\n' \
        'legacy-voice-preflight=legacy-poc-full-live-baseline-observed-not-owned' \
        "legacy-voice-ipfw-sha256=$QUAL_BASE" \
        "legacy-voice-managed-sha256=$QUAL_CANDIDATE" \
        'legacy-voice-ownership=not-adopted' \
        'voice-on=blocked'
}
HAS_COMMON_RECORD=0 PENDING_OLD=0 AUDIT_PY_AVAILABLE=1 EXACT_OK=1 EXACT_BAD=0
PROCESS=1 MONITOR=1 LEGACY_RULES=1
good=$(shared_apply_legacy_candidate_service "$QUAL_ID") || fail "bound legacy candidate audit refused"
printf '%s\n' "$good" | grep -Fqx "legacy-qualified-candidate=$QUAL_ID" ||
    fail "candidate identity missing"
printf '%s\n' "$good" | grep -Fqx 'legacy-handoff-authorized=0' ||
    fail "candidate qualification improperly allowed cutover"
QUAL_MODE=0
if shared_apply_legacy_candidate_service "$QUAL_ID" >/dev/null; then fail "legacy handoff accepted Voice OFF"; fi
QUAL_MODE=1 QUAL_VALID=0
if shared_apply_legacy_candidate_service "$QUAL_ID" >/dev/null; then fail "unsafe candidate accepted"; fi
QUAL_VALID=1 QUAL_SEAL=0
if shared_apply_legacy_candidate_service "$QUAL_ID" >/dev/null; then fail "unsealed bundle accepted"; fi
QUAL_SEAL=1 EXACT_OK=0
if shared_apply_legacy_candidate_service "$QUAL_ID" >/dev/null; then fail "failed old kernel witness accepted"; fi
EXACT_OK=1 HAS_COMMON_RECORD=1
if shared_apply_legacy_candidate_service "$QUAL_ID" >/dev/null; then fail "shared owner accepted as legacy"; fi
HAS_COMMON_RECORD=0
if shared_apply_legacy_candidate_service malformed >/dev/null; then fail "invalid candidate ID accepted"; fi
echo 'PASS: FD9 candidate-bound legacy kernel witness refuses OFF/foreign/conflicts'


# Real production wrapper, but mocked lower-level no-mutation old capture:
# only exact five-domain sealed predecessor and the same candidate qualify.
# Require membership in the OUTER original-FD9 dispatch, not in the
# service_dispatch handler. Individual exact shell case tokens are stable
# regardless of which command happens to be last when more are added.
OUTER_ROUTES=$(sed -n '/^case "${1:-}" in$/,$p' "$SERVICE_SOURCE")
[ -n "$OUTER_ROUTES" ] || fail "missing original-FD9 outer service dispatch"
for command in shared-apply-legacy-audit shared-apply-legacy-qualify \
    shared-apply-legacy-capture shared-apply-legacy-arm \
    shared-apply-legacy-cancel shared-apply-legacy-begin; do
    printf '%s\n' "$OUTER_ROUTES" | grep -Eq "(^|\\|)${command}(\\||\\))" ||
        fail "legacy operator $command bypasses original FD9"
done
CAPTURE_SCRIPT="$ROOT/common-legacy-capture.sh"
sed -n '/^shared_apply_legacy_capture_service()$/,/^}$/p' "$SERVICE_SOURCE" > "$CAPTURE_SCRIPT"
sh -n "$CAPTURE_SCRIPT" || fail "native predecessor wrapper is malformed"
python3 - "$CAPTURE_SCRIPT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
old='    [ -x /usr/local/bin/python3.13 ] &&\n    [ -r "${BACKEND_DIR}/voice_native_legacy_predecessor_route.py" ] || return 69'
assert old in s, "fixed native predecessor executable missing"
s=s.replace(old,'    [ "$CAPTURE_AVAILABLE" = 1 ] || return 69')
old='    _legacy_capture_result=$(/usr/local/bin/python3.13 \\\n        "${BACKEND_DIR}/voice_native_legacy_predecessor_route.py" \\\n        capture-common "$_legacy_capture_id") || return 70'
assert old in s, "candidate-rooted previous-five capture missing"
s=s.replace(old,'    _legacy_capture_result=$(legacy_previous_fixture "$_legacy_capture_id") || return 70')
p.write_text(s)
PY
. "$CAPTURE_SCRIPT"
CAPTURE_AVAILABLE=1 CAPTURE_READY=1 CAPTURE_DRIFT=0
CAPTURE_CALLS=0
shared_apply_legacy_candidate_service() {
    [ "$1" = "$QUAL_ID" ] && [ "$CAPTURE_READY" = 1 ] || return 69
    if [ "$CAPTURE_DRIFT" = 1 ]; then
        if [ -f "$ROOT/capture-audit-seen" ]; then
            echo 'changed-prev-state'
        else
            : > "$ROOT/capture-audit-seen"
            echo 'stable-old-state'
        fi
    else
        echo 'stable-old-state'
    fi
}
legacy_previous_fixture() {
    [ "$1" = "$QUAL_ID" ] && [ "$CAPTURE_AVAILABLE" = 1 ] || return 70
    : > "$ROOT/immutable-legacy-evidence"
    printf '%s\n' \
        "legacy-voice-bound-candidate=$QUAL_ID" \
        'legacy-voice-predecessor=legacy-poc-previous-and-reverse-plan-sealed-quiescence-pending' \
        'native-voice-public-apply=disabled'
}
record=$(shared_apply_legacy_capture_service "$QUAL_ID") || fail "bound old predecessor not captured"
printf '%s\n' "$record" | grep -Fqx 'legacy-backup-sealed=1' ||
    fail "durable predecessor not recorded as an inactive backup"
printf '%s\n' "$record" | grep -Fqx 'legacy-handoff-authorized=0' ||
    fail "operator backup incorrectly authorized live mutation"
CAPTURE_READY=0
if shared_apply_legacy_capture_service "$QUAL_ID" >/dev/null; then
    fail "unqualified old source was captured"
fi
CAPTURE_READY=1 CAPTURE_AVAILABLE=0
if shared_apply_legacy_capture_service "$QUAL_ID" >/dev/null; then
    fail "missing previous-five writer was ignored"
fi
CAPTURE_AVAILABLE=1
if shared_apply_legacy_capture_service bad >/dev/null; then
    fail "untrusted operation id reached old predecessor"
fi
rm -f "$ROOT/capture-audit-seen"
CAPTURE_DRIFT=1
if shared_apply_legacy_capture_service "$QUAL_ID" >/dev/null; then
    fail "changed old IPFW/argv/Config witness accepted after predecessor snapshot"
fi
[ -f "$ROOT/immutable-legacy-evidence" ] ||
    fail "failed post-capture audit removed sealed predecessor evidence"
CAPTURE_DRIFT=0
echo 'PASS: candidate-bound full legacy predecessor capture requires FD9 and no live mutation'


# The only new durable write is a bounded PREPARED record in the EXISTING
# common journal. Extract production shell, replace the fixed root Python
# CLI with an in-memory proof, and assert no runtime/kernel mutation.
ARM_SCRIPT="$ROOT/common-legacy-arm.sh"
sed -n '/^shared_apply_legacy_arm_service()$/,/^}$/p' "$SERVICE_SOURCE" > "$ARM_SCRIPT"
sh -n "$ARM_SCRIPT" || fail "production legacy arm is not valid sh"
python3 - "$ARM_SCRIPT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='    [ -x /usr/local/bin/python3.13 ] &&\n    [ -r "${BACKEND_DIR}/shared_apply_operation.py" ] || return 69'
assert old in s, "fixed common journal CLI missing"
s=s.replace(old,'    [ "$ARM_PY_AVAILABLE" = 1 ] || return 69')
old='    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \\\n        arm-legacy "$_legacy_arm_id" "$_legacy_arm_base" \\\n        "$_legacy_arm_candidate" "$_legacy_arm_fields"'
assert old in s, "native common journal arm command missing"
s=s.replace(old,'''    [ "$_legacy_arm_id" = "$QUAL_ID" ] &&
    [ "$_legacy_arm_base" = "$QUAL_BASE" ] &&
    [ "$_legacy_arm_candidate" = "$QUAL_CANDIDATE" ] &&
    [ "$_legacy_arm_fields" = "-" ] || return 69
    printf 'journal-prepared:%s\\n' "$_legacy_arm_id" >> "$LOG"
    printf 'legacy-armed-id=%s\\nlegacy-handoff-authorized=0\\n' "$_legacy_arm_id"''')
p.write_text(s)
PY
. "$ARM_SCRIPT"
# Restore shared qualifier and writer mocks from previous fixture.
shared_apply_legacy_candidate_service() {
    [ "$1" = "$QUAL_ID" ] && [ "$ARM_QUALIFIED" = 1 ] || return 69
    if [ "$ARM_DRIFT" = 1 ]; then
        if [ -e "$ROOT/arm-observed" ]; then echo changed
        else : > "$ROOT/arm-observed"; echo stable; fi
    else echo stable; fi
}
shared_apply_require_tools() { [ "$ARM_TOOLS" = 1 ]; }
shared_apply_native_config() {
    [ "$1" = preflight ] && [ "$2" = "$QUAL_ID" ] &&
    [ "$3" = voice ] && [ "$ARM_CONFIG" = 1 ] || return 69
    echo '{"enabled":"1","base":"candidate","fields":[]}'
}
shared_apply_json_field() {
    case "$1" in
        *'.enabled'*) [ "$ARM_ON" = 1 ] && echo 1 ;;
        *'.base'*) echo "$QUAL_BASE" ;;
        *'.candidate'*) echo "$QUAL_CANDIDATE" ;;
        *'.fields'*) echo "-" ;;
        *) return 69 ;;
    esac
}
shared_apply_bundle_service() {
    [ "$1" = verify ] && [ "$2" = "$QUAL_ID" ] && [ "$ARM_SEAL" = 1 ]
}
shared_apply_workspace() { echo "$ROOT/qual-work"; }
mkdir -p "$ROOT/qual-work/legacy-backup"
ARM_PY_AVAILABLE=1 ARM_QUALIFIED=1 ARM_TOOLS=1 ARM_CONFIG=1 ARM_ON=1 ARM_SEAL=1 ARM_DRIFT=0
LOG="$ROOT/common-arm.log"
: > "$LOG"
arm_report=$(shared_apply_legacy_arm_service "$QUAL_ID") || fail "sealed predecessor did not arm"
printf '%s\n' "$arm_report" | grep -Fqx 'legacy-handoff-authorized=0' ||
    fail "armed old predecessor incorrectly allowed mutation"
grep -Fqx "journal-prepared:$QUAL_ID" "$LOG" ||
    fail "operator arm failed to record one common prepared intent"
for fault in ARM_QUALIFIED ARM_TOOLS ARM_CONFIG ARM_ON ARM_SEAL ARM_PY_AVAILABLE; do
    : > "$LOG"
    eval "$fault=0"
    if shared_apply_legacy_arm_service "$QUAL_ID" >/dev/null; then
        fail "unsafe legacy arm ignored $fault"
    fi
    [ ! -s "$LOG" ] || fail "unsafe legacy arm wrote journal under $fault"
    eval "$fault=1"
done
: > "$LOG"
ARM_DRIFT=1
rm -f "$ROOT/arm-observed"
if shared_apply_legacy_arm_service "$QUAL_ID" >/dev/null; then
    fail "changing legacy owner was armed despite two different kernel witnesses"
fi
[ ! -s "$LOG" ] || fail "changing legacy owner wrote common journal"
ARM_DRIFT=0
: > "$LOG"
if shared_apply_legacy_arm_service bad >/dev/null; then
    fail "invalid old operation ID reached common journal"
fi
[ ! -s "$LOG" ] || fail "invalid old operation ID wrote common journal"
echo 'PASS: FD9 legacy predecessor is armed only as blocked durable common prepared record'

# Confirm the only user-facing cancellation action is operator-only under
# original FD9, and uses the pinned old FreeBSD read-only proof before the
# sole common-journal terminal write. No backup is removed automatically.
CANCEL_SCRIPT="$ROOT/common-legacy-cancel.sh"
sed -n '/^shared_apply_legacy_cancel_service()$/,/^}$/p' "$SERVICE_SOURCE" > "$CANCEL_SCRIPT"
sh -n "$CANCEL_SCRIPT" || fail "legacy cancellation production shell syntax invalid"
grep -Fq 'cancel-common "$_legacy_cancel_id"' "$CANCEL_SCRIPT" ||
    fail "legacy cancellation does not reuse fixed old predecessor route"
grep -Fq '|shared-apply-legacy-arm|shared-apply-legacy-cancel|shared-apply-legacy-begin)' "$SERVICE_SOURCE" ||
    fail "legacy cancel command not protected by original FD9 lifecycle"
echo 'PASS: pristine old owner cancellation uses strict fixed FreeBSD route and original FD9'

# Exact production command must persist the shared journal boundary under
# original FD9 WITHOUT calling engine stop or changing IPFW/Config.
BEGIN_SCRIPT="$ROOT/common-legacy-begin.sh"
sed -n '/^shared_apply_legacy_begin_service()$/,/^}$/p' "$SERVICE_SOURCE" > "$BEGIN_SCRIPT"
sh -n "$BEGIN_SCRIPT" || fail "legacy begin production shell syntax invalid"
grep -Fq 'begin-common "$_legacy_begin_id"' "$BEGIN_SCRIPT" ||
    fail "quiescing does not call the fixed FreeBSD predecessor route"
grep -Fq '|shared-apply-legacy-cancel|shared-apply-legacy-begin)' "$SERVICE_SOURCE" ||
    fail "legacy quiescing not protected by original FD9"
if grep -Eq 'launcher_stop|supervisor_stop|firewall_remove|apply_runtime_activate' "$BEGIN_SCRIPT"; then
    fail "quiescing accidentally crossed mutation boundary"
fi
echo 'PASS: durable common quiescing is published before any old process stop'
echo 'PASS: shared engine/IPFW, stopped legacy rollback and live legacy refusal'
