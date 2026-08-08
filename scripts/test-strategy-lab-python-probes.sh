#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PROBE_PY="${ZAPRET_DIR}/strategy_lab_py/probe.py"
COMPAT_PY="${ZAPRET_DIR}/strategy_lab_py/compat.py"
RUNNER="${ZAPRET_DIR}/strategy_lab_probe_runner.sh"
LAUNCHER="${ZAPRET_DIR}/strategy_lab_python_launcher.sh"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

"${PYTHON}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)' ||
    fail 'Python 3.13 is unavailable'
"${PYTHON}" -m py_compile "${PROBE_PY}" "${COMPAT_PY}" ||
    fail 'Python probe modules do not compile'

TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-python-probes.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM
MOCK_BIN="${TMP_ROOT}/bin"
WORK="${TMP_ROOT}/work"
mkdir -p "${MOCK_BIN}" "${WORK}"

cat > "${MOCK_BIN}/io" <<'MOCK'
#!/bin/sh
printf '%s\n' stdout-evidence
printf '%s\n' stderr-evidence >&2
exit 7
MOCK
cat > "${MOCK_BIN}/sleepy" <<'MOCK'
#!/bin/sh
sleep 2
printf '%s\n' too-late
MOCK
cat > "${MOCK_BIN}/curl" <<'MOCK'
#!/bin/sh
url=
for arg in "$@"
do
    case "${arg}" in https://*) url="${arg}" ;; esac
done
host=$(printf '%s' "${url}" | sed -e 's#^https://##' -e 's#/$##')
printf 'curl-stderr-%s\n' "${host}" >&2
case "${MOCK_CURL_MODE:-baseline-fail}:${host}" in
    network-pass:yandex.ru)
        printf '%s\n' 'exit=0 remote_ip=203.0.113.10 http=1.1 code=200 bytes=10'
        exit 0
        ;;
    network-pass:one.one.one.one)
        printf '%s\n' 'exit=0 remote_ip=2001:db8::10 http=1.1 code=200 bytes=10'
        exit 0
        ;;
    *)
        printf '%s\n' 'exit=28 remote_ip= http=0 code=000 bytes=0'
        exit 28
        ;;
esac
MOCK
cat > "${MOCK_BIN}/netstat" <<'MOCK'
#!/bin/sh
if [ "${MOCK_IPV6_ROUTE:-0}" = 1 ]; then
    printf '%s\n' 'default 2001:db8::1 UGS vtnet0'
fi
MOCK
cat > "${MOCK_BIN}/openssl" <<'MOCK'
#!/bin/sh
printf '%s\n' quic-diagnostic >&2
exit "${MOCK_QUIC_STATUS:-7}"
MOCK
cat > "${MOCK_BIN}/nc" <<'MOCK'
#!/bin/sh
printf '%s\n' tcp-diagnostic >&2
exit 1
MOCK
cat > "${MOCK_BIN}/drill" <<'MOCK'
#!/bin/sh
host="$1"
type="$2"
case "${MOCK_DNS_MODE:-valid}" in
    timeout)
        sleep 3
        exit 0
        ;;
    command)
        printf '%s\n' 'drill-command-error' >&2
        exit 9
        ;;
    parser)
        printf '%s\n' ';; QUESTION SECTION:'
        printf '%s. 60 IN %s %s\n' "${host}" "${type}" "${MOCK_DNS_VALUE:-203.0.113.99}"
        printf '%s\n' ';; AUTHORITY SECTION:'
        printf '%s. 60 IN %s %s\n' "${host}" "${type}" "${MOCK_DNS_VALUE:-203.0.113.99}"
        exit 0
        ;;
    valid)
        printf '%s\n' ';; QUESTION SECTION:'
        printf '%s. 60 IN %s %s\n' "${host}" "${type}" "${MOCK_DNS_VALUE:-203.0.113.99}"
        printf '%s\n' ';; ANSWER SECTION:'
        case "${type}" in
            A) printf '%s. 60 IN A 203.0.113.10\n' "${host}" ;;
            AAAA) printf '%s. 60 IN AAAA 2001:db8::10\n' "${host}" ;;
        esac
        printf '%s\n' ';; AUTHORITY SECTION:'
        printf '%s. 60 IN %s %s\n' "${host}" "${type}" "${MOCK_DNS_VALUE:-203.0.113.99}"
        exit 0
        ;;
