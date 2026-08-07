#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RUNTIME="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/runtime.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-owned-pid.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

STATE="${TEST_ROOT}/state"
SIGNALS="${TEST_ROOT}/signals"
PS="${TEST_ROOT}/ps"
SOCKSTAT="${TEST_ROOT}/sockstat"
JOB_DIR="${TEST_ROOT}/jobs/job.test"
PIDFILE="${JOB_DIR}/candidate-runtime/dvtws2.pid"

mkdir -p "$(dirname "${PIDFILE}")"
printf '%s\n' running > "${STATE}"
printf '%s' 4242 > "${PIDFILE}"
: > "${SIGNALS}"

strategy_lab_job_dir()
{
    printf '%s/jobs/%s\n' "${TEST_ROOT}" "$1"
}

cat > "${PS}" <<'MOCK'
#!/bin/sh
case " $* " in
    *' -p 4242 -o command= '*)
        [ "$(cat "${MOCK_STATE}")" = stopped ] ||
            printf '%s\n' '/mock/dvtws2 --port=9989 --filter-tcp=443'
        ;;
    *' ax -o pid= -o command= '*)
        # Deliberately omit the process from the global snapshot. The candidate
        # was already accepted from its owned PID file, so cleanup must not
        # depend exclusively on rediscovering it here.
        ;;
esac
MOCK
chmod 0755 "${PS}"

cat > "${SOCKSTAT}" <<'MOCK'
#!/bin/sh
# Deliberately return no listener. The owned PID remains the primary evidence
# even when both secondary discovery paths temporarily miss the candidate.
exit 0
MOCK
chmod 0755 "${SOCKSTAT}"

STRATEGY_LAB_DVTWS_BIN=/mock/dvtws2
STRATEGY_LAB_DIVERT_PORT=9989
STRATEGY_LAB_PS_BIN="${PS}"
STRATEGY_LAB_SOCKSTAT_BIN="${SOCKSTAT}"
STRATEGY_LAB_NETSTAT_BIN=/nonexistent
STRATEGY_LAB_RUNTIME_STOP_TIMEOUT=0
STRATEGY_LAB_RUNTIME_KILL_TIMEOUT=0
export MOCK_STATE="${STATE}"

kill()
{
    _signal="$1"
    _pid="$2"
    case "${_signal}" in
        -0)
            [ "${_pid}" = 4242 ] && [ "$(cat "${STATE}")" = running ]
            ;;
        -TERM|-KILL)
            [ "${_pid}" = 4242 ] || return 1
            printf '%s %s\n' "${_signal}" "${_pid}" >> "${SIGNALS}"
            printf '%s\n' stopped > "${STATE}"
            ;;
        *) return 1 ;;
    esac
}

. "${RUNTIME}"

strategy_lab_candidate_process_running "${PIDFILE}" ||
    fail 'owned candidate PID is not accepted by pid-specific identity check'
if strategy_lab_candidate_any_process_running; then
    fail 'fixture unexpectedly exposes the candidate through global process discovery'
fi
if strategy_lab_candidate_divert_port_in_use; then
    fail 'fixture unexpectedly exposes the candidate through socket discovery'
fi
if strategy_lab_candidate_job_runtime_absent job.test; then
    fail 'job runtime was declared absent while the validated owned PID was alive'
fi

strategy_lab_candidate_stop job.test ||
    fail 'candidate cleanup still depends exclusively on secondary discovery paths'

grep -Fq -- '-TERM 4242' "${SIGNALS}" ||
    fail 'owned PID did not receive TERM'
[ ! -e "${PIDFILE}" ] || fail 'owned PID file remains after verified cleanup'
strategy_lab_candidate_job_runtime_absent job.test || fail 'candidate job runtime remains after cleanup'

grep -Fq 'strategy_lab_candidate_signal_owned_pid "${_strategy_lab_pidfile}" TERM' "${RUNTIME}" ||
    fail 'runtime no longer signals the pidfile-owned candidate before the fallback sweep'
grep -Fq 'strategy_lab_candidate_signal_all TERM' "${RUNTIME}" ||
    fail 'secondary global candidate sweep was removed'
grep -Fq 'strategy_lab_candidate_job_runtime_absent "${_strategy_lab_job}"' "${RUNTIME}" ||
    fail 'candidate stop no longer includes the owned PID in absence verification'

sh -n "${RUNTIME}"

echo 'PASS: candidate teardown and absence verification remain anchored to the verified pidfile owner'
