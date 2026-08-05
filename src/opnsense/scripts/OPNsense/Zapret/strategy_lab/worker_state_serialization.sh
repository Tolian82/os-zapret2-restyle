#!/bin/sh

strategy_lab_record_json_field()
{
    strategy_lab_state_transform "${JOB_ID}" \
        '.[$field]=$value[0]' \
        --arg field "$1" --slurpfile value "$2"
}

strategy_lab_set_candidate_smoke_result()
{
    strategy_lab_state_transform "$1" '
        .candidate_smoke=$value[0] | .family_screening=$value[0]
    ' --slurpfile value "$2"
}

worker_budget_record_initial()
{
    _worker_budget_started_at=$(worker_budget_iso8601 \
        "${WORKER_BUDGET_STARTED_EPOCH}") || return 1
    _worker_budget_standard_deadline_at=$(worker_budget_iso8601 \
        "${WORKER_STANDARD_DEADLINE_EPOCH}") || return 1
    _worker_budget_deadline_at=$(worker_budget_iso8601 \
        "${WORKER_OVERALL_DEADLINE_EPOCH}") || return 1

    strategy_lab_state_transform "${JOB_ID}" '
        .started_at=$started_at |
        .standard_deadline_at=$standard_deadline_at |
        .deadline_at=$deadline_at |
        .standard_budget_seconds=$standard_budget_seconds |
        .extended_budget_seconds=$extended_budget_seconds |
        .search_budget_seconds=$search_budget_seconds |
        .stage80_budget_seconds=$stage80_budget_seconds
    ' --arg started_at "${_worker_budget_started_at}" \
      --arg standard_deadline_at "${_worker_budget_standard_deadline_at}" \
      --arg deadline_at "${_worker_budget_deadline_at}" \
      --argjson standard_budget_seconds "${STRATEGY_LAB_STANDARD_BUDGET}" \
      --argjson extended_budget_seconds "${STRATEGY_LAB_EXTENDED_BUDGET}" \
      --argjson search_budget_seconds "${WORKER_SEARCH_BUDGET_SECONDS}" \
      --argjson stage80_budget_seconds "${STRATEGY_LAB_STAGE80_TIMEOUT}"
}

worker_budget_record_stage80()
{
    _worker_budget_started_at=$(worker_budget_iso8601 \
        "${WORKER_STAGE80_STARTED_EPOCH}") || return 1
    _worker_budget_deadline_at=$(worker_budget_iso8601 \
        "${WORKER_STAGE80_DEADLINE_EPOCH}") || return 1

    strategy_lab_state_transform "${JOB_ID}" '
        .stage80_started_at=$started_at |
        .stage80_deadline_at=$deadline_at
    ' --arg started_at "${_worker_budget_started_at}" \
      --arg deadline_at "${_worker_budget_deadline_at}"
}

strategy_lab_set_parameter_expansion_result()
{
    strategy_lab_state_transform "$1" \
        '.parameter_expansion=$value[0]' \
        --slurpfile value "$2"
}

strategy_lab_set_extended_result()
{
    strategy_lab_state_transform "$1" \
        '.extended=$value[0]' \
        --slurpfile value "$2"
}

strategy_lab_set_quic_result()
{
    strategy_lab_state_transform "$1" \
        '.quic=$value[0]' \
        --slurpfile value "$2"
}

strategy_lab_set_udp_result()
{
    strategy_lab_state_transform "$1" \
        '.udp=$value[0]' \
        --slurpfile value "$2"
}

strategy_lab_set_stability_result()
{
    strategy_lab_state_transform "$1" '
        .stability=$stability[0] | .shortlist=$shortlist[0]
    ' --slurpfile stability "$2" --slurpfile shortlist "$3"
}

worker_result_set_circular_eligibility()
{
    _worker_result_status=$(strategy_lab_status_file "${JOB_ID}")
    _worker_result_shortlist="${JOB_DIR}/shortlist.json"
    _worker_result_eligible=false
    _worker_result_reason=terminal_outcome
    _worker_result_count=0

    if [ -r "${_worker_result_shortlist}" ]; then
        _worker_result_count=$("${STRATEGY_LAB_JQ}" -r \
            '.count // 0' "${_worker_result_shortlist}" 2>/dev/null || printf '%s\n' 0)
    fi

    if [ "${WORKER_FINAL_STATE}" != completed ] ||
       [ "${WORKER_FINAL_OUTCOME}" != SUCCESS ]; then
        _worker_result_reason=terminal_outcome
    elif [ "$("${STRATEGY_LAB_JQ}" -r '.target_type // ""' \
        "${_worker_result_status}")" != domain ]; then
        _worker_result_reason=domain_required
    elif ! "${STRATEGY_LAB_JQ}" -e '
        any(.stages[]; .number=="85" and .status=="PASS") and
        any(.stages[]; .number=="90" and .status=="PASS") and
        (.restoration.verified==true)
    ' "${_worker_result_status}" >/dev/null; then
        _worker_result_reason=restoration_required
    elif [ ! -r "${_worker_result_shortlist}" ] ||
         ! "${STRATEGY_LAB_JQ}" -e '
            (.count >= 3 and .count <= 5) and
            ((.items | length) == .count) and
            all(.items[];
                (.id | type == "string" and length > 0) and
                (.strategy | type == "string" and length > 0))
         ' "${_worker_result_shortlist}" >/dev/null; then
        _worker_result_reason=shortlist_size
    else
        _worker_result_eligible=true
        _worker_result_reason=eligible
    fi

    strategy_lab_state_transform "${JOB_ID}" '
        .circular_eligible=$eligible |
        .circular_eligibility_reason=$reason |
        .circular_candidate_count=$count
    ' --argjson eligible "${_worker_result_eligible}" \
      --arg reason "${_worker_result_reason}" \
      --argjson count "${_worker_result_count}"
}
