#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEST_SCRIPT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/test_domain.sh"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/DiagnosticsController.php"
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT HUP INT TERM
MOCK_BIN="$TMP_ROOT/bin"
mkdir -p "$MOCK_BIN"

cat > "$MOCK_BIN/drill" <<'MOCK'
#!/bin/sh
[ "${MOCK_DNS_EMPTY:-0}" = 1 ] && exit 0
printf '%s\n' ';; ANSWER SECTION:' 'example.com. 60 IN A 203.0.113.10' 'example.com. 60 IN A 203.0.113.11' ';; AUTHORITY SECTION:'
MOCK
cat > "$MOCK_BIN/chrome" <<'MOCK'
#!/bin/sh
printf '%s\n' "$@" > "$MOCK_ARGS_FILE"
printf 'HTTP Status: %s\nRemote IP: %s\nTLS Verify: %s\nTime Connect: 0.001000s\nTime TLS: %ss\nTime Total: 0.080000s\n' \
    "${MOCK_HTTP_STATUS:-200}" "${MOCK_REMOTE_IP:-203.0.113.10}" \
    "${MOCK_TLS_VERIFY:-0}" "${MOCK_TLS_TIME:-0.053000}"
exit "${MOCK_CURL_EXIT:-0}"
MOCK
chmod +x "$MOCK_BIN/"*

run_case()
{
    expected="$1"; shift
    output=$(env PATH="$MOCK_BIN:$PATH" MOCK_ARGS_FILE="$TMP_ROOT/args" \
        ZAPRET_TEST_DOMAIN_CURL_BIN="$MOCK_BIN/chrome" "$@" \
        sh "$TEST_SCRIPT" example.com 2>&1)
    printf '%s\n' "$output" | grep -Fq "=== Result: $expected ===" || {
        echo "FAIL: expected [$expected], got [$output]" >&2
        exit 1
    }
}

run_case 'SUCCESS' MOCK_CURL_EXIT=0 MOCK_HTTP_STATUS=200
# HTTP1/2 final 3xx-5xx is a valid authenticated response; no body needed.
run_case 'SUCCESS' MOCK_CURL_EXIT=0 MOCK_HTTP_STATUS=404
run_case 'SUCCESS' MOCK_CURL_EXIT=0 MOCK_HTTP_STATUS=503
# The actual owner failure: curl returned 200 through LAN 192.168.1.2 and
# TLS Verify 19. It MUST NEVER produce a success.
run_case 'UNEXPECTED REMOTE IP (possible proxy or redirect)' \
    MOCK_CURL_EXIT=0 MOCK_HTTP_STATUS=200 MOCK_REMOTE_IP=192.168.1.2 MOCK_TLS_VERIFY=19
run_case 'UNEXPECTED REMOTE IP (possible proxy or redirect)' \
    MOCK_CURL_EXIT=0 MOCK_HTTP_STATUS=200 MOCK_REMOTE_IP=192.168.1.2 MOCK_TLS_VERIFY=0
run_case 'CERTIFICATE VERIFICATION FAILED' MOCK_CURL_EXIT=0 MOCK_TLS_VERIFY=20
run_case 'CERTIFICATE VERIFICATION FAILED' MOCK_CURL_EXIT=60 MOCK_TLS_VERIFY=19
run_case 'NO VERIFIED HTTPS RESPONSE' MOCK_CURL_EXIT=0 MOCK_HTTP_STATUS=000
run_case 'NO VERIFIED HTTPS RESPONSE' MOCK_CURL_EXIT=0 MOCK_TLS_TIME=0.000000
run_case 'TIMEOUT' MOCK_CURL_EXIT=28
run_case 'CONNECTION RESET' MOCK_CURL_EXIT=56
run_case 'TLS HANDSHAKE FAILED' MOCK_CURL_EXIT=35
run_case 'CONNECTION FAILED' MOCK_CURL_EXIT=7
run_case 'FAILED (curl exit code: 42)' MOCK_CURL_EXIT=42

# Assert this is a pinned, direct, CA-verifying Chrome request. No insecure
# -k, -K or --insecure; not even a potential system-curl fallback.
grep -Fxq -- '--resolve' "$TMP_ROOT/args"
grep -Fxq -- 'example.com:443:203.0.113.10' "$TMP_ROOT/args"
grep -Fxq -- '--noproxy' "$TMP_ROOT/args"
grep -Fxq -- '--proxy' "$TMP_ROOT/args"
grep -Fxq -- 'https://example.com/' "$TMP_ROOT/args"
if grep -Exq -- '-k|--insecure|-K' "$TMP_ROOT/args"; then
    echo 'FAIL: disabled certificate checks in production arguments' >&2; exit 1
fi
if grep -Fq -- '203.0.113.11' "$TMP_ROOT/args"; then
    echo 'FAIL: did not pin the selected DNS answer' >&2; exit 1
fi

no_dns=$(env PATH="$MOCK_BIN:$PATH" MOCK_DNS_EMPTY=1 \
    ZAPRET_TEST_DOMAIN_CURL_BIN="$MOCK_BIN/chrome" sh "$TEST_SCRIPT" example.com)
printf '%s\n' "$no_dns" | grep -Fq '=== Result: DNS RESOLUTION FAILED ==='
set +e
invalid=$(env PATH="$MOCK_BIN:$PATH" sh "$TEST_SCRIPT" 'bad/domain' 2>&1)
status=$?
set -e
[ "$status" -ne 0 ]
printf '%s\n' "$invalid" | grep -Fq 'Invalid domain format.'
grep -Fq "if (trim(\$response) === '')" "$CONTROLLER"
grep -Fq 'Domain connectivity test returned no output.' "$CONTROLLER"
sh -n "$TEST_SCRIPT"
echo 'PASS: pinned direct private Chrome HTTPS rejects LAN redirects/invalid TLS and exit-only success'
