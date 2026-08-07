#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REQUEST_MODULE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/request.sh"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-freebsd-dns-timeout.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

MOCK_BIN="${TMP_ROOT}/bin"
CALLS_FILE="${TMP_ROOT}/timeout.calls"
OUTPUT_FILE="${TMP_ROOT}/dns.log"
mkdir -p "${MOCK_BIN}"

cat > "${MOCK_BIN}/uname" <<'MOCK'
#!/bin/sh
printf '%s\n' "${MOCK_UNAME:-Linux}"
MOCK

cat > "${MOCK_BIN}/timeout" <<'MOCK'
#!/bin/sh
printf '%s\n' "$*" >> "${MOCK_TIMEOUT_CALLS}"
if [ "${1:-}" = -f ]; then
    shift
fi
shift
exec "$@"
MOCK

cat > "${MOCK_BIN}/drill" <<'MOCK'
#!/bin/sh
printf '%s\n' ';; ANSWER SECTION:'
printf '%s. 60 IN %s 203.0.113.10\n' "$1" "$2"
MOCK

chmod +x "${MOCK_BIN}"/*

STRATEGY_LAB_TIMEOUT_BIN="${MOCK_BIN}/timeout"
STRATEGY_LAB_DRILL_BIN="${MOCK_BIN}/drill"
STRATEGY_LAB_UNAME_BIN="${MOCK_BIN}/uname"
MOCK_TIMEOUT_CALLS="${CALLS_FILE}"
export STRATEGY_LAB_TIMEOUT_BIN STRATEGY_LAB_DRILL_BIN STRATEGY_LAB_UNAME_BIN MOCK_TIMEOUT_CALLS

. "${REQUEST_MODULE}"

: > "${CALLS_FILE}"
MOCK_UNAME=FreeBSD
export MOCK_UNAME
strategy_lab_dns_request blocked.example A "${OUTPUT_FILE}" ||
    fail "FreeBSD DNS request failed"
[ "$(cat "${CALLS_FILE}")" = "-f 2 ${MOCK_BIN}/drill blocked.example A" ] ||
    fail "FreeBSD DNS request did not use timeout -f"
grep -Fq 'blocked.example. 60 IN A 203.0.113.10' "${OUTPUT_FILE}" ||
    fail "FreeBSD DNS request output is missing"

: > "${CALLS_FILE}"
MOCK_UNAME=Linux
export MOCK_UNAME
strategy_lab_dns_request blocked.example A "${OUTPUT_FILE}" ||
    fail "non-FreeBSD DNS request failed"
[ "$(cat "${CALLS_FILE}")" = "2 ${MOCK_BIN}/drill blocked.example A" ] ||
    fail "non-FreeBSD DNS request unexpectedly used timeout -f"

sh -n "${REQUEST_MODULE}"

echo 'PASS: Strategy Lab FreeBSD DNS timeout uses foreground mode only on FreeBSD'
