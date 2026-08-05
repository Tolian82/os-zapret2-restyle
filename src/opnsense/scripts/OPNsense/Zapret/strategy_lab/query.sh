#!/bin/sh

strategy_lab_cancel_message()
{
    _strategy_lab_status="$1"
    _strategy_lab_language=$("${STRATEGY_LAB_JQ}" -r '.language // "en"' "${_strategy_lab_status}")
    case "${_strategy_lab_language}" in ru) printf '%s\n' 'Запрошена остановка' ;; *) printf '%s\n' 'Cancellation requested' ;; esac
}

strategy_lab_latest_job_scan()
{
    set -- "${STRATEGY_LAB_JOBS_DIR}"/job.*
    [ "$1" != "${STRATEGY_LAB_JOBS_DIR}/job.*" ] || return 1
    _strategy_lab_latest=$(ls -1dt "$@" 2>/dev/null | head -1)
    [ -d "${_strategy_lab_latest}" ] || return 1
    basename "${_strategy_lab_latest}"
}

strategy_lab_latest_job()
{
    _strategy_lab_latest=$(strategy_lab_read_latest_job 2>/dev/null || true)
    if [ -n "${_strategy_lab_latest}" ]; then
        printf '%s\n' "${_strategy_lab_latest}"
        return 0
    fi
    _strategy_lab_latest=$(strategy_lab_latest_job_scan 2>/dev/null || true)
    [ -n "${_strategy_lab_latest}" ] || return 1
    strategy_lab_write_latest_job "${_strategy_lab_latest}" || true
    printf '%s\n' "${_strategy_lab_latest}"
}

read_job_json()
{
    _strategy_lab_job="$1"
    strategy_lab_job_id_valid "${_strategy_lab_job}" || usage_error "invalid job id"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || { emit_error_json "Strategy Lab job not found"; return 1; }

    _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${_strategy_lab_status}" 2>/dev/null || true)
    case "${_strategy_lab_state}" in
        queued|running|cancel_requested)
            strategy_lab_reconcile_stale_job "${_strategy_lab_job}" || { emit_error_json "Strategy Lab stale job recovery failed"; return 1; }
            ;;
    esac

    if [ -e "$(strategy_lab_cancel_file "${_strategy_lab_job}")" ]; then
        _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state' "${_strategy_lab_status}")
        case "${_strategy_lab_state}" in
            queued|running|cancel_requested)
                _strategy_lab_message=$(strategy_lab_cancel_message "${_strategy_lab_status}")
                strategy_lab_request_cancel "${_strategy_lab_job}" "${_strategy_lab_message}" || { emit_error_json "Strategy Lab cancellation state could not be refreshed"; return 1; }
                ;;
        esac
    fi
    cat "${_strategy_lab_status}"
}

show_status()
{
    [ "$#" -le 2 ] || usage_error "status accepts at most one JOB_ID"
    _strategy_lab_job="${2:-}"
    [ "${_strategy_lab_job}" != "-" ] || _strategy_lab_job=""
    if [ -z "${_strategy_lab_job}" ]; then
        cleanup_stale_active || { emit_error_json "Strategy Lab stale job recovery failed"; return 1; }
        _strategy_lab_job=$(strategy_lab_read_active_job 2>/dev/null || true)
        [ -n "${_strategy_lab_job}" ] || _strategy_lab_job=$(strategy_lab_latest_job 2>/dev/null || true)
        if [ -z "${_strategy_lab_job}" ]; then "${STRATEGY_LAB_JQ}" -nc '{status:"idle"}'; return 0; fi
    fi
    read_job_json "${_strategy_lab_job}"
}

cancel_job()
{
    [ "$#" -eq 2 ] || usage_error "cancel requires JOB_ID"
    _strategy_lab_job="$2"
    strategy_lab_job_id_valid "${_strategy_lab_job}" || usage_error "invalid job id"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || { emit_error_json "Strategy Lab job not found"; return 1; }
    strategy_lab_reconcile_stale_job "${_strategy_lab_job}" || { emit_error_json "Strategy Lab stale job recovery failed"; return 1; }
    _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state' "${_strategy_lab_status}")
    case "${_strategy_lab_state}" in
        queued|running|cancel_requested)
            _strategy_lab_message=$(strategy_lab_cancel_message "${_strategy_lab_status}")
            : | strategy_lab_atomic_write "$(strategy_lab_cancel_file "${_strategy_lab_job}")" || { emit_error_json "Strategy Lab cancellation control could not be recorded"; return 1; }
            strategy_lab_request_cancel "${_strategy_lab_job}" "${_strategy_lab_message}" || { emit_error_json "Strategy Lab cancellation state could not be recorded"; return 1; }
            ;;
    esac
    read_job_json "${_strategy_lab_job}"
}

show_result()
{
    [ "$#" -eq 2 ] || usage_error "result requires JOB_ID"
    _strategy_lab_job="$2"
    strategy_lab_job_id_valid "${_strategy_lab_job}" || usage_error "invalid job id"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || { emit_error_json "Strategy Lab job not found"; return 1; }
    strategy_lab_reconcile_stale_job "${_strategy_lab_job}" || { emit_error_json "Strategy Lab stale job recovery failed"; return 1; }
    _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state' "${_strategy_lab_status}")
    case "${_strategy_lab_state}" in completed|error) cat "${_strategy_lab_status}" ;; *) "${STRATEGY_LAB_JQ}" -nc --arg job_id "${_strategy_lab_job}" --arg state "${_strategy_lab_state}" '{status:"running",job_id:$job_id,state:$state}' ;; esac
}
