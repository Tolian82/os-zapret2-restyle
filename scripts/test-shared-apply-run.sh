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
    _shared_build_receipt=
    [ "$BUILD_OK" = 1 ] || return 69
    if [ "${BUILD_REFUSED:-0}" = 1 ]; then
        _shared_build_receipt=preflight-rejected=candidate
        echo "$_shared_build_receipt"
        return 0
    fi
    # These are the original in-memory generator scalars. A subshell
    # build would lose them, even though its prepared-id is correct.
    TRAFFIC_ARGS="--filter-tcp=443
--lua-desync=fake"
    HOSTLIST_MODE=list
    _shared_build_receipt="prepared-id=$ID"
    _shared_prepare_receipt="prepared-id=$ID"
    echo 'native template and runtime generated'
    echo "$_shared_build_receipt"
}
shared_apply_execute_service() {
    echo "execute:$1:$2" >> "$LOG"
    [ "${TRAFFIC_ARGS:-}" = "--filter-tcp=443
--lua-desync=fake" ] && [ "${HOSTLIST_MODE:-}" = list ] &&
    [ "${_shared_prepare_receipt:-}" = "prepared-id=$1" ] ||
        fail "execute lost original in-memory producer input"
    [ "$EXECUTE_OK" = 1 ] || return 70
    echo "applied-id=$1"
}
check() {
    expected="$1"; shift
    : > "$LOG"
    unset TRAFFIC_ARGS HOSTLIST_MODE _shared_prepare_receipt
    set +e
    shared_apply_run_service "$@" > "$TMP/response"
    code=$?
    set -e
    [ "$code" = "$expected" ] || fail "status $code expected $expected"
}
shared_apply_has_record_service() { [ "${FOUND_PENDING:-0}" = 1 ]; }
shared_apply_pending_found_service() { printf '%s\n' "$ID"; }
shared_apply_recover_found_service() { echo "recover:$1" >> "$LOG"; }
GUARD_OK=1; BUILD_OK=1; EXECUTE_OK=1
check 0 voice c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = "guard:common-apply build:c2FmZQ execute:$ID:voice " ] ||
    fail "build and execute not dispatched under one owner"
grep -Fqx "applied-id=$ID" "$TMP/response" || fail "Apply receipt missing"
[ "$(cat "$TMP/response")" = "applied-id=$ID" ] ||
    fail "internal producer output leaked into Apply receipt"
check 0 strategies c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = "guard:common-apply build:c2FmZQ execute:$ID:strategies " ] ||
    fail "Strategies used foreign page"
GUARD_OK=0
check 69 voice c2FmZQ
[ "$(cat "$LOG")" = "guard:common-apply" ] || fail "busy lock mutated"
GUARD_OK=1; BUILD_OK=1; BUILD_REFUSED=1
check 0 voice c2FmZQ
[ "$(cat "$TMP/response")" = 'preflight-rejected=candidate' ] ||
    fail "a native rejected candidate was incorrectly reported as an unknown Apply"
[ "$(tr '\n' ' ' < "$LOG")" = 'guard:common-apply build:c2FmZQ ' ] ||
    fail "preflight rejection started runtime mutation"
BUILD_REFUSED=0; BUILD_OK=0
check 69 voice c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = 'guard:common-apply build:c2FmZQ ' ] ||
    fail "failed build entered native Config save"
BUILD_OK=1; EXECUTE_OK=0
check 70 voice c2FmZQ
[ "$(tr '\n' ' ' < "$LOG")" = "guard:common-apply build:c2FmZQ execute:$ID:voice " ] ||
    fail "failed runtime concealed"
EXECUTE_OK=1
FOUND_PENDING=1
check 0 strategies c2FmZQ
[ "$(cat "$LOG")" = "recover:$ID" ] || fail "pending found Apply submitted another request"
grep -Fqx "apply-recovered=$ID" "$TMP/response" || fail "recovery receipt missing"
FOUND_PENDING=0
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
# Public Telegram status and common Voice inspection must use the SAME
# original FD9 dispatch as lifecycle. Verify the dispatch arm and its
# lock call, not an obsolete assumption that no newer action may appear
# between reconfigure and telegram-voice-status.
awk '
    index($0, "start|stop|restart|reconfigure|") &&
    index($0, "|telegram-voice-status|native-voice-lifecycle-inspect|") {
        if (getline > 0 &&
            index($0, "service_with_lifecycle_lock") &&
            index($0, "LIFECYCLE_LOCK_TIMEOUT")) matched = 1
    }
    END { exit !matched }
