#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
REQUEST_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/request.py"
CANDIDATE_PY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/candidate.py"
ROOT=$(mktemp -d /tmp/strategy-lab-interception.XXXXXX)
trap 'rm -rf "${ROOT}"' EXIT HUP INT TERM

STRATEGY_LAB_JQ=$(command -v jq)
COUNTER_FILE="${ROOT}/counter"
MOCK_IPFW="${ROOT}/ipfw"
export COUNTER_FILE
cat > "${MOCK_IPFW}" <<'MOCK'
#!/bin/sh
if [ "$1" = -a ] && [ "$2" = list ]; then
    packets=$(cat "${COUNTER_FILE}")
    printf '%s %s %s divert 9989 tcp from me to 203.0.113.10 443 out\n' "$3" "${packets}" "$((packets * 64))"
    exit 0
fi
exit 1
MOCK
chmod +x "${MOCK_IPFW}"

STRATEGY_LAB_IPFW_BIN="${MOCK_IPFW}"
STRATEGY_LAB_RULE_BASE=19100
STRATEGY_LAB_RULE_MAX=19131
. "${MODULE_DIR}/target.sh"
. "${MODULE_DIR}/firewall.sh"
. "${MODULE_DIR}/interception.sh"
. "${MODULE_DIR}/candidate.sh"

WORK="${ROOT}/work"
mkdir -p "${WORK}"
printf '1\texample.com\t203.0.113.10\t19100\n' > "$(strategy_lab_candidate_bindings_file "${WORK}")"
printf '%s\n' 4 > "${COUNTER_FILE}"
STATE="${WORK}/probe.state"
strategy_lab_candidate_probe_begin "${WORK}" 1 "${STATE}"
printf '%s\n' 5 > "${COUNTER_FILE}"
RAW="${WORK}/probe.log"
printf '%s\n' 'exit=0 remote_ip=203.0.113.10 http=1.1 code=200 bytes=128' > "${RAW}"
RESULT="${WORK}/result.json"
strategy_lab_candidate_endpoint_result_write \
    example.com 0 tls13-ipv4 "${RAW}" 203.0.113.10 "${STATE}" "${RESULT}"
"${STRATEGY_LAB_JQ}" -e '
    .status=="PASS" and .selected_ip=="203.0.113.10" and
    .remote_ip=="203.0.113.10" and .endpoint_match==true and
    .firewall.rule==19100 and .firewall.packets_before==4 and
    .firewall.packets_after==5 and .firewall.intercepted==true
' "${RESULT}" >/dev/null

printf '%s\n' 5 > "${COUNTER_FILE}"
strategy_lab_candidate_probe_begin "${WORK}" 1 "${STATE}"
printf '%s\n' 6 > "${COUNTER_FILE}"
strategy_lab_candidate_endpoint_result_write \
    example.com 0 tls13-ipv4 "${RAW}" 198.51.100.8 "${STATE}" "${RESULT}"
"${STRATEGY_LAB_JQ}" -e \
    '.status=="FAIL" and .endpoint_match==false and .firewall.intercepted==true' \
    "${RESULT}" >/dev/null

printf '%s\n' 6 > "${COUNTER_FILE}"
strategy_lab_candidate_probe_begin "${WORK}" 1 "${STATE}"
strategy_lab_candidate_endpoint_result_write \
    example.com 0 tls13-ipv4 "${RAW}" 203.0.113.10 "${STATE}" "${RESULT}"
"${STRATEGY_LAB_JQ}" -e \
    '.status=="FAIL" and .endpoint_match==true and .firewall.intercepted==false' \
    "${RESULT}" >/dev/null

