worker_restore()
{
    strategy_lab_update_stage "${JOB_ID}" 90 RUNNING '' || true
    strategy_lab_append_event "${JOB_ID}" 90 RUNNING 'Cleaning temporary state and restoring Zapret2' || true

    if strategy_lab_restore_initial_service_state; then
        case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
            RUNNING) _strategy_lab_restore_message="${RESTORED_RUNNING_MESSAGE}" ;;
            STOPPED) _strategy_lab_restore_message="${RESTORED_STOPPED_MESSAGE}" ;;
            *) _strategy_lab_restore_message="${RESTORED_NOOP_MESSAGE}" ;;
        esac
        strategy_lab_update_stage "${JOB_ID}" 90 PASS "${_strategy_lab_restore_message}" || true
        strategy_lab_append_event "${JOB_ID}" 90 PASS "${_strategy_lab_restore_message}" || true
        return 0
    fi

    strategy_lab_update_stage "${JOB_ID}" 90 FAIL "${RESTORE_FAILED_MESSAGE}" || true
    strategy_lab_append_event "${JOB_ID}" 90 FAIL "${RESTORE_FAILED_MESSAGE}" || true
    return 1
}

worker_finish()
{
    WORKER_FINAL_OUTCOME="$1"
    WORKER_FINAL_CANCELED="$2"
    WORKER_FINALIZING=1

    if command -v worker_watchdog_stop >/dev/null 2>&1; then
        worker_watchdog_stop
    fi

    if ! worker_restore; then
        WORKER_FINAL_OUTCOME='RESTORE_FAILED'
    fi

    WORKER_FINAL_STATE=$(worker_result_terminal_state "${WORKER_FINAL_OUTCOME}")
    WORKER_FINAL_REPORT_STATUS=$(worker_result_report_status "${WORKER_FINAL_OUTCOME}")
    WORKER_FINAL_MESSAGE=$(worker_result_message "${WORKER_FINAL_OUTCOME}" "${WORKER_FINAL_CANCELED}")

    strategy_lab_update_stage "${JOB_ID}" 99 "${WORKER_FINAL_REPORT_STATUS}" \
        "${WORKER_FINAL_MESSAGE}" || true
    strategy_lab_append_event "${JOB_ID}" 99 "${WORKER_FINAL_REPORT_STATUS}" \
        "${WORKER_FINAL_MESSAGE}" || true

    strategy_lab_update_job "${JOB_ID}" "${WORKER_FINAL_STATE}" \
        "${WORKER_FINAL_OUTCOME}" 99 "${WORKER_FINAL_CANCELED}" \
        "${WORKER_FINAL_MESSAGE}" || true
    worker_result_set_circular_eligibility || true
    strategy_lab_clear_active_job "${JOB_ID}"
    exit 0
}

worker_cancel()
{
    [ "${WORKER_FINALIZING}" -eq 0 ] || exit 0
    worker_skip_unfinished "${JOB_ID}" "${CANCEL_MESSAGE}" || true
    worker_finish PARTIAL true
}

worker_error()
{
    _strategy_lab_stage="$1"
    _strategy_lab_message="$2"
    strategy_lab_update_stage "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    strategy_lab_append_event "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    worker_skip_unfinished "${JOB_ID}" "${ERROR_SKIP_MESSAGE}" || true
    worker_finish ERROR false
}

worker_prerequisite_failed()
{
    _strategy_lab_stage="$1"
    _strategy_lab_message="$2"
    strategy_lab_update_stage "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    strategy_lab_append_event "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    worker_skip_unfinished "${JOB_ID}" "${PREREQUISITE_MESSAGE}" || true
    worker_finish PARTIAL false
}

worker_stage_timeout()
{
    _strategy_lab_stage="$1"
    strategy_lab_update_stage "${JOB_ID}" "${_strategy_lab_stage}" TIMEOUT "${STAGE_TIMEOUT_MESSAGE}" || true
    strategy_lab_append_event "${JOB_ID}" "${_strategy_lab_stage}" TIMEOUT "${STAGE_TIMEOUT_MESSAGE}" || true
    worker_skip_unfinished "${JOB_ID}" "${TIMEOUT_SKIP_MESSAGE}" || true
    worker_finish TIMEOUT false
}

trap worker_cancel HUP INT TERM
