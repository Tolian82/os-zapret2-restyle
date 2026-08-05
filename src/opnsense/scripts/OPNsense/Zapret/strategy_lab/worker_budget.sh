#!/bin/sh

worker_budget_now()
{
    if [ -n "${STRATEGY_LAB_NOW_EPOCH_FILE:-}" ] && [ -r "${STRATEGY_LAB_NOW_EPOCH_FILE}" ]; then
        IFS= read -r _wb_now < "${STRATEGY_LAB_NOW_EPOCH_FILE}" || return 1
    else
        _wb_now=$(date '+%s') || return 1
    fi
    case "${_wb_now}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    printf '%s\n' "${_wb_now}"
}

worker_budget_iso8601()
{
    _wb_epoch="$1"
    if _wb_iso=$(date -u -r "${_wb_epoch}" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null); then
        printf '%s\n' "${_wb_iso}"
        return 0
    fi
    date -u -d "@${_wb_epoch}" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null
}

worker_budget_min()
{
    if [ "$1" -le "$2" ]; then
        printf '%s\n' "$1"
    else
        printf '%s\n' "$2"
    fi
}

worker_budget_record_initial()
{
    _wb_status=$(strategy_lab_status_file "${JOB_ID}")
    _wb_tmp=$(mktemp "$(dirname "${_wb_status}")/.budget.XXXXXX") || return 1
    _wb_started_at=$(worker_budget_iso8601 "${WORKER_BUDGET_STARTED_EPOCH}") || return 1
    _wb_standard_deadline_at=$(worker_budget_iso8601 "${WORKER_STANDARD_DEADLINE_EPOCH}") || return 1
    _wb_deadline_at=$(worker_budget_iso8601 "${WORKER_OVERALL_DEADLINE_EPOCH}") || return 1

    "${STRATEGY_LAB_JQ}" \
        --arg started_at "${_wb_started_at}" \
        --arg standard_deadline_at "${_wb_standard_deadline_at}" \
        --arg deadline_at "${_wb_deadline_at}" \
        --argjson standard_budget_seconds "${STRATEGY_LAB_STANDARD_BUDGET}" \
        --argjson extended_budget_seconds "${STRATEGY_LAB_EXTENDED_BUDGET}" \
        --argjson search_budget_seconds "${WORKER_SEARCH_BUDGET_SECONDS}" \
        --argjson stage80_budget_seconds "${STRATEGY_LAB_STAGE80_TIMEOUT}" \
        '.started_at=$started_at |
         .standard_deadline_at=$standard_deadline_at |
         .deadline_at=$deadline_at |
         .standard_budget_seconds=$standard_budget_seconds |
         .extended_budget_seconds=$extended_budget_seconds |
         .search_budget_seconds=$search_budget_seconds |
         .stage80_budget_seconds=$stage80_budget_seconds' \
        "${_wb_status}" > "${_wb_tmp}" || {
            rm -f "${_wb_tmp}"
            return 1
        }
    chmod 0644 "${_wb_tmp}"
    mv -f "${_wb_tmp}" "${_wb_status}"
}

