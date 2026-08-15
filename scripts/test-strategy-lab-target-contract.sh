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

[ "$(strategy_lab_normalize_target 203.0.113.9)" = 203.0.113.9 ] ||
    fail 'canonical IPv4 target normalization is incorrect'
[ "$(strategy_lab_target_type 203.0.113.9)" = ip ] ||
    fail 'IPv4 target type is incorrect'
strategy_lab_write_endpoints 203.0.113.9 ip "${TMP}/ip-endpoint"
printf '%s\n' 203.0.113.9 > "${TMP}/ip-expected"
cmp -s "${TMP}/ip-expected" "${TMP}/ip-endpoint" ||
    fail 'bare IPv4 endpoint contract is incorrect'

for invalid in \
    203.0.113.009 \
    999.0.0.1 \
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
        fail "invalid or unsupported target was accepted: ${invalid}"
    fi
 done

if strategy_lab_normalize_service_host 203.0.113.9 >/dev/null 2>&1; then
    fail 'IP literal was accepted as service Host / SNI'
fi
[ "$(strategy_lab_normalize_service_host 'Example.COM.')" = example.com ] ||
    fail 'service Host / SNI domain normalization is incorrect'

grep -Fq 'private function targetContract(): array' "${CONTROLLER}" ||
    fail 'API domain-or-IPv4 target classifier is missing'
grep -Fq 'FILTER_VALIDATE_IP, FILTER_FLAG_IPV4' "${CONTROLLER}" ||
    fail 'API does not explicitly accept canonical IPv4 targets'
grep -Fq "getPost('service_host'" "${CONTROLLER}" ||
    fail 'API optional Host / SNI contract is missing'
grep -Fq 'Invalid Strategy Lab domain or IPv4 address.' "${CONTROLLER}" ||
    fail 'API domain-or-IPv4 rejection is missing'
! grep -Fq 'TARGET_PATTERN' "${CONTROLLER}" ||
    fail 'old colon-permitting generic target pattern remains active'
grep -Fq "{{ lang._('Blocked Domain / IP') }}" "${VIEW}" ||
    fail 'GUI does not describe the accepted target as domain or IP'
grep -Fq 'id="strategyLabServiceHostInput"' "${VIEW}" ||
    fail 'GUI optional Host / SNI input is missing'
grep -Fq 'placeholder="rutracker.org / 203.0.113.10"' "${VIEW}" ||
    fail 'GUI domain/IP example is missing'

sh -n "${MODULE}"
echo 'PASS: Strategy Lab accepts normalized domains or canonical IPv4 targets and rejects URLs, ports, IPv6, and invalid target identities'