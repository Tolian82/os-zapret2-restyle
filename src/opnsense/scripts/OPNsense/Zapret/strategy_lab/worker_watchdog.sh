#!/bin/sh

WORKER_WATCHDOG_PID=''

worker_watchdog_budget()
{
    case "${MODE}" in
        extended)
            printf '%s\n' $((STRATEGY_LAB_STANDARD_BUDGET + STRATEGY_LAB_EXTENDED_BUDGET))
            ;;
        *)
            printf '%s\n' "${STRATEGY_LAB_STANDARD_BUDGET}"
            ;;
    esac
}

worker_watchdog_stop()
{
    case "${WORKER_WATCHDOG_PID:-}" in
        ''|*[!0-9]*) return 0 ;;
    esac
    kill "${WORKER_WATCHDOG_PID}" 2>/dev/null || true
    wait "${WORKER_WATCHDOG_PID}" 2>/dev/null || true
    WORKER_WATCHDOG_PID=''
}

worker_hard_timeout()
{
    [ "${WORKER_FINALIZING:-0}" -eq 0 ] || return 0
    worker_watchdog_stop
    if [ -n "${CANCEL_FILE:-}" ]; then
        : > "${CANCEL_FILE}" || true
    fi
    _slwd_stage=$("${STRATEGY_LAB_JQ}" -r '.current_stage // "00"' \
        "${STATUS_FILE}" 2>/dev/null || printf '%s\n' 00)
    worker_stage_timeout "${_slwd_stage}"
}

worker_watchdog_start()
{
    _slwd_budget=$(worker_watchdog_budget) || return 1
    case "${_slwd_budget}" in
        ''|*[!0-9]*|0) return 1 ;;
    esac
    _slwd_parent=$$
    (
        _slwd_elapsed=0
        while [ "${_slwd_elapsed}" -lt "${_slwd_budget}" ]
        do
            kill -0 "${_slwd_parent}" 2>/dev/null || exit 0
            sleep 1
            _slwd_elapsed=$((_slwd_elapsed + 1))
        done
        kill -ALRM "${_slwd_parent}" 2>/dev/null || true
    ) &
    WORKER_WATCHDOG_PID=$!
    export WORKER_WATCHDOG_PID
}

trap worker_watchdog_stop EXIT
trap worker_hard_timeout ALRM
worker_watchdog_start || worker_error 00 \
    'Strategy Lab hard watchdog could not be started.'
