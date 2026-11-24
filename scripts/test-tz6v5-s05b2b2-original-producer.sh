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
sed -n '/^shared_apply_unbound_root_preflight_service()$/,/^}$/p' "$SERVICE" > "$ROOT/owner.sh"
sed -n '/^shared_apply_activate_and_commit_service()$/,/^}$/p' "$SERVICE" >> "$ROOT/owner.sh"
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
# The actual original owner has this sealed shared-work/release layout.
# Extracting an owner function without its required native directory is
# no longer a valid production-fault fixture after S10b2a's safety gate.
mkdir -p "$_shared_apply_root/release"
_shared_apply_mode=1
shared_apply_record_current_service() { printf "journal:%s\n" "$1" >> "$LOG"; }
apply_runtime_activate() { APPLY_EARLY_ENGINE_FAILURE=$STAGE; APPLY_IPFW_ATTACH_FAILURE=; return 1; }
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
# Original FD9 must emit no IPFW reason without a successful journal write.
cat > "$PYTHON_RUNTIME" <<'MOCK_IPFW'
#!/bin/sh
[ "$#" -eq 4 ] && [ "$1" = "$BACKEND_DIR/shared_apply_operation.py" ] &&
[ "$2" = record-ipfw-attach ] && [ "$3" = "$ID" ] &&
[ "$4" = rule-add-rejected ] || exit 69
printf 'producer:%s\n' "$4" >> "$LOG"
MOCK_IPFW
chmod 700 "$PYTHON_RUNTIME"
apply_runtime_activate() {
    APPLY_EARLY_ENGINE_FAILURE=
    APPLY_IPFW_ATTACH_FAILURE=$IPFW_CAUSE
    return 1
}
for _shared_found_scope in ordinary found; do
    for IPFW_CAUSE in rule-add-rejected unknown ""; do
        : > "$LOG"
        if _ipfw_stdout=$(shared_apply_activate_and_commit_service 2>/dev/null); then
            fail "unexpected IPFW Apply success"
        else
            [ "$?" -eq 70 ] || fail "FD9 refused with wrong rc"
        fi
        case "$_shared_found_scope:$IPFW_CAUSE" in
            ordinary:rule-add-rejected)
                [ "$_ipfw_stdout" = 'ipfw-attach-failure=rule-add-rejected' ] ||
                    fail "verified native marker not forwarded"
                grep -Fxq producer:rule-add-rejected "$LOG" || fail "original journal writer missed" ;;
            *)
                [ -z "$_ipfw_stdout" ] || fail "unqualified output surfaced"
                ! grep -Fq producer: "$LOG" || fail "found/unknown cause persisted" ;;
        esac
    done
done
echo "PASS: original FD9 IPFW cause emitted only after qualified ordinary journal"
