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
EXTRA_GUARD_VERIFY_FAIL=0
EXTRA_GUARD_EVIDENCE_FAIL=0
GIT_DIRTY=0
RECOVERY_SERVICE_CALLS="${TMP_ROOT}/recovery-service-calls"
RECEIPT_CAPTURE="${TMP_ROOT}/captured-checkpoint"
EVIDENCE_CAPTURE="${TMP_ROOT}/captured-attestation"

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
printf '%s\n' aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa > "${GIT_COMMIT_STATE}"
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
    strategy-lab-status)
        case "$(cat "${TEST_SERVICE_STATE}")" in
            running) exit 0 ;;
            stopped) exit 1 ;;
            *) exit 2 ;;
        esac
        ;;
    strategy-lab-start)
        printf '%s\n' started >> "${TEST_RECOVERY_SERVICE_CALLS}"
        if [ "${TEST_START_FAIL:-0}" = 1 ] &&
           [ "$(cat "${TEST_GIT_RELEASE_STATE}")" = v1.0.3 ]; then
            exit 70
        fi
        printf '%s\n' running > "${TEST_SERVICE_STATE}"
        exit 0
        ;;
    strategy-lab-stop)
        printf '%s\n' stopped >> "${TEST_RECOVERY_SERVICE_CALLS}"
        [ "${TEST_STOP_FAIL:-0}" != 1 ] || exit 70
        printf '%s\n' stopped > "${TEST_SERVICE_STATE}"
        exit 0
        ;;
    upstream-install)
        [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] || exit 75
        printf '%s\n' native-install-fd9 >> "${TEST_RECOVERY_SERVICE_CALLS}"
        ( STRATEGY_LAB_LIFECYCLE_OWNER=1 UPSTREAM_RUNTIME_LIFECYCLE_OWNER=1 \
            "${TEST_TRANSACTION}" install-under-native-lock "${2:-}" ) \
            9>"${TEST_LIFECYCLE_LOCK}"
        ;;
    upstream-recover-mutating)
        [ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] || exit 75
        printf '%s\n' native-fd9 >> "${TEST_RECOVERY_SERVICE_CALLS}"
        ( UPSTREAM_RECOVERY_LIFECYCLE_OWNER=1 \
            "${TEST_TRANSACTION}" recover-mutating-under-parent-lock ) \
            9>"${TEST_LIFECYCLE_LOCK}"
        ;;
    stop)
        [ "${UPSTREAM_RUNTIME_LIFECYCLE_OWNER:-0}" != 1 ] || exit 75
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
        case "${3:-}" in
            v1.0.4\^\{commit\}) printf '%s\n' aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa ;;
            v1.0.3\^\{commit\}) printf '%s\n' bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb ;;
            v1.0.2\^\{commit\}) printf '%s\n' cccccccccccccccccccccccccccccccccccccccc ;;
            HEAD) cat "${TEST_GIT_COMMIT_STATE}" ;;
            *) exit 64 ;;
        esac
        ;;
    cat-file)
        [ "${2:-}" = -e ] || exit 64
        case "${3:-}" in
            aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\^\{commit\}|bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\^\{commit\}) exit 0 ;;
            *) exit 64 ;;
        esac
        ;;
    status)
        [ "${2:-}" = --porcelain ] || exit 64
        [ "${3:-}" = --untracked-files=no ] || exit 64
        if [ "${TEST_GIT_DIRTY:-0}" = 1 ]; then echo ' M user-owned-file'; fi
        ;;
    checkout|reset)
        target=${3:-}
        [ -n "${target}" ] || exit 64
        printf '%s\n' "${target}" > "${TEST_GIT_COMMIT_STATE}"
        if [ "${target}" = aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa ]; then
            printf '%s\n' v1.0.4 > "${TEST_GIT_RELEASE_STATE}"
        elif [ "${target}" = bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb ]; then
            printf '%s\n' v1.0.3 > "${TEST_GIT_RELEASE_STATE}"
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
if [ "${1:-}" = snapshot ] && [ "${TEST_EXTRA_GUARD_FAIL}" = 1 ]; then
    mkdir -p "${TEST_ROLLBACK_DIR}/extra-managed"
    printf '%s\n' partial > "${TEST_ROLLBACK_DIR}/extra-managed/partial"
    exit 70
