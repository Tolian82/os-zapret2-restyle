#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
WORKER_HOLD_SECONDS="${WORKER_HOLD_SECONDS:-1}"

set -eu
umask 022

for module in common state lifecycle
do
    module_path="${MODULE_DIR}/${module}.sh"
    [ -r "${module_path}" ] || {
        echo "ERROR: required Strategy Lab module is missing: ${module_path}" >&2
        exit 1
    }
    . "${module_path}"
done

JOB_ID="${1:-}"
strategy_lab_job_id_valid "${JOB_ID}" || {
    echo "ERROR: invalid Strategy Lab job id" >&2
    exit 64
}
strategy_lab_require_jq

STATUS_FILE=$(strategy_lab_status_file "${JOB_ID}")
CANCEL_FILE=$(strategy_lab_cancel_file "${JOB_ID}")
[ -r "${STATUS_FILE}" ] || {
    echo "ERROR: Strategy Lab job state is missing: ${JOB_ID}" >&2
    exit 1
}

LANGUAGE=$("${STRATEGY_LAB_JQ}" -r '.language' "${STATUS_FILE}")
TARGET=$("${STRATEGY_LAB_JQ}" -r '.target' "${STATUS_FILE}")
MODE=$("${STRATEGY_LAB_JQ}" -r '.mode' "${STATUS_FILE}")
WORKER_FINALIZING=0

case "${LANGUAGE}" in
    ru)
        CANCEL_MESSAGE='SKIPPED — отменено'
        PENDING_MESSAGE='SKIPPED — реализация ожидается'
        ERROR_SKIP_MESSAGE='SKIPPED — не выполнено'
        TARGET_MESSAGE="PASS — Цель: ${TARGET}; тип: домен; endpoints: ${TARGET}; режим: $([ "${MODE}" = extended ] && printf 'расширенный' || printf 'основной')."
        SNAPSHOT_RUNNING_MESSAGE='PASS — Исходное состояние Zapret2: служба запущена.'
        SNAPSHOT_STOPPED_MESSAGE='PASS — Исходное состояние Zapret2: служба остановлена.'
        SERVICE_STOPPED_MESSAGE='PASS — Служба Zapret2 остановлена'
        RESTORED_RUNNING_MESSAGE='PASS — Временные процессы и правила удалены; исходная служба Zapret2 снова запущена и полностью исправна.'
        RESTORED_STOPPED_MESSAGE='PASS — Временные процессы и правила удалены; Zapret2 оставлен в исходном остановленном состоянии.'
        RESTORED_NOOP_MESSAGE='PASS — Изменения состояния Zapret2 не выполнялись.'
        RESTORE_FAILED_MESSAGE='RESTORE_FAILED — Исходное состояние Zapret2 восстановить не удалось.'
        CANCEL_FINAL_MESSAGE='PARTIAL — Тест отменён; результаты завершённых этапов сохранены.'
        ERROR_FINAL_MESSAGE='ERROR — Этап lifecycle завершился ошибкой; доступные результаты сохранены.'
        PARTIAL_FINAL_MESSAGE='Strategy Lab: этапы lifecycle готовы; сетевые этапы пока не активированы.'
        ;;
    *)
        CANCEL_MESSAGE='SKIPPED — canseled'
        PENDING_MESSAGE='SKIPPED — implementation pending'
        ERROR_SKIP_MESSAGE='SKIPPED — not executed'
        TARGET_MESSAGE="PASS — Target: ${TARGET}; type: domain; endpoints: ${TARGET}; mode: ${MODE}."
        SNAPSHOT_RUNNING_MESSAGE='PASS — Initial Zapret2 state: service running.'
        SNAPSHOT_STOPPED_MESSAGE='PASS — Initial Zapret2 state: service stopped.'
        SERVICE_STOPPED_MESSAGE='PASS — The Zapret2 service has been stopped.'
        RESTORED_RUNNING_MESSAGE='PASS — Temporary processes and rules were removed; the original Zapret2 service was restarted and is fully operational.'
        RESTORED_STOPPED_MESSAGE='PASS — Temporary processes and rules were removed; Zapret2 was left in its original stopped state.'
        RESTORED_NOOP_MESSAGE='PASS — No Zapret2 service-state changes were made.'
        RESTORE_FAILED_MESSAGE='RESTORE_FAILED — The original Zapret2 state could not be restored.'
        CANCEL_FINAL_MESSAGE='PARTIAL — Test canceled; completed stage results were preserved.'
        ERROR_FINAL_MESSAGE='ERROR — The lifecycle stage failed; available results were preserved.'
        PARTIAL_FINAL_MESSAGE='Strategy Lab lifecycle stages are ready; network stages are not active yet.'
        ;;
esac

worker_restore()
{
    strategy_lab_update_stage "${JOB_ID}" 90 RUNNING '' || true
    strategy_lab_append_event "${JOB_ID}" 90 RUNNING 'Cleaning temporary state and restoring Zapret2' || true

    if strategy_lab_restore_initial_service_state; then
        case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
            RUNNING) _strategy_lab_restore_message="${RESTORED_RUNNING_MESSAGE}" ;;
            STOPPED) _strategy_lab_restore_message="${RESTORED_STOPPED_MESSAGE}" ;;
            *) _strategy_lab_restore_message="${RESTORED_NOOP_MESSAGE}" ;;
        esac
        strategy_lab_update_stage "${JOB_ID}" 90 PASS "${_strategy_lab_restore_message}" || true
        strategy_lab_append_event "${JOB_ID}" 90 PASS "${_strategy_lab_restore_message}" || true
        return 0
    fi

    strategy_lab_update_stage "${JOB_ID}" 90 FAIL "${RESTORE_FAILED_MESSAGE}" || true
    strategy_lab_append_event "${JOB_ID}" 90 FAIL "${RESTORE_FAILED_MESSAGE}" || true
    return 1
}

