#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
CANDIDATE_RUNNER="${STRATEGY_LAB_BASE_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
set -eu
[ "$#" -ge 6 ] && [ "$#" -le 7 ] || exit 64
[ -x "${CANDIDATE_RUNNER}" ] || exit 69
export STRATEGY_LAB_CANDIDATE_PROTOCOL=quic
export STRATEGY_LAB_CANDIDATE_PORT=443
export STRATEGY_LAB_CANDIDATE_L7=quic
exec "${CANDIDATE_RUNNER}" "$1" "$2" "$3" "$4" "$5" "$6" "${7:-1}"
