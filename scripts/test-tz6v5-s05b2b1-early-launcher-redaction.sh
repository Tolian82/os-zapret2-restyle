#!/bin/sh
# Exercise the actual production launcher_start_once on both failed-start paths.
set -eu
SOURCE="$PWD/src/opnsense/scripts/OPNsense/Zapret/backend/launcher.sh"
if [ "$#" -gt 0 ]; then SOURCE=$1; fi
ROOT=$(mktemp -d "/tmp/s05b2b1-launcher.XXXXXXXX") || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }

cat > "$ROOT/mock-daemon" <<'MOCK'
#!/bin/sh
while [ "$#" -gt 0 ]; do
    if [ "$1" = -o ]; then
        shift
        log="$1"
    fi
    shift
done
# daemon(8) redirects dvtws2 output into this potentially sensitive log.
printf '%s\n' 'PRIVATE_DOMAIN=secret.example' 'PRIVATE_TOKEN=anothersecret' > "$log"
MOCK
cat > "$ROOT/mock-engine" <<'MOCK'
#!/bin/sh
exit 0
MOCK
chmod 700 "$ROOT/mock-daemon" "$ROOT/mock-engine"
printf '%s\n' '--filter-tcp=443' > "$ROOT/args"

for MODE in missing stable; do
    (
        . "$SOURCE"
        LAUNCHER_DAEMON_BIN="$ROOT/mock-daemon"
        common_require_file() { [ -f "$1" ]; }
        common_error() { printf 'ERROR: %s\n' "$*" >&2; }
        launcher_stop() { :; }  # no physical engine in this fixture
        calls=0
        launcher_is_running() {
            calls=$((calls + 1))
            if [ "$MODE" = stable ] && [ "$calls" -le 2 ]; then
                return 0
            fi
            return 1
        }
        sleep() { :; }  # accelerate the existing 10 readiness polls
        launcher_start_once "$ROOT/mock-engine" "$ROOT/args" \
            "$ROOT/child.pid" "$ROOT/engine.log" 1
    ) > "$ROOT/out-$MODE" 2>&1 && fail "$MODE accepted engine without verified readiness"
    case "$MODE" in
        missing) grep -Fq 'dvtws2 did not create a live PID' "$ROOT/out-$MODE" || fail 'missing fixed reason' ;;
        stable) grep -Fq 'dvtws2 exited during startup stability window' "$ROOT/out-$MODE" || fail 'missing fixed reason' ;;
    esac
    if grep -Eq 'PRIVATE_DOMAIN|PRIVATE_TOKEN|secret\.example|anothersecret' "$ROOT/out-$MODE"; then
        fail "$MODE leaked raw dvtws2 log via real launcher"
    fi
    grep -Fq 'PRIVATE_DOMAIN=secret.example' "$ROOT/engine.log" || fail 'fixture did not create native log'
done
printf '%s\n' 'PASS: both real launcher early failure branches hide raw engine log and preserve fixed errors'
