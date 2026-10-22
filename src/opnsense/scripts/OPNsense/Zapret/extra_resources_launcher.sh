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
        # Whitelisted, newline-free metadata only. Never expose arbitrary
        # status-file contents as shell assignments or render HTML from them.
        if [ -r "$STATUS" ] && [ ! -L "$STATUS" ]; then
            "$PYTHON_BIN" -c '
import json,re,sys
try:
 x=json.load(open(sys.argv[1],encoding="utf-8"))
 phase=x.get("phase","unknown")
 phases={"downloading","verifying","installing","ready","failed",
         "restore_failed","recovery_required","recovering","restored",
         "no_recovery_needed"}
 if phase not in phases: phase="unknown"
 revision=x.get("source_commit") or x.get("revision") or ""
 if not isinstance(revision,str) or not re.fullmatch(r"[0-9a-f]{40}",revision):
  revision=""
 def count(k):
  value=x.get(k)
  return value if type(value) is int and 0<=value<=10000 else 0
 detail=x.get("detail","")
 if not isinstance(detail,str): detail=""
 detail=re.sub(r"[\r\n\x00-\x1f]"," ",detail)[:300]
 print("phase="+phase)
 print("revision="+revision)
 print("lua="+str(count("lua")))
 print("bin="+str(count("bin")))
 print("detail="+detail)
except Exception:
 print("phase=unknown")
' "$STATUS" 2>/dev/null || printf 'phase=unknown\n'
        else
            printf 'phase=unknown\n'
        fi
        printf 'busy=%s\n' "$_busy"
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
