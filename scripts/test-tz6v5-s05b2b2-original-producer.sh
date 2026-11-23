#!/bin/sh
# Targeted real source function contract; no synthetic engine success/rc.
set -eu
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/s05b2b2.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
RUNTIME="$SOURCE/src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh"
SERVICE="$SOURCE/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
sed -n '/^apply_runtime_abort_after_launcher_failure()$/,/^}$/p' "$RUNTIME" > "$ROOT/abort.sh"
sed -n '/^shared_apply_activate_and_commit_service()$/,/^}$/p' "$SERVICE" > "$ROOT/owner.sh"
[ -s "$ROOT/abort.sh" ] && [ -s "$ROOT/owner.sh" ] || fail "production functions absent"
sh -n "$ROOT/abort.sh" && sh -n "$ROOT/owner.sh" || fail "production shell syntax"
. "$ROOT/abort.sh"
. "$ROOT/owner.sh"

# Production helper must freeze the original stage BEFORE rollback mutates it.
apply_runtime_abort() { LAUNCHER_FAILURE_STAGE=rollback-overwrote; return 70; }
for original in no-live-pid stability-unverified; do
    LAUNCHER_FAILURE_STAGE=$original
    APPLY_EARLY_ENGINE_FAILURE=
    if apply_runtime_abort_after_launcher_failure "replacement engine failed"; then
        fail "original rollback unexpectedly succeeded"
    else
        [ "$?" -eq 70 ] || fail "original abort rc lost"
    fi
    [ "$APPLY_EARLY_ENGINE_FAILURE" = "$original" ] || fail "rollback overwrote original cause"
done
LAUNCHER_FAILURE_STAGE=not-a-launcher-failure
APPLY_EARLY_ENGINE_FAILURE=
if apply_runtime_abort_after_launcher_failure "other failure"; then fail "unexpected success"; fi
[ -z "$APPLY_EARLY_ENGINE_FAILURE" ] || fail "unsupported cause accepted"

# Exercise the actual FD9 Apply failure branch. The CLI mock is deliberately
# narrow; the Python journal writer has a separate direct real-file test.
LOG="$ROOT/ordered.log"
BACKEND_DIR="$ROOT/backend"
PYTHON_RUNTIME="$ROOT/python-cli"
ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
export BACKEND_DIR LOG ID
cat > "$PYTHON_RUNTIME" <<'MOCK'
#!/bin/sh
[ "$#" -eq 4 ] &&
[ "$1" = "$BACKEND_DIR/shared_apply_operation.py" ] &&
[ "$2" = record-early-start ] &&
[ "$3" = "$ID" ] || exit 69
case "$4" in no-live-pid|stability-unverified) ;; *) exit 69 ;; esac
printf "producer:%s\n" "$4" >> "$LOG"
MOCK
chmod 700 "$PYTHON_RUNTIME"
_shared_apply_id=$ID
_shared_apply_page=strategies
_shared_apply_base=$(printf "%064d" 0 | tr 0 b)
_shared_apply_candidate=$(printf "%064d" 0 | tr 0 c)
_shared_apply_fields=general.enabled
_shared_apply_root="$ROOT/candidate"
_shared_apply_mode=1
shared_apply_record_current_service() { printf "journal:%s\n" "$1" >> "$LOG"; }
apply_runtime_activate() { APPLY_EARLY_ENGINE_FAILURE=$STAGE; return 1; }
for STAGE in no-live-pid stability-unverified "" ; do
    : > "$LOG"
    _shared_found_scope=ordinary
    if shared_apply_activate_and_commit_service >/dev/null 2>&1; then
        fail "Apply accepted unverified engine"
    else
        [ "$?" -eq 70 ] || fail "Apply incorrectly changed failure rc"
    fi
    grep -Fxq "journal:activating" "$LOG" || fail "missing original activating"
    grep -Fxq "journal:requires-review" "$LOG" || fail "missing original requires-review"
    case "$STAGE" in
        "") ! grep -Fq producer: "$LOG" || fail "generic error invented a receipt" ;;
        *) grep -Fxq "producer:$STAGE" "$LOG" || fail "original early event not delivered" ;;
    esac
done
STAGE=stability-unverified
_shared_found_scope=found
: > "$LOG"
if shared_apply_activate_and_commit_service >/dev/null 2>&1; then fail "found accepted"; fi
! grep -Fq producer: "$LOG" || fail "found WAL bypassed by ordinary event"
echo "PASS: real original rollback captures cause; original FD9 writer only after requires-review"
