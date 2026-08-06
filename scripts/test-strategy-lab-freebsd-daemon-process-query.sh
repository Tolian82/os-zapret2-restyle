#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
WRAPPER="${SCRIPT_DIR}/process_query.sh"
BACKEND_COMMON="${SCRIPT_DIR}/backend/common.sh"
STRATEGY_COMMON="${SCRIPT_DIR}/strategy_lab/common.sh"
CIRCULAR_OWNER="${SCRIPT_DIR}/strategy_lab/circular_owner.sh"
SERVICE_SOURCE="${SCRIPT_DIR}/zapret_service.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-freebsd-daemon-ps.XXXXXX")
TEST_PID=''
trap '[ -z "${TEST_PID}" ] || kill "${TEST_PID}" 2>/dev/null || true; rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

MOCK_PS="${TEST_ROOT}/ps"
PID_FILE="${TEST_ROOT}/worker.pid"
cat > "${MOCK_PS}" <<'MOCK'
#!/bin/sh
has_xww=false
for arg in "$@"
do
    [ "${arg}" = '-xww' ] && has_xww=true
done
[ "${has_xww}" = true ] || exit 0
case " $* " in
    *' -o lstart= '*) printf '%s\n' "${MOCK_PS_LSTART:-Thu Aug  6 15:42:00 2026}" ;;
    *) printf '%s\n' "${MOCK_PS_COMMAND:-}" ;;
esac
MOCK
chmod 0755 "${MOCK_PS}"

sleep 30 &
TEST_PID=$!
printf '%s\n' "${TEST_PID}" > "${PID_FILE}"

ZAPRET_NATIVE_PS_BIN="${MOCK_PS}"
ZAPRET_PROCESS_QUERY_BIN="${WRAPPER}"
unset COMMON_PS_BIN STRATEGY_LAB_SEMANTIC_PS_BIN STRATEGY_LAB_PS_BIN
export ZAPRET_NATIVE_PS_BIN ZAPRET_PROCESS_QUERY_BIN

. "${BACKEND_COMMON}"

[ "${COMMON_PS_BIN}" = "${WRAPPER}" ] || fail 'backend process checks do not use the FreeBSD-safe wrapper'
[ "${STRATEGY_LAB_SEMANTIC_PS_BIN}" = "${WRAPPER}" ] || fail 'semantic evidence does not inherit the FreeBSD-safe wrapper'
[ "${STRATEGY_LAB_PS_BIN}" = "${WRAPPER}" ] || fail 'Strategy Lab worker checks do not inherit the FreeBSD-safe wrapper'

MOCK_PS_COMMAND='/usr/local/etc/zapret2/binaries/my/dvtws2 --port=989'
export MOCK_PS_COMMAND
common_process_matches "${TEST_PID}" /usr/local/etc/zapret2/binaries/my/dvtws2 ||
    fail 'daemon child command was not detected through ps -xww'

. "${STRATEGY_COMMON}"
MOCK_PS_COMMAND="/bin/sh ${SCRIPT_DIR}/strategy_lab_worker.sh job.DAEMON"
export MOCK_PS_COMMAND
strategy_lab_worker_pid_matches job.DAEMON "${PID_FILE}" ||
    fail 'detached Strategy Lab worker was not detected through ps -xww'

. "${CIRCULAR_OWNER}"
MOCK_PS_LSTART='Thu Aug  6 15:42:00 2026'
export MOCK_PS_LSTART
[ "$(strategy_lab_circular_owner_process_token "${TEST_PID}")" = "${MOCK_PS_LSTART}" ] ||
    fail 'detached circular owner start token was not detected through ps -xww'
MOCK_PS_COMMAND="/bin/sh ${SCRIPT_DIR}/strategy_lab_circular_worker.sh session.DAEMON"
export MOCK_PS_COMMAND
strategy_lab_circular_owner_process_command "${TEST_PID}" |
    grep -Fq strategy_lab_circular_worker.sh ||
    fail 'detached circular owner command was not detected through ps -xww'

grep -Fq 'exec "${ZAPRET_NATIVE_PS_BIN}" -xww "$@"' "${WRAPPER}" ||
    fail 'process wrapper does not force FreeBSD no-TTY and untruncated output'
grep -Fq 'STRATEGY_LAB_SEMANTIC_PS_BIN="${STRATEGY_LAB_SEMANTIC_PS_BIN:-${ZAPRET_PROCESS_QUERY_BIN}}"' "${BACKEND_COMMON}" ||
    fail 'semantic process inspection is not routed through the wrapper'
grep -Fq 'STRATEGY_LAB_SEMANTIC_PS_BIN' "${SERVICE_SOURCE}" ||
    fail 'zapret service semantic evidence no longer uses the injectable process inspector'

sh -n "${WRAPPER}"
sh -n "${BACKEND_COMMON}"
sh -n "${STRATEGY_COMMON}"
sh -n "${CIRCULAR_OWNER}"

echo 'PASS: FreeBSD daemon, supervisor, Strategy Lab worker, and circular owner process queries include no-TTY processes and full command lines'
