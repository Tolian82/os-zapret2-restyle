#!/bin/sh
# Private Chrome client; explicit trusted system PEM, ECH off, never system curl or -k.
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=${ZAPRET2_IMPERSONATE_ROOT:-"$DIR/curl-impersonate"}
PROFILE=$(cat "$ROOT/CHROME_PROFILE")
CA=$(ZAPRET2_IMPERSONATE_ROOT="$ROOT" "$DIR/check-curl-impersonate.sh" --print-ca)
# Keep ECH off after all caller flags, including an accidental --ech override.
# The same policy applies to direct, candidate, QUIC and replay requests.
exec "$ROOT/bin/curl-impersonate" -q --impersonate "$PROFILE" --compressed \
    --cacert "$CA" --noproxy '*' "$@" --ech false