' "$SOURCE" || fail "compatibility status must own original FD9"
# Verify the actual release finalizer, not a mock of its implementation.
sed -n '/^shared_apply_finalize_release_modes()$/,/^}$/p' "$SOURCE" > "$TMP/release-modes.sh"
[ -s "$TMP/release-modes.sh" ] || fail "common runtime mode finalizer missing"
sh -n "$TMP/release-modes.sh" || fail "common runtime mode finalizer syntax"
. "$TMP/release-modes.sh"
common_set_directory_mode() { [ -d "$1" ] && chmod "$2" "$1"; }
validator_validate_runtime_modes() {
    [ "$(find "$1" -prune -perm 755 -print)" = "$1" ] &&
    [ -d "$1/managed" ] &&
    [ "$(find "$1/managed" -prune -perm 755 -print)" = "$1/managed" ]
}
mkdir -p "$TMP/private/release/managed"
chmod 0700 "$TMP/private" "$TMP/private/release"
chmod 0755 "$TMP/private/release/managed"
shared_apply_finalize_release_modes "$TMP/private/release" ||
    fail "native candidate runtime still has private 0700 mode"
[ "$(find "$TMP/private" -prune -perm 700 -print)" = "$TMP/private" ] ||
    fail "candidate workspace must remain private 0700"
[ "$(find "$TMP/private/release" -prune -perm 755 -print)" = "$TMP/private/release" ] ||
    fail "release mode must be 0755"
ln -s release "$TMP/private/symlink"
if shared_apply_finalize_release_modes "$TMP/private/symlink"; then
    fail "symlink candidate was accepted"
fi
chmod 0700 "$TMP/private/release/managed"
if shared_apply_finalize_release_modes "$TMP/private/release"; then
    fail "managed directory validator was bypassed"
fi
sed -n '/^shared_apply_prepare_service()$/,/^}$/p' "$SOURCE" > "$TMP/prepare.sh"
awk '/orchestrator_build_release / { build=NR }
     /_shared_auto_digest=\$\(/ { digest=NR }
     /shared_apply_original_source_gate "\$1" "\$_shared_auto_digest" \|\|/ { auto_gate=NR }
     /shared_apply_original_source_gate "\$1" \|\|/ { nonauto_gate=NR }
     /shared_apply_finalize_release_modes "\$_shared_work\/release"/ { modes=NR }
     /shared_apply_bundle_service seal / { seal=NR }
     /shared_apply_original_source_gate "\$1" "\$_shared_auto_digest" --sealed/ { final_auto=NR }
     /shared_apply_original_source_gate "\$1" --sealed/ { final_nonautos=NR }
     END { exit !(build > 0 && digest > build && auto_gate > digest &&
                  nonauto_gate > auto_gate && modes > nonauto_gate &&
                  seal > modes && final_auto > seal &&
                  final_nonautos > final_auto) }' "$TMP/prepare.sh" ||
    fail "original source gate preseal and postseal must bracket original promotion/seal"

# Stream the original shell scalars through the installed gate, without
# generating a second file-backed Config or passing user data in argv.
sed -n '/^shared_apply_original_source_gate()$/,/^}$/p' "$SOURCE" > "$TMP/source-gate.sh"
sh -n "$TMP/source-gate.sh" || fail "source gate shell syntax"
. "$TMP/source-gate.sh"
cat > "$TMP/source-gate-python-stub" <<EOF
#!/bin/sh
cat > "$TMP/source-gate.stdin"
EOF
chmod 0755 "$TMP/source-gate-python-stub"
BACKEND_DIR="$ROOT/src/opnsense/scripts/OPNsense/Zapret/backend"
PYTHON_RUNTIME="$TMP/source-gate-python-stub"
TRAFFIC_ARGS='--filter-tcp=443
--lua-desync=fake'
YOUTUBE_DOMAINS='youtube.com'
USER_DOMAINS='example.org'
TELEGRAM_IPS='91.108.13.10'
DISCORD_IPS=''
X_IPS=''
SIP_IPS=''
CUSTOM_IPS=''
EXCLUDE_DOMAINS='ads.example.org'
EXCLUDE_IPSET='203.0.113.0/24'
HOSTLIST_MODE='list'
DIVERT_PORT='989'
WAN_IF='opt0'
shared_apply_original_source_gate "$ID" || fail "same-operation source gate pipe failed"
shared_apply_original_source_gate "$ID" "$(printf '%064d' 0)" ||
    fail "same-operation Auto source digest forwarding failed"
shared_apply_original_source_gate "$ID" --sealed ||
    fail "same-operation sealed nonauto source forwarding failed"
shared_apply_original_source_gate "$ID" "$(printf '%064d' 0)" --sealed ||
    fail "same-operation sealed Auto source forwarding failed"
python3 - "$TMP/source-gate.stdin" <<'PY'
import pathlib, sys
data = pathlib.Path(sys.argv[1]).read_bytes()
assert data.endswith(b'\x00')
fields = data[:-1].split(b'\x00')
assert len(fields) == 14, len(fields)
assert fields[0] == b'S10C2B1_ORIGINAL_INPUT_V1'
assert fields[1] == b'--filter-tcp=443\n--lua-desync=fake'
assert fields[2] == b'youtube.com' and fields[3] == b'example.org'
assert fields[10] == b'203.0.113.0/24'
assert fields[11:] == [b'list', b'989', b'opt0']
PY
echo 'PASS: original-FD9 one-request shared Voice/Strategies transaction, source gate and configd action'
