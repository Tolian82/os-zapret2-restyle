#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
WORKER_HOLD_SECONDS="${WORKER_HOLD_SECONDS:-0}"
PROBE_RUNNER="${PROBE_RUNNER:-${SCRIPT_DIR}/strategy_lab_probe_runner.sh}"
STRATEGY_LAB_STAGE30_TIMEOUT="${STRATEGY_LAB_STAGE30_TIMEOUT:-6}"
STRATEGY_LAB_STAGE40_TIMEOUT="${STRATEGY_LAB_STAGE40_TIMEOUT:-5}"

set -eu
umask 022

for module in common state lifecycle target request result probe
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
[ -x "${PROBE_RUNNER}" ] || {
    echo "ERROR: Strategy Lab probe runner is unavailable: ${PROBE_RUNNER}" >&2
    exit 1
}

STATUS_FILE=$(strategy_lab_status_file "${JOB_ID}")
CANCEL_FILE=$(strategy_lab_cancel_file "${JOB_ID}")
JOB_DIR=$(strategy_lab_job_dir "${JOB_ID}")
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
        PREREQUISITE_MESSAGE='SKIPPED — предварительная проверка не пройдена'
        TARGET_ACCESSIBLE_SKIP='SKIPPED — цель доступна без обхода'
        ERROR_SKIP_MESSAGE='SKIPPED — не выполнено'
        TIMEOUT_SKIP_MESSAGE='SKIPPED — лимит времени исчерпан'
        STAGE_TIMEOUT_MESSAGE='TIMEOUT — превышен лимит этапа.'
        TIMEOUT_FINAL_MESSAGE='TIMEOUT — Тест остановлен по лимиту времени; доступные результаты сохранены.'
        SNAPSHOT_RUNNING_MESSAGE='PASS — Исходное состояние Zapret2: служба запущена.'
        SNAPSHOT_STOPPED_MESSAGE='PASS — Исходное состояние Zapret2: служба остановлена.'
        SERVICE_STOPPED_MESSAGE='PASS — Служба Zapret2 остановлена'
        NETWORK_IPV4_ONLY_MESSAGE='PASS — IPv4 доступен; IPv6 недоступен; QUIC/IPv4 закрыт; проверки IPv6 и QUIC исключены.'
        NETWORK_FULL_MESSAGE='PASS — IPv4, IPv6 и QUIC/IPv4 доступны.'
        NETWORK_NO_IPV6_MESSAGE='PASS — IPv4 и QUIC/IPv4 доступны; IPv6 недоступен; проверки IPv6 исключены.'
        NETWORK_NO_QUIC_MESSAGE='PASS — IPv4 и IPv6 доступны; QUIC/IPv4 закрыт; проверки QUIC исключены.'
        NETWORK_IPV4_FAILED_MESSAGE='FAIL — Контрольное IPv4-подключение недоступно; тестирование стратегий не выполнялось.'
        BASELINE_TLS_FAILED_MESSAGE='PASS — DNS: OK; прямое TLS 1.3-соединение не установлено.'
        BASELINE_DNS_FAILED_MESSAGE='FAIL — DNS-разрешение обязательного endpoint не выполнено.'
        BASELINE_ACCESSIBLE_MESSAGE='PASS — Все обязательные endpoints доступны без Zapret2.'
        BASELINE_IP_FAILED_MESSAGE='PASS — Прямое TCP/443-подключение к IP-цели не установлено.'
        RESTORED_RUNNING_MESSAGE='PASS — Временные процессы и правила удалены; исходная служба Zapret2 снова запущена и полностью исправна.'
        RESTORED_STOPPED_MESSAGE='PASS — Временные процессы и правила удалены; Zapret2 оставлен в исходном остановленном состоянии.'
        RESTORED_NOOP_MESSAGE='PASS — Изменения состояния Zapret2 не выполнялись.'
        RESTORE_FAILED_MESSAGE='RESTORE_FAILED — Исходное состояние Zapret2 восстановить не удалось.'
        CANCEL_FINAL_MESSAGE='PARTIAL — Тест отменён; результаты завершённых этапов сохранены.'
        ERROR_FINAL_MESSAGE='ERROR — Этап Strategy Lab завершился внутренней ошибкой; доступные результаты сохранены.'
        PREREQUISITE_FINAL_MESSAGE='PARTIAL — Предварительная проверка завершилась отрицательно; доступные результаты сохранены.'
        TARGET_ACCESSIBLE_FINAL_MESSAGE='TARGET_ACCESSIBLE — Цель доступна без обхода; поиск стратегий не требуется.'
        PARTIAL_FINAL_MESSAGE='Strategy Lab: сетевые предварительные проверки готовы; этапы поиска стратегий пока не активированы.'
        ;;
    *)
        CANCEL_MESSAGE='SKIPPED — canseled'
        PENDING_MESSAGE='SKIPPED — implementation pending'
        PREREQUISITE_MESSAGE='SKIPPED — prerequisite failed'
        TARGET_ACCESSIBLE_SKIP='SKIPPED — target accessible without bypass'
        ERROR_SKIP_MESSAGE='SKIPPED — not executed'
        TIMEOUT_SKIP_MESSAGE='SKIPPED — time budget exhausted'
        STAGE_TIMEOUT_MESSAGE='TIMEOUT — stage time limit exceeded.'
        TIMEOUT_FINAL_MESSAGE='TIMEOUT — The test reached its time limit; available results were preserved.'
        SNAPSHOT_RUNNING_MESSAGE='PASS — Initial Zapret2 state: service running.'
        SNAPSHOT_STOPPED_MESSAGE='PASS — Initial Zapret2 state: service stopped.'
        SERVICE_STOPPED_MESSAGE='PASS — The Zapret2 service has been stopped.'
        NETWORK_IPV4_ONLY_MESSAGE='PASS — IPv4 is available; IPv6 is unavailable; QUIC/IPv4 is blocked; IPv6 and QUIC tests have been excluded.'
        NETWORK_FULL_MESSAGE='PASS — IPv4, IPv6, and QUIC/IPv4 are available.'
        NETWORK_NO_IPV6_MESSAGE='PASS — IPv4 and QUIC/IPv4 are available; IPv6 is unavailable; IPv6 tests have been excluded.'
        NETWORK_NO_QUIC_MESSAGE='PASS — IPv4 and IPv6 are available; QUIC/IPv4 is blocked; QUIC tests have been excluded.'
        NETWORK_IPV4_FAILED_MESSAGE='FAIL — The IPv4 control connection is unavailable; strategy testing was not performed.'
        BASELINE_TLS_FAILED_MESSAGE='PASS — DNS: OK; direct TLS 1.3 connection failed.'
        BASELINE_DNS_FAILED_MESSAGE='FAIL — DNS resolution failed for a required endpoint.'
        BASELINE_ACCESSIBLE_MESSAGE='PASS — All required endpoints are accessible without Zapret2.'
        BASELINE_IP_FAILED_MESSAGE='PASS — Direct TCP/443 connection to the IP target failed.'
        RESTORED_RUNNING_MESSAGE='PASS — Temporary processes and rules were removed; the original Zapret2 service was restarted and is fully operational.'
        RESTORED_STOPPED_MESSAGE='PASS — Temporary processes and rules were removed; Zapret2 was left in its original stopped state.'
        RESTORED_NOOP_MESSAGE='PASS — No Zapret2 service-state changes were made.'
        RESTORE_FAILED_MESSAGE='RESTORE_FAILED — The original Zapret2 state could not be restored.'
        CANCEL_FINAL_MESSAGE='PARTIAL — Test canceled; completed stage results were preserved.'
        ERROR_FINAL_MESSAGE='ERROR — A Strategy Lab stage failed internally; available results were preserved.'
        PREREQUISITE_FINAL_MESSAGE='PARTIAL — A prerequisite check failed; available results were preserved.'
        TARGET_ACCESSIBLE_FINAL_MESSAGE='TARGET_ACCESSIBLE — The target is accessible without bypass; strategy search is not required.'
        PARTIAL_FINAL_MESSAGE='Strategy Lab network prechecks are ready; strategy-search stages are not active yet.'
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

