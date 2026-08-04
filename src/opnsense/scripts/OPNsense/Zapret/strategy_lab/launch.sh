#!/bin/sh

usage_error()
{
    echo "ERROR: $1" >&2
    echo "Usage: strategy_lab_launcher.sh {start TARGET MODE LANGUAGE|status [JOB_ID]|cancel JOB_ID|result JOB_ID}" >&2
    exit 64
}

emit_error_json()
{
    "${STRATEGY_LAB_JQ}" -nc --arg message "$1" '{status:"error",message:$message}'
}

cleanup_stale_active()
{
    _strategy_lab_active=$(strategy_lab_read_active_job 2>/dev/null || true)
    [ -n "${_strategy_lab_active}" ] || return 0
    if ! strategy_lab_job_active "${_strategy_lab_active}"; then
        strategy_lab_clear_active_job "${_strategy_lab_active}"
    fi
}

start_job()
{
    [ "$#" -eq 4 ] || usage_error "start requires TARGET MODE LANGUAGE"
    _strategy_lab_target="$2"
    _strategy_lab_mode="$3"
    _strategy_lab_language="$4"

    strategy_lab_target_safe "${_strategy_lab_target}" || usage_error "invalid target"
    strategy_lab_mode_valid "${_strategy_lab_mode}" || usage_error "invalid mode"
    strategy_lab_language_valid "${_strategy_lab_language}" || usage_error "invalid language"
    [ -x "${WORKER_SCRIPT}" ] || {
        emit_error_json "Strategy Lab worker is unavailable"
        return 1
    }
    [ -x "${TRANSACTION_SCRIPT}" ] || {
        emit_error_json "Strategy Lab lifecycle transaction is unavailable"
        return 1
    }
    [ -x "${DAEMON_BIN}" ] || {
        emit_error_json "Strategy Lab daemon launcher is unavailable"
        return 1
    }

    cleanup_stale_active
    _strategy_lab_active=$(strategy_lab_read_active_job 2>/dev/null || true)
    if [ -n "${_strategy_lab_active}" ]; then
        "${STRATEGY_LAB_JQ}" -nc --arg job_id "${_strategy_lab_active}" '{status:"busy",job_id:$job_id}'
        return 0
    fi

    _strategy_lab_jobdir=$(mktemp -d "${STRATEGY_LAB_JOBS_DIR}/job.XXXXXX") || {
        emit_error_json "Strategy Lab job directory could not be created"
        return 1
    }
    _strategy_lab_job=$(basename "${_strategy_lab_jobdir}")
    strategy_lab_job_id_valid "${_strategy_lab_job}" || {
        rm -rf "${_strategy_lab_jobdir}"
        emit_error_json "Strategy Lab job id generation failed"
        return 1
    }

    strategy_lab_initialize_state \
        "${_strategy_lab_job}" "${_strategy_lab_target}" \
        "${_strategy_lab_mode}" "${_strategy_lab_language}"
    strategy_lab_write_active_job "${_strategy_lab_job}"

    _strategy_lab_log=$(strategy_lab_log_file "${_strategy_lab_job}")
    _strategy_lab_pid=$(strategy_lab_pid_file "${_strategy_lab_job}")
    rm -f "${_strategy_lab_pid}"

    if ! "${DAEMON_BIN}" -f -o "${_strategy_lab_log}" -p "${_strategy_lab_pid}" \
        "${TRANSACTION_SCRIPT}" strategy-lab "${_strategy_lab_job}"; then
        strategy_lab_clear_active_job "${_strategy_lab_job}"
        strategy_lab_update_job "${_strategy_lab_job}" error ERROR 00 false \
            'Strategy Lab lifecycle transaction could not be started' || true
        emit_error_json "Strategy Lab lifecycle transaction could not be started"
        return 1
    fi

    "${STRATEGY_LAB_JQ}" -nc --arg job_id "${_strategy_lab_job}" \
        '{status:"ok",job_id:$job_id,state:"queued"}'
}
