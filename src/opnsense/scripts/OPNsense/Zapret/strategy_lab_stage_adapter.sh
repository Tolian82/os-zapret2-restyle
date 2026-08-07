#!/bin/sh

set -eu
umask 022

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
ACTION="${1:-}"
JOB_ID="${2:-}"
RESULT_FILE="${STRATEGY_LAB_STAGE_RESULT_FILE:-}"
OPERATION_TIMEOUT="${STRATEGY_LAB_OPERATION_TIMEOUT:-}"

case "${JOB_ID}" in job.*) ;; *) exit 64 ;; esac
[ -n "${RESULT_FILE}" ] || exit 64

for module in common state firewall runtime candidate lifecycle target request result probe family expansion stability profile extended quic udp udp_input preflight
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 70
    . "${path}"
done
strategy_lab_require_jq

JOB_DIR=$(strategy_lab_job_dir "${JOB_ID}")
STATUS_FILE=$(strategy_lab_status_file "${JOB_ID}")
CANCEL_FILE=$(strategy_lab_cancel_file "${JOB_ID}")
[ -r "${STATUS_FILE}" ] || exit 70
LANGUAGE=$("${STRATEGY_LAB_JQ}" -r '.language // "en"' "${STATUS_FILE}")
MODE=$("${STRATEGY_LAB_JQ}" -r '.mode // "standard"' "${STATUS_FILE}")
TARGET=$("${STRATEGY_LAB_JQ}" -r '.target // ""' "${STATUS_FILE}")
TARGET_TYPE=$("${STRATEGY_LAB_JQ}" -r '.target_type // ""' "${STATUS_FILE}")
ENDPOINTS_FILE="${JOB_DIR}/endpoints.txt"
PROBE_RUNNER="${PROBE_RUNNER:-${SCRIPT_DIR}/strategy_lab_probe_runner.sh}"
CANDIDATE_RUNNER="${CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_family_runner.sh}"
EXPANSION_RUNNER="${EXPANSION_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_expansion_runner.sh}"
STABILITY_RUNNER="${STABILITY_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_stability_runner.sh}"
EXTENDED_RUNNER="${EXTENDED_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_extended_runner.sh}"
QUIC_RUNNER="${QUIC_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_quic_runner.sh}"
UDP_RUNNER="${UDP_RUNNER:-${SCRIPT_DIR}/strategy_lab_cancellable_udp_runner.sh}"
STRATEGY_LAB_TIMEOUT_BIN="${STRATEGY_LAB_TIMEOUT_BIN:-/usr/bin/timeout}"

emit_result()
{
    _kind="$1"
    _message="${2:-}"
    _initial_state="${3:-}"
    "${STRATEGY_LAB_JQ}" -nc \
        --arg kind "${_kind}" --arg message "${_message}" --arg initial_state "${_initial_state}" \
        '{kind:$kind,message:$message,initial_state:$initial_state}' > "${RESULT_FILE}"
    chmod 0644 "${RESULT_FILE}"
}

pass(){ emit_result pass "$1" "${2:-}"; exit 0; }
error(){ emit_result error "$1"; exit 0; }
prerequisite(){ emit_result prerequisite "$1"; exit 0; }
accessible(){ emit_result accessible "$1"; exit 0; }
timeout_result(){ emit_result timeout ''; exit 124; }
cancel_result(){ emit_result cancel ''; exit 125; }

run_timed()
{
    [ -n "${OPERATION_TIMEOUT}" ] || return 64
    case "${OPERATION_TIMEOUT}" in ''|*[!0-9]*|0) return 64 ;; esac
    if "${STRATEGY_LAB_TIMEOUT_BIN}" "${OPERATION_TIMEOUT}" "$@"; then
        _status=0
    else
        _status=$?
    fi
    [ "${_status}" -ne 124 ] || timeout_result
    [ "${_status}" -ne 125 ] || cancel_result
    return "${_status}"
}

load_lifecycle_context()
{
    STRATEGY_LAB_INITIAL_SERVICE_STATE=$("${STRATEGY_LAB_JQ}" -r '.initial_service_state // ""' "${STATUS_FILE}")
    STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE=$("${STRATEGY_LAB_JQ}" -r '.lifecycle_snapshot.source // ""' "${STATUS_FILE}")
    export STRATEGY_LAB_INITIAL_SERVICE_STATE STRATEGY_LAB_INITIAL_EVIDENCE_SOURCE
}