worker_prerequisite_failed()
{
    _strategy_lab_stage="$1"
    _strategy_lab_message="$2"
    strategy_lab_update_stage "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    strategy_lab_append_event "${JOB_ID}" "${_strategy_lab_stage}" FAIL "${_strategy_lab_message}" || true
    strategy_lab_skip_unfinished "${JOB_ID}" "${PREREQUISITE_MESSAGE}" || true
    worker_finish PARTIAL false "${PREREQUISITE_FINAL_MESSAGE}"
}

worker_stage_timeout()
{
    _strategy_lab_stage="$1"
    strategy_lab_update_stage "${JOB_ID}" "${_strategy_lab_stage}" TIMEOUT "${STAGE_TIMEOUT_MESSAGE}" || true
    strategy_lab_append_event "${JOB_ID}" "${_strategy_lab_stage}" TIMEOUT "${STAGE_TIMEOUT_MESSAGE}" || true
    strategy_lab_skip_unfinished "${JOB_ID}" "${TIMEOUT_SKIP_MESSAGE}" || true
    worker_finish TIMEOUT false "${TIMEOUT_FINAL_MESSAGE}"
}

trap worker_cancel HUP INT TERM

strategy_lab_update_job "${JOB_ID}" running '' 00 false ''
strategy_lab_update_stage "${JOB_ID}" 00 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 00 RUNNING 'Validating target and resolving required endpoints'

