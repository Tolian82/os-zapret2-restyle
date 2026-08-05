#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
TRANSACTION_SCRIPT="${TRANSACTION_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"
DAEMON_BIN="${DAEMON_BIN:-/usr/sbin/daemon}"
MODE="${1:-status}"
set -eu
umask 022
for module in common state circular
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 1
    . "${path}"
done
strategy_lab_require_jq
strategy_lab_prepare_directories
strategy_lab_circular_prepare_dir

circular_emit_error()
{
    "${STRATEGY_LAB_JQ}" -nc --arg message "$1" '{status:"error",message:$message}'
}

circular_worker_running()
{
    [ -r "${STRATEGY_LAB_CIRCULAR_PID}" ] || return 1
    IFS= read -r _slcl_pid < "${STRATEGY_LAB_CIRCULAR_PID}" || return 1
    case "${_slcl_pid}" in ''|*[!0-9]*) return 1 ;; esac
    kill -0 "${_slcl_pid}" 2>/dev/null
}

circular_active()
{
    [ -r "${STRATEGY_LAB_CIRCULAR_STATE}" ] || return 1
    case "$("${STRATEGY_LAB_JQ}" -r '.state' "${STRATEGY_LAB_CIRCULAR_STATE}")" in
        queued|preparing|running|stop_requested)
            circular_worker_running
            ;;
        *)
            return 1
            ;;
    esac
}

circular_reject_stale()
{
    [ -r "${STRATEGY_LAB_CIRCULAR_STATE}" ] || return 1
    case "$("${STRATEGY_LAB_JQ}" -r '.state' "${STRATEGY_LAB_CIRCULAR_STATE}")" in
        queued|preparing|running|stop_requested)
            if ! circular_worker_running; then
                _slcl_job=$("${STRATEGY_LAB_JQ}" -r '.job_id // ""' "${STRATEGY_LAB_CIRCULAR_STATE}")
                _slcl_count=$("${STRATEGY_LAB_JQ}" -r '.candidate_count // 0' "${STRATEGY_LAB_CIRCULAR_STATE}")
                strategy_lab_circular_state_write error "${_slcl_job}" \
                    'Circular validation worker disappeared; verify Zapret2 state before retrying' \
                    "${_slcl_count}" stale_worker
                return 0
            fi
            ;;
    esac
    return 1
}

case "${MODE}" in
    start)
        [ "$#" -eq 2 ] || {
            circular_emit_error 'start requires JOB_ID'
            exit 64
        }
        JOB_ID="$2"
        if _slcl_eligibility=$(strategy_lab_circular_eligibility "${JOB_ID}"); then
            :
        else
            printf '%s\n' "${_slcl_eligibility}"
            exit 64
        fi
        _slcl_active_job=$(strategy_lab_read_active_job 2>/dev/null || true)
        [ -z "${_slcl_active_job}" ] || {
            "${STRATEGY_LAB_JQ}" -nc --arg job_id "${JOB_ID}" \
                '{status:"error",job_id:$job_id,circular_eligible:false,
                  reason:"automated_job_active",candidate_count:0}'
            exit 75
        }
        if circular_active; then
            cat "${STRATEGY_LAB_CIRCULAR_STATE}"
            exit 0
        fi
        if circular_reject_stale; then
            cat "${STRATEGY_LAB_CIRCULAR_STATE}"
            exit 1
        fi
        [ -x "${TRANSACTION_SCRIPT}" ] && [ -x "${DAEMON_BIN}" ] || {
            circular_emit_error 'circular lifecycle launcher is unavailable'
            exit 1
        }
        rm -f "${STRATEGY_LAB_CIRCULAR_STOP}" "${STRATEGY_LAB_CIRCULAR_PID}"
        COUNT=$("${STRATEGY_LAB_JQ}" -r '.items | length' \
            "$(strategy_lab_circular_shortlist_file "${JOB_ID}")")
        strategy_lab_circular_state_write queued "${JOB_ID}" \
            'Circular validation queued' "${COUNT}" ''
        if ! "${DAEMON_BIN}" -f -o "${STRATEGY_LAB_CIRCULAR_LOG}" \
            -p "${STRATEGY_LAB_CIRCULAR_PID}" \
            "${TRANSACTION_SCRIPT}" strategy-lab-circular "${JOB_ID}"; then
            strategy_lab_circular_state_write error "${JOB_ID}" \
                'Circular validation could not be started' "${COUNT}" launch_failed
            circular_emit_error 'circular validation could not be started'
            exit 1
        fi
        cat "${STRATEGY_LAB_CIRCULAR_STATE}"
        ;;
    status)
        circular_reject_stale || true
        if [ -r "${STRATEGY_LAB_CIRCULAR_STATE}" ]; then
            cat "${STRATEGY_LAB_CIRCULAR_STATE}"
        else
            "${STRATEGY_LAB_JQ}" -nc '{state:"idle"}'
        fi
        ;;
    stop)
        circular_reject_stale || true
        if ! circular_active; then
            if [ -r "${STRATEGY_LAB_CIRCULAR_STATE}" ]; then
                cat "${STRATEGY_LAB_CIRCULAR_STATE}"
            else
                "${STRATEGY_LAB_JQ}" -nc '{state:"idle"}'
            fi
            exit 0
        fi
        : > "${STRATEGY_LAB_CIRCULAR_STOP}"
        JOB_ID=$("${STRATEGY_LAB_JQ}" -r '.job_id' "${STRATEGY_LAB_CIRCULAR_STATE}")
        COUNT=$("${STRATEGY_LAB_JQ}" -r '.candidate_count' "${STRATEGY_LAB_CIRCULAR_STATE}")
        strategy_lab_circular_state_write stop_requested "${JOB_ID}" \
            'Circular validation stop requested' "${COUNT}" requested
        cat "${STRATEGY_LAB_CIRCULAR_STATE}"
        ;;
    *)
        circular_emit_error 'unsupported circular mode'
        exit 64
        ;;
esac