esac
MOCK
chmod +x "${MOCK_BIN}"/*

PYTHONPATH="${ZAPRET_DIR}" "${PYTHON}" - "${MOCK_BIN}/io" "${MOCK_BIN}/sleepy" <<'PY'
import sys
from strategy_lab_py import probe

poison = ''';; QUESTION SECTION:\npoison.example. 60 IN A 203.0.113.99\n;; AUTHORITY SECTION:\npoison.example. 60 IN A 203.0.113.98\n'''
assert probe.parse_drill_answers(poison, 'A') == []
valid = poison + ''';; ANSWER SECTION:\nvalid.example. 60 IN A 203.0.113.10\nvalid.example. 60 IN AAAA 2001:db8::10\n;; AUTHORITY SECTION:\nvalid.example. 60 IN A 203.0.113.77\n'''
assert probe.parse_drill_answers(valid, 'A') == ['203.0.113.10']
assert probe.parse_drill_answers(valid, 'AAAA') == ['2001:db8::10']
result = probe.run_command([sys.argv[1]], timeout=1)
assert result.returncode == 7
assert result.stdout == 'stdout-evidence\n'
assert result.stderr == 'stderr-evidence\n'
assert result.timed_out is False
assert result.termination == 'completed'
timeout = probe.run_command([sys.argv[2]], timeout=0.1)
assert timeout.returncode is None
assert timeout.timed_out is True
assert timeout.termination == 'timeout'
PY

run_probe()
{
    STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
    STRATEGY_LAB_CURL_BIN="${MOCK_BIN}/curl" \
    STRATEGY_LAB_DRILL_BIN="${MOCK_BIN}/drill" \
    STRATEGY_LAB_NETSTAT_BIN="${MOCK_BIN}/netstat" \
    STRATEGY_LAB_OPENSSL_BIN="${MOCK_BIN}/openssl" \
    STRATEGY_LAB_NC_BIN="${MOCK_BIN}/nc" \
    MOCK_CURL_MODE="${MOCK_CURL_MODE:-baseline-fail}" \
    MOCK_IPV6_ROUTE="${MOCK_IPV6_ROUTE:-0}" \
    MOCK_QUIC_STATUS="${MOCK_QUIC_STATUS:-7}" \
    MOCK_DNS_MODE="${MOCK_DNS_MODE:-valid}" \
    SCRIPT_DIR="${ZAPRET_DIR}" \
    "${RUNNER}" "$@"
}

NETWORK_FILE="${WORK}/network.json"
MOCK_CURL_MODE=network-pass
export MOCK_CURL_MODE
run_probe network "${NETWORK_FILE}" "${WORK}"
jq -e '. == {ipv4:"available",ipv6:"unavailable",quic_ipv4:"closed",quic_ipv6:"skipped"}' "${NETWORK_FILE}" >/dev/null ||
    fail 'public network JSON changed during Python cutover'
jq -e '
    .ipv4.returncode==0 and
    .ipv4.stdout|contains("exit=0")
' "${WORK}/network-evidence.json" >/dev/null || fail 'IPv4 structured evidence is missing'
jq -e '.ipv4.stderr|contains("curl-stderr-yandex.ru")' "${WORK}/network-evidence.json" >/dev/null ||
    fail 'IPv4 stderr was flattened into stdout'
jq -e '.quic_ipv4.returncode==7 and .quic_ipv4.timed_out==false' "${WORK}/network-evidence.json" >/dev/null ||
    fail 'QUIC command status was flattened into timeout'

printf '%s\n' probe.example > "${WORK}/endpoints.txt"
printf '%s\n' '{"ipv4":"available","ipv6":"unavailable","quic_ipv4":"closed","quic_ipv6":"skipped"}' > "${WORK}/baseline-network.json"

baseline_case()
{
    mode="$1"
    expected="$2"
    result_file="${WORK}/baseline-${mode}.json"
    case "${mode}" in valid) MOCK_DNS_MODE=valid ;; parser) MOCK_DNS_MODE=parser ;; command) MOCK_DNS_MODE=command ;; timeout) MOCK_DNS_MODE=timeout ;; esac
    MOCK_CURL_MODE=baseline-fail
    export MOCK_DNS_MODE MOCK_CURL_MODE
    set +e
    run_probe baseline probe.example domain "${WORK}/endpoints.txt" "${WORK}/baseline-network.json" "${WORK}" "${result_file}"
    status=$?
    set -e
    [ "${status}" -eq "${expected}" ] || fail "baseline ${mode} returned ${status}, expected ${expected}"
    printf '%s\n' "${result_file}"
}

valid_file=$(baseline_case valid 0)
jq -e '.target=="probe.example" and .target_type=="domain" and .dns_a=="PASS" and .dns_aaaa=="SKIPPED"' "${valid_file}" >/dev/null ||
    fail 'Python baseline changed target/type or public DNS contract'
jq -e '.endpoints[0].dns_a.classification=="pass" and .endpoints[0].dns_a.execution.returncode==0' "${WORK}/baseline-evidence.json" >/dev/null ||
    fail 'valid DNS execution evidence is missing'

parser_file=$(baseline_case parser 2)
jq -e '.target_type=="domain" and .dns_a=="FAIL" and .endpoints[0].transport=="dns-a"' "${parser_file}" >/dev/null ||
    fail 'answer-section parser rejection changed public baseline contract'
jq -e '.endpoints[0].dns_a.classification=="parser_rejected" and .endpoints[0].dns_a.execution.returncode==0 and .endpoints[0].dns_a.execution.timed_out==false' "${WORK}/baseline-evidence.json" >/dev/null ||
    fail 'DNS parser rejection is not distinct from command failure'

command_file=$(baseline_case command 2)
jq -e '.dns_a=="FAIL"' "${command_file}" >/dev/null || fail 'DNS command failure did not fail public DNS A state'
jq -e '.endpoints[0].dns_a.classification=="command_error" and .endpoints[0].dns_a.execution.returncode==9 and (.endpoints[0].dns_a.execution.stderr|contains("drill-command-error"))' "${WORK}/baseline-evidence.json" >/dev/null ||
    fail 'DNS command failure lost returncode/stderr evidence'

timeout_file=$(baseline_case timeout 2)
jq -e '.dns_a=="FAIL"' "${timeout_file}" >/dev/null || fail 'DNS timeout did not fail public DNS A state'
jq -e '.endpoints[0].dns_a.classification=="timeout" and .endpoints[0].dns_a.execution.returncode==null and .endpoints[0].dns_a.execution.timed_out==true and .endpoints[0].dns_a.execution.termination=="timeout"' "${WORK}/baseline-evidence.json" >/dev/null ||
    fail 'DNS timeout was flattened into command or parser failure'

grep -Fq 'exec "${PYTHON_LAUNCHER}" probe "$@"' "${RUNNER}" ||
    fail 'production probe runner does not delegate to Python'
if grep -Eq 'strategy_lab_run_network_precheck|strategy_lab_run_clean_baseline|for module in .*request.*probe' "${RUNNER}"; then
    fail 'production probe runner still owns shell probe logic'
fi
grep -Fq 'from . import probe as probe_execution' "${COMPAT_PY}" ||
    fail 'Python compatibility entry point does not expose probe execution'

sh -n "${RUNNER}"
sh -n "${LAUNCHER}"

echo 'PASS: Python 3.13 owns finite Strategy Lab probe execution, answer-aware DNS parsing, and distinct subprocess diagnostics'
