#!/bin/sh
# S05c1 source-level negative witnesses against the ACTUAL production function.
# Only private temporary fixture files; no installed service or kernel writes.
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/s05c1-fd9.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SERVICE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^service_with_lifecycle_lock()$/,/^}$/p' "$SERVICE" > "$ROOT/extracted.sh"
[ -s "$ROOT/extracted.sh" ] || fail "original function was not extracted"
sh -n "$ROOT/extracted.sh" || fail "original shell syntax"
. "$ROOT/extracted.sh"

LIFECYCLE_LOCK_FILE="$ROOT/original.lock"
LOCKF_BIN="$ROOT/lockf-mock.sh"
# Deliberately no Python interpreter: original native plain Status must work
# in the cold plugin-only state even when the interpreter is unavailable.
PYTHON_RUNTIME="$ROOT/missing-python"
PKG_UPDATE_RECORD="$ROOT/nonexistent-pkg-record.json"
cat > "$LOCKF_BIN" <<'STUB'
#!/bin/sh
[ "$#" -eq 4 ] && [ "$1" = -s ] && [ "$2" = -t ] &&
[ "$3" = 1 ] && [ "$4" = 9 ] || exit 64
[ "${LOCK_BUSY:-0}" = 1 ] && exit 75
exit 0
STUB
chmod 700 "$LOCKF_BIN"
export STATUS_PROJECTION_RC LOCK_BUSY
shared_apply_status_service() {
    case "${STATUS_PROJECTION_RC:-2}" in
        1) printf 'zapret is not running\n' ;;
        0) printf 'zapret is running\n' ;;
        *) printf 'zapret is in an incomplete runtime state\n' ;;
    esac
    return "${STATUS_PROJECTION_RC:-2}"
}
service_dispatch() {
    [ "$#" -eq 1 ] && [ "$1" = status ] || return 64
    printf 'zapret is not running\n'
    return 1
}

run_status() {
    expect_rc="$1"
    expected="$2"
    actual_rc=0
    service_with_lifecycle_lock 1 status > "$ROOT/result" 2> "$ROOT/stderr" || actual_rc=$?
    [ "$actual_rc" -eq "$expect_rc" ] || fail "source original rc: $actual_rc expected $expect_rc"
    if [ "$expected" = "@EMPTY@" ]; then : > "$ROOT/expected"; else printf '%s\n' "$expected" > "$ROOT/expected"; fi
    cmp -s "$ROOT/expected" "$ROOT/result" || fail "original status stdout changed"
    [ ! -s "$ROOT/stderr" ] || fail "private or unexpected stderr appeared"
}

# A nonexistent FD9 path MUST remain nonexistent. The ORIGINAL native
# observer may confirm STOPPED without Python; a purported RUNNING or UNKNOWN cannot.
[ ! -e "$LIFECYCLE_LOCK_FILE" ] || fail "fixture FD9 unexpectedly present"
STATUS_PROJECTION_RC=1
LOCK_BUSY=0
run_status 1 'zapret is not running'
[ ! -e "$LIFECYCLE_LOCK_FILE" ] || fail "plain Status created first-use original FD9"
for STATUS_PROJECTION_RC in 0 2 70; do
    run_status 2 'zapret is in an incomplete runtime state'
    [ ! -e "$LIFECYCLE_LOCK_FILE" ] || fail "unqualified fallback created FD9"
done

# If the ORIGINAL FD9 inode already exists, the same lockf must still
# execute on FD9, but open it read-only, never truncate any existing bytes.
printf 'existing original FD9 sentinel\n' > "$LIFECYCLE_LOCK_FILE"
cp "$LIFECYCLE_LOCK_FILE" "$ROOT/reference"
STATUS_PROJECTION_RC=70 # must NOT consult fallback with an existing FD9.
LOCK_BUSY=0
run_status 1 'zapret is not running'
cmp -s "$ROOT/reference" "$LIFECYCLE_LOCK_FILE" || fail "plain Status truncated FD9"
LOCK_BUSY=1
run_status 75 "@EMPTY@"
cmp -s "$ROOT/reference" "$LIFECYCLE_LOCK_FILE" || fail "BUSY Status modified original FD9"

echo "PASS: original native Pythonless plain Status on missing FD9, fail-closed negatives and same existing FD9 lock"
