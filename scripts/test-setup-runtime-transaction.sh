#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TRANSACTION="${TRANSACTION:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh}"
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/zapret-setup-transaction-test.XXXXXX")
trap 'rm -rf "${TMP_ROOT}"' EXIT INT TERM HUP

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

ZAPRET_DIR="${TMP_ROOT}/zapret2"
STATE_DIR="${TMP_ROOT}/state"
ROLLBACK_DIR="${STATE_DIR}/runtime-rollback"
ACTIVE_RELEASE_FILE="${STATE_DIR}/runtime.release"
SETUP_STATUS="${STATE_DIR}/setup.status"
SERVICE_STATE="${TMP_ROOT}/service.state"
GIT_RELEASE_STATE="${TMP_ROOT}/git.release"
GIT_COMMIT_STATE="${TMP_ROOT}/git.commit"
SETUP_RESULT="${TMP_ROOT}/setup.result"
SETUP_MOCK="${TMP_ROOT}/setup"
SERVICE_MOCK="${TMP_ROOT}/service"
CONFIGCTL_MOCK="${TMP_ROOT}/configctl"
GIT_MOCK="${TMP_ROOT}/git"
LOCKF_MOCK="${TMP_ROOT}/lockf"
EXTRA_GUARD_MOCK="${TMP_ROOT}/extra-guard"
EXTRA_GUARD_FAIL=0

mkdir -p \
    "${ZAPRET_DIR}/.git" \
    "${ZAPRET_DIR}/lua" \
    "${ZAPRET_DIR}/files/fake" \
    "${ZAPRET_DIR}/binaries/my" \
    "${STATE_DIR}"
printf '%s\n' old-binary > "${ZAPRET_DIR}/binaries/my/dvtws2"
printf '%s\n' old-lua > "${ZAPRET_DIR}/lua/zapret-lib.lua"
printf '%s\n' old-blob > "${ZAPRET_DIR}/files/fake/test.bin"
chmod 0755 "${ZAPRET_DIR}/binaries/my/dvtws2"
chmod 0640 "${ZAPRET_DIR}/lua/zapret-lib.lua" "${ZAPRET_DIR}/files/fake/test.bin"
printf '%s\n' v1.0.4 > "${GIT_RELEASE_STATE}"
printf '%s\n' oldcommit > "${GIT_COMMIT_STATE}"
printf '%s\n' running > "${SERVICE_STATE}"
printf '%s\n' fail > "${SETUP_RESULT}"
printf '%s\n' ready > "${SETUP_STATUS}"

cat > "${SERVICE_MOCK}" <<'MOCK'
#!/bin/sh
case "${1:-}" in
    status)
        case "$(cat "${TEST_SERVICE_STATE}")" in
            running) exit 0 ;;
            stopped) exit 1 ;;
            incomplete) exit 2 ;;
            *) exit 64 ;;
        esac
        ;;
    stop)
        printf '%s\n' stopped > "${TEST_SERVICE_STATE}"
        exit 0
        ;;
    *)
        exit 64
        ;;
esac
MOCK
chmod +x "${SERVICE_MOCK}"

cat > "${CONFIGCTL_MOCK}" <<'MOCK'
#!/bin/sh
case "$*" in
    'zapret start')
        printf '%s\n' running > "${TEST_SERVICE_STATE}"
        printf '%s\n' OK
        ;;
    *)
        exit 64
        ;;
esac
MOCK
chmod +x "${CONFIGCTL_MOCK}"

cat > "${GIT_MOCK}" <<'MOCK'
#!/bin/sh
[ "${1:-}" = -C ] || exit 64
shift 2
case "${1:-}" in
    describe)
        cat "${TEST_GIT_RELEASE_STATE}"
        ;;
    rev-parse)
        cat "${TEST_GIT_COMMIT_STATE}"
        ;;
    checkout|reset)
        target=${3:-}
        [ -n "${target}" ] || exit 64
        printf '%s\n' "${target}" > "${TEST_GIT_COMMIT_STATE}"
        if [ "${target}" = oldcommit ]; then
            printf '%s\n' v1.0.4 > "${TEST_GIT_RELEASE_STATE}"
        fi
        ;;
    *)
        exit 64
        ;;
esac
MOCK
chmod +x "${GIT_MOCK}"

