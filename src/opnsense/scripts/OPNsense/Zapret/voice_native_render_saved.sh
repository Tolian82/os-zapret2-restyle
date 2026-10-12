#!/bin/sh
# Original OPNsense Jinja renderer bound to saved candidate XML and a
# private alternate target_root_directory. Called ONLY under existing FD9
# and original Config inode flock; never configctl template reload.
set -e
[ "$(id -u)" = "0" ] || exit 69
SOURCE=/var/db/zapret2/voice-build-input
ROOT="${SOURCE}/.voice-template-root"
PYTHON=/usr/local/bin/python3.13
TEMPLATE_CTL=/usr/local/opnsense/service/template_ctl.py
[ -x "${PYTHON}" ] && [ -f "${TEMPLATE_CTL}" ] || exit 69
[ -f "${SOURCE}/config.xml" ] && [ ! -L "${SOURCE}/config.xml" ] || exit 69
[ ! -e "${ROOT}" ] && [ ! -L "${ROOT}" ] || exit 69
[ ! -e "${SOURCE}/zapret.conf" ] && [ ! -L "${SOURCE}/zapret.conf" ] || exit 69
mkdir -m 700 "${ROOT}" || exit 69
"${PYTHON}" "${TEMPLATE_CTL}" -c "${SOURCE}/config.xml" -r "${ROOT}" OPNsense/Zapret || exit 69
OUT="${ROOT}/usr/local/etc/zapret2/zapret.conf"
[ -f "${OUT}" ] && [ ! -L "${OUT}" ] || exit 69
# Partial generation remains private evidence; no unknown overwrite/retry.
install -m 600 "${OUT}" "${SOURCE}/zapret.conf" || exit 69
