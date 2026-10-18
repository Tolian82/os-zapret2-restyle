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
mkdir -p "$ROOT/work/release" "$ROOT/active"
ACTIVE_DIR="$ROOT/active"
CHILD_PIDFILE="$ROOT/child.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/supervisor.pid"
LOG="$ROOT/steps.log"
common_error() { echo "ERROR: $*" >&2; }
preflight_shared_apply_journal() { echo guard:$1 >> "$LOG"; [ "$GUARD" -eq 0 ]; }
shared_apply_bundle_service() { echo seal:$1 >> "$LOG"; [ "$SEAL" -eq 0 ]; }
shared_apply_native_config() { echo config:$1 >> "$LOG"; [ "$CONFIG" -eq 0 ] || return 69; echo '{"result":"committed","enabled":"'"$BOOT_ENABLED"'"}'; }
shared_apply_json_field() { case "$1" in *".enabled"*) echo "$BOOT_ENABLED" ;; *".result"*) echo committed ;; *) return 1 ;; esac; }
shared_apply_workspace() { echo "$ROOT/work"; }
apply_runtime_activate() {
  echo activate >> "$LOG"
  [ "$ACTIVE" -eq 0 ] || return 1
  # Native cold boot starts the exact selected common ON/OFF mode.
  ENGINE="$BOOT_ENABLED"
  MONITOR="$BOOT_ENABLED"
}
apply_runtime_commit() {
  echo commit >> "$LOG"
  [ "$COMMIT" -eq 0 ] || return 1
  # Fault injection AFTER the irreversible IPFW COMMIT, not before it.
  [ "$POST_ENGINE_LOST" -eq 0 ] || ENGINE=0
  [ "$POST_MONITOR_LOST" -eq 0 ] || MONITOR=0
}
launcher_is_running() { [ "$ENGINE" -eq 1 ]; }
supervisor_is_running() { [ "$MONITOR" -eq 1 ]; }
atomic_verify_tree() {
  echo tree-verify >> "$LOG"
  [ "$TREE_OK" -eq 1 ] && [ "$POST_TREE_DRIFT" -eq 0 ]
}
apply_runtime_probe() {
  echo probe:$2 >> "$LOG"
  [ "$PROBE_OK" -eq 1 ] && [ "$POST_PROBE_DRIFT" -eq 0 ]
}
reset() {
  GUARD=0; SEAL=0; CONFIG=0; ACTIVE=0; COMMIT=0
  ENGINE=0; MONITOR=0; TREE_OK=1; PROBE_OK=1; BOOT_ENABLED=1
  POST_TREE_DRIFT=0; POST_PROBE_DRIFT=0
  POST_ENGINE_LOST=0; POST_MONITOR_LOST=0
  : > "$LOG"
}
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
expect 0 'guard:common-apply seal:verify config:saved activate commit tree-verify probe:1 '
grep -Fqx "native-common-boot=$ID" "$ROOT/output" || fail "boot receipt"
# Global OFF still commits the saved common profile release without a
# daemon and must prove the new IPFW scope empty after commit.
reset; BOOT_ENABLED=0
expect 0 'guard:common-apply seal:verify config:saved activate commit tree-verify probe:0 '
grep -Fqx "native-common-boot=$ID" "$ROOT/output" || fail "OFF boot receipt"
# A cold start must never print a success receipt if its installed release
# changes, the kernel/argv proof fails or a process dies AFTER IPFW commit.
for fault in tree probe child monitor; do
  reset
  case "$fault" in
    tree) POST_TREE_DRIFT=1 ;;
    probe) POST_PROBE_DRIFT=1 ;;
    child) POST_ENGINE_LOST=1 ;;
    monitor) POST_MONITOR_LOST=1 ;;
  esac
  case "$fault" in
    tree) expected='guard:common-apply seal:verify config:saved activate commit tree-verify ' ;;
    *) expected='guard:common-apply seal:verify config:saved activate commit tree-verify probe:1 ' ;;
  esac
  expect 70 "$expected"
  [ ! -s "$ROOT/output" ] || fail "$fault post-COMMIT drift claimed boot"
