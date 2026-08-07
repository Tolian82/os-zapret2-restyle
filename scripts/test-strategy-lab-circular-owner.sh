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

cat > "${TMP}/bin/recover" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' "$*" >> "${MOCK_RECOVERY_LOG}"
[ "${1:-}" = strategy-lab-recover ] || exit 91
session="${2:-}"
state="${MOCK_CIRCULAR_SESSIONS}/${session}/state.json"
tmp="${state}.tmp.$$"
case "${MOCK_RECOVERY_MODE:-verified}" in
    verified)
        initial=$(jq -r '.mock_initial_state // "RUNNING"' "${state}")
        jq --arg initial "${initial}" '.restoration={verified:true,source:"zapret_service",initial_state:$initial,final_state:$initial,strategy_unchanged:true,temporary_runtime_clean:true}' "${state}" > "${tmp}"
        mv -f "${tmp}" "${state}"
        ;;
    inconsistent)
        jq '.restoration={verified:true,source:"zapret_service",initial_state:"STOPPED",final_state:"STOPPED",strategy_unchanged:false,temporary_runtime_clean:true}' "${state}" > "${tmp}"
        mv -f "${tmp}" "${state}"
        ;;
    failed)
        jq '.restoration={verified:false,source:"zapret_service",initial_state:"RUNNING",final_state:"unknown",strategy_unchanged:false,temporary_runtime_clean:true}' "${state}" > "${tmp}"
        mv -f "${tmp}" "${state}"
        exit 1
        ;;
    *) exit 92 ;;
esac
MOCK
chmod 0755 "${TMP}/bin/recover"

export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_PS_BIN="${TMP}/bin/ps"
export MOCK_TOKEN_FILE="${TMP}/token"
export MOCK_RECOVERY_LOG="${TMP}/recovery.log"
export MOCK_CIRCULAR_SESSIONS="${TMP}/run/circular/sessions"
export STRATEGY_LAB_CIRCULAR_RECOVERY_SCRIPT="${TMP}/bin/recover"

strategy_lab_job_id_valid(){ case "$1" in job.*) return 0 ;; *) return 1 ;; esac; }
strategy_lab_candidate_cleanup(){ : > "${TMP}/candidate-cleaned"; return 0; }
strategy_lab_firewall_remove_rules(){ : > "${TMP}/firewall-cleaned"; return 0; }
strategy_lab_firewall_range_empty(){ return 0; }

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
jq '.mock_initial_state="RUNNING"' "$(strategy_lab_circular_session_state_file "${SESSION}")" > "${TMP}/state.tmp"
mv "${TMP}/state.tmp" "$(strategy_lab_circular_session_state_file "${SESSION}")"
MOCK_RECOVERY_MODE=verified
export MOCK_RECOVERY_MODE
strategy_lab_circular_recover_stale_session "${SESSION}"
STATE=$(strategy_lab_circular_session_state_file "${SESSION}")
jq -e '.state=="error" and .reason=="stale_worker_restored" and .restoration.verified==true and .restoration.strategy_unchanged==true and .restoration.temporary_runtime_clean==true' "${STATE}" >/dev/null
[ ! -e "${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE}" ]

printf '%s\n' token-three > "${TMP}/token"
SESSION_FAIL=$(strategy_lab_circular_session_create job.parent)
strategy_lab_circular_state_write "${SESSION_FAIL}" preparing job.parent preparing 3 ''
cat > "$(strategy_lab_circular_session_dir "${SESSION_FAIL}")/lifecycle-snapshot.json" <<'JSON'
{"schema":1,"source":"zapret_service","state":"STOPPED"}
JSON
MOCK_RECOVERY_MODE=inconsistent
export MOCK_RECOVERY_MODE
set +e
strategy_lab_circular_recover_stale_session "${SESSION_FAIL}"
RECOVERY_STATUS=$?
set -e
[ "${RECOVERY_STATUS}" -ne 0 ]
FAIL_STATE=$(strategy_lab_circular_session_state_file "${SESSION_FAIL}")
jq -e '.state=="restore_failed" and .reason=="RESTORE_FAILED" and .restoration.verified==false' "${FAIL_STATE}" >/dev/null
[ "$(strategy_lab_circular_active_session_read)" = "${SESSION_FAIL}" ]

[ "$(wc -l < "${MOCK_RECOVERY_LOG}" | tr -d ' ')" -eq 2 ]
if grep -Ev '^strategy-lab-recover job\.[A-Za-z0-9]+$' "${MOCK_RECOVERY_LOG}" | grep -q .; then
    echo 'FAIL: circular stale recovery did not delegate exclusively to the lifecycle-owned recovery action' >&2
    exit 1
fi

! grep -Fq 'strategy_lab_restore_initial_service_state' "${MODULE_DIR}/circular_owner.sh"
grep -Fq 'STRATEGY_LAB_CIRCULAR_RECOVERY_SCRIPT' "${MODULE_DIR}/circular_owner.sh"
grep -Fq 'strategy-lab-recover "${_slco_session}"' "${MODULE_DIR}/circular_owner.sh"
grep -Fq 'for module in common firewall runtime candidate lifecycle circular' "${SCRIPT_DIR}/strategy_lab_recovery_worker.sh"
grep -Fq 'STRATEGY_LAB_CIRCULAR_SESSIONS_DIR' "${SCRIPT_DIR}/strategy_lab_recovery_worker.sh"
grep -Fq 'strategy_lab_restore_initial_service_state' "${SCRIPT_DIR}/strategy_lab_recovery_worker.sh"
grep -Fq 'strategy-lab|strategy-lab-circular|strategy-lab-recover)' "${SCRIPT_DIR}/zapret_service.sh"
grep -Fq 'STRATEGY_LAB_LIFECYCLE_OWNER=1' "${SCRIPT_DIR}/zapret_service.sh"
sh -n "${MODULE_DIR}/circular_owner.sh"
sh -n "${SCRIPT_DIR}/strategy_lab_recovery_worker.sh"
sh -n "${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
echo 'PASS: circular stale recovery delegates protected restoration to the lifecycle-owned semantic recovery transaction and blocks inconsistent proof'
