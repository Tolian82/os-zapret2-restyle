#!/bin/sh
# #1052 P2k8i: original FD9 common launcher, default safe/no observer.
set -eu
TOP=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$TOP/src/opnsense/scripts/OPNsense/Zapret/backend/apply_runtime.sh"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT TERM
ACTIVE_DIR="$TEMP_DIR/release"
mkdir -p "$ACTIVE_DIR"
EVENTS="$TEMP_DIR/events"
CHILD_PIDFILE="$TEMP_DIR/child.pid"
DVTWS_BIN=/usr/local/sbin/dvtws2
DVTWS_LOG="$TEMP_DIR/dvtws.log"
BACKUP_ROOT="$TEMP_DIR/backup"
SUPERVISOR_LOOP=/bin/true
SUPERVISOR_DAEMON_PIDFILE="$TEMP_DIR/supervisor-daemon.pid"
SUPERVISOR_MONITOR_PIDFILE="$TEMP_DIR/supervisor-monitor.pid"
SERVICE_SCRIPT=/bin/true
SUPERVISOR_LOG="$TEMP_DIR/supervisor.log"
PYTHON_RUNTIME=/bin/false
BACKEND_DIR="$TEMP_DIR/not-used-backend"
printf '%s\n' '--port=989' '--hostlist=/usr/local/etc/zapret2/ipset/auto-domains.txt' > "$ACTIVE_DIR/dvtws.args"
: > "$EVENTS"

fail()
{
    printf '%s\n' "P2K8I_FAILURE=$1" >&2
    exit 1
}
common_error() { :; }
common_pidfile_read() { printf '123\n'; }
launcher_start_once() { printf 'launch\n' >> "$EVENTS"; return 0; }
launcher_stop() { printf 'stop\n' >> "$EVENTS"; return 0; }
supervisor_start() { printf 'supervisor\n' >> "$EVENTS"; return 0; }
atomic_install_tree() { printf '%s\n' "$TEMP_DIR/old-tree"; }
firewall_shared_runtime()
{
    printf 'firewall:%s\n' "$1" >> "$EVENTS"
    return 0
}
apply_runtime_preflight()
{
    [ "$#" -eq 2 ] || return 64
    APPLY_CANDIDATE="$1"
    APPLY_NEW_RUNNING="$2"
    APPLY_OLD_RUNNING=0
    APPLY_PHASE=prepared
    APPLY_BACKUP=
    APPLY_OLD=-
    APPLY_NEW=-
    APPLY_IPFW_INSTALLED=0
}
apply_runtime_observer_preflight "$ACTIVE_DIR" ||
    fail "UNMODIFIED_EXPLICIT_HOSTLIST_REFUSED"
apply_runtime_activate "$ACTIVE_DIR" 1 ||
    fail "ORDINARY_SHARED_ACTIVATE_FAILED"
observed=$(cat "$EVENTS")
expected=$(printf 'launch\nfirewall:install\nfirewall:verify-staged\nsupervisor')
[ "$observed" = "$expected" ] ||
    fail "SINGLE_LAUNCH_BEFORE_IPFW_ORDER_CHANGED"
printf 'P2K8I_ORIGINAL_SHARED_NO_OBSERVER=PASS\n'

: > "$EVENTS"
printf '%s\n' '--port=989' '--filter-tcp=443' \
    '--hostlist-auto=/var/db/zapret2-auto-detect/inbox.txt' > "$ACTIVE_DIR/dvtws.args"
if apply_runtime_observer_preflight "$ACTIVE_DIR"; then
    fail "UNAUTHORIZED_NATIVE_OBSERVER_ACCEPTED"
fi
if apply_runtime_original_launcher_once "$DVTWS_BIN" \
   "$ACTIVE_DIR/dvtws.args" "$CHILD_PIDFILE" "$TEMP_DIR/log" 5; then
    fail "UNAUTHORIZED_NATIVE_OBSERVER_STARTED"
fi
[ ! -s "$EVENTS" ] || fail "UNAUTHORIZED_OBSERVER_STARTED_ENGINE"
printf 'P2K8I_MISSING_GENERATION_REFUSED_BEFORE_ENGINE=PASS\n'

# The debug-only native flag is also an unauthorized producer knob: it
# must never be accepted just because the raw hostlist flag is absent.
printf '%s\n' '--port=989' \
    '--hostlist-auto-debug=/var/db/zapret2-auto-detect/debug.log' > "$ACTIVE_DIR/dvtws.args"
if apply_runtime_observer_preflight "$ACTIVE_DIR"; then
    fail "UNAUTHORIZED_AUTO_DEBUG_WITHOUT_RAW_ACCEPTED"
fi
[ ! -s "$EVENTS" ] || fail "DEBUG_ONLY_STARTED_ENGINE"
printf 'P2K8I_DEBUG_ONLY_REFUSED_BEFORE_ENGINE=PASS\n'

printf '%s\n' '--port=989' \
    '--hostlist-auto=/var/db/zapret2-auto-detect/inbox.txt' > "$ACTIVE_DIR/dvtws.args"
printf '{}\n' > "$ACTIVE_DIR/auto-detect-generation.json"
if apply_runtime_observer_preflight "$ACTIVE_DIR"; then
    fail "FORGED_GENERATION_BYPASSED_DURABLE_WORKER"
fi
[ ! -s "$EVENTS" ] || fail "FORGED_GENERATION_STARTED_ENGINE"
printf 'P2K8I_FORGED_GENERATION_REFUSED_BEFORE_ENGINE=PASS\n'

printf '%s\n' '--port=989' '--hostlist=/usr/local/etc/zapret2/ipset/auto-domains.txt' > "$ACTIVE_DIR/dvtws.args"
if apply_runtime_observer_preflight "$ACTIVE_DIR"; then
    fail "ORPHAN_GENERATION_ACCEPTED_WITHOUT_NATIVE_ARG"
fi
rm -f "$ACTIVE_DIR/auto-detect-generation.json"
ln -s /dev/null "$ACTIVE_DIR/auto-detect-generation.json"
if apply_runtime_observer_preflight "$ACTIVE_DIR"; then
    fail "SYMLINKED_ACTIVE_GENERATION_ACCEPTED"
fi
rm -f "$ACTIVE_DIR/auto-detect-generation.json"
printf 'P2K8I_ORPHAN_OR_SYMLINKED_GENERATION_REFUSED=PASS\n'
printf 'P2K8I_SCOPE=ORIGINAL_SHARED_LAUNCHER_FAIL_CLOSED_NO_ACTIVE_OBSERVER\n'