cat > "${LOCKF_MOCK}" <<'MOCK'
#!/bin/sh
[ "$1" = -s ] || exit 64
shift
[ "$1" = -t ] || exit 64
shift 2
[ -n "${1:-}" ] || exit 64
shift
exec "$@"
MOCK
chmod +x "${LOCKF_MOCK}"

cat > "${EXTRA_GUARD_MOCK}" <<'MOCK'
#!/bin/sh
# Fail after writing only backup data; never mutate the running runtime.
if [ "${1:-}" = snapshot ]; then
    mkdir -p "${TEST_ROLLBACK_DIR}/extra-managed"
    printf '%s\n' partial > "${TEST_ROLLBACK_DIR}/extra-managed/partial"
    [ "${TEST_EXTRA_GUARD_FAIL}" != 1 ] || exit 70
fi
exit 0
MOCK
chmod +x "${EXTRA_GUARD_MOCK}"

cat > "${SETUP_MOCK}" <<'MOCK'
#!/bin/sh
[ "${1:-}" = install-under-parent-lock ] || exit 64
version=${2:-v1.0.4}
printf '%s\n' "${version}" > "${TEST_GIT_RELEASE_STATE}"
printf '%s\n' candidatecommit > "${TEST_GIT_COMMIT_STATE}"
printf '%s\n' new-binary > "${TEST_ZAPRET_DIR}/binaries/my/dvtws2"
printf '%s\n' candidate-lua > "${TEST_ZAPRET_DIR}/lua/zapret-lib.lua"
printf '%s\n' candidate-blob > "${TEST_ZAPRET_DIR}/files/fake/test.bin"
chmod 0640 "${TEST_ZAPRET_DIR}/lua/zapret-lib.lua" "${TEST_ZAPRET_DIR}/files/fake/test.bin"

if [ "$(cat "${TEST_SETUP_RESULT}")" = fail ]; then
    printf '%s\n' stopped > "${TEST_SERVICE_STATE}"
    printf '%s\n' failed > "${TEST_SETUP_STATUS}"
    exit 1
fi

printf '%s\n' ready > "${TEST_SETUP_STATUS}"
exit 0
MOCK
chmod +x "${SETUP_MOCK}"

run_transaction()
{
    TEST_SERVICE_STATE="${SERVICE_STATE}" \
    TEST_GIT_RELEASE_STATE="${GIT_RELEASE_STATE}" \
    TEST_GIT_COMMIT_STATE="${GIT_COMMIT_STATE}" \
    TEST_SETUP_RESULT="${SETUP_RESULT}" \
    TEST_SETUP_STATUS="${SETUP_STATUS}" \
    TEST_ZAPRET_DIR="${ZAPRET_DIR}" \
    SETUP_SCRIPT="${SETUP_MOCK}" \
    LOCKF_BIN="${LOCKF_MOCK}" \
    RUN_DIR="${TMP_ROOT}/run" \
    SERVICE_SCRIPT="${SERVICE_MOCK}" \
    CONFIGCTL="${CONFIGCTL_MOCK}" \
    GIT_BIN="${GIT_MOCK}" \
    FIND_BIN="$(command -v find)" \
    ZAPRET_DIR="${ZAPRET_DIR}" \
    STATE_DIR="${STATE_DIR}" \
    SETUP_STATUS="${SETUP_STATUS}" \
    ACTIVE_RELEASE_FILE="${ACTIVE_RELEASE_FILE}" \
    ROLLBACK_DIR="${ROLLBACK_DIR}" \
    EXTRA_PYTHON="$(command -v sh)" \
    EXTRA_GUARD="${EXTRA_GUARD_MOCK}" \
    TEST_ROLLBACK_DIR="${ROLLBACK_DIR}" \
    TEST_EXTRA_GUARD_FAIL="${EXTRA_GUARD_FAIL}" \
    "${TRANSACTION}" install "$1"
}

# Candidate activation fails after changing checkout, binaries, permissions, and
# service state. The previous release and running service must be restored.
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "failed candidate activation reported success"
fi
[ "$(cat "${ACTIVE_RELEASE_FILE}")" = v1.0.4 ] || fail "active release marker was not restored"
[ "$(cat "${GIT_RELEASE_STATE}")" = v1.0.4 ] || fail "previous Git release was not restored"
[ "$(cat "${GIT_COMMIT_STATE}")" = oldcommit ] || fail "previous Git commit was not restored"
[ "$(cat "${ZAPRET_DIR}/binaries/my/dvtws2")" = old-binary ] || fail "previous binary was not restored"
[ "$(cat "${SERVICE_STATE}")" = running ] || fail "previous running state was not restored"
[ "$(cat "${SETUP_STATUS}")" = failed ] || fail "failed operation did not remain visible"
[ "$(stat -c %a "${ZAPRET_DIR}/lua/zapret-lib.lua")" = 644 ] || fail "Lua permissions were not normalized"
[ "$(stat -c %a "${ZAPRET_DIR}/files/fake/test.bin")" = 644 ] || fail "blob permissions were not normalized"