done
# Repeated Start/reconfigure on already verified shared Voice ON must not
# stop, launch or replace the engine; a mismatched release/kernel refuses.
reset; ENGINE=1; MONITOR=1
expect 0 'guard:common-apply seal:verify config:saved tree-verify probe:1 '
grep -Fqx "native-common-boot=$ID" "$ROOT/output" || fail "idempotent boot receipt"
reset; ENGINE=1; MONITOR=1; TREE_OK=0
expect 69 'guard:common-apply seal:verify config:saved tree-verify '
reset; ENGINE=1; MONITOR=1; PROBE_OK=0
expect 69 'guard:common-apply seal:verify config:saved tree-verify probe:1 '
reset; ENGINE=1; MONITOR=0
expect 69 'guard:common-apply seal:verify config:saved '
reset; ENGINE=1; MONITOR=1; BOOT_ENABLED=0
expect 69 'guard:common-apply seal:verify config:saved '
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
    # The real root CLI commits PREPARED → RESTORED before the wrapper
    # re-inspects the journal, including an inherited common owner.
    if [ "$RECOVER_OWNER" = "-" ]; then
        OWNER=restored
    else
        OWNER="$RECOVER_OWNER"
    fi
}
shared_apply_recover_activating_pristine_service() {
    echo pristine-recover >> "$LOG"
    [ "$PRISTINE_OK" = 0 ] || return 69
    OWNER="committed $PREVIOUS voice"
}
shared_apply_recover_activated_cold_service() {
    echo installed-recover >> "$LOG"
    [ "$COLD_OK" = 0 ] || return 69
    OWNER="committed $PREVIOUS voice"
}
shared_apply_recover_activating_parked_service() {
    echo parked-recover >> "$LOG"
    [ "$PARKED_OK" = 0 ] || return 69
    OWNER="committed $PREVIOUS voice"
}
shared_apply_boot_service() { echo "common:$1" >> "$LOG"; }
shared_apply_stop_service() {
    if [ "$#" -eq 2 ]; then
        echo "common-failure-stop:$1:$2" >> "$LOG"
    else
        echo "common-stop:$1" >> "$LOG"
    fi
    [ "$STOP_OK" = 0 ] || return 70
}
preflight_shared_apply_journal() { echo "shared-guard" >> "$LOG"; }
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
RECOVER=0 RECOVER_OWNER=- SAVED_OK=0 STOP_OK=0 PRISTINE_OK=0 COLD_OK=0 PARKED_OK=1
COLD_NATIVE_OK=0 COLD_NO_ADVANCE=0
PREVIOUS=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
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
OWNER="committed $ID voice"
check_route 0 runtime-failure "exited" 542
[ "$(cat "$LOG")" = "common-failure-stop:committed $ID voice:542" ] ||
    fail "native runtime failure fell through to legacy rule sweep"
OWNER="activated $ID voice"
check_route 69 runtime-failure "exited" 542
[ ! -s "$LOG" ] || fail "pending native owner was torn down by callback"
OWNER=restored
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = 'shared-guard legacy:start ' ] ||
    fail "restored owner did not use ordinary legacy lifecycle"
OWNER="prepared $ID voice"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = 'prepared-recovered shared-guard legacy:start ' ] ||
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
OWNER="activating $ID voice $PREVIOUS voice"
PRISTINE_OK=0
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = "pristine-recover common:committed $PREVIOUS voice " ] ||
    fail "pristine activating boot did not restore previous common owner"
PRISTINE_OK=1
OWNER="activating $ID voice $PREVIOUS voice"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = "pristine-recover installed-recover common:committed $PREVIOUS voice " ] ||
    fail "fully installed activating runtime did not use cold verified recovery"
COLD_OK=1
OWNER="activating $ID voice $PREVIOUS voice"
check_route 69 start
[ "$(tr '\n' ' ' < "$LOG")" = 'pristine-recover installed-recover parked-recover ' ] ||
    fail "unverified activating runtime fell through to legacy"
PARKED_OK=0
OWNER="activating $ID voice $PREVIOUS voice"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = "pristine-recover installed-recover parked-recover common:committed $PREVIOUS voice " ] ||
    fail "verified parked previous owner did not route into native common boot"
PARKED_OK=1
COLD_OK=0 PRISTINE_OK=0
OWNER="activated $ID voice $PREVIOUS voice"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = "installed-recover common:committed $PREVIOUS voice " ] ||
    fail "activated cold boot lost previous native owner"
