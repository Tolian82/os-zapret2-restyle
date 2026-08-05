#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP=$(mktemp -d /tmp/strategy-lab-circular-owner.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/run/jobs/job.parent" "${TMP}/bin"
printf '%s\n' parent.example > "${TMP}/run/jobs/job.parent/endpoints.txt"
printf '%s\n' '{"state":"completed","outcome":"SUCCESS","target_type":"domain","stages":[{"number":"85","status":"PASS"},{"number":"90","status":"PASS"}],"restoration":{"verified":true},"circular_eligible":true,"circular_eligibility_reason":"eligible","circular_candidate_count":3}' > "${TMP}/run/jobs/job.parent/status.json"
printf '%s\n' '{"count":3,"items":[{"id":"a","strategy":"--lua-desync=a"},{"id":"b","strategy":"--lua-desync=b"},{"id":"c","strategy":"--lua-desync=c"}]}' > "${TMP}/run/jobs/job.parent/shortlist.json"
printf '%s\n' token-one > "${TMP}/token"

cat > "${TMP}/bin/ps" <<'MOCK'
#!/bin/sh
case "$*" in
    *lstart*) cat "${MOCK_TOKEN_FILE}" ;;
    *command*) printf '%s\n' '/bin/sh strategy_lab_circular_worker.sh job.parent' ;;
    *) exit 1 ;;
esac
MOCK
chmod 0755 "${TMP}/bin/ps"

export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_PS_BIN="${TMP}/bin/ps"
export MOCK_TOKEN_FILE="${TMP}/token"

strategy_lab_job_id_valid(){ case "$1" in job.*) return 0 ;; *) return 1 ;; esac; }
strategy_lab_candidate_cleanup(){ : > "${TMP}/candidate-cleaned"; return 0; }
strategy_lab_firewall_remove_rules(){ : > "${TMP}/firewall-cleaned"; return 0; }
strategy_lab_firewall_range_empty(){ return 0; }
strategy_lab_restore_initial_service_state()
{
    [ "${MOCK_RESTORE_FAIL:-0}" -eq 0 ] || return 1
    state_file="${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/${JOB_ID}/state.json"
    jq '.restoration={verified:true,source:"test",temporary_runtime_clean:true}' \
        "${state_file}" > "${state_file}.tmp"
    mv "${state_file}.tmp" "${state_file}"
    : > "${TMP}/restored"
}

. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/state.sh"
. "${MODULE_DIR}/circular.sh"
. "${MODULE_DIR}/circular_owner.sh"
strategy_lab_circular_prepare_dir

SESSION=$(strategy_lab_circular_session_create job.parent)
strategy_lab_circular_state_write "${SESSION}" running job.parent running 3 ''
strategy_lab_circular_owner_write "${SESSION}" job.parent "$$"
strategy_lab_circular_owner_valid "${SESSION}"
printf '%s\n' token-two > "${TMP}/token"
if strategy_lab_circular_owner_valid "${SESSION}"; then
    echo 'FAIL: changed process-start token was accepted' >&2
    exit 1
fi
cat > "$(strategy_lab_circular_session_dir "${SESSION}")/lifecycle-snapshot.json" <<'JSON'
{"schema":1,"source":"zapret_service","state":"RUNNING"}
JSON
strategy_lab_circular_recover_stale_session "${SESSION}"
STATE=$(strategy_lab_circular_session_state_file "${SESSION}")
jq -e '.state=="error" and .reason=="stale_worker_restored" and .restoration.verified==true' "${STATE}" >/dev/null
[ -e "${TMP}/candidate-cleaned" ]
[ -e "${TMP}/firewall-cleaned" ]
[ -e "${TMP}/restored" ]
[ ! -e "${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE}" ]

printf '%s\n' token-three > "${TMP}/token"
SESSION_FAIL=$(strategy_lab_circular_session_create job.parent)
strategy_lab_circular_state_write "${SESSION_FAIL}" preparing job.parent preparing 3 ''
cat > "$(strategy_lab_circular_session_dir "${SESSION_FAIL}")/lifecycle-snapshot.json" <<'JSON'
{"schema":1,"source":"zapret_service","state":"STOPPED"}
JSON
set +e
MOCK_RESTORE_FAIL=1 strategy_lab_circular_recover_stale_session "${SESSION_FAIL}"
RECOVERY_STATUS=$?
set -e
[ "${RECOVERY_STATUS}" -ne 0 ]
FAIL_STATE=$(strategy_lab_circular_session_state_file "${SESSION_FAIL}")
jq -e '.state=="restore_failed" and .reason=="RESTORE_FAILED"' "${FAIL_STATE}" >/dev/null
[ "$(strategy_lab_circular_active_session_read)" = "${SESSION_FAIL}" ]

grep -Fq 'LOCKF_BIN=' "${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
grep -Fq 'circular-launcher.lock' "${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
grep -Fq 'strategy_lab_circular_owner_write_from_pid_file' "${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
grep -Fq 'strategy_lab_circular_recover_stale_session' "${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
grep -Fq 'strategy_lab_status_file()' "${SCRIPT_DIR}/strategy_lab_circular_worker.sh"
grep -Fq 'automatic retry is blocked' "${SCRIPT_DIR}/strategy_lab_circular_worker.sh"
sh -n "${MODULE_DIR}/circular_owner.sh"
sh -n "${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
sh -n "${SCRIPT_DIR}/strategy_lab_circular_worker.sh"
echo 'PASS: circular launch ownership is serialized, PID reuse is rejected, and stale sessions restore or block safely'
