#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"

set -eu
umask 022

for module in common target request result probe
do
    module_path="${MODULE_DIR}/${module}.sh"
    [ -r "${module_path}" ] || {
        echo "ERROR: required Strategy Lab probe module is missing: ${module_path}" >&2
        exit 1
    }
    . "${module_path}"
done

strategy_lab_require_jq

strategy_lab_probe_runner_kill_tree()
{
    _slprobe_parent="$1"
    if command -v pgrep >/dev/null 2>&1; then
        for _slprobe_child in $(pgrep -P "${_slprobe_parent}" 2>/dev/null || true)
        do
            strategy_lab_probe_runner_kill_tree "${_slprobe_child}"
        done
    fi
    kill -TERM "${_slprobe_parent}" 2>/dev/null || true
}

strategy_lab_probe_runner_cleanup()
{
    for _slprobe_child in $(jobs -p 2>/dev/null || true)
    do
        [ -n "${_slprobe_child}" ] || continue
        strategy_lab_probe_runner_kill_tree "${_slprobe_child}"
    done
    wait 2>/dev/null || true
}
trap strategy_lab_probe_runner_cleanup HUP INT TERM

case "${1:-}" in
    network)
        [ "$#" -eq 3 ] || exit 64
        strategy_lab_run_network_precheck "$2" "$3"
        ;;
    baseline)
        [ "$#" -eq 7 ] || exit 64
        strategy_lab_run_clean_baseline "$2" "$3" "$4" "$5" "$6" "$7"
        ;;
    *)
        echo "usage: strategy_lab_probe_runner.sh {network RESULT WORKDIR|baseline TARGET TYPE ENDPOINTS NETWORK WORKDIR RESULT}" >&2
        exit 64
        ;;
esac
