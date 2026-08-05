#!/bin/sh

STRATEGY_LAB_JQ="${STRATEGY_LAB_JQ:-/usr/local/bin/jq}"
STRATEGY_LAB_RUN_DIR="${STRATEGY_LAB_RUN_DIR:-/var/run/zapret2-restyle/strategy-lab}"
STRATEGY_LAB_LOG_DIR="${STRATEGY_LAB_LOG_DIR:-/var/log/zapret2/strategy-lab}"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_JOBS_DIR:-${STRATEGY_LAB_RUN_DIR}/jobs}"
STRATEGY_LAB_ACTIVE_FILE="${STRATEGY_LAB_ACTIVE_FILE:-${STRATEGY_LAB_RUN_DIR}/active.job}"
STRATEGY_LAB_LATEST_FILE="${STRATEGY_LAB_LATEST_FILE:-${STRATEGY_LAB_RUN_DIR}/latest.job}"
STRATEGY_LAB_LOCK_FILE="${STRATEGY_LAB_LOCK_FILE:-${STRATEGY_LAB_RUN_DIR}/launcher.lock}"
STRATEGY_LAB_PS_BIN="${STRATEGY_LAB_PS_BIN:-/bin/ps}"

strategy_lab_require_jq()
{
    [ -x "${STRATEGY_LAB_JQ}" ] || {
        echo "ERROR: required JSON processor is missing: ${STRATEGY_LAB_JQ}" >&2
        return 1
    }
}

strategy_lab_prepare_directories()
{
    mkdir -p "${STRATEGY_LAB_JOBS_DIR}" "${STRATEGY_LAB_LOG_DIR}"
}

strategy_lab_job_id_valid()
{
    printf '%s\n' "$1" | grep -Eq '^job\.[A-Za-z0-9]+$'
}

strategy_lab_target_safe()
{
    _strategy_lab_target="$1"
    [ -n "${_strategy_lab_target}" ] || return 1
    [ "${#_strategy_lab_target}" -le 253 ] || return 1
    printf '%s\n' "${_strategy_lab_target}" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9.:-]*$'
}

strategy_lab_mode_valid()
{
    case "$1" in standard|extended) return 0 ;; esac
    return 1
}

strategy_lab_language_valid()
{
    case "$1" in en|ru) return 0 ;; esac
    return 1
}

strategy_lab_job_dir() { printf '%s/%s\n' "${STRATEGY_LAB_JOBS_DIR}" "$1"; }
strategy_lab_status_file() { printf '%s/status.json\n' "$(strategy_lab_job_dir "$1")"; }
strategy_lab_pid_file() { printf '%s/worker.pid\n' "$(strategy_lab_job_dir "$1")"; }
strategy_lab_cancel_file() { printf '%s/cancel.request\n' "$(strategy_lab_job_dir "$1")"; }
strategy_lab_event_file() { printf '%s/events.ndjson\n' "$(strategy_lab_job_dir "$1")"; }
strategy_lab_log_file() { printf '%s/%s.log\n' "${STRATEGY_LAB_LOG_DIR}" "$1"; }

strategy_lab_atomic_write()
{
    _strategy_lab_path="$1"
    _strategy_lab_dir=$(dirname "${_strategy_lab_path}")
    _strategy_lab_tmp=$(mktemp "${_strategy_lab_dir}/.strategy-lab.XXXXXX") || return 1
    cat > "${_strategy_lab_tmp}" || { rm -f "${_strategy_lab_tmp}"; return 1; }
    chmod 0644 "${_strategy_lab_tmp}"
    mv -f "${_strategy_lab_tmp}" "${_strategy_lab_path}"
}

strategy_lab_read_pointer()
{
    _strategy_lab_pointer="$1"
    _strategy_lab_value=''
    [ -r "${_strategy_lab_pointer}" ] || return 1
    IFS= read -r _strategy_lab_value < "${_strategy_lab_pointer}" || true
    strategy_lab_job_id_valid "${_strategy_lab_value}" || return 1
    [ -r "$(strategy_lab_status_file "${_strategy_lab_value}")" ] || return 1
    printf '%s\n' "${_strategy_lab_value}"
}

strategy_lab_write_pointer()
{
    _strategy_lab_pointer="$1"
    _strategy_lab_job="$2"
    strategy_lab_job_id_valid "${_strategy_lab_job}" || return 1
    printf '%s\n' "${_strategy_lab_job}" | strategy_lab_atomic_write "${_strategy_lab_pointer}"
}

strategy_lab_read_active_job()
{
    strategy_lab_read_pointer "${STRATEGY_LAB_ACTIVE_FILE}"
}

strategy_lab_write_active_job() { strategy_lab_write_pointer "${STRATEGY_LAB_ACTIVE_FILE}" "$1"; }
strategy_lab_read_latest_job() { strategy_lab_read_pointer "${STRATEGY_LAB_LATEST_FILE}"; }
strategy_lab_write_latest_job() { strategy_lab_write_pointer "${STRATEGY_LAB_LATEST_FILE}" "$1"; }

strategy_lab_clear_active_job()
{
    _strategy_lab_expected="$1"
    _strategy_lab_current=$(strategy_lab_read_active_job 2>/dev/null || true)
    [ "${_strategy_lab_current}" = "${_strategy_lab_expected}" ] && rm -f "${STRATEGY_LAB_ACTIVE_FILE}"
    return 0
}

strategy_lab_pid_read()
{
    _strategy_lab_pidfile="$1"
    _strategy_lab_pid=""
    [ -r "${_strategy_lab_pidfile}" ] || return 1
    IFS= read -r _strategy_lab_pid < "${_strategy_lab_pidfile}" || true
    case "${_strategy_lab_pid}" in ''|*[!0-9]*) return 1 ;; esac
    printf '%s\n' "${_strategy_lab_pid}"
}

strategy_lab_pid_running()
{
    _strategy_lab_pid=$(strategy_lab_pid_read "$1" 2>/dev/null || true)
    [ -n "${_strategy_lab_pid}" ] || return 1
    kill -0 "${_strategy_lab_pid}" 2>/dev/null
}

strategy_lab_worker_pid_matches()
{
    _strategy_lab_job="$1"
    _strategy_lab_pidfile="$2"
    _strategy_lab_pid=$(strategy_lab_pid_read "${_strategy_lab_pidfile}" 2>/dev/null || true)
    [ -n "${_strategy_lab_pid}" ] || return 1
    kill -0 "${_strategy_lab_pid}" 2>/dev/null || return 1
    [ -x "${STRATEGY_LAB_PS_BIN}" ] || return 1
    _strategy_lab_command=$("${STRATEGY_LAB_PS_BIN}" -p "${_strategy_lab_pid}" -o command= 2>/dev/null || true)
    printf '%s\n' "${_strategy_lab_command}" | grep -Fq "${_strategy_lab_job}" || return 1
    printf '%s\n' "${_strategy_lab_command}" | grep -Eq 'strategy_lab_worker\.sh|zapret_service\.sh.*strategy-lab'
}

strategy_lab_job_active()
{
    _strategy_lab_job="$1"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    _strategy_lab_pidfile=$(strategy_lab_pid_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || return 1
    _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${_strategy_lab_status}" 2>/dev/null || true)
    case "${_strategy_lab_state}" in
        queued|running|cancel_requested)
            strategy_lab_worker_pid_matches "${_strategy_lab_job}" "${_strategy_lab_pidfile}"
            ;;
        *) return 1 ;;
    esac
}
