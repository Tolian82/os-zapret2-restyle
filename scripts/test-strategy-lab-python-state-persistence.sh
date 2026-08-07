#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${ZAPRET_DIR}/strategy_lab"
STATE_MODULE="${MODULE_DIR}/state.sh"
PYTHON_STATE="${ZAPRET_DIR}/strategy_lab_py/state.py"
PYTHON_LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-python-state.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON_BIN}"
[ "$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" = 3.13 ] ||
    fail 'Strategy Lab state persistence must be tested on Python 3.13'

STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_RUN_DIR="${TEST_ROOT}/run"
STRATEGY_LAB_LOG_DIR="${TEST_ROOT}/log"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_RUN_DIR}/jobs"
STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}"
STRATEGY_LAB_PYTHON_LAUNCHER="${PYTHON_LAUNCHER}"
export STRATEGY_LAB_JQ STRATEGY_LAB_RUN_DIR STRATEGY_LAB_LOG_DIR STRATEGY_LAB_JOBS_DIR
export STRATEGY_LAB_PYTHON_BIN STRATEGY_LAB_PYTHON_LAUNCHER

. "${MODULE_DIR}/common.sh"
. "${STATE_MODULE}"

strategy_lab_prepare_directories
strategy_lab_initialize_state job.test example.com extended ru
status=$(strategy_lab_status_file job.test)
events=$(strategy_lab_event_file job.test)

"${STRATEGY_LAB_JQ}" -e '
    .schema==2 and .revision==0 and .job_id=="job.test" and
    .state=="queued" and .outcome=="" and
    .target=="example.com" and .mode=="extended" and .language=="ru" and
    .progress=={percent:0,stage:"00",stage_key:"target_initialization",message:""} and
    (.stages|length)==12 and
    [.stages[].number]==["00","10","20","30","40","50","60","70","80","85","90","99"] and
    [.stages[].key]==["target_initialization","lifecycle_snapshot","service_stop","network_precheck","clean_baseline","family_screening","family_expansion","stability","extended","shortlist","restore","report"]
' "${status}" >/dev/null || fail 'initial public state schema changed'
[ -f "${events}" ] && [ ! -s "${events}" ] || fail 'events.ndjson was not initialized empty'

printf '%s\n%s\n' example.com www.example.com > "${TEST_ROOT}/endpoints.txt"
strategy_lab_set_target_contract job.test example.com domain "${TEST_ROOT}/endpoints.txt"
"${STRATEGY_LAB_JQ}" -e '.revision==1 and .target_type=="domain" and .endpoints==["example.com","www.example.com"]' "${status}" >/dev/null ||
    fail 'target contract persistence changed'

printf '%s\n' '{"ipv4":"available","ipv6":"unavailable"}' > "${TEST_ROOT}/network.json"
printf '%s\n' '{"dns_a":"PASS","endpoints":[]}' > "${TEST_ROOT}/baseline.json"
printf '%s\n' '{"accepted":["multisplit"],"families":[]}' > "${TEST_ROOT}/candidate.json"
printf '%s\n' '{"completed":1,"working":["a"],"failed":[]}' > "${TEST_ROOT}/expansion.json"
printf '%s\n' '{"completed":1,"stable":["a"],"candidates":[]}' > "${TEST_ROOT}/stability.json"
printf '%s\n' '{"count":1,"items":[{"id":"a"}]}' > "${TEST_ROOT}/shortlist.json"
printf '%s\n' '{"protocols":{"tls12":{"tested":[],"working":null},"http":{"tested":[],"working":null}}}' > "${TEST_ROOT}/extended.json"
printf '%s\n' '{"status":"skipped","working":null}' > "${TEST_ROOT}/quic.json"
printf '%s\n' '{"status":"skipped","port":null,"working":null}' > "${TEST_ROOT}/udp.json"
printf '%s\n' '{"schema":1,"source":"zapret_service","state":"RUNNING"}' > "${TEST_ROOT}/lifecycle.json"
printf '%s\n' '{"verified":true,"source":"zapret_service","initial_state":"RUNNING","final_state":"RUNNING","strategy_unchanged":true,"temporary_runtime_clean":true}' > "${TEST_ROOT}/restoration.json"

