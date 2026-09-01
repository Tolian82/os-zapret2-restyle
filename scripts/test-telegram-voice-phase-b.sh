#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/backend"
SERVICE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
ORCHESTRATOR="${BACKEND}/orchestrator.sh"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-telegram-voice.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

. "${BACKEND}/common.sh"
. "${BACKEND}/telegram_voice.sh"

MARKER="${TEST_ROOT}/telegram-voice.enabled"
IPSET="${TEST_ROOT}/ipset-telegram.txt"
EMPTY_IPSET="${TEST_ROOT}/ipset-empty.txt"
USER_TRAFFIC="${TEST_ROOT}/traffic-user.conf"
EFFECTIVE="${TEST_ROOT}/traffic.conf"
STATE="${TEST_ROOT}/telegram-voice-poc.state"
IPSET_REFERENCE="/usr/local/etc/zapret2/runtime-v2/managed/ipset-telegram.txt"

printf '%s\n' '91.108.4.0/22' '149.154.160.0/20' > "${IPSET}"
: > "${EMPTY_IPSET}"
printf '%s\n' \
    '--filter-tcp=443' \
    '--lua-desync=multisplit:pos=1' \
    '--new' \
    '--filter-udp=443,3478' \
    '--lua-desync=fake:blob=0x00' > "${USER_TRAFFIC}"

telegram_voice_build_effective_traffic \
    "${MARKER}" "${IPSET}" "${IPSET_REFERENCE}" \
    "${USER_TRAFFIC}" "${EFFECTIVE}" "${STATE}" ||
    fail 'disabled profile build failed'
grep -qx disabled "${STATE}" || fail 'disabled state was not recorded'
cmp -s "${USER_TRAFFIC}" "${EFFECTIVE}" ||
    fail 'disabled PoC changed the user strategy'

telegram_voice_marker_enable "${MARKER}" || fail 'marker enable failed'
telegram_voice_build_effective_traffic \
    "${MARKER}" "${IPSET}" "${IPSET_REFERENCE}" \
    "${USER_TRAFFIC}" "${EFFECTIVE}" "${STATE}" ||
    fail 'enabled profile build failed'
grep -qx enabled "${STATE}" || fail 'enabled state was not recorded'
grep -Fqx -- '--filter-l3=ipv4' "${EFFECTIVE}" || fail 'IPv4 filter is missing'
grep -Fqx -- '--filter-udp=*' "${EFFECTIVE}" || fail 'all-port UDP profile filter is missing'
grep -Fqx -- '--filter-l7=stun' "${EFFECTIVE}" || fail 'STUN profile selector is missing'
grep -Fqx -- '--payload=stun' "${EFFECTIVE}" || fail 'STUN Lua payload guard is missing'
grep -Fqx -- "--ipset=${IPSET_REFERENCE}" "${EFFECTIVE}" ||
    fail 'managed Telegram IP set reference is missing'
grep -Fqx -- '--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2' \
    "${EFFECTIVE}" || fail 'upstream zero-fake baseline changed'
helper_line=$(grep -n -F -- '--name=telegram-voice-poc' "${EFFECTIVE}" | cut -d: -f1)
user_line=$(grep -n -F -- '--filter-tcp=443' "${EFFECTIVE}" | cut -d: -f1)
[ "${helper_line}" -lt "${user_line}" ] || fail 'STUN helper is not the first profile'

if telegram_voice_build_effective_traffic \
    "${MARKER}" "${EMPTY_IPSET}" "${IPSET_REFERENCE}" \
    "${USER_TRAFFIC}" "${EFFECTIVE}" "${STATE}" 2>/dev/null; then
    fail 'enabled PoC accepted an empty Telegram IPv4 set'
fi

MOCK_IPFW_DIR="${TEST_ROOT}/ipfw"
IPFW_BIN="${TEST_ROOT}/ipfw-mock"
export MOCK_IPFW_DIR IPFW_BIN
mkdir -p "${MOCK_IPFW_DIR}"

cat > "${IPFW_BIN}" <<'MOCK'
#!/bin/sh
set -eu
while [ "${1:-}" = -q ] || [ "${1:-}" = -qf ]; do
    shift
done
command=${1:-}
[ -n "${command}" ] || exit 64
shift
case "${command}" in
    table)
        name=$1
        action=$2
        shift 2
        table_file="${MOCK_IPFW_DIR}/table.${name}"
        case "${action}" in
            info)
                [ -f "${table_file}" ]
                ;;
            create)
                [ ! -e "${table_file}" ] || exit 1
                : > "${table_file}"
                ;;
            destroy)
                rm -f "${table_file}"
                ;;
            add)
                printf '%s\n' "$1" >> "${table_file}"
                ;;
            swap)
                other_file="${MOCK_IPFW_DIR}/table.$1"
                [ -f "${table_file}" ] && [ -f "${other_file}" ] || exit 1
                swap_file="${MOCK_IPFW_DIR}/swap.$$"
                mv "${table_file}" "${swap_file}"
                mv "${other_file}" "${table_file}"
                mv "${swap_file}" "${other_file}"
                ;;
            list)
                cat "${table_file}"
                ;;
            *) exit 64 ;;
        esac
        ;;
    add)
        number=$1
        shift
        if [ -f "${MOCK_IPFW_DIR}/fail-helper" ] &&
           printf '%s\n' "$*" | grep -Fq 'table(zapret2_tgvoice)'; then
            exit 1
        fi
        printf '%s %s\n' "${number}" "$*" > "${MOCK_IPFW_DIR}/rule.${number}"
        ;;
    delete)
        rm -f "${MOCK_IPFW_DIR}/rule.$1"
        ;;
    list)
        if [ "$#" -eq 0 ]; then
            for rule in "${MOCK_IPFW_DIR}"/rule.*; do
                [ -f "${rule}" ] && cat "${rule}"
            done
        elif [ -f "${MOCK_IPFW_DIR}/rule.$1" ]; then
            cat "${MOCK_IPFW_DIR}/rule.$1"
        fi
        ;;
    show)
        [ -f "${MOCK_IPFW_DIR}/rule.$1" ] || exit 1
        body=$(cat "${MOCK_IPFW_DIR}/rule.$1")
        number=${body%% *}
        printf '%s 7 280 %s\n' "${number}" "${body#* }"
        ;;
    *) exit 64 ;;
