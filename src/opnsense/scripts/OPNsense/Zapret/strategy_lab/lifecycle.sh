#!/bin/sh

STRATEGY_LAB_SERVICE_SCRIPT="${STRATEGY_LAB_SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}"
STRATEGY_LAB_TIMEOUT_BIN="${STRATEGY_LAB_TIMEOUT_BIN:-/usr/bin/timeout}"
STRATEGY_LAB_STOP_TIMEOUT="${STRATEGY_LAB_STOP_TIMEOUT:-10}"
STRATEGY_LAB_RESTORE_TIMEOUT="${STRATEGY_LAB_RESTORE_TIMEOUT:-15}"
STRATEGY_LAB_INITIAL_SERVICE_STATE=""

strategy_lab_service_status_code()
{
    if "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status >/dev/null 2>&1; then
        return 0
    else
        _strategy_lab_service_status=$?
    fi
    return "${_strategy_lab_service_status}"
}

strategy_lab_capture_initial_service_state()
{
    if strategy_lab_service_status_code; then
        STRATEGY_LAB_INITIAL_SERVICE_STATE="RUNNING"
        return 0
    else
        _strategy_lab_state_status=$?
    fi

    case "${_strategy_lab_state_status}" in
        1)
            STRATEGY_LAB_INITIAL_SERVICE_STATE="STOPPED"
            return 0
            ;;
        *)
            STRATEGY_LAB_INITIAL_SERVICE_STATE="INCOMPLETE"
            return 1
            ;;
    esac
}

strategy_lab_timed_service_action()
{
    _strategy_lab_action="$1"
    _strategy_lab_timeout="$2"

    [ -x "${STRATEGY_LAB_TIMEOUT_BIN}" ] || {
        echo "ERROR: Strategy Lab timeout utility is unavailable" >&2
        return 1
    }
    [ -x "${STRATEGY_LAB_SERVICE_SCRIPT}" ] || {
        echo "ERROR: Strategy Lab service control is unavailable" >&2
        return 1
    }

    "${STRATEGY_LAB_TIMEOUT_BIN}" "${_strategy_lab_timeout}" \
        "${STRATEGY_LAB_SERVICE_SCRIPT}" "strategy-lab-${_strategy_lab_action}"
}

strategy_lab_verify_stopped()
{
    if strategy_lab_service_status_code; then
        return 1
    else
        _strategy_lab_verify_status=$?
    fi
    [ "${_strategy_lab_verify_status}" -eq 1 ]
}

strategy_lab_verify_running()
{
    strategy_lab_service_status_code
}

strategy_lab_stop_normal_service()
{
    case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
        RUNNING)
            strategy_lab_timed_service_action stop "${STRATEGY_LAB_STOP_TIMEOUT}" || return 1
            strategy_lab_verify_stopped
            ;;
        STOPPED)
            strategy_lab_verify_stopped
            ;;
        *)
            return 1
            ;;
    esac
}

strategy_lab_cleanup_temporary_runtime()
{
    # Patch 3 has no temporary candidate runtime yet. The permanent cleanup hook is
    # present now so every later exit path already converges on stage 90.
    return 0
}

strategy_lab_restore_running_state()
{
    if strategy_lab_service_status_code; then
        return 0
    else
        _strategy_lab_current_status=$?
    fi

    case "${_strategy_lab_current_status}" in
        1)
            ;;
        2)
            strategy_lab_timed_service_action stop "${STRATEGY_LAB_STOP_TIMEOUT}" || return 1
            strategy_lab_verify_stopped || return 1
            ;;
        *)
            return 1
            ;;
    esac

    strategy_lab_timed_service_action start "${STRATEGY_LAB_RESTORE_TIMEOUT}" || return 1
    strategy_lab_verify_running
}

strategy_lab_restore_stopped_state()
{
    if strategy_lab_service_status_code; then
        _strategy_lab_current_status=0
    else
        _strategy_lab_current_status=$?
    fi

    case "${_strategy_lab_current_status}" in
        1)
            return 0
            ;;
        0|2)
            strategy_lab_timed_service_action stop "${STRATEGY_LAB_STOP_TIMEOUT}" || return 1
            strategy_lab_verify_stopped
            ;;
        *)
            return 1
            ;;
    esac
}

strategy_lab_restore_initial_service_state()
{
    strategy_lab_cleanup_temporary_runtime || return 1

    case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
        RUNNING)
            strategy_lab_restore_running_state
            ;;
        STOPPED)
            strategy_lab_restore_stopped_state
            ;;
        '')
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}
