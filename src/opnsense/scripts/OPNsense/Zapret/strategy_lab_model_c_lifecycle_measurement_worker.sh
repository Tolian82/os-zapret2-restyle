#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
MODEL_B_ADAPTER="${STRATEGY_LAB_MODEL_B_SYSTEM_ADAPTER:-${SCRIPT_DIR}/strategy_lab_model_b_adapter.sh}"
CANDIDATE_ADAPTER="${STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER:-${SCRIPT_DIR}/strategy_lab_candidate_adapter.sh}"
STRATEGY_LAB_JQ="${STRATEGY_LAB_JQ:-/usr/local/bin/jq}"
STRATEGY_LAB_RUN_DIR="${STRATEGY_LAB_RUN_DIR:-/var/run/zapret2-restyle/strategy-lab}"
REFERENCE_JOBS_DIR="${STRATEGY_LAB_REFERENCE_JOBS_DIR:-${STRATEGY_LAB_RUN_DIR}/jobs}"
REFERENCE_JOB="${1:-}"
OUTPUT="${2:-}"
REPEATS="${3:-5}"

set -u
umask 022
case "${REFERENCE_JOB}" in job.*) ;; *) exit 64 ;; esac
[ -n "${OUTPUT}" ] || exit 64
[ -x "${PYTHON_LAUNCHER}" ] || { echo 'ERROR: Strategy Lab Python launcher is unavailable' >&2; exit 70; }
[ -x "${MODEL_B_ADAPTER}" ] || { echo 'ERROR: Model-C runtime adapter is unavailable' >&2; exit 70; }
[ -x "${CANDIDATE_ADAPTER}" ] || { echo 'ERROR: Strategy Lab candidate adapter is unavailable' >&2; exit 70; }
[ -x "${STRATEGY_LAB_JQ}" ] || { echo 'ERROR: jq is unavailable' >&2; exit 70; }
[ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] || { echo 'ERROR: Model-C lifecycle measurement has no lifecycle-lock owner' >&2; exit 77; }
( : >&9 ) 2>/dev/null || { echo 'ERROR: Model-C lifecycle measurement lock descriptor is unavailable' >&2; exit 77; }
[ -x "${STRATEGY_LAB_SERVICE_SCRIPT:-}" ] || { echo 'ERROR: Model-C lifecycle measurement service control is unavailable' >&2; exit 70; }

SESSION_ROOT="${STRATEGY_LAB_RUN_DIR}/model-c-lifecycle-measurement"
SESSION_DIR="${SESSION_ROOT}/session.$$"
INITIAL_EVIDENCE="${SESSION_DIR}/lifecycle-initial.json"
FINAL_EVIDENCE="${SESSION_DIR}/lifecycle-final.json"
REFERENCE_STATUS="${REFERENCE_JOBS_DIR}/${REFERENCE_JOB}/status.json"
STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR="${SESSION_DIR}/runs"
CLEANUP_SESSION="${SESSION_DIR}/cleanup-runtime"
export STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR
export STRATEGY_LAB_REFERENCE_JOBS_DIR="${REFERENCE_JOBS_DIR}"
mkdir -p "${STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR}" "${CLEANUP_SESSION}" || exit 70
chmod 0700 "${SESSION_ROOT}" "${SESSION_DIR}" "${STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR}" "${CLEANUP_SESSION}" 2>/dev/null || exit 70

initial_state=''
service_changed=0
cleanup_ok=0
finalized=0

