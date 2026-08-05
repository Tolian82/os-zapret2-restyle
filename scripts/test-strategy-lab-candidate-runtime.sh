#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP=$(mktemp -d /tmp/strategy-lab-candidate-test.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test" "${TMP}/log" "${TMP}/lua"

cat > "${TMP}/bin/timeout" <<'SH'
#!/bin/sh
shift
exec "$@"
SH
cat > "${TMP}/bin/kldstat" <<'SH'
#!/bin/sh
exit 0
SH
cat > "${TMP}/bin/sysctl" <<'SH'
#!/bin/sh
[ "$1" = -n ] && echo 1
exit 0
SH
cat > "${TMP}/bin/ipfw" <<'SH'
#!/bin/sh
state=${MOCK_IPFW_STATE:?}
log=${MOCK_IPFW_LOG:?}
printf '%s\n' "$*" >> "$log"
case "$1" in -q|-qf) shift ;; esac
case "$1" in
    delete)
        n=$2
        [ -f "$state" ] && grep -v "^${n} " "$state" > "${state}.tmp" || :
        [ -f "${state}.tmp" ] && mv "${state}.tmp" "$state"
        ;;
    list)
        n=$2
        [ -f "$state" ] && grep "^${n} " "$state" || true
        ;;
    add)
        [ "${MOCK_IPFW_FAIL_ADD:-0}" = 0 ] || exit 1
        shift
        n=$1
        printf '%s %s\n' "$n" "$*" >> "$state"
        ;;
esac
SH
cat > "${TMP}/bin/drill" <<'SH'
#!/bin/sh
host=$1
printf '%s. 60 IN A 203.0.113.%s\n' "$host" "${MOCK_DRILL_OCTET:-10}"
SH
cat > "${TMP}/bin/curl" <<'SH'
#!/bin/sh
printf 'exit=0 remote_ip=203.0.113.10 http=1.1 code=200 bytes=10\n'
exit "${MOCK_CURL_STATUS:-0}"
SH
cat > "${TMP}/bin/nc" <<'SH'
#!/bin/sh
exit 0
SH
cat > "${TMP}/dvtws2.c" <<'C'
#include <signal.h>
#include <unistd.h>

static volatile sig_atomic_t running = 1;

static void stop_runtime(int signal_number)
{
    (void)signal_number;
    running = 0;
}

int main(void)
{
    signal(SIGTERM, stop_runtime);
    signal(SIGINT, stop_runtime);
    while (running) {
        pause();
    }
    return 0;
}
C
${CC:-cc} -O2 -o "${TMP}/bin/dvtws2" "${TMP}/dvtws2.c"
cat > "${TMP}/bin/daemon" <<'SH'
#!/bin/sh
pidfile=
logfile=
while [ "$#" -gt 0 ]; do
    case "$1" in
        -p) pidfile=$2; shift 2 ;;
        -o) logfile=$2; shift 2 ;;
        -f) shift; break ;;
        *) shift ;;
    esac
done
"$@" >> "$logfile" 2>&1 &
echo $! > "$pidfile"
SH
cat > "${TMP}/bin/sockstat" <<'SH'
#!/bin/sh
pidfile=${MOCK_DVTWS_PIDFILE:?}
[ -r "$pidfile" ] || exit 0
IFS= read -r pid < "$pidfile" || exit 0
kill -0 "$pid" 2>/dev/null || exit 0
state=$(ps -p "$pid" -o stat= 2>/dev/null || true)
case "$state" in
    ''|*Z*) exit 0 ;;
esac
printf 'nobody dvtws2 %s 3 div4 *:9989 *:*\n' "$pid"
SH
chmod +x "${TMP}/bin/"*
: > "${TMP}/ipfw.state"
: > "${TMP}/ipfw.log"
printf '%s\n' telegram.org web.telegram.org > "${TMP}/endpoints.txt"

export SCRIPT_DIR MODULE_DIR
export STRATEGY_LAB_JQ=/usr/bin/jq
export STRATEGY_LAB_RUN_DIR="${TMP}/run"
export STRATEGY_LAB_JOBS_DIR="${TMP}/run/jobs"
export STRATEGY_LAB_LOG_DIR="${TMP}/log"
export STRATEGY_LAB_TIMEOUT_BIN="${TMP}/bin/timeout"
export STRATEGY_LAB_CURL_BIN="${TMP}/bin/curl"
export STRATEGY_LAB_DRILL_BIN="${TMP}/bin/drill"
export STRATEGY_LAB_NC_BIN="${TMP}/bin/nc"
export STRATEGY_LAB_IPFW_BIN="${TMP}/bin/ipfw"
export STRATEGY_LAB_KLDSTAT_BIN="${TMP}/bin/kldstat"
export STRATEGY_LAB_SYSCTL_BIN="${TMP}/bin/sysctl"
export STRATEGY_LAB_DVTWS_BIN="${TMP}/bin/dvtws2"
export STRATEGY_LAB_DAEMON_BIN="${TMP}/bin/daemon"
export STRATEGY_LAB_SOCKSTAT_BIN="${TMP}/bin/sockstat"
export STRATEGY_LAB_NETSTAT_BIN=/nonexistent
export STRATEGY_LAB_LUA_DIR="${TMP}/lua"
export STRATEGY_LAB_WAN_DEVICE=mock0
export MOCK_IPFW_STATE="${TMP}/ipfw.state"
export MOCK_IPFW_LOG="${TMP}/ipfw.log"
export MOCK_DVTWS_PIDFILE="${TMP}/run/jobs/job.test/candidate-runtime/dvtws2.pid"

"${SCRIPT_DIR}/strategy_lab_candidate_runner.sh" job.test "${TMP}/endpoints.txt" "${TMP}/result.json"
/usr/bin/jq -e '.all_pass == true and (.endpoints|length)==2' "${TMP}/result.json" >/dev/null
[ ! -s "${TMP}/ipfw.state" ]
[ ! -e "${MOCK_DVTWS_PIDFILE}" ]
! pgrep -f "${TMP}/bin/dvtws2" >/dev/null 2>&1

grep -q 'add 19100 divert 9989 tcp from any to 203.0.113.10 443' "${TMP}/ipfw.log"

echo 'Strategy Lab candidate runtime success contract passed.'

: > "${TMP}/ipfw.state"
: > "${TMP}/ipfw.log"
rm -rf "${TMP}/run/jobs/job.test/candidate-runtime"
export MOCK_IPFW_FAIL_ADD=1
if "${SCRIPT_DIR}/strategy_lab_candidate_runner.sh" job.test "${TMP}/endpoints.txt" "${TMP}/failed.json"; then
    echo 'candidate runner unexpectedly succeeded during firewall failure' >&2
    exit 1
fi
[ ! -s "${TMP}/ipfw.state" ]
[ ! -e "${MOCK_DVTWS_PIDFILE}" ]
! pgrep -f "${TMP}/bin/dvtws2" >/dev/null 2>&1

echo 'Strategy Lab candidate runtime failure cleanup contract passed.'