TARGET=$(strategy_lab_normalize_target "${TARGET}" 2>/dev/null || true)
[ -n "${TARGET}" ] || worker_error 00 'Invalid Strategy Lab target.'
TARGET_TYPE=$(strategy_lab_target_type "${TARGET}" 2>/dev/null || true)
[ -n "${TARGET_TYPE}" ] || worker_error 00 'Strategy Lab target type could not be determined.'
ENDPOINTS_FILE="${JOB_DIR}/endpoints.txt"
strategy_lab_write_endpoints "${TARGET}" "${TARGET_TYPE}" "${ENDPOINTS_FILE}" ||
    worker_error 00 'Strategy Lab endpoints could not be prepared.'
strategy_lab_set_target_contract "${JOB_ID}" "${TARGET}" "${TARGET_TYPE}" "${ENDPOINTS_FILE}" ||
    worker_error 00 'Strategy Lab target state could not be recorded.'
ENDPOINTS_CSV=$(strategy_lab_endpoints_csv "${ENDPOINTS_FILE}")
case "${LANGUAGE}:${TARGET_TYPE}:${MODE}" in
    ru:domain:standard) TARGET_MESSAGE="PASS — Цель: ${TARGET}; тип: домен; endpoints: ${ENDPOINTS_CSV}; режим: основной." ;;
    ru:domain:extended) TARGET_MESSAGE="PASS — Цель: ${TARGET}; тип: домен; endpoints: ${ENDPOINTS_CSV}; режим: расширенный." ;;
    ru:ip:standard) TARGET_MESSAGE="PASS — Цель: ${TARGET}; тип: IP; endpoints: ${ENDPOINTS_CSV}; режим: основной." ;;
    ru:ip:extended) TARGET_MESSAGE="PASS — Цель: ${TARGET}; тип: IP; endpoints: ${ENDPOINTS_CSV}; режим: расширенный." ;;
    en:domain:*) TARGET_MESSAGE="PASS — Target: ${TARGET}; type: domain; endpoints: ${ENDPOINTS_CSV}; mode: ${MODE}." ;;
    en:ip:*) TARGET_MESSAGE="PASS — Target: ${TARGET}; type: IP; endpoints: ${ENDPOINTS_CSV}; mode: ${MODE}." ;;
esac
strategy_lab_update_stage "${JOB_ID}" 00 PASS "${TARGET_MESSAGE}"
strategy_lab_append_event "${JOB_ID}" 00 PASS "${TARGET_MESSAGE}"
[ ! -e "${CANCEL_FILE}" ] || worker_cancel

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
[ ! -e "${CANCEL_FILE}" ] || worker_cancel

_hold_elapsed=0
while [ "${_hold_elapsed}" -lt "${WORKER_HOLD_SECONDS}" ]
do
    [ ! -e "${CANCEL_FILE}" ] || worker_cancel
    sleep 1
    _hold_elapsed=$((_hold_elapsed + 1))
done

strategy_lab_update_stage "${JOB_ID}" 30 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 30 RUNNING 'Checking IPv4, IPv6, and QUIC capabilities'
NETWORK_FILE="${JOB_DIR}/network.json"
if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE30_TIMEOUT}" \
    "${PROBE_RUNNER}" network "${NETWORK_FILE}" "${JOB_DIR}"
then
    _strategy_lab_network_status=0
else
    _strategy_lab_network_status=$?
fi
[ "${_strategy_lab_network_status}" -ne 124 ] || worker_stage_timeout 30
[ -r "${NETWORK_FILE}" ] || worker_error 30 'Network capability result was not produced.'
strategy_lab_set_network_capabilities "${JOB_ID}" "${NETWORK_FILE}" ||
    worker_error 30 'Network capability state could not be recorded.'
