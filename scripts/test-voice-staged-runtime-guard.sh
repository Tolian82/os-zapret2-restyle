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

echo "PASS: native Voice ON is fail-closed until one-engine IPFW/runtime migration is ready"
