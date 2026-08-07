#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"

set -eu
umask 022

for module in common state firewall runtime candidate lifecycle circular
do
    module_path="${MODULE_DIR}/${module}.sh"
    [ -r "${module_path}" ] || {
        echo "ERROR: required Strategy Lab recovery module is missing: ${module_path}" >&2
        exit 1
    }
    . "${module_path}"
done

JOB_ID="${1:-}"
strategy_lab_job_id_valid "${JOB_ID}" || exit 64
strategy_lab_require_jq

# The same lifecycle-owned recovery transaction serves ordinary jobs and
# private circular sessions. Prefer the ordinary job namespace when it exists;
# otherwise bind all generic lifecycle/runtime helpers to the circular session.
JOB_DIR=$(strategy_lab_job_dir "${JOB_ID}")
STATUS_FILE=$(strategy_lab_status_file "${JOB_ID}")
if [ ! -r "${STATUS_FILE}" ]; then
    _strategy_lab_circular_state=$(strategy_lab_circular_session_state_file "${JOB_ID}" 2>/dev/null || true)
    [ -n "${_strategy_lab_circular_state}" ] && [ -r "${_strategy_lab_circular_state}" ] || {
        echo "ERROR: Strategy Lab stale recovery job/session state is unavailable" >&2
        exit 1
    }
    STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}"
    export STRATEGY_LAB_JOBS_DIR
    JOB_DIR=$(strategy_lab_circular_session_dir "${JOB_ID}")
    STATUS_FILE="${_strategy_lab_circular_state}"
    strategy_lab_status_file()
    {
        strategy_lab_circular_session_state_file "$1"
    }
fi
export JOB_ID JOB_DIR

SNAPSHOT_FILE=$(strategy_lab_lifecycle_snapshot_file)
[ -r "${SNAPSHOT_FILE}" ] || {
    echo "ERROR: Strategy Lab stale recovery has no lifecycle snapshot" >&2
    exit 2
}

STRATEGY_LAB_INITIAL_SERVICE_STATE=$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${SNAPSHOT_FILE}")
STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE=$("${STRATEGY_LAB_JQ}" -r '.source // ""' "${SNAPSHOT_FILE}")

case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
    RUNNING|STOPPED) ;;
    *)
        echo "ERROR: Strategy Lab stale recovery snapshot has invalid service state" >&2
        exit 2
        ;;
esac
case "${STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE}" in
    zapret_service|legacy-status) ;;
    *)
        echo "ERROR: Strategy Lab stale recovery snapshot has invalid evidence source" >&2
        exit 2
        ;;
esac

export STRATEGY_LAB_INITIAL_SERVICE_STATE STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE
strategy_lab_restore_initial_service_state
