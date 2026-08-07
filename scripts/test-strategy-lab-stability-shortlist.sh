#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP=$(mktemp -d /tmp/strategy-lab-stability-test.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test"
cat > "${TMP}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK
cat > "${TMP}/bin/candidate" <<'MOCK'
#!/bin/sh
[ "${STRATEGY_LAB_ENDPOINT_PROBE_MODE:-}" = sequential ] || exit 92
lock="${MOCK_STABILITY_LOCK}.d"
mkdir "${lock}" 2>/dev/null || exit 91
trap 'rmdir "${lock}" 2>/dev/null || true' EXIT HUP INT TERM
result=$3; id=$4; family=$5; strategy_file=$6
count_file="${MOCK_STABILITY_COUNTS}/${id}"
count=0; [ ! -r "${count_file}" ] || count=$(cat "${count_file}")
count=$((count+1)); printf '%s\n' "${count}" > "${count_file}"
printf '%s:%s\n' "${id}" "${count}" >> "${MOCK_STABILITY_ORDER}"
all_pass=true
[ "${id}:${count}" != 'c2:2' ] || all_pass=false
if [ "${all_pass}" = true ]; then status=PASS; else status=FAIL; fi
jq -n --arg id "${id}" --arg family "${family}" --rawfile strategy "${strategy_file}" --arg status "${status}" --argjson all_pass "${all_pass}" '{id:$id,family:$family,strategy:$strategy,endpoints:[{endpoint:"telegram.org",status:$status}],all_pass:$all_pass}' > "${result}"
MOCK
chmod +x "${TMP}/bin/"*
mkdir -p "${TMP}/counts"
printf 'telegram.org\nweb.telegram.org\n' > "${TMP}/endpoints.txt"
cat > "${TMP}/expansion.json" <<'JSON'
{"candidates":[
 {"id":"c1","family":"multisplit","strategy":"--lua-desync=multisplit:pos=1\n","all_pass":true},
 {"id":"c2","family":"fake","strategy":"--lua-desync=fake:blob=fake_default_tls\n","all_pass":true},
 {"id":"c3","family":"syndata","strategy":"--lua-desync=syndata:blob=0x1603\n","all_pass":true},
 {"id":"c4","family":"hostfakesplit","strategy":"--lua-desync=hostfakesplit:midhost=midsld\n","all_pass":true}
]}
JSON
printf '%s\n' '{"families":[]}' > "${TMP}/families.json"
export SCRIPT_DIR MODULE_DIR STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run" STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout" STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER="${TMP}/bin/candidate"
export STRATEGY_LAB_STABILITY_TARGET=3 STRATEGY_LAB_STABILITY_MAX_CANDIDATES=5 STRATEGY_LAB_STABILITY_ATTEMPTS=3
export STRATEGY_LAB_ENV_BIN=$(command -v env)
export MOCK_STABILITY_LOCK="${TMP}/lock" MOCK_STABILITY_COUNTS="${TMP}/counts" MOCK_STABILITY_ORDER="${TMP}/order"
. "${MODULE_DIR}/common.sh"
. "${MODULE_DIR}/stability.sh"
. "${MODULE_DIR}/profile.sh"
strategy_lab_stability_run job.test "${TMP}/endpoints.txt" "${TMP}/expansion.json" "${TMP}/families.json" "${TMP}/stability.json"
strategy_lab_shortlist_build "${TMP}/stability.json" "${TMP}/shortlist.json"
jq -e '.completed==4 and .stable==["c1","c3","c4"] and .unstable==["c2"] and .stopped_reason=="enough_stable_candidates"' "${TMP}/stability.json" >/dev/null
jq -e '.count==3 and .recommendation.id=="c1" and .circular_count==3' "${TMP}/shortlist.json" >/dev/null
[ "$(wc -l < "${TMP}/order" | tr -d ' ')" -eq 12 ]
[ "$(grep -c '^c2:' "${TMP}/order")" -eq 3 ]
! grep -Eq '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${MODULE_DIR}/stability.sh"
grep -Eq '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${MODULE_DIR}/profile.sh"
echo 'PASS: Strategy Lab stability requires sequential 3-of-3 confirmation and profile.sh builds the bounded unified shortlist'
