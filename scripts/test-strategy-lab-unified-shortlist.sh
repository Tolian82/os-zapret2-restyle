#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP=$(mktemp -d /tmp/strategy-lab-unified.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/jobs/job.test" "${TMP}/jobs/job.standard" "${TMP}/lua"

cat > "${TMP}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK
cat > "${TMP}/bin/profile-replay" <<'MOCK'
#!/bin/sh
result=$3
profile=$6
target=$7
protocol=$9
port=${10}
count_file=${MOCK_PROFILE_REPLAY_COUNT:?}
count=0
[ ! -r "${count_file}" ] || count=$(cat "${count_file}")
printf '%s\n' "$((count + 1))" > "${count_file}"
case "${protocol}" in
    udp) selected_ip=203.0.113.53 ;;
    *) selected_ip=203.0.113.10 ;;
esac
jq -nc --rawfile profile "${profile}" --arg target "${target}" \
    --arg protocol "${protocol}" --argjson port "${port}" --arg selected_ip "${selected_ip}" '
    {
      strategy:$profile,
      profile:$profile,
      profile_exact:true,
      target:$target,
      protocol:$protocol,
      port:$port,
      endpoints:[{selected_ip:$selected_ip,remote_ip:$selected_ip,status:"PASS"}],
      all_pass:true
    }
' > "${result}"
MOCK
chmod +x "${TMP}/bin/"*

export SCRIPT_DIR MODULE_DIR
export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}"
export STRATEGY_LAB_JOBS_DIR="${TMP}/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout"
export STRATEGY_LAB_PROFILE_REPLAY_RUNNER="${TMP}/bin/profile-replay"
export STRATEGY_LAB_PROFILE_ENV_BIN=$(command -v env)
export MOCK_PROFILE_REPLAY_COUNT="${TMP}/replay-count"
export STRATEGY_LAB_LUA_DIR="${TMP}/lua"
export STRATEGY_LAB_DIVERT_PORT=9989

strategy_lab_job_dir(){ printf '%s/jobs/%s\n' "${TMP}" "$1"; }
strategy_lab_status_file(){ printf '%s/jobs/%s/status.json\n' "${TMP}" "$1"; }
strategy_lab_job_id_valid(){ case "$1" in job.*) return 0 ;; *) return 1 ;; esac; }
strategy_lab_domain_valid(){ case "$1" in *.*) return 0 ;; *) return 1 ;; esac; }
strategy_lab_ipv4_valid()
{
    printf '%s\n' "$1" | awk -F. 'NF==4 {for(i=1;i<=4;i++) if($i !~ /^[0-9]+$/ || $i>255) exit 1; ok=1} END{exit !ok}'
}
strategy_lab_candidate_runtime_dir()
{
    case "$1" in
        job.test|job.standard)
            printf '%s/jobs/%s/candidate-runtime\n' "${TMP}" "$1"
            ;;
        *)
            printf '%s/circular/sessions/%s/candidate-runtime\n' "${TMP}" "$1"
            ;;
    esac
}
strategy_lab_candidate_args_file(){ printf '%s/args\n' "$(strategy_lab_candidate_runtime_dir "$1")"; }
strategy_lab_candidate_hostlist_file(){ printf '%s/hostlist.txt\n' "$(strategy_lab_candidate_runtime_dir "$1")"; }

. "${MODULE_DIR}/profile.sh"
. "${MODULE_DIR}/worker_result.sh"
. "${MODULE_DIR}/circular.sh"
strategy_lab_circular_prepare_dir

JOB_DIR="${TMP}/jobs/job.test"
printf '%s\n' example.com > "${JOB_DIR}/endpoints.txt"
cat > "${JOB_DIR}/status.json" <<'JSON'
{"target":"example.com","target_type":"domain","mode":"extended","state":"completed","outcome":"SUCCESS","stages":[{"number":"85","status":"PASS"},{"number":"90","status":"PASS"}],"restoration":{"verified":true}}
JSON
cat > "${JOB_DIR}/stability.json" <<'JSON'
{"candidates":[
 {"id":"t1","family":"multisplit","strategy":"--lua-desync=multisplit:pos=1\n","stable":true,"line_count":1,"character_count":30},
 {"id":"t2","family":"multidisorder","strategy":"--lua-desync=multidisorder:pos=1\n","stable":true,"line_count":1,"character_count":35},
 {"id":"t3","family":"fake","strategy":"--lua-desync=fake:blob=fake_default_tls\n","stable":true,"line_count":1,"character_count":40}
]}
JSON
cat > "${JOB_DIR}/extended-tcp.json" <<'JSON'
{"protocols":{"tls12":{"working":{"id":"x12","family":"multisplit","strategy":"--lua-desync=multisplit:pos=2\n","endpoints":[{"selected_ip":"203.0.113.10"}],"all_pass":true}},"http":{"working":{"id":"xh","family":"multidisorder","strategy":"--lua-desync=multidisorder:pos=2\n","endpoints":[{"selected_ip":"203.0.113.10"}],"all_pass":true}}}}
JSON
cat > "${JOB_DIR}/quic.json" <<'JSON'
{"working":{"id":"xq","family":"fake","strategy":"--lua-desync=fake:blob=fake_quic\n","endpoints":[{"selected_ip":"203.0.113.10"}],"all_pass":true}}
JSON
cat > "${JOB_DIR}/udp.json" <<'JSON'
{"port":5555,"working":{"id":"xu","family":"ipfrag","strategy":"--lua-desync=ipfrag:udp=8\n","endpoints":[{"selected_ip":"203.0.113.53"}],"all_pass":true}}
JSON

