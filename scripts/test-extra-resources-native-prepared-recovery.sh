#!/bin/sh
# Execute the REAL prepared native recovery function against an isolated
# process/IPFW model. Never touch a live service, Config or kernel.
set -eu
HERE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SRC="$HERE/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/remove-prepared.XXXXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
OLD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
NEW=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
HASH=$(printf '%064d' 0 | tr 0 c)
export OLD NEW HASH
cat > "$TMP/fakepython" <<'MOCK'
#!/bin/sh
[ "$2" = remove-prepared-context ] || exit 69
if [ "${TRIAL_STATE:-prepared}" = other ]; then
    echo 'remove-prepared none'
else
    printf 'remove-prepared %s %s %s voice %s\n' "${TRIAL_STATE:-prepared}" "$NEW" "$OLD" "$HASH"
fi
MOCK
chmod 700 "$TMP/fakepython"
sed -n '/^extra_resources_native_recover_prepared_service()$/,/^}$/p' "$SRC" > "$TMP/extracted"
sed "s@/usr/local/bin/python3.13@$TMP/fakepython@g" "$TMP/extracted" > "$TMP/native.sh"
sh -n "$TMP/native.sh" || fail syntax
. "$TMP/native.sh"
LOG="$TMP/log"
BACKEND_DIR="$TMP"
ACTIVE_DIR="$TMP/active"
CHILD_PIDFILE="$TMP/child"
SUPERVISOR_MONITOR_PIDFILE="$TMP/monitor"
EXTRA_RESOURCES_SETUP_LOCK_OWNER=1
EXTRA_RESOURCES_NATIVE_REMOVE_RESTORE=1
mkdir -p "$TMP/active" "$TMP/old/release" "$TMP/new/release"
shared_apply_workspace() {
    case "$1" in "$OLD") echo "$TMP/old" ;; "$NEW") echo "$TMP/new" ;; *) return 69 ;; esac
}
shared_apply_bundle_service() { echo "seal:$1:$2" >> "$LOG"; [ "$SEAL_FAIL" = 0 ]; }
shared_apply_native_config() { echo config:$1 >> "$LOG"; echo '{}'; }
shared_apply_json_field() {
    case "$1" in
        *'.result'*) echo committed ;;
        *'.snapshot'*) if [ "$DRIFT" = 1 ]; then echo "${HASH%?}d"; else echo "$HASH"; fi ;;
        *'.enabled'*) echo 1 ;;
        *) return 69 ;;
    esac
}
atomic_verify_tree() {
    echo "tree:$1:$2" >> "$LOG"
    [ "$TREE_FAIL" = 0 ] || return 1
    if [ "$2" = "$ACTIVE_DIR" ]; then
        case "$1" in
            "$TMP/old/release") [ "$ACTIVE_VARIANT" = old ] || return 1 ;;
            "$TMP/new/release") [ "$ACTIVE_VARIANT" = new ] || return 1 ;;
            *) return 1 ;;
        esac
    fi
    return 0
}
launcher_is_running() { [ "$ENGINE" = 1 ]; }
supervisor_is_running() { [ "$ENGINE" = 1 ]; }
apply_runtime_attest_engine_inventory() { echo census >> "$LOG"; [ "$ENGINE" = 0 ]; }
firewall_shared_runtime() {
    echo ipfw:$1 >> "$LOG"
    [ "$IPFW_FAIL" = 0 ] && [ "$1" = verify ] && [ "$3" = - ]
}
shared_apply_recover_prepared_service() {
    echo "recover:$1" >> "$LOG"
    [ "$1" = "prepared $NEW strategies" ]
}
shared_apply_recover_activating_pristine_service() {
    echo "recover-pristine:$1" >> "$LOG"
    [ "$1" = "activating $NEW strategies $OLD voice" ] &&
    [ "$PRISTINE_FAIL" = 0 ]
}
shared_apply_recover_activated_cold_service() {
    echo "recover-cold:$1" >> "$LOG"
    case "$1" in
        "activating $NEW strategies $OLD voice"|"activated $NEW strategies $OLD voice")
            [ "$COLD_FAIL" = 0 ] ;;
        *) return 69 ;;
    esac
}
shared_apply_inspect_service() {
    if [ "$WRONG_INSPECT" = 1 ]; then
        echo restored
    else
        echo "committed $OLD voice"
    fi
}
reset() {
    : > "$LOG"
    SEAL_FAIL=0; TREE_FAIL=0; DRIFT=0; ENGINE=0; IPFW_FAIL=0; PRISTINE_FAIL=0; COLD_FAIL=0; WRONG_INSPECT=0; ACTIVE_VARIANT=old
    TRIAL_STATE=prepared; export TRIAL_STATE
}
run() {
    expected="$1"
    set +e
    extra_resources_native_recover_prepared_service "$OLD" voice "$HASH" >"$TMP/output"
    status=$?
    set -e
    [ "$status" = "$expected" ] || fail "status $status expected $expected"
}
reset; run 0
grep -Fqx "native-remove-prepared-restored=$OLD" "$TMP/output" || fail receipt
grep -Fqx "recover:prepared $NEW strategies" "$LOG" || fail "canonical recovery not used"
reset; TRIAL_STATE=activating; export TRIAL_STATE; run 0
grep -Fqx "recover-pristine:activating $NEW strategies $OLD voice" "$LOG" ||
    fail "activating bypassed original pristine recovery"
