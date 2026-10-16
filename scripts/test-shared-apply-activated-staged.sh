#!/bin/sh
# Exercises the real shared ACTIVATED recovery with mock process/IPFW adapters.
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/shared-activated.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^shared_apply_recover_activated_cold_service()$/,/^}$/p' "$SOURCE" > "$ROOT/recover.sh"
sh -n "$ROOT/recover.sh" || fail "production recovery syntax"
# Only the root-only durable terminal CLI is mocked; the exact shell route
# runs with injected kernel/Config observers and scoped firewall transactions.
python3 - "$ROOT/recover.sh" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
s = p.read_text()
a = '    [ -x /usr/local/bin/python3.13 ] || return 70'
assert s.count(a) == 1
s = s.replace(a, '    : # mocked native interpreter')
pattern = (r'(?m)^    /usr/local/bin/python3\.13 .* \\'
           r'\n        "finish-\$_shared_cold_phase" "\$_shared_cold_id" "\$_shared_cold_old" \|\| return 70$')
s, n = re.subn(pattern, '    finish_mock || return 70', s)
assert n == 1, "native finish contract changed"
p.write_text(s)
PY
. "$ROOT/recover.sh"
OLD_ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
NEW_ID=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
mkdir -p "$ROOT/old/release" "$ROOT/new/release"
printf 'old\n' > "$ROOT/old/release/voice-plan.json"
printf 'new\n' > "$ROOT/new/release/voice-plan.json"
ACTIVE_DIR="$ROOT/active"
BACKUP_ROOT="$ROOT/backup"
CHILD_PIDFILE="$ROOT/child.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
LOG="$ROOT/events"
shared_apply_workspace() {
    case "$1" in "$OLD_ID") echo "$ROOT/old" ;; "$NEW_ID") echo "$ROOT/new" ;; *) return 1 ;; esac
}
preflight_shared_apply_journal() { [ "$GUARD_OK" = 1 ]; }
shared_apply_bundle_service() { [ "$SEAL_OK" = 1 ]; }
shared_apply_native_config() { [ "$CONFIG_OK" = 1 ] || return 69; echo '{"result":"committed"}'; }
shared_apply_json_field() { echo committed; }
launcher_is_running() { [ "$ENGINE" = 1 ]; }
supervisor_is_running() { [ "$MONITOR" = 1 ]; }
apply_runtime_attest_engine_inventory() { [ "$_apply_engine" = 0 ] && [ "$CENSUS_OK" = 1 ]; }
atomic_verify_tree() {
    [ -d "$1" ] && [ -d "$2" ] &&
        cmp -s "$1/voice-plan.json" "$2/voice-plan.json"
}
atomic_install_tree() {
    atomic_verify_tree "$ROOT/new/release" "$ACTIVE_DIR" || return 1
    mkdir -p "$3"
    mv "$ACTIVE_DIR" "$3/failed-$$" || return 1
    cp -R "$1" "$ACTIVE_DIR" || return 1
    echo "$3/failed-$$"
}
firewall_shared_runtime() {
    echo "ipfw:$1" >> "$LOG"
    [ "$2" = "$ROOT/old/release" ] || return 1
    case "$1" in
        verify)
            if [ "$3" = - ]; then [ "$STATE" = empty ]
            else [ "$3" = "$ROOT/old/release" ] && [ "$STATE" = old ]; fi ;;
        verify-staged)
            if [ "$3" = - ]; then [ "$STATE" = retiring ]
            else [ "$3" = "$ROOT/new/release" ] && [ "$STATE" = staged ]; fi ;;
        rollback)
            [ "$3" = "$ROOT/new/release" ] && [ "$STATE" = staged ] &&
                [ "$ROLLBACK_OK" = 1 ] || return 1
            STATE=old ;;
        install)
            [ "$3" = - ] && [ "$STATE" = old ] &&
                [ "$INSTALL_OK" = 1 ] || return 1
            STATE=retiring ;;
        commit)
            [ "$3" = - ] && [ "$STATE" = retiring ] &&
                [ "$COMMIT_OK" = 1 ] || return 1
            STATE=empty ;;
        *) return 1 ;;
    esac
}
finish_mock() { echo finished >> "$LOG"; [ "$FINISH_OK" = 1 ]; }
reset() {
    rm -rf "$ACTIVE_DIR" "$BACKUP_ROOT"
    cp -R "$ROOT/new/release" "$ACTIVE_DIR"
    STATE=staged GUARD_OK=1 SEAL_OK=1 CONFIG_OK=1
    ENGINE=0 MONITOR=0 CENSUS_OK=1
    ROLLBACK_OK=1 INSTALL_OK=1 COMMIT_OK=1 FINISH_OK=1
    : > "$LOG"
}
check() {
    expected="$1"; shift
    set +e
    shared_apply_recover_activated_cold_service "$@" > "$ROOT/result"
    actual=$?
    set -e
    [ "$actual" -eq "$expected" ] || fail "state=$STATE status=$actual expected=$expected"
}
OWNER="activated $NEW_ID voice $OLD_ID strategies"
reset
check 0 "$OWNER"
[ "$STATE" = empty ] && atomic_verify_tree "$ROOT/old/release" "$ACTIVE_DIR" ||
    fail "staged IPFW and old runtime were not restored"