fi
# When snapshot identity cannot be sealed, the attempt must abort before
# checkout, leave no fake committed checkpoint and permit safe retry.
if [ "${1:-}" = snapshot-evidence ]; then
    printf '%s\n' '{"schema":1,"mock":"original backups"}' > "${TEST_ROLLBACK_DIR}/backup-attestation.json"
    [ "${TEST_EXTRA_GUARD_EVIDENCE_FAIL}" != 1 ] || exit 70
    exit 0
fi
if [ "${1:-}" = verify-evidence ]; then
    [ "${TEST_EXTRA_GUARD_EVIDENCE_FAIL}" != 1 ] || exit 70
    [ "${2:-}" = 1 ] || exit 70
    grep -Fqx '{"schema":1,"mock":"original backups"}' "${TEST_ROLLBACK_DIR}/backup-attestation.json" || exit 70
    exit 0
fi
# Prepared cleanup requires live-resource verification as well as a saved
# backup verification, even though a mutating checkout may remove live files.
if [ "${1:-}" = verify ] && [ "${TEST_EXTRA_GUARD_VERIFY_FAIL}" = 1 ]; then
    exit 70
fi
# The mock manifest is empty; a successful snapshot has no managed backup.
[ "${1:-}" != verify-snapshot ] || [ ! -e "${TEST_ROLLBACK_DIR}/extra-managed" ] || exit 70
exit 0
MOCK
chmod +x "${EXTRA_GUARD_MOCK}"

cat > "${SETUP_MOCK}" <<'MOCK'
#!/bin/sh
[ "${1:-}" = install-under-parent-lock ] || exit 64
version=${2:-v1.0.4}
[ "${UPSTREAM_RUNTIME_LIFECYCLE_OWNER:-0}" = 1 ] || exit 75
[ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] || exit 75
[ "$(cat "${TEST_SERVICE_STATE}")" = stopped ] || exit 75
printf '%s\n' candidate-build-under-fd9 >> "${TEST_RECOVERY_SERVICE_CALLS}"
[ -f "${TEST_ROLLBACK_DIR}/checkpoint" ] || exit 65
grep -Fqx 'phase=mutating' "${TEST_ROLLBACK_DIR}/checkpoint" || exit 65
cp "${TEST_ROLLBACK_DIR}/checkpoint" "${TEST_RECEIPT_CAPTURE}" || exit 65
cp "${TEST_ROLLBACK_DIR}/backup-attestation.json" "${TEST_EVIDENCE_CAPTURE}" || exit 65
printf '%s\n' "${version}" > "${TEST_GIT_RELEASE_STATE}"
printf '%s\n' bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb > "${TEST_GIT_COMMIT_STATE}"
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

inspect_recovery()
{
    ROLLBACK_DIR="${ROLLBACK_DIR}" \
    RUN_DIR="${TMP_ROOT}/run" LOCKF_BIN="${LOCKF_MOCK}" \
    "${TRANSACTION}" inspect-recovery
}

run_setup_action()
{
    _action="$1"
    shift
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
    TEST_EXTRA_GUARD_VERIFY_FAIL="${EXTRA_GUARD_VERIFY_FAIL}" \
    TEST_EXTRA_GUARD_EVIDENCE_FAIL="${EXTRA_GUARD_EVIDENCE_FAIL}" \
    TEST_EVIDENCE_CAPTURE="${EVIDENCE_CAPTURE}" \
    TEST_RECOVERY_SERVICE_CALLS="${RECOVERY_SERVICE_CALLS}" \
    TEST_TRANSACTION="${TRANSACTION}" \
    TEST_LIFECYCLE_LOCK="${TMP_ROOT}/native-fd9" \
    TEST_GIT_DIRTY="${GIT_DIRTY}" \
    TEST_RECEIPT_CAPTURE="${RECEIPT_CAPTURE}" \
    TEST_STOP_FAIL="${TEST_STOP_FAIL:-0}" \
    TEST_START_FAIL="${TEST_START_FAIL:-0}" \
    "${TRANSACTION}" "${_action}" "$@"
}

