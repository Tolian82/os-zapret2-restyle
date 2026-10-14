#!/bin/sh
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/shared-saved.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
sed -n '/^shared_apply_recover_saved_service()$/,/^}$/p' "$SOURCE" > "$ROOT/recover.sh"
sh -n "$ROOT/recover.sh" || fail "source syntax"
. "$ROOT/recover.sh"
ID=dddddddddddddddddddddddddddddddd
mkdir -p "$ROOT/work/release"
LOG="$ROOT/steps.log"
CHILD_PIDFILE="$ROOT/child.pid"
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
preflight_voice_cutover_journals() { echo "guard:$1" >> "$LOG"; [ "$GUARD" = 0 ]; }
shared_apply_bundle_service() { echo "seal:$1" >> "$LOG"; [ "$SEAL" = 0 ]; }
shared_apply_native_config() {
    echo "config:$1" >> "$LOG"
    [ "$CONFIG" = 0 ] || return 69
    n=$(grep -c '^config:saved$' "$LOG")
    if [ "$n" -gt 1 ]; then
        [ "$POST_CONFIG" = 0 ] || return 69
        if [ "$POST_DIGEST" = 1 ]; then
            echo '{"result":"committed","enabled":"1","snapshot":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}'
            return
        fi
        if [ "$POST_MODE" = 1 ]; then
            echo '{"result":"committed","enabled":"0","snapshot":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}'
            return
        fi
    fi
    echo '{"result":"committed","enabled":"1","snapshot":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}'
}
shared_apply_json_field() {
    json=$(cat)
    case "$1" in
        *".enabled"*) case "$json" in *'"enabled":"0"'*) echo 0 ;; *) echo 1 ;; esac ;;
        *".result"*) echo committed ;;
        *".snapshot"*)
            case "$json" in
                *'"snapshot":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"'*) printf '%064d\n' 0 | tr 0 c ;;
                *) printf '%064d\n' 0 | tr 0 b ;;
            esac ;;
        *) return 1 ;;
    esac
}
shared_apply_workspace() { echo "$ROOT/work"; }
launcher_is_running() { echo launcher-check >> "$LOG"; [ "$ENGINE" = 1 ]; }
supervisor_is_running() { echo supervisor-check >> "$LOG"; [ "$MONITOR" = 1 ]; }
firewall_shared_runtime() { echo "ipfw:$1" >> "$LOG"; [ "$KERNEL" = 0 ]; }
apply_runtime_activate() {
    echo activate >> "$LOG"
    [ "$#" -eq 3 ] && [ "$3" = "$ID" ] && [ "$ACTIVATE" = 0 ]
}
apply_runtime_attest_activated() {
    echo attest >> "$LOG"
    n=$(grep -c '^attest$' "$LOG")
    [ "$ATTEST_PRE" = 0 ] &&
    { [ "$ATTEST_POST" = 0 ] || [ "$n" -eq 1 ]; }
}
apply_runtime_commit() { echo commit >> "$LOG"; [ "$COMMIT" = 0 ]; }
# Built-in worker is root-only: mock fixed binary by substituting a function
# for the extracted shell executor variable and keeping terminal guard.
BACKEND_DIR="$ROOT/backend"
mkdir -p "$BACKEND_DIR"
cat > "$BACKEND_DIR/shared_apply_operation.py" <<'PY'
# mock only
PY
reset() {
    GUARD=0; SEAL=0; CONFIG=0; ENGINE=0; MONITOR=0
    KERNEL=0; ACTIVATE=0; COMMIT=0; POST_CONFIG=0; POST_DIGEST=0
    POST_MODE=0; ATTEST_PRE=0; ATTEST_POST=0; : > "$LOG"
}
check() {
    expected="$1"; shift
    set +e
    shared_apply_recover_saved_service "config-saved $ID voice" > "$ROOT/output"
    status=$?
    set -e
    [ "$status" = "$expected" ] || fail "return $status expected $expected"
    steps=$(tr "\n" " " < "$LOG")
    [ "$steps" = "$*" ] || fail "steps $steps"
}
# Never execute privileged production interpreter in the regression:
# extract and replace only the final fixed CLI call with a deterministic mock.
python3 - "$ROOT/recover.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
old='    /usr/local/bin/python3.13 "${BACKEND_DIR}/shared_apply_operation.py" \\\n        finish-saved "$_shared_saved_id" || return 70'
assert old in s
s=s.replace(old,'    echo finish-saved >> "$LOG"; [ "$FINISH" = 0 ] || return 70')
# The real executable is a fixed FreeBSD dependency; the Linux fault-test
# replaces its final invocation and therefore bypasses only that presence
# check, never the pre-save owner, kernel or Config guards.
presence='    [ -x /usr/local/bin/python3.13 ] || return 70'
assert presence in s
s=s.replace(presence,'    : # root Python CLI is mocked below')
p.write_text(s)
PY
. "$ROOT/recover.sh"
FINISH=0; reset
check 0 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest config:saved attest commit finish-saved '
grep -Fqx "recovered-saved-id=$ID" "$ROOT/output" || fail "recovery receipt missing"
reset; GUARD=1
check 69 'guard:common-recover-saved '
reset; SEAL=1
check 69 'guard:common-recover-saved seal:verify '
reset; CONFIG=1
check 69 'guard:common-recover-saved seal:verify config:saved '
reset; ENGINE=1
check 69 'guard:common-recover-saved seal:verify config:saved launcher-check '
reset; MONITOR=1
check 69 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check '
reset; KERNEL=1
check 69 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify '
reset; ACTIVATE=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate '
reset; COMMIT=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest config:saved attest commit '
reset; POST_CONFIG=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest config:saved '
reset; POST_DIGEST=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest config:saved '
reset; POST_MODE=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest config:saved '
reset; ATTEST_PRE=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest '
reset; ATTEST_POST=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest config:saved attest '
reset; FINISH=1
check 70 'guard:common-recover-saved seal:verify config:saved launcher-check supervisor-check ipfw:verify activate seal:verify attest config:saved attest commit finish-saved '
if shared_apply_recover_saved_service "activated $ID voice"; then fail "unproven activation resumed"; fi
if shared_apply_recover_saved_service "config-saved /tmp/bad voice"; then fail "foreign operation resumed"; fi
echo 'PASS: post-save recovery only from empty kernel and saved native Config'
