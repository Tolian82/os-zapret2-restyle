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
[ "$TEST_BUILD_FAIL" != 2 ] || exit 69
mkdir -p "$ZAPRET_DIR/.git" "$ZAPRET_DIR/binaries/my"
printf '#!/bin/sh\nexit 0\n' > "$ZAPRET_DIR/binaries/my/dvtws2"
chmod 0755 "$ZAPRET_DIR/binaries/my/dvtws2"
# The upstream v1.0.7 Makefile creates these three internal compiler links.
mkdir -p "$ZAPRET_DIR/nfq2" "$ZAPRET_DIR/ip2net" "$ZAPRET_DIR/mdig"
for binary in ip2net mdig; do
  cp "$ZAPRET_DIR/binaries/my/dvtws2" "$ZAPRET_DIR/binaries/my/$binary"
  chmod 0755 "$ZAPRET_DIR/binaries/my/$binary"
done
ln -s ../binaries/my/dvtws2 "$ZAPRET_DIR/nfq2/dvtws2"
ln -s ../binaries/my/ip2net "$ZAPRET_DIR/ip2net/ip2net"
ln -s ../binaries/my/mdig "$ZAPRET_DIR/mdig/mdig"
if [ "${TEST_UNSAFE_LINK:-0}" = 1 ]; then
  ln -s /etc/passwd "$ZAPRET_DIR/nfq2/foreign"
fi
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
[ "${1:-}" = first-install-read-record ] && [ "$#" -eq 2 ] || exit 69
[ "${SETUP_TRANSACTION_LOCK_OWNER:-0}" = 1 ] &&
[ "${UPSTREAM_RUNTIME_LIFECYCLE_OWNER:-0}" = 1 ] &&
[ "${STRATEGY_LAB_LIFECYCLE_OWNER:-0}" = 1 ] &&
[ "${FIRST_INSTALL_ORIGINAL_PRODUCER:-0}" = 1 ] &&
( : >&9 ) 2>/dev/null || exit 75
[ "$2" = v1.0.7 ] && [ -d "$ZAPRET_DIR/.git" ] || exit 69
case "$ZAPRET_DIR" in
 "$FIRST_INSTALL_ACTIVE_ROOT"|"$FIRST_INSTALL_STAGE_ROOT/runtime") ;;
 *) exit 69 ;;
