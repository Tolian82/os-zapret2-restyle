#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"; MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
REQUEST_PY="${SCRIPT_DIR}/strategy_lab_py/request.py"
TMP=$(mktemp -d /tmp/strategy-lab-extended-test.XXXXXX); trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test"
cat > "${TMP}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK
cat > "${TMP}/bin/candidate" <<'MOCK'
#!/bin/sh
result=$3; id=$4; family=$5; strategy=$6
printf '%s:%s:%s:%s\n' "${STRATEGY_LAB_CANDIDATE_PROTOCOL}" "${STRATEGY_LAB_CANDIDATE_PORT}" "${STRATEGY_LAB_CANDIDATE_L7}" "${id}" >> "${MOCK_EXTENDED_ORDER}"
case "${id}" in tls12-multisplit|http-multisplit) pass=false; status=FAIL ;; *) pass=true; status=PASS ;; esac
jq -n --arg id "${id}" --arg family "${family}" --rawfile strategy "${strategy}" --arg status "${status}" --argjson pass "${pass}" '{id:$id,family:$family,strategy:$strategy,endpoints:[{endpoint:"example.org",status:$status}],all_pass:$pass}' > "${result}"
MOCK
chmod +x "${TMP}/bin/"*
printf 'example.org\n' > "${TMP}/endpoints.txt"
export SCRIPT_DIR MODULE_DIR STRATEGY_LAB_JQ=$(command -v jq)
export STRATEGY_LAB_RUN_DIR="${TMP}/run" STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout" STRATEGY_LAB_EXTENDED_CANDIDATE_RUNNER="${TMP}/bin/candidate"
export STRATEGY_LAB_ENV_BIN=$(command -v env) MOCK_EXTENDED_ORDER="${TMP}/order"
. "${MODULE_DIR}/common.sh"; . "${MODULE_DIR}/extended.sh"
strategy_lab_extended_run job.test "${TMP}/endpoints.txt" "${TMP}/result.json"
jq -e '.protocols.tls12.working.id=="tls12-fake" and .protocols.http.working.id=="http-multidisorder" and (.protocols.tls12.tested|length)==2 and (.protocols.http.tested|length)==2' "${TMP}/result.json" >/dev/null
[ "$(paste -sd, "${TMP}/order")" = 'tls12:443:tls:tls12-multisplit,tls12:443:tls:tls12-fake,http:80:http:http-multisplit,http:80:http:http-multidisorder' ]
grep -Fq 'strategy_lab_request_python tls12' "${MODULE_DIR}/extended_request.sh"
grep -Fq 'strategy_lab_request_python http' "${MODULE_DIR}/extended_request.sh"
grep -Fq '"--tls-max", tls_version' "${REQUEST_PY}"
grep -Fq 'command = [binary("curl"), f"--{family}", "--proto", f"={scheme}"]' "${REQUEST_PY}"
echo 'PASS: Strategy Lab extended TLS 1.2 and HTTP branches preserve protocol-specific contracts through the Python finite-request owner'