OWNER="legacy-common-committing $ID voice"
check_route 69 start
[ ! -s "$LOG" ] || fail "retired PoC cold migration must not run"

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
[ "$(tr '\n' ' ' < "$LOG")" = 'shared-guard legacy:stop ' ] || fail "legacy stop lost"
check_route 0 restart
[ "$(tr '\n' ' ' < "$LOG")" = 'shared-guard legacy:restart ' ] || fail "legacy restart lost"
check_route 0 start
[ "$(tr '\n' ' ' < "$LOG")" = 'shared-guard legacy:start ' ] ||
    fail "no common journal changed ordinary legacy startup"
# The original FD9 wrapper delegates compatibility names only after the
# common journal preflight; owner/marker checks now live in their real adapter.
for compat_action in telegram-voice-enable telegram-voice-disable; do
    HAS_RECORD=1 OWNER_OK=1 OWNER="committed $ID voice"
    check_route 0 "$compat_action"
    [ "$(tr '\n' ' ' < "$LOG")" = "shared-guard legacy:$compat_action " ] ||
        fail "compatibility command skipped original FD9 preflight"
done

# Exercise the real new compatibility adapter with only the native PHP
# envelope emission stubbed. The PHP model envelope has its own pure test.
sed -n '/^telegram_voice_compat_apply_service()$/,/^}$/p' "$SOURCE" > "$ROOT/compat.sh"
python3 - "$ROOT/compat.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); text=p.read_text()
old='_compat_encoded=$(/usr/local/bin/php \\\n        "$SCRIPT_DIR/shared_apply_request.php" telegram-envelope "$1")'
assert text.count(old)==1, "native PHP envelope handoff missing"
p.write_text(text.replace(old, '_compat_encoded=$(mock_compat_envelope "$1")'))
PY
sh -n "$ROOT/compat.sh" || fail "native Telegram adapter syntax"
. "$ROOT/compat.sh"
ACTIVE_DIR="$ROOT/compat-active"
mkdir -p "$ACTIVE_DIR"
COMPAT_ENVELOPE_OK=1
shared_apply_require_tools() { :; }
telegram_voice_marker_is_enabled() { fail "retired marker was consulted"; }
firewall_table_exists() { fail "retired PoC table was consulted"; }
mock_compat_envelope() {
    echo "envelope:$1" >> "$LOG"
    [ "$COMPAT_ENVELOPE_OK" = 1 ] || return 69
    echo 'c2FmZQ'
}
shared_apply_run_service() {
    echo "native:$1:$2" >> "$LOG"
    echo "applied-id=$ID"
}
compat_run() {
    wanted="$1"; shift
    : > "$LOG"
    set +e
    telegram_voice_compat_apply_service "$@" > "$ROOT/compat-response"
    actual=$?
    set -e
    [ "$actual" = "$wanted" ] || fail "compat adapter returned $actual expected $wanted"
}
HAS_RECORD=1 OWNER_OK=1 OWNER="committed $ID voice"
compat_run 0 enable
[ "$(tr '\n' ' ' < "$LOG")" = 'shared-guard envelope:enable native:voice:c2FmZQ ' ] ||
    fail "Telegram enable missed native shared Voice Apply"
compat_run 0 disable
[ "$(tr '\n' ' ' < "$LOG")" = 'shared-guard envelope:disable native:voice:c2FmZQ ' ] ||
    fail "Telegram disable missed native shared Voice Apply"
for forbidden in "prepared $ID voice" "activated $ID strategies" pending; do
    OWNER="$forbidden"
    compat_run 69 enable
    ! grep -Fq native: "$LOG" || fail "unfinished native owner reached Apply"
done
OWNER="committed $ID voice" OWNER_OK=0
compat_run 69 enable
OWNER_OK=1
# Old marker and private Telegram table can no longer veto native Apply.
compat_run 0 disable
compat_run 0 enable
COMPAT_ENVELOPE_OK=0
compat_run 69 enable
! grep -Fq native: "$LOG" || fail "failed PHP envelope reached native mutation"
COMPAT_ENVELOPE_OK=1 HAS_RECORD=0
printf 'native\n' > "$ACTIVE_DIR/voice-plan.json"
compat_run 69 disable
rm -f "$ACTIVE_DIR/voice-plan.json"
ln -s "$ROOT/missing-native" "$ACTIVE_DIR/voice-plan.json"
compat_run 69 enable
rm -f "$ACTIVE_DIR/voice-plan.json"
compat_run 0 disable
[ "$(tr '\n' ' ' < "$LOG")" = 'shared-guard envelope:disable native:voice:c2FmZQ ' ] ||
    fail "native compatibility unexpectedly bypassed shared Apply"

