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

"${PYTHON}" -m py_compile \
    "${SCRIPT_DIR}/strategy_lab_py/request.py" \
    "${SCRIPT_DIR}/strategy_lab_py/telemetry.py" \
    "${SCRIPT_DIR}/strategy_lab_py/endpoint_epoch.py" \
    "${SCRIPT_DIR}/strategy_lab_py/resources.py" \
    "${SCRIPT_DIR}/strategy_lab_py/candidate_spec.py" \
    "${SCRIPT_DIR}/strategy_lab_py/candidate.py" \
    "${SCRIPT_DIR}/strategy_lab_py/search_graph.py" \
    "${SCRIPT_DIR}/strategy_lab_py/search.py" \
    "${SCRIPT_DIR}/strategy_lab_py/extended.py" \
    "${SCRIPT_DIR}/strategy_lab_py/compat.py"

grep -Fq 'strategy_lab_stage60_parallel_runner.sh' "${SCRIPT_DIR}/strategy_lab_expansion_runner.sh" || fail 'expansion runner is not routed to the Python-owned Stage-60 parallel owner'
grep -Fq 'stage60-parallel expand' "${SCRIPT_DIR}/strategy_lab_stage60_parallel_runner.sh" || fail 'Stage-60 parallel owner is not Python-owned'
grep -Fq 'search stabilize' "${SCRIPT_DIR}/strategy_lab_stability_runner.sh" || fail 'stability runner is not Python-owned'
grep -Fq 'extended tcp' "${SCRIPT_DIR}/strategy_lab_extended_runner.sh" || fail 'extended TCP runner is not Python-owned'
grep -Fq 'extended quic' "${SCRIPT_DIR}/strategy_lab_quic_runner.sh" || fail 'QUIC runner is not Python-owned'
grep -Fq 'extended udp' "${SCRIPT_DIR}/strategy_lab_udp_runner.sh" || fail 'UDP runner is not Python-owned'
grep -Fq 'STRATEGY_LAB_CANDIDATE_PROTOCOL=quic' "${SCRIPT_DIR}/strategy_lab_quic_candidate_runner.sh" || fail 'QUIC candidate compatibility wrapper is missing'
grep -Fq 'STRATEGY_LAB_CANDIDATE_PROTOCOL=udp' "${SCRIPT_DIR}/strategy_lab_udp_candidate_runner.sh" || fail 'UDP candidate compatibility wrapper is missing'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-python-search.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
JOBS="${TMP}/jobs"
JOB="job.test"
JOB_DIR="${JOBS}/${JOB}"
mkdir -p "${JOB_DIR}" "${TMP}/bin" "${TMP}/lua" "${TMP}/fake"
for lua in zapret-lib.lua zapret-antidpi.lua
do
  printf '%s\n' '-- fixture' > "${TMP}/lua/${lua}"
done
printf '%s\n' fake > "${TMP}/fake/fake_tls_7.bin"
printf '%s\n' example.test > "${TMP}/endpoints.txt"
printf '%s\n' 'payload' > "${TMP}/payload.bin"

PYTHONPATH="${SCRIPT_DIR}" STRATEGY_LAB_EPOCH_JOB_DIR="${JOB_DIR}" \
STRATEGY_LAB_EPOCH_ENDPOINTS="${TMP}/endpoints.txt" "${PYTHON}" - <<'PY'
import os
from pathlib import Path

from strategy_lab_py.endpoint_epoch import create

job = Path(os.environ["STRATEGY_LAB_EPOCH_JOB_DIR"])
endpoints = Path(os.environ["STRATEGY_LAB_EPOCH_ENDPOINTS"]).read_text().splitlines()
evidence = [
    {
        "endpoint": endpoint,
        "dns_a": {"classification": "pass", "answers": ["203.0.113.10"]},
    }
    for endpoint in endpoints
]
create(job, "example.test", "domain", endpoints, evidence)
PY
EPOCH_ID=$("${JQ}" -r .epoch_id "${JOB_DIR}/search-epoch.json")

FAKE="${TMP}/bin/candidate"
LOG="${TMP}/candidate.log"
cat > "${FAKE}" <<'MOCK'
#!/bin/sh
set -eu
result="$3"; id="$4"; family="$5"; strategy="$6"
protocol="${STRATEGY_LAB_CANDIDATE_PROTOCOL:-tls13}"
epoch=$(jq -r .epoch_id "${STRATEGY_LAB_JOBS_DIR}/${1}/search-epoch.json")
printf '%s|%s|%s|%s|%s\n' "${protocol}" "${id}" "${STRATEGY_LAB_ENDPOINT_PROBE_MODE:-}" "${STRATEGY_LAB_UDP_PORT:-}" "${STRATEGY_LAB_UDP_PAYLOAD_FILE:-}" >> "${MOCK_LOG}"
case "${id}" in
  multisplit-midsld|fbase|tls12-fake|http-multidisorder|quic-fake-2|udp-ipfrag-16) pass=true ;;
  *) pass=false ;;
