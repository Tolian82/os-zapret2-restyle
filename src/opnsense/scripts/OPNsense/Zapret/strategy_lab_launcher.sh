#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
WORKER_SCRIPT="${WORKER_SCRIPT:-${SCRIPT_DIR}/strategy_lab_worker.sh}"
TRANSACTION_SCRIPT="${TRANSACTION_SCRIPT:-${SCRIPT_DIR}/zapret_service.sh}"
DAEMON_BIN="${DAEMON_BIN:-/usr/sbin/daemon}"
LOCKF_BIN="${LOCKF_BIN:-/usr/bin/lockf}"
MODE="${1:-status}"

set -eu
umask 022

for module in common state target firewall runtime launch query
do
    module_path="${MODULE_DIR}/${module}.sh"
    [ -r "${module_path}" ] || { echo "ERROR: required Strategy Lab module is missing: ${module_path}" >&2; exit 1; }
    . "${module_path}"
done

strategy_lab_require_jq
strategy_lab_prepare_directories
[ -x "${LOCKF_BIN}" ] || { emit_error_json "Strategy Lab lock utility is unavailable"; exit 1; }

case "${MODE}" in
    start|cancel|status|result)
        (
            if ! "${LOCKF_BIN}" -s -t 0 9; then
                "${STRATEGY_LAB_JQ}" -nc '{status:"busy",message:"Strategy Lab launcher is busy"}'
                exit 75
            fi
            case "${MODE}" in
                start) start_job "$@" ;;
                cancel) cancel_job "$@" ;;
                status) show_status "$@" ;;
                result) show_result "$@" ;;
            esac
        ) 9>"${STRATEGY_LAB_LOCK_FILE}"
        ;;
    *) usage_error "unsupported mode: ${MODE}" ;;
esac