run_transaction()
{
    run_setup_action install "$1"
}

recover_prepared()
{
    run_setup_action recover-prepared
}

recover_mutating_stopped()
{
    run_setup_action recover-mutating-stopped
}

# Bypass of the original native lifecycle FD9 must be refused.
before_commit=$(cat "${GIT_COMMIT_STATE}")
if run_setup_action install-under-parent-lock v1.0.3 >/dev/null 2>&1; then
    fail "native-lockless upstream install was accepted"
fi
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before_commit}" ] ||
    fail "native-lockless install changed upstream Git"

# Candidate activation fails after Stop/checkpoint and candidate checkout.
# Original checkout and running service must both be restored.
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "failed candidate activation reported success"
fi
[ "$(cat "${ACTIVE_RELEASE_FILE}")" = v1.0.4 ] || fail "active release marker was not restored"
[ "$(cat "${GIT_RELEASE_STATE}")" = v1.0.4 ] || fail "previous Git release was not restored"
[ "$(cat "${GIT_COMMIT_STATE}")" = aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa ] || fail "previous Git commit was not restored"
[ "$(cat "${ZAPRET_DIR}/binaries/my/dvtws2")" = old-binary ] || fail "previous binary was not restored"
[ "$(cat "${SERVICE_STATE}")" = running ] || fail "previous running state was not restored"
[ "$(cat "${SETUP_STATUS}")" = failed ] || fail "failed operation did not remain visible"
[ ! -e "${ROLLBACK_DIR}" ] || fail "automatic rollback leaked checkpoint"
[ "$(sed -n '1p' "${RECEIPT_CAPTURE}")" = schema=2 ] || fail "missing sealed checkpoint schema"
[ -s "${EVIDENCE_CAPTURE}" ] || fail "upstream backup identity was not sealed before mutation"
grep -Fqx 'phase=mutating' "${RECEIPT_CAPTURE}" || fail "snapshot not marked before mutation"
grep -Fqx 'previous_commit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' "${RECEIPT_CAPTURE}" || fail "old commit not persisted"
grep -Fqx 'previous_release=v1.0.4' "${RECEIPT_CAPTURE}" || fail "old release not persisted"
grep -Fqx 'service_was_running=1' "${RECEIPT_CAPTURE}" || fail "old service state not persisted"
grep -Fqx 'previous_binaries=1' "${RECEIPT_CAPTURE}" || fail "old binaries not persisted"
[ "$(inspect_recovery)" = 'recovery=none' ] || fail "no-snapshot view failed"
[ "$(head -n 4 "${RECOVERY_SERVICE_CALLS}" | tr '\n' '|')" = 'native-install-fd9|stopped|candidate-build-under-fd9|started|' ] ||
    fail "FD9 -> native Stop -> build -> native Start ordering not proven"
[ "$(stat -c %a "${ZAPRET_DIR}/lua/zapret-lib.lua")" = 644 ] || fail "Lua permissions were not normalized"
[ "$(stat -c %a "${ZAPRET_DIR}/files/fake/test.bin")" = 644 ] || fail "blob permissions were not normalized"

# A successful activation publishes the selected release only after setup succeeds
# and repairs restrictive data modes inherited from the setup process.
printf '%s\n' success > "${SETUP_RESULT}"
printf '%s\n' running > "${SERVICE_STATE}"
printf '%s\n' v1.0.4 > "${GIT_RELEASE_STATE}"
printf '%s\n' aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa > "${GIT_COMMIT_STATE}"
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
if inspect_recovery > "${TMP_ROOT}/legacy-inspection"; then
    fail "unidentified legacy rollback was trusted"
fi
grep -Fqx 'recovery=unverified' "${TMP_ROOT}/legacy-inspection" ||
    fail "legacy rollback refusal not diagnostic"
