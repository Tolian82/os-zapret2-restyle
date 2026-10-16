#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="${ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/zapret-voice-ipsets.XXXXXX")
trap 'rm -rf "${WORK}"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }

. "${BACKEND}/common.sh"
. "${BACKEND}/registry.sh"
. "${BACKEND}/storage.sh"
. "${BACKEND}/targets.sh"

registry_build "${WORK}/registry.tsv"
storage_catalog_build "${WORK}/storage.tsv"
targets_prepare_managed "${WORK}/managed" \
    'youtube.com' '91.108.0.0/16' 'example.com' \
    ' 203.0.113.0/24
203.0.113.0/24
198.51.100.1' \
    '198.51.100.0/24' \
    '' \
    '192.0.2.15'

for name in telegram discord x sip custom; do
    expected="${WORK}/managed/ipset-${name}.txt"
    [ -f "${expected}" ] || fail "missing generated IPSET for ${name}"
    [ "$(stat -c %a "${expected}" 2>/dev/null || stat -f %Lp "${expected}")" = 644 ] ||
        fail "incorrect managed IPSET permissions: ${name}"
    [ "$(registry_lookup "${WORK}/registry.tsv" IPSET "${name}")" = "$(printf '%s\t%s\t%s' --ipset "ipset.${name}" 1)" ] ||
        fail "IPSET ${name} not registered to required managed storage"
    [ "$(storage_lookup "${WORK}/storage.tsv" "ipset.${name}")" = "$(printf '%s\t%s' managed "ipset-${name}.txt")" ] ||
        fail "IPSET ${name} storage mapping differs from registry"
    grep -Fq "hostlist.${name}ips" "${ROOT}/src/opnsense/service/templates/OPNsense/Zapret/zapret.conf" ||
        fail "IPSET ${name} is not read from persistent OPNsense model"
done

printf '%s\n' '203.0.113.0/24' '198.51.100.1' > "${WORK}/expected-discord"
cmp -s "${WORK}/managed/ipset-discord.txt" "${WORK}/expected-discord" ||
    fail "Discord normalization/order/dedup differs"
[ ! -s "${WORK}/managed/ipset-sip.txt" ] ||
    fail "disabled/empty SIP IPSET should remain empty, not 'any'"
grep -Fqx '91.108.0.0/16' "${WORK}/managed/ipset-telegram.txt" ||
    fail "existing Telegram IPSET was altered"
grep -Fqx '192.0.2.15' "${WORK}/managed/ipset-custom.txt" ||
    fail "Custom IPSET is not mapped"

if targets_prepare_managed "${WORK}/invalid" 'youtube.com' '91.108.0.0/16' \
    'example.com' '203.0.113.1/24' '' '' '' 2>"${WORK}/invalid.err"; then
    fail "accepted host bits in Discord CIDR"
fi
grep -Fq 'DISCORD IPs, line 1' "${WORK}/invalid.err" ||
    fail "bad CIDR error does not identify Discord and line"
grep -Fq "printf 'IPSET\ttelegram" "${BACKEND}/target_mode.sh" ||
    fail "Strategies lost historical Telegram default target policy"
if grep -Fq "printf 'IPSET\tdiscord" "${BACKEND}/target_mode.sh"; then
    fail "new Voice destination changed default Strategies target mode"
fi

echo "PASS: five shared IPSETs, normalization, errors, empty safety, Strategy defaults"
