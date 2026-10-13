#!/bin/sh
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/shared-boot.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^shared_apply_boot_service()$/,/^}$/p' "$SOURCE" > "$ROOT/boot.sh"
sh -n "$ROOT/boot.sh" || fail "boot shell syntax"
. "$ROOT/boot.sh"
ID=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
mkdir -p "$ROOT/work/release"
LOG="$ROOT/steps.log"
preflight_voice_cutover_journals() { echo guard:$1 >> "$LOG"; [ "$GUARD" -eq 0 ]; }
shared_apply_bundle_service() { echo seal:$1 >> "$LOG"; [ "$SEAL" -eq 0 ]; }
shared_apply_native_config() { echo config:$1 >> "$LOG"; [ "$CONFIG" -eq 0 ] || return 69; echo '{"result":"committed","enabled":"1"}'; }
shared_apply_json_field() { case "$1" in *".enabled"*) echo 1 ;; *".result"*) echo committed ;; *) return 1 ;; esac; }
shared_apply_workspace() { echo "$ROOT/work"; }
apply_runtime_activate() { echo activate >> "$LOG"; [ "$ACTIVE" -eq 0 ]; }
apply_runtime_commit() { echo commit >> "$LOG"; [ "$COMMIT" -eq 0 ]; }
reset() { GUARD=0; SEAL=0; CONFIG=0; ACTIVE=0; COMMIT=0; : > "$LOG"; }
expect() {
  expected="$1"; shift
  set +e
  shared_apply_boot_service "committed $ID voice" > "$ROOT/output"
  status="$?"
  set -e
  [ "$status" -eq "$expected" ] || fail "boot status $status expected $expected"
  got=$(tr "\n" " " < "$LOG")
  [ "$got" = "$*" ] || fail "boot steps: $got"
}
reset
expect 0 'guard:common-apply seal:verify config:saved activate commit '
grep -Fqx "native-common-boot=$ID" "$ROOT/output" || fail "boot receipt"
reset; SEAL=1
expect 69 'guard:common-apply seal:verify '
reset; CONFIG=1
expect 69 'guard:common-apply seal:verify config:saved '
reset; ACTIVE=1
expect 70 'guard:common-apply seal:verify config:saved activate '
reset; COMMIT=1
expect 70 'guard:common-apply seal:verify config:saved activate commit '
reset; GUARD=1
expect 69 'guard:common-apply '
reset
if shared_apply_boot_service "restored $ID voice"; then fail "foreign owner booted"; fi
if shared_apply_boot_service "committed /tmp/x voice"; then fail "path injection booted"; fi
grep -Fq "shared_apply_boot_service" "$SOURCE" || fail "common native boot function absent"
grep -Fq "start|reconfigure)" "$SOURCE" || fail "normal startup not routed through common owner"
grep -Fq 'shared_apply_boot_service "$_shared_owner"' "$SOURCE" || fail "common boot not called from lifecycle"
# Exercise the ACTUAL lifecycle wrapper, including the original lockf FD9.
# These tests never touch a real system lock or OPNsense configuration.
sed -n '/^service_with_lifecycle_lock()$/,/^}$/p' "$SOURCE" > "$ROOT/lifecycle.sh"
sh -n "$ROOT/lifecycle.sh" || fail "lifecycle shell syntax"
. "$ROOT/lifecycle.sh"
cat > "$ROOT/lockf" <<'MOCK'
#!/bin/sh
[ "$1" = -s ] && [ "$2" = -t ] && [ "$4" = 9 ]
MOCK
chmod 700 "$ROOT/lockf"
LOCKF_BIN="$ROOT/lockf"
LIFECYCLE_LOCK_FILE="$ROOT/owner.lock"
shared_apply_has_record_service() { [ "$HAS_RECORD" = 1 ]; }
shared_apply_inspect_service() { [ "$OWNER_OK" = 1 ] || return 69; echo "$OWNER"; }
shared_apply_recover_saved_service() { echo saved-recovered >> "$LOG"; [ "$SAVED_OK" = 0 ] || return 69; }
shared_apply_recover_prepared_service() {
    echo prepared-recovered >> "$LOG"
    [ "$RECOVER" = 0 ] || return 69
    [ "$RECOVER_OWNER" = "-" ] || OWNER="$RECOVER_OWNER"
}
shared_apply_boot_service() { echo "common:$1" >> "$LOG"; }
shared_apply_stop_service() { echo "common-stop:$1" >> "$LOG"; [ "$STOP_OK" = 0 ] || return 70; }
preflight_voice_cutover_journals() { echo "legacy-guard" >> "$LOG"; }
service_dispatch() { echo "legacy:$1" >> "$LOG"; }
check_route() {
    expected="$1"; shift
    : > "$LOG"
    set +e
    service_with_lifecycle_lock 5 "$@"
    result="$?"
    set -e
    [ "$result" = "$expected" ] || fail "lifecycle returned $result instead of $expected"
}
RECOVER=0 RECOVER_OWNER=- SAVED_OK=0 STOP_OK=0
HAS_RECORD=1 OWNER_OK=1 OWNER="committed $ID voice"
check_route 0 start
[ "$(cat "$LOG")" = "common:committed $ID voice" ] ||
    fail "committed start fell through to legacy runtime"