# Old configctl status keys always reflect native inspection, not retired PoC.
sed -n '/^telegram_voice_compat_status_service()$/,/^}$/p' "$SOURCE" > "$ROOT/compat-status.sh"
sh -n "$ROOT/compat-status.sh" || fail "compatibility status syntax"
. "$ROOT/compat-status.sh"
telegram_voice_native_status_service() { echo verified-native; }
telegram_voice_status_service() { fail "retired PoC status was consulted"; }
HAS_RECORD=1 OWNER_OK=1 OWNER="committed $ID voice"
[ "$(telegram_voice_compat_status_service)" = verified-native ] ||
    fail "committed status read old hardcoded PoC"
OWNER="prepared $ID voice"
set +e
telegram_voice_compat_status_service > "$ROOT/compat-status-output"
rc=$?
set -e
[ "$rc" = 2 ] || fail "pending native status claimed ready"
HAS_RECORD=0
[ "$(telegram_voice_compat_status_service)" = verified-native ] ||
    fail "unowned compatibility status did not call native inspector"
printf 'native\n' > "$ACTIVE_DIR/voice-plan.json"
set +e
telegram_voice_compat_status_service > "$ROOT/compat-status-output"
rc=$?
set -e
[ "$rc" = 2 ] || fail "orphan native manifest fell back to PoC status"
rm -f "$ACTIVE_DIR/voice-plan.json"
echo 'PASS: Telegram compatibility delegates all operations and status to native common Apply'

# Recover the narrow phase where the previous committed release was never
# displaced. Use the production service recovery function and mock only
# its root-only terminal CLI; no kernel, Config or files are touched.
sed -n '/^shared_apply_recover_activating_pristine_service()$/,/^}$/p' "$SOURCE" > "$ROOT/pristine.sh"
python3 - "$ROOT/pristine.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='    [ -x /usr/local/bin/python3.13 ] || return 69\n    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \\\n        recover-activating "$_shared_pristine_id" "$_shared_pristine_old" || return 69'
assert old in s, "production root CLI boundary missing"
s=s.replace(old,'    echo terminal-restore >> "$LOG"; [ "$TERMINAL_OK" = 0 ] || return 69')
p.write_text(s)
PY
. "$ROOT/pristine.sh"
OLD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
CURRENT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
ACTIVE_DIR="$ROOT/live"
BACKUP_ROOT="$ROOT/backups"
mkdir -p "$ACTIVE_DIR" "$BACKUP_ROOT"
PRISTINE_STAGE="$ROOT/.live.stage.$CURRENT"
PRISTINE_PARKED="$ROOT/.live.old.$CURRENT"
PRISTINE_BACKUP="$BACKUP_ROOT/live-$CURRENT"
CHILD_PIDFILE="$ROOT/child"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/supervisor"
atomic_verify_tree() {
  echo compare >> "$LOG"
  if [ "$2" = "$PRISTINE_STAGE" ]; then [ "$STAGE_OK" = 0 ]
  else [ "$TREE_OK" = 0 ]; fi
}
atomic_remove_tree() {
  echo stage-remove >> "$LOG"
  [ "$REMOVE_OK" = 0 ] || return 1
  rm -rf "$1"
}
apply_runtime_attest_engine_inventory() { echo census >> "$LOG"; [ "$CENSUS_OK" = 0 ]; }
firewall_shared_runtime() { echo ipfw >> "$LOG"; [ "$IPFW_OK" = 0 ]; }
launcher_is_running() { echo engine >> "$LOG"; [ "$ENGINE" = 1 ]; }
supervisor_is_running() { echo supervisor >> "$LOG"; [ "$MONITOR" = 1 ]; }
reset_pristine() {
  : > "$LOG"
  TREE_OK=0 STAGE_OK=0 REMOVE_OK=0 CENSUS_OK=0 IPFW_OK=0 ENGINE=0 MONITOR=0
  TERMINAL_OK=0 GUARD=0 SEAL=0 CONFIG=0
}
pristine_check() {
  wanted="$1"; shift
  set +e
  shared_apply_recover_activating_pristine_service "$1" > "$ROOT/pristine-output"
  actual=$?
  set -e
  [ "$actual" -eq "$wanted" ] || fail "pristine status $actual expected $wanted"
}
reset_pristine
pristine_check 0 "activating $CURRENT voice $OLD voice"
grep -Fqx "recovered-pristine-id=$CURRENT" "$ROOT/pristine-output" || fail "pristine receipt missing"
grep -Fq terminal-restore "$LOG" || fail "pristine terminal phase omitted"
reset_pristine; TREE_OK=1
pristine_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fq terminal-restore "$LOG" || fail "altered installed runtime finalized"
reset_pristine; CENSUS_OK=1
pristine_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fq terminal-restore "$LOG" || fail "orphan engine finalized"
reset_pristine; IPFW_OK=1
pristine_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fq terminal-restore "$LOG" || fail "foreign kernel finalized"
reset_pristine; CONFIG=1
pristine_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fq terminal-restore "$LOG" || fail "changed saved Config finalized"
reset_pristine
mkdir -p "$PRISTINE_STAGE"
printf 'sealed candidate\n' > "$PRISTINE_STAGE/release-proof"
pristine_check 0 "activating $CURRENT voice $OLD voice"
[ ! -e "$PRISTINE_STAGE" ] || fail "sealed stage not removed before terminal recovery"
grep -Fq stage-remove "$LOG" && grep -Fq terminal-restore "$LOG" ||
    fail "pristine stage recovery skipped removal or journal"