strategy_lab_shortlist_build "${JOB_DIR}/stability.json" "${JOB_DIR}/shortlist.json"
"${STRATEGY_LAB_JQ}" -e '.count==5 and ([.items[].protocol]|join(","))=="tls13,tls12,http,quic,udp" and .recommendation.protocol=="tls13" and .circular_count==3 and ([.circular_items[].protocol]|unique)==["tls13"] and all(.items[];.profile_replay.verified==true and .profile_replay.attempt_count==3 and .profile_replay.pass_count==3)' "${JOB_DIR}/shortlist.json" >/dev/null
[ "$(cat "${TMP}/replay-count")" -eq 21 ]
"${STRATEGY_LAB_JQ}" -r '.items[]|select(.protocol=="tls13")|.profile' "${JOB_DIR}/shortlist.json" | grep -Fq -- '--filter-tcp=443'
"${STRATEGY_LAB_JQ}" -r '.items[]|select(.protocol=="tls12")|.profile' "${JOB_DIR}/shortlist.json" | grep -Fq -- '--filter-l7=tls'
"${STRATEGY_LAB_JQ}" -r '.items[]|select(.protocol=="http")|.profile' "${JOB_DIR}/shortlist.json" | grep -Fq -- '--filter-tcp=80'
"${STRATEGY_LAB_JQ}" -r '.items[]|select(.protocol=="quic")|.profile' "${JOB_DIR}/shortlist.json" | grep -Fq -- '--filter-udp=443'
UDP_PROFILE=$("${STRATEGY_LAB_JQ}" -r '.items[]|select(.protocol=="udp")|.profile' "${JOB_DIR}/shortlist.json")
printf '%s\n' "${UDP_PROFILE}" | grep -Fq -- '--filter-udp=5555'
printf '%s\n' "${UDP_PROFILE}" | grep -Fq -- '--ipset-ip=203.0.113.53'
if printf '%s\n' "${UDP_PROFILE}" | grep -Fq -- '--filter-l7='; then exit 1; fi

JOB_ID=job.test
WORKER_FINAL_STATE=completed
WORKER_FINAL_OUTCOME=SUCCESS
worker_result_set_circular_eligibility
"${STRATEGY_LAB_JQ}" -e '.circular_eligible==true and .circular_eligibility_reason=="eligible" and .circular_candidate_count==3' "${JOB_DIR}/status.json" >/dev/null
strategy_lab_circular_eligibility job.test >/dev/null
CIRCULAR_SESSION_ID=$(strategy_lab_circular_session_create job.test)
strategy_lab_circular_session_validate "${CIRCULAR_SESSION_ID}" job.test
strategy_lab_circular_build_profile "${CIRCULAR_SESSION_ID}"
CIRCULAR_ARGS=$(strategy_lab_candidate_args_file "${CIRCULAR_SESSION_ID}")
[ "$(grep -Ec ':strategy=[1-3]$' "${CIRCULAR_ARGS}")" -eq 3 ]
if grep -Eq 'pos=2|fake_quic|ipfrag' "${CIRCULAR_ARGS}"; then exit 1; fi
[ ! -e "${JOB_DIR}/candidate-runtime" ]

STANDARD_DIR="${TMP}/jobs/job.standard"
printf '%s\n' example.com > "${STANDARD_DIR}/endpoints.txt"
printf '%s\n' '{"target":"example.com","target_type":"domain","mode":"standard"}' > "${STANDARD_DIR}/status.json"
cp "${JOB_DIR}/stability.json" "${STANDARD_DIR}/stability.json"
strategy_lab_shortlist_build "${STANDARD_DIR}/stability.json" "${STANDARD_DIR}/shortlist.json"
"${STRATEGY_LAB_JQ}" -e '.count==3 and .circular_count==3 and all(.items[];.protocol=="tls13")' "${STANDARD_DIR}/shortlist.json" >/dev/null

grep -Fq 'PROTOCOL="${9:-tls13}"' "${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh"
grep -Fq 'source_module quic_candidate' "${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh"
grep -Fq 'source_module udp_candidate' "${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh"
echo 'PASS: verified TLS 1.3, TLS 1.2, HTTP, QUIC, and UDP profiles share one deterministic shortlist'
