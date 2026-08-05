#!/bin/sh

usage_error()
{
    echo "ERROR: $1" >&2
    echo "Usage: strategy_lab_launcher.sh {start TARGET MODE LANGUAGE [UDP_PORT UDP_PAYLOAD_BASE64]|status [JOB_ID]|cancel JOB_ID|result JOB_ID}" >&2
    exit 64
}

emit_error_json()
{
    "${STRATEGY_LAB_JQ}" -nc --arg message "$1" '{status:"error",message:$message}'
}

strategy_lab_recovery_service_status()
{
    if "${TRANSACTION_SCRIPT}" status >/dev/null 2>&1; then return 0; fi
    return $?
}

strategy_lab_recovery_restore_service()
{
    _strategy_lab_initial="$1"
    if strategy_lab_recovery_service_status; then _strategy_lab_current=0; else _strategy_lab_current=$?; fi
    case "${_strategy_lab_initial}:${_strategy_lab_current}" in
        RUNNING:0|STOPPED:1) return 0 ;;
        RUNNING:1) "${TRANSACTION_SCRIPT}" start >/dev/null 2>&1 ;;
        RUNNING:2) "${TRANSACTION_SCRIPT}" stop >/dev/null 2>&1 && "${TRANSACTION_SCRIPT}" start >/dev/null 2>&1 ;;
        STOPPED:0|STOPPED:2) "${TRANSACTION_SCRIPT}" stop >/dev/null 2>&1 ;;
        *) return 1 ;;
    esac
}

strategy_lab_reconcile_stale_job()
{
    _strategy_lab_job="$1"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    [ -r "${_strategy_lab_status}" ] || return 1
    _strategy_lab_state=$("${STRATEGY_LAB_JQ}" -r '.state // ""' "${_strategy_lab_status}" 2>/dev/null || true)
    case "${_strategy_lab_state}" in queued|running|cancel_requested) ;; *) return 0 ;; esac
    strategy_lab_job_active "${_strategy_lab_job}" && return 0

    _strategy_lab_initial=$("${STRATEGY_LAB_JQ}" -r '.initial_service_state // ""' "${_strategy_lab_status}" 2>/dev/null || true)
    _strategy_lab_runtime_clean=false
    _strategy_lab_restored=false
    if strategy_lab_candidate_stop "${_strategy_lab_job}" &&
       strategy_lab_firewall_remove_rules &&
       strategy_lab_firewall_range_empty &&
       strategy_lab_candidate_runtime_absent; then
        _strategy_lab_runtime_clean=true
        strategy_lab_recovery_restore_service "${_strategy_lab_initial}" && _strategy_lab_restored=true
    fi
    strategy_lab_udp_input_cleanup "${_strategy_lab_job}" || true

    _strategy_lab_tmp=$(mktemp "$(dirname "${_strategy_lab_status}")/.stale-recovery.XXXXXX") || return 1
    if [ "${_strategy_lab_restored}" = true ]; then
        _strategy_lab_outcome=ERROR
        _strategy_lab_message='ERROR — Strategy Lab worker disappeared; temporary state was cleaned and the original service state was restored.'
        _strategy_lab_restore_status=PASS
    else
        _strategy_lab_outcome=RESTORE_FAILED
        _strategy_lab_message='RESTORE_FAILED — Strategy Lab worker disappeared and the original service state could not be proven restored.'
        _strategy_lab_restore_status=FAIL
    fi
    "${STRATEGY_LAB_JQ}" \
        --arg outcome "${_strategy_lab_outcome}" \
        --arg message "${_strategy_lab_message}" \
        --arg restore_status "${_strategy_lab_restore_status}" \
        --arg initial "${_strategy_lab_initial}" \
        --argjson restored "${_strategy_lab_restored}" \
        --argjson clean "${_strategy_lab_runtime_clean}" '
        .state="error" | .outcome=$outcome | .current_stage="99" | .message=$message |
        .stale_worker_recovered=true |
        .restoration={verified:$restored,source:"stale-worker-recovery",initial_state:$initial,
                      final_state:(if $restored then $initial else "unknown" end),
                      strategy_unchanged:false,temporary_runtime_clean:$clean} |
        (.stages[] | select((.status=="PENDING" or .status=="RUNNING") and .number!="90" and .number!="99") | .status)="SKIPPED" |
        (.stages[] | select(.number=="90") | .status)=$restore_status |
        (.stages[] | select(.number=="90") | .message)=$message |
        (.stages[] | select(.number=="99") | .status)="FAIL" |
        (.stages[] | select(.number=="99") | .message)=$message
    ' "${_strategy_lab_status}" > "${_strategy_lab_tmp}" || { rm -f "${_strategy_lab_tmp}"; return 1; }
    chmod 0644 "${_strategy_lab_tmp}"
    mv -f "${_strategy_lab_tmp}" "${_strategy_lab_status}"
    rm -f "$(strategy_lab_pid_file "${_strategy_lab_job}")"
    strategy_lab_clear_active_job "${_strategy_lab_job}"
}

