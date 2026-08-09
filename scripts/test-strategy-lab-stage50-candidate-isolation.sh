#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_python_launcher.sh"
JQ=$(command -v jq || true)

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python 3.13 test interpreter is unavailable: ${PYTHON}"
[ -x "${JQ}" ] || fail 'jq is unavailable'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-stage50-isolation.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
JOBS="${TMP}/jobs"
JOB="job.test"
JOB_DIR="${JOBS}/${JOB}"
ENDPOINTS="${TMP}/endpoints.txt"
CATALOG="${TMP}/families.tsv"
ARGS_DIR="${TMP}/args"
RESULT="${TMP}/family.json"
RUNNER="${TMP}/candidate.sh"
mkdir -p "${JOB_DIR}" "${ARGS_DIR}" "${TMP}/lua"
for lua in zapret-lib.lua zapret-antidpi.lua
do
    printf '%s\n' '-- fixture' > "${TMP}/lua/${lua}"
done
printf '%s\n' example.test > "${ENDPOINTS}"

for id in f1 f2 f3
do
    printf '%s\t%s\t1\t%s.args\n' "${id}" "family-${id}" "${id}" >> "${CATALOG}"
    printf '%s\n' '--lua-desync=multisplit:pos=1' > "${ARGS_DIR}/${id}.args"
done

cat > "${RUNNER}" <<'EOF'
#!/bin/sh
set -eu
output="$3"
id="$4"
family="$5"
epoch=$(jq -r .epoch_id "${STRATEGY_LAB_JOBS_DIR}/${1}/search-epoch.json")
case "${id}" in
    01-multisplit)
        jq -n --arg id "${id}" --arg family "${family}" --arg epoch "${epoch}" '{id:$id,family:$family,strategy:"",search_epoch_id:$epoch,endpoints:[],all_pass:true}' > "${output}"
        exit 0
        ;;
    02-multidisorder)
        jq -n --arg id "${id}" --arg family "${family}" --arg epoch "${epoch}" '{id:$id,family:$family,strategy:"",search_epoch_id:$epoch,endpoints:[],all_pass:false,error:true,message:"candidate runtime rejected itself"}' > "${output}"
        exit 1
        ;;
    *)
        jq -n --arg id "${id}" --arg family "${family}" --arg epoch "${epoch}" '{id:$id,family:$family,strategy:"",search_epoch_id:$epoch,endpoints:[],all_pass:false}' > "${output}"
        exit 0
        ;;
esac
EOF
chmod 0755 "${RUNNER}"

PYTHONPATH="${SCRIPT_DIR}" STRATEGY_LAB_EPOCH_JOB_DIR="${JOB_DIR}" \
STRATEGY_LAB_EPOCH_ENDPOINTS="${ENDPOINTS}" "${PYTHON}" - <<'PY'
import os
from pathlib import Path

from strategy_lab_py.endpoint_epoch import create

job = Path(os.environ["STRATEGY_LAB_EPOCH_JOB_DIR"])
endpoints = Path(os.environ["STRATEGY_LAB_EPOCH_ENDPOINTS"]).read_text().splitlines()
evidence = [{"endpoint": value, "dns_a": {"classification": "pass", "answers": ["203.0.113.10"]}} for value in endpoints]
create(job, "example.test", "domain", endpoints, evidence)
PY

STRATEGY_LAB_JOBS_DIR="${JOBS}" \
STRATEGY_LAB_LUA_DIR="${TMP}/lua" \
STRATEGY_LAB_FAMILY_CATALOG="${CATALOG}" \
STRATEGY_LAB_FAMILY_ARGS_DIR="${ARGS_DIR}" \
STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${RUNNER}" \
STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT=1 \
STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
sh "${LAUNCHER}" family screen "${JOB}" "${ENDPOINTS}" "${RESULT}"

"${JQ}" -e '
  .total==7 and .completed==7 and
  [.families[].id]==["01-multisplit","02-multidisorder","03-seqovl","04-fake","05-fake-split","06-syndata","07-hostfakesplit"] and
  .accepted==["multisplit"] and
  .rejected==["multidisorder","seqovl","fake","fake+split","syndata","hostfakesplit"] and
  .all_pass==true and
  .families[1].error==true and
  .families[1].runner_status==1 and
  .families[1].message=="candidate runtime rejected itself"
' "${RESULT}" >/dev/null || {
    cat "${RESULT}" >&2
    fail 'structured candidate-level error aborted or corrupted Stage 50 aggregation'
}

echo 'PASS: Stage 50 preserves structured candidate failures as rejected entries and continues screening'
