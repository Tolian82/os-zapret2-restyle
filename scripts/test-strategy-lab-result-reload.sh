#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
LAUNCH="${MODULE_DIR}/launch.sh"
QUERY="${MODULE_DIR}/query.sh"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
TMP=$(mktemp -d /tmp/strategy-lab-reload.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/run/jobs/job.old" "${TMP}/run/jobs/job.new" \
    "${TMP}/run/jobs/job.active" "${TMP}/log"
printf '%s\n' '{"job_id":"job.old","state":"completed","outcome":"SUCCESS"}' > "${TMP}/run/jobs/job.old/status.json"
sleep 1
printf '%s\n' '{"job_id":"job.new","state":"error","outcome":"TIMEOUT"}' > "${TMP}/run/jobs/job.new/status.json"
printf '%s\n' '{"job_id":"job.active","state":"running","outcome":""}' > "${TMP}/run/jobs/job.active/status.json"

export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_LOG_DIR="${TMP}/log"
export STRATEGY_LAB_ACTIVE_FILE="${TMP}/run/active.job"
export STRATEGY_LAB_LATEST_FILE="${TMP}/run/latest.job"

. "${MODULE_DIR}/common.sh"
usage_error(){ return 64; }
emit_error_json(){ printf '%s\n' "$1"; }
cleanup_stale_active(){ return 0; }
strategy_lab_reconcile_stale_job(){ return 0; }
. "${QUERY}"

# Terminal evidence remains addressable and the latest pointer remains repairable.
latest=$(strategy_lab_latest_job)
[ "${latest}" = job.active ]
[ "$(cat "${STRATEGY_LAB_LATEST_FILE}")" = job.active ]
status=$(show_status status job.new)
printf '%s\n' "${status}" | jq -e '.job_id=="job.new" and .state=="error" and .outcome=="TIMEOUT"' >/dev/null
status=$(show_status status job.old)
printf '%s\n' "${status}" | jq -e '.job_id=="job.old" and .state=="completed"' >/dev/null

# Automatic Diagnostics discovery resumes only a genuinely active job.
printf '%s\n' job.active > "${STRATEGY_LAB_ACTIVE_FILE}"
status=$(show_status status -)
printf '%s\n' "${status}" | jq -e '.job_id=="job.active" and .state=="running"' >/dev/null

# After terminal cleanup removes active.job, a page reload starts idle instead
# of resurrecting the latest completed or failed result.
rm -f "${STRATEGY_LAB_ACTIVE_FILE}"
printf '%s\n' job.new > "${STRATEGY_LAB_LATEST_FILE}"
status=$(show_status status -)
printf '%s\n' "${status}" | jq -e '.status=="idle" and (has("job_id")|not)' >/dev/null
[ "$(cat "${STRATEGY_LAB_LATEST_FILE}")" = job.new ]

# A corrupt latest pointer can still be repaired for retention/history users,
# but it is never used by automatic status discovery.
printf '%s\n' 'invalid/job' > "${STRATEGY_LAB_LATEST_FILE}"
latest=$(strategy_lab_latest_job)
[ "${latest}" = job.active ]
[ "$(cat "${STRATEGY_LATEST_FILE:-${STRATEGY_LAB_LATEST_FILE}}")" = job.active ]
status=$(show_status status -)
printf '%s\n' "${status}" | jq -e '.status=="idle"' >/dev/null

grep -Fq 'strategy_lab_write_latest_job "${_strategy_lab_job}"' "${LAUNCH}"
grep -Eq "apiPost\('/api/zapret/strategy_lab/status',[[:space:]]*\{job_id:'-'\}" "${VIEW}"
grep -Fq 'strategy_lab_read_active_job' "${QUERY}"
! sed -n '/show_status()/,/^}/p' "${QUERY}" | grep -Fq 'strategy_lab_latest_job'
grep -Fq 'pollStatus();' "${VIEW}"
sh -n "${MODULE_DIR}/common.sh"
sh -n "${QUERY}"
sh -n "${LAUNCH}"
echo 'PASS: Diagnostics reload resumes active work, opens idle after terminal work, and preserves explicit historical result access'