[ "$(cat "${ROLLBACK_DIR}/pending-recovery")" = protected ] ||
    fail "inspection changed legacy evidence"

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
# Failure while sealing old compiled binary bytes is still pre-mutation and
# must not leave an unrelated RECOVERY_REQUIRED blocker.
EXTRA_GUARD_EVIDENCE_FAIL=1
before_commit=$(cat "${GIT_COMMIT_STATE}")
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "failed sealed backup unexpectedly activated upstream"
fi
[ ! -e "${ROLLBACK_DIR}" ] || fail "failed backup seal left partial snapshot"
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before_commit}" ] || fail "backup seal changed checkout"
EXTRA_GUARD_EVIDENCE_FAIL=0
run_transaction v1.0.3 >/dev/null || fail "retry after failed snapshot did not succeed"
[ ! -e "${ROLLBACK_DIR}" ] || fail "retry left rollback data"
[ "$(cat "${SETUP_STATUS}")" = ready ] || fail "retry did not reach ready"

mkdir "${ROLLBACK_DIR}"
cp "${RECEIPT_CAPTURE}" "${ROLLBACK_DIR}/checkpoint"
cp "${EVIDENCE_CAPTURE}" "${ROLLBACK_DIR}/backup-attestation.json"
output=$(inspect_recovery) || fail "durable checkpoint unreadable"
printf '%s\n' "${output}" | grep -Fqx 'recovery=required' || fail "required phase not shown"
printf '%s\n' "${output}" | grep -Fqx 'previous_commit=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' || fail "previous commit absent"
printf '%s\n' "${output}" | grep -Fqx 'previous_release=v1.0.3' || fail "previous release absent"
printf '%s\n' "${output}" | grep -Fqx 'service_was_running=1' || fail "previous service state absent"
grep -Fqx 'phase=mutating' "${ROLLBACK_DIR}/checkpoint" || fail "inspection changed evidence"
sed -i 's/phase=mutating/phase=invalid/' "${ROLLBACK_DIR}/checkpoint"
if inspect_recovery > "${TMP_ROOT}/invalid-inspection"; then
    fail "tampered checkpoint trusted"
fi
grep -Fqx 'recovery=unverified' "${TMP_ROOT}/invalid-inspection" || fail "tamper not reported"
rm "${ROLLBACK_DIR}/checkpoint"
ln -s "${RECEIPT_CAPTURE}" "${ROLLBACK_DIR}/checkpoint"
if inspect_recovery > "${TMP_ROOT}/symlink-inspection"; then
    fail "symlinked checkpoint trusted"
fi
[ -L "${ROLLBACK_DIR}/checkpoint" ] || fail "inspection changed symlink"

# Only a fully attested PREPARED snapshot (no runtime mutation) may be
# released. Any possible runtime mutation remains blocked for future audited
# recovery; the rejected evidence must survive untouched.
rm -rf "${ROLLBACK_DIR}"
mkdir -p "${ROLLBACK_DIR}/binaries"
cp -Rp "${ZAPRET_DIR}/binaries/my" "${ROLLBACK_DIR}/binaries/"
sed 's/phase=mutating/phase=prepared/' "${RECEIPT_CAPTURE}" > "${ROLLBACK_DIR}/checkpoint"
cp "${EVIDENCE_CAPTURE}" "${ROLLBACK_DIR}/backup-attestation.json"
grep -Fqx 'phase=prepared' "${ROLLBACK_DIR}/checkpoint" || fail "prepared fixture missing"
before_commit=$(cat "${GIT_COMMIT_STATE}")
before_release=$(cat "${ACTIVE_RELEASE_FILE}")
before_service=$(cat "${SERVICE_STATE}")
cp "${ROLLBACK_DIR}/checkpoint" "${TMP_ROOT}/prepared.original"

printf '%s\n' modified > "${ROLLBACK_DIR}/binaries/my/dvtws2"
if recover_prepared >/dev/null 2>&1; then
    fail "tampered binary backup was cleared"
