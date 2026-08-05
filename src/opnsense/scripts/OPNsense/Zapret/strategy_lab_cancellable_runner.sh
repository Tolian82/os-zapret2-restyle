#!/bin/sh

set -u

CANCEL_EXIT_STATUS="${STRATEGY_LAB_CANCEL_EXIT_STATUS:-125}"
CANCEL_POLL_SECONDS="${STRATEGY_LAB_CANCEL_POLL_SECONDS:-1}"
CANCEL_GRACE_SECONDS="${STRATEGY_LAB_CANCEL_GRACE_SECONDS:-2}"
PGREP_BIN="${STRATEGY_LAB_PGREP_BIN:-/usr/bin/pgrep}"

runner="${1:-}"
[ -n "${runner}" ] || exit 64
shift
[ -x "${runner}" ] || exit 69

case "${CANCEL_GRACE_SECONDS}" in
    ''|*[!0-9]*) exit 64 ;;
esac
[ -x "${PGREP_BIN}" ] || exit 69

collect_descendants()
{
    _slcr_parent="$1"
    _slcr_children=$("${PGREP_BIN}" -P "${_slcr_parent}" 2>/dev/null || true)
    for _slcr_child in ${_slcr_children}
    do
        collect_descendants "${_slcr_child}"
        printf '%s\n' "${_slcr_child}"
    done
}

pid_alive()
{
    kill -0 "$1" 2>/dev/null
}

signal_pid()
{
    _slcr_signal="$1"
    _slcr_pid="$2"
    case "${_slcr_signal}" in
        TERM) kill -TERM "${_slcr_pid}" 2>/dev/null || true ;;
        KILL) kill -KILL "${_slcr_pid}" 2>/dev/null || true ;;
        *) return 64 ;;
    esac
}

any_alive()
{
    for _slcr_pid in $1
    do
        pid_alive "${_slcr_pid}" && return 0
    done
    return 1
}

terminate_tree()
{
    _slcr_root="$1"
    _slcr_descendants=$(collect_descendants "${_slcr_root}")
    _slcr_pids="${_slcr_root} ${_slcr_descendants}"

    signal_pid TERM "${_slcr_root}"
    for _slcr_pid in ${_slcr_descendants}
    do
        signal_pid TERM "${_slcr_pid}"
    done

    _slcr_elapsed=0
    while any_alive "${_slcr_pids}" && [ "${_slcr_elapsed}" -lt "${CANCEL_GRACE_SECONDS}" ]
    do
        sleep 1
        _slcr_elapsed=$((_slcr_elapsed + 1))
    done

    if any_alive "${_slcr_pids}"; then
        for _slcr_pid in ${_slcr_pids}
        do
            signal_pid KILL "${_slcr_pid}"
        done
    fi

    if wait "${_slcr_root}" 2>/dev/null; then
        :
    else
        :
    fi
}

request_worker_cancel()
{
    _slcr_worker="${STRATEGY_LAB_WORKER_PID:-}"
    case "${_slcr_worker}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    pid_alive "${_slcr_worker}" || return 1
    kill -TERM "${_slcr_worker}" 2>/dev/null
}

cancel_requested()
{
    [ -n "${CANCEL_FILE:-}" ] && [ -e "${CANCEL_FILE}" ]
}

if cancel_requested; then
    request_worker_cancel || true
    exit "${CANCEL_EXIT_STATUS}"
fi

"${runner}" "$@" &
runner_pid=$!

while pid_alive "${runner_pid}"
do
    if cancel_requested; then
        terminate_tree "${runner_pid}"
        request_worker_cancel || true
        exit "${CANCEL_EXIT_STATUS}"
    fi
    sleep "${CANCEL_POLL_SECONDS}"
done

if wait "${runner_pid}"; then
    runner_status=0
else
    runner_status=$?
fi

if cancel_requested; then
    request_worker_cancel || true
    exit "${CANCEL_EXIT_STATUS}"
fi

exit "${runner_status}"
