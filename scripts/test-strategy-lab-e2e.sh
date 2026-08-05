#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_launcher.sh"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
PROBE_RUNNER="${SCRIPT_DIR}/strategy_lab_probe_runner.sh"
CIRCULAR_LAUNCHER="${SCRIPT_DIR}/strategy_lab_circular_launcher.sh"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-e2e.XXXXXX")

cleanup()
{
    if [ -d "${TEST_ROOT}" ]; then
        find "${TEST_ROOT}" -type f -name '*.pid' -print 2>/dev/null |
            while IFS= read -r pidfile
            do
                pid=$(cat "${pidfile}" 2>/dev/null || true)
                case "${pid}" in ''|*[!0-9]*) continue ;; esac
                kill "${pid}" 2>/dev/null || true
            done
        rm -rf "${TEST_ROOT}"
    fi
}
trap cleanup EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

BIN_DIR="${TEST_ROOT}/bin"
RUN_DIR="${TEST_ROOT}/run"
LOG_DIR="${TEST_ROOT}/log"
STATE_FILE="${TEST_ROOT}/service.state"
RESTORED_FILE="${TEST_ROOT}/service.restored"
STRATEGY_FILE="${TEST_ROOT}/zapret.conf"
ARGS_FILE="${TEST_ROOT}/dvtws.args"
IPFW_LOG="${TEST_ROOT}/ipfw.log"
mkdir -p "${BIN_DIR}" "${RUN_DIR}/jobs" "${LOG_DIR}"
printf '%s\n' RUNNING > "${STATE_FILE}"
printf '%s\n' 'TRAFFIC_ARGS=--lua-desync=multisplit:pos=1' > "${STRATEGY_FILE}"
printf '%s\n' '--filter-tcp=443' '--lua-desync=multisplit:pos=1' > "${ARGS_FILE}"
: > "${IPFW_LOG}"

cat > "${BIN_DIR}/lockf" <<'MOCK'
#!/bin/sh
exit 0
MOCK

cat > "${BIN_DIR}/daemon" <<'MOCK'
#!/bin/sh
log_file=/dev/null
pid_file=
while [ "$#" -gt 0 ]
do
    case "$1" in
        -f) shift ;;
        -o) log_file="$2"; shift 2 ;;
        -p) pid_file="$2"; shift 2 ;;
        *) break ;;
    esac
done
"$@" >> "${log_file}" 2>&1 &
pid=$!
[ -z "${pid_file}" ] || printf '%s\n' "${pid}" > "${pid_file}"
exit 0
MOCK

cat > "${BIN_DIR}/timeout" <<'MOCK'
#!/bin/sh
exec "${MOCK_REAL_TIMEOUT}" "$@"
MOCK

cat > "${BIN_DIR}/curl" <<'MOCK'
#!/bin/sh
url=
for argument in "$@"
do
    case "${argument}" in https://*) url="${argument}" ;; esac
done
host=$(printf '%s' "${url}" | sed -e 's#^https://##' -e 's#/$##')
if [ "${MOCK_SCENARIO:-}" = timeout ] && [ "${host}" = yandex.ru ]; then
    sleep 3
fi
case "${host}" in
    yandex.ru)
        printf '%s\n' 'exit=0 remote_ip=203.0.113.1 http=1.1 code=200 bytes=100'
        exit 0
        ;;
    accessible.example)
        printf '%s\n' 'exit=0 remote_ip=203.0.113.20 http=1.1 code=200 bytes=100'
        exit 0
        ;;
    *)
        printf '%s\n' 'exit=28 remote_ip=203.0.113.10 http=0 code=000 bytes=0'
        exit 28
        ;;
esac
MOCK

cat > "${BIN_DIR}/drill" <<'MOCK'
#!/bin/sh
host="$1"
type="$2"
printf '%s\n' ';; ANSWER SECTION:'
case "${type}" in
    A) printf '%s. 60 IN A 203.0.113.10\n' "${host}" ;;
    AAAA) printf '%s. 60 IN AAAA 2001:db8::10\n' "${host}" ;;
