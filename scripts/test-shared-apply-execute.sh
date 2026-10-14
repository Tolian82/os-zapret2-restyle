#!/bin/sh
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/shared-exec.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^shared_apply_execute_service()$/,/^}$/p' "$SOURCE" > "$ROOT/executor.sh"
sed -n '/^shared_apply_save_retired_legacy_config_service()$/,/^}$/p' "$SOURCE" >> "$ROOT/executor.sh"
sh -n "$ROOT/executor.sh" || fail "shell syntax"
. "$ROOT/executor.sh"
ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
mkdir -p "$ROOT/work/release"
: > "$ROOT/work/plan.json"
: > "$ROOT/work/candidate.xml"
LOG="$ROOT/steps.log"
preflight_voice_cutover_journals() { [ "$1" = common-apply ]; }
shared_apply_workspace() { echo "$ROOT/work"; }
shared_apply_inspect_service() {
    if [ "$BAD_OWNER" = 1 ]; then echo "legacy-common-activated $ID voice"
    else echo "legacy-config-saving $ID voice"; fi
}
apply_runtime_rehydrate_retired_legacy() {
    echo runtime-rehydrate >> "$LOG"
    [ "$REHYDRATE_RC" -eq 0 ]
}
shared_apply_require_tools() { return 0; }
shared_apply_bundle_service() { printf "bundle:%s\n" "$1" >> "$LOG"; [ "$1" != verify ] || [ "$BAD_BUNDLE" = 0 ]; }
shared_apply_native_config() {
    case "$1" in
        preflight) echo '{"snapshot":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","enabled":"1","base":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","candidate":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","fields":["voice.telegram.enabled"]}' ;;
        save) echo config-save >> "$LOG"; return "$SAVE_RC" ;;
        saved)
            echo config-readback >> "$LOG"
            [ "$SAVED_RC" -eq 0 ] || return "$SAVED_RC"
            echo '{"result":"committed","snapshot":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","enabled":"1"}'
            ;;
        *) return 1 ;;
    esac
}
shared_apply_json_field() {
    case "$1" in
        *".enabled"*)
            # The saved worker runs inside $(...), so side effects cannot
            # change a parent-shell flag. Inspect this exact readback input.
            saved_input=$(cat)
            case "$saved_input" in
                *'"result":"committed"'*)
                    if [ "$SAVED_MODE_DRIFT" = 1 ]; then echo 0; else echo 1; fi ;;
                *) echo 1 ;;
            esac ;;
        *".base"*) printf "%064d\n" 0 | tr 0 a ;;
        *".candidate"*) printf "%064d\n" 0 | tr 0 b ;;
        *".result"*) echo committed ;;
        *".snapshot"*)
            field_input=$(cat)
            case "$field_input" in
                *'"result":"committed"'*)
                    if [ "$SAVED_DIGEST_DRIFT" = 1 ]; then
                        printf "%064d\n" 0 | tr 0 c
                    else
                        printf "%064d\n" 0 | tr 0 b
                    fi ;;
                *) printf "%064d\n" 0 | tr 0 b ;;
            esac ;;
        *".fields"*) echo voice.telegram.enabled ;;
        *) return 1 ;;
    esac
}
shared_apply_record_service() {
    printf "record:%s\n" "$1" >> "$LOG"
    [ "$1" != "$BAD_RECORD" ]
}
apply_runtime_probe() { echo runtime-probe >> "$LOG"; [ "$PROBE_RC" -eq 0 ]; }
apply_runtime_activate() { echo runtime-activate >> "$LOG"; [ "$ACTIVATE_RC" -eq 0 ] || return 1; [ "$TAMPER_DURING_ACTIVATION" = 0 ] || BAD_BUNDLE=1; }
apply_runtime_restore() { echo runtime-restore >> "$LOG"; [ "$RESTORE_RC" -eq 0 ]; }
apply_runtime_attest_activated() {
    echo runtime-attest >> "$LOG"
    ATTEST_COUNT=$((ATTEST_COUNT + 1))
    [ "$ATTEST_RC" -eq 0 ] &&
    { [ "$ATTEST_FAIL_AT" -eq 0 ] || [ "$ATTEST_FAIL_AT" -ne "$ATTEST_COUNT" ]; }
}
apply_runtime_commit() { echo runtime-commit >> "$LOG"; [ "$COMMIT_RC" -eq 0 ]; }
reset() { : > "$LOG"; SAVE_RC=0; ACTIVATE_RC=0; RESTORE_RC=0; COMMIT_RC=0; BAD_RECORD=none; BAD_BUNDLE=0; TAMPER_DURING_ACTIVATION=0; PROBE_RC=0; ATTEST_RC=0; ATTEST_COUNT=0; ATTEST_FAIL_AT=0; SAVED_RC=0; SAVED_DIGEST_DRIFT=0; SAVED_MODE_DRIFT=0; BAD_OWNER=0; REHYDRATE_RC=0; }
expect_status() {
    expected="$1"; shift
    set +e
    shared_apply_execute_service "$ID" voice > "$ROOT/response.txt"
    actual="$?"
    set -e
    [ "$actual" -eq "$expected" ] || fail "return=$actual expected=$expected"
    actual_steps=$(tr "\n" " " < "$LOG")
    [ "$actual_steps" = "$*" ] || fail "steps: $actual_steps"
}
reset
expect_status 0 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest runtime-commit record:committed '
grep -Fqx "applied-id=$ID" "$ROOT/response.txt" || fail "successful receipt"
reset; BAD_BUNDLE=1
expect_status 69 'bundle:verify '
reset; SAVE_RC=69
expect_status 69 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save runtime-restore record:restored '
reset; SAVE_RC=70
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:requires-review '
reset; TAMPER_DURING_ACTIVATION=1
expect_status 69 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-restore record:restored '
reset; ATTEST_RC=1
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest record:requires-review '
reset; PROBE_RC=1
expect_status 69 'bundle:verify runtime-probe '
reset; ACTIVATE_RC=1
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:requires-review '
reset; COMMIT_RC=1
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest runtime-commit record:requires-review '
reset; SAVED_RC=69
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback record:requires-review '
reset; SAVED_DIGEST_DRIFT=1
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback record:requires-review '
reset; SAVED_MODE_DRIFT=1
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback record:requires-review '
reset; ATTEST_FAIL_AT=2
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest record:requires-review '
reset; BAD_RECORD=activated
expect_status 69 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated runtime-restore record:restored '
reset; BAD_RECORD=config-saved
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved '
reset; RESTORE_RC=1; SAVE_RC=69
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save runtime-restore record:requires-review '
# First native save of a previously switched old owner, only after
# durable legacy-config-saving. No commit or terminal journal write.
run_retired() {
    expected="$1"; shift
    set +e
    shared_apply_save_retired_legacy_config_service "$ID" > "$ROOT/retired-response.txt"
    actual="$?"
    set -e
    [ "$actual" -eq "$expected" ] ||
        fail "legacy Config status=$actual expected=$expected"
    steps=$(tr '\n' ' ' < "$LOG")
    [ "$steps" = "$*" ] || fail "legacy Config steps: $steps"
}
reset
run_retired 0 'bundle:verify runtime-rehydrate runtime-attest config-save config-readback bundle:verify runtime-attest '
grep -Fqx "legacy-native-config-saved=$ID" "$ROOT/retired-response.txt" ||
    fail "legacy native Config saved witness missing"
reset; BAD_OWNER=1
run_retired 69 ''
reset; REHYDRATE_RC=69
run_retired 70 'bundle:verify runtime-rehydrate '
reset; SAVE_RC=70
run_retired 70 'bundle:verify runtime-rehydrate runtime-attest config-save '
reset; SAVED_DIGEST_DRIFT=1
run_retired 70 'bundle:verify runtime-rehydrate runtime-attest config-save config-readback '
reset; ATTEST_FAIL_AT=2
run_retired 70 'bundle:verify runtime-rehydrate runtime-attest config-save config-readback bundle:verify runtime-attest '
echo 'PASS: shared FD9 native runtime/Config fault-injection matrix'