fi
[ -f "${ROLLBACK_DIR}/checkpoint" ] || fail "tampered backup evidence was erased"
cp -Rp "${ZAPRET_DIR}/binaries/my/dvtws2" "${ROLLBACK_DIR}/binaries/my/dvtws2"

printf '%s\n' incomplete > "${SERVICE_STATE}"
if recover_prepared >/dev/null 2>&1; then
    fail "incomplete service owner was allowed to clear snapshot"
fi
printf '%s\n' running > "${SERVICE_STATE}"

printf '%s\n' cccccccccccccccccccccccccccccccccccccccc > "${GIT_COMMIT_STATE}"
if recover_prepared >/dev/null 2>&1; then
    fail "foreign checkout cleared prepared backup"
fi
printf '%s\n' "${before_commit}" > "${GIT_COMMIT_STATE}"

sed 's/phase=prepared/phase=mutating/' "${TMP_ROOT}/prepared.original" > "${ROLLBACK_DIR}/checkpoint"
if recover_prepared >/dev/null 2>&1; then
    fail "possibly mutated snapshot incorrectly cleared"
fi
[ -d "${ROLLBACK_DIR}" ] || fail "mutating backup evidence was erased"

cp "${TMP_ROOT}/prepared.original" "${ROLLBACK_DIR}/checkpoint"
printf '%s\n' foreign > "${ROLLBACK_DIR}/unexpected"
if recover_prepared >/dev/null 2>&1; then
    fail "foreign snapshot entry was silently erased"
fi
[ -f "${ROLLBACK_DIR}/unexpected" ] || fail "foreign evidence changed"
rm "${ROLLBACK_DIR}/unexpected"

mkdir "${ROLLBACK_DIR}/binaries/foreign"
if recover_prepared >/dev/null 2>&1; then
    fail "unexpected nested binary backup entry was erased"
fi
[ -d "${ROLLBACK_DIR}/binaries/foreign" ] || fail "nested backup evidence lost"
rmdir "${ROLLBACK_DIR}/binaries/foreign"

EXTRA_GUARD_VERIFY_FAIL=1
if recover_prepared >/dev/null 2>&1; then
    fail "prepared recovery cleared backup despite altered live resources"
fi
[ -f "${ROLLBACK_DIR}/checkpoint" ] ||
    fail "live-resource mismatch erased prepared snapshot"
EXTRA_GUARD_VERIFY_FAIL=0
# Even matching current bytes cannot authorize cleanup after evidence tamper.
printf '%s\n' modified > "${ROLLBACK_DIR}/backup-attestation.json"
if recover_prepared >/dev/null 2>&1; then
    fail "prepared recovery removed tampered binary attestation"
fi
[ -f "${ROLLBACK_DIR}/checkpoint" ] || fail "tampered attestation was deleted"
cp "${EVIDENCE_CAPTURE}" "${ROLLBACK_DIR}/backup-attestation.json"

output=$(recover_prepared) || fail "attested pre-mutation recovery was refused"
[ "${output}" = 'RECOVERY_PREPARED_CLEARED: previous runtime and service are unchanged' ] ||
    fail "prepared recovery reported incorrect result"
[ ! -e "${ROLLBACK_DIR}" ] || fail "verified prepared snapshot was not released"
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before_commit}" ] || fail "recovery changed checkout"
[ "$(cat "${ACTIVE_RELEASE_FILE}")" = "${before_release}" ] || fail "recovery changed active release"
[ "$(cat "${SERVICE_STATE}")" = "${before_service}" ] || fail "recovery changed service"
[ "$(cat "${SETUP_STATUS}")" = failed ] || fail "recovery did not record prior aborted setup"
[ "$(inspect_recovery)" = 'recovery=none' ] || fail "recovery left pending state"

