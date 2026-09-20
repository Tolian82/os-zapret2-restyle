#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMPOSE="${ROOT_DIR}/tools/telegram-voice-lab/compose.tos.yml"
EVIDENCE="${ROOT_DIR}/docs/verification/evidence/2026-09-20-telegram-voice-win-android-source-parity.md"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

[ -f "${COMPOSE}" ] || fail "Telegram Voice compose recipe is missing"
[ -f "${EVIDENCE}" ] || fail "Windows/Android source-parity evidence is missing"

grep -Fq "network_mode: host" "${COMPOSE}" ||
    fail "Telegram Voice lab must remain on Docker host networking"
grep -Fq "BUILD_WORKSPACE_SHA=6ad963e5b62d354da79040f388ae2b9132fb17b8" "${COMPOSE}" ||
    fail "build workspace pin changed"
grep -Fq "HARNESS_TGCALLS_SHA=e3069322a3d1e16ecb11a5e302242e59ddd7f09e" "${COMPOSE}" ||
    fail "qualified CLI harness pin changed"
grep -Fq "CLIENT_REFLECTOR_TGCALLS_SHA=24694f64b03e301ec2c90792566046e61a2c4967" "${COMPOSE}" ||
    fail "Windows/Android reflector reference pin changed"
grep -Fq "TDESKTOP_SOURCE_SHA=4d4da471fbee771c10e173a83c003ba1728989f1" "${COMPOSE}" ||
    fail "Telegram Desktop source epoch changed"
grep -Fq "ANDROID_SOURCE_SHA=9552e5541e1274b9557c9832b204dbfcaf44b3dc" "${COMPOSE}" ||
    fail "Telegram Android source epoch changed"

if grep -Fq '      - TELEGRAM_IOS_SHA=' "${COMPOSE}"; then
    fail "legacy client-authority TELEGRAM_IOS_SHA name returned"
fi
if grep -Fq '      - TGCALLS_SHA=' "${COMPOSE}"; then
    fail "ambiguous TGCALLS_SHA name returned"
fi
if grep -Fq '$$${' "${COMPOSE}"; then
    fail "invalid triple-dollar Compose interpolation found"
fi

grep -Fq 'git -C /work/Telegram-iOS fetch --depth=1 origin "$${BUILD_WORKSPACE_SHA}"' "${COMPOSE}" ||
    fail "build workspace fetch lost Compose-safe shell expansion"
grep -Fq 'test "$$(git -C /work/Telegram-iOS/submodules/TgVoipWebrtc/tgcalls rev-parse HEAD)" = \' "${COMPOSE}" ||
    fail "harness gitlink check lost shell command substitution"
grep -Fq '"$${HARNESS_TGCALLS_SHA}"' "${COMPOSE}" ||
    fail "harness SHA check lost Compose-safe shell expansion"

grep -Fq '/results/source-provenance.txt' "${COMPOSE}" ||
    fail "source provenance artifact is not emitted"
grep -Fq 'reflector_parity=source-audited-2026-09-20' "${COMPOSE}" ||
    fail "reflector source-audit marker is missing"
grep -Fq 'harness_tgcalls_sha=$${HARNESS_TGCALLS_SHA}' "${COMPOSE}" ||
    fail "harness provenance is missing"
grep -Fq 'client_reflector_tgcalls_sha=$${CLIENT_REFLECTOR_TGCALLS_SHA}' "${COMPOSE}" ||
    fail "client reflector provenance is missing"

grep -Fq '24694f64b03e301ec2c90792566046e61a2c4967' "${EVIDENCE}" ||
    fail "client reflector reference is missing from evidence"
grep -Fq 'e3069322a3d1e16ecb11a5e302242e59ddd7f09e' "${EVIDENCE}" ||
    fail "CLI harness reference is missing from evidence"
grep -Fq 'v1.0.5.2' "${EVIDENCE}" ||
    fail "current Zapret2 runtime boundary is missing from evidence"
grep -Fq 'not an independent DPI-free control' "${EVIDENCE}" ||
    fail "historical .140 path is not explicitly bounded"

echo 'PASS: Telegram Voice laboratory provenance and Compose escaping are pinned'
