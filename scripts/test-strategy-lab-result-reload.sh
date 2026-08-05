#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
LAUNCH="${MODULE_DIR}/launch.sh"
QUERY="${MODULE_DIR}/query.sh"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
TMP=$(mktemp -d /tmp/strategy-lab-reload.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/run/jobs/job.old" "${TMP}/run/jobs/job.new" "${TMP}/log"
printf '%s\n' '{"job_id":"job.old","state":"completed","outcome":"SUCCESS"}' > "${TMP}/run/jobs/job.old/status.json"
sleep 1
printf '%s\n' '{"job_id":"job.new","state":"error","outcome":"TIMEOUT"}' > "${TMP}/run/jobs/job.new/status.json"

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

latest=$(strategy_lab_latest_job)
[ "${latest}" = job.new ]
[ "$(cat "${STRATEGY_LAB_LATEST_FILE}")" = job.new ]
status=$(show_status status -)
printf '%s\n' "${status}" | jq -e '.job_id=="job.new" and .state=="error" and .outcome=="TIMEOUT"' >/dev/null
printf '%s\n' job.old > "${STRATEGY_LAB_LATEST_FILE}"
status=$(show_status status -)
printf '%s\n' "${status}" | jq -e '.job_id=="job.old" and .state=="completed"' >/dev/null

# A corrupt pointer falls back to the most recent directory and repairs itself.
printf '%s\n' 'invalid/job' > "${STRATEGY_LAB_LATEST_FILE}"
latest=$(strategy_lab_latest_job)
[ "${latest}" = job.new ]
[ "$(cat "${STRATEGY_LAB_LATEST_FILE}")" = job.new ]

grep -Fq 'strategy_lab_write_latest_job "${_strategy_lab_job}"' "${LAUNCH}"
grep -Fq "apiPost('/api/zapret/strategy_lab/status', {job_id:'-'}" "${VIEW}"
grep -Fq 'if (terminal(data.state)) {' "${VIEW}"
grep -Fq 'fetchResult();' "${VIEW}"
grep -Fq 'pollStatus();' "${VIEW}"
sh -n "${MODULE_DIR}/common.sh"
sh -n "${QUERY}"
sh -n "${LAUNCH}"
echo 'PASS: latest terminal Strategy Lab result is restored after Diagnostics reload'
