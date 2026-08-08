#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
PROFILE_ADAPTER="${STRATEGY_LAB_PROFILE_CANDIDATE_ADAPTER:-${SCRIPT_DIR}/strategy_lab_profile_candidate_adapter.sh}"
set -eu

[ -x "${PYTHON_LAUNCHER}" ] || exit 69
[ -f "${PROFILE_ADAPTER}" ] || exit 69
export STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER="${PROFILE_ADAPTER}"

exec "${PYTHON_LAUNCHER}" result "$@"
