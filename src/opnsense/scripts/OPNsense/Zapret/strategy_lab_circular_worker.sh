#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
umask 022
for module in common state firewall runtime candidate lifecycle circular
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 1
    . "${path}"
done
strategy_lab_require_jq
JOB_ID="${1:-}"
strategy_lab_circular_prepare_dir

if [ "${STRATEGY_LAB_LIFECYCLE_LOCK_FAILED:-0}" = 1 ]; then
    strategy_lab_circular_state_write error "${JOB_ID}" \
        'Circular validation could not acquire the Zapret2 lifecycle lock' 0 lifecycle_lock
    exit 75
fi

strategy_lab_circular_validate_job "${JOB_ID}" || {
    strategy_lab_circular_state_write error "${JOB_ID}" \
        'Completed domain Strategy Lab shortlist with 3-5 candidates is required' 0 invalid_job
    exit 64
}

printf '%s\n' "$$" > "${STRATEGY_LAB_CIRCULAR_PID}"
rm -f "${STRATEGY_LAB_CIRCULAR_STOP}"
INITIAL_STATE=''
CIRCULAR_COUNT=$("${STRATEGY_LAB_JQ}" -r '.items | length' \
    "$(strategy_lab_circular_shortlist_file "${JOB_ID}")")
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
    strategy_lab_candidate_cleanup "${JOB_ID}" || _slcw_cleanup_ok=0
    STRATEGY_LAB_INITIAL_SERVICE_STATE="${INITIAL_STATE}"
    strategy_lab_restore_initial_service_state || _slcw_cleanup_ok=0
    if [ "${_slcw_cleanup_ok}" -eq 1 ]; then
        strategy_lab_circular_state_write "${FINAL_STATE}" "${JOB_ID}" \
            "${FINAL_MESSAGE}" "${CIRCULAR_COUNT}" "${FINAL_REASON}" || true
    else
        strategy_lab_circular_state_write restore_failed "${JOB_ID}" \
            'Circular validation cleanup could not restore Zapret2 exactly' \
            "${CIRCULAR_COUNT}" RESTORE_FAILED || true
    fi
    rm -f "${STRATEGY_LAB_CIRCULAR_PID}" "${STRATEGY_LAB_CIRCULAR_STOP}"
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

strategy_lab_capture_initial_service_state || \
    circular_fail 'Zapret2 initial state is incomplete' incomplete_state
INITIAL_STATE="${STRATEGY_LAB_INITIAL_SERVICE_STATE}"
strategy_lab_circular_state_write preparing "${JOB_ID}" \
    'Stopping Zapret2 and preparing circular profile' "${CIRCULAR_COUNT}" ''
strategy_lab_stop_normal_service || \
    circular_fail 'Zapret2 could not be stopped' stop_failed
strategy_lab_candidate_cleanup "${JOB_ID}" || \
    circular_fail 'Previous temporary Strategy Lab runtime could not be cleaned' cleanup_failed
strategy_lab_circular_build_profile "${JOB_ID}" || \
    circular_fail 'Circular profile could not be built' profile_failed
CIRCULAR_RUNTIME=$(strategy_lab_candidate_runtime_dir "${JOB_ID}")
CIRCULAR_ADDRESSES=$(strategy_lab_candidate_addresses_file "${JOB_ID}")
CIRCULAR_ENDPOINTS=$(strategy_lab_circular_endpoints_file "${JOB_ID}")
CIRCULAR_WAN=$(strategy_lab_candidate_resolve_wan) || \
    circular_fail 'WAN interface could not be resolved' wan_failed
strategy_lab_candidate_resolve_addresses "${CIRCULAR_ENDPOINTS}" \
    "${CIRCULAR_ADDRESSES}" "${CIRCULAR_RUNTIME}" || \
    circular_fail 'Circular target addresses could not be resolved' resolve_failed
strategy_lab_circular_install_firewall "${CIRCULAR_ADDRESSES}" "${CIRCULAR_WAN}" || \
    circular_fail 'Circular firewall rules could not be installed' firewall_failed
strategy_lab_candidate_start "${JOB_ID}" || \
    circular_fail 'Temporary circular dvtws2 could not be started' runtime_failed
strategy_lab_circular_state_write running "${JOB_ID}" \
    'Temporary circular validation is active' "${CIRCULAR_COUNT}" ''

elapsed=0
while [ "${elapsed}" -lt "${STRATEGY_LAB_CIRCULAR_TTL}" ]
do
    if [ -e "${STRATEGY_LAB_CIRCULAR_STOP}" ]; then
        FINAL_STATE=completed
        FINAL_MESSAGE='Circular validation stopped and Zapret2 state restored'
        FINAL_REASON=requested
        exit 0
    fi
    strategy_lab_candidate_process_running "$(strategy_lab_candidate_pid_file "${JOB_ID}")" || \
        circular_fail 'Temporary circular dvtws2 stopped unexpectedly' runtime_failed
    sleep 1
    elapsed=$((elapsed + 1))
done
FINAL_STATE=completed
FINAL_MESSAGE='Circular validation time limit reached and Zapret2 state restored'
FINAL_REASON=timeout
exit 0
