#!/bin/sh

read_job_json()
{
    _strategy_lab_job="$1"
    strategy_lab_job_id_valid "${_strategy_lab_job}" || usage_error "invalid job id"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || {
        emit_error_json "Strategy Lab job not found"
        return 1
    }
    cat "${_strategy_lab_status}"
}

show_status()
{
    [ "$#" -le 2 ] || usage_error "status accepts at most one JOB_ID"
    _strategy_lab_job="${2:-}"
    [ "${_strategy_lab_job}" != "-" ] || _strategy_lab_job=""
    if [ -z "${_strategy_lab_job}" ]; then
        cleanup_stale_active
        _strategy_lab_job=$(strategy_lab_read_active_job 2>/dev/null || true)
        if [ -z "${_strategy_lab_job}" ]; then
            "${STRATEGY_LAB_JQ}" -nc '{status:"idle"}'
            return 0
        fi
    fi
    read_job_json "${_strategy_lab_job}"
}

cancel_job()
{
    [ "$#" -eq 2 ] || usage_error "cancel requires JOB_ID"
    _strategy_lab_job="$2"
    strategy_lab_job_id_valid "${_strategy_lab_job}" || usage_error "invalid job id"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || {
        emit_error_json "Strategy Lab job not found"
        return 1
    }

    _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state' "${_strategy_lab_status}")
    case "${_strategy_lab_state}" in
        queued|running|cancel_requested)
            _strategy_lab_language=$("${STRATEGY_LAB_JQ}" -r '.language // "en"' "${_strategy_lab_status}")
            case "${_strategy_lab_language}" in
                ru) _strategy_lab_cancel_message='Запрошена остановка' ;;
                *) _strategy_lab_cancel_message='Cancellation requested' ;;
            esac
            : | strategy_lab_atomic_write "$(strategy_lab_cancel_file "${_strategy_lab_job}")" || {
                emit_error_json "Strategy Lab cancellation control could not be recorded"
                return 1
            }
            strategy_lab_request_cancel "${_strategy_lab_job}" "${_strategy_lab_cancel_message}" || {
                emit_error_json "Strategy Lab cancellation state could not be recorded"
                return 1
            }
            read_job_json "${_strategy_lab_job}"
            ;;
        *)
            read_job_json "${_strategy_lab_job}"
            ;;
    esac
}

show_result()
{
    [ "$#" -eq 2 ] || usage_error "result requires JOB_ID"
    _strategy_lab_job="$2"
    strategy_lab_job_id_valid "${_strategy_lab_job}" || usage_error "invalid job id"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || {
        emit_error_json "Strategy Lab job not found"
        return 1
    }
    _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state' "${_strategy_lab_status}")
    case "${_strategy_lab_state}" in
        completed|error)
            cat "${_strategy_lab_status}"
            ;;
        *)
            "${STRATEGY_LAB_JQ}" -nc --arg job_id "${_strategy_lab_job}" \
                --arg state "${_strategy_lab_state}" \
                '{status:"running",job_id:$job_id,state:$state}'
            ;;
    esac
}
