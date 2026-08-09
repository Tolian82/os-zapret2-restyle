#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
BASE_ADAPTER="${STRATEGY_LAB_BASE_CANDIDATE_SYSTEM_ADAPTER:-${SCRIPT_DIR}/strategy_lab_candidate_adapter.sh}"
set -eu

[ -x "${BASE_ADAPTER}" ] || exit 69
exec /bin/sh "${BASE_ADAPTER}" "$@"