cleanup_stale_active()
{
    _strategy_lab_active=$(strategy_lab_read_active_job 2>/dev/null || true)
    [ -n "${_strategy_lab_active}" ] || return 0
    strategy_lab_reconcile_stale_job "${_strategy_lab_active}" || return 1
    strategy_lab_job_active "${_strategy_lab_active}" || strategy_lab_clear_active_job "${_strategy_lab_active}"
}

start_job()
{
    case "$#" in
        4)
            _strategy_lab_udp_port='-'
            _strategy_lab_udp_payload='-'
            ;;
        6)
            _strategy_lab_udp_port="$5"
            _strategy_lab_udp_payload="$6"
            ;;
        *)
            usage_error "start requires TARGET MODE LANGUAGE and optional UDP_PORT UDP_PAYLOAD_BASE64"
            ;;
    esac
    _strategy_lab_target=$(strategy_lab_normalize_target "$2" 2>/dev/null || true)
    _strategy_lab_mode="$3"
    _strategy_lab_language="$4"

    [ -n "${_strategy_lab_target}" ] || usage_error "invalid target"
    strategy_lab_mode_valid "${_strategy_lab_mode}" || usage_error "invalid mode"
    strategy_lab_language_valid "${_strategy_lab_language}" || usage_error "invalid language"
    [ -x "${WORKER_SCRIPT}" ] || { emit_error_json "Strategy Lab worker is unavailable"; return 1; }
    [ -x "${TRANSACTION_SCRIPT}" ] || { emit_error_json "Strategy Lab lifecycle transaction is unavailable"; return 1; }
    [ -x "${DAEMON_BIN}" ] || { emit_error_json "Strategy Lab daemon launcher is unavailable"; return 1; }

    cleanup_stale_active || { emit_error_json "Strategy Lab stale job recovery failed"; return 1; }
    _strategy_lab_active=$(strategy_lab_read_active_job 2>/dev/null || true)
    if [ -n "${_strategy_lab_active}" ]; then
        "${STRATEGY_LAB_JQ}" -nc --arg job_id "${_strategy_lab_active}" '{status:"busy",job_id:$job_id}'
        return 0
    fi

    _strategy_lab_jobdir=$(mktemp -d "${STRATEGY_LAB_JOBS_DIR}/job.XXXXXX") || { emit_error_json "Strategy Lab job directory could not be created"; return 1; }
    _strategy_lab_job=$(basename "${_strategy_lab_jobdir}")
    strategy_lab_job_id_valid "${_strategy_lab_job}" || { rm -rf "${_strategy_lab_jobdir}"; emit_error_json "Strategy Lab job id generation failed"; return 1; }

    strategy_lab_initialize_state "${_strategy_lab_job}" "${_strategy_lab_target}" "${_strategy_lab_mode}" "${_strategy_lab_language}"
    if ! strategy_lab_udp_input_prepare "${_strategy_lab_job}" "${_strategy_lab_mode}" \
        "${_strategy_lab_udp_port}" "${_strategy_lab_udp_payload}"
    then
        rm -rf "${_strategy_lab_jobdir}"
        emit_error_json "Invalid Strategy Lab generic UDP input"
        return 1
    fi

    strategy_lab_write_active_job "${_strategy_lab_job}"
    _strategy_lab_log=$(strategy_lab_log_file "${_strategy_lab_job}")
    _strategy_lab_pid=$(strategy_lab_pid_file "${_strategy_lab_job}")
    rm -f "${_strategy_lab_pid}"

    if ! "${DAEMON_BIN}" -f -o "${_strategy_lab_log}" -p "${_strategy_lab_pid}" "${TRANSACTION_SCRIPT}" strategy-lab "${_strategy_lab_job}"; then
        strategy_lab_clear_active_job "${_strategy_lab_job}"
        strategy_lab_udp_input_cleanup "${_strategy_lab_job}" || true
        strategy_lab_update_job "${_strategy_lab_job}" error ERROR 00 false 'Strategy Lab lifecycle transaction could not be started' || true
        emit_error_json "Strategy Lab lifecycle transaction could not be started"
        return 1
    fi
    "${STRATEGY_LAB_JQ}" -nc --arg job_id "${_strategy_lab_job}" '{status:"ok",job_id:$job_id,state:"queued"}'
}
