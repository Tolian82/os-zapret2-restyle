#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
RUNNER="${SCRIPT_DIR}/strategy_lab_family_runner.sh"
CATALOG="${MODULE_DIR}/catalog/tls13-families.tsv"
TMP_ROOT=$(mktemp -d /tmp/strategy-lab-family-test.XXXXXX)
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM
mkdir -p "${TMP_ROOT}/bin" "${TMP_ROOT}/lua" "${TMP_ROOT}/run/jobs/job.test"
for lua in zapret-lib.lua zapret-antidpi.lua
do
    printf '%s\n' '-- fixture' > "${TMP_ROOT}/lua/${lua}"
done

cat > "${TMP_ROOT}/bin/candidate" <<'MOCK'
#!/bin/sh
set -eu
result_file="$3"
candidate_id="$4"
family="$5"
strategy_file="$6"
lock_dir="${MOCK_FAMILY_LOCK}.d"
mkdir "${lock_dir}" 2>/dev/null || exit 91
trap 'rmdir "${lock_dir}" 2>/dev/null || true' EXIT HUP INT TERM
printf '%s\n' "${candidate_id}" >> "${MOCK_FAMILY_ORDER}"
case "${MOCK_FAMILY_MODE:-all}" in
    mixed)
        case "${family}" in
            multisplit|fake|hostfakesplit) all_pass=true ;;
            *) all_pass=false ;;
        esac
        ;;
    timeout)
        if [ "${family}" = seqovl ]; then
            sleep 2
        fi
        all_pass=true
        ;;
    *)
        all_pass=true
        ;;
esac
if [ "${all_pass}" = true ]; then endpoint_status=PASS; else endpoint_status=FAIL; fi
jq -n \
    --arg id "${candidate_id}" \
    --arg family "${family}" \
    --rawfile strategy "${strategy_file}" \
    --arg endpoint_status "${endpoint_status}" \
    --argjson all_pass "${all_pass}" \
    '{id:$id,family:$family,strategy:$strategy,endpoints:[{endpoint:"telegram.org",status:$endpoint_status}],all_pass:$all_pass}' \
    > "${result_file}"
MOCK
chmod +x "${TMP_ROOT}/bin/candidate"
printf '%s\n' telegram.org > "${TMP_ROOT}/endpoints.txt"

export SCRIPT_DIR MODULE_DIR
export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP_ROOT}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP_ROOT}/run/jobs"
export STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${TMP_ROOT}/bin/candidate"
export STRATEGY_LAB_FAMILY_CATALOG="${CATALOG}"
export STRATEGY_LAB_FAMILY_ARGS_DIR="${MODULE_DIR}/catalog/tls13"
export STRATEGY_LAB_PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
export STRATEGY_LAB_LUA_DIR="${TMP_ROOT}/lua"
export MOCK_FAMILY_LOCK="${TMP_ROOT}/family.lock"
export MOCK_FAMILY_ORDER="${TMP_ROOT}/order.txt"

run_screen()
{
    mode="$1"
    output="$2"
    timeout="$3"
    : > "${MOCK_FAMILY_ORDER}"
    MOCK_FAMILY_MODE="${mode}"
    STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT="${timeout}"
    export MOCK_FAMILY_MODE STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT
    sh "${RUNNER}" job.test "${TMP_ROOT}/endpoints.txt" "${output}"
    [ "$(paste -sd, "${MOCK_FAMILY_ORDER}")" = '01-multisplit,02-multidisorder,03-seqovl,04-fake,05-fake-split,06-syndata,07-hostfakesplit' ]
}

run_screen all "${TMP_ROOT}/all.json" 5
jq -e '.total==7 and .completed==7 and (.accepted|length)==7 and (.rejected|length)==0 and .all_pass==true' "${TMP_ROOT}/all.json" >/dev/null

run_screen mixed "${TMP_ROOT}/mixed.json" 5
jq -e '.accepted==["multisplit","fake","hostfakesplit"] and .rejected==["multidisorder","seqovl","fake+split","syndata"] and .all_pass==true' "${TMP_ROOT}/mixed.json" >/dev/null

run_screen timeout "${TMP_ROOT}/timeout.json" 0.2
jq -e '.completed==7 and (.families[] | select(.family=="seqovl") | .timeout)==true and (.rejected|index("seqovl"))!=null' "${TMP_ROOT}/timeout.json" >/dev/null

grep -Fxq -- '--lua-desync=multisplit:pos=1:seqovl=1' "${MODULE_DIR}/catalog/tls13/03-seqovl.args"
grep -Fxq -- '--lua-desync=fake:blob=fake_default_tls' "${MODULE_DIR}/catalog/tls13/05-fake-split.args"
grep -Fxq -- '--lua-desync=multisplit:pos=1' "${MODULE_DIR}/catalog/tls13/05-fake-split.args"
grep -Fxq -- '--lua-desync=syndata' "${MODULE_DIR}/catalog/tls13/06-syndata.args"
grep -Fxq -- '--lua-desync=hostfakesplit' "${MODULE_DIR}/catalog/tls13/07-hostfakesplit.args"

echo 'PASS: Python Strategy Lab TLS 1.3 family screening preserves native-graph order, isolation, timeout, compatibility fixtures, and classification'
