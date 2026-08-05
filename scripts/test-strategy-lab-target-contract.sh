#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/target.sh"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-target-contract.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

. "${MODULE}"

[ "$(strategy_lab_normalize_target 'Telegram.ORG.')" = telegram.org ] ||
    fail 'domain normalization is incorrect'
[ "$(strategy_lab_target_type telegram.org)" = domain ] ||
    fail 'domain target type is incorrect'
strategy_lab_write_endpoints telegram.org domain "${TMP}/endpoints"
printf '%s\n' telegram.org web.telegram.org > "${TMP}/expected"
cmp -s "${TMP}/expected" "${TMP}/endpoints" ||
    fail 'Telegram endpoint expansion is incorrect'

for invalid in \
    203.0.113.9 \
    2001:db8::1 \
    example.com:443 \
    https://example.com \
    example \
    .example.com \
    example..com \
    -example.com \
    example-.com \
    example.123
 do
    if strategy_lab_normalize_target "${invalid}" >/dev/null 2>&1; then
        fail "invalid or implicit target was accepted: ${invalid}"
    fi
 done

if strategy_lab_write_endpoints 203.0.113.9 ip "${TMP}/ip-endpoint"; then
    fail 'backend-only implicit IP endpoint contract remains active'
fi

grep -Fq 'private function domainTarget(): string' "${CONTROLLER}" ||
    fail 'API domain validator is missing'
grep -Fq 'FILTER_VALIDATE_IP' "${CONTROLLER}" ||
    fail 'API does not explicitly reject IP literals'
grep -Fq 'Invalid Strategy Lab domain.' "${CONTROLLER}" ||
    fail 'API domain-specific rejection is missing'
! grep -Fq 'TARGET_PATTERN' "${CONTROLLER}" ||
    fail 'old colon-permitting generic target pattern remains active'
grep -Fq "{{ lang._('Blocked Domain') }}" "${VIEW}" ||
    fail 'GUI does not describe the accepted target as a domain'
grep -Fq 'placeholder="rutracker.org"' "${VIEW}" ||
    fail 'GUI domain example is missing'

sh -n "${MODULE}"
echo 'PASS: Strategy Lab accepts normalized domains only and rejects implicit IP/port/URL targets'