strategy_lab_set_network_capabilities job.test "${TEST_ROOT}/network.json"
strategy_lab_set_baseline_result job.test "${TEST_ROOT}/baseline.json"
strategy_lab_set_candidate_smoke_result job.test "${TEST_ROOT}/candidate.json"
strategy_lab_set_json_field job.test parameter_expansion "${TEST_ROOT}/expansion.json"
strategy_lab_state_python set-stability job.test "${status}" "${TEST_ROOT}/stability.json" "${TEST_ROOT}/shortlist.json"
strategy_lab_set_json_field job.test extended "${TEST_ROOT}/extended.json"
strategy_lab_set_json_field job.test quic "${TEST_ROOT}/quic.json"
strategy_lab_set_json_field job.test udp "${TEST_ROOT}/udp.json"
strategy_lab_set_json_field job.test lifecycle_snapshot "${TEST_ROOT}/lifecycle.json"
strategy_lab_set_json_field job.test restoration "${TEST_ROOT}/restoration.json"
"${STRATEGY_LAB_JQ}" -e '
    .revision==11 and .network.ipv4=="available" and .baseline.dns_a=="PASS" and
    .candidate_smoke.accepted==["multisplit"] and .family_screening.accepted==["multisplit"] and
    .parameter_expansion.working==["a"] and .stability.stable==["a"] and .shortlist.count==1 and
    .extended.protocols.tls12.working==null and .quic.status=="skipped" and .udp.status=="skipped" and
    .lifecycle_snapshot.state=="RUNNING" and .restoration.verified==true
' "${status}" >/dev/null || fail 'structured status fields changed during Python persistence cutover'

strategy_lab_update_stage job.test 50 RUNNING screening
"${STRATEGY_LAB_JQ}" -e '.revision==12 and .current_stage=="50" and .progress.percent==45 and .progress.stage_key=="family_screening" and (.stages[]|select(.number=="50")|.status)=="RUNNING"' "${status}" >/dev/null ||
    fail 'stage-50 progress parity changed'
strategy_lab_update_stage job.test 90 PASS restored
"${STRATEGY_LAB_JQ}" -e '.revision==13 and .progress.percent==91 and .progress.stage=="90" and .progress.stage_key=="restore"' "${status}" >/dev/null ||
    fail 'stage-90 progress parity changed'
strategy_lab_update_job job.test completed SUCCESS 99 false done
"${STRATEGY_LAB_JQ}" -e '.revision==14 and .state=="completed" and .outcome=="SUCCESS" and .progress.percent==100 and .progress.stage=="99" and .progress.stage_key=="report" and .progress.message=="done"' "${status}" >/dev/null ||
    fail 'terminal progress parity changed'
strategy_lab_request_cancel job.test late-cancel
strategy_lab_update_stage job.test 50 RUNNING late-stage
"${STRATEGY_LAB_JQ}" -e '.revision==16 and .state=="completed" and .outcome=="SUCCESS" and .current_stage=="99" and .progress.percent==100 and (.stages[]|select(.number=="50")|.status)=="RUNNING"' "${status}" >/dev/null ||
    fail 'terminal no-op writes changed terminal state'

strategy_lab_append_event job.test 50 RUNNING screening
strategy_lab_append_event job.test 50 PASS accepted
"${STRATEGY_LAB_JQ}" -s -e 'length==2 and .[0]=={stage:"50",status:"RUNNING",message:"screening"} and .[1]=={stage:"50",status:"PASS",message:"accepted"}' "${events}" >/dev/null ||
    fail 'events.ndjson contract changed'

strategy_lab_initialize_state job.cancel example.org standard en
cancel_status=$(strategy_lab_status_file job.cancel)
strategy_lab_request_cancel job.cancel 'Cancellation requested'
cancel_at=$("${STRATEGY_LAB_JQ}" -r '.cancel_requested_at' "${cancel_status}")
[ -n "${cancel_at}" ] || fail 'cancel timestamp was not persisted'
strategy_lab_request_cancel job.cancel 'Cancellation requested again'
"${STRATEGY_LAB_JQ}" -e --arg at "${cancel_at}" '.revision==2 and .state=="cancel_requested" and .cancel_requested==true and .cancel_requested_at==$at' "${cancel_status}" >/dev/null ||
    fail 'repeated cancellation changed the original timestamp'

