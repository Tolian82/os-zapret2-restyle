#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP_ROOT=$(mktemp -d /tmp/strategy-lab-expansion-test.XXXXXX)
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
lock_dir="${MOCK_EXPANSION_LOCK}.d"
mkdir "${lock_dir}" 2>/dev/null || exit 91
trap 'rmdir "${lock_dir}" 2>/dev/null || true' EXIT HUP INT TERM
printf '%s\n' "${family}:${candidate_id}" >> "${MOCK_EXPANSION_ORDER}"
if [ "${MOCK_EXPANSION_MODE:-normal}" = timeout ] && [ "${candidate_id}" = fake-rnd ]; then
    exit 124
fi
case "${candidate_id}" in
    multisplit-midsld|syndata-160301) all_pass=false; endpoint_status=FAIL ;;
    *) all_pass=true; endpoint_status=PASS ;;
esac
jq -n --arg id "${candidate_id}" --arg family "${family}" --rawfile strategy "${strategy_file}" \
    --arg endpoint_status "${endpoint_status}" --argjson all_pass "${all_pass}" \
    '{id:$id,family:$family,strategy:$strategy,endpoints:[{endpoint:"telegram.org",status:$endpoint_status}],all_pass:$all_pass}' \
    > "${result_file}"
MOCK
chmod +x "${TMP_ROOT}/bin/timeout" "${TMP_ROOT}/bin/candidate"
printf '%s\n' telegram.org > "${TMP_ROOT}/endpoints.txt"
cat > "${TMP_ROOT}/families.json" <<'JSON'
{"accepted":["multisplit","fake","syndata"],"rejected":["multidisorder","seqovl","fake+split","hostfakesplit"]}
JSON

export SCRIPT_DIR MODULE_DIR
export STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP_ROOT}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP_ROOT}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP_ROOT}/bin/timeout"
export STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${TMP_ROOT}/bin/candidate"
export STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT=5
export STRATEGY_LAB_EXPANSION_CATALOG="${MODULE_DIR}/catalog/tls13-expansion.tsv"
export STRATEGY_LAB_EXPANSION_ARGS_DIR="${MODULE_DIR}/catalog/tls13-expansion"
export MOCK_EXPANSION_LOCK="${TMP_ROOT}/expansion.lock"
export MOCK_EXPANSION_ORDER="${TMP_ROOT}/order.txt"

. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/expansion.sh"

STRATEGY_LAB_EXPANSION_TARGET=3
export STRATEGY_LAB_EXPANSION_TARGET
MOCK_EXPANSION_MODE=normal
export MOCK_EXPANSION_MODE
: > "${MOCK_EXPANSION_ORDER}"
strategy_lab_expansion_run job.test "${TMP_ROOT}/endpoints.txt" "${TMP_ROOT}/families.json" "${TMP_ROOT}/target.json"
jq -e '.completed==4 and .working==["multisplit-host","fake-repeat2","fake-rnd"] and .failed==["multisplit-midsld"] and .stopped_reason=="enough_candidates"' "${TMP_ROOT}/target.json" >/dev/null
[ "$(paste -sd, "${MOCK_EXPANSION_ORDER}")" = 'multisplit:multisplit-host,multisplit:multisplit-midsld,fake:fake-repeat2,fake:fake-rnd' ]

STRATEGY_LAB_EXPANSION_TARGET=99
export STRATEGY_LAB_EXPANSION_TARGET
MOCK_EXPANSION_MODE=timeout
export MOCK_EXPANSION_MODE
: > "${MOCK_EXPANSION_ORDER}"
strategy_lab_expansion_run job.test "${TMP_ROOT}/endpoints.txt" "${TMP_ROOT}/families.json" "${TMP_ROOT}/full.json"
jq -e '.total_available==6 and .completed==6 and .stopped_reason=="catalog_exhausted" and (.candidates[] | select(.id=="fake-rnd") | .timeout)==true and (.failed|index("fake-rnd"))!=null' "${TMP_ROOT}/full.json" >/dev/null
! grep -Eq 'multidisorder|seqovl|fake\+split|hostfakesplit' "${MOCK_EXPANSION_ORDER}"

grep -Fxq -- '--lua-desync=fake:blob=fake_default_tls:repeats=2' "${MODULE_DIR}/catalog/tls13-expansion/fake-repeat2.args"
grep -Fxq -- '--lua-desync=syndata:blob=0x1603' "${MODULE_DIR}/catalog/tls13-expansion/syndata-1603.args"
grep -Fxq -- '--lua-desync=hostfakesplit:midhost=midsld:disorder_after=-1' "${MODULE_DIR}/catalog/tls13-expansion/hostfakesplit-disorder.args"

echo 'PASS: Strategy Lab expands only accepted families and preserves ordered partial results'