# Exact schema-2 `mutating` evidence from a power cut: an explicitly
# requested operation may restore ONLY a verified STOPPED native owner. Test
# both refused states and a successful original-state restoration.
mkdir -p "${ROLLBACK_DIR}/binaries"
cp -Rp "${ZAPRET_DIR}/binaries/my" "${ROLLBACK_DIR}/binaries/"
cp "${RECEIPT_CAPTURE}" "${ROLLBACK_DIR}/checkpoint"
cp "${EVIDENCE_CAPTURE}" "${ROLLBACK_DIR}/backup-attestation.json"
printf '%s\n' cccccccccccccccccccccccccccccccccccccccc > "${GIT_COMMIT_STATE}"
printf '%s\n' v1.0.2 > "${GIT_RELEASE_STATE}"
printf '%s\n' damaged-candidate > "${ZAPRET_DIR}/binaries/my/dvtws2"
before=$(cat "${GIT_COMMIT_STATE}")
if run_setup_action recover-mutating-under-parent-lock >/dev/null 2>&1; then
    fail "direct recovery without setup+native owner was accepted"
fi
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before}" ] || fail "unauthorized recovery mutated checkout"

if recover_mutating_stopped >/dev/null 2>&1; then
    fail "mutating recovery stopped an already running service"
fi
[ "$(cat "${SERVICE_STATE}")" = running ] || fail "recovery changed running service"
printf '%s\n' incomplete > "${SERVICE_STATE}"
if recover_mutating_stopped >/dev/null 2>&1; then
    fail "mutating recovery accepted incomplete native owner"
fi
printf '%s\n' stopped > "${SERVICE_STATE}"
GIT_DIRTY=1
if recover_mutating_stopped >/dev/null 2>&1; then
    fail "mutating recovery reset dirty tracked upstream tree"
fi
GIT_DIRTY=0
EXTRA_GUARD_EVIDENCE_FAIL=1
if recover_mutating_stopped >/dev/null 2>&1; then
    fail "mutating recovery accepted corrupt saved binary proof"
fi
EXTRA_GUARD_EVIDENCE_FAIL=0
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before}" ] || fail "unsafe preflight changed checkout"
[ -f "${ROLLBACK_DIR}/checkpoint" ] || fail "preflight erased restoration evidence"
sed 's/schema=2/schema=1/' "${RECEIPT_CAPTURE}" > "${ROLLBACK_DIR}/checkpoint"
if recover_mutating_stopped >/dev/null 2>&1; then
    fail "schema-1 mutating snapshot was promoted to safe recovery"
fi
cp "${RECEIPT_CAPTURE}" "${ROLLBACK_DIR}/checkpoint"
output=$(recover_mutating_stopped) || fail "attested stopped-owner recovery failed"
printf '%s\n' "${output}" | grep -Fq 'RECOVERY_MUTATING_RESTORED:' ||
    fail "explicit stopped-owner recovery reported incorrect result"
[ "$(cat "${GIT_COMMIT_STATE}")" = bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb ] ||
    fail "original checkout was not restored after interruption"
[ "$(cat "${GIT_RELEASE_STATE}")" = v1.0.3 ] || fail "original git release was not restored"
[ "$(cat "${ACTIVE_RELEASE_FILE}")" = v1.0.3 ] || fail "original release marker was not restored"
[ "$(cat "${ZAPRET_DIR}/binaries/my/dvtws2")" = new-binary ] ||
    fail "original compiled binary was not restored"
[ "$(cat "${SERVICE_STATE}")" = running ] || fail "original running service not restarted"
[ ! -e "${ROLLBACK_DIR}" ] || fail "restored recovery retained active rollback blocker"
grep -Fqx native-fd9 "${RECOVERY_SERVICE_CALLS}" || fail "native FD9 route not exercised"
grep -Fqx started "${RECOVERY_SERVICE_CALLS}" || fail "native Start route not exercised"

