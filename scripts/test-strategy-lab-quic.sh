#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd); SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"; MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP=$(mktemp -d /tmp/strategy-lab-quic-test.XXXXXX); trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test"
cat > "${TMP}/bin/timeout" <<'MOCK'
#!/bin/sh
shift
exec "$@"
MOCK
cat > "${TMP}/bin/candidate" <<'MOCK'
#!/bin/sh
result=$3; id=$4; family=$5; strategy=$6
printf '%s\n' "${id}" >> "${MOCK_QUIC_ORDER}"
case "${id}" in quic-fake-1) pass=false; status=FAIL ;; *) pass=true; status=PASS ;; esac
jq -n --arg id "${id}" --arg family "${family}" --rawfile strategy "${strategy}" --arg status "${status}" --argjson pass "${pass}" '{id:$id,family:$family,strategy:$strategy,endpoints:[{endpoint:"example.org",status:$status}],all_pass:$pass}' > "${result}"
MOCK
chmod +x "${TMP}/bin/"*
printf 'example.org\n' > "${TMP}/endpoints.txt"
export SCRIPT_DIR MODULE_DIR STRATEGY_LAB_JQ=$(command -v jq) STRATEGY_LAB_RUN_DIR="${TMP}/run" STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout" STRATEGY_LAB_QUIC_CANDIDATE_RUNNER="${TMP}/bin/candidate" MOCK_QUIC_ORDER="${TMP}/order"
. "${MODULE_DIR}/common.sh"; . "${MODULE_DIR}/quic.sh"
printf '%s\n' '{"quic_ipv4":"closed"}' > "${TMP}/closed.json"
strategy_lab_quic_run job.test "${TMP}/endpoints.txt" "${TMP}/closed.json" "${TMP}/closed-result.json"
jq -e '.status=="skipped" and .reason=="quic_ipv4_closed" and (.tested|length)==0' "${TMP}/closed-result.json" >/dev/null
[ ! -e "${MOCK_QUIC_ORDER}" ]
printf '%s\n' '{"quic_ipv4":"available"}' > "${TMP}/available.json"
strategy_lab_quic_run job.test "${TMP}/endpoints.txt" "${TMP}/available.json" "${TMP}/available-result.json"
jq -e '.status=="working" and .working.id=="quic-fake-2" and (.tested|length)==2' "${TMP}/available-result.json" >/dev/null
[ "$(paste -sd, "${MOCK_QUIC_ORDER}")" = 'quic-fake-1,quic-fake-2' ]
grep -Fxq -- '--payload=quic_initial' "${MODULE_DIR}/catalog/quic/quic-fake-1.args"
grep -Fxq -- '--lua-desync=send:ipfrag:ipfrag_pos_udp=8' "${MODULE_DIR}/catalog/quic/quic-ipfrag-8.args"
grep -Fxq -- '--lua-desync=drop' "${MODULE_DIR}/catalog/quic/quic-ipfrag-8.args"
echo 'PASS: Strategy Lab QUIC branch obeys capability gating and Zapret2-only candidate order'
