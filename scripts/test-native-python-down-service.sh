#!/bin/sh
# Exact extracted production FD9 dispatcher: fail-safe shell Stop/Status when
# the qualified Python interpreter is absent. No actual IPFW/process mutation.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SERVICE="${ROOT}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/zapret-python-down-service.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
for fn in stop_legacy_without_python_service service_with_lifecycle_lock; do
    sed -n "/^${fn}()$/,/^}$/p" "${SERVICE}" >> "${TMP}/functions.sh"
done
grep -Fq 'stop_legacy_without_python_service()' "${TMP}/functions.sh" ||
    fail "missing native Python-down Stop implementation"
grep -Fq 'service_with_lifecycle_lock()' "${TMP}/functions.sh" ||
    fail "missing native FD9 dispatcher"
sh -n "${TMP}/functions.sh"
. "${TMP}/functions.sh"
# WAN is present in the Python-down fixture; test the subsequent Python gate.
wan_first_service() { return 0; }

mkdir -p "${TMP}/active"
ACTIVE_DIR="${TMP}/active"
LIFECYCLE_LOCK_FILE="${TMP}/original-fd9.lock"
LOG="${TMP}/events"
STATE="${TMP}/state"
OUT="${TMP}/stdout"
ERR="${TMP}/stderr"
CHILD_PIDFILE="${TMP}/child.pid"
SUPERVISOR_MONITOR_PIDFILE="${TMP}/supervisor.pid"
RULE_BASE=19000 RULE_MAX=19010
PYTHON_RUNTIME="${TMP}/missing-python3"
MOCK_RECORD=0 MOCK_PENDING=0 MOCK_STOP_FAIL=0 MOCK_POST_DRIFT=0
: > "${LOG}"

cat > "${TMP}/lockf" <<'LOCKF'
#!/bin/sh
# A real FD9 must have been inherited from the dispatcher shell.
: >&9 || exit 75
exit 0
LOCKF
chmod 0700 "${TMP}/lockf"
LOCKF_BIN="${TMP}/lockf"

common_error() { echo "ERROR: $*" >&2; }
shared_apply_has_record_service() { [ "${MOCK_RECORD}" = 1 ]; }
extra_resources_block_pending_start_service() { [ "${MOCK_PENDING}" = 0 ]; }
shared_apply_inspect_service() { return 69; }
preflight_shared_apply_journal() {
    echo forbidden-python-gate >> "${LOG}"
    return 69
}
orchestrator_native_status() {
    [ "$#" -eq 5 ] || fail "status did not inspect native PID/IPFW inputs"
    echo status-query >> "${LOG}"
    case "$(cat "${STATE}")" in
        running) echo "zapret is running"; return 0 ;;
        stopped) echo "zapret is not running"; return 1 ;;
        *) echo "zapret is in an incomplete runtime state"; return 2 ;;
    esac
}
stop_service() {
    echo native-stop >> "${LOG}"
    [ "${MOCK_STOP_FAIL}" = 0 ] || return 70
    if [ "${MOCK_POST_DRIFT}" = 1 ]; then
        echo incomplete > "${STATE}"
    else
        echo stopped > "${STATE}"
    fi
    echo "zapret is not running (stopped)"
}
service_dispatch() {
    echo "dispatch:$1" >> "${LOG}"
    case "$1" in
        status)
            if shared_apply_has_record_service; then
                echo "zapret is in an incomplete runtime state"
                return 2
            fi
            orchestrator_native_status "${CHILD_PIDFILE}" "${SUPERVISOR_MONITOR_PIDFILE}" "${RULE_BASE}" "${RULE_MAX}" "${ACTIVE_DIR}"
            ;;
        stop) stop_service ;;
        *) echo "unexpected-dispatch:$1" >> "${LOG}"; return 99 ;;
    esac
}
check()
{
    wanted="$1"
    shift
    set +e
    service_with_lifecycle_lock 2 "$@" > "${OUT}" 2> "${ERR}"
    rc=$?
    set -e
    [ "${rc}" -eq "${wanted}" ] || {
        cat "${OUT}" "${ERR}" >&2
        fail "$*: returned ${rc}, expected ${wanted}"
    }
}
assert_no_stop()
{
    ! grep -Fq native-stop "${LOG}" || fail "unverified owner was stopped"
    ! grep -Fq forbidden-python-gate "${LOG}" || fail "fell into unavailable Python gate"
}
clear_events() { : > "${LOG}"; : > "${OUT}"; : > "${ERR}"; }

echo running > "${STATE}"
check 0 status
grep -Fqx 'zapret is running' "${OUT}" || fail "running status suppressed without Python"
clear_events
check 0 stop
[ "$(grep -Fxc native-stop "${LOG}")" -eq 1 ] ||
    fail "verified native owner not stopped exactly once"
[ "$(grep -Fxc status-query "${LOG}")" -eq 2 ] ||
    fail "native status was not checked both before and after Stop"
[ "$(cat "${STATE}")" = stopped ] || fail "process state not stopped"
check 1 status
grep -Fqx 'zapret is not running' "${OUT}" || fail "stopped status inaccurate"
clear_events
check 0 stop
assert_no_stop
grep -Fqx 'zapret is not running (stopped)' "${OUT}" ||
    fail "stopped Stop must be idempotent without deleting IPFW"

echo incomplete > "${STATE}"
clear_events
check 69 stop
assert_no_stop
grep -Fq 'incomplete/unknown legacy owner' "${ERR}" || fail "no unknown-owner diagnostic"

echo running > "${STATE}"
MOCK_RECORD=1
clear_events
check 69 stop
assert_no_stop
grep -Fq 'shared/Voice ownership' "${ERR}" || fail "unverified shared owner not diagnosed"
check 2 status
grep -Fqx 'zapret is in an incomplete runtime state' "${OUT}" ||
    fail "unverifiable shared Status claimed running/stopped"
MOCK_RECORD=0

: > "${ACTIVE_DIR}/voice-plan.json"
clear_events
check 69 stop
assert_no_stop
rm "${ACTIVE_DIR}/voice-plan.json"
ln -s "${TMP}/missing-target" "${ACTIVE_DIR}/voice-plan.json"
clear_events
check 69 stop
assert_no_stop
rm "${ACTIVE_DIR}/voice-plan.json"

MOCK_PENDING=1
clear_events
check 69 stop
assert_no_stop
MOCK_PENDING=0

MOCK_STOP_FAIL=1
clear_events
check 70 stop
[ "$(cat "${STATE}")" = running ] || fail "failed stop incorrectly declared stopped"
MOCK_STOP_FAIL=0

MOCK_POST_DRIFT=1
clear_events
check 70 stop
grep -Fq 'did not verify complete native shutdown' "${ERR}" ||
    fail "post-stop divergence was presented as success"
MOCK_POST_DRIFT=0

echo running > "${STATE}"
for action in start restart reconfigure shared-apply-run telegram-voice-enable upstream-install; do
    clear_events
    check 69 "${action}"
    assert_no_stop
    [ ! -s "${LOG}" ] || fail "${action} entered mutation/status code without Python"
    [ ! -s "${OUT}" ] || fail "${action} contaminated machine-readable stdout"
done

# Service status remains read-only and does not create a missing Python
# interpreter, alter the original FD9 file or touch the native owner journal.
[ ! -e "${PYTHON_RUNTIME}" ] || fail "missing interpreter was created"
echo 'PASS: Python-down legacy native Stop/Status under FD9, idempotency, incomplete/common/Voice/pending refusal and Start/Apply no-mutation'