esac
MOCK
chmod 0755 "${IPFW_BIN}"

. "${BACKEND}/firewall.sh"

TCP_PORTS="${TEST_ROOT}/tcp-ports.txt"
UDP_PORTS="${TEST_ROOT}/udp-ports.txt"
printf '%s\n' 443 > "${TCP_PORTS}"
printf '%s\n' 3478 > "${UDP_PORTS}"

firewall_install_runtime_rules \
    "${TCP_PORTS}" "${UDP_PORTS}" wan0 989 19000 19010 \
    "${STATE}" "${IPSET}" || fail 'scoped runtime rule installation failed'
cmp -s "${IPSET}" "${MOCK_IPFW_DIR}/table.${TELEGRAM_VOICE_TABLE}" ||
    fail 'active IPFW table does not contain the normalized Telegram set'
grep -Fq 'udp from any to table(zapret2_tgvoice)' \
    "${MOCK_IPFW_DIR}/rule.19000" || fail 'helper rule is not destination scoped'
grep -Fq 'out not diverted not sockarg xmit wan0' \
    "${MOCK_IPFW_DIR}/rule.19000" || fail 'helper rule lost reinjection/WAN guards'
grep -Fq 'tcp from any to any 443' "${MOCK_IPFW_DIR}/rule.19001" ||
    fail 'normal user TCP rule was not shifted behind the helper'
grep -Fq 'udp from any to any 3478' "${MOCK_IPFW_DIR}/rule.19002" ||
    fail 'normal user UDP rule changed'
if grep -R -Fq 'udp from any to any 1-65535' "${MOCK_IPFW_DIR}"; then
    fail 'PoC installed an all-Internet UDP rule'
fi
[ "$(firewall_telegram_voice_rule_counters 19000)" = '7 280' ] ||
    fail 'helper counters are not readable'
firewall_telegram_voice_runtime_complete "${STATE}" 19000 ||
    fail 'enabled Telegram Voice runtime was not recognized as complete'

printf '%s\n' disabled > "${STATE}"
firewall_install_runtime_rules \
    "${TCP_PORTS}" "${UDP_PORTS}" wan0 989 19000 19010 \
    "${STATE}" "${IPSET}" || fail 'disabled runtime rule installation failed'
grep -Fq 'tcp from any to any 443' "${MOCK_IPFW_DIR}/rule.19000" ||
    fail 'normal TCP rule did not return to its default number after disable'
[ ! -e "${MOCK_IPFW_DIR}/rule.19002" ] || fail 'shifted UDP rule survived disable'
[ ! -e "${MOCK_IPFW_DIR}/table.${TELEGRAM_VOICE_TABLE}" ] ||
    fail 'helper table survived disable'
if firewall_telegram_voice_rule_counters 19000 >/dev/null 2>&1; then
    fail 'ordinary rule 19000 was misreported as the helper counter'
fi
firewall_telegram_voice_runtime_complete "${STATE}" 19000 ||
    fail 'clean disabled runtime was not recognized as complete'

printf '%s\n' enabled > "${STATE}"
printf '%s\n' '10.0.0.0/8' > "${IPSET}"
firewall_install_runtime_rules \
    "${TCP_PORTS}" "${UDP_PORTS}" wan0 989 19000 19010 \
    "${STATE}" "${IPSET}" || fail 'rollback fixture installation failed'
printf '%s\n' '91.108.8.0/22' > "${IPSET}"
: > "${MOCK_IPFW_DIR}/fail-helper"
if firewall_install_runtime_rules \
    "${TCP_PORTS}" "${UDP_PORTS}" wan0 989 19000 19010 \
    "${STATE}" "${IPSET}"; then
    fail 'helper rule failure was accepted'
fi
grep -Fqx '10.0.0.0/8' "${MOCK_IPFW_DIR}/table.${TELEGRAM_VOICE_TABLE}" ||
    fail 'failed rule replacement did not restore the previous IPFW table'
rm -f "${MOCK_IPFW_DIR}/fail-helper"

grep -Fq 'telegram_voice_build_effective_traffic' "${ORCHESTRATOR}" ||
    fail 'orchestrator does not build the temporary profile'
grep -Fq 'firewall_install_runtime_rules' "${ORCHESTRATOR}" ||
    fail 'orchestrator does not install scoped runtime rules'
grep -Fq 'telegram_voice' "${SERVICE}" || fail 'service control surface is missing'
grep -Fq '[telegram_voice_enable]' "${ACTIONS}" || fail 'enable action is missing'
grep -Fq '[telegram_voice_disable]' "${ACTIONS}" || fail 'disable action is missing'
grep -Fq '[telegram_voice_status]' "${ACTIONS}" || fail 'status action is missing'

sh -n "${BACKEND}/telegram_voice.sh"
sh -n "${BACKEND}/firewall.sh"
sh -n "${ORCHESTRATOR}"
sh -n "${SERVICE}"

echo 'PASS: Telegram Voice Phase B is opt-in, Telegram-IP scoped, observable, and rollback-safe'