worker_budget_initialize()
{
    for _wb_value in "${STRATEGY_LAB_STANDARD_BUDGET}" \
        "${STRATEGY_LAB_EXTENDED_BUDGET}" "${STRATEGY_LAB_STAGE80_TIMEOUT}"
    do
        case "${_wb_value}" in
            ''|*[!0-9]*|0) return 1 ;;
        esac
    done

    WORKER_BUDGET_STARTED_EPOCH=$(worker_budget_now) || return 1
    WORKER_STANDARD_DEADLINE_EPOCH=$((WORKER_BUDGET_STARTED_EPOCH + STRATEGY_LAB_STANDARD_BUDGET))
    WORKER_SEARCH_BUDGET_SECONDS="${STRATEGY_LAB_STANDARD_BUDGET}"
    WORKER_OVERALL_DEADLINE_EPOCH="${WORKER_STANDARD_DEADLINE_EPOCH}"
    if [ "${MODE}" = extended ]; then
        WORKER_SEARCH_BUDGET_SECONDS=$((STRATEGY_LAB_STANDARD_BUDGET + STRATEGY_LAB_EXTENDED_BUDGET))
        WORKER_OVERALL_DEADLINE_EPOCH=$((WORKER_BUDGET_STARTED_EPOCH + WORKER_SEARCH_BUDGET_SECONDS))
    fi
    WORKER_STAGE80_DEADLINE_EPOCH=''
    export WORKER_BUDGET_STARTED_EPOCH WORKER_STANDARD_DEADLINE_EPOCH
    export WORKER_SEARCH_BUDGET_SECONDS WORKER_OVERALL_DEADLINE_EPOCH
    export WORKER_STAGE80_DEADLINE_EPOCH
    worker_budget_record_initial
}

worker_budget_record_stage80()
{
    _wb_status=$(strategy_lab_status_file "${JOB_ID}")
    _wb_tmp=$(mktemp "$(dirname "${_wb_status}")/.stage80-budget.XXXXXX") || return 1
    _wb_started_at=$(worker_budget_iso8601 "${WORKER_STAGE80_STARTED_EPOCH}") || return 1
    _wb_deadline_at=$(worker_budget_iso8601 "${WORKER_STAGE80_DEADLINE_EPOCH}") || return 1

    "${STRATEGY_LAB_JQ}" \
        --arg started_at "${_wb_started_at}" \
        --arg deadline_at "${_wb_deadline_at}" \
        '.stage80_started_at=$started_at | .stage80_deadline_at=$deadline_at' \
        "${_wb_status}" > "${_wb_tmp}" || {
            rm -f "${_wb_tmp}"
            return 1
        }
    chmod 0644 "${_wb_tmp}"
    mv -f "${_wb_tmp}" "${_wb_status}"
}

worker_budget_begin_stage80()
{
    WORKER_STAGE80_STARTED_EPOCH=$(worker_budget_now) || return 1
    [ "${WORKER_STAGE80_STARTED_EPOCH}" -lt "${WORKER_OVERALL_DEADLINE_EPOCH}" ] || return 1
    _wb_stage_deadline=$((WORKER_STAGE80_STARTED_EPOCH + STRATEGY_LAB_STAGE80_TIMEOUT))
    WORKER_STAGE80_DEADLINE_EPOCH=$(worker_budget_min \
        "${_wb_stage_deadline}" "${WORKER_OVERALL_DEADLINE_EPOCH}") || return 1
    export WORKER_STAGE80_STARTED_EPOCH WORKER_STAGE80_DEADLINE_EPOCH
    worker_budget_record_stage80
}

worker_budget_deadline_for()
{
    case "$1" in
        80)
            [ -n "${WORKER_STAGE80_DEADLINE_EPOCH:-}" ] || return 1
            printf '%s\n' "${WORKER_STAGE80_DEADLINE_EPOCH}"
            ;;
        85)
            printf '%s\n' "${WORKER_OVERALL_DEADLINE_EPOCH}"
            ;;
        *)
            printf '%s\n' "${WORKER_STANDARD_DEADLINE_EPOCH}"
            ;;
    esac
}

worker_budget_timeout_for()
{
    _wb_stage="$1"
    _wb_operation_limit="$2"
    case "${_wb_operation_limit}" in
        ''|*[!0-9]*|0) return 1 ;;
    esac
    _wb_deadline=$(worker_budget_deadline_for "${_wb_stage}") || return 1
    _wb_now=$(worker_budget_now) || return 1
    _wb_remaining=$((_wb_deadline - _wb_now))
    [ "${_wb_remaining}" -gt 0 ] || return 1
    worker_budget_min "${_wb_operation_limit}" "${_wb_remaining}"
}

worker_budget_require()
{
    worker_budget_timeout_for "$1" 2147483647 >/dev/null
}