worker_finish()
{
    WORKER_FINAL_OUTCOME="$1"
    WORKER_FINAL_CANCELED="$2"
    WORKER_FINAL_MESSAGE="$3"

    WORKER_FINALIZING=1
    if ! worker_restore; then
        WORKER_FINAL_OUTCOME='RESTORE_FAILED'
        WORKER_FINAL_MESSAGE="${RESTORE_FAILED_MESSAGE}"
        strategy_lab_update_stage "${JOB_ID}" 99 FAIL "${WORKER_FINAL_MESSAGE}" || true
        strategy_lab_append_event "${JOB_ID}" 99 FAIL "${WORKER_FINAL_MESSAGE}" || true
    else
        strategy_lab_update_stage "${JOB_ID}" 99 PASS "${WORKER_FINAL_MESSAGE}" || true
        strategy_lab_append_event "${JOB_ID}" 99 PASS "${WORKER_FINAL_MESSAGE}" || true
    fi

    strategy_lab_update_job "${JOB_ID}" completed "${WORKER_FINAL_OUTCOME}" 99 \
        "${WORKER_FINAL_CANCELED}" "${WORKER_FINAL_MESSAGE}" || true
    strategy_lab_clear_active_job "${JOB_ID}"
    exit 0
}

worker_cancel()
{
    [ "${WORKER_FINALIZING}" -eq 0 ] || exit 0
    strategy_lab_skip_unfinished "${JOB_ID}" "${CANCEL_MESSAGE}" || true
    worker_finish PARTIAL true "${CANCEL_FINAL_MESSAGE}"
}

worker_error()
{
    _strategy_lab_stage="$1"
    _strategy_lab_message="$2"
    strategy_lab_update_stage "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    strategy_lab_append_event "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    strategy_lab_skip_unfinished "${JOB_ID}" "${ERROR_SKIP_MESSAGE}" || true
    worker_finish ERROR false "${ERROR_FINAL_MESSAGE}"
}

trap worker_cancel HUP INT TERM

strategy_lab_update_job "${JOB_ID}" running '' 00 false ''
strategy_lab_update_stage "${JOB_ID}" 00 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 00 RUNNING 'Strategy Lab job started'
[ ! -e "${CANCEL_FILE}" ] || worker_cancel
strategy_lab_update_stage "${JOB_ID}" 00 PASS "${TARGET_MESSAGE}"
strategy_lab_append_event "${JOB_ID}" 00 PASS "${TARGET_MESSAGE}"

strategy_lab_update_stage "${JOB_ID}" 10 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 10 RUNNING 'Capturing the initial Zapret2 lifecycle state'

if [ "${STRATEGY_LAB_LIFECYCLE_LOCK_FAILED:-0}" = 1 ]; then
    worker_error 10 'Strategy Lab could not acquire the shared Zapret2 lifecycle lock.'
fi

if ! strategy_lab_capture_initial_service_state; then
    STRATEGY_LAB_INITIAL_SERVICE_STATE=''
    worker_error 10 'Zapret2 is in an incomplete or unknown state.'
fi
strategy_lab_set_initial_service_state "${JOB_ID}" "${STRATEGY_LAB_INITIAL_SERVICE_STATE}"
case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
    RUNNING) _strategy_lab_snapshot_message="${SNAPSHOT_RUNNING_MESSAGE}" ;;
    STOPPED) _strategy_lab_snapshot_message="${SNAPSHOT_STOPPED_MESSAGE}" ;;
    *) worker_error 10 'Zapret2 is in an incomplete or unknown state.' ;;
esac
strategy_lab_update_stage "${JOB_ID}" 10 PASS "${_strategy_lab_snapshot_message}"
strategy_lab_append_event "${JOB_ID}" 10 PASS "${_strategy_lab_snapshot_message}"
[ ! -e "${CANCEL_FILE}" ] || worker_cancel

strategy_lab_update_stage "${JOB_ID}" 20 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 20 RUNNING 'Stopping and verifying the normal Zapret2 service'
if ! strategy_lab_stop_normal_service; then
    worker_error 20 'The normal Zapret2 service could not be stopped and verified.'
fi
strategy_lab_update_stage "${JOB_ID}" 20 PASS "${SERVICE_STOPPED_MESSAGE}"
strategy_lab_append_event "${JOB_ID}" 20 PASS "${SERVICE_STOPPED_MESSAGE}"

_elapsed=0
while [ "${_elapsed}" -lt "${WORKER_HOLD_SECONDS}" ]
do
    [ ! -e "${CANCEL_FILE}" ] || worker_cancel
    sleep 1
    _elapsed=$((_elapsed + 1))
done
[ ! -e "${CANCEL_FILE}" ] || worker_cancel

strategy_lab_skip_unfinished "${JOB_ID}" "${PENDING_MESSAGE}"
worker_finish PARTIAL false "${PARTIAL_FINAL_MESSAGE}"
