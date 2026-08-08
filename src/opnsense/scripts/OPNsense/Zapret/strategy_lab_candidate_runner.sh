#!/bin/sh
SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
set -eu
[ "$#" -ge 3 ] && [ "$#" -le 7 ] || exit 64
[ -x "${PYTHON_LAUNCHER}" ] || exit 69
JOB_ID="$1"
ENDPOINTS_FILE="$2"
RESULT_FILE="$3"
CANDIDATE_ID="${4:-smoke-multisplit}"
CANDIDATE_FAMILY="${5:-multisplit}"
STRATEGY_FILE="${6:-${MODULE_DIR}/catalog/tls13/01-multisplit.args}"
USE_HOSTLIST="${7:-1}"
exec "${PYTHON_LAUNCHER}" candidate run \
    "${JOB_ID}" "${ENDPOINTS_FILE}" "${RESULT_FILE}" \
    "${CANDIDATE_ID}" "${CANDIDATE_FAMILY}" "${STRATEGY_FILE}" "${USE_HOSTLIST}"
