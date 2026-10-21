#!/bin/sh
# Standalone prerequisite check for future Strategy Lab entrypoint integration.
# Read-only; do not stop or modify the running zapret service.
set -eu
ROOT=${ZAPRET2_IMPERSONATE_ROOT:-/usr/local/libexec/zapret2-restyle/curl-impersonate}
BIN="${ROOT}/bin/curl-impersonate"
[ -x "${BIN}" ] || { echo 'CURL_IMPERSONATE_MISSING' >&2; exit 1; }
[ -s "${ROOT}/CHROME_PROFILE" ] || { echo 'CHROME_PROFILE_MISSING' >&2; exit 1; }
PROFILE=$(cat "${ROOT}/CHROME_PROFILE")
case "${PROFILE}" in chrome[0-9]*) ;; *) echo 'CHROME_PROFILE_INVALID' >&2; exit 1 ;; esac
"$BIN" -V | grep -q HTTP3 || { echo 'HTTP3_UNSUPPORTED' >&2; exit 1; }
[ -s /etc/ssl/cert.pem ] || [ -s /usr/local/share/certs/ca-root-nss.crt ] || {
    echo 'TRUSTED_CA_MISSING' >&2; exit 1;
}
echo "CURL_IMPERSONATE_READY profile=${PROFILE}"
