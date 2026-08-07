#!/bin/sh

STRATEGY_LAB_SERVICE_SCRIPT="${STRATEGY_LAB_SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}"
STRATEGY_LAB_TIMEOUT_BIN="${STRATEGY_LAB_TIMEOUT_BIN:-/usr/bin/timeout}"
STRATEGY_LAB_STOP_TIMEOUT="${STRATEGY_LAB_STOP_TIMEOUT:-10}"
STRATEGY_LAB_RESTORE_TIMEOUT="${STRATEGY_LAB_RESTORE_TIMEOUT:-45}"
STRATEGY_LAB_INITIAL_SERVICE_STATE=""
STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE=""

strategy_lab_service_status_code()
{
    if "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-status >/dev/null 2>&1; then return 0; else _strategy_lab_service_status=$?; fi
    return "${_strategy_lab_service_status}"
}

strategy_lab_lifecycle_snapshot_file(){ printf '%s/lifecycle-snapshot.json\n' "${JOB_DIR}"; }
strategy_lab_lifecycle_restoration_file(){ printf '%s/lifecycle-restoration.json\n' "${JOB_DIR}"; }

strategy_lab_record_json_field()
{
    _strategy_lab_record_field="$1"
    _strategy_lab_record_file="$2"
    if command -v strategy_lab_state_transform >/dev/null 2>&1; then
        strategy_lab_state_transform "${JOB_ID}" '.[$field]=$value[0]' \
            --arg field "${_strategy_lab_record_field}" --slurpfile value "${_strategy_lab_record_file}"
        return $?
    fi
    _strategy_lab_record_status=$(strategy_lab_status_file "${JOB_ID}")
    _strategy_lab_record_tmp=$(mktemp "$(dirname "${_strategy_lab_record_status}")/.lifecycle.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" --arg field "${_strategy_lab_record_field}" --slurpfile value "${_strategy_lab_record_file}" \
        '.[$field]=$value[0]' "${_strategy_lab_record_status}" > "${_strategy_lab_record_tmp}" || { rm -f "${_strategy_lab_record_tmp}"; return 1; }
    chmod 0644 "${_strategy_lab_record_tmp}"
    mv -f "${_strategy_lab_record_tmp}" "${_strategy_lab_record_status}"
}

strategy_lab_fetch_semantic_evidence()
{
    _strategy_lab_evidence_output="$1"; _strategy_lab_evidence_tmp="${_strategy_lab_evidence_output}.tmp.$$"
    if "${STRATEGY_LAB_SERVICE_SCRIPT}" strategy-lab-evidence > "${_strategy_lab_evidence_tmp}" 2>/dev/null; then _strategy_lab_evidence_status=0; else _strategy_lab_evidence_status=$?; fi
    if [ "${_strategy_lab_evidence_status}" -eq 64 ]; then rm -f "${_strategy_lab_evidence_tmp}"; return 2; fi
    [ "${_strategy_lab_evidence_status}" -eq 0 ] || { rm -f "${_strategy_lab_evidence_tmp}"; return 1; }
    "${STRATEGY_LAB_JQ}" -e '
        .schema==1 and .source=="zapret_service" and
        (.state=="RUNNING" or .state=="STOPPED" or .state=="INCOMPLETE") and
        (.child_running|type)=="boolean" and (.supervisor_running|type)=="boolean" and
        (.runtime_args_hash|type)=="string" and (.effective_config_hash|type)=="string" and
        (.normal_firewall_hash|type)=="string"
    ' "${_strategy_lab_evidence_tmp}" >/dev/null || { rm -f "${_strategy_lab_evidence_tmp}"; return 1; }
    mv -f "${_strategy_lab_evidence_tmp}" "${_strategy_lab_evidence_output}"
    chmod 0644 "${_strategy_lab_evidence_output}"
}

strategy_lab_semantic_snapshot_valid()
{
    _strategy_lab_snapshot="$1"; _strategy_lab_expected_state="$2"
    "${STRATEGY_LAB_JQ}" -e --arg state "${_strategy_lab_expected_state}" '
        .state==$state and .effective_config_hash!="missing" and
        (if $state=="RUNNING" then
            .child_running==true and .supervisor_running==true and .runtime_args_hash!="missing" and
            .normal_firewall_hash!="empty" and .normal_firewall_hash!="missing"
         else .child_running==false and .supervisor_running==false and .normal_firewall_hash=="empty" end)
    ' "${_strategy_lab_snapshot}" >/dev/null
}

strategy_lab_write_legacy_snapshot()
{
    _strategy_lab_legacy_output="$1"
    "${STRATEGY_LAB_JQ}" -nc --arg state "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" '
        {schema:1,source:"legacy-status",state:$state,child_running:null,supervisor_running:null,
         runtime_args_hash:"unavailable",effective_config_hash:"unavailable",normal_firewall_hash:"unavailable"}
    ' > "${_strategy_lab_legacy_output}"
    chmod 0644 "${_strategy_lab_legacy_output}"
}

strategy_lab_capture_initial_service_state()
{
    if strategy_lab_service_status_code; then STRATEGY_LAB_INITIAL_SERVICE_STATE="RUNNING"; else
        _strategy_lab_state_status=$?
        case "${_strategy_lab_state_status}" in 1) STRATEGY_LAB_INITIAL_SERVICE_STATE="STOPPED" ;; *) STRATEGY_LAB_INITIAL_SERVICE_STATE="INCOMPLETE"; return 1 ;; esac
    fi
    _strategy_lab_snapshot=$(strategy_lab_lifecycle_snapshot_file)
    if strategy_lab_fetch_semantic_evidence "${_strategy_lab_snapshot}"; then
        STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE=zapret_service
        strategy_lab_semantic_snapshot_valid "${_strategy_lab_snapshot}" "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" || { STRATEGY_LAB_INITIAL_SERVICE_STATE="INCOMPLETE"; return 1; }
    else
        _strategy_lab_evidence_status=$?
        [ "${_strategy_lab_evidence_status}" -eq 2 ] || { STRATEGY_LAB_INITIAL_SERVICE_STATE="INCOMPLETE"; return 1; }
        STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE=legacy-status
        strategy_lab_write_legacy_snapshot "${_strategy_lab_snapshot}" || return 1
    fi
    export STRATEGY_LAB_INITIAL_SERVICE_STATE STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE
    strategy_lab_record_json_field lifecycle_snapshot "${_strategy_lab_snapshot}"
}

