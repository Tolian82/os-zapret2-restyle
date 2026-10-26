#!/bin/sh
# Exercise the ACTUAL installed native Remove trial shell body with bounded
# fake service/kernel primitives. No copy of the compiler, parser or runtime
# algorithm and no real OPNsense files/IPFW are touched.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/native-remove-trial.XXXXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
OLD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
NEW=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
HASH=$(printf '%064d' 0 | tr 0 c)
export OLD HASH
cat > "$TMP/fakepython" <<'SH'
#!/bin/sh
[ "$2" = remove-trial-context ] || exit 69
[ "${BAD_CONTEXT:-0}" = 0 ] || exit 69
printf 'remove-trial-owner %s voice %s\n' "$OLD" "$HASH"
SH
chmod 700 "$TMP/fakepython"
sed -n '/^extra_resources_native_trial_abort_service()$/,/^}$/p' "$SOURCE" > "$TMP/native.sh"
sed -n '/^extra_resources_native_trial_service()$/,/^}$/p' "$SOURCE" >> "$TMP/native.sh"
sed "s@/usr/local/bin/python3.13@$TMP/fakepython@g" "$TMP/native.sh" > "$TMP/native-test.sh"
sh -n "$TMP/native-test.sh" || fail "actual native trial body syntax"
. "$TMP/native-test.sh"
EXTRA_RESOURCES_SETUP_LOCK_OWNER=1
EXTRA_RESOURCES_NATIVE_REMOVE_TRIAL=1
BACKEND_DIR="$TMP"
ACTIVE_DIR="$TMP/active"
CHILD_PIDFILE="$TMP/child"
SUPERVISOR_MONITOR_PIDFILE="$TMP/monitor"
LOG="$TMP/log"
mkdir -p "$TMP/old/release" "$TMP/new/release" "$ACTIVE_DIR"
shared_apply_workspace() {
    case "$1" in "$OLD") echo "$TMP/old" ;; "$NEW") echo "$TMP/new" ;; *) return 69 ;; esac
}
preflight_shared_apply_journal() { [ "$1" = common-apply ]; }
shared_apply_require_tools() { return 0; }
shared_apply_bundle_service() { echo "bundle:$1:$2" >> "$LOG"; return 0; }
shared_apply_native_config() {
    [ "$1" != save ] || fail "native Remove must NEVER save Config"
    case "$1" in
        preflight) echo candidate-readback >> "$LOG" ;;
        saved) echo "saved:$2" >> "$LOG" ;;
        *) return 69 ;;
    esac
    echo '{}'
}
shared_apply_json_field() {
    case "$1" in
        *'.enabled'*) echo 1 ;;
        *'.result'*) echo committed ;;
        *'.snapshot'*) echo "$HASH" ;;
        *'.base'*) if [ "$DRIFT" = 1 ]; then printf '%064d\n' 0 | tr 0 d; else echo "$HASH"; fi ;;
        *'.candidate'*) echo "$HASH" ;;
        *'.changes'*) echo 0 ;;
        *'.fields'*) echo 0 ;;
        *) return 69 ;;
    esac
}
extra_resources_native_build_saved_service() {
    echo gui-common-saved-builder >> "$LOG"
    printf 'prepared-id=%s\n' "$NEW"
}
atomic_verify_tree() { echo "verify-tree:$1" >> "$LOG"; return 0; }
launcher_is_running() { [ "$ENGINE" = 1 ]; }
supervisor_is_running() { [ "$ENGINE" = 1 ]; }
apply_runtime_attest_engine_inventory() { [ "$_apply_engine" = 0 ]; }
firewall_shared_runtime() {
    echo "ipfw:$1" >> "$LOG"
    [ "$1" = verify ] && [ "$3" = - ]
}
apply_runtime_probe() { echo runtime-probe >> "$LOG"; return 0; }
shared_apply_record_service() {
    echo "record:$1" >> "$LOG"
    [ "$1" != "$BAD_RECORD" ]
}
apply_runtime_activate() {
    echo runtime-activate >> "$LOG"
    APPLY_PHASE=installed
    if [ "$ACTIVATE_FAIL" = 1 ]; then return 70; fi
    ENGINE=1
    APPLY_PHASE=activated
}
apply_runtime_restore() {
    echo runtime-restore >> "$LOG"
    ENGINE=0
    APPLY_PHASE=idle
}
apply_runtime_attest_activated() {
    echo runtime-attest >> "$LOG"
    [ "$ATTEST_FAIL" = 0 ]
}
apply_runtime_commit() {
    echo runtime-commit >> "$LOG"
    APPLY_PHASE=idle
    [ "$COMMIT_FAIL" = 0 ]
}
shared_apply_status_observe_service() {
    [ "$STATUS_FAIL" = 0 ] || return 69
    echo ready
}
common_error() { echo "$*" >> "$LOG"; }
reset() {
    : > "$LOG"
    DRIFT=0; ENGINE=0; BAD_RECORD=none; ACTIVATE_FAIL=0
    ATTEST_FAIL=0; COMMIT_FAIL=0; STATUS_FAIL=0
    BAD_CONTEXT=0; APPLY_PHASE=idle
    export BAD_CONTEXT
}
check() {
    expected="$1"; shift
    set +e
    extra_resources_native_trial_service "$@" > "$TMP/output"
    actual=$?
    set -e
    [ "$actual" = "$expected" ] || {
        cat "$LOG" >&2
        fail "return=$actual expected=$expected"
    }
}
reset
check 0
grep -Fqx "native-remove-applied=$NEW" "$TMP/output" || fail "missing committed trial receipt"
grep -Fq 'gui-common-saved-builder' "$LOG" || fail "did not reuse GUI candidate compiler"
grep -Fq 'record:prepared' "$LOG" && grep -Fq 'record:activating' "$LOG" &&
grep -Fq 'record:activated' "$LOG" && grep -Fq 'record:config-saved' "$LOG" &&
grep -Fq 'record:committed' "$LOG" || fail "missing standard Apply journal phases"
grep -Fq runtime-activate "$LOG" && grep -Fq runtime-commit "$LOG" ||
    fail "missing original native runtime actuation"
if grep -Fqx 'config-save' "$LOG"; then fail "wrote Config"; fi
reset; DRIFT=1
check 69
if grep -Fq 'record:' "$LOG" || grep -Fq runtime-activate "$LOG"; then
    fail "saved Config drift reached journal/runtime"
fi
reset; ACTIVATE_FAIL=1
check 69
grep -Fqx runtime-restore "$LOG" && grep -Fqx record:restored "$LOG" ||
    fail "failed native activation did not restore old stopped owner"
[ ! -s "$TMP/output" ] || fail "failed activation produced success receipt"
reset; ATTEST_FAIL=1
check 69
grep -Fqx runtime-restore "$LOG" && grep -Fqx record:restored "$LOG" ||
    fail "failed post-activation witness did not restore old stopped owner"
reset; COMMIT_FAIL=1
check 70
grep -Fqx record:config-saved "$LOG" || fail "lost durable pending common owner"
! grep -Fqx record:committed "$LOG" || fail "uncertain commit claimed success"
reset; STATUS_FAIL=1
check 70
grep -Fqx record:committed "$LOG" || fail "lost completed trial evidence"
[ ! -s "$TMP/output" ] || fail "unverified native status produced success receipt"
reset; BAD_CONTEXT=1
check 69
[ ! -s "$LOG" ] || fail "missing journal witness reached service operation"
echo 'PASS: real saved common trial shell stages, native runtime, exact commit/rollback and refusal'
