#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
TRANSACTION_SCRIPT="${TRANSACTION_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"
DAEMON_BIN="${DAEMON_BIN:-/usr/sbin/daemon}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
STRATEGY_LAB_CIRCULAR_LOCK_FILE="${STRATEGY_LAB_CIRCULAR_LOCK_FILE:-${STRATEGY_LAB_RUN_DIR:-/var/run/zapret2-restyle/strategy-lab}/circular-launcher.lock}"
MODE="${1:-status}"
set -eu
umask 022

for module in common state firewall runtime candidate lifecycle circular circular_owner retention
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 1
    . "${path}"
done

strategy_lab_require_jq
strategy_lab_prepare_directories
strategy_lab_circular_prepare_dir
[ -x "${LOCKF_BIN}" ] || {
    "${STRATEGY_LAB_JQ}" -nc '{status:"error",message:"Circular launcher lock utility is unavailable"}'
    exit 1
}

circular_emit_error()
{
    "${STRATEGY_LAB_JQ}" -nc --arg message "$1" '{status:"error",message:$message}'
}

circular_active_session()
{
    _slcl_session=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
    [ -n "${_slcl_session}" ] || return 1
    _slcl_state_file=$(strategy_lab_circular_session_state_file "${_slcl_session}") || return 1
    [ -r "${_slcl_state_file}" ] || return 1
    case "$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${_slcl_state_file}")" in
        queued|preparing|running|stop_requested)
            strategy_lab_circular_owner_valid "${_slcl_session}" || return 1
            printf '%s\n' "${_slcl_session}"
            ;;
        *) return 1 ;;
    esac
}

circular_reconcile_stale()
{
    _slcl_session=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
    [ -n "${_slcl_session}" ] || return 1
    _slcl_state_file=$(strategy_lab_circular_session_state_file "${_slcl_session}") || return 1
    [ -r "${_slcl_state_file}" ] || {
        strategy_lab_circular_active_session_clear "${_slcl_session}"
        return 0
    }
    _slcl_state=$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${_slcl_state_file}")
    case "${_slcl_state}" in
        queued|preparing|running|stop_requested)
            strategy_lab_circular_owner_valid "${_slcl_session}" && return 1
            strategy_lab_circular_recover_stale_session "${_slcl_session}" || true
            return 0
            ;;
        restore_failed)
            return 0
            ;;
        *)
            strategy_lab_circular_active_session_clear "${_slcl_session}"
            return 0
            ;;
    esac
}

circular_cat_current()
{
    _slcl_state=$(strategy_lab_circular_current_state_file 2>/dev/null || true)
    if [ -n "${_slcl_state}" ] && [ -r "${_slcl_state}" ]; then
        cat "${_slcl_state}"
    else
        "${STRATEGY_LAB_JQ}" -nc '{state:"idle"}'
    fi
}

circular_abort_unowned_launch()
{
    _slcl_session="$1"
    _slcl_parent="$2"
    _slcl_count="$3"
    _slcl_pid_file=$(strategy_lab_circular_session_pid_file "${_slcl_session}")
    : > "$(strategy_lab_circular_session_stop_file "${_slcl_session}")"
    if [ -r "${_slcl_pid_file}" ]; then
        IFS= read -r _slcl_pid < "${_slcl_pid_file}" || _slcl_pid=''
        case "${_slcl_pid}" in ''|*[!0-9]*) ;; *) kill -TERM "${_slcl_pid}" 2>/dev/null || true ;; esac
    fi
    strategy_lab_circular_state_write "${_slcl_session}" error "${_slcl_parent}" \
        'Circular validation owner identity could not be established' \
        "${_slcl_count}" owner_unavailable
    strategy_lab_circular_active_session_clear "${_slcl_session}"
}

