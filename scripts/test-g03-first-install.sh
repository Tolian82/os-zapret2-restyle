#!/bin/sh
# G03 source transaction tests. Disposable fixtures, no live firewall access.
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TRANSACTION="$ROOT_DIR/src/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh"
ROOT=$(mktemp -d "/tmp/zapret-g03-first.XXXXXXXX")
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
RUNTIME="$ROOT/runtime"
STATE="$ROOT/state"
STATUS="$STATE/setup.status"
MARKER="$STATE/runtime.release"
STAGE="$RUNTIME.first-install"
INTENT="$STATE/first-install.intent"
mkdir -p "$STATE"
fail() { echo "FAIL G03: $*" >&2; exit 1; }
cat > "$ROOT/service" <<'EOF'
#!/bin/sh
case "$1" in
  strategy-lab-status|status) exit 1 ;;
  *) echo "unexpected service mutation" >&2; exit 70 ;;
esac
EOF
cat > "$ROOT/setup" <<'EOF'
#!/bin/sh
[ "$1" = install-under-parent-lock ] && [ "$2" = v1.0.7 ] || exit 65
[ "$SETUP_TRANSACTION_LOCK_OWNER" = 1 ] || exit 75
[ "$UPSTREAM_RUNTIME_LIFECYCLE_OWNER" = 1 ] || exit 75
[ "$STRATEGY_LAB_LIFECYCLE_OWNER" = 1 ] || exit 75
printf '%s\n' setup >> "$TEST_INSTALL_CALLS"
mkdir -p "$ZAPRET_DIR/.git" "$ZAPRET_DIR/binaries/my"
printf '#!/bin/sh\nexit 0\n' > "$ZAPRET_DIR/binaries/my/dvtws2"
chmod 0755 "$ZAPRET_DIR/binaries/my/dvtws2"
[ "$TEST_BUILD_FAIL" != 1 ] || exit 77
printf '%s\n' ready > "$TEST_SETUP_STATUS"
EOF
cat > "$ROOT/git" <<'EOF'
#!/bin/sh
[ "$1" = -C ] && [ -d "$2/.git" ] || exit 69
case "$3" in
  describe) printf '%s\n' v1.0.7 ;;
  rev-parse) printf '%s\n' aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa ;;
  *) exit 69 ;;
esac
EOF
cat > "$ROOT/extra" <<'EOF'
#!/bin/sh
# Old-runtime rollback is tested independently by test-setup-runtime-transaction.
exit 69
EOF
cat > "$ROOT/configctl" <<'EOF'
#!/bin/sh
exit 69
EOF
chmod 0755 "$ROOT/service" "$ROOT/setup" "$ROOT/git" "$ROOT/extra" "$ROOT/configctl"
run() {
  TEST_BUILD_FAIL="$1" \
  TEST_SETUP_STATUS="$STATUS" TEST_INSTALL_CALLS="$ROOT/install.calls" \
  SETUP_SCRIPT="$ROOT/setup" SERVICE_SCRIPT="$ROOT/service" \
  CONFIGCTL="$ROOT/configctl" GIT_BIN="$ROOT/git" \
  ZAPRET_DIR="$RUNTIME" STATE_DIR="$STATE" \
  SETUP_STATUS="$STATUS" ACTIVE_RELEASE_FILE="$MARKER" \
  ROLLBACK_DIR="$STATE/runtime-rollback" \
  FIND_BIN="$(command -v find)" EXTRA_PYTHON="$(command -v sh)" \
  EXTRA_GUARD="$ROOT/extra" \
  SETUP_TRANSACTION_LOCK_OWNER=1 UPSTREAM_RUNTIME_LIFECYCLE_OWNER=1 \
  STRATEGY_LAB_LIFECYCLE_OWNER=1 \
  sh "$TRANSACTION" install-under-native-lock v1.0.7 9>"$ROOT/fd9"
}
run 0 || fail "clean setup failed"
[ "$(cat "$MARKER")" = v1.0.7 ] || fail "no release marker"
[ "$(cat "$STATUS")" = ready ] || fail "not ready"
[ -x "$RUNTIME/binaries/my/dvtws2" ] || fail "binary not published"
[ ! -e "$STAGE" ] && [ ! -e "$INTENT" ] || fail "stage not cleaned"
[ ! -e "$STATE/runtime-rollback" ] || fail "unexpected old rollback"
# Simulate crash after atomic promotion but before marker finalization.
rm -f "$MARKER"
printf 'version=v1.0.7\noriginal=0\n' > "$INTENT"
before=$(wc -l < "$ROOT/install.calls")
run 0 || fail "post-promotion recovery failed"
[ "$(wc -l < "$ROOT/install.calls")" -eq "$before" ] || fail "recovery rebuilt"
[ "$(cat "$MARKER")" = v1.0.7 ] && [ ! -e "$INTENT" ] ||
  fail "post-promotion marker incomplete"
# Compilation failure must not leave runtime; retry must work.
rm -rf "$RUNTIME"
rm -f "$MARKER" "$STATUS"
if run 1 >/dev/null 2>&1; then fail "build failure reported success"; fi
[ ! -e "$RUNTIME" ] && [ ! -e "$STAGE" ] && [ ! -e "$INTENT" ] ||
  fail "failed build left runtime artifacts"
