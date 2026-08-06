#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
RETENTION="${MODULE_DIR}/retention.sh"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_launcher.sh"
CIRCULAR_LAUNCHER="${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
TMP=$(mktemp -d /tmp/strategy-lab-retention.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM

export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_LOG_DIR="${TMP}/log"
export STRATEGY_LAB_ACTIVE_FILE="${TMP}/run/active.job"
export STRATEGY_LAB_LATEST_FILE="${TMP}/run/latest.job"
mkdir -p "${STRATEGY_LAB_JOBS_DIR}" "${STRATEGY_LAB_LOG_DIR}"

. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/circular.sh"
. "${RETENTION}"
strategy_lab_circular_prepare_dir

write_job()
{
    job="$1" state="$2" outcome="$3" restored="$4" stamp="$5"
    dir="${STRATEGY_LAB_JOBS_DIR}/${job}"
    mkdir -p "${dir}"
    jq -nc --arg job "${job}" --arg state "${state}" --arg outcome "${outcome}" \
        --argjson restored "${restored}" \
        '{job_id:$job,state:$state,outcome:$outcome,restoration:{verified:$restored}}' \
        > "${dir}/status.json"
    printf '%s\n' log > "${STRATEGY_LAB_LOG_DIR}/${job}.log"
    touch -t "${stamp}" "${dir}"
}

write_job job.old1 completed SUCCESS true 202601010101
write_job job.old2 completed SUCCESS true 202601020101
write_job job.old3 error ERROR true 202601030101
write_job job.latest completed SUCCESS true 202601040101
write_job job.active running '' false 202601050101
write_job job.restore error RESTORE_FAILED false 202601060101
write_job job.unverified error ERROR false 202601070101
printf '%s\n' job.latest > "${STRATEGY_LAB_LATEST_FILE}"
printf '%s\n' job.active > "${STRATEGY_LAB_ACTIVE_FILE}"

STRATEGY_LAB_RETENTION_MAX_JOBS=2
export STRATEGY_LAB_RETENTION_MAX_JOBS
strategy_lab_retention_prune_automated
[ ! -d "${STRATEGY_LAB_JOBS_DIR}/job.old1" ]
[ ! -e "${STRATEGY_LAB_LOG_DIR}/job.old1.log" ]
[ -d "${STRATEGY_LAB_JOBS_DIR}/job.old2" ]
[ -d "${STRATEGY_LAB_JOBS_DIR}/job.old3" ]
[ -d "${STRATEGY_LAB_JOBS_DIR}/job.latest" ]
[ -d "${STRATEGY_LAB_JOBS_DIR}/job.active" ]
[ -d "${STRATEGY_LAB_JOBS_DIR}/job.restore" ]
[ -d "${STRATEGY_LAB_JOBS_DIR}/job.unverified" ]
[ "$(cat "${STRATEGY_LAB_LATEST_FILE}")" = job.latest ]
[ "$(cat "${STRATEGY_LAB_ACTIVE_FILE}")" = job.active ]

STRATEGY_LAB_RETENTION_MAX_JOBS=0
if strategy_lab_retention_prune_automated; then
    echo 'FAIL: invalid automated retention limit was accepted' >&2
    exit 1
fi
[ -d "${STRATEGY_LAB_JOBS_DIR}/job.old2" ]

write_session()
{
    session="$1" state="$2" reason="$3" restored="$4" stamp="$5"
    dir="${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/${session}"
    mkdir -p "${dir}"
    jq -nc --arg session "${session}" --arg state "${state}" --arg reason "${reason}" \
        --argjson restored "${restored}" \
        '{session_id:$session,state:$state,reason:$reason,restoration:{verified:$restored}}' \
        > "${dir}/state.json"
    touch -t "${stamp}" "${dir}"
}

write_session job.cold1 completed requested true 202602010101
write_session job.cold2 error stale_worker_restored true 202602020101
write_session job.csafe error lifecycle_lock false 202602030101
write_session job.clatest completed timeout true 202602040101
write_session job.cactive running '' false 202602050101
write_session job.crestore restore_failed RESTORE_FAILED false 202602060101
write_session job.cunverified error runtime_failed false 202602070101
printf '%s\n' job.clatest > "${STRATEGY_LAB_CIRCULAR_LATEST_FILE}"
printf '%s\n' job.cactive > "${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE}"

STRATEGY_LAB_RETENTION_MAX_CIRCULAR=1
export STRATEGY_LAB_RETENTION_MAX_CIRCULAR
strategy_lab_retention_prune_circular
[ ! -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.cold1" ]
[ ! -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.cold2" ]
[ -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.csafe" ]
[ -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.clatest" ]
[ -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.cactive" ]
[ -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.crestore" ]
[ -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.cunverified" ]
[ "$(cat "${STRATEGY_LAB_CIRCULAR_LATEST_FILE}")" = job.clatest ]
[ "$(cat "${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE}")" = job.cactive ]

STRATEGY_LAB_RETENTION_MAX_CIRCULAR=1001
if strategy_lab_retention_prune_circular; then
    echo 'FAIL: invalid circular retention limit was accepted' >&2
    exit 1
fi

grep -Fq 'retention launch query' "${LAUNCHER}"
grep -Fq 'strategy_lab_retention_prune_automated' "${LAUNCHER}"
grep -Fq 'circular circular_owner retention' "${CIRCULAR_LAUNCHER}"
grep -Fq 'strategy_lab_retention_prune_circular' "${CIRCULAR_LAUNCHER}"
sh -n "${RETENTION}"
sh -n "${LAUNCHER}"
sh -n "${CIRCULAR_LAUNCHER}"
echo 'PASS: retention removes only excess verified terminal artifacts and protects lifecycle evidence'
