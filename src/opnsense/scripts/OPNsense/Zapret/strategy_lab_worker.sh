#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
WORKER_HOLD_SECONDS="${WORKER_HOLD_SECONDS:-1}"

set -eu
umask 022

for module in common state
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

case "${LANGUAGE}" in
    ru)
        CANCEL_MESSAGE='SKIPPED — отменено'
        PENDING_MESSAGE='SKIPPED — реализация ожидается'
        TARGET_MESSAGE="PASS — Цель: ${TARGET}; тип: домен; endpoints: ${TARGET}; режим: $([ "${MODE}" = extended ] && printf 'расширенный' || printf 'основной')."
        FINAL_MESSAGE='Strategy Lab: каркас асинхронного задания проверен; сетевые этапы пока не активированы.'
        ;;
    *)
        CANCEL_MESSAGE='SKIPPED — canseled'
        PENDING_MESSAGE='SKIPPED — implementation pending'
        TARGET_MESSAGE="PASS — Target: ${TARGET}; type: domain; endpoints: ${TARGET}; mode: ${MODE}."
        FINAL_MESSAGE='Strategy Lab job framework is ready; network stages are not active yet.'
        ;;
esac

worker_complete_cancel()
{
    strategy_lab_skip_unfinished "${JOB_ID}" "${CANCEL_MESSAGE}" || true
    strategy_lab_update_job "${JOB_ID}" completed PARTIAL 99 true "${CANCEL_MESSAGE}" || true
    strategy_lab_append_event "${JOB_ID}" 99 SKIPPED "${CANCEL_MESSAGE}" || true
    strategy_lab_clear_active_job "${JOB_ID}"
    exit 0
}

worker_abort()
{
    worker_complete_cancel
}
trap worker_abort HUP INT TERM

strategy_lab_update_job "${JOB_ID}" running '' 00 false ''
strategy_lab_update_stage "${JOB_ID}" 00 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 00 RUNNING 'Strategy Lab job started'

_elapsed=0
while [ "${_elapsed}" -lt "${WORKER_HOLD_SECONDS}" ]
do
    [ ! -e "${CANCEL_FILE}" ] || worker_complete_cancel
    sleep 1
    _elapsed=$((_elapsed + 1))
done

[ ! -e "${CANCEL_FILE}" ] || worker_complete_cancel

strategy_lab_update_stage "${JOB_ID}" 00 PASS "${TARGET_MESSAGE}"
strategy_lab_append_event "${JOB_ID}" 00 PASS "${TARGET_MESSAGE}"
strategy_lab_skip_unfinished "${JOB_ID}" "${PENDING_MESSAGE}"
strategy_lab_update_job "${JOB_ID}" completed PARTIAL 99 false "${FINAL_MESSAGE}"
strategy_lab_append_event "${JOB_ID}" 99 PASS "${FINAL_MESSAGE}"
strategy_lab_clear_active_job "${JOB_ID}"
exit 0