check_route 0 reconfigure
[ "$(cat "$LOG")" = "common:committed $ID voice" ] ||
    fail "committed reconfigure fell through to legacy runtime"
check_route 0 stop
[ "$(cat "$LOG")" = "common-stop:committed $ID voice" ] || fail "stop dropped to legacy"
check_route 0 restart
[ "$(tr '\n' ' ' < "$LOG")" = "common-stop:committed $ID voice common:committed $ID voice " ] || fail "restart did not keep native owner"
STOP_OK=1
check_route 70 restart
[ "$(cat "$LOG")" = "common-stop:committed $ID voice" ] || fail "failed stop started replacement"
STOP_OK=0
OWNER=restored
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = 'legacy-guard legacy:start ' ] ||
    fail "restored owner did not use ordinary legacy lifecycle"
OWNER="prepared $ID voice"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = 'prepared-recovered legacy-guard legacy:start ' ] ||
    fail "prepared recovery did not resume ordinary runtime"
RECOVER_OWNER="committed bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb voice"
OWNER="prepared $ID voice"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = "prepared-recovered common:committed bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb voice " ] ||
    fail "recovered previous common owner was replaced by legacy boot"
RECOVER_OWNER=-
RECOVER=1
check_route 69 reconfigure
[ "$(cat "$LOG")" = "prepared-recovered" ] ||
    fail "recovery failure fell through to legacy"
RECOVER=0
OWNER="config-saved $ID voice"
check_route 0 start
[ "$(cat "$LOG")" = "saved-recovered" ] ||
    fail "config-saved phase did not route through native recovery"
SAVED_OK=1
check_route 69 reconfigure
[ "$(cat "$LOG")" = "saved-recovered" ] ||
    fail "failed native post-save recovery fell through to legacy"
SAVED_OK=0
OWNER=pending
check_route 69 stop
[ ! -s "$LOG" ] || fail "pending stop touched runtime"
check_route 69 restart
[ ! -s "$LOG" ] || fail "pending restart touched runtime"
check_route 69 start
[ ! -s "$LOG" ] || fail "pending owner changed lifecycle"
OWNER_OK=0
check_route 69 reconfigure
[ ! -s "$LOG" ] || fail "corrupt owner was ignored"
HAS_RECORD=0 OWNER_OK=1
check_route 0 stop
[ "$(tr '\n' ' ' < "$LOG")" = 'legacy-guard legacy:stop ' ] || fail "legacy stop lost"
check_route 0 restart
[ "$(tr '\n' ' ' < "$LOG")" = 'legacy-guard legacy:restart ' ] || fail "legacy restart lost"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = 'legacy-guard legacy:start ' ] ||
    fail "no common journal changed ordinary legacy startup"
echo 'PASS: committed native common owner routes boot through sealed release and fresh saved Config'