case "${ACTION}" in
    00)
        strategy_lab_preflight_cleanup "${JOB_ID}" ||
            error 'Strategy Lab could not remove temporary residue from an earlier run.'
        TARGET=$(strategy_lab_normalize_target "${TARGET}" 2>/dev/null || true)
        [ -n "${TARGET}" ] || error 'Invalid Strategy Lab target.'
        TARGET_TYPE=$(strategy_lab_target_type "${TARGET}" 2>/dev/null || true)
        [ -n "${TARGET_TYPE}" ] || error 'Strategy Lab target type could not be determined.'
        strategy_lab_write_endpoints "${TARGET}" "${TARGET_TYPE}" "${ENDPOINTS_FILE}" ||
            error 'Strategy Lab endpoints could not be prepared.'
        strategy_lab_set_target_contract "${JOB_ID}" "${TARGET}" "${TARGET_TYPE}" "${ENDPOINTS_FILE}" ||
            error 'Strategy Lab target state could not be recorded.'
        ENDPOINTS_CSV=$(strategy_lab_endpoints_csv "${ENDPOINTS_FILE}")
        case "${LANGUAGE}:${TARGET_TYPE}:${MODE}" in
            ru:domain:standard) msg="PASS — Цель: ${TARGET}; тип: домен; endpoints: ${ENDPOINTS_CSV}; режим: основной." ;;
            ru:domain:extended) msg="PASS — Цель: ${TARGET}; тип: домен; endpoints: ${ENDPOINTS_CSV}; режим: расширенный." ;;
            ru:ip:standard) msg="PASS — Цель: ${TARGET}; тип: IP; endpoints: ${ENDPOINTS_CSV}; режим: основной." ;;
            ru:ip:extended) msg="PASS — Цель: ${TARGET}; тип: IP; endpoints: ${ENDPOINTS_CSV}; режим: расширенный." ;;
            en:domain:*) msg="PASS — Target: ${TARGET}; type: domain; endpoints: ${ENDPOINTS_CSV}; mode: ${MODE}." ;;
            en:ip:*) msg="PASS — Target: ${TARGET}; type: IP; endpoints: ${ENDPOINTS_CSV}; mode: ${MODE}." ;;
            *) error 'Strategy Lab target presentation could not be classified.' ;;
        esac
        pass "${msg}"
        ;;
    10)
        if [ "${STRATEGY_LAB_LIFECYCLE_LOCK_FAILED:-0}" = 1 ]; then
            error 'Strategy Lab could not acquire the shared Zapret2 lifecycle lock.'
        fi
        if ! strategy_lab_capture_initial_service_state; then
            error 'Zapret2 is in an incomplete or unknown state.'
        fi
        strategy_lab_set_initial_service_state "${JOB_ID}" "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" ||
            error 'Initial Zapret2 state could not be recorded.'
        case "${STRATEGY_LAB_INITIAL_SERVICE_STATE}" in
            RUNNING)
                msg='PASS — Initial Zapret2 state: service running.'
                [ "${LANGUAGE}" != ru ] || msg='PASS — Исходное состояние Zapret2: служба запущена.'
                ;;
            STOPPED)
                msg='PASS — Initial Zapret2 state: service stopped.'
                [ "${LANGUAGE}" != ru ] || msg='PASS — Исходное состояние Zapret2: служба остановлена.'
                ;;
            *) error 'Zapret2 is in an incomplete or unknown state.' ;;
        esac
        pass "${msg}" "${STRATEGY_LAB_INITIAL_SERVICE_STATE}"
        ;;
    20)
        load_lifecycle_context
        strategy_lab_stop_normal_service ||
            error 'The normal Zapret2 service could not be stopped and verified.'
        msg='PASS — The Zapret2 service has been stopped.'
        [ "${LANGUAGE}" != ru ] || msg='PASS — Служба Zapret2 остановлена'
        pass "${msg}"
        ;;
    30)
        NETWORK_FILE="${JOB_DIR}/network.json"
        if run_timed "${PROBE_RUNNER}" network "${NETWORK_FILE}" "${JOB_DIR}"; then status=0; else status=$?; fi
        [ -r "${NETWORK_FILE}" ] || error 'Network capability result was not produced.'
        strategy_lab_set_network_capabilities "${JOB_ID}" "${NETWORK_FILE}" ||
            error 'Network capability state could not be recorded.'
        case "${status}" in
            0)
                IPV6_STATE=$("${STRATEGY_LAB_JQ}" -r '.ipv6' "${NETWORK_FILE}")
                QUIC_STATE=$("${STRATEGY_LAB_JQ}" -r '.quic_ipv4' "${NETWORK_FILE}")
                if [ "${LANGUAGE}" = ru ]; then
                    case "${IPV6_STATE}:${QUIC_STATE}" in
                        unavailable:closed) msg='PASS — IPv4 доступен; IPv6 недоступен; QUIC/IPv4 закрыт; проверки IPv6 и QUIC исключены.' ;;
                        available:available) msg='PASS — IPv4, IPv6 и QUIC/IPv4 доступны.' ;;
                        unavailable:available) msg='PASS — IPv4 и QUIC/IPv4 доступны; IPv6 недоступен; проверки IPv6 исключены.' ;;
                        available:closed) msg='PASS — IPv4 и IPv6 доступны; QUIC/IPv4 закрыт; проверки QUIC исключены.' ;;
                        *) error 'Unexpected network capability classification.' ;;
                    esac
                else
                    case "${IPV6_STATE}:${QUIC_STATE}" in
                        unavailable:closed) msg='PASS — IPv4 is available; IPv6 is unavailable; QUIC/IPv4 is blocked; IPv6 and QUIC tests have been excluded.' ;;
                        available:available) msg='PASS — IPv4, IPv6, and QUIC/IPv4 are available.' ;;
                        unavailable:available) msg='PASS — IPv4 and QUIC/IPv4 are available; IPv6 is unavailable; IPv6 tests have been excluded.' ;;
                        available:closed) msg='PASS — IPv4 and IPv6 are available; QUIC/IPv4 is blocked; QUIC tests have been excluded.' ;;
                        *) error 'Unexpected network capability classification.' ;;
                    esac
                fi
                pass "${msg}"
                ;;
            2)
                msg='FAIL — The IPv4 control connection is unavailable; strategy testing was not performed.'
                [ "${LANGUAGE}" != ru ] || msg='FAIL — Контрольное IPv4-подключение недоступно; тестирование стратегий не выполнялось.'
                prerequisite "${msg}"
                ;;
            *) error 'Network capability precheck failed internally.' ;;
        esac
        ;;
    40)
        TARGET=$("${STRATEGY_LAB_JQ}" -r '.target // ""' "${STATUS_FILE}")
        TARGET_TYPE=$("${STRATEGY_LAB_JQ}" -r '.target_type // ""' "${STATUS_FILE}")
        NETWORK_FILE="${JOB_DIR}/network.json"
        BASELINE_FILE="${JOB_DIR}/baseline.json"
        if run_timed "${PROBE_RUNNER}" baseline "${TARGET}" "${TARGET_TYPE}" "${ENDPOINTS_FILE}" \
            "${NETWORK_FILE}" "${JOB_DIR}" "${BASELINE_FILE}"; then status=0; else status=$?; fi
        [ -r "${BASELINE_FILE}" ] || error 'Clean baseline result was not produced.'
        strategy_lab_set_baseline_result "${JOB_ID}" "${BASELINE_FILE}" ||
            error 'Clean baseline state could not be recorded.'
        case "${status}" in
            0)
                if strategy_lab_baseline_all_accessible "${BASELINE_FILE}"; then
                    msg='PASS — All required endpoints are accessible without Zapret2.'
                    [ "${LANGUAGE}" != ru ] || msg='PASS — Все обязательные endpoints доступны без Zapret2.'
                    accessible "${msg}"
                fi
                total=$(strategy_lab_baseline_total_count "${BASELINE_FILE}")
                failed=$(strategy_lab_baseline_failed_count "${BASELINE_FILE}")
                if [ "${TARGET_TYPE}" = ip ]; then
                    msg='PASS — Direct TCP/443 connection to the IP target failed.'
                    [ "${LANGUAGE}" != ru ] || msg='PASS — Прямое TCP/443-подключение к IP-цели не установлено.'
                elif [ "${failed}" -eq "${total}" ]; then
                    msg='PASS — DNS: OK; direct TLS 1.3 connection failed.'
                    [ "${LANGUAGE}" != ru ] || msg='PASS — DNS: OK; прямое TLS 1.3-соединение не установлено.'
                elif [ "${LANGUAGE}" = ru ]; then
                    msg="PASS — Чистый TLS 1.3 baseline: недоступно ${failed} из ${total} обязательных endpoints."
                else
                    msg="PASS — Clean TLS 1.3 baseline: ${failed} of ${total} required endpoints are unavailable."
                fi
                pass "${msg}"
                ;;
            2)
                msg='FAIL — DNS resolution failed for a required endpoint.'
                [ "${LANGUAGE}" != ru ] || msg='FAIL — DNS-разрешение обязательного endpoint не выполнено.'
                prerequisite "${msg}"
                ;;
            *) error 'Clean baseline probe failed internally.' ;;
        esac
        ;;
    50)
        CANDIDATE_FILE="${JOB_DIR}/candidate-smoke.json"
        if run_timed "${CANDIDATE_RUNNER}" "${JOB_ID}" "${ENDPOINTS_FILE}" "${CANDIDATE_FILE}"; then status=0; else status=$?; fi
        [ -r "${CANDIDATE_FILE}" ] || error 'Temporary candidate result was not produced.'
        strategy_lab_set_candidate_smoke_result "${JOB_ID}" "${CANDIDATE_FILE}" ||
            error 'Temporary candidate state could not be recorded.'
        [ "${status}" -eq 0 ] || error 'Temporary candidate runtime failed internally.'
        if "${STRATEGY_LAB_JQ}" -e '.all_pass == true' "${CANDIDATE_FILE}" >/dev/null; then
            msg='PASS — Family screening completed; at least one working TLS 1.3 family was found.'
            [ "${LANGUAGE}" != ru ] || msg='PASS — Проверка семейств завершена; найдено как минимум одно рабочее TLS 1.3-семейство.'
        else
            msg='PASS — Family screening completed; no working TLS 1.3 family was found.'
            [ "${LANGUAGE}" != ru ] || msg='PASS — Проверка семейств завершена; рабочие TLS 1.3-семейства не найдены.'
        fi
        pass "${msg}"
        ;;
    60)
        EXPANSION_FILE="${JOB_DIR}/parameter-expansion.json"
        if run_timed "${EXPANSION_RUNNER}" "${JOB_ID}" "${ENDPOINTS_FILE}" "${JOB_DIR}/candidate-smoke.json" "${EXPANSION_FILE}"; then status=0; else status=$?; fi
        [ "${status}" -eq 0 ] || error 'Accepted-family parameter expansion failed internally.'
        [ -r "${EXPANSION_FILE}" ] || error 'Parameter expansion result was not produced.'
        strategy_lab_set_parameter_expansion_result "${JOB_ID}" "${EXPANSION_FILE}" ||
            error 'Parameter expansion state could not be recorded.'
        working=$("${STRATEGY_LAB_JQ}" -r '.working|length' "${EXPANSION_FILE}")
        completed=$("${STRATEGY_LAB_JQ}" -r '.completed' "${EXPANSION_FILE}")
        if [ "${LANGUAGE}" = ru ]; then
            msg="PASS — Расширение параметров завершено: рабочих кандидатов ${working}, проверено ${completed}."
        else
            msg="PASS — Parameter expansion completed: ${working} working candidates from ${completed} tested."
        fi
        pass "${msg}"
        ;;
    70)
        STABILITY_FILE="${JOB_DIR}/stability.json"
        if run_timed "${STABILITY_RUNNER}" "${JOB_ID}" "${ENDPOINTS_FILE}" "${JOB_DIR}/parameter-expansion.json" \
            "${JOB_DIR}/candidate-smoke.json" "${STABILITY_FILE}"; then status=0; else status=$?; fi
        [ "${status}" -eq 0 ] || error 'Stability confirmation failed internally.'
        [ -r "${STABILITY_FILE}" ] || error 'Stability result was not produced.'
        stable=$("${STRATEGY_LAB_JQ}" -r '.stable|length' "${STABILITY_FILE}")
        completed=$("${STRATEGY_LAB_JQ}" -r '.completed' "${STABILITY_FILE}")
        if [ "${LANGUAGE}" = ru ]; then
            msg="PASS — Проверка стабильности завершена: стабильных ${stable}, проверено ${completed}."
        else
            msg="PASS — Stability confirmation completed: ${stable} stable candidates from ${completed} tested."
        fi
        pass "${msg}"
        ;;
    80-tcp)
        EXTENDED_FILE="${JOB_DIR}/extended-tcp.json"
        if run_timed "${EXTENDED_RUNNER}" "${JOB_ID}" "${ENDPOINTS_FILE}" "${EXTENDED_FILE}"; then status=0; else status=$?; fi
        [ "${status}" -eq 0 ] || error 'Extended TLS/HTTP testing failed internally.'
        [ -r "${EXTENDED_FILE}" ] || error 'Extended TLS/HTTP result was not produced.'
        strategy_lab_set_extended_result "${JOB_ID}" "${EXTENDED_FILE}" ||
            error 'Extended result could not be recorded.'
        pass ''
        ;;
    80-quic)
        QUIC_FILE="${JOB_DIR}/quic.json"
        if run_timed "${QUIC_RUNNER}" "${JOB_ID}" "${ENDPOINTS_FILE}" "${JOB_DIR}/network.json" "${QUIC_FILE}"; then status=0; else status=$?; fi
        [ "${status}" -eq 0 ] || error 'QUIC testing failed internally.'
        [ -r "${QUIC_FILE}" ] || error 'QUIC result was not produced.'
        strategy_lab_set_quic_result "${JOB_ID}" "${QUIC_FILE}" || error 'QUIC result could not be recorded.'
        pass ''
        ;;
    80-udp)
        UDP_FILE="${JOB_DIR}/udp.json"
        if run_timed "${UDP_RUNNER}" "${JOB_ID}" "${ENDPOINTS_FILE}" "${UDP_FILE}"; then status=0; else status=$?; fi
        [ "${status}" -eq 0 ] || error 'Configured UDP testing failed internally.'
        [ -r "${UDP_FILE}" ] || error 'Configured UDP result was not produced.'
        strategy_lab_set_udp_result "${JOB_ID}" "${UDP_FILE}" || error 'UDP result could not be recorded.'
        pass ''
        ;;
    85)
        STABILITY_FILE="${JOB_DIR}/stability.json"
        SHORTLIST_FILE="${JOB_DIR}/shortlist.json"
        [ -r "${STABILITY_FILE}" ] || error 'Stability result is unavailable for shortlist construction.'
        strategy_lab_shortlist_build "${STABILITY_FILE}" "${SHORTLIST_FILE}" || error 'Shortlist could not be constructed.'
        strategy_lab_set_stability_result "${JOB_ID}" "${STABILITY_FILE}" "${SHORTLIST_FILE}" ||
            error 'Stability and shortlist state could not be recorded.'
        count=$("${STRATEGY_LAB_JQ}" -r '.count' "${SHORTLIST_FILE}")
        if [ "${LANGUAGE}" = ru ]; then
            msg="PASS — Итоговый список сформирован: стабильных кандидатов ${count}."
        else
            msg="PASS — Final shortlist built: ${count} stable candidates."
        fi
        pass "${msg}"
        ;;
    restore)
        load_lifecycle_context
        strategy_lab_udp_input_cleanup "${JOB_ID}" || true
        if strategy_lab_restore_initial_service_state; then
            pass '' "${STRATEGY_LAB_INITIAL_SERVICE_STATE}"
        fi
        error ''
        ;;
    eligibility)
        FINAL_STATE="${STRATEGY_LAB_FINAL_STATE:-}"
        FINAL_OUTCOME="${STRATEGY_LAB_FINAL_OUTCOME:-}"
        SHORTLIST_FILE="${JOB_DIR}/shortlist.json"
        eligible=false
        reason=terminal_outcome
        count=0
        if [ -r "${SHORTLIST_FILE}" ]; then
            count=$("${STRATEGY_LAB_JQ}" -r \
                'if has("circular_count") then .circular_count elif has("circular_items") then (.circular_items|length) else (.items|length) end' \
                "${SHORTLIST_FILE}") || count=0
        fi
        if [ "${FINAL_STATE}" != completed ] || [ "${FINAL_OUTCOME}" != SUCCESS ]; then
            reason=terminal_outcome
        elif [ "$("${STRATEGY_LAB_JQ}" -r '.target_type // ""' "${STATUS_FILE}")" != domain ]; then
            reason=domain_required
        elif ! "${STRATEGY_LAB_JQ}" -e '
            any(.stages[]; .number=="85" and .status=="PASS") and
            any(.stages[]; .number=="90" and .status=="PASS") and
            (.restoration.verified==true)
        ' "${STATUS_FILE}" >/dev/null; then
            reason=restoration_required
        elif [ ! -r "${SHORTLIST_FILE}" ] || ! "${STRATEGY_LAB_JQ}" -e '
            (.circular_items // [.items[] | . + {protocol:(.protocol // "tls13"),circular_eligible:(.circular_eligible // true)}]) as $items |
            (($items|length)>=3 and ($items|length)<=5) and
            all($items[]; .protocol=="tls13" and .circular_eligible==true and (.id|type=="string" and length>0) and (.strategy|type=="string" and length>0))
        ' "${SHORTLIST_FILE}" >/dev/null; then
            reason=shortlist_size
        else
            eligible=true
            reason=eligible
        fi
        strategy_lab_set_circular_eligibility "${JOB_ID}" "${eligible}" "${reason}" "${count}" || exit 70
        pass ''
        ;;
    clear-active)
        strategy_lab_clear_active_job "${JOB_ID}"
        pass ''
        ;;
    *) exit 64 ;;
esac