strategy_lab_dns_request()
{
    case "$1" in
        example.com|alias.example.com) address=203.0.113.10 ;;
        *) return 1 ;;
    esac
    printf '%s\n' ';; QUESTION SECTION:' > "$3"
    printf '%s. 60 IN A 198.51.100.99\n' "$1" >> "$3"
    printf '%s\n' ';; ANSWER SECTION:' >> "$3"
    printf '%s. 60 IN A %s\n' "$1" "${address}" >> "$3"
    printf '%s\n' ';; AUTHORITY SECTION:' >> "$3"
    printf '%s. 60 IN A 198.51.100.98\n' "$1" >> "$3"
}
strategy_lab_dns_first_answer()
{
    awk -v wanted="$1" '
        /^;; ANSWER SECTION:/ { answer=1; next }
        /^;; [A-Z]+ SECTION:/ { answer=0 }
        answer && $(NF-1)==wanted { print $NF; exit }
    ' "$2"
}
ENDPOINTS="${ROOT}/endpoints"
ADDRESSES="${ROOT}/addresses"
printf '%s\n' example.com alias.example.com 198.51.100.5 > "${ENDPOINTS}"
strategy_lab_candidate_resolve_addresses "${ENDPOINTS}" "${ADDRESSES}" "${WORK}"
[ "$(wc -l < "${ADDRESSES}" | tr -d '[:space:]')" -eq 2 ]
BINDINGS=$(strategy_lab_candidate_bindings_file "${WORK}")
awk -F '\t' '
    NR==1 { ok=($2=="example.com" && $3=="203.0.113.10" && $4==19100) }
    NR==2 { ok=ok && ($2=="alias.example.com" && $3=="203.0.113.10" && $4==19100) }
    NR==3 { ok=ok && ($2=="198.51.100.5" && $3=="198.51.100.5" && $4==19101) }
    END { exit !(NR==3 && ok) }
' "${BINDINGS}"

# Bound TLS/HTTP finite requests are Python-owned in Migration Patch 4. The
# invariant remains: a bound probe pins the exact endpoint and cannot follow a
# redirect away from that IP.
grep -Fq 'command.extend(["--max-redirs", "0", "--resolve", f"{host}:{port}:{bound_ip}"])' "${REQUEST_PY}"
grep -Fq 'if bound_ip is None:' "${REQUEST_PY}"
grep -Fq 'command.extend(["--location", "--max-redirs", "2"])' "${REQUEST_PY}"
grep -Fq 'strategy_lab_request_python tls13-bound' "${MODULE_DIR}/request.sh"
grep -Fq 'strategy_lab_request_python tls12-bound' "${MODULE_DIR}/extended_request.sh"
grep -Fq 'strategy_lab_request_python http-bound' "${MODULE_DIR}/extended_request.sh"

# Migration Patch 5 moves standard TLS13 candidate interception policy to
# Python. It still requires both endpoint identity and IPFW counter growth.
grep -Fq 'before_packets, before_bytes = _counter(rule)' "${CANDIDATE_PY}"
grep -Fq 'after_packets, after_bytes = _counter(rule)' "${CANDIDATE_PY}"
grep -Fq 'endpoint_match = remote_ip == selected' "${CANDIDATE_PY}"
grep -Fq 'intercepted = after_packets > before_packets' "${CANDIDATE_PY}"
grep -Fq 'passed = exit_code == 0 and endpoint_match and intercepted' "${CANDIDATE_PY}"

grep -Fq -- '-connect "${_slquicreq_ip}:443"' "${MODULE_DIR}/quic_request.sh"
for file in candidate.sh extended_candidate.sh quic_candidate.sh udp_candidate.sh
do
    grep -Fq 'strategy_lab_candidate_probe_begin' "${MODULE_DIR}/${file}"
    grep -Fq 'strategy_lab_candidate_endpoint_result_write' "${MODULE_DIR}/${file}"
done
# QUIC/UDP/extended protocol candidate orchestration is intentionally still
# shell-owned until Migration Patch 6.
for runner in strategy_lab_quic_candidate_runner.sh strategy_lab_udp_candidate_runner.sh
do
    grep -Eq '(^|[[:space:]])interception([[:space:]]|$)' \
        "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/${runner}"
done
grep -Fq 'candidate run' "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_candidate_runner.sh"
if grep -Fq '_slcand_run_pids' "${MODULE_DIR}/candidate.sh"; then
    echo 'candidate probes still share counters in parallel' >&2
    exit 1
fi

echo 'PASS: candidate success requires one bound endpoint and verified IPFW counter growth across Python standard and shell extended candidate owners'
