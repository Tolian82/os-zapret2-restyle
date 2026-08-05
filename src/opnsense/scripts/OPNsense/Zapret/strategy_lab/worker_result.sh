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
        ru:standard:SUCCESS:*)
            printf 'SUCCESS — Основной поиск завершён; стабильных рабочих стратегий: %s.\n' "${_wrr_count}"
            ;;
        ru:extended:SUCCESS:*)
            printf 'SUCCESS — Расширенный поиск завершён; стабильных рабочих стратегий: %s.\n' "${_wrr_count}"
            ;;
        en:standard:SUCCESS:*)
            printf 'SUCCESS — Standard search completed with %s stable working strategies.\n' "${_wrr_count}"
            ;;
        en:extended:SUCCESS:*)
            printf 'SUCCESS — Extended search completed with %s stable working strategies.\n' "${_wrr_count}"
            ;;
        ru:standard:NO_CANDIDATE:*)
            printf '%s\n' 'NO_CANDIDATE — Основной поиск завершён; стабильная рабочая стратегия не найдена.'
            ;;
        ru:extended:NO_CANDIDATE:*)
            printf '%s\n' 'NO_CANDIDATE — Расширенный поиск завершён; стабильная рабочая стратегия не найдена.'
            ;;
        en:standard:NO_CANDIDATE:*)
            printf '%s\n' 'NO_CANDIDATE — Standard search completed; no stable working strategy was found.'
            ;;
        en:extended:NO_CANDIDATE:*)
            printf '%s\n' 'NO_CANDIDATE — Extended search completed; no stable working strategy was found.'
            ;;
        ru:*:TARGET_ACCESSIBLE:*)
            printf '%s\n' 'TARGET_ACCESSIBLE — Цель доступна без обхода; поиск стратегий не требуется.'
            ;;
        en:*:TARGET_ACCESSIBLE:*)
            printf '%s\n' 'TARGET_ACCESSIBLE — The target is accessible without bypass; strategy search is not required.'
            ;;
        ru:*:PARTIAL:true)
            printf '%s\n' 'PARTIAL — Тест отменён; результаты завершённых этапов сохранены.'
            ;;
        en:*:PARTIAL:true)
            printf '%s\n' 'PARTIAL — Test canceled; completed stage results were preserved.'
            ;;
        ru:*:PARTIAL:false)
            printf '%s\n' 'PARTIAL — Поиск завершён не полностью; доступные результаты сохранены.'
            ;;
        en:*:PARTIAL:false)
            printf '%s\n' 'PARTIAL — The search ended before completion; available results were preserved.'
            ;;
        ru:*:TIMEOUT:*)
            printf '%s\n' 'TIMEOUT — Лимит времени исчерпан; доступные результаты сохранены.'
            ;;
        en:*:TIMEOUT:*)
            printf '%s\n' 'TIMEOUT — The time limit was reached; available results were preserved.'
            ;;
        ru:*:ERROR:*)
            printf '%s\n' 'ERROR — Внутренняя ошибка Strategy Lab; доступные результаты сохранены.'
            ;;
        en:*:ERROR:*)
            printf '%s\n' 'ERROR — Strategy Lab failed internally; available results were preserved.'
            ;;
        ru:*:RESTORE_FAILED:*)
            printf '%s\n' 'RESTORE_FAILED — Исходное состояние Zapret2 восстановить не удалось.'
            ;;
        en:*:RESTORE_FAILED:*)
            printf '%s\n' 'RESTORE_FAILED — The original Zapret2 state could not be restored.'
            ;;
        *)
            printf 'ERROR — Unsupported Strategy Lab outcome: %s.\n' "${_wrr_outcome}"
            ;;
    esac
}

worker_finish_search()
{
    _wrr_count=$(worker_result_shortlist_count) ||
        worker_error 85 'Final shortlist result is unavailable or invalid.'
    if [ "${_wrr_count}" -gt 0 ]; then
        worker_finish SUCCESS false
    else
        worker_finish NO_CANDIDATE false
    fi
}