esac
MOCK

cat > "${BIN_DIR}/netstat" <<'MOCK'
#!/bin/sh
exit 0
MOCK
cat > "${BIN_DIR}/openssl" <<'MOCK'
#!/bin/sh
exit 1
MOCK
cat > "${BIN_DIR}/nc" <<'MOCK'
#!/bin/sh
exit 1
MOCK
cat > "${BIN_DIR}/kldstat" <<'MOCK'
#!/bin/sh
exit 0
MOCK
cat > "${BIN_DIR}/sysctl" <<'MOCK'
#!/bin/sh
printf '%s\n' 1
MOCK
cat > "${BIN_DIR}/ipfw" <<'MOCK'
#!/bin/sh
printf '%s\n' "$*" >> "${MOCK_IPFW_LOG}"
case "$*" in
    *list*) exit 0 ;;
    *) exit 0 ;;
esac
MOCK

cat > "${BIN_DIR}/candidate" <<'MOCK'
#!/bin/sh
[ "${MOCK_SCENARIO:-}" != internal_error ] || exit 7
output="$3"
cat > "${output}" <<'JSON'
{"all_pass":true,"accepted":["multisplit"],"rejected":[],"families":[{"id":"f1","family":"multisplit","strategy":"--lua-desync=multisplit:pos=1\n","all_pass":true}]}
JSON
MOCK

cat > "${BIN_DIR}/expansion" <<'MOCK'
#!/bin/sh
output="$4"
if [ "${MOCK_SCENARIO:-}" = no_candidate ]; then
    printf '%s\n' '{"completed":0,"working":[],"candidates":[]}' > "${output}"
else
    cat > "${output}" <<'JSON'
{"completed":3,"working":["c1","c2","c3"],"candidates":[
 {"id":"c1","family":"multisplit","strategy":"--lua-desync=multisplit:pos=1\n","all_pass":true},
 {"id":"c2","family":"fake","strategy":"--lua-desync=fake:blob=fake_default_tls\n","all_pass":true},
 {"id":"c3","family":"hostfakesplit","strategy":"--lua-desync=hostfakesplit:midhost=midsld\n","all_pass":true}
]}
JSON
fi
MOCK

cat > "${BIN_DIR}/stability" <<'MOCK'
#!/bin/sh
output="$5"
if [ "${MOCK_SCENARIO:-}" = no_candidate ]; then
    printf '%s\n' '{"completed":0,"stable":[],"unstable":[],"candidates":[],"stopped_reason":"no_working_candidate"}' > "${output}"
else
    cat > "${output}" <<'JSON'
{"completed":3,"stable":["c1","c2","c3"],"unstable":[],"stopped_reason":"enough_stable_candidates","candidates":[
 {"id":"c1","family":"multisplit","strategy":"--lua-desync=multisplit:pos=1\n","stable":true,"line_count":1,"character_count":35},
 {"id":"c2","family":"fake","strategy":"--lua-desync=fake:blob=fake_default_tls\n","stable":true,"line_count":1,"character_count":45},
 {"id":"c3","family":"hostfakesplit","strategy":"--lua-desync=hostfakesplit:midhost=midsld\n","stable":true,"line_count":1,"character_count":50}
]}
JSON
fi
MOCK

cat > "${BIN_DIR}/extended" <<'MOCK'
#!/bin/sh
printf '%s\n' '{"protocols":{"tls12":{"working":null},"http":{"working":null}}}' > "$3"
MOCK
cat > "${BIN_DIR}/quic" <<'MOCK'
#!/bin/sh
printf '%s\n' '{"status":"skipped","working":null}' > "$4"
MOCK
cat > "${BIN_DIR}/udp" <<'MOCK'
#!/bin/sh
printf '%s\n' '{"status":"skipped","working":null}' > "$3"
MOCK