reset_pristine
mkdir -p "$PRISTINE_STAGE"
STAGE_OK=1
pristine_check 69 "activating $CURRENT voice $OLD voice"
[ -e "$PRISTINE_STAGE" ] && ! grep -Fq stage-remove "$LOG" ||
    fail "partial/foreign stage removed or authorized"
rm -rf "$PRISTINE_STAGE"
reset_pristine; mkdir -p "$PRISTINE_PARKED"
pristine_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fq terminal-restore "$LOG" || fail "parked old owner ignored"
rmdir "$PRISTINE_PARKED"
reset_pristine; mkdir -p "$PRISTINE_BACKUP"
pristine_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fq terminal-restore "$LOG" || fail "backup collision ignored"
rmdir "$PRISTINE_BACKUP"
reset_pristine; mkdir -p "$PRISTINE_STAGE"; REMOVE_OK=1
pristine_check 70 "activating $CURRENT voice $OLD voice"
[ -e "$PRISTINE_STAGE" ] && ! grep -Fq terminal-restore "$LOG" ||
    fail "failed stage removal finalized journal"
rm -rf "$PRISTINE_STAGE"
reset_pristine
pristine_check 69 "activating $CURRENT voice"
pristine_check 69 "activated $CURRENT voice $OLD voice"
echo 'PASS: pristine interrupted activating restores exact old owner and cleans sealed stage only'

