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
         "no_recovery_needed","removing","not_installed"}
 if phase not in phases: phase="unknown"
 operation=x.get("operation","")
 if not isinstance(operation,str) or not re.fullmatch(r"[a-f0-9]{32}",operation):
  operation=""
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
 print("operation="+operation)
 print("revision="+revision)
 print("detail="+detail)
 # The GUI inventory already has a validated, atomically refreshed cache.
 # A recovery receipt ("restored") is an operation outcome, NOT evidence
 # that Additional Resources are absent. No Git/filesystem enumeration here.
 try:
  import os
  from pathlib import Path
  sys.path.insert(0,os.path.dirname(os.path.realpath(sys.argv[2])))
  from extra_resources_inventory_cache import read_cached
  inventory=read_cached(Path(sys.argv[1]).parent)
  # Live counts are derived from the same validated inventory as installed,
  # never from stale transaction receipt fields in status.json.
  print("lua="+str(sum(item["origin"]=="other" for item in inventory["lua"])))
  print("bin="+str(sum(item["origin"]=="other" for item in inventory["bin"])))
  print("installed="+("1" if inventory["installed"] else "0"))
 except Exception:
  print("installed=unknown")
except Exception:
 print("phase=unknown")
 print("installed=unknown")
' "$STATUS" "$SERVICE_SCRIPT" 2>/dev/null || printf 'phase=unknown\ninstalled=unknown\n'
        else
            printf 'phase=unknown\ninstalled=unknown\n'
        fi
        printf 'busy=%s\n' "$_busy"
        ;;
    preview-saved)
        [ "$#" -eq 1 ] || exit 64
        [ -x "$SERVICE_SCRIPT" ] && [ -x "$LOCKF_BIN" ] &&
        [ -x "$PYTHON_BIN" ] || {
            echo "ERROR: read-only resource preview tools missing" >&2
            exit 69
        }
        # A synchronous, non-mutating operation. Existing setup.lock is
        # always acquired BEFORE the original native FD9 service owner.
        exec "$LOCKF_BIN" -s -t 3 "$LOCK_FILE" \
            /usr/bin/env EXTRA_RESOURCES_SETUP_LOCK_OWNER=1 \
            "$SERVICE_SCRIPT" extra-resources-preview-saved
        ;;
    plan)
        [ "$#" -eq 1 ] || exit 64
        [ -x "$SERVICE_SCRIPT" ] && [ -x "$LOCKF_BIN" ] || exit 69
        # Same setup.lock -> original FD9; no daemon, status write,
        # Config mutation, resource removal or runtime compilation.
        exec "$LOCKF_BIN" -s -t 10 "$LOCK_FILE" \
            /usr/bin/env EXTRA_RESOURCES_SETUP_LOCK_OWNER=1 \
            "$SERVICE_SCRIPT" extra-resources-remove-plan
        ;;
    remove-test|remove-test-fail|remove-test-interrupt|remove-test-commit-interrupt|recover-test)
        # Explicit owner-console acceptance. FOREGROUND, root only; never
        # exposed through configd or GUI. setup.lock -> native FD9.
        [ "$(/usr/bin/id -u)" -eq 0 ] && [ -x "$SERVICE_SCRIPT" ] &&
        [ -x "$LOCKF_BIN" ] && [ -x "$PYTHON_BIN" ] || exit 75
        if [ "$MODE" = recover-test ]; then
            [ "$#" -eq 1 ] || exit 64
            exec "$LOCKF_BIN" -s -t 60 "$LOCK_FILE" \
                /usr/bin/env EXTRA_RESOURCES_SETUP_LOCK_OWNER=1 \
                EXTRA_RESOURCES_REMOVE_OWNER_ACCEPTANCE=1 \
                "$SERVICE_SCRIPT" extra-resources-recover-test
        fi
        [ "$#" -eq 2 ] || exit 64
        _witness="$2"
        case "$_witness" in ''|*[!a-f0-9]*) exit 64 ;; esac
        [ "${#_witness}" -eq 64 ] || exit 64
        exec "$LOCKF_BIN" -s -t 60 "$LOCK_FILE" \
            /usr/bin/env EXTRA_RESOURCES_SETUP_LOCK_OWNER=1 \
            EXTRA_RESOURCES_REMOVE_OWNER_ACCEPTANCE=1 \
            "$SERVICE_SCRIPT" "$MODE" "$_witness"
        ;;
    install|recover)
        if [ "$MODE" = install ]; then
            [ "$#" -eq 2 ] || exit 64
            _operation_id="$2"
            case "$_operation_id" in ''|*[!a-f0-9]*) exit 64 ;; esac
            [ "${#_operation_id}" -eq 32 ] || exit 64
        else
            [ "$#" -eq 1 ] || exit 64
            _operation_id=""
        fi
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
            "EXTRA_RESOURCES_OPERATION_ID=${_operation_id}" \
            "$SERVICE_SCRIPT" "$_command"
        ;;
    *)
        echo 'usage: extra_resources_launcher.sh {install|recover|status|preview-saved|plan|remove-test|remove-test-fail|remove-test-interrupt|remove-test-commit-interrupt|recover-test}' >&2
        exit 64
        ;;
esac
