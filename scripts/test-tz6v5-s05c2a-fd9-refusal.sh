#!/bin/sh
# S05c2a: extract actual production FD9 function; refuse fake success
# and verify marker is emitted ONLY by real rc75 of a test-only lockf stub.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TEMP=$(mktemp -d "${TMPDIR:-/tmp}/s05c2a.XXXXXXXX") || exit 1
trap 'rm -rf "$TEMP"' EXIT HUP INT TERM
error() { echo "S05C2A_SOURCE_REFUSED=$1" >&2; exit 1; }
SRC="$ROOT/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
sed -n '/^service_with_lifecycle_lock()$/,/^}$/p' "$SRC" > "$TEMP/fn.sh"
[ -s "$TEMP/fn.sh" ] || error MISSING_ORIGINAL_FD9_FUNCTION
sh -n "$TEMP/fn.sh" || error ORIGINAL_FD9_SYNTAX
. "$TEMP/fn.sh"
LIFECYCLE_LOCK_FILE="$TEMP/original-FD9"
PKG_UPDATE_RECORD="$TEMP/no-pkg-update.json"
LOCKF_BIN="$TEMP/fake-lockf"
cat > "$LOCKF_BIN" <<'STUB'
#!/bin/sh
[ "$#" -eq 4 ] && [ "$1" = -s ] && [ "$2" = -t ] &&
[ "$3" = 1 ] && [ "$4" = 9 ] || exit 64
exit "${LOCK_RESULT:-75}"
STUB
chmod 700 "$LOCKF_BIN"
export LOCK_RESULT
service_dispatch() { error ORIGINAL_DISPATCH_UNEXPECTED; }
test_case() {
    result_rc=0
    service_with_lifecycle_lock 1 "$@" > "$TEMP/output" 2> "$TEMP/error" ||
        result_rc=$?
    [ "$result_rc" -eq 75 ] || error BAD_LOCKF_EXIT
    [ ! -s "$TEMP/error" ] || error RAW_STDERR
    case "$#" in
        2)
            [ "$2" = --configd-receipt ] || error UNSUPPORTED_PARAMETER
            printf 'zapret-api-lifecycle-v1:%s:refused:fd9-busy\n' "$1" > "$TEMP/expected"
            [ "$LOCK_RESULT" -eq 75 ] || : > "$TEMP/expected"
            ;;
        1) : > "$TEMP/expected" ;;
        *) error WRONG_TEST_CASE ;;
    esac
    cmp -s "$TEMP/output" "$TEMP/expected" || error MARKER_MISMATCH
}
LOCK_RESULT=75
for verb in stop restart; do
    test_case "$verb" --configd-receipt
    test_case "$verb"
done
# Generic lockf error: original public rc remains 75 but MUST NOT claim busy.
LOCK_RESULT=1
for verb in stop restart; do
    test_case "$verb" --configd-receipt
done
test ! -e "$PKG_UPDATE_RECORD" || error JOURNAL_CREATED
echo "S05C2A_ORIGINAL_FD9_REFUSAL_SHELL=PASS"
