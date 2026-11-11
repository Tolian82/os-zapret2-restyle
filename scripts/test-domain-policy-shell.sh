#!/bin/sh
# Test production targets.sh -> the one Python domain_policy.py.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="$ROOT/src/opnsense/scripts/OPNsense/Zapret/backend"
BACKEND_DIR="$BACKEND"
PYTHON_RUNTIME=$(command -v python3)
export BACKEND_DIR PYTHON_RUNTIME
. "$BACKEND/common.sh"
. "$BACKEND/targets.sh"
. "$BACKEND/exclude.sh"
TMP=$(mktemp -d "/tmp/zapret-domain-policy.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
printf '%s\n' '^!Example.com' 'plain.COM' > "$TMP/in.txt"
targets_normalize_hostlist "$TMP/in.txt" "$TMP/out.txt" 'YouTube Domains' || fail 'normalization'
printf '!^example.com\nplain.com\n' > "$TMP/expected.txt"
cmp -s "$TMP/out.txt" "$TMP/expected.txt" || fail 'HOSTLIST mismatch'
mkdir -p "$TMP/global"
file=$(exclude_prepare "$TMP/global" 'Example.com') || fail 'global Exclude preparation'
[ "$(cat "$file")" = example.com ] || fail 'global Exclude mismatch'
printf 'Example.com\n!Example.com\n' > "$TMP/in.txt"
if targets_normalize_hostlist "$TMP/in.txt" "$TMP/out.txt" 'User Domains' 2> "$TMP/errors.txt"; then
    fail 'contradictory entries accepted'
fi
grep -q 'line 2: conflicting_modifiers' "$TMP/errors.txt" || fail 'line error absent'
cmp -s "$TMP/out.txt" "$TMP/expected.txt" || fail 'failed normalization changed target'
printf '%s\n' '^Example.com' > "$TMP/in.txt"
if targets_normalize_hostlist "$TMP/in.txt" "$TMP/global/denied.txt" 'Exclude Domains' >/dev/null 2>&1; then
    fail 'Exclude accepted modifier'
fi
[ ! -e "$TMP/global/denied.txt" ] || fail 'invalid Exclude mutated target'
echo 'PASS: shell is a thin Python adapter, Exclude is isolated, failures are atomic'