strategy_lab_initialize_state job.race race.example standard en
race_status=$(strategy_lab_status_file job.race)
iteration=1
while [ "${iteration}" -le 24 ]
do
    strategy_lab_set_initial_service_state job.race "RUNNING-${iteration}" &
    iteration=$((iteration + 1))
done
reader=1
while [ "${reader}" -le 100 ]
do
    "${PYTHON_BIN}" -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "${race_status}" || fail 'concurrent reader observed partial JSON'
    reader=$((reader + 1))
done
wait
[ "$("${STRATEGY_LAB_JQ}" -r '.revision' "${race_status}")" -eq 24 ] || fail 'concurrent revision writes were lost'

"${PYTHON_BIN}" - "${status}" "${events}" <<'PY'
import os
import stat
import sys
for name in sys.argv[1:]:
    mode = stat.S_IMODE(os.stat(name).st_mode)
    assert mode == 0o644, (name, oct(mode))
PY

if find "${STRATEGY_LAB_JOBS_DIR}" -type f \( -name '.status.*' -o -name '.events.*' \) | grep -q .; then
    fail 'atomic persistence left temporary automated-job state/event files behind'
fi

mkdir -p "${TEST_ROOT}/circular/job.circular"
printf '%s\n' '{"schema":1,"state":"active"}' > "${TEST_ROOT}/circular/job.circular/state.json"
set +e
STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" "${PYTHON_LAUNCHER}" state set-json-field job.circular "${TEST_ROOT}/circular/job.circular/state.json" restoration "${TEST_ROOT}/restoration.json" >"${TEST_ROOT}/circular.out" 2>"${TEST_ROOT}/circular.err"
circular_status=$?
set -e
[ "${circular_status}" -eq 64 ] || fail "private circular state path returned ${circular_status}, expected 64"
grep -Fq 'ERROR: invalid Strategy Lab automated-job state path' "${TEST_ROOT}/circular.err" ||
    fail 'private circular state path was not rejected by the automated-job writer'

set +e
STRATEGY_LAB_PYTHON_BIN="${PYTHON_BIN}" "${PYTHON_LAUNCHER}" state set-json-field job.test "${TEST_ROOT}/wrong/status.json" network "${TEST_ROOT}/network.json" >"${TEST_ROOT}/invalid.out" 2>"${TEST_ROOT}/invalid.err"
invalid_status=$?
set -e
[ "${invalid_status}" -eq 64 ] || fail "invalid automated-job state path returned ${invalid_status}, expected 64"
grep -Fq 'ERROR: invalid Strategy Lab automated-job state path' "${TEST_ROOT}/invalid.err" || fail 'invalid automated-job state path error is not deterministic'

! grep -Fq 'strategy_lab_state_transform' "${STATE_MODULE}" || fail 'shell state transform still exists'
! grep -Fq 'STRATEGY_LAB_JQ' "${STATE_MODULE}" || fail 'shell automated-job state adapter still owns jq mutation'
! grep -Fq 'mktemp' "${STATE_MODULE}" || fail 'shell automated-job state adapter still owns temporary state files'
! grep -Fq 'mv -f' "${STATE_MODULE}" || fail 'shell automated-job state adapter still owns atomic state replacement'
grep -Fq 'strategy_lab_finalize_stale_recovery' "${MODULE_DIR}/launch.sh" || fail 'stale automated-job recovery does not use Python persistence'
! grep -Fq '.stale-recovery.' "${MODULE_DIR}/launch.sh" || fail 'stale recovery still has a private automated-job state writer'
grep -Fq 'for module in common state firewall runtime candidate lifecycle circular' "${ZAPRET_DIR}/strategy_lab_recovery_worker.sh" ||
    fail 'recovery worker does not load the Python automated-job state adapter'

if grep -RFn 'strategy_lab_state_transform' "${MODULE_DIR}"; then
    fail 'a Strategy Lab shell module still owns the removed automated-job status transform'
fi

grep -Fq '*/state.json)' "${MODULE_DIR}/lifecycle.sh" || fail 'shared lifecycle code does not preserve the separate circular-state writer boundary'

PYTHONDONTWRITEBYTECODE=1 "${PYTHON_BIN}" -m py_compile "${PYTHON_STATE}"
sh -n "${STATE_MODULE}"
sh -n "$0"
echo 'PASS: Python 3.13 exclusively owns automated-job status/progress/event persistence with atomic revisioned writes and public JSON parity'
