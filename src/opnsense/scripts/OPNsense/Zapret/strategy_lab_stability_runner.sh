#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
set -eu
[ "$#" -eq 5 ] || exit 64
[ -x "${PYTHON_LAUNCHER}" ] || exit 69
exec "${PYTHON_LAUNCHER}" search stabilize "$1" "$2" "$3" "$4" "$5"
