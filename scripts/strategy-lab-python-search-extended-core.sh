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
    "${SCRIPT_DIR}/strategy_lab_py/candidate.py" \
    "${SCRIPT_DIR}/strategy_lab_py/search.py" \
    "${SCRIPT_DIR}/strategy_lab_py/extended.py" \
    "${SCRIPT_DIR}/strategy_lab_py/compat.py"

grep -Fq 'search expand' "${SCRIPT_DIR}/strategy_lab_expansion_runner.sh" || fail 'expansion runner is not Python-owned'
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
mkdir -p "${JOB_DIR}" "${TMP}/args" "${TMP}/bin"
printf '%s\n' example.test > "${TMP}/endpoints.txt"
printf '%s\n' 'payload' > "${TMP}/payload.bin"

FAKE="${TMP}/bin/candidate"
LOG="${TMP}/candidate.log"
cat > "${FAKE}" <<'MOCK'
#!/bin/sh
set -eu
result="$3"; id="$4"; family="$5"; strategy="$6"
protocol="${STRATEGY_LAB_CANDIDATE_PROTOCOL:-tls13}"
printf '%s|%s|%s|%s|%s\n' "${protocol}" "${id}" "${STRATEGY_LAB_ENDPOINT_PROBE_MODE:-}" "${STRATEGY_LAB_UDP_PORT:-}" "${STRATEGY_LAB_UDP_PAYLOAD_FILE:-}" >> "${MOCK_LOG}"
case "${id}" in
  e2|fbase|tls12-fake|http-multidisorder|quic-fake-2|udp-ipfrag-16) pass=true ;;
  *) pass=false ;;
esac
jq -n --arg id "${id}" --arg family "${family}" --rawfile strategy "${strategy}" --arg protocol "${protocol}" --argjson pass "${pass}" \
  '{id:$id,family:$family,strategy:$strategy,protocol:$protocol,endpoints:[{endpoint:"example.test",status:(if $pass then "PASS" else "FAIL" end)}],all_pass:$pass}' > "${result}"
MOCK
chmod 0755 "${FAKE}"

EXP_CATALOG="${TMP}/expansion.tsv"
printf '%s\n' \
  'f1	e1	1	e1.args' \
  'f1	e2	1	e2.args' \
  'f2	e3	1	e3.args' > "${EXP_CATALOG}"
printf '%s\n' '--lua-desync=fake:blob=fake_default_tls' > "${TMP}/args/e1.args"
printf '%s\n' '--lua-desync=multisplit:pos=1' > "${TMP}/args/e2.args"
printf '%s\n' '--lua-desync=syndata' > "${TMP}/args/e3.args"
cat > "${TMP}/family.json" <<'JSON'
{"total":1,"completed":1,"families":[{"id":"fbase","family":"f1","strategy":"--lua-desync=multisplit:pos=2\n","endpoints":[],"all_pass":true}],"accepted":["f1"],"rejected":[],"all_pass":true}
JSON

COMMON_ENV="STRATEGY_LAB_JOBS_DIR=${JOBS} STRATEGY_LAB_PYTHON_BIN=${PYTHON} MOCK_LOG=${LOG}"

env ${COMMON_ENV} \
  STRATEGY_LAB_EXPANSION_CATALOG="${EXP_CATALOG}" \
  STRATEGY_LAB_EXPANSION_ARGS_DIR="${TMP}/args" \
  STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${FAKE}" \
  STRATEGY_LAB_EXPANSION_TARGET=1 \
  sh "${LAUNCHER}" search expand "${JOB}" "${TMP}/endpoints.txt" "${TMP}/family.json" "${TMP}/expansion.json"
"${JQ}" -e '.total_available==2 and .completed==2 and .working==["e2"] and .failed==["e1"] and .stopped_reason=="enough_candidates"' "${TMP}/expansion.json" >/dev/null || fail 'Python expansion contract failed'

env ${COMMON_ENV} \
  STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER="${FAKE}" \
  STRATEGY_LAB_STABILITY_ATTEMPTS=3 \
  STRATEGY_LAB_STABILITY_TARGET=1 \
  sh "${LAUNCHER}" search stabilize "${JOB}" "${TMP}/endpoints.txt" "${TMP}/expansion.json" "${TMP}/family.json" "${TMP}/stability.json"
"${JQ}" -e '.completed==1 and (.stable|length)==1 and .candidates[0].stable==true and (.candidates[0].attempts|length)==3 and .stopped_reason=="enough_stable_candidates"' "${TMP}/stability.json" >/dev/null || fail 'Python stability contract failed'
[ "$(grep -c '|sequential|' "${LOG}")" -eq 3 ] || fail 'stability attempts were not forced to sequential fresh-connection mode'

# Existing extended TCP catalog: first candidate per protocol fails, second succeeds.
env ${COMMON_ENV} \
  MODULE_DIR="${SCRIPT_DIR}/strategy_lab" \
  STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER="${FAKE}" \
  sh "${LAUNCHER}" extended tcp "${JOB}" "${TMP}/endpoints.txt" "${TMP}/extended.json"
"${JQ}" -e '.protocols.tls12.working.id=="tls12-fake" and .protocols.http.working.id=="http-multidisorder" and (.protocols.tls12.tested|length)==2 and (.protocols.http.tested|length)==2' "${TMP}/extended.json" >/dev/null || fail 'Python extended TCP contract failed'

grep -Fq 'tls12|tls12-multisplit|' "${LOG}" || fail 'TLS 1.2 candidate protocol environment missing'
grep -Fq 'http|http-multisplit|' "${LOG}" || fail 'HTTP candidate protocol environment missing'

printf '%s\n' '{"quic_ipv4":"closed"}' > "${TMP}/network-closed.json"
env ${COMMON_ENV} MODULE_DIR="${SCRIPT_DIR}/strategy_lab" STRATEGY_LAB_QUIC_CANDIDATE_RUNNER="${FAKE}" \
  sh "${LAUNCHER}" extended quic "${JOB}" "${TMP}/endpoints.txt" "${TMP}/network-closed.json" "${TMP}/quic-closed.json"
"${JQ}" -e '.status=="skipped" and .reason=="quic_ipv4_closed" and (.tested|length)==0' "${TMP}/quic-closed.json" >/dev/null || fail 'Python QUIC capability skip contract failed'

printf '%s\n' '{"quic_ipv4":"available"}' > "${TMP}/network.json"
env ${COMMON_ENV} MODULE_DIR="${SCRIPT_DIR}/strategy_lab" STRATEGY_LAB_QUIC_CANDIDATE_RUNNER="${FAKE}" \
  sh "${LAUNCHER}" extended quic "${JOB}" "${TMP}/endpoints.txt" "${TMP}/network.json" "${TMP}/quic.json"
"${JQ}" -e '.status=="working" and .working.id=="quic-fake-2" and (.tested|length)==2' "${TMP}/quic.json" >/dev/null || fail 'Python QUIC ordering contract failed'
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

echo 'PASS: Python 3.13 owns Strategy Lab expansion, stability replay, and extended TLS/HTTP/QUIC/UDP orchestration with preserved result contracts'
