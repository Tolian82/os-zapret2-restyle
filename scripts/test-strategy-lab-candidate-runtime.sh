#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
TMP=$(mktemp -d /tmp/strategy-lab-candidate-test.XXXXXX)
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/bin" "${TMP}/run/jobs/job.test" "${TMP}/log" "${TMP}/lua"
# Production job directories are created with mktemp -d and start private. The temporary
# dvtws2 runtime later drops to nobody, so this fixture must preserve that boundary.
chmod 0700 "${TMP}/run/jobs/job.test"

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
counter=${MOCK_IPFW_COUNTER:?}
printf '%s\n' "$*" >> "$log"
if [ "$1" = -a ] && [ "$2" = list ]; then
    n=$3
    packets=$(cat "$counter")
    rule=$(grep "^${n} " "$state" 2>/dev/null || true)
    [ -n "$rule" ] || exit 0
    printf '%s %s %s %s\n' "$n" "$packets" "$((packets * 64))" "${rule#* }"
    exit 0
fi
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
type=${2:-A}
printf '%s\n' ';; QUESTION SECTION:'
printf '%s. 60 IN %s 198.51.100.99\n' "$host" "$type"
printf '%s\n' ';; ANSWER SECTION:'
printf '%s. 60 IN A 203.0.113.%s\n' "$host" "${MOCK_DRILL_OCTET:-10}"
printf '%s\n' ';; AUTHORITY SECTION:'
printf '%s. 60 IN A 198.51.100.98\n' "$host"
SH
cat > "${TMP}/bin/curl" <<'SH'
#!/bin/sh
counter=${MOCK_IPFW_COUNTER:?}
packets=$(cat "$counter")
printf '%s\n' "$((packets + 1))" > "$counter"
printf 'exit=0 remote_ip=203.0.113.10 http=1.1 code=200 bytes=10\n'
exit "${MOCK_CURL_STATUS:-0}"
SH
cat > "${TMP}/bin/nc" <<'SH'
#!/bin/sh
counter=${MOCK_IPFW_COUNTER:?}
packets=$(cat "$counter")
printf '%s\n' "$((packets + 1))" > "$counter"
exit 0
SH
cat > "${TMP}/dvtws2.c" <<'C'
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

static volatile sig_atomic_t running = 1;

static void stop_runtime(int signal_number)
{
    (void)signal_number;
    running = 0;
}

static int require_other_access(const char *path, mode_t bit, const char *label)
{
    struct stat st;
    if (path == NULL || stat(path, &st) != 0 || (st.st_mode & bit) == 0) {
        fprintf(stderr, "file_open_test: Permission denied\n");
        fprintf(stderr, "cannot access %s '%s'\n", label, path == NULL ? "" : path);
        return 0;
    }
    return 1;
}

int main(void)
{
    const char *jobdir = getenv("MOCK_DVTWS_JOBDIR");
    const char *runtime = getenv("MOCK_DVTWS_RUNTIME_DIR");
    const char *hostlist = getenv("MOCK_DVTWS_HOSTLIST");

    /* Model dvtws2 after --user=nobody: it is neither owner nor owning group. */
    if (!require_other_access(jobdir, S_IXOTH, "job directory") ||
        !require_other_access(runtime, S_IXOTH, "candidate runtime directory") ||
        !require_other_access(hostlist, S_IROTH, "hostlist file")) {
        return 1;
    }

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
child=$!
echo "$child" > "$pidfile"
# FreeBSD daemon(8) stays resident when -p/-o is used. Model that behavior so
# production startup must detach the monitor before it can run readiness checks.
wait "$child"
rm -f "$pidfile"
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
printf '%s\n' 0 > "${TMP}/ipfw.counter"
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
export MOCK_IPFW_COUNTER="${TMP}/ipfw.counter"
export MOCK_DVTWS_PIDFILE="${TMP}/run/jobs/job.test/candidate-runtime/dvtws2.pid"
export MOCK_DVTWS_JOBDIR="${TMP}/run/jobs/job.test"
export MOCK_DVTWS_RUNTIME_DIR="${TMP}/run/jobs/job.test/candidate-runtime"
export MOCK_DVTWS_HOSTLIST="${TMP}/run/jobs/job.test/candidate-runtime/hostlist.txt"

set +e
/usr/bin/timeout 15 "${SCRIPT_DIR}/strategy_lab_candidate_runner.sh" job.test "${TMP}/endpoints.txt" "${TMP}/result.json"
candidate_status=$?
set -e
if [ "${candidate_status}" -ne 0 ]; then
    echo "candidate runtime regression failed or timed out: rc=${candidate_status}" >&2
    ps ax -o pid= -o ppid= -o stat= -o command= | grep -F "${TMP}" >&2 || true
    if [ -r "${MOCK_DVTWS_PIDFILE}" ]; then
        printf 'candidate pidfile: ' >&2
        cat "${MOCK_DVTWS_PIDFILE}" >&2 || true
    fi
    [ ! -r "${TMP}/run/jobs/job.test/candidate-runtime/dvtws2.log" ] || {
        echo 'candidate dvtws2.log:' >&2
        cat "${TMP}/run/jobs/job.test/candidate-runtime/dvtws2.log" >&2 || true
    }
    echo 'candidate ipfw state:' >&2
    cat "${TMP}/ipfw.state" >&2 || true
    exit "${candidate_status}"
fi
/usr/bin/jq -e '
    .all_pass == true and (.endpoints|length)==2 and
    all(.endpoints[];
        .selected_ip=="203.0.113.10" and
        .remote_ip=="203.0.113.10" and
        .endpoint_match==true and
        .firewall.rule==19100 and
        .firewall.intercepted==true and
        .firewall.packets_after > .firewall.packets_before
    )
' "${TMP}/result.json" >/dev/null
[ ! -s "${TMP}/ipfw.state" ]
[ ! -e "${MOCK_DVTWS_PIDFILE}" ]
! pgrep -f "${TMP}/bin/dvtws2" >/dev/null 2>&1
[ "$(stat -c '%a' "${TMP}/run/jobs/job.test")" = 700 ]

grep -q 'add 19100 divert 9989 tcp from me to 203.0.113.10 443' "${TMP}/ipfw.log"

echo 'Strategy Lab candidate runtime success contract passed with Python answer-section DNS binding, post-drop hostlist access, and private cleanup.'

: > "${TMP}/ipfw.state"
: > "${TMP}/ipfw.log"
printf '%s\n' 0 > "${TMP}/ipfw.counter"
rm -rf "${TMP}/run/jobs/job.test/candidate-runtime"
export MOCK_IPFW_FAIL_ADD=1
if "${SCRIPT_DIR}/strategy_lab_candidate_runner.sh" job.test "${TMP}/endpoints.txt" "${TMP}/failed.json"; then
    echo 'candidate runner unexpectedly succeeded during firewall failure' >&2
    exit 1
fi
[ ! -s "${TMP}/ipfw.state" ]
[ ! -e "${MOCK_DVTWS_PIDFILE}" ]
! pgrep -f "${TMP}/bin/dvtws2" >/dev/null 2>&1
[ "$(stat -c '%a' "${TMP}/run/jobs/job.test")" = 700 ]

echo 'Strategy Lab candidate runtime failure cleanup contract passed.'
