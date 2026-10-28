#!/bin/sh
# Regress the exact owner-installed pre-v0.6.1 eight-file sealed runtime.
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-old-exclude.XXXXXXXX")
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/backend/validator.sh
sed -n '/^validator_validate_runtime_modes()$/,/^}$/p' "$SOURCE" > "$ROOT/validator.sh"
sh -n "$ROOT/validator.sh" || fail "validator syntax"
. "$ROOT/validator.sh"
validator_fail() { echo "$*" > "$ROOT/error"; }
# FreeBSD stat -f format is modeled with exact owned fixture modes on Linux.
stat() {
    [ "$1" = -f ] && [ "$2" = '%Lp' ] || return 1
    case "$3" in
        "$ROOT/old"|"$ROOT/old/managed") echo 755 ;;
        "$ROOT/old/managed/"*) echo 644 ;;
        *) return 1 ;;
    esac
}
mkdir -p "$ROOT/old/managed"
for f in hostlist-youtube.txt ipset-telegram.txt ipset-discord.txt ipset-x.txt ipset-sip.txt ipset-custom.txt hostlist-user.txt hostlist-exclude.txt; do
    : > "$ROOT/old/managed/$f"
done
printf '%s\n' '--filter-tcp=443' > "$ROOT/old/dvtws.args"
if validator_validate_runtime_modes "$ROOT/old"; then fail "ordinary validator silently accepted missing exclude file"; fi
SHARED_BOOT_LEGACY_EMPTY_EXCLUDE_IPSET=1
validator_validate_runtime_modes "$ROOT/old" || fail "sealed old eight-file boot rejected"
SHARED_BOOT_LEGACY_EMPTY_EXCLUDE_IPSET=0
if validator_validate_runtime_modes "$ROOT/old"; then fail "new-format Apply bypassed required nine files"; fi
SHARED_BOOT_LEGACY_EMPTY_EXCLUDE_IPSET=1
: > "$ROOT/old/ipset-manifest.json"
if validator_validate_runtime_modes "$ROOT/old"; then fail "new manifest accepted with missing exclude file"; fi
rm "$ROOT/old/ipset-manifest.json"
printf '%s\n' '--ipset-exclude=/tmp/some-ipset' > "$ROOT/old/dvtws.args"
if validator_validate_runtime_modes "$ROOT/old"; then fail "old boot omitted required referenced IPSet file"; fi
printf '%s\n' '--filter-tcp=443' > "$ROOT/old/dvtws.args"
rm "$ROOT/old/managed/ipset-telegram.txt"
if validator_validate_runtime_modes "$ROOT/old"; then fail "legacy witness waived a different required file"; fi
: > "$ROOT/old/managed/ipset-telegram.txt"
rm "$ROOT/old/dvtws.args"
if validator_validate_runtime_modes "$ROOT/old"; then fail "old boot accepted missing engine args"; fi
printf '%s\n' '--filter-tcp=443' > "$ROOT/old/dvtws.args"
: > "$ROOT/old/managed/ipset-exclude.txt"
SHARED_BOOT_LEGACY_EMPTY_EXCLUDE_IPSET=0
validator_validate_runtime_modes "$ROOT/old" || fail "modern complete nine-file layout rejected"
echo "PASS: legacy sealed empty Exclude IPSet boot and strict modern file requirements"