# Cold activated recovery tests the production FD9 service with mock kernel.
sed -n '/^shared_apply_recover_activated_cold_service()$/,/^}$/p' "$SOURCE" > "$ROOT/activated-cold.sh"
python3 - "$ROOT/activated-cold.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
old='    [ -x /usr/local/bin/python3.13 ] || return 70\n    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \\\n        "finish-$_shared_cold_phase" "$_shared_cold_id" "$_shared_cold_old" || return 70'
assert old in s, "production root completion CLI boundary missing"
s=s.replace(old,'    echo "finish-$_shared_cold_phase" >> "$LOG"; [ "$TERMINAL_OK" = 0 ] || return 70')
p.write_text(s)
PY
. "$ROOT/activated-cold.sh"
OLD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
CURRENT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
BACKUP_ROOT="$ROOT/backups"
mkdir -p "$BACKUP_ROOT" "$ROOT/work-old/release" "$ROOT/work-new/release"
CHILD_PIDFILE="$ROOT/child"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/supervisor"
shared_apply_workspace() {
  case "$1" in "$OLD") echo "$ROOT/work-old" ;; "$CURRENT") echo "$ROOT/work-new" ;; *) return 1 ;; esac
}
atomic_verify_tree() {
  echo "compare:$1" >> "$LOG"
  case "$1" in "$ROOT/work-old/release") [ "$INSTALLED" = old ] ;;
    "$ROOT/work-new/release") [ "$INSTALLED" = new ] ;; *) return 1 ;; esac
}
atomic_install_tree() {
  echo install-previous >> "$LOG"
  [ "$INSTALL_OK" = 0 ] || return 1
  [ "$1" = "$ROOT/work-old/release" ] &&
  [ "$2" = "$ACTIVE_DIR" ] && [ "$3" = "$BACKUP_ROOT" ] || return 1
  INSTALLED=old
}
reset_cold() {
  : > "$LOG"
  INSTALLED=new INSTALL_OK=0 TERMINAL_OK=0
  GUARD=0 SEAL=0 CONFIG=0 ENGINE=0 MONITOR=0 CENSUS_OK=0 IPFW_OK=0
}
cold_check() {
  expected="$1"; shift
  set +e
  shared_apply_recover_activated_cold_service "$1" > "$ROOT/cold-output"
  actual=$?
  set -e
  [ "$actual" = "$expected" ] || fail "activated status $actual expected $expected"
}
reset_cold
cold_check 0 "activated $CURRENT voice $OLD voice"
[ "$INSTALLED" = old ] || fail "previous sealed release not restored"
grep -Fqx "recovered-activated-id=$CURRENT" "$ROOT/cold-output" || fail "missing restored receipt"
grep -Fqx finish-activated "$LOG" || fail "journal not completed"
reset_cold; INSTALLED=old
cold_check 0 "activated $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" || fail "duplicate installation in idempotent retry"
reset_cold; INSTALLED=foreign
cold_check 69 "activated $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" || fail "foreign release overwritten"
reset_cold; ENGINE=1
cold_check 69 "activated $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" || fail "live process overwritten"
reset_cold; CENSUS_OK=1
cold_check 69 "activated $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" || fail "orphan engine overwritten"
reset_cold; IPFW_OK=1
cold_check 69 "activated $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" || fail "foreign IPFW overwritten"
reset_cold; CONFIG=1
cold_check 69 "activated $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" || fail "saved Config drift overwritten"
reset_cold; INSTALL_OK=1
cold_check 70 "activated $CURRENT voice $OLD voice"
! grep -Fqx finish-activated "$LOG" || fail "failed atomic install was committed"
reset_cold; TERMINAL_OK=1
cold_check 70 "activated $CURRENT voice $OLD voice"
reset_cold
cold_check 69 "activated $CURRENT voice"
cold_check 69 "activating $CURRENT voice"
reset_cold
cold_check 0 "activating $CURRENT voice $OLD voice"
[ "$INSTALLED" = old ] || fail "installed-but-uncommitted activating release was not restored"
grep -Fqx "recovered-activating-id=$CURRENT" "$ROOT/cold-output" ||
    fail "activating restored receipt missing"
grep -Fqx finish-activating "$LOG" ||
    fail "activating restore did not use phase-specific durable CLI"
reset_cold; INSTALLED=old
cold_check 0 "activating $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" ||
    fail "recovered activating case reinstalled an existing previous tree"
reset_cold; INSTALLED=foreign
cold_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx finish-activating "$LOG" ||
    fail "partial activating tree was falsely marked restored"
reset_cold; IPFW_OK=1
cold_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" ||
    fail "nonempty IPFW caused destructive activating rollback"
reset_cold; CONFIG=1
cold_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx install-previous "$LOG" ||
    fail "saved Config drift caused destructive activating rollback"
reset_cold; INSTALL_OK=1
cold_check 70 "activating $CURRENT voice $OLD voice"
! grep -Fqx finish-activating "$LOG" ||
    fail "failed activating atomic rename was declared restored"
echo 'PASS: shared cold activated recovery, idempotent previous owner and fail-closed checks'


