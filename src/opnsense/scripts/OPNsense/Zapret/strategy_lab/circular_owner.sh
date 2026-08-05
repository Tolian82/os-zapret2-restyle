#!/bin/sh

STRATEGY_LAB_PS_BIN="${STRATEGY_LAB_PS_BIN:-/bin/ps}"
STRATEGY_LAB_CIRCULAR_OWNER_WAIT="${STRATEGY_LAB_CIRCULAR_OWNER_WAIT:-3}"

strategy_lab_circular_session_owner_file()
{
    printf '%s/owner.json\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_owner_process_token()
{
    _slco_pid="$1"
    "${STRATEGY_LAB_PS_BIN}" -p "${_slco_pid}" -o lstart= 2>/dev/null |
        awk '{$1=$1; print}'
}

strategy_lab_circular_owner_process_command()
{
    _slco_pid="$1"
    "${STRATEGY_LAB_PS_BIN}" -p "${_slco_pid}" -o command= 2>/dev/null |
        awk '{$1=$1; print}'
}

strategy_lab_circular_owner_write()
{
    _slco_session="$1"
    _slco_parent="$2"
    _slco_pid="$3"
    strategy_lab_circular_session_id_valid "${_slco_session}" || return 1
    strategy_lab_job_id_valid "${_slco_parent}" || return 1
    case "${_slco_pid}" in ''|*[!0-9]*) return 1 ;; esac
    kill -0 "${_slco_pid}" 2>/dev/null || return 1
    _slco_token=$(strategy_lab_circular_owner_process_token "${_slco_pid}")
    [ -n "${_slco_token}" ] || return 1
    _slco_command=$(strategy_lab_circular_owner_process_command "${_slco_pid}" || true)
    _slco_owner=$(strategy_lab_circular_session_owner_file "${_slco_session}")
    _slco_tmp=$(mktemp "$(dirname "${_slco_owner}")/.owner.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" -nc \
        --arg session_id "${_slco_session}" \
        --arg parent_job_id "${_slco_parent}" \
        --argjson pid "${_slco_pid}" \
        --arg process_token "${_slco_token}" \
        --arg command "${_slco_command}" \
        --argjson recorded_at "$(date +%s)" '
        {session_id:$session_id,parent_job_id:$parent_job_id,pid:$pid,
         process_token:$process_token,command:$command,recorded_at:$recorded_at}
    ' > "${_slco_tmp}" || {
        rm -f "${_slco_tmp}"
        return 1
    }
    chmod 0600 "${_slco_tmp}"
    mv -f "${_slco_tmp}" "${_slco_owner}"
}

strategy_lab_circular_owner_write_from_pid_file()
{
    _slco_session="$1"
    _slco_parent="$2"
    _slco_pid_file=$(strategy_lab_circular_session_pid_file "${_slco_session}") || return 1
    _slco_waited=0
    while [ "${_slco_waited}" -le "${STRATEGY_LAB_CIRCULAR_OWNER_WAIT}" ]
    do
        if [ -r "${_slco_pid_file}" ]; then
            IFS= read -r _slco_pid < "${_slco_pid_file}" || _slco_pid=''
            if strategy_lab_circular_owner_write "${_slco_session}" \
                "${_slco_parent}" "${_slco_pid}"; then
                return 0
            fi
        fi
        [ "${_slco_waited}" -lt "${STRATEGY_LAB_CIRCULAR_OWNER_WAIT}" ] || break
        sleep 1
        _slco_waited=$((_slco_waited + 1))
    done
    return 1
}

strategy_lab_circular_owner_valid()
{
    _slco_session="$1"
    _slco_owner=$(strategy_lab_circular_session_owner_file "${_slco_session}") || return 1
    [ -r "${_slco_owner}" ] || return 1
    _slco_recorded_session=$("${STRATEGY_LAB_JQ}" -r '.session_id // ""' "${_slco_owner}")
    [ "${_slco_recorded_session}" = "${_slco_session}" ] || return 1
    _slco_pid=$("${STRATEGY_LAB_JQ}" -r '.pid // ""' "${_slco_owner}")
    _slco_expected=$("${STRATEGY_LAB_JQ}" -r '.process_token // ""' "${_slco_owner}")
    case "${_slco_pid}" in ''|*[!0-9]*) return 1 ;; esac
    [ -n "${_slco_expected}" ] || return 1
    kill -0 "${_slco_pid}" 2>/dev/null || return 1
    _slco_actual=$(strategy_lab_circular_owner_process_token "${_slco_pid}")
    [ -n "${_slco_actual}" ] && [ "${_slco_actual}" = "${_slco_expected}" ]
}

