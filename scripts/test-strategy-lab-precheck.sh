#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LAUNCHER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_launcher.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab"
PROBE_RUNNER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_probe_runner.sh"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-precheck-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

MOCK_BIN="${TMP_ROOT}/bin"
RUN_DIR="${TMP_ROOT}/run"
LOG_DIR="${TMP_ROOT}/log"
STATE_FILE="${TMP_ROOT}/service.state"
CALLS_FILE="${TMP_ROOT}/service.calls"
mkdir -p "${MOCK_BIN}" "${RUN_DIR}" "${LOG_DIR}"

cat > "${MOCK_BIN}/lockf" <<'MOCK'
#!/bin/sh
exit 0
MOCK

cat > "${MOCK_BIN}/daemon" <<'MOCK'
#!/bin/sh
log_file=""
pid_file=""
while [ "$#" -gt 0 ]
do
    case "$1" in
        -f) shift ;;
        -o) log_file="$2"; shift 2 ;;
        -p) pid_file="$2"; shift 2 ;;
        *) break ;;
    esac
done
"$@" >> "${log_file}" 2>&1 &
pid=$!
printf '%s\n' "${pid}" > "${pid_file}"
exit 0
MOCK

cat > "${MOCK_BIN}/service" <<'MOCK'
#!/bin/sh
state=$(cat "${MOCK_STATE_FILE}")
case "${1:-}" in
    strategy-lab)
        STRATEGY_LAB_LIFECYCLE_OWNER=1
        STRATEGY_LAB_SERVICE_SCRIPT="$0"
        export STRATEGY_LAB_LIFECYCLE_OWNER STRATEGY_LAB_SERVICE_SCRIPT
        exec "${MOCK_WORKER}" "${2:-}"
        ;;
    strategy-lab-status)
        case "${state}" in
            RUNNING) exit 0 ;;
            STOPPED) exit 1 ;;
            *) exit 2 ;;
        esac
        ;;
    strategy-lab-stop)
        printf '%s\n' stop >> "${MOCK_CALLS_FILE}"
        printf '%s\n' STOPPED > "${MOCK_STATE_FILE}"
        ;;
    strategy-lab-start)
        printf '%s\n' start >> "${MOCK_CALLS_FILE}"
        printf '%s\n' RUNNING > "${MOCK_STATE_FILE}"
        ;;
    *) exit 64 ;;
esac
MOCK

cat > "${MOCK_BIN}/curl" <<'MOCK'
#!/bin/sh
url=""
family=ipv4
for argument in "$@"
do
    case "${argument}" in
        --ipv6) family=ipv6 ;;
        https://*) url="${argument}" ;;
    esac
done
host=$(printf '%s' "${url}" | sed -e 's#^https://##' -e 's#/$##')
[ "${MOCK_CURL_SLEEP:-0}" -eq 0 ] || sleep "${MOCK_CURL_SLEEP}"
case "${host}" in
    yandex.ru) status="${MOCK_IPV4_CONTROL_STATUS:-0}" ;;
    one.one.one.one) status="${MOCK_IPV6_CONTROL_STATUS:-0}" ;;
    "${MOCK_TLS_PASS_HOST:-__none__}") status=0 ;;
    *) status=28 ;;
esac
if [ "${status}" -eq 0 ]; then
    if [ "${family}" = ipv6 ]; then
        remote='2001:db8::1'
    else
        remote='203.0.113.10'
    fi
    printf 'exit=0 remote_ip=%s http=1.1 code=200 bytes=100\n' "${remote}"
    exit 0
fi
printf '%s\n' 'curl: (28) Connection timed out' >&2
printf 'exit=%s remote_ip= http=0 code=000 bytes=0\n' "${status}"
exit "${status}"
MOCK

cat > "${MOCK_BIN}/drill" <<'MOCK'
#!/bin/sh
host="$1"
type="$2"
printf '%s\n' ';; ANSWER SECTION:'
if [ "${type}" = A ] && [ "${host}" = "${MOCK_DNS_FAIL_HOST:-__none__}" ]; then
    exit 0
fi
case "${type}" in
    A) printf '%s. 60 IN A 203.0.113.10\n' "${host}" ;;
    AAAA) printf '%s. 60 IN AAAA 2001:db8::10\n' "${host}" ;;
esac
MOCK

cat > "${MOCK_BIN}/netstat" <<'MOCK'
#!/bin/sh
[ "${MOCK_IPV6_ROUTE:-0}" = 1 ] || exit 0
printf '%s\n' 'default 2001:db8::1 UGS vtnet0'
MOCK

cat > "${MOCK_BIN}/openssl" <<'MOCK'
#!/bin/sh
printf '%s\n' 'ignored QUIC diagnostic output' >&2
exit "${MOCK_QUIC_STATUS:-124}"
MOCK

cat > "${MOCK_BIN}/nc" <<'MOCK'
#!/bin/sh
exit "${MOCK_NC_STATUS:-1}"
MOCK

