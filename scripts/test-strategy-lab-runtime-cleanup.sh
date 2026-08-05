#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RUNTIME_UNDER_TEST="${RUNTIME_UNDER_TEST:-${PROJECT_ROOT}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/runtime.sh}"
export RUNTIME_UNDER_TEST

ROOT=$(mktemp -d /tmp/strategy-lab-runtime-cleanup.XXXXXX)
trap 'rm -rf "${ROOT}"' EXIT HUP INT TERM
STATE="${ROOT}/state"
LOG="${ROOT}/signals"
printf '%s\n' running > "${STATE}"
: > "${LOG}"

strategy_lab_job_dir() { printf '%s/jobs/%s\n' "${ROOT}" "$1"; }
STRATEGY_LAB_DIVERT_PORT=9989
STRATEGY_LAB_DVTWS_BIN=/mock/dvtws2
STRATEGY_LAB_RUNTIME_STOP_TIMEOUT=1
STRATEGY_LAB_RUNTIME_KILL_TIMEOUT=1
STRATEGY_LAB_PS_BIN="${ROOT}/ps"
STRATEGY_LAB_SOCKSTAT_BIN="${ROOT}/sockstat"
STRATEGY_LAB_NETSTAT_BIN=/nonexistent

mkdir -p "${ROOT}/jobs/job.test/candidate-runtime"
printf '%s\n' 4242 > "${ROOT}/jobs/job.test/candidate-runtime/dvtws2.pid"

cat > "${ROOT}/ps" <<'EOS'
#!/bin/sh
case "$*" in
  *'ax -o pid= -o command='*)
    [ "$(cat "${MOCK_STATE}")" = stopped ] || printf '%s\n' '4242 /mock/dvtws2 --port=9989 --filter-tcp=443'
    ;;
  *'-p 4242 -o command='*)
    [ "$(cat "${MOCK_STATE}")" = stopped ] || printf '%s\n' '/mock/dvtws2 --port=9989 --filter-tcp=443'
    ;;
esac
EOS
chmod +x "${ROOT}/ps"

cat > "${ROOT}/sockstat" <<'EOS'
#!/bin/sh
[ "$(cat "${MOCK_STATE}")" = stopped ] || printf '%s\n' 'nobody dvtws2 4242 3 div4 *:9989 *:*'
EOS
chmod +x "${ROOT}/sockstat"

export MOCK_STATE="${STATE}"

kill()
{
    signal=$1
    pid=$2
    printf '%s %s\n' "${signal}" "${pid}" >> "${LOG}"
    case "${signal}" in
      -0) [ "$(cat "${STATE}")" != stopped ] ;;
      -TERM) return 0 ;;
      -KILL) printf '%s\n' stopped > "${STATE}" ;;
      *) return 1 ;;
    esac
}

. "${RUNTIME_UNDER_TEST}"

strategy_lab_candidate_stop job.test
[ ! -e "${ROOT}/jobs/job.test/candidate-runtime/dvtws2.pid" ]
grep -q -- '-TERM 4242' "${LOG}"
grep -q -- '-KILL 4242' "${LOG}"
strategy_lab_candidate_runtime_absent

printf '%s\n' running > "${STATE}"
printf '%s\n' 4242 > "${ROOT}/jobs/job.test/candidate-runtime/dvtws2.pid"
STRATEGY_LAB_RUNTIME_KILL_TIMEOUT=0
kill()
{
    signal=$1
    pid=$2
    case "${signal}" in
      -0) return 0 ;;
      -TERM|-KILL) return 0 ;;
    esac
}
if strategy_lab_candidate_stop job.test; then
    echo 'cleanup falsely succeeded while the process and divert socket remained' >&2
    exit 1
fi
[ -e "${ROOT}/jobs/job.test/candidate-runtime/dvtws2.pid" ]

echo 'PASS: Strategy Lab candidate cleanup requires proven process and divert-port absence'
