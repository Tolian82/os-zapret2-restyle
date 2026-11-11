#!/bin/sh
# Exercise the original shell APIs against the one Python profile policy.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="$ROOT/src/opnsense/scripts/OPNsense/Zapret/backend"
BACKEND_DIR="$BACKEND"
PYTHON_RUNTIME=$(command -v python3)
export BACKEND_DIR PYTHON_RUNTIME
. "$BACKEND/common.sh"
. "$BACKEND/parser.sh"
. "$BACKEND/profile_normalizer.sh"
TMP=$(mktemp -d /tmp/zapret-profile-policy.XXXXXX)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
strategy='--filter-tcp=443
<HOSTLIST:youtube>
<IPSET:telegram>
--payload=tls_client_hello
--lua-desync=fake
--new=udp-target
--filter-udp=443
--payload=quic_initial
--lua-desync=multisplit'
count=$(parser_parse "$strategy" "$TMP")
[ "$count" = 2 ] || fail 'parser count'
grep -qx -- '--name=udp-target' "$TMP/profile-2.conf" || fail 'named native profile'
parser_validate_placeholder_syntax 1 "$TMP/profile-1.conf" || fail 'placeholder syntax'
parser_index_placeholders "$TMP/profile-1.conf" "$TMP/source.placeholders" || fail 'placeholder index'
printf 'HOSTLIST\tyoutube\nIPSET\ttelegram\n' > "$TMP/expected"
cmp -s "$TMP/expected" "$TMP/source.placeholders" || fail 'index differs'
count=$(profile_normalizer_normalize_all "$TMP" "$count")
[ "$count" = 3 ] || fail 'expanded count'
for file in "$TMP/profile-1.conf" "$TMP/profile-2.conf"; do
    grep -qx -- '--payload=tls_client_hello' "$file" || fail 'lost payload'
    grep -qx -- '--lua-desync=fake' "$file" || fail 'lost Lua handler'
done
grep -qx -- '--name=udp-target' "$TMP/profile-3.conf" || fail 'lost second --new'
if parser_parse '--new' "$TMP" >/dev/null 2>&1; then fail 'bad --new accepted'; fi
[ "$(cat "$TMP/profile-count")" = 3 ] || fail 'invalid parse mutated count'
[ -f "$TMP/profile-3.conf" ] || fail 'invalid parse removed profiles'
count=$(parser_parse '' "$TMP")
[ "$count" = 0 ] || fail 'empty strategy count'
[ ! -e "$TMP/profile-1.conf" ] || fail 'ghost profile'
count=$(profile_normalizer_normalize_all "$TMP" 0)
[ "$count" = 0 ] || fail 'zero normalization'
echo 'PASS: original shell profile interfaces delegate to one Python policy'
