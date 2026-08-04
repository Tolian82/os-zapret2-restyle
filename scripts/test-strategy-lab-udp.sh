#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd); SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"; MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP=$(mktemp -d /tmp/strategy-lab-udp-test.XXXXXX); trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test"
cat > "${TMP}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK
cat > "${TMP}/bin/candidate" <<'MOCK'
#!/bin/sh
result=$3; id=$4; family=$5; strategy=$6
[ "${STRATEGY_LAB_UDP_PORT}" = 3478 ] || exit 92
[ -s "${STRATEGY_LAB_UDP_PAYLOAD_FILE}" ] || exit 93
printf '%s\n' "${id}" >> "${MOCK_UDP_ORDER}"
case "${id}" in udp-ipfrag-8) pass=false; status=FAIL ;; *) pass=true; status=PASS ;; esac
jq -n --arg id "${id}" --arg family "${family}" --rawfile strategy "${strategy}" --arg status "${status}" --argjson pass "${pass}" '{id:$id,family:$family,strategy:$strategy,endpoints:[{endpoint:"203.0.113.10",status:$status}],all_pass:$pass}' > "${result}"
MOCK
chmod +x "${TMP}/bin/"*
printf '203.0.113.10\n' > "${TMP}/endpoints.txt"; printf 'request' > "${TMP}/payload.bin"
export SCRIPT_DIR MODULE_DIR STRATEGY_LAB_JQ=$(command -v jq) STRATEGY_LAB_RUN_DIR="${TMP}/run" STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout" STRATEGY_LAB_UDP_CANDIDATE_RUNNER="${TMP}/bin/candidate" STRATEGY_LAB_ENV_BIN=$(command -v env) MOCK_UDP_ORDER="${TMP}/order"
. "${MODULE_DIR}/common.sh"; . "${MODULE_DIR}/udp.sh"
unset STRATEGY_LAB_UDP_PORT STRATEGY_LAB_UDP_PAYLOAD_FILE
strategy_lab_udp_run job.test "${TMP}/endpoints.txt" "${TMP}/skipped.json"
jq -e '.status=="skipped" and .reason=="udp_port_not_configured" and (.tested|length)==0' "${TMP}/skipped.json" >/dev/null
STRATEGY_LAB_UDP_PORT=3478; STRATEGY_LAB_UDP_PAYLOAD_FILE="${TMP}/payload.bin"; export STRATEGY_LAB_UDP_PORT STRATEGY_LAB_UDP_PAYLOAD_FILE
strategy_lab_udp_run job.test "${TMP}/endpoints.txt" "${TMP}/result.json"
jq -e '.status=="working" and .port==3478 and .working.id=="udp-ipfrag-16" and (.tested|length)==2' "${TMP}/result.json" >/dev/null
[ "$(paste -sd, "${MOCK_UDP_ORDER}")" = 'udp-ipfrag-8,udp-ipfrag-16' ]
grep -Fxq -- '--lua-desync=send:ipfrag:ipfrag_pos_udp=8' "${MODULE_DIR}/catalog/udp/udp-ipfrag-8.args"
echo 'PASS: Strategy Lab generic UDP requires explicit request-response configuration and runs sequentially'