esac
hash=$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$ZAPRET_DIR/binaries/my/dvtws2") || exit 69
printf 'v1.0.7\ncommit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nengine_sha256=%s\n' "$hash"
EOF
cat > "$ROOT/configctl" <<'EOF'
#!/bin/sh
exit 69
EOF
chmod 0755 "$ROOT/service" "$ROOT/setup" "$ROOT/git" "$ROOT/extra" "$ROOT/configctl"
run() {
  TEST_BUILD_FAIL="$1" TEST_UNSAFE_LINK="${2:-0}" \
  TEST_SETUP_STATUS="$STATUS" TEST_INSTALL_CALLS="$ROOT/install.calls" \
  ZAPRET_SETUP_OPERATION_ID="${TEST_SETUP_OPERATION:-}" \
  SETUP_SCRIPT="${TEST_SETUP_SCRIPT:-$ROOT/setup}" SERVICE_SCRIPT="$ROOT/service" \
  FETCH_BIN="$ROOT/fetch-unavailable" LOCKF_BIN="$ROOT/lockf" RUN_DIR="$ROOT/run" \
  RELEASE_CACHE="$STATE/releases.cache" \
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
# Real resolver + real first-install wrapper, isolated unavailable fetch.
printf '#!/bin/sh\nexit 1\n' > "$ROOT/fetch-unavailable"
cat > "$ROOT/lockf" <<'EOF_LOCK'
#!/bin/sh
[ "$1" = -s ] && [ "$2" = -t ] || exit 75
shift 4
exec "$@"
EOF_LOCK
chmod 0755 "$ROOT/fetch-unavailable" "$ROOT/lockf"
TEST_SETUP_SCRIPT="$ROOT_DIR/src/opnsense/scripts/OPNsense/Zapret/setup.sh"
if run 0 >/dev/null 2>&1; then fail "unavailable releases accepted"; else rc=$?; fi
[ "$rc" -eq 69 ] || fail "resolver rc changed"
printf '%s\n' failed 'cause=release-list-unavailable' | cmp -s "$STATUS" - ||
  fail "actual resolver cause lost after first-install cleanup"
[ ! -e "$RUNTIME" ] && [ ! -e "$MARKER" ] && [ ! -e "$STAGE" ] && [ ! -e "$INTENT" ] ||
  fail "release-list failure leaked staged runtime"
TEST_SETUP_OPERATION=2983ba1c2983ba1c2983ba1c2983ba1c
if run 0 >/dev/null 2>&1; then fail "correlated unavailable releases accepted"; else rc=$?; fi
[ "$rc" -eq 69 ] || fail "correlated resolver rc changed"
printf '%s\n' failed 'cause=release-list-unavailable' "operation=$TEST_SETUP_OPERATION" |
  cmp -s "$STATUS" - || fail "original resolver lost the admitted operation ID"
[ ! -e "$STAGE" ] && [ ! -e "$INTENT" ] || fail "terminal record preceded first-install cleanup"
unset TEST_SETUP_OPERATION
unset TEST_SETUP_SCRIPT
if run 2 >/dev/null 2>&1; then fail "unrelated rc69 accepted"; fi
[ "$(cat "$STATUS")" = failed ] || fail "unrelated rc69 inherited stale cause"
run 0 || fail "clean setup failed"
expected_record() {
  hash=$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$RUNTIME/binaries/my/dvtws2") || fail "no binary hash"
  printf 'v1.0.7\ncommit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nengine_sha256=%s\n' "$hash"
}
expected_record | cmp -s "$MARKER" - || fail "first make did not bind exact original marker"
[ "$(cat "$STATUS")" = ready ] || fail "not ready"
[ -x "$RUNTIME/binaries/my/dvtws2" ] || fail "binary not published"
[ -L "$RUNTIME/nfq2/dvtws2" ] &&
[ "$(readlink "$RUNTIME/nfq2/dvtws2")" = "../binaries/my/dvtws2" ] ||
  fail "expected upstream compiler link was not preserved"
[ ! -e "$STAGE" ] && [ ! -e "$INTENT" ] || fail "stage not cleaned"
[ ! -e "$STATE/runtime-rollback" ] || fail "unexpected old rollback"
# An original sealed built intent can resume after the root rename, but
# metadata alone must never be promoted after a changed binary.
printf 'version=v1.0.7\noriginal=0\nstate=built\n' > "$INTENT"
expected_record | sed -n '2,3p' >> "$INTENT"
before=$(wc -l < "$ROOT/install.calls")
run 0 || fail "original built-intent post-publication recovery failed"
expected_record | cmp -s "$MARKER" - || fail "recovery lost original build digest"
[ "$(wc -l < "$ROOT/install.calls")" -eq "$before" ] ||
  fail "bound recovery spuriously rebuilt"
# Crash after make proof, before moving the staged runtime.
rm -f "$MARKER"
mkdir -m 0700 "$STAGE"
mv "$RUNTIME" "$STAGE/runtime"
printf 'version=v1.0.7\noriginal=0\nstate=built\n' > "$INTENT"
hash=$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$STAGE/runtime/binaries/my/dvtws2")
printf 'commit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nengine_sha256=%s\n' "$hash" >> "$INTENT"
before=$(wc -l < "$ROOT/install.calls")
run 0 || fail "sealed staged make could not resume"
expected_record | cmp -s "$MARKER" - || fail "staged recovery did not bind record"
[ "$(wc -l < "$ROOT/install.calls")" -eq "$before" ] || fail "staged recovery rebuilt"
# Digest substitution with a valid tag and executable must refuse, not
# silently publish or delete the original staged tree.
mv "$RUNTIME" "$STAGE/runtime" 2>/dev/null || {
  mkdir -m 0700 "$STAGE"
  mv "$RUNTIME" "$STAGE/runtime"
}
rm -f "$MARKER"
printf 'version=v1.0.7\noriginal=0\nstate=built\n' > "$INTENT"
printf 'commit=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nengine_sha256=%064d\n' 0 >> "$INTENT"
if run 0 >/dev/null 2>&1; then fail "mismatched built digest accepted"; fi
[ ! -e "$MARKER" ] && [ -d "$STAGE/runtime" ] && [ -f "$INTENT" ] ||
  fail "tamper refusal mutated first-install state"
# Disposable fixture reset after intentional foreign evidence refusal.
rm -rf "$STAGE"
rm -f "$INTENT"
run 0 || fail "post-tamper clean retry failed"
# Simulate legacy pre-make crash after atomic promotion: no saved proof.

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

# A staging symlink to an external path is not a valid compiler link.
rm -rf "$RUNTIME"
rm -f "$MARKER"
if run 0 1 >/dev/null 2>&1; then fail "external stage symlink accepted"; fi
[ ! -e "$RUNTIME" ] && [ -L "$STAGE/runtime/nfq2/foreign" ] ||
  fail "unsafe staged checkout was published or overwritten"
# These are disposable test-fixture files only. Production preserves uncertain
# foreign state for inspection rather than deleting it.
rm -rf "$STAGE"
rm -f "$INTENT"

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
