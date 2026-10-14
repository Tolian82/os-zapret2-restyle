#!/bin/sh
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/shared-exec.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^shared_apply_execute_service()$/,/^}$/p' "$SOURCE" > "$ROOT/executor.sh"
sh -n "$ROOT/executor.sh" || fail "shell syntax"
. "$ROOT/executor.sh"
ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
mkdir -p "$ROOT/work/release"
: > "$ROOT/work/plan.json"
: > "$ROOT/work/candidate.xml"
LOG="$ROOT/steps.log"
preflight_voice_cutover_journals() { [ "$1" = common-apply ]; }
shared_apply_workspace() { echo "$ROOT/work"; }
shared_apply_require_tools() { return 0; }
shared_apply_bundle_service() { printf "bundle:%s\n" "$1" >> "$LOG"; [ "$1" != verify ] || [ "$BAD_BUNDLE" = 0 ]; }
shared_apply_native_config() {
    case "$1" in
        preflight) echo '{"enabled":"1","base":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","candidate":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","fields":["voice.telegram.enabled"]}' ;;
        save) echo config-save >> "$LOG"; return "$SAVE_RC" ;;
        *) return 1 ;;
    esac
}
shared_apply_json_field() {
    case "$1" in
        *".enabled"*) echo 1 ;;
        *".base"*) printf "%064d\n" 0 | tr 0 a ;;
        *".candidate"*) printf "%064d\n" 0 | tr 0 b ;;
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
apply_runtime_attest_activated() { echo runtime-attest >> "$LOG"; [ "$ATTEST_RC" -eq 0 ]; }
apply_runtime_commit() { echo runtime-commit >> "$LOG"; [ "$COMMIT_RC" -eq 0 ]; }
reset() { : > "$LOG"; SAVE_RC=0; ACTIVATE_RC=0; RESTORE_RC=0; COMMIT_RC=0; BAD_RECORD=none; BAD_BUNDLE=0; TAMPER_DURING_ACTIVATION=0; PROBE_RC=0; ATTEST_RC=0; }
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
expect_status 0 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved runtime-commit record:committed '
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
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved runtime-commit record:requires-review '
reset; BAD_RECORD=activated
expect_status 69 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated runtime-restore record:restored '
reset; BAD_RECORD=config-saved
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved '
reset; RESTORE_RC=1; SAVE_RC=69
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save runtime-restore record:requires-review '
echo 'PASS: shared FD9 native runtime/Config fault-injection matrix'
