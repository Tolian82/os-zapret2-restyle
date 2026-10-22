#!/bin/sh
# A direct, pinned, certificate-verified HTTPS diagnostic.
# Unlike the Strategy Lab this read-only shortcut never starts/stops Zapret2.
# The UI may call the test "SUCCESS" only when the real target replied.
DOMAIN=${1:-}
if [ -z "$DOMAIN" ]; then
    echo 'No domain specified.'
    exit 1
fi
echo "$DOMAIN" | grep -qE '^[a-zA-Z0-9][a-zA-Z0-9.\-]+[a-zA-Z]{2,}$' || {
    echo 'Invalid domain format.'
    exit 1
}

echo "=== DNS Resolution ==="
DNS_RESULT=$(drill "$DOMAIN" A 2>/dev/null | awk '
    /^;; ANSWER SECTION/ {in_ans=1; next}
    /^;;/ {in_ans=0}
    in_ans && $4=="A" {print $5}
')
if [ -z "$DNS_RESULT" ]; then
    echo '(no IPv4 A answer)'
    echo ''
    echo '=== HTTPS Connection Test ==='
    echo '=== Result: DNS RESOLUTION FAILED ==='
    exit 0
fi
printf '%s\n' "$DNS_RESULT"
# Test one explicit IPv4 endpoint consistently. --resolve binds Host/SNI to
# this DNS answer; a local proxy/redirect cannot impersonate this remote IP.
TARGET_IP=$(printf '%s\n' "$DNS_RESULT" | awk 'NR==1 {print; exit}')
echo "Pinned target IPv4: $TARGET_IP"
echo ''
echo '=== HTTPS Connection Test ==='
echo 'Mode: direct Chrome-profile HTTPS (system CA; proxy bypassed)'
# The private FreeBSD Chrome launcher owns a trusted --cacert and -q.
# Test injection is local to the regression fixture; production uses only
# the installed private launcher and never falls back to insecure curl -k.
RUNNER=${ZAPRET_TEST_DOMAIN_CURL_BIN:-/usr/local/libexec/zapret2-restyle/run-curl-impersonate.sh}
CURL_OUTPUT=$("$RUNNER" -4 --noproxy '*' --proxy '' \
    --resolve "$DOMAIN:443:$TARGET_IP" --connect-timeout 5 --max-time 10 \
    --max-redirs 0 -sS -o /dev/null \
    -w "HTTP Status: %{http_code}\nRemote IP: %{remote_ip}\nTLS Verify: %{ssl_verify_result}\nTime Connect: %{time_connect}s\nTime TLS: %{time_appconnect}s\nTime Total: %{time_total}s\n" \
    "https://$DOMAIN/" 2>&1)
RESULT=$?
printf '%s\n' "$CURL_OUTPUT"
HTTP_STATUS=$(printf '%s\n' "$CURL_OUTPUT" | awk '/^HTTP Status: / {print $3}' | tail -n 1)
REMOTE_IP=$(printf '%s\n' "$CURL_OUTPUT" | awk '/^Remote IP: / {print $3}' | tail -n 1)
TLS_VERIFY=$(printf '%s\n' "$CURL_OUTPUT" | awk '/^TLS Verify: / {print $3}' | tail -n 1)
TLS_TIME=$(printf '%s\n' "$CURL_OUTPUT" | awk '/^Time TLS: / {sub(/s$/, "", $3); print $3}' | tail -n 1)
# A final response can be any 2xx-5xx HTTP status; HTTP/1.1 vs H2 does
# not affect reachability. No exit-only, spoofed proxy IP, or -k success.
case "$HTTP_STATUS" in
    [2345][0-9][0-9]) HTTP_FINAL=yes ;;
    *) HTTP_FINAL=no ;;
esac
TLS_ESTABLISHED=no
case "$TLS_TIME" in
    ''|*[!0-9.]*) ;;
    *) if awk "BEGIN {exit !($TLS_TIME > 0)}"; then TLS_ESTABLISHED=yes; fi ;;
esac
echo ''
if [ "$RESULT" -eq 0 ] && [ "$REMOTE_IP" != "$TARGET_IP" ]; then
    echo "Expected remote IP: $TARGET_IP"
    echo '=== Result: UNEXPECTED REMOTE IP (possible proxy or redirect) ==='
elif [ "$RESULT" -eq 0 ] && [ "$TLS_VERIFY" != 0 ]; then
    echo '=== Result: CERTIFICATE VERIFICATION FAILED ==='
elif [ "$RESULT" -eq 0 ] && [ "$TLS_ESTABLISHED" = yes ] && [ "$HTTP_FINAL" = yes ]; then
    echo '=== Result: SUCCESS ==='
elif [ "$RESULT" -eq 0 ]; then
    echo '=== Result: NO VERIFIED HTTPS RESPONSE ==='
elif [ "$RESULT" -eq 60 ]; then
    echo '=== Result: CERTIFICATE VERIFICATION FAILED ==='
elif [ "$RESULT" -eq 35 ]; then
    echo '=== Result: TLS HANDSHAKE FAILED ==='
elif [ "$RESULT" -eq 56 ]; then
    echo '=== Result: CONNECTION RESET ==='
elif [ "$RESULT" -eq 28 ]; then
    echo '=== Result: TIMEOUT ==='
elif [ "$RESULT" -eq 6 ]; then
    echo '=== Result: DNS RESOLUTION FAILED ==='
elif [ "$RESULT" -eq 7 ]; then
    echo '=== Result: CONNECTION FAILED ==='
else
    echo "=== Result: FAILED (curl exit code: $RESULT) ==="
fi
# configd script_output discards stdout on nonzero exit. Preserve the
# diagnostic result in stdout; API status=ok means report delivered only.
exit 0