chmod +x "${MOCK_BIN}"/*

launcher()
{
    STRATEGY_LAB_JQ="$(command -v jq)" \
    STRATEGY_LAB_RUN_DIR="${RUN_DIR}" \
    STRATEGY_LAB_LOG_DIR="${LOG_DIR}" \
    STRATEGY_LAB_JOBS_DIR="${RUN_DIR}/jobs" \
    STRATEGY_LAB_ACTIVE_FILE="${RUN_DIR}/active.job" \
    STRATEGY_LAB_LOCK_FILE="${RUN_DIR}/launcher.lock" \
    SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret" \
    MODULE_DIR="${MODULE_DIR}" \
    WORKER_SCRIPT="${WORKER}" \
    PROBE_RUNNER="${PROBE_RUNNER}" \
    TRANSACTION_SCRIPT="${MOCK_BIN}/service" \
    DAEMON_BIN="${MOCK_BIN}/daemon" \
    LOCKF_BIN="${MOCK_BIN}/lockf" \
    STRATEGY_LAB_TIMEOUT_BIN="$(command -v timeout)" \
    STRATEGY_LAB_CURL_BIN="${MOCK_BIN}/curl" \
    STRATEGY_LAB_DRILL_BIN="${MOCK_BIN}/drill" \
    STRATEGY_LAB_NETSTAT_BIN="${MOCK_BIN}/netstat" \
    STRATEGY_LAB_OPENSSL_BIN="${MOCK_BIN}/openssl" \
    STRATEGY_LAB_NC_BIN="${MOCK_BIN}/nc" \
    MOCK_WORKER="${WORKER}" \
    MOCK_STATE_FILE="${STATE_FILE}" \
    MOCK_CALLS_FILE="${CALLS_FILE}" \
    MOCK_IPV4_CONTROL_STATUS="${MOCK_IPV4_CONTROL_STATUS:-0}" \
    MOCK_IPV6_CONTROL_STATUS="${MOCK_IPV6_CONTROL_STATUS:-0}" \
    MOCK_IPV6_ROUTE="${MOCK_IPV6_ROUTE:-0}" \
    MOCK_QUIC_STATUS="${MOCK_QUIC_STATUS:-124}" \
    MOCK_TLS_PASS_HOST="${MOCK_TLS_PASS_HOST:-}" \
    MOCK_DNS_FAIL_HOST="${MOCK_DNS_FAIL_HOST:-}" \
    MOCK_NC_STATUS="${MOCK_NC_STATUS:-1}" \
    MOCK_CURL_SLEEP="${MOCK_CURL_SLEEP:-0}" \
    STRATEGY_LAB_STAGE30_TIMEOUT="${STRATEGY_LAB_STAGE30_TIMEOUT:-6}" \
    STRATEGY_LAB_STAGE40_TIMEOUT="${STRATEGY_LAB_STAGE40_TIMEOUT:-5}" \
    WORKER_HOLD_SECONDS=0 \
    "${LAUNCHER}" "$@"
}

wait_for_completion()
{
    job_id="$1"
    attempts=0
    while [ "${attempts}" -lt 40 ]
    do
        state=$(launcher status "${job_id}" | jq -r '.state // ""')
        [ "${state}" != completed ] || return 0
        sleep 1
        attempts=$((attempts + 1))
    done
    fail "job ${job_id} did not complete"
}

run_job()
{
    target="$1"
    language="$2"
    printf '%s\n' RUNNING > "${STATE_FILE}"
    : > "${CALLS_FILE}"
    output=$(launcher start "${target}" standard "${language}")
    job=$(printf '%s\n' "${output}" | jq -r '.job_id')
    wait_for_completion "${job}"
    launcher result "${job}"
}

# IPv4 only, QUIC closed, two required Telegram endpoints, clean TLS failure.
unset MOCK_IPV6_ROUTE MOCK_QUIC_STATUS MOCK_TLS_PASS_HOST MOCK_DNS_FAIL_HOST MOCK_IPV4_CONTROL_STATUS MOCK_NC_STATUS
result=$(run_job 'Telegram.ORG.' en)
printf '%s\n' "${result}" | jq -e '.target=="telegram.org" and .target_type=="domain"' >/dev/null ||
    fail "domain target was not normalized and classified"
printf '%s\n' "${result}" | jq -e '.endpoints==["telegram.org","web.telegram.org"]' >/dev/null ||
    fail "Telegram endpoint contract is incorrect"
printf '%s\n' "${result}" | jq -e '.network=={ipv4:"available",ipv6:"unavailable",quic_ipv4:"closed",quic_ipv6:"skipped"}' >/dev/null ||
    fail "IPv4-only network classification is incorrect"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="30" and .message=="PASS — IPv4 is available; IPv6 is unavailable; QUIC/IPv4 is blocked; IPv6 and QUIC tests have been excluded.")' >/dev/null ||
    fail "IPv4-only English summary is incorrect"
printf '%s\n' "${result}" | jq -e '.baseline.dns_a=="PASS" and (.baseline.endpoints|length)==2 and ([.baseline.endpoints[].status]|all(.=="FAIL"))' >/dev/null ||
    fail "clean Telegram baseline is incorrect"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="40" and .message=="PASS — DNS: OK; direct TLS 1.3 connection failed.")' >/dev/null ||
    fail "clean TLS failure summary is incorrect"
[ "$(cat "${STATE_FILE}")" = RUNNING ] || fail "service was not restored after baseline"

# Full network capability and direct target access. OpenSSL output is ignored; status 0 wins.
MOCK_IPV6_ROUTE=1
MOCK_QUIC_STATUS=0
MOCK_TLS_PASS_HOST=accessible.example
export MOCK_IPV6_ROUTE MOCK_QUIC_STATUS MOCK_TLS_PASS_HOST
result=$(run_job accessible.example en)
printf '%s\n' "${result}" | jq -e '.outcome=="TARGET_ACCESSIBLE" and .baseline.all_accessible==true' >/dev/null ||
    fail "directly accessible target did not stop strategy search"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="30" and .message=="PASS — IPv4, IPv6, and QUIC/IPv4 are available.")' >/dev/null ||
    fail "full network summary is incorrect"
printf '%s\n' "${result}" | jq -e '.baseline.endpoints[0].ipv4.status=="PASS" and .baseline.endpoints[0].ipv6.status=="PASS"' >/dev/null ||
    fail "clean IPv4/IPv6 baseline details are incorrect"
printf '%s\n' "${result}" | jq -e '[.stages[] | select(.number=="50" or .number=="60" or .number=="70" or .number=="80" or .number=="85")] | all(.status=="SKIPPED" and .message=="SKIPPED — target accessible without bypass")' >/dev/null ||
    fail "strategy stages were not skipped for an accessible target"

# DNS failure is a valid negative stage result, not an internal ERROR.
unset MOCK_IPV6_ROUTE MOCK_QUIC_STATUS MOCK_TLS_PASS_HOST
MOCK_DNS_FAIL_HOST=dnsfail.example
export MOCK_DNS_FAIL_HOST
result=$(run_job dnsfail.example en)
printf '%s\n' "${result}" | jq -e '.outcome=="PARTIAL" and .baseline.dns_a=="FAIL"' >/dev/null ||
    fail "DNS failure outcome is incorrect"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="40" and .status=="FAIL")' >/dev/null ||
    fail "DNS failure did not fail stage 40"

# IPv4 control failure stops before baseline, but stage 90 still restores service state.
unset MOCK_DNS_FAIL_HOST
MOCK_IPV4_CONTROL_STATUS=28
export MOCK_IPV4_CONTROL_STATUS
result=$(run_job no-control.example en)
printf '%s\n' "${result}" | jq -e '.outcome=="PARTIAL" and .network.ipv4=="unavailable"' >/dev/null ||
    fail "IPv4 control failure classification is incorrect"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="30" and .status=="FAIL")' >/dev/null ||
    fail "IPv4 control failure did not fail stage 30"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="PASS")' >/dev/null ||
    fail "IPv4 control failure did not restore service state"

# IPv4 target uses an explicit TCP/443 baseline without pretending to have DNS or SNI.
unset MOCK_IPV4_CONTROL_STATUS
MOCK_NC_STATUS=1
export MOCK_NC_STATUS
result=$(run_job 203.0.113.9 ru)
printf '%s\n' "${result}" | jq -e '.target_type=="ip" and .baseline.dns_a=="SKIPPED" and .baseline.endpoints[0].transport=="tcp-443"' >/dev/null ||
    fail "IP target baseline contract is incorrect"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="40" and .message=="PASS — Прямое TCP/443-подключение к IP-цели не установлено.")' >/dev/null ||
    fail "Russian IP baseline summary is incorrect"


# Stage budget is enforced independently from individual operation limits.
unset MOCK_NC_STATUS
MOCK_CURL_SLEEP=2
STRATEGY_LAB_STAGE30_TIMEOUT=1
export MOCK_CURL_SLEEP STRATEGY_LAB_STAGE30_TIMEOUT
result=$(run_job timeout.example en)
printf '%s\n' "${result}" | jq -e '.outcome=="TIMEOUT"' >/dev/null ||
    fail "stage timeout did not produce TIMEOUT outcome"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="30" and .status=="TIMEOUT")' >/dev/null ||
    fail "stage 30 timeout was not recorded"
printf '%s\n' "${result}" | jq -e '.stages[] | select(.number=="90" and .status=="PASS")' >/dev/null ||
    fail "stage timeout did not restore service state"
unset MOCK_CURL_SLEEP STRATEGY_LAB_STAGE30_TIMEOUT

set +e
invalid=$(launcher start 999.999.999.999 standard en 2>&1)
invalid_status=$?
set -e
[ "${invalid_status}" -eq 64 ] || fail "invalid IPv4 target was accepted"
printf '%s\n' "${invalid}" | grep -Fq 'invalid target' || fail "invalid-target reason is missing"

for file in target request result probe state
 do
    sh -n "${MODULE_DIR}/${file}.sh"
done
sh -n "${WORKER}"
sh -n "${PROBE_RUNNER}"
sh -n "${LAUNCHER}"

echo 'PASS: Strategy Lab target, network precheck, and clean baseline contract'
