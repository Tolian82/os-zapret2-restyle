#!/bin/sh
# Manually requested Additional Resources launcher. setup.lock -> original FD9.
set -eu
umask 077
MODE="$1"
SERVICE_SCRIPT="${SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}"
DAEMON_BIN="${DAEMON_BIN:-/usr/sbin/daemon}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
RUN_DIR="${RUN_DIR:-/var/run/zapret2-restyle}"
LOG_DIR="${LOG_DIR:-/var/log/zapret2}"
SETUP_PID="${SETUP_PID:-${RUN_DIR}/setup.pid}"
PID_FILE="${PID_FILE:-${RUN_DIR}/extra-resources.pid}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/extra-resources.log}"
LOCK_FILE="${LOCK_FILE:-${RUN_DIR}/setup.lock}"
STATUS="${STATUS:-/var/db/zapret2-restyle/extra-resources/status.json}"
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python3.13}"

pid_live()
{
    _pid_file="$1"
    [ -r "$_pid_file" ] || return 1
    _pid=""
    IFS= read -r _pid < "$_pid_file" || true
    case "$_pid" in ''|*[!0-9]*) return 1 ;; esac
    kill -0 "$_pid" 2>/dev/null
}

case "$MODE" in
    status)
        _busy=0
        pid_live "$PID_FILE" && _busy=1
        _phase=unknown
        if [ -r "$STATUS" ] && [ ! -L "$STATUS" ]; then
            _phase=$("$PYTHON_BIN" -c '
import json,sys
try:
 x=json.load(open(sys.argv[1],encoding="utf-8"))
 p=x.get("phase","unknown")
 if isinstance(p,str) and p in {
    "downloading","verifying","installing","ready","failed",
    "restore_failed","recovery_required","recovering","restored",
    "no_recovery_needed"}:
  print(p)
 else: print("unknown")
except Exception: print("unknown")
' "$STATUS" 2>/dev/null) || _phase=unknown
        fi
        printf 'busy=%s\nphase=%s\n' "$_busy" "$_phase"
        ;;
    install|recover)
        [ "$#" -eq 1 ] || exit 64
        [ -x "$SERVICE_SCRIPT" ] && [ -x "$DAEMON_BIN" ] && [ -x "$LOCKF_BIN" ] || {
            echo "ERROR: resource service tools missing" >&2; exit 69;
        }
        if pid_live "$PID_FILE" || pid_live "$SETUP_PID"; then
            echo "ERROR: another zapret setup/resources operation is active" >&2
            exit 75
        fi
        mkdir -p "$LOG_DIR" "$RUN_DIR"
        rm -f "$PID_FILE"
        if [ "$MODE" = install ]; then
            _command=extra-resources-install
        else
            _command=extra-resources-recover
        fi
        exec "$DAEMON_BIN" -f -o "$LOG_FILE" -p "$PID_FILE" \
            "$LOCKF_BIN" -s -t 60 "$LOCK_FILE" \
            /usr/bin/env EXTRA_RESOURCES_SETUP_LOCK_OWNER=1 \
            "$SERVICE_SCRIPT" "$_command"
        ;;
    *)
        echo 'usage: extra_resources_launcher.sh {install|recover|status}' >&2
        exit 64
        ;;
esac
