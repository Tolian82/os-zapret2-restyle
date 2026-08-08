#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
REQUEST_MODULE="${ZAPRET_DIR}/strategy_lab/request.sh"
REQUEST_PY="${ZAPRET_DIR}/strategy_lab_py/request.py"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-freebsd-dns-timeout.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

MOCK_BIN="${TMP_ROOT}/bin"
OUTPUT_FILE="${TMP_ROOT}/dns.log"
mkdir -p "${MOCK_BIN}"

cat > "${MOCK_BIN}/drill" <<'MOCK'
#!/bin/sh
if [ "${MOCK_DNS_SLEEP:-0}" = 1 ]; then
    sleep 3
fi
printf '%s\n' ';; ANSWER SECTION:'
printf '%s. 60 IN %s 203.0.113.10\n' "$1" "$2"
MOCK
chmod +x "${MOCK_BIN}/drill"

SCRIPT_DIR="${ZAPRET_DIR}"
STRATEGY_LAB_PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-${STRATEGY_LAB_PYTHON_BIN:-python3.13}}
STRATEGY_LAB_PYTHON_LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
STRATEGY_LAB_DRILL_BIN="${MOCK_BIN}/drill"
export SCRIPT_DIR STRATEGY_LAB_PYTHON_BIN STRATEGY_LAB_PYTHON_LAUNCHER STRATEGY_LAB_DRILL_BIN

. "${REQUEST_MODULE}"

strategy_lab_dns_request blocked.example A "${OUTPUT_FILE}" ||
    fail "Python-owned DNS request failed"
grep -Fq 'blocked.example. 60 IN A 203.0.113.10' "${OUTPUT_FILE}" ||
    fail "Python-owned DNS request output is missing"

MOCK_DNS_SLEEP=1
export MOCK_DNS_SLEEP
set +e
strategy_lab_dns_request blocked.example A "${OUTPUT_FILE}"
status=$?
set -e
[ "${status}" -eq 124 ] ||
    fail "Python-owned DNS timeout returned ${status}, expected 124"
grep -Fq 'Strategy Lab subprocess timeout' "${OUTPUT_FILE}" ||
    fail "Python-owned DNS timeout evidence is missing"

# The old FreeBSD timeout(1) -f workaround is intentionally retired: Python now
# owns the deadline and process termination portably on both Linux CI and FreeBSD 15.
grep -Fq 'subprocess.run(' "${REQUEST_PY}" ||
    fail "Python request owner does not use subprocess execution"
grep -Fq 'timeout=timeout' "${REQUEST_PY}" ||
    fail "Python request owner does not enforce its subprocess timeout"
if grep -Fq 'STRATEGY_LAB_UNAME_BIN' "${REQUEST_MODULE}" || grep -Fq 'timeout -f' "${REQUEST_MODULE}"; then
    fail "retired platform-specific shell DNS timeout logic returned"
fi

sh -n "${REQUEST_MODULE}"
echo 'PASS: Strategy Lab DNS timeout is Python-owned and portable across FreeBSD 15 and Linux without timeout(1) foreground-mode branching'
