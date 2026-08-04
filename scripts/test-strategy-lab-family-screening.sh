#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
CATALOG="${MODULE_DIR}/catalog/tls13-families.tsv"
TMP_ROOT=$(mktemp -d /tmp/strategy-lab-family-test.XXXXXX)
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM
mkdir -p "${TMP_ROOT}/bin" "${TMP_ROOT}/run/jobs/job.test"

cat > "${TMP_ROOT}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK

cat > "${TMP_ROOT}/bin/candidate" <<'MOCK'
#!/bin/sh
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
        [ "${family}" != seqovl ] || exit 124
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
chmod +x "${TMP_ROOT}/bin/timeout" "${TMP_ROOT}/bin/candidate"
printf '%s\n' telegram.org > "${TMP_ROOT}/endpoints.txt"

export SCRIPT_DIR MODULE_DIR
export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP_ROOT}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP_ROOT}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP_ROOT}/bin/timeout"
export STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${TMP_ROOT}/bin/candidate"
export STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT=5
export STRATEGY_LAB_FAMILY_CATALOG="${CATALOG}"
export STRATEGY_LAB_FAMILY_ARGS_DIR="${MODULE_DIR}/catalog/tls13"
export MOCK_FAMILY_LOCK="${TMP_ROOT}/family.lock"
export MOCK_FAMILY_ORDER="${TMP_ROOT}/order.txt"

. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/family.sh"

run_screen()
{
    mode="$1"
    output="$2"
    : > "${MOCK_FAMILY_ORDER}"
    MOCK_FAMILY_MODE="${mode}"
    export MOCK_FAMILY_MODE
    strategy_lab_family_screen job.test "${TMP_ROOT}/endpoints.txt" "${output}"
    [ "$(paste -sd, "${MOCK_FAMILY_ORDER}")" = '01-multisplit,02-multidisorder,03-seqovl,04-fake,05-fake-split,06-syndata,07-hostfakesplit' ]
}

run_screen all "${TMP_ROOT}/all.json"
jq -e '.total==7 and .completed==7 and (.accepted|length)==7 and (.rejected|length)==0 and .all_pass==true' "${TMP_ROOT}/all.json" >/dev/null

run_screen mixed "${TMP_ROOT}/mixed.json"
jq -e '.accepted==["multisplit","fake","hostfakesplit"] and .rejected==["multidisorder","seqovl","fake+split","syndata"] and .all_pass==true' "${TMP_ROOT}/mixed.json" >/dev/null

run_screen timeout "${TMP_ROOT}/timeout.json"
jq -e '.completed==7 and (.families[] | select(.family=="seqovl") | .timeout)==true and (.rejected|index("seqovl"))!=null' "${TMP_ROOT}/timeout.json" >/dev/null

grep -Fxq -- '--lua-desync=multisplit:pos=1:seqovl=1' "${MODULE_DIR}/catalog/tls13/03-seqovl.args"
grep -Fxq -- '--lua-desync=fake:blob=fake_default_tls' "${MODULE_DIR}/catalog/tls13/05-fake-split.args"
grep -Fxq -- '--lua-desync=multisplit:pos=1' "${MODULE_DIR}/catalog/tls13/05-fake-split.args"
grep -Fxq -- '--lua-desync=syndata' "${MODULE_DIR}/catalog/tls13/06-syndata.args"
grep -Fxq -- '--lua-desync=hostfakesplit' "${MODULE_DIR}/catalog/tls13/07-hostfakesplit.args"

echo 'PASS: Strategy Lab TLS 1.3 family screening order, isolation, catalog, and classification'
