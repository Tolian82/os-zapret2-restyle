#!/bin/sh
set -eu
# Test real RUNNING schema3 preflight before generic FD9 transaction tests.
sh "$(CDPATH= cd -- "$(dirname "$0")" && pwd)/test-schema3-running-apply-preflight.sh"
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/shared-exec.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
RUNTIME=$(dirname "$SOURCE")/backend/apply_runtime.sh
sed -n '/^shared_apply_execute_service()$/,/^}$/p' "$SOURCE" > "$ROOT/executor.sh"
for entry in shared_apply_record_current_service shared_apply_activate_and_commit_service; do
    sed -n "/^$entry()$/,/^}$/p" "$SOURCE" >> "$ROOT/executor.sh"
done
sed -n '/^apply_runtime_observer_retirement_preflight()$/,/^}$/p' "$RUNTIME" >> "$ROOT/executor.sh"
sed -n '/^apply_runtime_observer_previous_preflight()$/,/^}$/p' "$RUNTIME" >> "$ROOT/executor.sh"
sh -n "$ROOT/executor.sh" || fail "shell syntax"
. "$ROOT/executor.sh"
ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
mkdir -p "$ROOT/work/release"
printf '%s\n' '{"page":"voice"}' > "$ROOT/work/plan.json"
: > "$ROOT/work/candidate.xml"
LOG="$ROOT/steps.log"
# Source-only executor test: the real service normally initializes these.
# Stub precisely the new read-only original FD9 verification child.
BACKEND_DIR="$ROOT"
PYTHON_RUNTIME="$ROOT/mock-python-runtime.sh"
FOUND_DRIFT=0
export ROOT ID LOG BACKEND_DIR FOUND_DRIFT
cat > "$PYTHON_RUNTIME" <<'MOCK'
#!/bin/sh
[ "$#" -eq 3 ] &&
[ "$1" = "$BACKEND_DIR/auto_detect_effective_known.py" ] &&
[ "$2" = verify-planned ] &&
[ "$3" = "$ID" ] || exit 69
echo found-witness >> "$LOG"
[ "$FOUND_DRIFT" = 0 ]
MOCK
chmod 700 "$PYTHON_RUNTIME"
# The production FD9 executor uses fixed PID paths. This isolated mock
# supplies disposable equivalents so the new final process check is run.
CHILD_PIDFILE="$ROOT/dvtws.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/supervisor.pid"
ACTIVE_DIR="$ROOT/active"
preflight_shared_apply_journal() { [ "$1" = common-apply ]; }
shared_apply_workspace() { echo "$ROOT/work"; }
shared_apply_inspect_service() {
    if [ "$BAD_OWNER" = 1 ]; then echo "legacy-common-activated $ID voice"
    elif [ "$COMMIT_OWNER" = 1 ]; then echo "legacy-common-committing $ID voice"
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
        preflight) [ "$CONFIG_PREFLIGHT_RC" = 0 ] || return "$CONFIG_PREFLIGHT_RC"; echo '{"snapshot":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","enabled":"1","base":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","candidate":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","fields":["voice.telegram.enabled"]}' ;;
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
        *'has("found_intent")'*)
            # Mirror the real jq predicate using ONLY this fixture plan.
            # No successful old Apply may ignore a pending found-file edit.
            plan_content=$(cat)
            case "$plan_content" in
                *'"found_intent"'*'"found_batch"'*) printf '%s\n' found ;;
                *'"found_intent"'*) printf '%s\n' invalid ;;
                *'"page"'*) printf '%s\n' ordinary ;;
                *) return 1 ;;
            esac ;;
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
                *)
                    if [ "$PRE_DRIFT" = 1 ]; then
                        printf "%064d\n" 0 | tr 0 c
                    else
                        printf "%064d\n" 0 | tr 0 b
                    fi ;;
            esac ;;
        *".fields"*) echo voice.telegram.enabled ;;
        *) return 1 ;;
    esac
}
shared_apply_record_service() {
    printf "record:%s\n" "$1" >> "$LOG"
    [ "$1" != "$BAD_RECORD" ]
}
apply_runtime_probe() {
    echo runtime-probe >> "$LOG"
    PROBE_COUNT=$((PROBE_COUNT + 1))
    [ "$PROBE_RC" -eq 0 ] &&
    { [ "$FINAL_PROBE_FAIL" -eq 0 ] || [ "$PROBE_COUNT" -ne 2 ]; }
}
atomic_verify_tree() { echo runtime-tree >> "$LOG"; [ "$FINAL_TREE_OK" -eq 1 ]; }
launcher_is_running() { [ "$FINAL_ENGINE" -eq 1 ]; }
supervisor_is_running() { [ "$FINAL_MONITOR" -eq 1 ]; }
apply_runtime_activate() { echo runtime-activate >> "$LOG"; [ "$ACTIVATE_RC" -eq 0 ] || return 1; [ "$TAMPER_DURING_ACTIVATION" = 0 ] || BAD_BUNDLE=1; }
apply_runtime_restore() { echo runtime-restore >> "$LOG"; [ "$RESTORE_RC" -eq 0 ]; }
apply_runtime_attest_activated() {
    echo runtime-attest >> "$LOG"
    ATTEST_COUNT=$((ATTEST_COUNT + 1))
    [ "$ATTEST_RC" -eq 0 ] &&
    { [ "$ATTEST_FAIL_AT" -eq 0 ] || [ "$ATTEST_FAIL_AT" -ne "$ATTEST_COUNT" ]; }
}
apply_runtime_commit() { echo runtime-commit >> "$LOG"; [ "$COMMIT_RC" -eq 0 ]; }
apply_runtime_verify_retired_legacy_committed() {
    echo runtime-final-verify >> "$LOG"
    [ "$FINAL_RC" -eq 0 ]
}
reset() { : > "$LOG"; FOUND_DRIFT=0; export FOUND_DRIFT; FINISH_FAIL=0; SAVE_RC=0; ACTIVATE_RC=0; RESTORE_RC=0; COMMIT_RC=0; BAD_RECORD=none; BAD_BUNDLE=0; TAMPER_DURING_ACTIVATION=0; PROBE_RC=0; ATTEST_RC=0; ATTEST_COUNT=0; ATTEST_FAIL_AT=0; SAVED_RC=0; SAVED_DIGEST_DRIFT=0; SAVED_MODE_DRIFT=0; BAD_OWNER=0; REHYDRATE_RC=0; PRE_DRIFT=0; CONFIG_PREFLIGHT_RC=0; COMMIT_OWNER=0; FINAL_RC=0; PROBE_COUNT=0; FINAL_PROBE_FAIL=0; FINAL_TREE_OK=1; FINAL_ENGINE=1; FINAL_MONITOR=1; _apply_engine=0; }
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
expect_status 0 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest runtime-commit bundle:verify runtime-tree runtime-probe record:committed '
grep -Fqx "applied-id=$ID" "$ROOT/response.txt" || fail "successful receipt"
# A sealed but uncommitted form intent must refuse BEFORE the original
# Prepared journal, Config::save, runtime transition and IPFW. The same
# legacy Voice Apply fixture must remain operational with no found intent.
printf '%s\n' '{"page":"voice","found_intent":{}}' > "$ROOT/work/plan.json"
reset
expect_status 0 'bundle:verify '
grep -Fqx 'preflight-rejected=found-intent' "$ROOT/response.txt" ||
    fail "found intent crossed pre-journal gate"
