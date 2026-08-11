#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
STAGE60_RUNNER="${STRATEGY_LAB_STAGE60_RUNNER:-${SCRIPT_DIR}/strategy_lab_stage60_parallel_runner.sh}"
set -eu
[ "$#" -eq 4 ] || exit 64
[ -x "${STAGE60_RUNNER}" ] || exit 69
exec "${STAGE60_RUNNER}" "$@"