strategy_lab_timed_service_action()
{
    _strategy_lab_action="$1"; _strategy_lab_timeout="$2"
    [ -x "${STRATEGY_LAB_TIMEOUT_BIN}" ] || { echo "ERROR: Strategy Lab timeout utility is unavailable" >&2; return 1; }
    [ -x "${STRATEGY_LAB_SERVICE_SCRIPT}" ] || { echo "ERROR: Strategy Lab service control is unavailable" >&2; return 1; }
    "${STRATEGY_LAB_TIMEOUT_BIN}" -f "${_strategy_lab_timeout}" "${STRATEGY_LAB_SERVICE_SCRIPT}" "strategy-lab-${_strategy_lab_action}"
}

strategy_lab_verify_stopped()
{
    if strategy_lab_service_status_code; then return 1; else _strategy_lab_verify_status=$?; fi
    [ "${_strategy_lab_verify_status}" -eq 1 ]
}
strategy_lab_verify_running(){ strategy_lab_service_status_code; }

strategy_lab_stop_normal_service()
{
    case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
        RUNNING) strategy_lab_timed_service_action stop "${STRATEGY_LAB_STOP_TIMEOUT}" || return 1; strategy_lab_verify_stopped ;;
        STOPPED) strategy_lab_verify_stopped ;;
        *) return 1 ;;
    esac
}

strategy_lab_cleanup_temporary_runtime()
{
    if command -v strategy_lab_candidate_cleanup >/dev/null 2>&1 && [ -n "${JOB_ID:-}" ]; then strategy_lab_candidate_cleanup "${JOB_ID}" || return 1; fi
    if command -v strategy_lab_firewall_range_empty >/dev/null 2>&1; then strategy_lab_firewall_range_empty || return 1; fi
    if command -v strategy_lab_candidate_pid_file >/dev/null 2>&1 && command -v strategy_lab_candidate_process_running >/dev/null 2>&1 && [ -n "${JOB_ID:-}" ]; then
        _strategy_lab_candidate_pid=$(strategy_lab_candidate_pid_file "${JOB_ID}")
        strategy_lab_candidate_process_running "${_strategy_lab_candidate_pid}" && return 1
        [ ! -e "${_strategy_lab_candidate_pid}" ] || return 1
    fi
    return 0
}

strategy_lab_normalize_stopped_state()
{
    if strategy_lab_service_status_code; then _strategy_lab_current_status=0; else _strategy_lab_current_status=$?; fi
    case "${_strategy_lab_current_status}" in
        1) return 0 ;;
        0|2) strategy_lab_timed_service_action stop "${STRATEGY_LAB_STOP_TIMEOUT}" || return 1; strategy_lab_verify_stopped ;;
        *) return 1 ;;
    esac
}

