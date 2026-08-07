#!/bin/sh

worker_result_terminal_state()
{
    case "$1" in
        ERROR|TIMEOUT|RESTORE_FAILED) printf '%s\n' error ;;
        *) printf '%s\n' completed ;;
    esac
}

worker_result_report_status()
{
    case "$1" in
        ERROR|TIMEOUT|RESTORE_FAILED) printf '%s\n' FAIL ;;
        *) printf '%s\n' PASS ;;
    esac
}

worker_result_shortlist_count()
{
    _wrr_shortlist="${JOB_DIR}/shortlist.json"
    [ -r "${_wrr_shortlist}" ] || return 1
    _wrr_count=$("${STRATEGY_LAB_JQ}" -r '.count // empty' "${_wrr_shortlist}") || return 1
    case "${_wrr_count}" in
        ''|*[!0-9]*) return 1 ;;
    esac
    printf '%s\n' "${_wrr_count}"
}

worker_result_message()
{
    _wrr_outcome="$1"
    _wrr_canceled="$2"
    _wrr_count=0
    case "${_wrr_outcome}" in
        SUCCESS) _wrr_count=$(worker_result_shortlist_count 2>/dev/null || printf '%s\n' 0) ;;
    esac

    case "${LANGUAGE}:${MODE}:${_wrr_outcome}:${_wrr_canceled}" in
        ru:standard:SUCCESS:*) printf 'SUCCESS — Основной поиск завершён; стабильных рабочих стратегий: %s.\n' "${_wrr_count}" ;;
        ru:extended:SUCCESS:*) printf 'SUCCESS — Расширенный поиск завершён; стабильных рабочих стратегий: %s.\n' "${_wrr_count}" ;;
        en:standard:SUCCESS:*) printf 'SUCCESS — Standard search completed with %s stable working strategies.\n' "${_wrr_count}" ;;
        en:extended:SUCCESS:*) printf 'SUCCESS — Extended search completed with %s stable working strategies.\n' "${_wrr_count}" ;;
        ru:standard:NO_CANDIDATE:*) printf '%s\n' 'NO_CANDIDATE — Основной поиск завершён; стабильная рабочая стратегия не найдена.' ;;
        ru:extended:NO_CANDIDATE:*) printf '%s\n' 'NO_CANDIDATE — Расширенный поиск завершён; стабильная рабочая стратегия не найдена.' ;;
        en:standard:NO_CANDIDATE:*) printf '%s\n' 'NO_CANDIDATE — Standard search completed; no stable working strategy was found.' ;;
        en:extended:NO_CANDIDATE:*) printf '%s\n' 'NO_CANDIDATE — Extended search completed; no stable working strategy was found.' ;;
        ru:*:TARGET_ACCESSIBLE:*) printf '%s\n' 'TARGET_ACCESSIBLE — Цель доступна без обхода; поиск стратегий не требуется.' ;;
        en:*:TARGET_ACCESSIBLE:*) printf '%s\n' 'TARGET_ACCESSIBLE — The target is accessible without bypass; strategy search is not required.' ;;
        ru:*:PARTIAL:true) printf '%s\n' 'PARTIAL — Тест отменён; результаты завершённых этапов сохранены.' ;;
        en:*:PARTIAL:true) printf '%s\n' 'PARTIAL — Test canceled; completed stage results were preserved.' ;;
        ru:*:PARTIAL:false) printf '%s\n' 'PARTIAL — Поиск завершён не полностью; доступные результаты сохранены.' ;;
        en:*:PARTIAL:false) printf '%s\n' 'PARTIAL — The search ended before completion; available results were preserved.' ;;
        ru:*:TIMEOUT:*) printf '%s\n' 'TIMEOUT — Лимит времени исчерпан; доступные результаты сохранены.' ;;
        en:*:TIMEOUT:*) printf '%s\n' 'TIMEOUT — The time limit was reached; available results were preserved.' ;;
        ru:*:ERROR:*) printf '%s\n' 'ERROR — Внутренняя ошибка Strategy Lab; доступные результаты сохранены.' ;;
        en:*:ERROR:*) printf '%s\n' 'ERROR — Strategy Lab failed internally; available results were preserved.' ;;
        ru:*:RESTORE_FAILED:*) printf '%s\n' 'RESTORE_FAILED — Исходное состояние Zapret2 восстановить не удалось.' ;;
        en:*:RESTORE_FAILED:*) printf '%s\n' 'RESTORE_FAILED — The original Zapret2 state could not be restored.' ;;
        *) printf 'ERROR — Unsupported Strategy Lab outcome: %s.\n' "${_wrr_outcome}" ;;
    esac
}

