#!/bin/sh

worker_skip_unfinished()
{
    _wsm_job="$1"
    _wsm_message="$2"
    strategy_lab_state_transform "${_wsm_job}" '
        (.stages[] |
            select((.status=="PENDING" or .status=="RUNNING") and
                   .number!="90" and .number!="99") |
            .status)="SKIPPED" |
        (.stages[] | select(.status=="SKIPPED" and .message=="") | .message)=$message
    ' --arg message "${_wsm_message}"
}

worker_check_cancel()
{
    [ ! -e "${CANCEL_FILE}" ] || worker_cancel
}

worker_stage_60()
{
    strategy_lab_update_stage "${JOB_ID}" 60 RUNNING '' || return 1
    strategy_lab_append_event "${JOB_ID}" 60 RUNNING \
        'Expanding parameters inside accepted TLS 1.3 families' || return 1

    _wsm_expansion="${JOB_DIR}/parameter-expansion.json"
    _wsm_timeout=$(worker_budget_timeout_for 60 "${STRATEGY_LAB_STAGE60_TIMEOUT}") || worker_stage_timeout 60
    if "${STRATEGY_LAB_TIMEOUT_BIN}" "${_wsm_timeout}" \
        "${EXPANSION_RUNNER}" "${JOB_ID}" "${JOB_DIR}/endpoints.txt" \
        "${JOB_DIR}/candidate-smoke.json" "${_wsm_expansion}"
    then
        _wsm_status=0
    else
        _wsm_status=$?
    fi
    worker_check_cancel
    [ "${_wsm_status}" -ne 124 ] || worker_stage_timeout 60
    [ "${_wsm_status}" -eq 0 ] || worker_error 60 \
        'Accepted-family parameter expansion failed internally.'
    [ -r "${_wsm_expansion}" ] || worker_error 60 \
        'Parameter expansion result was not produced.'
    strategy_lab_set_parameter_expansion_result "${JOB_ID}" "${_wsm_expansion}" ||
        worker_error 60 'Parameter expansion state could not be recorded.'

    _wsm_working=$("${STRATEGY_LAB_JQ}" -r '.working|length' "${_wsm_expansion}")
    _wsm_completed=$("${STRATEGY_LAB_JQ}" -r '.completed' "${_wsm_expansion}")
    if [ "${LANGUAGE}" = ru ]; then
        _wsm_message="PASS — Расширение параметров завершено: рабочих кандидатов ${_wsm_working}, проверено ${_wsm_completed}."
    else
        _wsm_message="PASS — Parameter expansion completed: ${_wsm_working} working candidates from ${_wsm_completed} tested."
    fi
    strategy_lab_update_stage "${JOB_ID}" 60 PASS "${_wsm_message}" || return 1
    strategy_lab_append_event "${JOB_ID}" 60 PASS "${_wsm_message}" || return 1
}

worker_stage_70()
{
    strategy_lab_update_stage "${JOB_ID}" 70 RUNNING '' || return 1
    strategy_lab_append_event "${JOB_ID}" 70 RUNNING \
        'Confirming candidate stability with three sequential fresh-connection attempts' || return 1

    _wsm_stability="${JOB_DIR}/stability.json"
    _wsm_timeout=$(worker_budget_timeout_for 70 "${STRATEGY_LAB_STAGE70_TIMEOUT}") || worker_stage_timeout 70
    if "${STRATEGY_LAB_TIMEOUT_BIN}" "${_wsm_timeout}" \
        "${STABILITY_RUNNER}" "${JOB_ID}" "${JOB_DIR}/endpoints.txt" \
        "${JOB_DIR}/parameter-expansion.json" "${JOB_DIR}/candidate-smoke.json" \
        "${_wsm_stability}"
    then
        _wsm_status=0
    else
        _wsm_status=$?
    fi
    worker_check_cancel
    [ "${_wsm_status}" -ne 124 ] || worker_stage_timeout 70
    [ "${_wsm_status}" -eq 0 ] || worker_error 70 \
        'Stability confirmation failed internally.'
    [ -r "${_wsm_stability}" ] || worker_error 70 \
        'Stability result was not produced.'

    _wsm_stable=$("${STRATEGY_LAB_JQ}" -r '.stable|length' "${_wsm_stability}")
    _wsm_tested=$("${STRATEGY_LAB_JQ}" -r '.completed' "${_wsm_stability}")
    if [ "${LANGUAGE}" = ru ]; then
        _wsm_message="PASS — Проверка стабильности завершена: стабильных ${_wsm_stable}, проверено ${_wsm_tested}."
    else
        _wsm_message="PASS — Stability confirmation completed: ${_wsm_stable} stable candidates from ${_wsm_tested} tested."
    fi
    strategy_lab_update_stage "${JOB_ID}" 70 PASS "${_wsm_message}" || return 1
    strategy_lab_append_event "${JOB_ID}" 70 PASS "${_wsm_message}" || return 1
}

worker_stage_80_command()
{
    _wsm_error="$1"
    shift
    _wsm_timeout=$(worker_budget_timeout_for 80 "${STRATEGY_LAB_STAGE80_TIMEOUT}") || worker_stage_timeout 80
    if "${STRATEGY_LAB_TIMEOUT_BIN}" "${_wsm_timeout}" "$@"
    then
        _wsm_status=0
    else
        _wsm_status=$?
    fi
    worker_check_cancel
    [ "${_wsm_status}" -ne 124 ] || worker_stage_timeout 80
    [ "${_wsm_status}" -eq 0 ] || worker_error 80 "${_wsm_error}"
}

