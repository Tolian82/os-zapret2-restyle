#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
TARGET_SH="${ZAPRET_DIR}/strategy_lab/target.sh"
PYTHON_LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
JQ=$(command -v jq || true)

fail(){ echo "FAIL: $*" >&2; exit 1; }
[ -x "${JQ}" ] || fail 'jq is unavailable'
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python 3.13 is unavailable: ${PYTHON}"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-ip-targets.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
STRATEGY_LAB_RUN_DIR="${TMP}/run"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_RUN_DIR}/jobs"
mkdir -p "${STRATEGY_LAB_JOBS_DIR}/job.ip"
export STRATEGY_LAB_RUN_DIR STRATEGY_LAB_JOBS_DIR

strategy_lab_job_dir(){ printf '%s/%s\n' "${STRATEGY_LAB_JOBS_DIR}" "$1"; }
. "${TARGET_SH}"

[ "$(strategy_lab_normalize_target 203.0.113.10)" = 203.0.113.10 ] || fail 'canonical IPv4 target was rejected'
[ "$(strategy_lab_target_type 203.0.113.10)" = ip ] || fail 'IPv4 target type was not classified as ip'
[ "$(strategy_lab_normalize_target Example.COM.)" = example.com ] || fail 'domain normalization regressed'
[ "$(strategy_lab_target_type example.com)" = domain ] || fail 'domain target type regressed'
if strategy_lab_normalize_target 203.0.113.010 >/dev/null 2>&1; then fail 'non-canonical IPv4 target was accepted'; fi
if strategy_lab_normalize_service_host 203.0.113.10 >/dev/null 2>&1; then fail 'IP literal was accepted as Host / SNI'; fi

JOB_ID=job.ip
export JOB_ID
printf '%s\n' service.example > "${STRATEGY_LAB_JOBS_DIR}/${JOB_ID}/service-host"
strategy_lab_write_endpoints 203.0.113.10 ip "${TMP}/endpoints.txt"
[ "$(cat "${TMP}/endpoints.txt")" = service.example ] || fail 'IP target did not use optional Host / SNI endpoint identity'
: > "${STRATEGY_LAB_JOBS_DIR}/${JOB_ID}/service-host"
strategy_lab_write_endpoints 203.0.113.10 ip "${TMP}/endpoints-bare.txt"
[ "$(cat "${TMP}/endpoints-bare.txt")" = 203.0.113.10 ] || fail 'bare IP target endpoint changed'
unset JOB_ID

MOCK_BIN="${TMP}/bin"
WORK="${STRATEGY_LAB_JOBS_DIR}/job.ip"
mkdir -p "${MOCK_BIN}"
cat > "${MOCK_BIN}/curl" <<'EOF'
#!/bin/sh
printf '%s\n' 'exit=0 remote_ip=203.0.113.10 http=1.1 code=200 bytes=64'
EOF
cat > "${MOCK_BIN}/nc" <<'EOF'
#!/bin/sh
echo 'nc must not be used as proof of a TLS candidate' >&2
exit 91
EOF
chmod +x "${MOCK_BIN}/curl" "${MOCK_BIN}/nc"
printf '%s\n' '{"ipv4":"available","ipv6":"unavailable","quic_ipv4":"closed","quic_ipv6":"skipped"}' > "${WORK}/network.json"
printf '%s\n' service.example > "${WORK}/endpoints.txt"

STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_JOBS_DIR}" \
STRATEGY_LAB_CURL_BIN="${MOCK_BIN}/curl" \
STRATEGY_LAB_NC_BIN="${MOCK_BIN}/nc" \
STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
"${PYTHON_LAUNCHER}" probe baseline 203.0.113.10 ip "${WORK}/endpoints.txt" "${WORK}/network.json" "${WORK}" "${WORK}/baseline.json"

"${JQ}" -e '
  .target=="203.0.113.10" and .target_type=="ip" and .all_accessible==true and
  .endpoints==[{endpoint:"service.example",status:"PASS",exit_code:0,transport:"tls13-ipv4",detail:""}]
' "${WORK}/baseline.json" >/dev/null || {
    cat "${WORK}/baseline.json" >&2
    fail 'IP baseline did not use truthful TLS 1.3 semantics'
}
"${JQ}" -e '
  .target=="203.0.113.10" and .target_type=="ip" and
  .bindings[0].endpoint=="service.example" and .bindings[0].selected_ip=="203.0.113.10"
' "${WORK}/search-epoch.json" >/dev/null || fail 'IP search epoch did not keep destination IP separate from Host / SNI'
"${JQ}" -e '
  .endpoints[0].destination_ip=="203.0.113.10" and
  (.endpoints[0].tls_ipv4.command|index("--resolve"))!=null and
  (.endpoints[0].tls_ipv4.command|index("service.example:443:203.0.113.10"))!=null and
  (.endpoints[0].tls_ipv4.command[0]|endswith("/curl"))
' "${WORK}/baseline-evidence.json" >/dev/null || fail 'IP baseline did not connect to the fixed IP with separate service identity'

PYTHONPATH="${ZAPRET_DIR}" STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_JOBS_DIR}" "${PYTHON}" - "${JOB_ID:-job.ip}" <<'PY'
import os
import sys
from strategy_lab_py import ip_target_support, result, search_graph

job = sys.argv[1]
sys.argv = ["strategy_lab_python.py", "family", "screen", job, "endpoints", "result"]
ip_target_support.install()
graph = search_graph.native_tls13_graph()
assert graph.nodes
assert all(node.spec.target_binding is False for node in graph.nodes)
assert result.selector_for("203.0.113.10", "ip", "tls13") == "--ipset-ip=203.0.113.10"
PY

CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
LAUNCH="${ZAPRET_DIR}/strategy_lab/launch.sh"
ENTRY="${ZAPRET_DIR}/strategy_lab_python.py"
SUPPORT="${ZAPRET_DIR}/strategy_lab_py/ip_target_support.py"

grep -Fq "FILTER_VALIDATE_IP, FILTER_FLAG_IPV4" "${CONTROLLER}" || fail 'API does not accept explicit IPv4 targets'
grep -Fq "getPost('service_host'" "${CONTROLLER}" || fail 'API Host / SNI handoff is missing'
grep -Fq 'parameters:%s %s %s %s %s %s %s' "${ACTIONS}" || fail 'configd Strategy Lab start contract does not carry Host / SNI'
grep -Fq 'strategyLabServiceHostInput' "${VIEW}" || fail 'Laboratory Host / SNI input is missing'
grep -Fq 'service_host:serviceHost' "${VIEW}" || fail 'Laboratory does not send Host / SNI to the API'
grep -Fq 'service-host' "${LAUNCH}" || fail 'launcher does not persist immutable service identity'
grep -Fq 'ip_target_support.install()' "${ENTRY}" || fail 'packaged Python entry point does not install IP target support'
grep -Fq 'request.curl_request(' "${SUPPORT}" || fail 'IP target support does not use protocol-aware curl probing'
! grep -Fq 'tcp_request(selected, spec.port)' "${SUPPORT}" || fail 'IP TLS candidate still falls back to plain TCP proof'
grep -Eq '^PLUGIN_REVISION=[[:space:]]+22$' "${ROOT_DIR}/Makefile" || fail 'package revision is not v0.4.1_22'

sh -n "${TARGET_SH}" "${LAUNCH}" "$0"
"${PYTHON}" -m py_compile "${ENTRY}" "${SUPPORT}"
echo 'PASS: Laboratory accepts canonical IPv4 targets, preserves optional Host/SNI identity, and validates TLS against the fixed destination IP'
