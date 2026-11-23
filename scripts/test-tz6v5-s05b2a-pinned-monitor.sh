#!/bin/sh
# S05b2a: the ORIGINAL monitor is the only physical late-exit PID witness.
# Test exact pinned argv, process birth and original -p PIDfile agreement.
set -eu
ROOT=$(mktemp -d /tmp/zapret-s05b2a-supervisor.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "S05B2A_FAIL:$*" >&2; exit 1; }
SERVICE="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
sed -n '/^shared_apply_callback_monitor_service()$/,/^}$/p' "$SERVICE" > "$ROOT/verify.sh"
sh -n "$ROOT/verify.sh" || fail syntax
. "$ROOT/verify.sh"
SUPERVISOR_LOOP=/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh
CHILD_PIDFILE=/var/run/dvtws2.pid
SERVICE_SCRIPT=/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
DVTWS_BIN=/usr/local/etc/zapret2/binaries/my/dvtws2
SUPERVISOR_MONITOR_PIDFILE="$ROOT/monitor.pid"
printf '%s\n' 777 > "$SUPERVISOR_MONITOR_PIDFILE"
supervisor_pidfile_read() { sed -n '1p' "$1"; }
common_process_matches() { [ "$1" = 777 ] && [ "$2" = "$SUPERVISOR_LOOP" ] && [ "${MOCK_RUNNING:-1}" = 1 ]; }
cat > "$ROOT/ps" <<'SHELL'
#!/bin/sh
[ "$1" = -p ] && [ "$2" = 777 ] || exit 1
[ "$3" = -o ] && [ "$4" = lstart= ] && [ "$5" = -o ] && [ "$6" = command= ] || exit 1
echo "Mon Nov 23 18:00:00 2026 /bin/sh /usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh /var/run/dvtws2.pid /usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh /usr/local/etc/zapret2/binaries/my/dvtws2 ${MOCK_CHILD:-542}"
SHELL
chmod 755 "$ROOT/ps"
COMMON_PS_BIN="$ROOT/ps"; export COMMON_PS_BIN
shared_apply_callback_monitor_service 542 777 || fail correct_monitor_refused
if shared_apply_callback_monitor_service 543 777; then fail wrong_original_child_accepted; fi
if shared_apply_callback_monitor_service 542 778; then fail stale_replaced_monitor_accepted; fi
if shared_apply_callback_monitor_service 0 777; then fail invalid_pid_accepted; fi
MOCK_CHILD=599; export MOCK_CHILD
if shared_apply_callback_monitor_service 542 777; then fail forged_pinned_argv_accepted; fi
unset MOCK_CHILD
MOCK_RUNNING=0
if shared_apply_callback_monitor_service 542 777; then fail dead_monitor_accepted; fi
unset MOCK_RUNNING
printf '%s\n' 778 > "$SUPERVISOR_MONITOR_PIDFILE"
if shared_apply_callback_monitor_service 542 777; then fail replaced_pidfile_accepted; fi
printf '%s\n' 777 > "$SUPERVISOR_MONITOR_PIDFILE"
mv "$SUPERVISOR_MONITOR_PIDFILE" "$ROOT/original"
ln -s "$ROOT/original" "$SUPERVISOR_MONITOR_PIDFILE"
if shared_apply_callback_monitor_service 542 777; then fail symlinked_pidfile_accepted; fi
# Execute the ACTUAL script once with an extinct child PID, not merely
# sh -n. The synchronous callback must receive its own numeric monitor PID.
LOOP="$(dirname "$SERVICE")/supervisor_loop.sh"
printf '%s\n' 2000000000 > "$ROOT/pinned-child.pid"
cat > "$ROOT/callback" <<'CALLBACK'
#!/bin/sh
[ "$1" = runtime-failure ] && [ "$3" = 2000000000 ] || exit 1
case "$4" in ""|*[!0-9]*) exit 1 ;; esac
[ "$4" -gt 1 ] || exit 1
printf '%s\n' "$4" > "$S05B2A_TEST_CALLBACK_OUTPUT"
CALLBACK
chmod 755 "$ROOT/callback"
S05B2A_TEST_CALLBACK_OUTPUT="$ROOT/callback.result"
export S05B2A_TEST_CALLBACK_OUTPUT
/bin/sh "$LOOP" "$ROOT/pinned-child.pid" "$ROOT/callback" /usr/bin/false 2000000000 || fail callback_execution
[ -s "$ROOT/callback.result" ] || fail no_real_shell_monitor_pid
echo PASS_S05B2A_PINNED_MONITOR_PROOF