strategy_lab_circular_owner_clear()
{
    rm -f "$(strategy_lab_circular_session_owner_file "$1")"
}

strategy_lab_circular_recovery_state_file()
{
    strategy_lab_circular_session_state_file "$1"
}

strategy_lab_circular_recover_stale_session()
(
    _slco_session="$1"
    strategy_lab_circular_session_id_valid "${_slco_session}" || exit 64
    _slco_state=$(strategy_lab_circular_recovery_state_file "${_slco_session}") || exit 1
    [ -r "${_slco_state}" ] || exit 1
    strategy_lab_circular_owner_valid "${_slco_session}" && exit 75

    _slco_parent=$(strategy_lab_circular_session_parent_read "${_slco_session}" 2>/dev/null || true)
    _slco_count=$("${STRATEGY_LAB_JQ}" -r '.candidate_count // 0' "${_slco_state}")
    _slco_lifecycle_state=$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${_slco_state}")
    _slco_snapshot="$(strategy_lab_circular_session_dir "${_slco_session}")/lifecycle-snapshot.json"

    STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}"
    export STRATEGY_LAB_JOBS_DIR
    JOB_ID="${_slco_session}"
    JOB_DIR=$(strategy_lab_circular_session_dir "${_slco_session}")
    export JOB_ID JOB_DIR
    strategy_lab_status_file()
    {
        strategy_lab_circular_session_state_file "$1"
    }

    if [ ! -r "${_slco_snapshot}" ]; then
        if [ "${_slco_lifecycle_state}" = queued ] &&
            strategy_lab_candidate_cleanup "${_slco_session}" &&
            strategy_lab_firewall_remove_rules &&
            strategy_lab_firewall_range_empty; then
            strategy_lab_circular_state_write "${_slco_session}" error "${_slco_parent}" \
                'Circular owner disappeared before runtime mutation; temporary residue was cleaned' \
                "${_slco_count}" stale_before_mutation
            strategy_lab_circular_owner_clear "${_slco_session}"
            rm -f "$(strategy_lab_circular_session_pid_file "${_slco_session}")" \
                "$(strategy_lab_circular_session_stop_file "${_slco_session}")"
            strategy_lab_circular_active_session_clear "${_slco_session}"
            exit 0
        fi
        strategy_lab_circular_state_write "${_slco_session}" restore_failed "${_slco_parent}" \
            'Circular owner disappeared without a usable lifecycle snapshot; automatic retry is blocked' \
            "${_slco_count}" RESTORE_FAILED
        exit 1
    fi

    STRATEGY_LAB_INITIAL_SERVICE_STATE=$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${_slco_snapshot}")
    STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE=$("${STRATEGY_LAB_JQ}" -r '.source // ""' "${_slco_snapshot}")
    export STRATEGY_LAB_INITIAL_SERVICE_STATE STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE

    if strategy_lab_candidate_cleanup "${_slco_session}" &&
       strategy_lab_firewall_remove_rules &&
       strategy_lab_firewall_range_empty &&
       strategy_lab_restore_initial_service_state; then
        strategy_lab_circular_state_write "${_slco_session}" error "${_slco_parent}" \
            'Circular owner disappeared; temporary state was cleaned and Zapret2 was restored' \
            "${_slco_count}" stale_worker_restored
        strategy_lab_circular_owner_clear "${_slco_session}"
        rm -f "$(strategy_lab_circular_session_pid_file "${_slco_session}")" \
            "$(strategy_lab_circular_session_stop_file "${_slco_session}")"
        strategy_lab_circular_active_session_clear "${_slco_session}"
        exit 0
    fi

    strategy_lab_circular_state_write "${_slco_session}" restore_failed "${_slco_parent}" \
        'Circular owner disappeared and semantic Zapret2 restoration could not be proven; automatic retry is blocked' \
        "${_slco_count}" RESTORE_FAILED
    exit 1
)