grep -qx "recovered-activated-id=$NEW_ID" "$ROOT/result" || fail "no recovery receipt"
grep -q 'ipfw:rollback' "$LOG" && grep -q 'ipfw:install' "$LOG" &&
    grep -q 'ipfw:commit' "$LOG" || fail "missing reversible IPFW steps"
for state in old retiring empty; do
    reset; STATE="$state"
    check 0 "$OWNER"
    [ "$STATE" = empty ] && atomic_verify_tree "$ROOT/old/release" "$ACTIVE_DIR" ||
        fail "$state failed to resume"
done
reset; STATE=foreign
check 69 "$OWNER"
[ "$STATE" = foreign ] && ! grep -Eq 'ipfw:(rollback|install|commit)' "$LOG" ||
    fail "foreign kernel was mutated"
reset; ENGINE=1
check 69 "$OWNER"
[ "$STATE" = staged ] || fail "live engine triggered rollback"
reset; CENSUS_OK=0
check 69 "$OWNER"
[ "$STATE" = staged ] || fail "orphan engine triggered rollback"
reset; CONFIG_OK=0
check 69 "$OWNER"
[ "$STATE" = staged ] || fail "stale Config triggered rollback"
reset
printf 'foreign\n' > "$ACTIVE_DIR/voice-plan.json"
check 69 "$OWNER"
[ "$STATE" = staged ] || fail "unsealed runtime triggered rollback"
reset; ROLLBACK_OK=0
check 70 "$OWNER"
[ "$STATE" = staged ] || fail "failed rollback misreported complete"
reset; STATE=old; INSTALL_OK=0
check 70 "$OWNER"
[ "$STATE" = old ] || fail "failed removal misreported complete"
reset; COMMIT_OK=0
check 70 "$OWNER"
[ "$STATE" = retiring ] || fail "failed cleanup misreported complete"
reset; FINISH_OK=0
check 70 "$OWNER"
[ "$STATE" = empty ] && atomic_verify_tree "$ROOT/old/release" "$ACTIVE_DIR" ||
    fail "terminal failure erased restoration evidence"
FINISH_OK=1
check 0 "$OWNER"
# Crash after install/staged IPFW but before durable "activated" transition:
# it is still the SAME sealed candidate and previous native Config.
ACTIVATING="activating $NEW_ID voice $OLD_ID strategies"
reset
check 0 "$ACTIVATING"
[ "$STATE" = empty ] && atomic_verify_tree "$ROOT/old/release" "$ACTIVE_DIR" ||
    fail "activating staged IPFW and old runtime were not restored"
grep -qx "recovered-activating-id=$NEW_ID" "$ROOT/result" ||
    fail "activating did not finalize with its own journal phase"
grep -q '^ipfw:rollback$' "$LOG" || fail "activating skipped exact old IPFW rollback"
for state in old retiring empty; do
    reset; STATE="$state"
    check 0 "$ACTIVATING"
    [ "$STATE" = empty ] && atomic_verify_tree "$ROOT/old/release" "$ACTIVE_DIR" ||
        fail "activating $state retry failed"
done
reset; STATE=foreign
check 69 "$ACTIVATING"
[ "$STATE" = foreign ] && ! grep -Eq 'ipfw:(rollback|install|commit)' "$LOG" ||
    fail "activating accepted foreign IPFW"
reset; ENGINE=1
check 69 "$ACTIVATING"
[ "$STATE" = staged ] || fail "activating touched live engine"
reset; CENSUS_OK=0
check 69 "$ACTIVATING"
[ "$STATE" = staged ] || fail "activating ignored orphan engine"
reset; CONFIG_OK=0
check 69 "$ACTIVATING"
[ "$STATE" = staged ] || fail "activating ignored stale Config"
reset
printf 'partial\n' > "$ACTIVE_DIR/voice-plan.json"
check 69 "$ACTIVATING"
[ "$STATE" = staged ] || fail "activating accepted partial installed release"
reset; ROLLBACK_OK=0
check 70 "$ACTIVATING"
[ "$STATE" = staged ] || fail "activating failure cleared staged IPFW"
reset; FINISH_OK=0
check 70 "$ACTIVATING"
[ "$STATE" = empty ] && atomic_verify_tree "$ROOT/old/release" "$ACTIVE_DIR" ||
    fail "activating terminal failure erased restored owner"
echo 'PASS: activated and activating staged IPFW recovery and fail-closed states'
