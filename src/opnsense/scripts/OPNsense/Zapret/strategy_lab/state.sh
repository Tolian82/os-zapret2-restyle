#!/bin/sh

STRATEGY_LAB_STATE_LOCK_TIMEOUT="${STRATEGY_LAB_STATE_LOCK_TIMEOUT:-10}"
if [ -z "${STRATEGY_LAB_PYTHON_LAUNCHER:-}" ]; then
    if [ -n "${SCRIPT_DIR:-}" ]; then
        STRATEGY_LAB_PYTHON_LAUNCHER="${SCRIPT_DIR}/strategy_lab_python_launcher.sh"
    elif [ -n "${MODULE_DIR:-}" ]; then
        STRATEGY_LAB_PYTHON_LAUNCHER="${MODULE_DIR%/strategy_lab}/strategy_lab_python_launcher.sh"
    else
        STRATEGY_LAB_PYTHON_LAUNCHER="/usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_python_launcher.sh"
    fi
fi

strategy_lab_state_python()
{
    [ -x "${STRATEGY_LAB_PYTHON_LAUNCHER}" ] || {
        echo "ERROR: Strategy Lab Python state launcher is unavailable: ${STRATEGY_LAB_PYTHON_LAUNCHER}" >&2
        return 70
    }

    STRATEGY_LAB_STATE_LOCK_TIMEOUT="${STRATEGY_LAB_STATE_LOCK_TIMEOUT}" \
    STRATEGY_LAB_PYTHON_BIN="${STRATEGY_LAB_PYTHON_BIN:-/usr/local/bin/python3}" \
        "${STRATEGY_LAB_PYTHON_LAUNCHER}" state "$@"
}

strategy_lab_initialize_state()
{
    _strategy_lab_job="$1"
    _strategy_lab_target="$2"
    _strategy_lab_mode="$3"
    _strategy_lab_language="$4"
    _strategy_lab_jobdir=$(strategy_lab_job_dir "${_strategy_lab_job}")
    mkdir -p "${_strategy_lab_jobdir}" || return 1

    strategy_lab_state_python initialize \
        "${_strategy_lab_job}" \
        "$(strategy_lab_status_file "${_strategy_lab_job}")" \
        "$(strategy_lab_event_file "${_strategy_lab_job}")" \
        "${_strategy_lab_target}" \
        "${_strategy_lab_mode}" \
        "${_strategy_lab_language}"
}

strategy_lab_set_target_contract()
{
    strategy_lab_state_python set-target \
        "$1" "$(strategy_lab_status_file "$1")" "$2" "$3" "$4"
}

strategy_lab_set_json_field()
{
    strategy_lab_state_python set-json-field \
        "$1" "$(strategy_lab_status_file "$1")" "$2" "$3"
}

strategy_lab_set_network_capabilities()
{
    strategy_lab_set_json_field "$1" network "$2"
}

strategy_lab_set_baseline_result()
{
    strategy_lab_set_json_field "$1" baseline "$2"
}

strategy_lab_set_candidate_smoke_result()
{
    strategy_lab_state_python set-candidate \
        "$1" "$(strategy_lab_status_file "$1")" "$2"
}

strategy_lab_request_cancel()
{
    strategy_lab_state_python request-cancel \
        "$1" "$(strategy_lab_status_file "$1")" "$2"
}

strategy_lab_update_job()
{
    strategy_lab_state_python update-job \
        "$1" "$(strategy_lab_status_file "$1")" \
        "$2" "$3" "$4" "$5" "$6"
}

strategy_lab_set_initial_service_state()
{
    strategy_lab_state_python set-initial-service-state \
        "$1" "$(strategy_lab_status_file "$1")" "$2"
}

strategy_lab_update_stage()
{
    strategy_lab_state_python update-stage \
        "$1" "$(strategy_lab_status_file "$1")" "$2" "$3" "$4"
}

strategy_lab_append_event()
{
    strategy_lab_state_python append-event \
        "$1" "$(strategy_lab_status_file "$1")" \
        "$(strategy_lab_event_file "$1")" "$2" "$3" "$4"
}

strategy_lab_skip_unfinished()
{
    strategy_lab_state_python skip-unfinished \
        "$1" "$(strategy_lab_status_file "$1")" "$2"
}

strategy_lab_set_circular_eligibility()
{
    strategy_lab_state_python set-circular-eligibility \
        "$1" "$(strategy_lab_status_file "$1")" "$2" "$3" "$4"
}

strategy_lab_finalize_stale_recovery()
{
    strategy_lab_state_python finalize-stale-recovery \
        "$1" "$(strategy_lab_status_file "$1")" "$2" "$3" "$4" "$5"
}