esac
jq -n --arg id "${id}" --arg family "${family}" --arg epoch "${epoch}" \
  --rawfile strategy "${strategy}" --arg protocol "${protocol}" --argjson pass "${pass}" \
  '{id:$id,family:$family,strategy:$strategy,protocol:$protocol,search_epoch_id:$epoch,endpoints:[{endpoint:"example.test",selected_ip:"203.0.113.10",status:(if $pass then "PASS" else "FAIL" end)}],all_pass:$pass}' > "${result}"
MOCK
chmod 0755 "${FAKE}"

"${JQ}" -n --arg epoch "${EPOCH_ID}" '{
  total:2,completed:2,search_epoch_id:$epoch,
  families:[
    {id:"fbase1",family:"multisplit",strategy:"--out-range=-d10\n--lua-desync=multisplit:pos=2\n",search_epoch_id:$epoch,endpoints:[],all_pass:true},
    {id:"fbase2",family:"fake",strategy:"--out-range=-d10\n--lua-desync=fake:blob=fake_default_tls\n",search_epoch_id:$epoch,endpoints:[],all_pass:false}
  ],accepted:["multisplit"],rejected:["fake"],all_pass:true
}' > "${TMP}/family.json"
"${JQ}" -n --arg epoch "${EPOCH_ID}" '{
  total:2,completed:2,search_epoch_id:$epoch,
  families:[
    {id:"fbase1",family:"multisplit",strategy:"--out-range=-d10\n--lua-desync=multisplit:pos=2\n",search_epoch_id:$epoch,endpoints:[],all_pass:false},
    {id:"fbase2",family:"fake",strategy:"--out-range=-d10\n--lua-desync=fake:blob=fake_default_tls\n",search_epoch_id:$epoch,endpoints:[],all_pass:false}
  ],accepted:[],rejected:["multisplit","fake"],all_pass:false
}' > "${TMP}/family-none.json"

COMMON_ENV="STRATEGY_LAB_JOBS_DIR=${JOBS} STRATEGY_LAB_PYTHON_BIN=${PYTHON} STRATEGY_LAB_LUA_DIR=${TMP}/lua STRATEGY_LAB_FAKE_DIR=${TMP}/fake MOCK_LOG=${LOG}"

env ${COMMON_ENV} \
  STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${FAKE}" \
  STRATEGY_LAB_EXPANSION_TARGET=99 \
  sh "${LAUNCHER}" search expand "${JOB}" "${TMP}/endpoints.txt" "${TMP}/family.json" "${TMP}/expansion.json"
"${JQ}" -e '.total_graph_nodes==16 and .total_available==16 and .completed==16 and .working==["multisplit-midsld"] and (.failed|length)==15 and .stopped_reason=="graph_exhausted" and (.search_epoch_id|startswith("se1-"))' "${TMP}/expansion.json" >/dev/null || fail 'Stage-50 evidence priority/reachability contract failed'
[ "$(sed -n '1,2p' "${LOG}" | cut -d '|' -f 2 | paste -sd, -)" = 'multisplit-host,multisplit-midsld' ] || fail 'accepted Stage-50 evidence did not affect graph priority without gating other families'

: > "${LOG}"
env ${COMMON_ENV} \
  STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${FAKE}" \
  STRATEGY_LAB_EXPANSION_TARGET=1 \
  sh "${LAUNCHER}" search expand "${JOB}" "${TMP}/endpoints.txt" "${TMP}/family-none.json" "${TMP}/expansion.json"
"${JQ}" -e '.total_available==16 and .completed==2 and .working==["multisplit-midsld"] and .failed==["multisplit-host"] and .stopped_reason=="enough_candidates"' "${TMP}/expansion.json" >/dev/null || fail 'all-rejected Stage-50 evidence still gated Stage-60 reachability'
[ "$(sed -n '1,2p' "${LOG}" | cut -d '|' -f 2 | paste -sd, -)" = 'multisplit-host,multisplit-midsld' ] || fail 'all-rejected Stage-50 evidence did not retain graph reachability/order'

env ${COMMON_ENV} \
  STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER="${FAKE}" \
  STRATEGY_LAB_STABILITY_ATTEMPTS=3 \
  STRATEGY_LAB_STABILITY_TARGET=1 \
  sh "${LAUNCHER}" search stabilize "${JOB}" "${TMP}/endpoints.txt" "${TMP}/expansion.json" "${TMP}/family-none.json" "${TMP}/stability.json"
"${JQ}" -e '.completed==1 and (.stable|length)==1 and .candidates[0].stable==true and (.candidates[0].attempts|length)==3 and .stopped_reason=="enough_stable_candidates" and .early_stop.triggered==true' "${TMP}/stability.json" >/dev/null || fail 'Python stability contract failed'
[ "$(grep -c '|sequential|' "${LOG}")" -eq 3 ] || fail 'stability attempts were not forced to sequential fresh-connection mode'

