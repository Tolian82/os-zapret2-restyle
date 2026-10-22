#!/bin/sh
# Proves the installed Chrome launcher forces ECH off for all caller modes.
# Network-free: fake curl is used; no OPNsense configuration is modified.
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/zapret-ech.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/curl-impersonate/bin"
cp "$ROOT_DIR/scripts/run-curl-impersonate.sh" "$ROOT_DIR/scripts/check-curl-impersonate.sh" "$work/"
printf 'chrome150\n' > "$work/curl-impersonate/CHROME_PROFILE"
printf '%s\n' '-----BEGIN CERTIFICATE-----' 'test-only-ca' '-----END CERTIFICATE-----' > "$work/ca.pem"
cat > "$work/curl-impersonate/bin/curl-impersonate" <<'FAKE_CURL'
#!/bin/sh
if [ "${1:-}" = "-V" ]; then
    echo 'curl-impersonate test binary: HTTP3'
    exit 0
fi
for arg do
    printf '[%s]\n' "$arg"
done
FAKE_CURL
chmod 755 "$work/curl-impersonate/bin/curl-impersonate"

verify()
{
    output=$(ZAPRET2_IMPERSONATE_ROOT="$work/curl-impersonate" \
        ZAPRET2_IMPERSONATE_CA_BUNDLE="$work/ca.pem" \
        "$work/run-curl-impersonate.sh" "$@")
    last=$(printf '%s\n' "$output" | tail -n 2)
    expected=$(printf '[--ech]\n[false]')
    [ "$last" = "$expected" ] || {
        echo 'FAIL: ECH must be disabled after all caller-provided flags' >&2
        exit 1
    }
    printf '%s\n' "$output" | grep -Fqx '[--impersonate]'
    printf '%s\n' "$output" | grep -Fqx '[chrome150]'
    printf '%s\n' "$output" | grep -Fqx '[--cacert]'
    printf '%s\n' "$output" | grep -Fqx '[-q]'
}
verify -4 --resolve example.com:443:203.0.113.10 https://example.com/
verify -4 --http3-only --resolve example.com:443:203.0.113.10 https://example.com/
verify -4 --ech true --resolve example.com:443:203.0.113.10 https://example.com/
echo 'PASS: private Chrome forces ECH off for HTTPS, HTTP3 and caller overrides'