case "${_strategy_lab_network_status}" in
    0)
        IPV6_STATE=$("${STRATEGY_LAB_JQ}" -r '.ipv6' "${NETWORK_FILE}")
        QUIC_STATE=$("${STRATEGY_LAB_JQ}" -r '.quic_ipv4' "${NETWORK_FILE}")
        case "${IPV6_STATE}:${QUIC_STATE}" in
            unavailable:closed) NETWORK_MESSAGE="${NETWORK_IPV4_ONLY_MESSAGE}" ;;
            available:available) NETWORK_MESSAGE="${NETWORK_FULL_MESSAGE}" ;;
            unavailable:available) NETWORK_MESSAGE="${NETWORK_NO_IPV6_MESSAGE}" ;;
            available:closed) NETWORK_MESSAGE="${NETWORK_NO_QUIC_MESSAGE}" ;;
            *) worker_error 30 'Unexpected network capability classification.' ;;
        esac
        strategy_lab_update_stage "${JOB_ID}" 30 PASS "${NETWORK_MESSAGE}"
        strategy_lab_append_event "${JOB_ID}" 30 PASS "${NETWORK_MESSAGE}"
        ;;
    2)
        worker_prerequisite_failed 30 "${NETWORK_IPV4_FAILED_MESSAGE}"
        ;;
    *)
        worker_error 30 'Network capability precheck failed internally.'
        ;;
esac
[ ! -e "${CANCEL_FILE}" ] || worker_cancel

strategy_lab_update_stage "${JOB_ID}" 40 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 40 RUNNING 'Testing the clean target baseline without Zapret2'
BASELINE_FILE="${JOB_DIR}/baseline.json"
if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_STAGE40_TIMEOUT}" \
    "${PROBE_RUNNER}" baseline \
    "${TARGET}" "${TARGET_TYPE}" "${ENDPOINTS_FILE}" \
    "${NETWORK_FILE}" "${JOB_DIR}" "${BASELINE_FILE}"
then
    _strategy_lab_baseline_status=0
else
    _strategy_lab_baseline_status=$?
fi
[ "${_strategy_lab_baseline_status}" -ne 124 ] || worker_stage_timeout 40
[ -r "${BASELINE_FILE}" ] || worker_error 40 'Clean baseline result was not produced.'
strategy_lab_set_baseline_result "${JOB_ID}" "${BASELINE_FILE}" ||
    worker_error 40 'Clean baseline state could not be recorded.'
case "${_strategy_lab_baseline_status}" in
    0)
        if strategy_lab_baseline_all_accessible "${BASELINE_FILE}"; then
            strategy_lab_update_stage "${JOB_ID}" 40 PASS "${BASELINE_ACCESSIBLE_MESSAGE}"
            strategy_lab_append_event "${JOB_ID}" 40 PASS "${BASELINE_ACCESSIBLE_MESSAGE}"
            strategy_lab_skip_unfinished "${JOB_ID}" "${TARGET_ACCESSIBLE_SKIP}"
            worker_finish TARGET_ACCESSIBLE false "${TARGET_ACCESSIBLE_FINAL_MESSAGE}"
        fi
        _strategy_lab_total=$(strategy_lab_baseline_total_count "${BASELINE_FILE}")
        _strategy_lab_failed=$(strategy_lab_baseline_failed_count "${BASELINE_FILE}")
        if [ "${TARGET_TYPE}" = ip ]; then
            BASELINE_MESSAGE="${BASELINE_IP_FAILED_MESSAGE}"
        elif [ "${_strategy_lab_failed}" -eq "${_strategy_lab_total}" ]; then
            BASELINE_MESSAGE="${BASELINE_TLS_FAILED_MESSAGE}"
        elif [ "${LANGUAGE}" = ru ]; then
            BASELINE_MESSAGE="PASS — Чистый TLS 1.3 baseline: недоступно ${_strategy_lab_failed} из ${_strategy_lab_total} обязательных endpoints."
        else
            BASELINE_MESSAGE="PASS — Clean TLS 1.3 baseline: ${_strategy_lab_failed} of ${_strategy_lab_total} required endpoints are unavailable."
        fi
        strategy_lab_update_stage "${JOB_ID}" 40 PASS "${BASELINE_MESSAGE}"
        strategy_lab_append_event "${JOB_ID}" 40 PASS "${BASELINE_MESSAGE}"
        ;;
    2)
        worker_prerequisite_failed 40 "${BASELINE_DNS_FAILED_MESSAGE}"
        ;;
    *)
        worker_error 40 'Clean baseline probe failed internally.'
        ;;
esac
[ ! -e "${CANCEL_FILE}" ] || worker_cancel

strategy_lab_skip_unfinished "${JOB_ID}" "${PENDING_MESSAGE}"
worker_finish PARTIAL false "${PARTIAL_FINAL_MESSAGE}"
