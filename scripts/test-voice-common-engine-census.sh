#!/bin/sh
# Exact production engine census; fake process query only, no router writes.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh"
TMP=$(mktemp -d /tmp/zapret-census.XXXXXXXX) || exit 1
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
sed -n '/^apply_runtime_attest_engine_inventory()$/,/^}$/p' "$SOURCE" > "$TMP/census.sh"
sh -n "$TMP/census.sh" || fail "invalid census syntax"
. "$TMP/census.sh"
DVTWS_BIN=/usr/local/etc/zapret2/binaries/my/dvtws2
CHILD_PIDFILE="$TMP/child.pid"
COMMON_PS_BIN="$TMP/native-ps"
cat > "$COMMON_PS_BIN" <<'SH'
#!/bin/sh
[ "$1" = ax ] && [ "$2" = -o ] && [ "$3" = pid= ] &&
[ "$4" = -o ] && [ "$5" = command= ] || exit 1
[ "${QUERY_FAIL:-0}" = 0 ] || exit 1
cat "$FIXTURE"
SH
chmod 700 "$COMMON_PS_BIN"
FIXTURE="$TMP/ps.txt"
QUERY_FAIL=0
export FIXTURE QUERY_FAIL
common_error() { :; }
common_pidfile_read() { cat "$1" 2>/dev/null; }
check() {
    expected="$1"
    set +e
    apply_runtime_attest_engine_inventory
    status="$?"
    set -e
    [ "$status" -eq "$expected" ] || fail "status $status expected $expected"
}
: > "$FIXTURE"
_apply_engine=0
check 0
printf "%s\n" " 542 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
check 69
printf "%s\n" 542 > "$CHILD_PIDFILE"
_apply_engine=1
check 0
printf "%s\n" " 999 $DVTWS_BIN --filter-udp=443" > "$FIXTURE"
check 69
{
    printf "%s\n" " 542 $DVTWS_BIN --filter-udp=443"
    printf "%s\n" " 999 $DVTWS_BIN --filter-udp=555"
} > "$FIXTURE"
check 69
printf "%s\n" 555 > "$CHILD_PIDFILE"
check 69
# A similarly named application must not match the exact binary token.
printf "%s\n" " 999 ${DVTWS_BIN}-other --filter-udp=555" > "$FIXTURE"
_apply_engine=0
check 0
QUERY_FAIL=1; export QUERY_FAIL
check 69
echo 'PASS: orphan, duplicate, stale and missing-process-inventory refusal'