capture_evidence()
{
    _output="$1"
    "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-evidence > "${_output}" 2>/dev/null || return 1
    "${STRATEGY_LAB_JQ}" -e '.schema==1 and .source=="zapret_service" and (.state=="RUNNING" or .state=="STOPPED")' "${_output}" >/dev/null || return 1
    chmod 0600 "${_output}"
}
cleanup_warm_runtime()
{
    STRATEGY_LAB_MODEL_B_SESSION_DIR="${CLEANUP_SESSION}" "${MODEL_B_ADAPTER}" cleanup-all >/dev/null 2>&1
}
cleanup_all_measurement_runtime()
{
    _cleanup_status=0
    cleanup_warm_runtime || _cleanup_status=1
    "${CANDIDATE_ADAPTER}" cleanup "${REFERENCE_JOB}" >/dev/null 2>&1 || _cleanup_status=1
    return "${_cleanup_status}"
}
restore_service()
{
    [ "${service_changed}" -eq 1 ] || return 0
    case "${initial_state}" in
        RUNNING)
            if "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status >/dev/null 2>&1; then return 0; fi
            "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-start >/dev/null 2>&1 || return 1
            "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status >/dev/null 2>&1
            ;;
        STOPPED)
            if "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status >/dev/null 2>&1; then
                "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-stop >/dev/null 2>&1 || return 1
            else
                _status=$?; [ "${_status}" -eq 1 ] || return 1
            fi
            ;;
        *) return 1 ;;
    esac
}
finalize_report()
{
    [ "${finalized}" -eq 0 ] || return 0
    finalized=1
    if [ -f "${OUTPUT}" ] && [ -f "${INITIAL_EVIDENCE}" ] && [ -f "${FINAL_EVIDENCE}" ]; then
        "${PYTHON_LAUNCHER}" model-c-lifecycle-measure finalize "${OUTPUT}" "${INITIAL_EVIDENCE}" "${FINAL_EVIDENCE}" "${cleanup_ok}" >/dev/null 2>&1 || true
    fi
}
on_exit()
{
    _status=$?
    trap - EXIT HUP INT TERM
    if cleanup_all_measurement_runtime; then cleanup_ok=1; else cleanup_ok=0; fi
    restore_service || _status=70
    capture_evidence "${FINAL_EVIDENCE}" || _status=70
    finalize_report
    rm -rf "${SESSION_DIR}" 2>/dev/null || true
    exit "${_status}"
}
trap on_exit EXIT HUP INT TERM

capture_evidence "${INITIAL_EVIDENCE}" || { echo 'ERROR: Model-C lifecycle measurement could not capture initial Zapret2 evidence' >&2; exit 70; }
initial_state=$("${STRATEGY_LAB_JQ}" -r '.state' "${INITIAL_EVIDENCE}")
[ -r "${REFERENCE_STATUS}" ] || { echo 'ERROR: Model-C lifecycle measurement reference status is unavailable' >&2; exit 70; }
reference_initial=$("${STRATEGY_LAB_JQ}" -r '.restoration.initial_state // .initial_service_state // ""' "${REFERENCE_STATUS}" 2>/dev/null || true)
[ "${reference_initial}" = "${initial_state}" ] || { echo "ERROR: current Zapret2 state ${initial_state} does not match reference ${reference_initial}" >&2; exit 65; }
cleanup_all_measurement_runtime || { echo 'ERROR: stale Stage-60 runtime residue could not be cleaned' >&2; exit 70; }
case "${initial_state}" in
    RUNNING)
        "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-stop >/dev/null 2>&1 || exit 70
        service_changed=1
        ;;
    STOPPED) service_changed=1 ;;
    *) exit 70 ;;
esac

"${PYTHON_LAUNCHER}" model-c-lifecycle-measure run "${REFERENCE_JOB}" "${OUTPUT}" "${REPEATS}"
python_status=$?
if cleanup_all_measurement_runtime; then cleanup_ok=1; else cleanup_ok=0; fi
restore_service || exit 70
capture_evidence "${FINAL_EVIDENCE}" || exit 70
finalize_report
service_changed=0
if [ "${python_status}" -ne 0 ]; then exit "${python_status}"; fi
[ -r "${OUTPUT}" ] || exit 70
conclusion=$("${STRATEGY_LAB_JQ}" -r '.conclusion // ""' "${OUTPUT}")
printf 'Model-C lifecycle measurement report: %s\n' "${OUTPUT}"
printf 'Model-C lifecycle measurement conclusion: %s\n' "${conclusion}"
[ "${conclusion}" = measurement_accepted ] || exit 70
exit 0