# Exercise the exact new root FD9 service helper, with the root-only journal
# write mocked. Verify both known atomic gaps and refusal of foreign files.
sed -n '/^shared_apply_recover_activating_parked_service()$/,/^}$/p' "$SOURCE" > "$ROOT/parked.sh"
python3 - "$ROOT/parked.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='    [ -x /usr/local/bin/python3.13 ] || return 70\n    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \\\n        finish-activating "$_parked_id" "$_parked_old" || return 70'
assert old in s, "parked recovery CLI phase gate missing"
s=s.replace(old,'    echo finish-activating-parked >> "$LOG"; [ "$TERMINAL_OK" = 0 ] || return 70')
p.write_text(s)
PY
. "$ROOT/parked.sh"
ACTIVE_DIR="$ROOT/live-parked"
BACKUP_ROOT="$ROOT/parked-backups"
stage="$ROOT/.live-parked.stage.$CURRENT"
hold="$ROOT/.live-parked.old.$CURRENT"
previous="$BACKUP_ROOT/live-parked-$CURRENT"
mkdir -p "$BACKUP_ROOT" "$stage" "$hold"
atomic_verify_tree() {
  echo "compare:$2" >> "$LOG"
  case "$2" in
    "$stage") [ "$STAGE_OK" = 0 ] ;;
    "$hold"|"$previous") [ "$PREVIOUS_OK" = 0 ] ;;
    "$ACTIVE_DIR") [ "$INSTALLED" = old ] ;;
    *) return 69 ;;
  esac
}
atomic_install_tree() {
  echo restore-missing-active >> "$LOG"
  [ "$INSTALL_OK" = 0 ] &&
  [ "$1" = "$ROOT/work-old/release" ] &&
  [ "$2" = "$ACTIVE_DIR" ] &&
  [ "$3" = "$BACKUP_ROOT" ] || return 70
  INSTALLED=old
}
reset_parked() {
  : > "$LOG"
  INSTALLED=missing STAGE_OK=0 PREVIOUS_OK=0
  GUARD=0 SEAL=0 CONFIG=0 ENGINE=0 MONITOR=0
  CENSUS_OK=0 IPFW_OK=0 INSTALL_OK=0 TERMINAL_OK=0
  rm -rf "$ACTIVE_DIR" "$stage" "$hold" "$previous"
  mkdir -p "$stage" "$hold"
}
parked_check() {
  wanted="$1"; shift
  set +e
  shared_apply_recover_activating_parked_service "$1" > "$ROOT/parked-output"
  actual=$?
  set -e
  [ "$actual" = "$wanted" ] || fail "parked recovery status $actual expected $wanted"
}
reset_parked
parked_check 0 "activating $CURRENT voice $OLD voice"
grep -Fqx "recovered-parked-id=$CURRENT" "$ROOT/parked-output" || fail "parked recovery receipt missing"
grep -Fqx finish-activating-parked "$LOG" || fail "parked recovery not durable"
[ -d "$stage" ] && [ -d "$hold" ] || fail "parked evidence was consumed"
reset_parked
mv "$hold" "$previous"
parked_check 0 "activating $CURRENT voice $OLD voice"
[ -d "$stage" ] && [ -d "$previous" ] || fail "backup evidence was consumed"
reset_parked; mkdir -p "$previous"
parked_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx restore-missing-active "$LOG" || fail "ambiguous two owners restored"
reset_parked; STAGE_OK=1
parked_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx restore-missing-active "$LOG" || fail "foreign staged release restored"
reset_parked; PREVIOUS_OK=1
parked_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx restore-missing-active "$LOG" || fail "foreign old parked release restored"
reset_parked; CONFIG=1
parked_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx restore-missing-active "$LOG" || fail "Config drift restored"
reset_parked; ENGINE=1
parked_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx restore-missing-active "$LOG" || fail "live process restored"
reset_parked; IPFW_OK=1
parked_check 69 "activating $CURRENT voice $OLD voice"
! grep -Fqx restore-missing-active "$LOG" || fail "kernel ownership conflict restored"
reset_parked; INSTALL_OK=1
parked_check 70 "activating $CURRENT voice $OLD voice"
! grep -Fqx finish-activating-parked "$LOG" || fail "failed install marked restored"
reset_parked; TERMINAL_OK=1
parked_check 70 "activating $CURRENT voice $OLD voice"
reset_parked
parked_check 69 "activating $CURRENT voice"
parked_check 69 "activated $CURRENT voice $OLD voice"
echo 'PASS: ID-scoped park/backup gaps recover only exact sealed previous owner'