strategy_lab_restore_running_state()
{
    if strategy_lab_service_status_code; then return 0; else _strategy_lab_current_status=$?; fi
    case "${_strategy_lab_current_status}" in 1) ;; 2) strategy_lab_normalize_stopped_state || return 1 ;; *) return 1 ;; esac
    _strategy_lab_restore_attempt=1
    while [ "${_strategy_lab_restore_attempt}" -le 2 ]; do
        if strategy_lab_timed_service_action start "${STRATEGY_LAB_RESTORE_TIMEOUT}"; then strategy_lab_verify_running && return 0; else strategy_lab_verify_running && return 0; fi
        if [ "${_strategy_lab_restore_attempt}" -ge 2 ]; then strategy_lab_normalize_stopped_state || true; return 1; fi
        strategy_lab_normalize_stopped_state || return 1
        _strategy_lab_restore_attempt=$((_strategy_lab_restore_attempt + 1))
    done
    return 1
}
strategy_lab_restore_stopped_state(){ strategy_lab_normalize_stopped_state; }

strategy_lab_write_restoration_result()
{
    _strategy_lab_restore_verified="$1"; _strategy_lab_restore_source="$2"; _strategy_lab_restore_final_state="$3"; _strategy_lab_restore_strategy_unchanged="$4"; _strategy_lab_restore_runtime_clean="$5"
    _strategy_lab_restore_output=$(strategy_lab_lifecycle_restoration_file)
    "${STRATEGY_LAB_JQ}" -nc --argjson verified "${_strategy_lab_restore_verified}" --arg source "${_strategy_lab_restore_source}" \
        --arg initial_state "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" --arg final_state "${_strategy_lab_restore_final_state}" \
        --argjson strategy_unchanged "${_strategy_lab_restore_strategy_unchanged}" --argjson temporary_runtime_clean "${_strategy_lab_restore_runtime_clean}" '
        {verified:$verified,source:$source,initial_state:$initial_state,final_state:$final_state,
         strategy_unchanged:$strategy_unchanged,temporary_runtime_clean:$temporary_runtime_clean}' > "${_strategy_lab_restore_output}" || return 1
    chmod 0644 "${_strategy_lab_restore_output}"
    strategy_lab_record_json_field restoration "${_strategy_lab_restore_output}"
}

strategy_lab_verify_semantic_restoration()
{
    _strategy_lab_initial=$(strategy_lab_lifecycle_snapshot_file); _strategy_lab_final="${JOB_DIR}/lifecycle-final.json"
    strategy_lab_fetch_semantic_evidence "${_strategy_lab_final}" || return 1
    strategy_lab_semantic_snapshot_valid "${_strategy_lab_final}" "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" || return 1
    _strategy_lab_strategy_unchanged=false; _strategy_lab_runtime_clean=true
    if "${STRATEGY_LAB_JQ}" -e --slurpfile initial "${_strategy_lab_initial}" '
        .effective_config_hash==$initial[0].effective_config_hash and .runtime_args_hash==$initial[0].runtime_args_hash and
        .normal_firewall_hash==$initial[0].normal_firewall_hash' "${_strategy_lab_final}" >/dev/null; then _strategy_lab_strategy_unchanged=true; fi
    [ "${_strategy_lab_strategy_unchanged}" = true ] || { strategy_lab_write_restoration_result false zapret_service "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" false true || true; return 1; }
    strategy_lab_write_restoration_result true zapret_service "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" true "${_strategy_lab_runtime_clean}"
}

strategy_lab_restore_initial_service_state()
{
    if ! strategy_lab_cleanup_temporary_runtime; then strategy_lab_write_restoration_result false "${STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE:-unknown}" unknown false false || true; return 1; fi
    case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
        RUNNING) strategy_lab_restore_running_state || { strategy_lab_write_restoration_result false "${STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE:-unknown}" unknown false true || true; return 1; } ;;
        STOPPED) strategy_lab_restore_stopped_state || { strategy_lab_write_restoration_result false "${STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE:-unknown}" unknown false true || true; return 1; } ;;
        '') return 0 ;;
        *) return 1 ;;
    esac
    if [ "${STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE}" = zapret_service ]; then strategy_lab_verify_semantic_restoration; return $?; fi
    strategy_lab_write_restoration_result true legacy-status "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" true true
}
