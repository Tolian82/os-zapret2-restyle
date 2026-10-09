#!/bin/sh
# Native Voice requests must never activate silently through the old PoC.
# No router/kernel operations; pure generated shell-config gate regression.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "${ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend/config.sh"
common_error() { printf '%s\n' "$*" >&2; }

VOICE_TELEGRAM_REQUESTED=0
VOICE_DISCORD_REQUESTED=0
VOICE_X_REQUESTED=0
VOICE_SIP_REQUESTED=0
VOICE_CUSTOM_REQUESTED=0
config_voice_staged_only_guard ||
    { echo "FAIL: five OFF values must not block ordinary Zapret2" >&2; exit 1; }

for service in TELEGRAM DISCORD X SIP CUSTOM; do
    eval "VOICE_${service}_REQUESTED=1"
    if config_voice_staged_only_guard >/dev/null 2>&1; then
        echo "FAIL: ${service} ON would be silently ignored by PoC" >&2
        exit 1
    fi
    eval "VOICE_${service}_REQUESTED=0"
done

VOICE_TELEGRAM_REQUESTED='true'
if config_voice_staged_only_guard >/dev/null 2>&1; then
    echo "FAIL: invalid native Voice enablement incorrectly accepted" >&2
    exit 1
fi
VOICE_TELEGRAM_REQUESTED=0

# Templates must project each persisted native checkbox and default missing
# legacy model groups to OFF without invoking shell expansion of form args.
TPL="${ROOT}/src/opnsense/service/templates/OPNsense/Zapret/zapret.conf"
for service in telegram discord x sip custom; do
    grep -Fq "VOICE_$(printf '%s' "${service}" | tr '[:lower:]' '[:upper:]')_REQUESTED=" "${TPL}" ||
        { echo "FAIL: native checkbox is missing from generated template: ${service}" >&2; exit 1; }
    grep -Fq "OPNsense.Zapret.voice.${service}.enabled" "${TPL}" ||
        { echo "FAIL: native checkbox source is wrong: ${service}" >&2; exit 1; }
done

ORCH="${ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh"
grep -Fq 'config_voice_staged_only_guard || {' "${ORCH}" ||
    { echo "FAIL: native Voice preflight is not integrated" >&2; exit 1; }


# Verify START checks native Voice before cleanup_runtime even when
# an old engine was considered complete.
. "${ROOT}/src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh"
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT HUP INT TERM
SOURCE="${WORK}/zapret.conf"
CALLS="${WORK}/operations"
: > "${CALLS}"
orchestrator_runtime_is_complete() { return 1; }
orchestrator_cleanup_runtime() { printf '%s\n' cleanup >> "${CALLS}"; }
common_create_workspace() { return 1; }
launcher_status() { return 0; }
invoke_start() {
    orchestrator_native_start "${SOURCE}" /tmp/zapret /tmp/active /tmp/backup \
        /bin/true /tmp/child.pid /tmp/supd.pid /tmp/supmon.pid /tmp/suploop \
        /tmp/service 19000 19010 /tmp/stage /tmp/log /tmp/suplog
}
printf '%s\n' 'ZAPRET_ENABLED=1' 'VOICE_TELEGRAM_REQUESTED=1' > "${SOURCE}"
if invoke_start >/dev/null 2>&1; then
    echo "FAIL: unsupported Voice ON incorrectly started" >&2
    exit 1
fi
[ ! -s "${CALLS}" ] || {
    echo "FAIL: start destroyed running resources before Voice preflight" >&2
    exit 1
}
orchestrator_runtime_is_complete() { return 0; }
if invoke_start >/dev/null 2>&1; then
    echo "FAIL: complete old runtime incorrectly hides requested Voice ON" >&2
    exit 1
fi
[ ! -s "${CALLS}" ] || { echo "FAIL: old engine modified on rejected ON" >&2; exit 1; }
orchestrator_runtime_is_complete() { return 1; }
printf '%s\n' 'ZAPRET_ENABLED=1' 'VOICE_TELEGRAM_REQUESTED=0' > "${SOURCE}"
if invoke_start >/dev/null 2>&1; then
    echo "FAIL: mocked workspace was expected to refuse further start" >&2
    exit 1
fi
grep -qx 'cleanup' "${CALLS}" || {
    echo "FAIL: all Voice OFF unexpectedly bypassed ordinary start cleanup" >&2
    exit 1
}


# The top-level service entrypoint must also fail before firewall_prepare,
# which may load/configure IPFW even before reaching orchestrator.
SERVICE="${ROOT}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
for entry in start_service reconfigure_service; do
    body=$(sed -n "/^${entry}()$/,/^}$/p" "${SERVICE}")
    case "${body}" in
        *'refresh_generated_configuration || return 1'*'preflight_native_voice_before_firewall || return 1'*'prepare_firewall_prerequisites || return 1'*)
            ;;
        *)
            echo "FAIL: ${entry} may alter IPFW before Voice ON preflight" >&2
            exit 1
            ;;
    esac
done
awk '/^preflight_native_voice_before_firewall\(\)$/,/^}$/ { print }' "${SERVICE}" > "${WORK}/preflight.sh"
. "${WORK}/preflight.sh"
CONFIG="${SOURCE}"
printf '%s\n' 'ZAPRET_ENABLED=1' 'VOICE_TELEGRAM_REQUESTED=1' > "${SOURCE}"
if preflight_native_voice_before_firewall >/dev/null 2>&1; then
    echo "FAIL: service preflight allowed native Voice ON" >&2
    exit 1
fi
printf '%s\n' 'ZAPRET_ENABLED=0' 'VOICE_TELEGRAM_REQUESTED=1' > "${SOURCE}"
preflight_native_voice_before_firewall || {
    echo "FAIL: global Zapret OFF must remain able to stop the service" >&2
    exit 1
}
printf '%s\n' 'ZAPRET_ENABLED=1' 'VOICE_TELEGRAM_REQUESTED=0' > "${SOURCE}"
preflight_native_voice_before_firewall || {
    echo "FAIL: five Voice OFF settings must not disrupt ordinary service" >&2
    exit 1
}

echo "PASS: native Voice ON is fail-closed until one-engine IPFW/runtime migration is ready"
