#!/bin/sh

# Lifecycle-lock owner for the experiment-only controlled parallel Model-B benchmark.
# The benchmark reuses only dedicated Model-B runtime identity and restores the exact
# normal-service state after the complete corpus replay.

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
MODEL_B_ADAPTER="${STRATEGY_LAB_MODEL_B_PARALLEL_ADAPTER:-${SCRIPT_DIR}/strategy_lab_model_b_parallel_adapter.sh}"
STRATEGY_LAB_JQ="${STRATEGY_LAB_JQ:-/usr/local/bin/jq}"
STRATEGY_LAB_RUN_DIR="${STRATEGY_LAB_RUN_DIR:-/var/run/zapret2-restyle/strategy-lab}"
REFERENCE_JOB="${1:-}"
OUTPUT="${2:-}"

set -u
umask 022

case "${REFERENCE_JOB}" in job.*) ;; *) echo 'ERROR: invalid parallel Model B reference job id' >&2; exit 64 ;; esac
[ -n "${OUTPUT}" ] || { echo 'ERROR: parallel Model B output path is required' >&2; exit 64; }
[ -x "${PYTHON_LAUNCHER}" ] || { echo 'ERROR: Strategy Lab Python launcher is unavailable' >&2; exit 70; }
[ -x "${MODEL_B_ADAPTER}" ] || { echo 'ERROR: parallel Model B adapter is unavailable' >&2; exit 70; }
[ -x "${STRATEGY_LAB_JQ}" ] || { echo 'ERROR: jq is unavailable' >&2; exit 70; }
[ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] || { echo 'ERROR: parallel Model B has no lifecycle-lock owner' >&2; exit 77; }
( : >&9 ) 2>/dev/null || { echo 'ERROR: parallel Model B lifecycle lock descriptor is unavailable' >&2; exit 77; }
[ -x "${STRATEGY_LAB_SERVICE_SCRIPT:-}" ] || { echo 'ERROR: parallel Model B service control is unavailable' >&2; exit 70; }

SESSION_ROOT="${STRATEGY_LAB_RUN_DIR}/model-b-parallel"
SESSION_DIR="${SESSION_ROOT}/session.$$"
INITIAL_EVIDENCE="${SESSION_DIR}/lifecycle-initial.json"
FINAL_EVIDENCE="${SESSION_DIR}/lifecycle-final.json"
REFERENCE_STATUS="${STRATEGY_LAB_RUN_DIR}/jobs/${REFERENCE_JOB}/status.json"
STRATEGY_LAB_MODEL_B_SESSION_DIR="${SESSION_DIR}"
STRATEGY_LAB_MODEL_B_SYSTEM_ADAPTER="${MODEL_B_ADAPTER}"
export STRATEGY_LAB_MODEL_B_SESSION_DIR STRATEGY_LAB_MODEL_B_SYSTEM_ADAPTER

mkdir -p "${SESSION_DIR}/workers" || exit 70
chmod 0711 "${SESSION_ROOT}" "${SESSION_DIR}" 2>/dev/null || exit 70

initial_state=''
service_changed=0
cleanup_ok=0
finalized=0

capture_evidence()
{
    _mb_output="$1"
    "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-evidence > "${_mb_output}" 2>/dev/null || return 1
    "${STRATEGY_LAB_JQ}" -e '
      .schema==1 and .source=="zapret_service" and
      (.state=="RUNNING" or .state=="STOPPED") and
      (.effective_config_hash|type)=="string" and
      (.runtime_args_hash|type)=="string" and
      (.normal_firewall_hash|type)=="string"
    ' "${_mb_output}" >/dev/null || return 1
    chmod 0600 "${_mb_output}"
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
                _mb_status=$?
                [ "${_mb_status}" -eq 1 ] || return 1
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
        "${PYTHON_LAUNCHER}" model-b-parallel finalize "${OUTPUT}" "${INITIAL_EVIDENCE}" "${FINAL_EVIDENCE}" "${cleanup_ok}" >/dev/null 2>&1 || true
    fi
}

on_exit()
{
    _mb_status=$?
    trap - EXIT HUP INT TERM
    if "${MODEL_B_ADAPTER}" cleanup-all >/dev/null 2>&1; then cleanup_ok=1; else cleanup_ok=0; fi
    restore_service || _mb_status=70
    capture_evidence "${FINAL_EVIDENCE}" || _mb_status=70
    finalize_report
    chmod 0700 "${SESSION_ROOT}" "${SESSION_DIR}" 2>/dev/null || true
    rm -rf "${SESSION_DIR}" 2>/dev/null || true
    exit "${_mb_status}"
}
trap on_exit EXIT HUP INT TERM

capture_evidence "${INITIAL_EVIDENCE}" || { echo 'ERROR: parallel Model B could not capture initial Zapret2 evidence' >&2; exit 70; }
initial_state=$("${STRATEGY_LAB_JQ}" -r '.state' "${INITIAL_EVIDENCE}")

[ -r "${REFERENCE_STATUS}" ] || { echo 'ERROR: parallel Model B reference status is unavailable' >&2; exit 70; }
reference_initial=$("${STRATEGY_LAB_JQ}" -r '.restoration.initial_state // ""' "${REFERENCE_STATUS}" 2>/dev/null || true)
[ -n "${reference_initial}" ] || reference_initial=$("${STRATEGY_LAB_JQ}" -r '.initial_service_state // ""' "${REFERENCE_STATUS}" 2>/dev/null || true)
[ "${reference_initial}" = "${initial_state}" ] || {
    echo "ERROR: current Zapret2 state ${initial_state} does not match parallel reference ${reference_initial}" >&2
    exit 65
}

"${MODEL_B_ADAPTER}" cleanup-all >/dev/null 2>&1 || {
    echo 'ERROR: parallel Model B could not clear dedicated stale residue' >&2
    exit 70
}
"${MODEL_B_ADAPTER}" preflight >/dev/null 2>&1 || {
    echo 'ERROR: parallel Model B dedicated ports/rules are not available' >&2
    exit 70
}

case "${initial_state}" in
    RUNNING)
        "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-stop >/dev/null 2>&1 || {
            echo 'ERROR: parallel Model B could not stop normal Zapret2 service' >&2
            exit 70
        }
        service_changed=1
        if "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status >/dev/null 2>&1; then
            echo 'ERROR: normal Zapret2 service is still running' >&2
            exit 70
        else
            _mb_status=$?
            [ "${_mb_status}" -eq 1 ] || exit 70
        fi
        ;;
    STOPPED) service_changed=1 ;;
    *) exit 70 ;;
esac

"${PYTHON_LAUNCHER}" model-b-parallel run "${REFERENCE_JOB}" "${OUTPUT}"
python_status=$?

if "${MODEL_B_ADAPTER}" cleanup-all >/dev/null 2>&1; then cleanup_ok=1; else cleanup_ok=0; fi
restore_service || exit 70
capture_evidence "${FINAL_EVIDENCE}" || exit 70
finalize_report
service_changed=0

if [ "${python_status}" -ne 0 ]; then exit "${python_status}"; fi
[ -r "${OUTPUT}" ] || exit 70
conclusion=$("${STRATEGY_LAB_JQ}" -r '.conclusion // ""' "${OUTPUT}")
printf 'Model B parallel report: %s\n' "${OUTPUT}"
printf 'Model B parallel conclusion: %s\n' "${conclusion}"
exit 0
