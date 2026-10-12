#!/bin/sh
# Stage-3 private production orchestrator entry. NEVER invokes start/stop,
# installer, IPFW adapter, GUI or configctl template reload.
# Called only by voice_native_prepare_route.py while original FD9 and the
# original /conf/config.xml inode flock remain held by its parent.
set -e
[ "$(id -u)" = "0" ] || exit 69
SOURCE=/var/db/zapret2/voice-build-input
SCRIPT_DIR=/usr/local/opnsense/scripts/OPNsense/Zapret
BACKEND_DIR="${SCRIPT_DIR}/backend"
ACTIVE=/usr/local/etc/zapret2/runtime-v2
RUNTIME=/usr/local/etc/zapret2
[ -f "${SOURCE}/config.xml" ] && [ ! -L "${SOURCE}/config.xml" ] || exit 69
[ -f "${SOURCE}/zapret.conf" ] && [ ! -L "${SOURCE}/zapret.conf" ] || exit 69
[ ! -e "${SOURCE}/release" ] && [ ! -L "${SOURCE}/release" ] || exit 69
[ ! -e "${SOURCE}/.voice-build-workspace" ] &&
    [ ! -L "${SOURCE}/.voice-build-workspace" ] || exit 69
mkdir -m 700 "${SOURCE}/.voice-build-workspace" || exit 69
for module in common config parser registry storage targets telegram_voice target_mode \
    profile_normalizer profile_pipeline exclude blobs ports firewall generator validator atomic \
    stage launcher supervisor orchestrator
do
    module_path="${BACKEND_DIR}/${module}.sh"
    [ -r "${module_path}" ] || exit 69
    . "${module_path}"
done
orchestrator_build_release \
    "${SOURCE}/zapret.conf" "${RUNTIME}" "${ACTIVE}" \
    "${SOURCE}/.voice-build-workspace" "${SOURCE}/release" \
    "${SOURCE}/.voice-build-workspace/stage.status" native-detached \
    "${SOURCE}/config.xml"
