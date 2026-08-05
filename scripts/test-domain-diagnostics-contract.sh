#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEST_SCRIPT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/test_domain.sh"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/DiagnosticsController.php"
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM
MOCK_BIN="${TMP_ROOT}/bin"
mkdir -p "${MOCK_BIN}"
cat > "${MOCK_BIN}/drill" <<'MOCK'
#!/bin/sh
printf '%s\n' ';; ANSWER SECTION:' 'example.com. 60 IN A 203.0.113.10' ';; AUTHORITY SECTION:'
MOCK
cat > "${MOCK_BIN}/curl" <<'MOCK'
#!/bin/sh
printf '%s\n' 'HTTP Status: 000' 'Remote IP: 203.0.113.10' 'TLS Verify: 0' 'Time Connect: 0.010000s' 'Time TLS: 0.000000s' 'Time Total: 10.000000s'
exit "${MOCK_CURL_EXIT:-0}"
MOCK
chmod +x "${MOCK_BIN}/"*
run_case()
{
    set +e
    output=$(MOCK_CURL_EXIT="$1" PATH="${MOCK_BIN}:${PATH}" sh "${TEST_SCRIPT}" example.com 2>&1)
    status=$?
    set -e
    [ "${status}" -eq 0 ]
    printf '%s\n' "${output}" | grep -Fq "$2"
}
run_case 28 '=== Result: TIMEOUT ==='
run_case 56 '=== Result: CONNECTION RESET (likely DPI blocking) ==='
run_case 42 '=== Result: FAILED (curl exit code: 42) ==='
set +e
invalid=$(PATH="${MOCK_BIN}:${PATH}" sh "${TEST_SCRIPT}" 'bad/domain' 2>&1)
code=$?
set -e
[ "${code}" -ne 0 ]
printf '%s\n' "${invalid}" | grep -Fq 'Invalid domain format.'
grep -Fq "if (trim(\$response) === '')" "${CONTROLLER}"
grep -Fq 'Domain connectivity test returned no output.' "${CONTROLLER}"
for test in job-contract candidate-runtime family-screening parameter-expansion \
    stability-shortlist extended-tcp quic udp circular
do
    sh "${ROOT_DIR}/scripts/test-strategy-lab-${test}.sh"
done
echo 'Domain diagnostics contract tests passed.'