circular_dispatch()
{
    case "${MODE}" in
        start)
            [ "$#" -eq 2 ] || {
                circular_emit_error 'start requires JOB_ID'
                return 64
            }
            PARENT_JOB_ID="$2"
            if _slcl_eligibility=$(strategy_lab_circular_eligibility "${PARENT_JOB_ID}"); then
                :
            else
                printf '%s\n' "${_slcl_eligibility}"
                return 64
            fi
            _slcl_active_job=$(strategy_lab_read_active_job 2>/dev/null || true)
            [ -z "${_slcl_active_job}" ] || {
                "${STRATEGY_LAB_JQ}" -nc --arg job_id "${PARENT_JOB_ID}" \
                    '{status:"error",job_id:$job_id,circular_eligible:false,
                      reason:"automated_job_active",candidate_count:0}'
                return 75
            }
            if _slcl_session=$(circular_active_session); then
                cat "$(strategy_lab_circular_session_state_file "${_slcl_session}")"
                return 0
            fi
            if circular_reconcile_stale; then
                circular_cat_current
                return 75
            fi
            [ -x "${TRANSACTION_SCRIPT}" ] && [ -x "${DAEMON_BIN}" ] || {
                circular_emit_error 'circular lifecycle launcher is unavailable'
                return 1
            }

            SESSION_ID=$(strategy_lab_circular_session_create "${PARENT_JOB_ID}") || {
                circular_emit_error 'circular validation session could not be created'
                return 1
            }
            COUNT=$(strategy_lab_circular_candidate_count \
                "$(strategy_lab_circular_session_shortlist_file "${SESSION_ID}")")
            strategy_lab_circular_state_write "${SESSION_ID}" queued "${PARENT_JOB_ID}" \
                'Circular validation queued' "${COUNT}" ''
            _slcl_log=$(strategy_lab_circular_session_log_file "${SESSION_ID}")
            _slcl_pid=$(strategy_lab_circular_session_pid_file "${SESSION_ID}")
            rm -f "$(strategy_lab_circular_session_stop_file "${SESSION_ID}")" \
                "${_slcl_pid}" "$(strategy_lab_circular_session_owner_file "${SESSION_ID}")"
            if ! "${DAEMON_BIN}" -f -o "${_slcl_log}" -p "${_slcl_pid}" \
                "${TRANSACTION_SCRIPT}" strategy-lab-circular "${PARENT_JOB_ID}" 9>&-; then
                strategy_lab_circular_state_write "${SESSION_ID}" error "${PARENT_JOB_ID}" \
                    'Circular validation could not be started' "${COUNT}" launch_failed
                strategy_lab_circular_active_session_clear "${SESSION_ID}"
                circular_emit_error 'circular validation could not be started'
                return 1
            fi
            if ! strategy_lab_circular_owner_write_from_pid_file "${SESSION_ID}" "${PARENT_JOB_ID}"; then
                circular_abort_unowned_launch "${SESSION_ID}" "${PARENT_JOB_ID}" "${COUNT}"
                circular_emit_error 'circular validation owner identity could not be established'
                return 1
            fi
            cat "$(strategy_lab_circular_session_state_file "${SESSION_ID}")"
            ;;
        status)
            circular_reconcile_stale || true
            circular_cat_current
            ;;
        stop)
            circular_reconcile_stale || true
            SESSION_ID=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
            if [ -z "${SESSION_ID}" ] || ! _slcl_live=$(circular_active_session 2>/dev/null); then
                circular_cat_current
                return 0
            fi
            : > "$(strategy_lab_circular_session_stop_file "${SESSION_ID}")"
            _slcl_state=$(strategy_lab_circular_session_state_file "${SESSION_ID}")
            PARENT_JOB_ID=$("${STRATEGY_LAB_JQ}" -r '.parent_job_id // .job_id // ""' "${_slcl_state}")
            COUNT=$("${STRATEGY_LAB_JQ}" -r '.candidate_count // 0' "${_slcl_state}")
            strategy_lab_circular_state_write "${SESSION_ID}" stop_requested "${PARENT_JOB_ID}" \
                'Circular validation stop requested' "${COUNT}" requested
            cat "${_slcl_state}"
            ;;
        *)
            circular_emit_error 'unsupported circular mode'
            return 64
            ;;
    esac
}

(
    if ! "${LOCKF_BIN}" -s -t 0 9; then
        "${STRATEGY_LAB_JQ}" -nc '{status:"busy",message:"Circular launcher is busy"}'
        exit 75
    fi
    strategy_lab_retention_prune_circular || true
    circular_dispatch "$@"
) 9>"${STRATEGY_LAB_CIRCULAR_LOCK_FILE}"
