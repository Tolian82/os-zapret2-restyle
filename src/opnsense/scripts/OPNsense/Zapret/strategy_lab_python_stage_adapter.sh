#!/bin/sh

set -eu
umask 022

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
SYSTEM_ADAPTER="${STRATEGY_LAB_SYSTEM_STAGE_ADAPTER:-${SCRIPT_DIR}/strategy_lab_stage_adapter.sh}"
RESULT_RUNNER="${STRATEGY_LAB_RESULT_RUNNER:-${SCRIPT_DIR}/strategy_lab_result_runner.sh}"
PYTHON_LAUNCHER="${STRATEGY_LAB_PYTHON_LAUNCHER:-${SCRIPT_DIR}/strategy_lab_python_launcher.sh}"
ACTION="${1:-}"
JOB_ID="${2:-}"
RESULT_FILE="${STRATEGY_LAB_STAGE_RESULT_FILE:-}"
JQ="${STRATEGY_LAB_JQ:-/usr/local/bin/jq}"
JOBS_DIR="${STRATEGY_LAB_JOBS_DIR:-/var/run/zapret2-restyle/strategy-lab/jobs}"

case "${JOB_ID}" in job.*) ;; *) exit 64 ;; esac
[ -n "${RESULT_FILE}" ] || exit 64

emit_pass()
{
    message="${1:-}"
    "${JQ}" -nc --arg message "${message}" '{kind:"pass",message:$message,initial_state:""}' > "${RESULT_FILE}"
    chmod 0644 "${RESULT_FILE}"
}

case "${ACTION}" in
    85)
        [ -f "${RESULT_RUNNER}" ] || exit 70
        [ -x "${PYTHON_LAUNCHER}" ] || exit 70
        set +e
        /bin/sh "${RESULT_RUNNER}" shortlist "${JOB_ID}"
        result_status=$?
        set -e
        case "${result_status}" in
            0) ;;
            124) exit 124 ;;
            125) exit 125 ;;
            *) exit 70 ;;
        esac
        job_dir="${JOBS_DIR}/${JOB_ID}"
        stability="${job_dir}/stability.json"
        shortlist="${job_dir}/shortlist.json"
        status="${job_dir}/status.json"
        [ -r "${stability}" ] && [ -r "${shortlist}" ] && [ -r "${status}" ] || exit 70
        "${PYTHON_LAUNCHER}" state set-stability "${JOB_ID}" "${status}" "${stability}" "${shortlist}" || exit 70
        count=$("${JQ}" -r '.count // empty' "${shortlist}")
        case "${count}" in ''|*[!0-9]*) exit 70 ;; esac
        language=$("${JQ}" -r '.language // "en"' "${status}")
        if [ "${language}" = ru ]; then
            message="PASS — Итоговый список сформирован: стабильных кандидатов ${count}."
        else
            message="PASS — Final shortlist built: ${count} stable candidates."
        fi
        emit_pass "${message}"
        ;;
    eligibility)
        [ -f "${RESULT_RUNNER}" ] || exit 70
        /bin/sh "${RESULT_RUNNER}" eligibility "${JOB_ID}" "${STRATEGY_LAB_FINAL_STATE:-}" "${STRATEGY_LAB_FINAL_OUTCOME:-}" || exit 70
        emit_pass ''
        ;;
    *)
        [ -f "${SYSTEM_ADAPTER}" ] || exit 70
        exec /bin/sh "${SYSTEM_ADAPTER}" "$@"
        ;;
esac
