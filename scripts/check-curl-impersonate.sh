#!/bin/sh
# Local prerequisites only; not proof of a TLS/QUIC connection.
set -eu
ROOT=${ZAPRET2_IMPERSONATE_ROOT:-/usr/local/libexec/zapret2-restyle/curl-impersonate}
BIN="$ROOT/bin/curl-impersonate"
[ -x "$BIN" ] || { echo 'CURL_IMPERSONATE_MISSING' >&2; exit 1; }
[ -s "$ROOT/CHROME_PROFILE" ] || { echo 'CHROME_PROFILE_MISSING' >&2; exit 1; }
PROFILE=$(cat "$ROOT/CHROME_PROFILE")
case "$PROFILE" in chrome[0-9]*) ;; *) echo 'CHROME_PROFILE_INVALID' >&2; exit 1 ;; esac
"$BIN" -V | grep -q HTTP3 || { echo 'HTTP3_UNSUPPORTED' >&2; exit 1; }

valid_bundle()
{
    [ -f "$1" ] && [ -r "$1" ] && [ -s "$1" ] &&
        grep -q '^-----BEGIN CERTIFICATE-----' "$1"
}
CA=""
if [ -n "${ZAPRET2_IMPERSONATE_CA_BUNDLE:-}" ]; then
    case "$ZAPRET2_IMPERSONATE_CA_BUNDLE" in /*) ;; *)
        echo 'CA_BUNDLE_OVERRIDE_NOT_ABSOLUTE' >&2; exit 1 ;;
    esac
    valid_bundle "$ZAPRET2_IMPERSONATE_CA_BUNDLE" || {
        echo "CA_BUNDLE_OVERRIDE_INVALID: $ZAPRET2_IMPERSONATE_CA_BUNDLE" >&2
        exit 1
    }
    CA=$ZAPRET2_IMPERSONATE_CA_BUNDLE
else
    # OPNsense-managed bundle then FreeBSD/ports NSS bundle.
    # The default /etc/ssl/cert.pem caused curl(77) in owner-live 0.5.6_2.
    for path in /usr/local/etc/ssl/cert.pem /usr/local/share/certs/ca-root-nss.crt
    do
        if valid_bundle "$path"; then CA=$path; break; fi
    done
fi
[ -n "$CA" ] || {
    echo 'CURL_IMPERSONATE_CA_BUNDLE_UNAVAILABLE: no readable PEM at /usr/local/etc/ssl/cert.pem or /usr/local/share/certs/ca-root-nss.crt' >&2
    exit 1
}
case "${1:-}" in
    --print-ca) printf '%s\n' "$CA" ;;
    '') echo "CURL_IMPERSONATE_LOCAL_READY profile=$PROFILE ca_bundle=$CA network_tls_quic=NOT_TESTED" ;;
    *) echo 'Usage: check-curl-impersonate.sh [--print-ca]' >&2; exit 2 ;;
esac