# Verify a post-seal minute change stays a bounded pre-journal refusal.
reset
FOUND_DRIFT=1
export FOUND_DRIFT
printf '%s\n' '{"page":"strategies","found_intent":{},"found_batch":{}}' > "$ROOT/work/plan.json"
set +e
shared_apply_execute_service "$ID" strategies > "$ROOT/response.txt"
result=$?
set -e
[ "$result" = 0 ] && [ "$(tr '\n' ' ' < "$LOG")" = 'bundle:verify found-witness ' ] ||
    fail "found drift reached native Config or runtime"
grep -Fqx 'preflight-rejected=found-source-drift' "$ROOT/response.txt" ||
    fail "late minute drift crossed pre-journal gate"
printf '%s\n' '{"invalid":' > "$ROOT/work/plan.json"
reset
expect_status 69 'bundle:verify '
[ ! -s "$ROOT/response.txt" ] || fail "corrupt found candidate crossed pre-journal gate"
printf '%s\n' '{"page":"voice"}' > "$ROOT/work/plan.json"
# The final proof is AFTER native Config + IPFW commit: neither an
# altered installed traffic/IPSET tree, nor dead engine, nor a changed
# committed rule set may produce the GUI's applied-id receipt.
reset; FINAL_TREE_OK=0
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest runtime-commit bundle:verify runtime-tree record:requires-review '
[ ! -s "$ROOT/response.txt" ] || fail "postcommit tree drift confirmed Apply"
reset; FINAL_PROBE_FAIL=1
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest runtime-commit bundle:verify runtime-tree runtime-probe record:requires-review '
reset; FINAL_ENGINE=0
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest runtime-commit bundle:verify runtime-tree runtime-probe record:requires-review '
reset; FINAL_MONITOR=0
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:config-saved config-readback runtime-attest runtime-commit bundle:verify runtime-tree runtime-probe record:requires-review '
reset; BAD_BUNDLE=1
expect_status 0 'bundle:verify '
grep -Fqx 'preflight-rejected=bundle-verify' "$ROOT/response.txt" ||
    fail "bundle refused before journal but GUI receipt was uncertain"