# Generic status must not use the old PID/any-divert witness for a common owner.
sed -n '/^shared_apply_status_service()$/,/^}$/p' "$SOURCE" > "$ROOT/status.sh"
sh -n "$ROOT/status.sh" || fail "status syntax"
. "$ROOT/status.sh"
grep -Fq 'voice_live_inspect.py' "$SOURCE" || fail "native status inspector absent"
grep -Fq 'json.load(sys.stdin)' "$SOURCE" || fail "status JSON unvalidated"
STATUS_LOG="$ROOT/status-legacy.log"
RULE_BASE=19000
RULE_MAX=19010
ACTIVE_DIR="$ROOT/status-active"
mkdir -p "$ACTIVE_DIR"
shared_apply_has_record_service() { [ "$STATUS_RECORD" = 1 ]; }
shared_apply_inspect_service() { [ "$STATUS_VALID" = 1 ] || return 69; echo "$STATUS_OWNER"; }
shared_apply_status_observe_service() {
  [ "$STATUS_PROBE_OK" = 1 ] || return 69
  echo "$STATUS_PROBE"
}
orchestrator_native_status() {
  echo legacy >> "$STATUS_LOG"
  echo legacy-status
  return "$STATUS_LEGACY_RC"
}
status_case() {
  wanted="$1"
  : > "$STATUS_LOG"
  set +e
  shared_apply_status_service > "$ROOT/status-output"
  got=$?
  set -e
  [ "$got" = "$wanted" ] || fail "service status $got instead of $wanted"
}
STATUS_RECORD=1 STATUS_VALID=1 STATUS_PROBE_OK=1 STATUS_LEGACY_RC=0
STATUS_OWNER="committed $ID voice" STATUS_PROBE=ready
status_case 0
grep -Fqx 'zapret is running' "$ROOT/status-output" || fail "native ready receipt missing"
[ ! -s "$STATUS_LOG" ] || fail "native ready delegated to legacy"
STATUS_PROBE=stopped
status_case 1
grep -Fqx 'zapret is not running' "$ROOT/status-output" || fail "native stopped receipt missing"
STATUS_PROBE_OK=0
status_case 2
[ ! -s "$STATUS_LOG" ] || fail "failed native witness delegated to legacy"
STATUS_PROBE_OK=1 STATUS_PROBE=ready STATUS_OWNER="committed $ID strategies"
status_case 0
[ ! -s "$STATUS_LOG" ] || fail "Strategies native owner delegated to legacy"
STATUS_OWNER="prepared $ID voice"
status_case 2
[ ! -s "$STATUS_LOG" ] || fail "pending native owner delegated to legacy"
STATUS_VALID=0
status_case 2
[ ! -s "$STATUS_LOG" ] || fail "invalid native owner delegated to legacy"
STATUS_VALID=1 STATUS_OWNER=restored
status_case 0
grep -Fqx legacy "$STATUS_LOG" || fail "restored legacy status missing"
STATUS_RECORD=0 STATUS_LEGACY_RC=1
status_case 1
grep -Fqx legacy "$STATUS_LOG" || fail "unowned legacy status missing"
printf 'native\n' > "$ACTIVE_DIR/voice-plan.json"
status_case 2
[ ! -s "$STATUS_LOG" ] || fail "orphan common release delegated to legacy"
rm -f "$ACTIVE_DIR/voice-plan.json"
ln -s "$ROOT/absent" "$ACTIVE_DIR/voice-plan.json"
status_case 2
[ ! -s "$STATUS_LOG" ] || fail "orphan native symlink delegated to legacy"
rm -f "$ACTIVE_DIR/voice-plan.json"

# The old generic status test called shared_apply_status_service directly,
# bypassing the actual top-level shell dispatcher. Extract and execute the
# exact final entrypoint with the original service_with_lifecycle_lock so the
# recovered legacy journal can only be read with the inherited FD9.
awk '
  /^case "\$\{1:-\}" in$/ { begin = NR }
  { data[NR] = $0 }
  END {
    if (begin == 0) exit 1
    for (i = begin; i <= NR; i++) print data[i]
  }
' "$SOURCE" > "$ROOT/status-entry.sh" || fail "entrypoint extraction"
sh -n "$ROOT/status-entry.sh" || fail "entrypoint syntax"
(
  set -- status
  STATUS_RECORD=1 STATUS_VALID=1 STATUS_OWNER=restored STATUS_LEGACY_RC=0
  shared_apply_inspect_service() {
    # In real production this read-only CLI rejects a missing root FD9.
    # The test only verifies routing and availability of fd9, not privileged
    # FreeBSD lock ownership.
    : >&9 || return 69
    printf '%s\n' restored
  }
  orchestrator_native_status() { echo "zapret is running"; }
  . "$ROOT/status-entry.sh"
) > "$ROOT/status-entry-output" || fail "restored owner status not routed via FD9"
grep -Fqx 'zapret is running' "$ROOT/status-entry-output" ||
    fail "real status entrypoint classified complete restored legacy as incomplete"
(
  set -- status
  LOCKF_BIN="$ROOT/reject-lockf"
  printf '#!/bin/sh\nexit 1\n' > "$LOCKF_BIN"
  chmod 700 "$LOCKF_BIN"
  orchestrator_native_status() { fail "status bypassed refused lifecycle lock"; }
  . "$ROOT/status-entry.sh"
) > "$ROOT/status-entry-rejected" 2>&1 &&
    fail "status ignored unavailable lifecycle lock"

echo 'PASS: generic status separates verified native and genuine legacy'

echo 'PASS: committed native common owner routes boot through sealed release and fresh saved Config'