reset; TRIAL_STATE=activating; PRISTINE_FAIL=1; export TRIAL_STATE; run 70
[ ! -s "$TMP/output" ] || fail "failed pristine recovery falsely successful"
! grep -Fq 'recover-cold:' "$LOG" || fail "pristine failed over to installed route"
reset; TRIAL_STATE=activating; ACTIVE_VARIANT=new; export TRIAL_STATE; run 0
grep -Fqx "recover-cold:activating $NEW strategies $OLD voice" "$LOG" ||
    fail "installed activating did not delegate original common cold rollback"
! grep -Fq 'recover-pristine:' "$LOG" || fail "installed activating used pristine handler"
reset; TRIAL_STATE=activated; ACTIVE_VARIANT=new; export TRIAL_STATE; run 0
grep -Fqx "recover-cold:activated $NEW strategies $OLD voice" "$LOG" ||
    fail "activated did not delegate original common cold rollback"
reset; TRIAL_STATE=activated; ACTIVE_VARIANT=old; export TRIAL_STATE; run 0
grep -Fqx "recover-cold:activated $NEW strategies $OLD voice" "$LOG" ||
    fail "already-restored active release could not resume cold rollback"
reset; TRIAL_STATE=activated; ACTIVE_VARIANT=new; COLD_FAIL=1; export TRIAL_STATE; run 70
[ ! -s "$TMP/output" ] || fail "failed cold rollback claimed restored"
reset; TRIAL_STATE=activated; ACTIVE_VARIANT=new; WRONG_INSPECT=1; export TRIAL_STATE; run 70
[ ! -s "$TMP/output" ] || fail "foreign inspect owner claimed restored"
for failure in engine drift seal; do
    reset; TRIAL_STATE=activated; ACTIVE_VARIANT=new; export TRIAL_STATE
    case "$failure" in
        engine) ENGINE=1 ;;
        drift) DRIFT=1 ;;
        seal) SEAL_FAIL=1 ;;
    esac
    run 69
    ! grep -Fq 'recover-cold:' "$LOG" || fail "untrusted $failure reached cold recovery"
done
for failure in drift engine ipfw tree seal; do
    reset
    case "$failure" in
        drift) DRIFT=1 ;;
        engine) ENGINE=1 ;;
        ipfw) IPFW_FAIL=1 ;;
        tree) TREE_FAIL=1 ;;
        seal) SEAL_FAIL=1 ;;
    esac
    run 69
    ! grep -Fq 'recover:' "$LOG" || fail "untrusted $failure mutated journal"
done
reset; TRIAL_STATE=other; export TRIAL_STATE
run 0
grep -Fqx 'native-remove-prepared=not-needed' "$TMP/output" || fail foreign
[ ! -s "$LOG" ] || fail "other common phase modified"
echo 'PASS: exact pre-save Remove cold rollback, existing native phases and committed previous-owner inspect receipt'