worker_result_set_circular_eligibility()
{
    _wrr_status=$(strategy_lab_status_file "${JOB_ID}")
    _wrr_shortlist="${JOB_DIR}/shortlist.json"
    _wrr_eligible=false
    _wrr_reason=terminal_outcome
    _wrr_count=0

    if [ -r "${_wrr_shortlist}" ]; then
        _wrr_count=$("${STRATEGY_LAB_JQ}" -r \
            'if has("circular_count") then .circular_count
             elif has("circular_items") then (.circular_items | length)
             else (.items | length) end' \
            "${_wrr_shortlist}") || _wrr_count=0
    fi

    if [ "${WORKER_FINAL_STATE}" != completed ] || [ "${WORKER_FINAL_OUTCOME}" != SUCCESS ]; then
        _wrr_reason=terminal_outcome
    elif [ "$("${STRATEGY_LAB_JQ}" -r '.target_type // ""' "${_wrr_status}")" != domain ]; then
        _wrr_reason=domain_required
    elif ! "${STRATEGY_LAB_JQ}" -e '
        any(.stages[]; .number=="85" and .status=="PASS") and
        any(.stages[]; .number=="90" and .status=="PASS") and
        (.restoration.verified==true)
    ' "${_wrr_status}" >/dev/null; then
        _wrr_reason=restoration_required
    elif [ ! -r "${_wrr_shortlist}" ] || ! "${STRATEGY_LAB_JQ}" -e '
        (.circular_items //
            [.items[] | . + {protocol:(.protocol // "tls13"),
                             circular_eligible:(.circular_eligible // true)}]) as $items |
        (($items | length) >= 3 and ($items | length) <= 5) and
        all($items[];
            .protocol=="tls13" and .circular_eligible==true and
            (.id | type == "string" and length > 0) and
            (.strategy | type == "string" and length > 0))
    ' "${_wrr_shortlist}" >/dev/null; then
        _wrr_reason=shortlist_size
    else
        _wrr_eligible=true
        _wrr_reason=eligible
    fi

    if command -v strategy_lab_state_transform >/dev/null 2>&1; then
        strategy_lab_state_transform "${JOB_ID}" '
            .circular_eligible=$eligible |
            .circular_eligibility_reason=$reason |
            .circular_candidate_count=$count
        ' --argjson eligible "${_wrr_eligible}" \
          --arg reason "${_wrr_reason}" \
          --argjson count "${_wrr_count}"
        return $?
    fi

    _wrr_tmp=$(mktemp "$(dirname "${_wrr_status}")/.circular-eligibility.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" \
        --argjson eligible "${_wrr_eligible}" \
        --arg reason "${_wrr_reason}" \
        --argjson count "${_wrr_count}" \
        '.circular_eligible=$eligible |
         .circular_eligibility_reason=$reason |
         .circular_candidate_count=$count' \
        "${_wrr_status}" > "${_wrr_tmp}" || {
            rm -f "${_wrr_tmp}"
            return 1
        }
    chmod 0644 "${_wrr_tmp}"
    mv -f "${_wrr_tmp}" "${_wrr_status}"
}

worker_finish_search()
{
    _wrr_count=$(worker_result_shortlist_count) || worker_error 85 'Final shortlist result is unavailable or invalid.'
    if [ "${_wrr_count}" -gt 0 ]; then
        worker_finish SUCCESS false
    else
        worker_finish NO_CANDIDATE false
    fi
}