reset; CONFIG_PREFLIGHT_RC=69
expect_status 0 'bundle:verify '
grep -Fqx 'preflight-rejected=config-preflight' "$ROOT/response.txt" ||
    fail "Config refused before journal but GUI receipt was uncertain"
reset; SAVE_RC=69
expect_status 69 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save runtime-restore record:restored '
reset; SAVE_RC=70
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest config-save record:requires-review '
reset; TAMPER_DURING_ACTIVATION=1
expect_status 69 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-restore record:restored '
reset; ATTEST_RC=1
expect_status 70 'bundle:verify runtime-probe record:prepared record:activating runtime-activate record:activated bundle:verify runtime-attest record:requires-review '
reset; PROBE_RC=1
expect_status 0 'bundle:verify runtime-probe '
grep -Fqx 'preflight-rejected=runtime-preflight' "$ROOT/response.txt" ||
    fail "legacy runtime preflight failure did not reach GUI"
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
# Complete both ordinary and epoch scenarios before reporting PASS.

# Invalid/forged observer release cannot pass native promotion verification
# or enter the durable Apply journal. Previous tests used a zero-byte
# auto-detect-generation.json plus a fake finish-epoch helper as if this
# were a QUALIFIED original FD9 epoch; that no longer represents a valid
# candidate. Real positive generation/ACK tests run on FreeBSD in P2i.
: > "$ROOT/work/release/auto-detect-source-map.json"
reset
expect_status 0 'bundle:verify '
grep -Fqx 'preflight-rejected=observer-generation' "$ROOT/response.txt" ||
    fail "unpromoted original source map reached runtime mutation"
rm -f "$ROOT/work/release/auto-detect-source-map.json"

: > "$ROOT/work/release/auto-detect-generation.json"
# The original CLI is independently qualified by the FreeBSD witness;
# if it refuses an invalid map, the executor MUST preserve the clean
# journal and emit a non-successful GUI preflight receipt.
PYTHON_RUNTIME=/bin/false
BACKEND_DIR="$ROOT"
reset
expect_status 0 'bundle:verify '
grep -Fqx 'preflight-rejected=observer-generation' "$ROOT/response.txt" ||
    fail "invalid original epoch map reached runtime mutation"
echo 'PASS: original FD9 Apply fault matrix and unqualified observer refusal'
