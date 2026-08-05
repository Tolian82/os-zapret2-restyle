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
            worker_skip_unfinished "${JOB_ID}" "${TARGET_ACCESSIBLE_SKIP}"
            worker_finish TARGET_ACCESSIBLE false
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

strategy_lab_update_stage "${JOB_ID}" 50 RUNNING ''
strategy_lab_append_event "${JOB_ID}" 50 RUNNING 'Running one isolated Zapret2 smoke candidate'
CANDIDATE_FILE="${JOB_DIR}/candidate-smoke.json"
if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_CANDIDATE_TIMEOUT}" \
    "${CANDIDATE_RUNNER}" "${JOB_ID}" "${ENDPOINTS_FILE}" "${CANDIDATE_FILE}"
then
    _strategy_lab_candidate_status=0
else
    _strategy_lab_candidate_status=$?
fi
[ "${_strategy_lab_candidate_status}" -ne 124 ] || worker_stage_timeout 50
[ -r "${CANDIDATE_FILE}" ] || worker_error 50 'Temporary candidate result was not produced.'
strategy_lab_set_candidate_smoke_result "${JOB_ID}" "${CANDIDATE_FILE}" ||
    worker_error 50 'Temporary candidate state could not be recorded.'
if [ "${_strategy_lab_candidate_status}" -ne 0 ]; then
    worker_error 50 'Temporary candidate runtime failed internally.'
fi
if "${STRATEGY_LAB_JQ}" -e '.all_pass == true' "${CANDIDATE_FILE}" >/dev/null; then
    CANDIDATE_MESSAGE="${CANDIDATE_RUNTIME_PASS_MESSAGE}"
else
    CANDIDATE_MESSAGE="${CANDIDATE_RUNTIME_FAIL_MESSAGE}"
fi
strategy_lab_update_stage "${JOB_ID}" 50 PASS "${CANDIDATE_MESSAGE}"
strategy_lab_append_event "${JOB_ID}" 50 PASS "${CANDIDATE_MESSAGE}"
[ ! -e "${CANCEL_FILE}" ] || worker_cancel

worker_run_search_stages
worker_finish_search