# Initially STOPPED services stay stopped after an otherwise valid recovery.
mkdir -p "${ROLLBACK_DIR}/binaries"
cp -Rp "${ZAPRET_DIR}/binaries/my" "${ROLLBACK_DIR}/binaries/"
sed 's/service_was_running=1/service_was_running=0/' "${RECEIPT_CAPTURE}" > "${ROLLBACK_DIR}/checkpoint"
cp "${EVIDENCE_CAPTURE}" "${ROLLBACK_DIR}/backup-attestation.json"
printf '%s\n' stopped > "${SERVICE_STATE}"
printf '%s\n' cccccccccccccccccccccccccccccccccccccccc > "${GIT_COMMIT_STATE}"
printf '%s\n' damaged-candidate > "${ZAPRET_DIR}/binaries/my/dvtws2"
recover_mutating_stopped >/dev/null || fail "stopped-before upgrade recovery failed"
[ "$(cat "${SERVICE_STATE}")" = stopped ] || fail "recovery unexpectedly started previously stopped service"
[ ! -e "${ROLLBACK_DIR}" ] || fail "stopped state recovery retained evidence"

# The native status exit code must be preserved. Incomplete/foreign owner
# cannot start a new upstream transaction or acquire a backup directory.
printf '%s\n' incomplete > "${SERVICE_STATE}"
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "incomplete native owner was accepted for a new upgrade"
fi
[ ! -e "${ROLLBACK_DIR}" ] || fail "unsafe native status created backup data"
printf '%s\n' stopped > "${SERVICE_STATE}"
printf '%s\n' fail > "${SETUP_RESULT}"
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "mocked failed install from stopped state unexpectedly succeeded"
fi
[ "$(cat "${SERVICE_STATE}")" = stopped ] ||
    fail "stopped native service was erroneously restarted on rollback"
[ ! -e "${ROLLBACK_DIR}" ] ||
    fail "failed upgrade from stopped state left rollback evidence"
printf '%s\n' running > "${SERVICE_STATE}"

# A refused native Stop must leave both original service and sealed recovery
# evidence untouched. The test harness alone discards the fixture afterwards.
TEST_STOP_FAIL=1
before_commit=$(cat "${GIT_COMMIT_STATE}")
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "failed native Stop permitted upstream mutation"
fi
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before_commit}" ] ||
    fail "refused native Stop mutated Git"
[ "$(cat "${SERVICE_STATE}")" = running ] ||
    fail "failed Stop changed original running service"
[ -f "${ROLLBACK_DIR}/checkpoint" ] &&
grep -Fqx 'phase=mutating' "${ROLLBACK_DIR}/checkpoint" ||
    fail "failed Stop discarded mutating recovery evidence"
rm -rf "${ROLLBACK_DIR}" # test fixture only
TEST_STOP_FAIL=0

# Fault injection after checkout/build but before new native Start. Only the
# original release may restart; target failure must roll back bytes and state.
printf '%s\n' success > "${SETUP_RESULT}"
TEST_START_FAIL=1
if run_transaction v1.0.3 >/dev/null 2>&1; then
    fail "failed target native Start reported upgrade success"
fi
[ "$(cat "${GIT_COMMIT_STATE}")" = "${before_commit}" ] ||
    fail "failed target Start did not roll back checkout"
[ "$(cat "${GIT_RELEASE_STATE}")" = v1.0.4 ] ||
    fail "failed target Start did not restore previous Git release"
[ "$(cat "${SERVICE_STATE}")" = running ] ||
    fail "original native service was not restarted after target Start failure"
[ "$(cat "${ACTIVE_RELEASE_FILE}")" = v1.0.4 ] ||
    fail "failed target Start left changed active release"
[ ! -e "${ROLLBACK_DIR}" ] || fail "successful original rollback retained state"
TEST_START_FAIL=0

# Real production entrypoint and setup must agree about inherited FD9.
grep -Fq 'upstream-install)' "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh" ||
    fail "native upstream-install dispatcher is missing"
grep -Fq 'strategy-lab-stop' "${TRANSACTION}" ||
    fail "upstream mutation does not invoke native stop under FD9"
grep -Fq 'install-under-native-lock' "${TRANSACTION}" ||
    fail "upstream transaction does not demand inherited FD9"
grep -Fq 'UPSTREAM_RUNTIME_LIFECYCLE_OWNER' "${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/setup.sh" ||
    fail "setup backend does not recognize inherited FD9"
sh -n "${TRANSACTION}"
echo "PASS: original FD9 upstream Stop/build/Start, failure rollback and recovery evidence"
