#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
TMP=$(mktemp -d /tmp/strategy-lab-unified.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/jobs/job.test" "${TMP}/circular/sessions"

fail(){ echo "FAIL: $*" >&2; exit 1; }

STRATEGY_LAB_TEST_PYTHON="${PYTHON}" sh "${ROOT_DIR}/scripts/test-strategy-lab-python-final-results.sh" >/dev/null ||
    fail 'Python unified shortlist owner regression failed'

export SCRIPT_DIR MODULE_DIR
export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}"
export STRATEGY_LAB_JOBS_DIR="${TMP}/jobs"
export STRATEGY_LAB_CIRCULAR_DIR="${TMP}/circular"
export STRATEGY_LAB_CIRCULAR_SESSIONS_DIR="${TMP}/circular/sessions"
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
        job.*) printf '%s/jobs/%s/candidate-runtime\n' "${TMP}" "$1" ;;
        *) printf '%s/circular/sessions/%s/candidate-runtime\n' "${TMP}" "$1" ;;
    esac
}
strategy_lab_candidate_args_file(){ printf '%s/args\n' "$(strategy_lab_candidate_runtime_dir "$1")"; }
strategy_lab_candidate_hostlist_file(){ printf '%s/hostlist.txt\n' "$(strategy_lab_candidate_runtime_dir "$1")"; }

. "${MODULE_DIR}/circular.sh"
strategy_lab_circular_prepare_dir

JOB_DIR="${TMP}/jobs/job.test"
printf '%s\n' example.com > "${JOB_DIR}/endpoints.txt"
cat > "${JOB_DIR}/status.json" <<'JSON'
{"revision":1,"target":"example.com","target_type":"domain","mode":"extended","state":"completed","outcome":"SUCCESS","circular_eligible":true,"circular_eligibility_reason":"eligible","circular_candidate_count":3,"stages":[{"number":"85","status":"PASS"},{"number":"90","status":"PASS"}],"restoration":{"verified":true}}
JSON
cat > "${JOB_DIR}/shortlist.json" <<'JSON'
{"count":3,"items":[
 {"id":"t1","family":"multisplit","protocol":"tls13","port":443,"strategy":"--lua-desync=multisplit:pos=1\n","profile":"--filter-tcp=443\n--filter-l7=tls\n--hostlist-domains=example.com\n--out-range=-d10\n--lua-desync=multisplit:pos=1\n","circular_eligible":true},
 {"id":"t2","family":"multidisorder","protocol":"tls13","port":443,"strategy":"--lua-desync=multidisorder:pos=1\n","profile":"--filter-tcp=443\n--filter-l7=tls\n--hostlist-domains=example.com\n--out-range=-d10\n--lua-desync=multidisorder:pos=1\n","circular_eligible":true},
 {"id":"t3","family":"fake","protocol":"tls13","port":443,"strategy":"--lua-desync=fake:blob=fake_default_tls\n","profile":"--filter-tcp=443\n--filter-l7=tls\n--hostlist-domains=example.com\n--out-range=-d10\n--lua-desync=fake:blob=fake_default_tls\n","circular_eligible":true}
],"recommendation":{"id":"t1","protocol":"tls13"},"circular_count":3,"circular_items":[
 {"id":"t1","family":"multisplit","protocol":"tls13","strategy":"--lua-desync=multisplit:pos=1\n","circular_eligible":true},
 {"id":"t2","family":"multidisorder","protocol":"tls13","strategy":"--lua-desync=multidisorder:pos=1\n","circular_eligible":true},
 {"id":"t3","family":"fake","protocol":"tls13","strategy":"--lua-desync=fake:blob=fake_default_tls\n","circular_eligible":true}
]}
JSON
cp "${JOB_DIR}/shortlist.json" "${TMP}/parent-before.json"

strategy_lab_circular_eligibility job.test >/dev/null
CIRCULAR_SESSION_ID=$(strategy_lab_circular_session_create job.test)
strategy_lab_circular_session_validate "${CIRCULAR_SESSION_ID}" job.test
strategy_lab_circular_build_profile "${CIRCULAR_SESSION_ID}"
CIRCULAR_ARGS=$(strategy_lab_candidate_args_file "${CIRCULAR_SESSION_ID}")
[ "$(grep -Ec ':strategy=[1-3]$' "${CIRCULAR_ARGS}")" -eq 3 ] ||
    fail 'private circular profile does not contain exactly three frozen TLS 1.3 strategies'
cmp -s "${TMP}/parent-before.json" "${JOB_DIR}/shortlist.json" ||
    fail 'private circular consumer mutated the parent Python-published shortlist'
[ ! -e "${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh" ] ||
    fail 'retired shell final replay owner is still packaged'
[ ! -e "${MODULE_DIR}/worker_result.sh" ] ||
    fail 'retired shell automated eligibility owner is still packaged'

echo 'PASS: Python publishes the automated unified shortlist while private circular consumes only the frozen TLS 1.3 subset without mutating parent evidence'
