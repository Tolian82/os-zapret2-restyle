#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LIFECYCLE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/lifecycle.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-restoration.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

STATE="${TEST_ROOT}/state"
STARTS="${TEST_ROOT}/starts"
STOPS="${TEST_ROOT}/stops"
TIMEOUT_LOG="${TEST_ROOT}/timeout.log"
SERVICE="${TEST_ROOT}/service"
TIMEOUT="${TEST_ROOT}/timeout"

cat > "${SERVICE}" <<'MOCK'
#!/bin/sh
state=$(cat "${MOCK_STATE}")
case "${1:-}" in
    strategy-lab-status)
        case "${state}" in
            RUNNING) exit 0 ;;
            STOPPED) exit 1 ;;
            INCOMPLETE) exit 2 ;;
            *) exit 3 ;;
        esac
        ;;
    strategy-lab-stop)
        count=$(cat "${MOCK_STOPS}")
        printf '%s\n' $((count + 1)) > "${MOCK_STOPS}"
        printf '%s\n' STOPPED > "${MOCK_STATE}"
        exit 0
        ;;
    strategy-lab-start)
        count=$(cat "${MOCK_STARTS}")
        count=$((count + 1))
        printf '%s\n' "${count}" > "${MOCK_STARTS}"
        case "${MOCK_MODE}" in
            recover)
                if [ "${count}" -eq 1 ]; then
                    printf '%s\n' INCOMPLETE > "${MOCK_STATE}"
                    exit 1
                fi
                printf '%s\n' RUNNING > "${MOCK_STATE}"
                exit 0
                ;;
            late-running)
                printf '%s\n' RUNNING > "${MOCK_STATE}"
                exit 1
                ;;
            fail-twice)
                printf '%s\n' INCOMPLETE > "${MOCK_STATE}"
                exit 1
                ;;
            *) exit 64 ;;
        esac
        ;;
    *) exit 64 ;;
esac
MOCK
chmod 0755 "${SERVICE}"

cat > "${TIMEOUT}" <<'MOCK'
#!/bin/sh
limit="$1"
shift
printf '%s %s\n' "${limit}" "${2:-}" >> "${MOCK_TIMEOUT_LOG}"
exec "$@"
MOCK
chmod 0755 "${TIMEOUT}"

export MOCK_STATE="${STATE}"
export MOCK_STARTS="${STARTS}"
export MOCK_STOPS="${STOPS}"
export MOCK_TIMEOUT_LOG="${TIMEOUT_LOG}"
STRATEGY_LAB_SERVICE_SCRIPT="${SERVICE}"
STRATEGY_LAB_TIMEOUT_BIN="${TIMEOUT}"
unset STRATEGY_LAB_RESTORE_TIMEOUT 2>/dev/null || true
. "${LIFECYCLE}"

[ "${STRATEGY_LAB_RESTORE_TIMEOUT}" -ge 30 ] ||
    fail 'restoration timeout is shorter than the bounded native startup path'

reset_fixture()
{
    printf '%s\n' STOPPED > "${STATE}"
    printf '%s\n' 0 > "${STARTS}"
    printf '%s\n' 0 > "${STOPS}"
    : > "${TIMEOUT_LOG}"
}

reset_fixture
export MOCK_MODE=recover
strategy_lab_restore_running_state ||
    fail 'one interrupted start was not normalized and recovered'
[ "$(cat "${STATE}")" = RUNNING ] || fail 'recovery did not reach RUNNING'
[ "$(cat "${STARTS}")" -eq 2 ] || fail 'recovery did not use exactly one second start attempt'
[ "$(cat "${STOPS}")" -eq 1 ] || fail 'INCOMPLETE first attempt was not normalized exactly once'
[ "$(grep -c '^45 strategy-lab-start$' "${TIMEOUT_LOG}")" -eq 2 ] ||
    fail 'start attempts did not receive the full restoration timeout'
[ "$(grep -c '^10 strategy-lab-stop$' "${TIMEOUT_LOG}")" -eq 1 ] ||
    fail 'recovery normalization did not use the bounded stop action'

reset_fixture
export MOCK_MODE=late-running
strategy_lab_restore_running_state ||
    fail 'nonzero outer start result was rejected even though service reached RUNNING'
[ "$(cat "${STATE}")" = RUNNING ] || fail 'late-running fixture did not remain RUNNING'
[ "$(cat "${STARTS}")" -eq 1 ] || fail 'healthy late completion triggered an unnecessary retry'
[ "$(cat "${STOPS}")" -eq 0 ] || fail 'healthy late completion was unnecessarily stopped'

reset_fixture
export MOCK_MODE=fail-twice
if strategy_lab_restore_running_state; then
    fail 'two failed starts were incorrectly accepted'
fi
[ "$(cat "${STARTS}")" -eq 2 ] || fail 'restoration performed an unbounded or incomplete retry sequence'
[ "$(cat "${STOPS}")" -eq 2 ] || fail 'failed starts were not normalized after each attempt'
[ "$(cat "${STATE}")" = STOPPED ] || fail 'final failed restoration was left INCOMPLETE'

sh -n "${LIFECYCLE}"

echo 'PASS: RUNNING restoration has sufficient bounded time, one recovery attempt, and safe failure normalization'