# A successful activation publishes the selected release only after setup succeeds
# and repairs restrictive data modes inherited from the setup process.
printf '%s\n' success > "${SETUP_RESULT}"
printf '%s\n' running > "${SERVICE_STATE}"
printf '%s\n' v1.0.4 > "${GIT_RELEASE_STATE}"
printf '%s\n' oldcommit > "${GIT_COMMIT_STATE}"
printf '%s\n' old-binary > "${ZAPRET_DIR}/binaries/my/dvtws2"
run_transaction v1.0.3 >/dev/null
[ "$(cat "${ACTIVE_RELEASE_FILE}")" = v1.0.3 ] || fail "successful activation did not publish selected release"
[ "$(cat "${GIT_RELEASE_STATE}")" = v1.0.3 ] || fail "successful activation has wrong Git release"
[ "$(cat "${SERVICE_STATE}")" = running ] || fail "successful activation changed running state"
[ "$(cat "${ZAPRET_DIR}/binaries/my/dvtws2")" = new-binary ] || fail "successful activation did not retain candidate binary"
[ "$(stat -c %a "${ZAPRET_DIR}/lua/zapret-lib.lua")" = 644 ] || fail "successful Lua permissions were not normalized"
[ "$(stat -c %a "${ZAPRET_DIR}/files/fake/test.bin")" = 644 ] || fail "successful blob permissions were not normalized"
[ ! -e "${ROLLBACK_DIR}" ] || fail "successful activation retained rollback data"

# Power-loss evidence from an interrupted upstream upgrade is never deleted
# simply to prepare a new operation. No changes to Git/service may occur.
mkdir -p "${ROLLBACK_DIR}"
printf '%s\n' protected > "${ROLLBACK_DIR}/pending-recovery"
before_commit=$(cat "${GIT_COMMIT_STATE}")
before_service=$(cat "${SERVICE_STATE}")
run_transaction v1.0.3 >/dev/null 2>&1 && fail "pending rollback evidence was overwritten"
[ "$(cat "${ROLLBACK_DIR}/pending-recovery")" = protected ] ||
    fail "pending recovery evidence was lost"
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before_commit}" ] ||
    fail "blocked setup changed Git checkout"
[ "$(cat "${SERVICE_STATE}")" = "${before_service}" ] ||
    fail "blocked setup changed service state"

# An error while preparing a NEW snapshot cannot block the next attempt.
# Only a preexisting interrupted rollback must remain untouched.
rm -rf "${ROLLBACK_DIR}"
mkdir -p "${STATE_DIR}/extra-resources"
printf '%s\n' '{"schema":1,"files":{}}' > "${STATE_DIR}/extra-resources/installed.json"
EXTRA_GUARD_FAIL=1
before_commit=$(cat "${GIT_COMMIT_STATE}")
before_service=$(cat "${SERVICE_STATE}")
before_release=$(cat "${ACTIVE_RELEASE_FILE}")
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "failed snapshot unexpectedly completed"
fi
[ ! -e "${ROLLBACK_DIR}" ] || fail "failed snapshot left false recovery-required state"
[ "$(cat "${SETUP_STATUS}")" = failed ] || fail "snapshot failure status was not recorded"
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before_commit}" ] || fail "snapshot failure changed checkout"
[ "$(cat "${SERVICE_STATE}")" = "${before_service}" ] || fail "snapshot failure changed service"
[ "$(cat "${ACTIVE_RELEASE_FILE}")" = "${before_release}" ] || fail "snapshot failure changed release"
EXTRA_GUARD_FAIL=0
run_transaction v1.0.3 >/dev/null || fail "retry after failed snapshot did not succeed"
[ ! -e "${ROLLBACK_DIR}" ] || fail "retry left rollback data"
[ "$(cat "${SETUP_STATUS}")" = ready ] || fail "retry did not reach ready"

sh -n "${TRANSACTION}"
echo "PASS: transactional runtime activation and pre-mutation snapshot failure retry"
