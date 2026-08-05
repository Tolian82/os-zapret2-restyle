#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
umask 022

for module in common state firewall runtime candidate lifecycle circular circular_owner
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 1
    . "${path}"
done

strategy_lab_require_jq
strategy_lab_circular_prepare_dir

PARENT_JOB_ID="${1:-}"
strategy_lab_job_id_valid "${PARENT_JOB_ID}" || exit 64
SESSION_ID=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
[ -n "${SESSION_ID}" ] || exit 64
strategy_lab_circular_session_validate "${SESSION_ID}" "${PARENT_JOB_ID}" || exit 64

CIRCULAR_STATE=$(strategy_lab_circular_session_state_file "${SESSION_ID}")
CIRCULAR_PID=$(strategy_lab_circular_session_pid_file "${SESSION_ID}")
CIRCULAR_STOP=$(strategy_lab_circular_session_stop_file "${SESSION_ID}")
CIRCULAR_COUNT=$(strategy_lab_circular_candidate_count \
    "$(strategy_lab_circular_session_shortlist_file "${SESSION_ID}")")

if [ "${STRATEGY_LAB_LIFECYCLE_LOCK_FAILED:-0}" = 1 ]; then
    strategy_lab_circular_state_write "${SESSION_ID}" error "${PARENT_JOB_ID}" \
        'Circular validation could not acquire the Zapret2 lifecycle lock' \
        "${CIRCULAR_COUNT}" lifecycle_lock
    strategy_lab_circular_owner_clear "${SESSION_ID}"
    strategy_lab_circular_active_session_clear "${SESSION_ID}"
    exit 75
fi

# All generic Strategy Lab runtime and lifecycle helpers resolve below the
# private circular-session root. The completed parent job is never mutated.
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}"
export STRATEGY_LAB_JOBS_DIR
JOB_ID="${SESSION_ID}"
JOB_DIR=$(strategy_lab_circular_session_dir "${SESSION_ID}")
export JOB_ID JOB_DIR
strategy_lab_status_file()
{
    strategy_lab_circular_session_state_file "$1"
}

printf '%s\n' "$$" > "${CIRCULAR_PID}"
chmod 0600 "${CIRCULAR_PID}"
rm -f "${CIRCULAR_STOP}"
INITIAL_STATE=''
FINAL_STATE=completed
FINAL_MESSAGE='Circular validation stopped and Zapret2 state restored'
FINAL_REASON=exit
CIRCULAR_FINALIZING=0

circular_fail()
{
    FINAL_STATE=error
    FINAL_MESSAGE="$1"
    FINAL_REASON="$2"
    exit 1
}

circular_cleanup()
{
    [ "${CIRCULAR_FINALIZING}" -eq 0 ] || return 0
    CIRCULAR_FINALIZING=1
    _slcw_cleanup_ok=1
    strategy_lab_candidate_cleanup "${SESSION_ID}" || _slcw_cleanup_ok=0
    STRATEGY_LAB_INITIAL_SERVICE_STATE="${INITIAL_STATE}"
    strategy_lab_restore_initial_service_state || _slcw_cleanup_ok=0
    if [ "${_slcw_cleanup_ok}" -eq 1 ]; then
        strategy_lab_circular_state_write "${SESSION_ID}" "${FINAL_STATE}" \
            "${PARENT_JOB_ID}" "${FINAL_MESSAGE}" "${CIRCULAR_COUNT}" "${FINAL_REASON}" || true
        strategy_lab_circular_owner_clear "${SESSION_ID}"
        rm -f "${CIRCULAR_PID}" "${CIRCULAR_STOP}"
        strategy_lab_circular_active_session_clear "${SESSION_ID}"
    else
        strategy_lab_circular_state_write "${SESSION_ID}" restore_failed \
            "${PARENT_JOB_ID}" \
            'Circular validation cleanup could not restore Zapret2 exactly; automatic retry is blocked' \
            "${CIRCULAR_COUNT}" RESTORE_FAILED || true
        rm -f "${CIRCULAR_PID}" "${CIRCULAR_STOP}"
    fi
}

circular_signal()
{
    FINAL_STATE=completed
    FINAL_MESSAGE='Circular validation interrupted and Zapret2 state restored'
    FINAL_REASON=signal
    exit 0
}

trap circular_signal HUP INT TERM
trap circular_cleanup EXIT

strategy_lab_circular_owner_write "${SESSION_ID}" "${PARENT_JOB_ID}" "$$" ||
    circular_fail 'Circular validation owner identity could not be refreshed' owner_unavailable
strategy_lab_capture_initial_service_state ||
    circular_fail 'Zapret2 initial state is incomplete' incomplete_state
INITIAL_STATE="${STRATEGY_LAB_INITIAL_SERVICE_STATE}"
strategy_lab_circular_state_write "${SESSION_ID}" preparing "${PARENT_JOB_ID}" \
    'Stopping Zapret2 and preparing circular profile' "${CIRCULAR_COUNT}" ''
strategy_lab_stop_normal_service ||
    circular_fail 'Zapret2 could not be stopped' stop_failed
strategy_lab_candidate_cleanup "${SESSION_ID}" ||
    circular_fail 'Previous temporary Strategy Lab runtime could not be cleaned' cleanup_failed
strategy_lab_circular_build_profile "${SESSION_ID}" ||
    circular_fail 'Circular profile could not be built' profile_failed
CIRCULAR_RUNTIME=$(strategy_lab_candidate_runtime_dir "${SESSION_ID}")
CIRCULAR_ADDRESSES=$(strategy_lab_candidate_addresses_file "${SESSION_ID}")
CIRCULAR_ENDPOINTS=$(strategy_lab_circular_session_endpoints_file "${SESSION_ID}")
CIRCULAR_WAN=$(strategy_lab_candidate_resolve_wan) ||
    circular_fail 'WAN interface could not be resolved' wan_failed
strategy_lab_candidate_resolve_addresses \
    "${CIRCULAR_ENDPOINTS}" "${CIRCULAR_ADDRESSES}" "${CIRCULAR_RUNTIME}" ||
    circular_fail 'Circular target addresses could not be resolved' resolve_failed
strategy_lab_circular_install_firewall "${CIRCULAR_ADDRESSES}" "${CIRCULAR_WAN}" ||
    circular_fail 'Circular firewall rules could not be installed' firewall_failed
strategy_lab_candidate_start "${SESSION_ID}" ||
    circular_fail 'Temporary circular dvtws2 could not be started' runtime_failed
strategy_lab_circular_state_write "${SESSION_ID}" running "${PARENT_JOB_ID}" \
    'Temporary circular validation is active' "${CIRCULAR_COUNT}" ''

elapsed=0
while [ "${elapsed}" -lt "${STRATEGY_LAB_CIRCULAR_TTL}" ]
do
    if [ -e "${CIRCULAR_STOP}" ]; then
        FINAL_STATE=completed
        FINAL_MESSAGE='Circular validation stopped and Zapret2 state restored'
        FINAL_REASON=requested
        exit 0
    fi
    strategy_lab_candidate_process_running \
        "$(strategy_lab_candidate_pid_file "${SESSION_ID}")" ||
        circular_fail 'Temporary circular dvtws2 stopped unexpectedly' runtime_failed
    sleep 1
    elapsed=$((elapsed + 1))
done

FINAL_STATE=completed
FINAL_MESSAGE='Circular validation time limit reached and Zapret2 state restored'
FINAL_REASON=timeout
exit 0