worker_stage_80()
{
    if [ "${MODE}" != extended ]; then
        if [ "${LANGUAGE}" = ru ]; then
            _wsm_message='SKIPPED — расширенные ветви отключены в основном режиме.'
        else
            _wsm_message='SKIPPED — extended branches are disabled in standard mode.'
        fi
        strategy_lab_update_stage "${JOB_ID}" 80 SKIPPED "${_wsm_message}" || return 1
        strategy_lab_append_event "${JOB_ID}" 80 SKIPPED "${_wsm_message}" || return 1
        return 0
    fi

    strategy_lab_update_stage "${JOB_ID}" 80 RUNNING '' || return 1
    strategy_lab_append_event "${JOB_ID}" 80 RUNNING \
        'Testing extended TLS, HTTP, QUIC, and configured UDP branches' || return 1
    worker_budget_begin_stage80 || worker_stage_timeout 80

    _wsm_extended="${JOB_DIR}/extended-tcp.json"
    _wsm_quic="${JOB_DIR}/quic.json"
    _wsm_udp="${JOB_DIR}/udp.json"

    worker_stage_80_command 'Extended TLS/HTTP testing failed internally.' \
        "${EXTENDED_RUNNER}" "${JOB_ID}" "${JOB_DIR}/endpoints.txt" "${_wsm_extended}"
    [ -r "${_wsm_extended}" ] || worker_error 80 \
        'Extended TLS/HTTP result was not produced.'
    strategy_lab_set_extended_result "${JOB_ID}" "${_wsm_extended}" ||
        worker_error 80 'Extended result could not be recorded.'

    worker_stage_80_command 'QUIC testing failed internally.' \
        "${QUIC_RUNNER}" "${JOB_ID}" "${JOB_DIR}/endpoints.txt" \
        "${JOB_DIR}/network.json" "${_wsm_quic}"
    [ -r "${_wsm_quic}" ] || worker_error 80 'QUIC result was not produced.'
    strategy_lab_set_quic_result "${JOB_ID}" "${_wsm_quic}" ||
        worker_error 80 'QUIC result could not be recorded.'

    worker_stage_80_command 'Configured UDP testing failed internally.' \
        "${UDP_RUNNER}" "${JOB_ID}" "${JOB_DIR}/endpoints.txt" "${_wsm_udp}"
    [ -r "${_wsm_udp}" ] || worker_error 80 'Configured UDP result was not produced.'
    strategy_lab_set_udp_result "${JOB_ID}" "${_wsm_udp}" ||
        worker_error 80 'UDP result could not be recorded.'

    _wsm_quic_status=$("${STRATEGY_LAB_JQ}" -r '.status' "${_wsm_quic}")
    _wsm_udp_status=$("${STRATEGY_LAB_JQ}" -r '.status' "${_wsm_udp}")
    if [ "${LANGUAGE}" = ru ]; then
        _wsm_message="PASS — Расширенная проверка завершена; QUIC=${_wsm_quic_status}, UDP=${_wsm_udp_status}."
    else
        _wsm_message="PASS — Extended testing completed; QUIC=${_wsm_quic_status}, UDP=${_wsm_udp_status}."
    fi
    strategy_lab_update_stage "${JOB_ID}" 80 PASS "${_wsm_message}" || return 1
    strategy_lab_append_event "${JOB_ID}" 80 PASS "${_wsm_message}" || return 1
}

worker_stage_85()
{
    worker_budget_require 85 || worker_stage_timeout 85
    strategy_lab_update_stage "${JOB_ID}" 85 RUNNING '' || return 1
    strategy_lab_append_event "${JOB_ID}" 85 RUNNING \
        'Building the final stable-candidate shortlist' || return 1

    _wsm_stability="${JOB_DIR}/stability.json"
    _wsm_shortlist="${JOB_DIR}/shortlist.json"
    [ -r "${_wsm_stability}" ] || worker_error 85 \
        'Stability result is unavailable for shortlist construction.'
    strategy_lab_shortlist_build "${_wsm_stability}" "${_wsm_shortlist}" ||
        worker_error 85 'Shortlist could not be constructed.'
    strategy_lab_set_stability_result "${JOB_ID}" "${_wsm_stability}" \
        "${_wsm_shortlist}" || worker_error 85 \
        'Stability and shortlist state could not be recorded.'

    _wsm_count=$("${STRATEGY_LAB_JQ}" -r '.count' "${_wsm_shortlist}")
    if [ "${LANGUAGE}" = ru ]; then
        _wsm_message="PASS — Итоговый список сформирован: стабильных кандидатов ${_wsm_count}."
    else
        _wsm_message="PASS — Final shortlist built: ${_wsm_count} stable candidates."
    fi
    strategy_lab_update_stage "${JOB_ID}" 85 PASS "${_wsm_message}" || return 1
    strategy_lab_append_event "${JOB_ID}" 85 PASS "${_wsm_message}" || return 1
}

worker_run_search_stages()
{
    worker_check_cancel
    worker_stage_60
    worker_check_cancel
    worker_stage_70
    worker_check_cancel
    worker_stage_80
    worker_check_cancel
    worker_stage_85
    worker_check_cancel
}
