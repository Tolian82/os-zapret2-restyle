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
echo 'PASS: committed native common owner routes boot through sealed release and fresh saved Config'