[ "$(cat "$STATUS")" = failed ] || fail "failure not reported"
run 0 || fail "clean retry after failed build did not install"
# Simulate SIGKILL during staged checkout and retry.
rm -rf "$RUNTIME"
rm -f "$MARKER"
printf 'version=v1.0.7\noriginal=0\n' > "$INTENT"
mkdir -p "$STAGE/runtime"
printf '%s\n' partial > "$STAGE/runtime/unfinished"
run 0 || fail "interrupted staged checkout could not retry"
[ ! -e "$STAGE" ] && [ ! -e "$INTENT" ] || fail "interrupted stage leaked"
# A normal stock OPNsense package has already rendered zapret.conf and
# hostlists into the upstream path. They must survive source installation.
rm -rf "$RUNTIME"
rm -f "$MARKER"
mkdir -p "$RUNTIME"
printf '%s\n' USER_CONFIG > "$RUNTIME/zapret.conf"
printf '%s\n' user.example > "$RUNTIME/hostlist.txt"
printf '%s\n' exempt.example > "$RUNTIME/hostlist-exclude.txt"
run 0 || fail "stock configd templates blocked clean first setup"
[ "$(cat "$RUNTIME/zapret.conf")" = USER_CONFIG ] ||
  fail "stock generated zapret.conf overwritten"
[ "$(cat "$RUNTIME/hostlist.txt")" = user.example ] ||
  fail "stock hostlist overwritten"
[ "$(cat "$RUNTIME/hostlist-exclude.txt")" = exempt.example ] ||
  fail "stock exclusion overwritten"
[ ! -e "$STAGE" ] && [ ! -e "$INTENT" ] ||
  fail "stock templates left first-install staging residue"

# A worker cut between backing up stock config and staging promotion must
# restore exact originals before starting any new build.
rm -rf "$RUNTIME"
rm -f "$MARKER"
printf 'version=v1.0.7\noriginal=1\n' > "$INTENT"
mkdir -p "$STAGE/original" "$STAGE/runtime"
printf '%s\n' USER_CONFIG > "$STAGE/original/zapret.conf"
printf '%s\n' user.example > "$STAGE/original/hostlist.txt"
printf '%s\n' exempt.example > "$STAGE/original/hostlist-exclude.txt"
printf '%s\n' partial > "$STAGE/runtime/unfinished"
run 0 || fail "interrupted stock-template promotion could not recover"
[ "$(cat "$RUNTIME/zapret.conf")" = USER_CONFIG ] &&
[ "$(cat "$RUNTIME/hostlist.txt")" = user.example ] &&
[ "$(cat "$RUNTIME/hostlist-exclude.txt")" = exempt.example ] ||
  fail "interrupted stock-template promotion lost original bytes"

# A crash after promoting a compiled runtime but before commit must verify
# the preserved original config before it can finalize the new marker.
rm -f "$MARKER"
printf 'version=v1.0.7\noriginal=1\n' > "$INTENT"
mkdir -p "$STAGE/original"
cp "$RUNTIME/zapret.conf" "$STAGE/original/zapret.conf"
cp "$RUNTIME/hostlist.txt" "$STAGE/original/hostlist.txt"
cp "$RUNTIME/hostlist-exclude.txt" "$STAGE/original/hostlist-exclude.txt"
before=$(wc -l < "$ROOT/install.calls")
run 0 || fail "interrupted original-template confirmation could not finish"
[ "$(wc -l < "$ROOT/install.calls")" -eq "$before" ] ||
  fail "post-promotion confirmation rebuilt upstream"
[ ! -e "$INTENT" ] && [ ! -e "$STAGE" ] &&
[ "$(cat "$MARKER")" = v1.0.7 ] ||
  fail "post-promotion original-template stage not completed"

# An unrelated file in the fresh directory is not a stock template.
rm -rf "$RUNTIME"
rm -f "$MARKER"
mkdir -p "$RUNTIME"
printf '%s\n' keep > "$RUNTIME/foreign-user-lua"
if run 0 >/dev/null 2>&1; then fail "foreign directory content accepted"; fi
[ "$(cat "$RUNTIME/foreign-user-lua")" = keep ] ||
  fail "foreign directory content removed"
rm -rf "$RUNTIME"

# Existing foreign runtime and linked stage must fail before deletion.
rm -rf "$RUNTIME"
rm -f "$MARKER"
printf '%s\n' foreign > "$RUNTIME"
if run 0 >/dev/null 2>&1; then fail "foreign runtime accepted"; fi
[ "$(cat "$RUNTIME")" = foreign ] || fail "foreign runtime modified"
rm -f "$RUNTIME"
mkdir -p "$ROOT/foreign"
printf '%s\n' KEEP > "$ROOT/foreign/sentinel"
ln -s "$ROOT/foreign" "$STAGE"
if run 0 >/dev/null 2>&1; then fail "foreign stage symlink accepted"; fi
[ "$(cat "$ROOT/foreign/sentinel")" = KEEP ] || fail "foreign symlink target modified"
[ -L "$STAGE" ] || fail "foreign symlink removed"
rm "$STAGE"
mkdir -p "$STATE/extra-resources"
printf '%s\n' '{}' > "$STATE/extra-resources/installed.json"
if run 0 >/dev/null 2>&1; then fail "orphan managed resources accepted"; fi
[ -f "$STATE/extra-resources/installed.json" ] || fail "managed state deleted"
echo "PASS: G03 first setup, FD9, failed build, retries, staged recovery and foreign refusal"
