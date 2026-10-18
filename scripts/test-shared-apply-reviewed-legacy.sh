#!/bin/sh
set -eu
ROOT=$(mktemp -d /tmp/zapret-reviewed.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^shared_apply_reviewed_legacy_attest_service()$/,/^}$/p' "$SOURCE" > "$ROOT/attest.sh"
[ -s "$ROOT/attest.sh" ] || fail "production attestation missing"
sh -n "$ROOT/attest.sh" || fail "attestation syntax"
. "$ROOT/attest.sh"
ID=1595b71b6f6c268615c17d62a3449175
BASE=$(printf '%064d' 0 | tr 0 a)
CAND=$(printf '%064d' 0 | tr 0 b)
ACTIVE_DIR="$ROOT/runtime-v2"
BACKUP_ROOT="$ROOT/backups"
SUPERVISOR_LOOP="$ROOT/supervisor_loop.sh"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
SUPERVISOR_DAEMON_PIDFILE="$ROOT/daemon.pid"
CHILD_PIDFILE="$ROOT/engine.pid"
mkdir "$ACTIVE_DIR" "$BACKUP_ROOT" "$ROOT/work"
echo 2848 > "$CHILD_PIDFILE"
FAKE_PS="$ROOT/processes"
export FAKE_PS
COMMON_PS_BIN="$ROOT/ps"
printf '#!/bin/sh\ncat "$FAKE_PS"\n' > "$COMMON_PS_BIN"
chmod 755 "$COMMON_PS_BIN"
printf ' 2848 /usr/local/etc/zapret2/binaries/my/dvtws2 --port=989\n' > "$FAKE_PS"
shared_apply_workspace() { echo "$ROOT/work"; }
shared_apply_bundle_service() { [ "$SEAL" = ok ]; }
shared_apply_native_config() { echo "native mocked preflight"; }
shared_apply_json_field() {
    case "$1" in
       *'.base '*) echo "$ACTUAL_BASE" ;;
       *'.candidate '*) echo "$CAND" ;;
       *) return 1 ;;
    esac
}
firewall_shared_runtime() {
    [ "$IPFW" = ok ] && [ "$1" = verify-legacy ] &&
    [ "$2" = "$ACTIVE_DIR" ] && [ "$3" = "$ROOT/work/release" ]
}
launcher_is_running() { [ "$ENGINE" = ok ]; }
apply_runtime_attest_engine_inventory() { [ "$ENGINE" = ok ] && [ "$_apply_engine" = 1 ]; }
supervisor_is_running() { [ "$MONITOR" = 1 ]; }
supervisor_pidfile_read() { cat "$SUPERVISOR_MONITOR_PIDFILE"; }
SEAL=ok; ACTUAL_BASE="$BASE"; IPFW=ok; ENGINE=ok; MONITOR=0
shared_apply_reviewed_legacy_attest_service "$ID" "$BASE" "$CAND" 0 || fail "valid old state refused"
for defect in seal config ipfw engine voice_plan backup orphan monitor; do
    case "$defect" in
        seal) SEAL=bad ;;
        config) ACTUAL_BASE=$(printf '%064d' 0 | tr 0 c) ;;
        ipfw) IPFW=bad ;;
        engine) ENGINE=bad ;;
        voice_plan) : > "$ACTIVE_DIR/voice-plan.json" ;;
        backup) mkdir "$BACKUP_ROOT/runtime-v2-$ID" ;;
        orphan) printf ' 999 /bin/sh %s\n' "$SUPERVISOR_LOOP" > "$FAKE_PS" ;;
        monitor) MONITOR=1 ;;
    esac
    if shared_apply_reviewed_legacy_attest_service "$ID" "$BASE" "$CAND" 0; then
        fail "unsafe old runtime accepted: $defect"
    fi
    SEAL=ok; ACTUAL_BASE="$BASE"; IPFW=ok; ENGINE=ok; MONITOR=0
    rm -f "$ACTIVE_DIR/voice-plan.json"
    rmdir "$BACKUP_ROOT/runtime-v2-$ID" 2>/dev/null || :
    printf ' 2848 /usr/local/etc/zapret2/binaries/my/dvtws2 --port=989\n' > "$FAKE_PS"
done
echo 2345 > "$SUPERVISOR_MONITOR_PIDFILE"
printf ' 2848 /usr/local/etc/zapret2/binaries/my/dvtws2 --port=989\n 2345 /bin/sh %s %s\n' "$SUPERVISOR_LOOP" "$CHILD_PIDFILE" > "$FAKE_PS"
MONITOR=1
shared_apply_reviewed_legacy_attest_service "$ID" "$BASE" "$CAND" 1 || fail "restored supervisor refused"
printf ' 2848 /usr/local/etc/zapret2/binaries/my/dvtws2 --port=989\n 2345 /bin/sh %s %s\n 4444 /bin/sh %s %s\n' "$SUPERVISOR_LOOP" "$CHILD_PIDFILE" "$SUPERVISOR_LOOP" "$CHILD_PIDFILE" > "$FAKE_PS"
if shared_apply_reviewed_legacy_attest_service "$ID" "$BASE" "$CAND" 1; then
    fail "second independent supervisor accepted"
fi
grep -Fq 'shared-apply-recover-reviewed-legacy)' "$SOURCE" || fail "native dispatcher missing"
grep -Fq 'preflight_shared_apply_journal common-recover-reviewed-legacy' "$SOURCE" || fail "journal review gate missing"
grep -Fq 'finish-reviewed-legacy "$_review_id"' "$SOURCE" || fail "durable terminal closure missing"
echo "PASS: native reviewed legacy handoff refuses foreign states"