cat > "${BIN_DIR}/service" <<'MOCK'
#!/bin/sh
state=$(cat "${MOCK_STATE_FILE}")
hash_file()
{
    sha256sum "$1" | awk '{print $1}'
}
case "${1:-}" in
    strategy-lab)
        STRATEGY_LAB_LIFECYCLE_OWNER=1
        STRATEGY_LAB_SERVICE_SCRIPT="$0"
        export STRATEGY_LAB_LIFECYCLE_OWNER STRATEGY_LAB_SERVICE_SCRIPT
        exec "${MOCK_WORKER}" "${2:-}"
        ;;
    strategy-lab-status)
        case "${state}" in RUNNING) exit 0 ;; STOPPED) exit 1 ;; *) exit 2 ;; esac
        ;;
    strategy-lab-stop)
        printf '%s\n' STOPPED > "${MOCK_STATE_FILE}"
        ;;
    strategy-lab-start)
        printf '%s\n' RUNNING > "${MOCK_STATE_FILE}"
        : > "${MOCK_RESTORED_FILE}"
        ;;
    strategy-lab-evidence)
        config_hash=$(hash_file "${MOCK_STRATEGY_FILE}")
        args_hash=$(hash_file "${MOCK_ARGS_FILE}")
        if [ "${MOCK_SCENARIO:-}" = restore_failure ] && [ -e "${MOCK_RESTORED_FILE}" ]; then
            config_hash=restoration-mismatch
        fi
        if [ "${state}" = RUNNING ]; then
            child=true; supervisor=true; firewall_hash=normal-rules-v1
        else
            child=false; supervisor=false; firewall_hash=empty
        fi
        printf '{"schema":1,"source":"zapret_service","state":"%s",' "${state}"
        printf '"child_running":%s,"supervisor_running":%s,' "${child}" "${supervisor}"
        printf '"runtime_args_hash":"%s","effective_config_hash":"%s",' "${args_hash}" "${config_hash}"
        printf '"normal_firewall_hash":"%s"}\n' "${firewall_hash}"
        ;;
    strategy-lab-circular)
        circular_dir="${STRATEGY_LAB_RUN_DIR}/circular"
        state_file="${circular_dir}/state.json"
        stop_file="${circular_dir}/stop"
        job="$2"
        count=$(jq -r '.count' "${STRATEGY_LAB_JOBS_DIR}/${job}/shortlist.json")
        jq -nc --arg job_id "${job}" --argjson count "${count}" \
            '{state:"running",job_id:$job_id,message:"Circular validation running",reason:"",candidate_count:$count}' > "${state_file}"
        while [ ! -e "${stop_file}" ]; do sleep 1; done
        jq -nc --arg job_id "${job}" --argjson count "${count}" \
            '{state:"stopped",job_id:$job_id,message:"Circular validation stopped",reason:"requested",candidate_count:$count}' > "${state_file}"
        ;;
    *) exit 64 ;;
esac
MOCK

cat > "${BIN_DIR}/configd" <<'MOCK'
#!/bin/sh
action="$1"
shift
case "${action}" in
    strategy_lab_start) exec "${MOCK_LAUNCHER}" start "$@" ;;
    strategy_lab_status) exec "${MOCK_LAUNCHER}" status "$@" ;;
    strategy_lab_cancel) exec "${MOCK_LAUNCHER}" cancel "$@" ;;
    strategy_lab_result) exec "${MOCK_LAUNCHER}" result "$@" ;;
    strategy_lab_circular_start) exec "${MOCK_CIRCULAR_LAUNCHER}" start "$@" ;;
    strategy_lab_circular_status) exec "${MOCK_CIRCULAR_LAUNCHER}" status ;;
    strategy_lab_circular_stop) exec "${MOCK_CIRCULAR_LAUNCHER}" stop ;;
    *) exit 64 ;;
esac
MOCK

