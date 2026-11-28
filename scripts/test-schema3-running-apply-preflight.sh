#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
SOURCE_FILE="$HERE/../src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh"
if [ "$#" -eq 1 ]; then SOURCE_FILE="$1"; else [ "$#" -eq 0 ] || exit 64; fi
R=$(mktemp -d)
trap 'rm -rf "$R"' EXIT HUP INT TERM
sed -n '/^apply_runtime_observer_retirement_preflight()$/,/^}$/p' "$SOURCE_FILE" > "$R/check.sh"
sed -n '/^apply_runtime_observer_previous_preflight()$/,/^}$/p' "$SOURCE_FILE" >> "$R/check.sh"
sh -n "$R/check.sh"
. "$R/check.sh"
ACTIVE_DIR="$R/active"
BACKEND_DIR="$R/backend"
PYTHON_RUNTIME="$R/python.sh"
mkdir -p "$ACTIVE_DIR" "$BACKEND_DIR"
cat > "$PYTHON_RUNTIME" <<'MOCK'
#!/bin/sh
printf 'epoch:%s\n' "$2" >> "$LOG"
[ "$1" = "$BACKEND_DIR/auto_detect_minute.py" ] || exit 69
[ "$EPOCH_OK" = 1 ] || exit 69
case "$2" in
  --pre-retire) echo 'auto-detect-retire=original-learning-running-attested' ;;
  --retired-ready)
    if [ "${REQUIRE_BORROWED:-0}" = 1 ]; then
      [ "$#" -eq 3 ] && [ "$3" = --inherited-queue ] && ( : <&3 ) || exit 69
      printf '%s\n' 'borrowed-p2a' >> "$LOG"
    fi
    echo 'auto-detect-retire=ready' ;;
  *) exit 69 ;;
esac
MOCK
chmod 700 "$PYTHON_RUNTIME"
LOG="$R/log"
export LOG BACKEND_DIR EPOCH_OK
common_error() { echo "error:$*" >> "$LOG"; }
apply_runtime_observer_preflight() {
  [ "$1" = "$ACTIVE_DIR" ] || return 69
  printf 'map-preflight\n' >> "$LOG"
  [ "$PRECHECK_OK" = 1 ] || return 69
  grep -Fqx '{"schema":3}' "$ACTIVE_DIR/auto-detect-generation.json" || return 69
  grep -q -- '--hostlist-auto=' "$ACTIVE_DIR/dvtws.args" || return 69
  _apply_native_schema=3
}
pass() { if ! apply_runtime_observer_previous_preflight; then echo "FAIL: $1" >&2; exit 1; fi; }
refuse() { if apply_runtime_observer_previous_preflight; then echo "FAIL: $1" >&2; exit 1; fi; }
printf '%s\n' '--port=989 --hostlist-auto=/var/db/zapret2/native' > "$ACTIVE_DIR/dvtws.args"
printf '%s\n' '{"schema":3}' > "$ACTIVE_DIR/auto-detect-generation.json"
_apply_engine=1 PRECHECK_OK=1 EPOCH_OK=1
pass 'RUNNING, exact authenticated schema3 must pass read-only preflight'
grep -q 'map-preflight' "$LOG" || { echo 'missing map preflight'; exit 1; }
grep -q 'epoch:--pre-retire' "$LOG" || { echo 'missing original native epoch'; exit 1; }
EPOCH_OK=0; refuse 'denied running epoch'
EPOCH_OK=1; PRECHECK_OK=0; refuse 'untrusted owner map'
PRECHECK_OK=1
printf '%s\n' '{"schema":2}' > "$ACTIVE_DIR/auto-detect-generation.json"
refuse 'old schema2 cannot use schema3-only release exception'
printf '%s\n' '{"schema":3}' > "$ACTIVE_DIR/auto-detect-generation.json"
rm "$ACTIVE_DIR/auto-detect-generation.json"
refuse 'native auto with no immutable generation'
printf '%s\n' '{"schema":3}' > "$ACTIVE_DIR/auto-detect-generation.json"
_apply_engine=0; EPOCH_OK=1
pass 'STOPPED original completed epoch permitted'
REQUIRE_BORROWED=1
export REQUIRE_BORROWED
: > "$LOG"
apply_runtime_observer_previous_preflight --inherited-queue 3<"$LOG" || {
  echo 'FAIL: stopped Auto did not borrow the held queue' >&2; exit 1;
}
grep -Fqx borrowed-p2a "$LOG"
_apply_engine=1
if apply_runtime_observer_previous_preflight --inherited-queue 3<"$LOG"; then
  echo 'FAIL: borrowed-queue activation admitted a running owner' >&2; exit 1
fi
_apply_engine=0
REQUIRE_BORROWED=0
EPOCH_OK=0; refuse 'STOPPED epoch not retired'
rm "$ACTIVE_DIR/auto-detect-generation.json"
refuse 'unqualified stopped active auto'
printf '%s\n' '--port=989' > "$ACTIVE_DIR/dvtws.args"
pass 'ordinary stopped runtime remains accepted'
echo 'PASS: schema3 RUNNING Apply preflight and negative gates'
