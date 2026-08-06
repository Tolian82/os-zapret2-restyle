#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
WRAPPER="${SCRIPT_DIR}/process_query.sh"
BACKEND_COMMON="${SCRIPT_DIR}/backend/common.sh"
LAUNCHER_SOURCE="${SCRIPT_DIR}/backend/launcher.sh"
SUPERVISOR_SOURCE="${SCRIPT_DIR}/backend/supervisor.sh"
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
PID_NEWLINE_FILE="${TEST_ROOT}/worker-newline.pid"
BAD_PID_FILE="${TEST_ROOT}/bad.pid"
EMPTY_PID_FILE="${TEST_ROOT}/empty.pid"
ZERO_PID_FILE="${TEST_ROOT}/zero.pid"
ONE_PID_FILE="${TEST_ROOT}/one.pid"
cat > "${MOCK_PS}" <<'MOCK'
#!/bin/sh
has_xww=false
for arg in "$@"
do
    [ "${arg}" = '-xww' ] && has_xww=true
done
case "${MOCK_PS_MODE:-freebsd}" in
    freebsd) [ "${has_xww}" = true ] || exit 0 ;;
    portable) [ "${has_xww}" = false ] || exit 70 ;;
    *) exit 64 ;;
esac
case " $* " in
    *' -o lstart= '*) printf '%s\n' "${MOCK_PS_LSTART:-Thu Aug  6 15:42:00 2026}" ;;
    *) printf '%s\n' "${MOCK_PS_COMMAND:-}" ;;
esac
MOCK
chmod 0755 "${MOCK_PS}"

sleep 30 &
TEST_PID=$!
# FreeBSD daemon(8) PID files may end at EOF without a trailing newline.
printf '%s' "${TEST_PID}" > "${PID_FILE}"
printf '%s\n' "${TEST_PID}" > "${PID_NEWLINE_FILE}"
printf '%s' '12x' > "${BAD_PID_FILE}"
: > "${EMPTY_PID_FILE}"
printf '%s' '0' > "${ZERO_PID_FILE}"
printf '%s' '1' > "${ONE_PID_FILE}"

ZAPRET_NATIVE_PS_BIN="${MOCK_PS}"
ZAPRET_PROCESS_QUERY_BIN="${WRAPPER}"
ZAPRET_PROCESS_QUERY_SYSTEM=FreeBSD
MOCK_PS_MODE=freebsd
unset COMMON_PS_BIN STRATEGY_LAB_SEMANTIC_PS_BIN STRATEGY_LAB_PS_BIN
export ZAPRET_NATIVE_PS_BIN ZAPRET_PROCESS_QUERY_BIN ZAPRET_PROCESS_QUERY_SYSTEM MOCK_PS_MODE

. "${BACKEND_COMMON}"
. "${LAUNCHER_SOURCE}"
. "${SUPERVISOR_SOURCE}"

[ "${COMMON_PS_BIN}" = "${WRAPPER}" ] || fail 'backend process checks do not use the FreeBSD-safe wrapper'
[ "${STRATEGY_LAB_SEMANTIC_PS_BIN}" = "${WRAPPER}" ] || fail 'semantic evidence does not inherit the FreeBSD-safe wrapper'
[ "${STRATEGY_LAB_PS_BIN}" = "${WRAPPER}" ] || fail 'Strategy Lab worker checks do not inherit the FreeBSD-safe wrapper'
[ "$(common_pidfile_read "${PID_FILE}")" = "${TEST_PID}" ] ||
    fail 'PID file without trailing newline was not read'
[ "$(common_pidfile_read "${PID_NEWLINE_FILE}")" = "${TEST_PID}" ] ||
    fail 'newline-terminated PID file was not read'
[ "$(launcher_pidfile_read "${PID_FILE}")" = "${TEST_PID}" ] ||
    fail 'launcher did not use the shared EOF-safe PID reader'
[ "$(supervisor_pidfile_read "${PID_FILE}")" = "${TEST_PID}" ] ||
    fail 'supervisor did not use the shared EOF-safe PID reader'
for invalid_pid_file in \
    "${BAD_PID_FILE}" \
    "${EMPTY_PID_FILE}" \
    "${ZERO_PID_FILE}" \
    "${ONE_PID_FILE}"
do
    if common_pidfile_read "${invalid_pid_file}" >/dev/null 2>&1; then
        fail "invalid PID file was accepted: ${invalid_pid_file}"
    fi
done

MOCK_PS_COMMAND='/usr/local/etc/zapret2/binaries/my/dvtws2 --port=989'
export MOCK_PS_COMMAND
common_process_matches "${TEST_PID}" /usr/local/etc/zapret2/binaries/my/dvtws2 ||
    fail 'daemon child command was not detected through FreeBSD ps -xww'

