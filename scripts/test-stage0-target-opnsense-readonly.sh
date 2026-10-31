#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE="${ROOT}/stage0-target-opnsense-readonly.sh"
sh -n "$SOURCE"
for fixed in 'opnsense-version -a' 'pkg config ABI' 'pkg which' 'REPO_AUTOUPDATE=false' 'elfdump -d' 'REPO_OWNERSHIP=NOT_PROVEN_BY_THIS_PROBE' '/var/db/zapret2-restyle/FreeBSD.conf.backup'
do
    grep -Fq "$fixed" "$SOURCE" || { echo "FAIL: missing audit witness $fixed" >&2; exit 1; }
done
if grep -Eq '^[[:space:]]*(pkg (install|add|update|upgrade|remove|delete)|ipfw |configctl |rm |mv |cp |chmod |chown |ln |mkdir |touch )' "$SOURCE"; then
    echo 'FAIL: target probe contains a modifying command' >&2
    exit 1
fi
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT HUP INT TERM
sh "$SOURCE" >"$TMP" 2>&1
for marker in 'STAGE0_TARGET_PROBE=READ_ONLY' 'REPO_OWNERSHIP=NOT_PROVEN_BY_THIS_PROBE' 'STAGE0_TARGET_PROBE=END_READ_ONLY'
do
    grep -Fxq "$marker" "$TMP" || { echo "FAIL: missing marker $marker" >&2; exit 1; }
done
printf '%s\n' 'PASS: read-only OPNsense Stage 0 target probe syntax, negative inventory smoke, repository ownership stop condition'