# Existing extended TCP catalog: first candidate per protocol fails, second succeeds.
env ${COMMON_ENV} \
  MODULE_DIR="${SCRIPT_DIR}/strategy_lab" \
  STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER="${FAKE}" \
  sh "${LAUNCHER}" extended tcp "${JOB}" "${TMP}/endpoints.txt" "${TMP}/extended.json"
"${JQ}" -e '.protocols.tls12.working.id=="tls12-fake" and .protocols.http.working.id=="http-multidisorder" and (.protocols.tls12.tested|length)==2 and (.protocols.http.tested|length)==2' "${TMP}/extended.json" >/dev/null || fail 'Python extended TCP contract failed'

grep -Fq 'tls12|tls12-multisplit|' "${LOG}" || fail 'TLS 1.2 candidate protocol environment missing'
grep -Fq 'http|http-multisplit|' "${LOG}" || fail 'HTTP candidate protocol environment missing'

# The control probe may report QUIC blocked; explicit Enable QUIC must still run candidates.
printf '%s\n' '{"quic_ipv4":"closed"}' > "${TMP}/network-closed.json"
env ${COMMON_ENV} MODULE_DIR="${SCRIPT_DIR}/strategy_lab" STRATEGY_LAB_QUIC_CANDIDATE_RUNNER="${FAKE}" \
  sh "${LAUNCHER}" extended quic "${JOB}" "${TMP}/endpoints.txt" "${TMP}/network-closed.json" "${TMP}/quic-closed.json"
"${JQ}" -e '.enabled==true and .status=="working" and .working.id=="quic-fake-2" and (.tested|length)==2' "${TMP}/quic-closed.json" >/dev/null || fail 'Python QUIC search was still gated by the blocked control probe'
grep -Fq 'quic|quic-fake-1|' "${LOG}" || fail 'QUIC candidate protocol environment missing'

env ${COMMON_ENV} MODULE_DIR="${SCRIPT_DIR}/strategy_lab" STRATEGY_LAB_UDP_CANDIDATE_RUNNER="${FAKE}" \
  sh "${LAUNCHER}" extended udp "${JOB}" "${TMP}/endpoints.txt" "${TMP}/udp-skipped.json"
"${JQ}" -e '.status=="skipped" and .reason=="udp_port_not_configured" and (.tested|length)==0' "${TMP}/udp-skipped.json" >/dev/null || fail 'Python UDP unconfigured skip contract failed'

env ${COMMON_ENV} MODULE_DIR="${SCRIPT_DIR}/strategy_lab" STRATEGY_LAB_UDP_CANDIDATE_RUNNER="${FAKE}" \
  STRATEGY_LAB_UDP_PORT=3478 STRATEGY_LAB_UDP_PAYLOAD_FILE="${TMP}/payload.bin" \
  sh "${LAUNCHER}" extended udp "${JOB}" "${TMP}/endpoints.txt" "${TMP}/udp.json"
"${JQ}" -e '.status=="working" and .port==3478 and .working.id=="udp-ipfrag-16" and (.tested|length)==2' "${TMP}/udp.json" >/dev/null || fail 'Python UDP ordering/input contract failed'
grep -Fq "udp|udp-ipfrag-8||3478|${TMP}/payload.bin" "${LOG}" || fail 'UDP candidate job-local environment missing'

# Protocol candidate policy is unified in candidate.py rather than shell override files.
PYTHONPATH="${SCRIPT_DIR}" STRATEGY_LAB_CANDIDATE_PROTOCOL=tls12 "${PYTHON}" -c 'from strategy_lab_py.candidate import _protocol_spec; s=_protocol_spec(); assert (s.protocol,s.transport,s.port,s.l7)==("tls12","tcp",443,"tls")'
PYTHONPATH="${SCRIPT_DIR}" STRATEGY_LAB_CANDIDATE_PROTOCOL=http "${PYTHON}" -c 'from strategy_lab_py.candidate import _protocol_spec; s=_protocol_spec(); assert (s.protocol,s.transport,s.port,s.l7)==("http","tcp",80,"http")'
PYTHONPATH="${SCRIPT_DIR}" STRATEGY_LAB_CANDIDATE_PROTOCOL=quic "${PYTHON}" -c 'from strategy_lab_py.candidate import _protocol_spec; s=_protocol_spec(); assert (s.protocol,s.transport,s.port,s.l7)==("quic","udp",443,"quic")'
PYTHONPATH="${SCRIPT_DIR}" STRATEGY_LAB_CANDIDATE_PROTOCOL=udp STRATEGY_LAB_UDP_PORT=3478 STRATEGY_LAB_UDP_PAYLOAD_FILE="${TMP}/payload.bin" "${PYTHON}" -c 'from strategy_lab_py.candidate import _protocol_spec; s=_protocol_spec(); assert (s.protocol,s.transport,s.port)==("udp","udp",3478)'

echo 'PASS: Python 3.13 preserves adaptive/stability/extended contracts and runs QUIC independently of control-probe reachability'