chmod 0755 "${BIN_DIR}"/*

export MOCK_REAL_TIMEOUT=$(command -v timeout)
export MOCK_STATE_FILE="${STATE_FILE}"
export MOCK_RESTORED_FILE="${RESTORED_FILE}"
export MOCK_STRATEGY_FILE="${STRATEGY_FILE}"
export MOCK_ARGS_FILE="${ARGS_FILE}"
export MOCK_IPFW_LOG="${IPFW_LOG}"
export MOCK_WORKER="${WORKER}"
export MOCK_LAUNCHER="${LAUNCHER}"
export MOCK_CIRCULAR_LAUNCHER="${CIRCULAR_LAUNCHER}"

api_call()
{
    SCRIPT_DIR="${SCRIPT_DIR}" \
    MODULE_DIR="${MODULE_DIR}" \
    WORKER_SCRIPT="${WORKER}" \
    TRANSACTION_SCRIPT="${BIN_DIR}/service" \
    DAEMON_BIN="${BIN_DIR}/daemon" \
    LOCKF_BIN="${BIN_DIR}/lockf" \
    STRATEGY_LAB_RUN_DIR="${RUN_DIR}" \
    STRATEGY_LAB_JOBS_DIR="${RUN_DIR}/jobs" \
    STRATEGY_LAB_LOG_DIR="${LOG_DIR}" \
    STRATEGY_LAB_ACTIVE_FILE="${RUN_DIR}/active.job" \
    STRATEGY_LAB_LOCK_FILE="${RUN_DIR}/launcher.lock" \
    STRATEGY_LAB_CIRCULAR_DIR="${RUN_DIR}/circular" \
    STRATEGY_LAB_TIMEOUT_BIN="${BIN_DIR}/timeout" \
    STRATEGY_LAB_CURL_BIN="${BIN_DIR}/curl" \
    STRATEGY_LAB_DRILL_BIN="${BIN_DIR}/drill" \
    STRATEGY_LAB_NETSTAT_BIN="${BIN_DIR}/netstat" \
    STRATEGY_LAB_OPENSSL_BIN="${BIN_DIR}/openssl" \
    STRATEGY_LAB_NC_BIN="${BIN_DIR}/nc" \
    STRATEGY_LAB_IPFW_BIN="${BIN_DIR}/ipfw" \
    STRATEGY_LAB_KLDSTAT_BIN="${BIN_DIR}/kldstat" \
    STRATEGY_LAB_SYSCTL_BIN="${BIN_DIR}/sysctl" \
    STRATEGY_LAB_DVTWS_BIN="${BIN_DIR}/dvtws2-unused" \
    PROBE_RUNNER="${PROBE_RUNNER}" \
    CANDIDATE_RUNNER="${BIN_DIR}/candidate" \
    EXPANSION_RUNNER="${BIN_DIR}/expansion" \
    STABILITY_RUNNER="${BIN_DIR}/stability" \
    EXTENDED_RUNNER="${BIN_DIR}/extended" \
    QUIC_RUNNER="${BIN_DIR}/quic" \
    UDP_RUNNER="${BIN_DIR}/udp" \
    STRATEGY_LAB_STAGE30_TIMEOUT="${MOCK_STAGE30_TIMEOUT:-6}" \
    STRATEGY_LAB_STAGE40_TIMEOUT=5 \
    STRATEGY_LAB_CANDIDATE_TIMEOUT=10 \
    STRATEGY_LAB_STAGE60_TIMEOUT=10 \
    STRATEGY_LAB_STAGE70_TIMEOUT=10 \
    STRATEGY_LAB_STAGE80_TIMEOUT=20 \
    STRATEGY_LAB_STANDARD_BUDGET=60 \
    STRATEGY_LAB_EXTENDED_BUDGET=30 \
    "${BIN_DIR}/configd" "$@"
}

wait_terminal()
{
    job="$1"
    attempt=0
    while [ "${attempt}" -lt 40 ]
    do
        status=$(api_call strategy_lab_status "${job}")
        state=$(printf '%s\n' "${status}" | jq -r '.state // ""')
        case "${state}" in completed|error) return 0 ;; esac
        sleep 1
        attempt=$((attempt + 1))
    done
    fail "job ${job} did not reach a terminal state"
}

assert_full_event_order()
{
    job="$1"
    events="${RUN_DIR}/jobs/${job}/events.jsonl"
    order=$(jq -r '.stage' "${events}" | awk '!seen[$0]++' | paste -sd, -)
    [ "${order}" = '00,10,20,30,40,50,60,70,80,85,90,99' ] ||
        fail "unexpected stage event order for ${job}: ${order}"
}

run_job()
{
    scenario="$1"
    mode="$2"
    initial_state="$3"
    expected_state="$4"
    expected_outcome="$5"
    target="${6:-blocked.example}"

    export MOCK_SCENARIO="${scenario}"
    rm -f "${RESTORED_FILE}"
    printf '%s\n' "${initial_state}" > "${STATE_FILE}"
    if [ "${scenario}" = timeout ]; then
        MOCK_STAGE30_TIMEOUT=1
    else
        MOCK_STAGE30_TIMEOUT=6
    fi
    export MOCK_STAGE30_TIMEOUT

    start=$(api_call strategy_lab_start "${target}" "${mode}" en)
    job=$(printf '%s\n' "${start}" | jq -r '.job_id')
    printf '%s\n' "${job}" | grep -Eq '^job\.[A-Za-z0-9]+$' ||
        fail "configd start did not return a valid job id"
    wait_terminal "${job}"
    result=$(api_call strategy_lab_result "${job}")
    printf '%s\n' "${result}" | jq -e \
        --arg state "${expected_state}" --arg outcome "${expected_outcome}" \
        '.state==$state and .outcome==$outcome and .current_stage=="99"' >/dev/null ||
        fail "unexpected terminal result for ${scenario}/${mode}"
    recovered=$(api_call strategy_lab_status -)
    printf '%s\n' "${recovered}" | jq -e --arg job "${job}" '.job_id==$job' >/dev/null ||
        fail "polling recovery did not return latest job ${job}"
    LAST_JOB="${job}"
    LAST_RESULT="${result}"
}

strategy_before=$(sha256sum "${STRATEGY_FILE}" | awk '{print $1}')
run_job success standard RUNNING completed SUCCESS
SUCCESS_JOB="${LAST_JOB}"
assert_full_event_order "${SUCCESS_JOB}"
printf '%s\n' "${LAST_RESULT}" | jq -e '
    .shortlist.count==3 and .circular_eligible==true and
    (.stages[] | select(.number=="80" and .status=="SKIPPED")) and
    .restoration.verified==true
' >/dev/null || fail 'standard success result contract is invalid'
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail 'initial RUNNING service was not restored'
strategy_after=$(sha256sum "${STRATEGY_FILE}" | awk '{print $1}')
[ "${strategy_before}" = "${strategy_after}" ] || fail 'saved Traffic Strategy changed'

run_job success extended RUNNING completed SUCCESS
assert_full_event_order "${LAST_JOB}"
printf '%s\n' "${LAST_RESULT}" | jq -e '
    .shortlist.count==3 and (.stages[] | select(.number=="80" and .status=="PASS"))
' >/dev/null || fail 'extended success result contract is invalid'

run_job no_candidate standard RUNNING completed NO_CANDIDATE
printf '%s\n' "${LAST_RESULT}" | jq -e '.shortlist.count==0 and .circular_eligible==false' >/dev/null ||
    fail 'no-candidate result contract is invalid'

run_job accessible standard RUNNING completed TARGET_ACCESSIBLE accessible.example
printf '%s\n' "${LAST_RESULT}" | jq -e '.baseline.all_accessible==true and .circular_eligible==false' >/dev/null ||
    fail 'target-accessible result contract is invalid'

run_job internal_error standard RUNNING error ERROR
printf '%s\n' "${LAST_RESULT}" | jq -e '.restoration.verified==true' >/dev/null ||
    fail 'internal error did not restore service'

run_job timeout standard RUNNING error TIMEOUT
printf '%s\n' "${LAST_RESULT}" | jq -e '
    (.stages[] | select(.number=="30" and .status=="TIMEOUT")) and
    .restoration.verified==true
' >/dev/null || fail 'timeout result contract is invalid'

run_job restore_failure standard RUNNING error RESTORE_FAILED
printf '%s\n' "${LAST_RESULT}" | jq -e '
    (.stages[] | select(.number=="90" and .status=="FAIL")) and
    .restoration.verified==false
' >/dev/null || fail 'restoration failure contract is invalid'

run_job success standard STOPPED completed SUCCESS
[ "$(cat "${STATE_FILE}")" = STOPPED ] || fail 'initial STOPPED service state was not preserved'
printf '%s\n' "${LAST_RESULT}" | jq -e '.initial_service_state=="STOPPED" and .restoration.verified==true' >/dev/null ||
    fail 'STOPPED restoration evidence is invalid'

export MOCK_SCENARIO=success
circular=$(api_call strategy_lab_circular_start "${SUCCESS_JOB}")
printf '%s\n' "${circular}" | jq -e '.state=="queued" or .state=="running"' >/dev/null ||
    fail 'eligible circular validation did not start'
attempt=0
while [ "${attempt}" -lt 10 ]
do
    circular=$(api_call strategy_lab_circular_status)
    [ "$(printf '%s\n' "${circular}" | jq -r '.state')" = running ] && break
    sleep 1
    attempt=$((attempt + 1))
done
[ "$(printf '%s\n' "${circular}" | jq -r '.state')" = running ] ||
    fail 'circular validation did not become active'
api_call strategy_lab_circular_stop >/dev/null
attempt=0
while [ "${attempt}" -lt 10 ]
do
    circular=$(api_call strategy_lab_circular_status)
    [ "$(printf '%s\n' "${circular}" | jq -r '.state')" = stopped ] && break
    sleep 1
    attempt=$((attempt + 1))
done
[ "$(printf '%s\n' "${circular}" | jq -r '.state')" = stopped ] ||
    fail 'circular validation did not stop'

[ ! -e "${RUN_DIR}/active.job" ] || fail 'active automated job marker remains'
find "${RUN_DIR}/jobs" -type f -path '*/candidate-runtime/*.pid' -print |
    grep -q . && fail 'candidate pidfile residue remains'
! pgrep -f "${TEST_ROOT}" >/dev/null 2>&1 || fail 'temporary integration process remains'

grep -Fq '[strategy_lab_start]' "${ACTIONS}" || fail 'configd start action is missing'
grep -Fq '[strategy_lab_status]' "${ACTIONS}" || fail 'configd status action is missing'
grep -Fq '[strategy_lab_result]' "${ACTIONS}" || fail 'configd result action is missing'
grep -Fq 'public function startAction(): array' "${CONTROLLER}" || fail 'API start action is missing'
grep -Fq 'public function statusAction(): array' "${CONTROLLER}" || fail 'API status action is missing'
grep -Fq 'public function cancelAction(): array' "${CONTROLLER}" || fail 'API cancel action is missing'
grep -Fq 'public function resultAction(): array' "${CONTROLLER}" || fail 'API result action is missing'

sh "${ROOT_DIR}/scripts/test-strategy-lab-active-cancel.sh" >/dev/null
sh "${ROOT_DIR}/scripts/test-strategy-lab-time-budget.sh" >/dev/null
sh "${ROOT_DIR}/scripts/test-strategy-lab-semantic-restoration.sh" >/dev/null
sh "${ROOT_DIR}/scripts/test-strategy-lab-candidate-runtime.sh" >/dev/null

sh -n "${LAUNCHER}"
sh -n "${WORKER}"
sh -n "${CIRCULAR_LAUNCHER}"
sh -n "${MODULE_DIR}/query.sh"

echo 'PASS: Strategy Lab API/configd facade, launcher, lifecycle, worker stages, result recovery, and circular flow integrate end to end'
