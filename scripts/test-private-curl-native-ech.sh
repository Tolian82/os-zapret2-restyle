#!/bin/sh
# Test the *real bundled FreeBSD binary* with ECH disabled, no external network.
set -eu
BIN="${1:-work/stage/usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate}"
[ -x "$BIN" ] || {
    echo "FAIL: no executable bundled curl-impersonate: $BIN" >&2
    exit 1
}
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT HUP INT TERM
if "$BIN" -q --ech false --noproxy '*' --connect-timeout 1 \
    --max-time 2 --silent --show-error --output /dev/null \
    https://127.0.0.1:1/ >/dev/null 2>"$tmp"; then
    code=0
else
    code=$?
fi
case "$code" in
    0|7|28) ;;
    *)
        echo "FAIL: FreeBSD private curl rejected or could not use --ech false (exit $code)" >&2
        cat "$tmp" >&2
        exit 1
        ;;
esac
echo "PASS: FreeBSD bundled private Chrome curl accepts ECH-off (loopback smoke)"