. "${STRATEGY_COMMON}"
MOCK_PS_COMMAND="/bin/sh ${SCRIPT_DIR}/strategy_lab_worker.sh job.DAEMON"
export MOCK_PS_COMMAND
strategy_lab_worker_pid_matches job.DAEMON "${PID_FILE}" ||
    fail 'detached Strategy Lab worker with a no-newline PID file was not detected'

. "${CIRCULAR_OWNER}"
MOCK_PS_LSTART='Thu Aug  6 15:42:00 2026'
EXPECTED_PS_LSTART='Thu Aug 6 15:42:00 2026'
export MOCK_PS_LSTART
[ "$(strategy_lab_circular_owner_process_token "${TEST_PID}")" = "${EXPECTED_PS_LSTART}" ] ||
    fail 'detached circular owner start token was not detected through FreeBSD ps -xww'
MOCK_PS_COMMAND="/bin/sh ${SCRIPT_DIR}/strategy_lab_circular_worker.sh session.DAEMON"
export MOCK_PS_COMMAND
strategy_lab_circular_owner_process_command "${TEST_PID}" |
    grep -Fq strategy_lab_circular_worker.sh ||
    fail 'detached circular owner command was not detected through FreeBSD ps -xww'

ZAPRET_PROCESS_QUERY_SYSTEM=Linux
MOCK_PS_MODE=portable
MOCK_PS_COMMAND='portable-pid-selection'
export ZAPRET_PROCESS_QUERY_SYSTEM MOCK_PS_MODE MOCK_PS_COMMAND
[ "$("${WRAPPER}" -p "${TEST_PID}" -o command=)" = portable-pid-selection ] ||
    fail 'non-FreeBSD process query unexpectedly injected BSD selection flags'

grep -Fq 'FreeBSD) exec "${ZAPRET_NATIVE_PS_BIN}" -xww "$@"' "${WRAPPER}" ||
    fail 'FreeBSD process wrapper does not force no-TTY and untruncated output'
grep -Fq '*) exec "${ZAPRET_NATIVE_PS_BIN}" "$@"' "${WRAPPER}" ||
    fail 'non-FreeBSD process wrapper does not preserve caller PID selection'
grep -Fq 'common_pidfile_read()' "${BACKEND_COMMON}" ||
    fail 'shared robust PID-file reader is missing'
grep -Fq 'common_pidfile_read "$1"' "${LAUNCHER_SOURCE}" ||
    fail 'launcher retains a duplicate PID-file parser'
grep -Fq 'common_pidfile_read "$1"' "${SUPERVISOR_SOURCE}" ||
    fail 'supervisor retains a duplicate PID-file parser'
grep -Fq '_strategy_lab_semantic_pid=$(common_pidfile_read \' "${SERVICE_SOURCE}" ||
    fail 'Strategy Lab semantic evidence does not use the shared PID-file reader'
! grep -Fq 'IFS= read -r _strategy_lab_semantic_pid' "${SERVICE_SOURCE}" ||
    fail 'Strategy Lab semantic evidence still rejects no-newline daemon PID files'
grep -Fq 'STRATEGY_LAB_SEMANTIC_PS_BIN="${STRATEGY_LAB_SEMANTIC_PS_BIN:-${ZAPRET_PROCESS_QUERY_BIN}}"' "${BACKEND_COMMON}" ||
    fail 'semantic process inspection is not routed through the wrapper in backend common'
grep -Fq 'STRATEGY_LAB_SEMANTIC_PS_BIN="${STRATEGY_LAB_SEMANTIC_PS_BIN:-${ZAPRET_PROCESS_QUERY_BIN}}"' "${SERVICE_SOURCE}" ||
    fail 'zapret service overrides semantic evidence away from the FreeBSD-safe wrapper'
! grep -Fq 'STRATEGY_LAB_SEMANTIC_PS_BIN="${STRATEGY_LAB_SEMANTIC_PS_BIN:-/bin/ps}"' "${SERVICE_SOURCE}" ||
    fail 'zapret service still restores the obsolete direct /bin/ps default'

sh -n "${WRAPPER}"
sh -n "${BACKEND_COMMON}"
sh -n "${LAUNCHER_SOURCE}"
sh -n "${SUPERVISOR_SOURCE}"
sh -n "${STRATEGY_COMMON}"
sh -n "${CIRCULAR_OWNER}"
sh -n "${SERVICE_SOURCE}"

echo 'PASS: one shared reader handles newline and EOF PID files while rejecting malformed and unsafe values'
