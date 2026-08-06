#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
STATE="${MODULE_DIR}/state.sh"
MESSAGES="${MODULE_DIR}/worker_messages.sh"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
TMP=$(mktemp -d /tmp/strategy-lab-progress.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/jobs/job.test"

export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_JOBS_DIR="${TMP}/jobs"
export STRATEGY_LAB_STATE_LOCKF_BIN=''
export STRATEGY_LAB_STATE_FLOCK_BIN=$(command -v flock)

strategy_lab_job_dir(){ printf '%s/%s\n' "${STRATEGY_LAB_JOBS_DIR}" "$1"; }
strategy_lab_status_file(){ printf '%s/status.json\n' "$(strategy_lab_job_dir "$1")"; }
strategy_lab_event_file(){ printf '%s/events.ndjson\n' "$(strategy_lab_job_dir "$1")"; }
strategy_lab_atomic_write(){ path="$1"; tmp="${path}.tmp"; cat > "${tmp}"; mv "${tmp}" "${path}"; }

. "${STATE}"
strategy_lab_initialize_state job.test example.com extended ru
jq -e '.progress.percent==0 and .progress.stage=="00" and .progress.stage_key=="target_initialization"' \
    "$(strategy_lab_status_file job.test)" >/dev/null
strategy_lab_update_stage job.test 50 RUNNING 'screening'
jq -e '.progress.percent==45 and .progress.stage=="50" and .progress.stage_key=="family_screening" and .progress.message=="screening"' \
    "$(strategy_lab_status_file job.test)" >/dev/null
strategy_lab_update_stage job.test 90 PASS 'restored'
jq -e '.progress.percent==91 and .progress.stage_key=="restore"' \
    "$(strategy_lab_status_file job.test)" >/dev/null
strategy_lab_update_job job.test completed SUCCESS 99 false 'done'
jq -e '.state=="completed" and .progress.percent==100 and .progress.stage=="99" and .progress.stage_key=="report" and .progress.message=="done"' \
    "$(strategy_lab_status_file job.test)" >/dev/null

grep -Fq 'var stageLabels = isRussian' "${VIEW}"
grep -Fq 'var statusLabels = isRussian' "${VIEW}"
grep -Fq 'var outcomeLabels = isRussian' "${VIEW}"
grep -Fq 'var circularMessages = isRussian' "${VIEW}"
grep -Fq 'function renderProgress(data)' "${VIEW}"
grep -Fq 'id="strategyLabProgressBar"' "${VIEW}"
grep -Fq "STOP_REQUESTED:'ОСТАНОВКА ЗАПРОШЕНА'" "${VIEW}"
grep -Fq "COMPLETED:'ЗАВЕРШЕНО'" "${VIEW}"
grep -Fq "completed:'Circular validation finished and Zapret2 was restored.'" "${VIEW}"
grep -Fq "completed:'Циклическая проверка завершена, состояние Zapret2 восстановлено.'" "${VIEW}"
! grep -Fq 'canseled' "${MESSAGES}"
grep -Fq "CANCEL_MESSAGE='SKIPPED — canceled'" "${MESSAGES}"
sh -n "${STATE}"
echo 'PASS: persisted stage progress and complete RU/EN Strategy Lab localization are enforced'
