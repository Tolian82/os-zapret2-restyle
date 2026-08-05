#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
LIFECYCLE_LOCK_FILE="${LIFECYCLE_LOCK_FILE:-/var/run/zapret2-lifecycle.lock}"
set -eu
umask 022

for module in common state circular circular_owner
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 1
    . "${path}"
done

strategy_lab_require_jq
strategy_lab_prepare_directories
strategy_lab_circular_prepare_dir

emit_guard()
{
    _slg_busy="$1"
    _slg_owner="$2"
    _slg_id="$3"
    _slg_state="$4"
    _slg_reason="$5"
    "${STRATEGY_LAB_JQ}" -nc \
        --argjson busy "${_slg_busy}" \
        --arg owner "${_slg_owner}" \
        --arg owner_id "${_slg_id}" \
        --arg state "${_slg_state}" \
        --arg reason "${_slg_reason}" '
        {status:(if $busy then "busy" else "ok" end),busy:$busy,
         owner:$owner,owner_id:$owner_id,state:$state,reason:$reason}
    '
}

automated_job=$(strategy_lab_read_active_job 2>/dev/null || true)
if [ -n "${automated_job}" ] && strategy_lab_job_id_valid "${automated_job}"; then
    automated_status=$(strategy_lab_status_file "${automated_job}")
    automated_state='unknown'
    [ ! -r "${automated_status}" ] || automated_state=$("${STRATEGY_LAB_JQ}" -r '.state // "unknown"' "${automated_status}" 2>/dev/null || printf '%s\n' unknown)
    case "${automated_state}" in
        queued|running|cancel_requested)
            emit_guard true automated "${automated_job}" "${automated_state}" strategy_lab_active
            exit 0
            ;;
    esac
fi

circular_session=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
if [ -n "${circular_session}" ]; then
    circular_state_file=$(strategy_lab_circular_session_state_file "${circular_session}" 2>/dev/null || true)
    circular_state='unknown'
    [ ! -r "${circular_state_file}" ] || circular_state=$("${STRATEGY_LAB_JQ}" -r '.state // "unknown"' "${circular_state_file}" 2>/dev/null || printf '%s\n' unknown)
    case "${circular_state}" in
        queued|preparing|running|stop_requested|restore_failed)
            emit_guard true circular "${circular_session}" "${circular_state}" circular_active
            exit 0
            ;;
    esac
fi

[ -x "${LOCKF_BIN}" ] || {
    emit_guard true lifecycle '' unavailable lock_utility_unavailable
    exit 0
}

if (
    "${LOCKF_BIN}" -s -t 0 9
) 9>"${LIFECYCLE_LOCK_FILE}"; then
    emit_guard false none '' idle available
else
    emit_guard true lifecycle '' locked lifecycle_lock_busy
fi
