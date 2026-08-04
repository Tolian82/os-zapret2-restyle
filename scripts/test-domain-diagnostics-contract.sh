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
cat <<'OUTPUT'
;; ANSWER SECTION:
example.com. 60 IN A 203.0.113.10
;; AUTHORITY SECTION:
OUTPUT
MOCK

cat > "${MOCK_BIN}/curl" <<'MOCK'
#!/bin/sh
printf '%s\n' \
    'HTTP Status: 000' \
    'Remote IP: 203.0.113.10' \
    'TLS Verify: 0' \
    'Time Connect: 0.010000s' \
    'Time TLS: 0.000000s' \
    'Time Total: 10.000000s'
exit "${MOCK_CURL_EXIT:-0}"
MOCK

chmod +x "${MOCK_BIN}/drill" "${MOCK_BIN}/curl"

run_connectivity_case() {
    curl_status="$1"
    expected_result="$2"

    set +e
    output=$(MOCK_CURL_EXIT="${curl_status}" PATH="${MOCK_BIN}:${PATH}" \
        sh "${TEST_SCRIPT}" example.com 2>&1)
    status=$?
    set -e

    [ "${status}" -eq 0 ] || {
        echo "Connectivity result ${curl_status} exited with ${status}" >&2
        exit 1
    }

    printf '%s\n' "${output}" | grep -Fq '=== DNS Resolution ==='
    printf '%s\n' "${output}" | grep -Fq '=== HTTPS Connection Test ==='
    printf '%s\n' "${output}" | grep -Fq "${expected_result}"
}

run_connectivity_case 28 '=== Result: TIMEOUT ==='
run_connectivity_case 56 '=== Result: CONNECTION RESET (likely DPI blocking) ==='
run_connectivity_case 42 '=== Result: FAILED (curl exit code: 42) ==='

set +e
invalid_output=$(PATH="${MOCK_BIN}:${PATH}" sh "${TEST_SCRIPT}" 'bad/domain' 2>&1)
invalid_status=$?
set -e

[ "${invalid_status}" -ne 0 ] || {
    echo 'Invalid input must remain an execution error' >&2
    exit 1
}
printf '%s\n' "${invalid_output}" | grep -Fq 'Invalid domain format.'

grep -Fq "if (trim(\$response) === '')" "${CONTROLLER}"
grep -Fq 'Domain connectivity test returned no output.' "${CONTROLLER}"

sh "${ROOT_DIR}/scripts/test-strategy-lab-job-contract.sh"
sh "${ROOT_DIR}/scripts/test-strategy-lab-candidate-runtime.sh"
sh "${ROOT_DIR}/scripts/test-strategy-lab-family-screening.sh"

echo 'Domain diagnostics contract tests passed.'
