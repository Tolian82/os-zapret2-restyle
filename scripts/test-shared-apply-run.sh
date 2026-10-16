#!/bin/sh
# Invoke the exact common native stage/build/execute owner with mock internals.
set -eu
TMP=$(mktemp -d /tmp/zapret-common-run.XXXXXXXX) || exit 1
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
sed -n '/^shared_apply_run_service()$/,/^}$/p' "$SOURCE" > "$TMP/runner.sh"
sh -n "$TMP/runner.sh" || fail "native runner syntax"
. "$TMP/runner.sh"
LOG="$TMP/log"
ID=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
preflight_shared_apply_journal() {
    echo "guard:$1" >> "$LOG"
    [ "$GUARD_OK" = 1 ]
}
shared_apply_build_service() {
    echo "build:$1" >> "$LOG"
    [ "$BUILD_OK" = 1 ] || return 69
    echo 'native template and runtime generated'
    echo "prepared-id=$ID"
}
shared_apply_execute_service() {
    echo "execute:$1:$2" >> "$LOG"
    [ "$EXECUTE_OK" = 1 ] || return 70
    echo "applied-id=$1"
}
check() {
    expected="$1"; shift
    : > "$LOG"
    set +e
    shared_apply_run_service "$@" > "$TMP/response"
    code=$?
    set -e
    [ "$code" = "$expected" ] || fail "status $code expected $expected"
}
GUARD_OK=1; BUILD_OK=1; EXECUTE_OK=1
check 0 voice c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = "guard:common-apply build:c2FmZQ execute:$ID:voice " ] ||
    fail "build and execute not dispatched under one owner"
grep -Fqx "applied-id=$ID" "$TMP/response" || fail "Apply receipt missing"
check 0 strategies c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = "guard:common-apply build:c2FmZQ execute:$ID:strategies " ] ||
    fail "Strategies used foreign page"
GUARD_OK=0
check 69 voice c2FmZQ
[ "$(cat "$LOG")" = "guard:common-apply" ] || fail "busy lock mutated"
GUARD_OK=1; BUILD_OK=0
check 69 voice c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = 'guard:common-apply build:c2FmZQ ' ] ||
    fail "failed build entered native Config save"
BUILD_OK=1; EXECUTE_OK=0
check 70 voice c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = "guard:common-apply build:c2FmZQ execute:$ID:voice " ] ||
    fail "failed runtime concealed"
EXECUTE_OK=1
check 64 other c2FmZQ
[ ! -s "$LOG" ] || fail "unknown page started mutation"
check 64 voice ''
[ ! -s "$LOG" ] || fail "blank request started mutation"
grep -Fq 'shared_apply_run_service' "$SOURCE" || fail "production native runner missing"
grep -Fq 'shared-apply-run)' "$SOURCE" || fail "native dispatch missing"
grep -Fq 'shared-apply-run)' "$SOURCE" || fail "FD9 entry missing"
ACTIONS="$ROOT/src/opnsense/service/conf/actions.d/actions_zapret.conf"
grep -A 5 '^\[shared_apply\]$' "$ACTIONS" | grep -Fq 'parameters:%s %s' ||
    fail "single native configd Apply action missing"
# Compatibility configctl names must reuse the canonical shared owner and
# root PHP model envelope, not the old request-marker toggle/reconfigure.
grep -Fq 'telegram_voice_compat_apply_service()' "$SOURCE" ||
    fail "Telegram compatibility does not use shared native Apply"
grep -Fq 'shared_apply_run_service voice "$_compat_encoded"' "$SOURCE" ||
    fail "Telegram compatibility uses a second runtime writer"
grep -Fq 'shared_apply_request.php" telegram-envelope' "$SOURCE" ||
    fail "Telegram adapter ignores the saved native Config baseline"
grep -Fq 'telegram_voice_native_status_service()' "$SOURCE" ||
    fail "Telegram status still reports only hardcoded PoC profile"
grep -Fq 'shared_apply_request.php" telegram-saved' "$SOURCE" ||
    fail "Telegram status uses old marker as saved preference"
# Public Telegram status is in the same original FD9 dispatch as lifecycle.
grep -Fq 'reconfigure|telegram-voice-status|native-voice-lifecycle-inspect' "$SOURCE" ||
    fail "compatibility status must own original FD9"
echo 'PASS: original-FD9 one-request shared Voice/Strategies transaction and configd action'
