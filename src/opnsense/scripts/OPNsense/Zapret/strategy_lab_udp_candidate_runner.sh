#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
CANDIDATE_RUNNER="${STRATEGY_LAB_BASE_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
set -eu
[ "$#" -eq 6 ] || exit 64
[ -x "${CANDIDATE_RUNNER}" ] || exit 69
case "${STRATEGY_LAB_UDP_PORT:-}" in ''|*[!0-9]*) exit 64 ;; esac
[ -r "${STRATEGY_LAB_UDP_PAYLOAD_FILE:-}" ] && [ -s "${STRATEGY_LAB_UDP_PAYLOAD_FILE}" ] || exit 64
export STRATEGY_LAB_CANDIDATE_PROTOCOL=udp
export STRATEGY_LAB_CANDIDATE_PORT="${STRATEGY_LAB_UDP_PORT}"
export STRATEGY_LAB_CANDIDATE_L7='-'
exec "${CANDIDATE_RUNNER}" "$1" "$2" "$3" "$4" "$5" "$6" 0
