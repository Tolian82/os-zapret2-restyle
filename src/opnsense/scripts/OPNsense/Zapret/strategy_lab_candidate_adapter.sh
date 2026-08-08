#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
umask 022

for module in common firewall runtime
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 69
    . "${path}"
done

jobdir_allow_access()
{
    jobdir=$(strategy_lab_job_dir "$1")
    runtime=$(strategy_lab_candidate_runtime_dir "$1")
    [ -d "${jobdir}" ] && [ -d "${runtime}" ] || return 1
    chmod 0711 "${jobdir}" || return 1
    chmod 0755 "${runtime}" || {
        chmod 0700 "${jobdir}" || true
        return 1
    }
}

jobdir_restore_private()
{
    jobdir=$(strategy_lab_job_dir "$1")
    [ ! -d "${jobdir}" ] || chmod 0700 "${jobdir}"
}

cleanup_candidate()
{
    status=0
    strategy_lab_candidate_stop "$1" || status=1
    strategy_lab_firewall_remove_rules || status=1
    strategy_lab_firewall_range_empty || status=1
    jobdir_restore_private "$1" || status=1
    return "${status}"
}

launch_candidate()
{
    job="$1"
    args=$(strategy_lab_candidate_args_file "${job}")
    pidfile=$(strategy_lab_candidate_pid_file "${job}")
    log=$(strategy_lab_candidate_log_file "${job}")

    [ -x "${STRATEGY_LAB_DVTWS_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_DAEMON_BIN}" ] || return 1
    [ -r "${args}" ] && [ -s "${args}" ] || return 1
    strategy_lab_candidate_stop "${job}" || return 1
    : > "${log}" || return 1

    set -- "${STRATEGY_LAB_DVTWS_BIN}"
    while IFS= read -r argument || [ -n "${argument}" ]
    do
        [ -n "${argument}" ] || continue
        set -- "$@" "${argument}"
    done < "${args}"
    set -- "$@" '--sockarg=0x200' '--user=nobody'

    "${STRATEGY_LAB_DAEMON_BIN}" -p "${pidfile}" -o "${log}" -f "$@" 9>&- </dev/null >/dev/null 2>&1 &
    return 0
}

runtime_snapshot()
{
    job="$1"
    pidfile=$(strategy_lab_candidate_pid_file "${job}")
    pid=$(strategy_lab_candidate_pid_read "${pidfile}" 2>/dev/null || true)
    identity=false
    socket=false
    command=''
    if [ -n "${pid}" ] && strategy_lab_candidate_pid_identity "${pid}"; then
        identity=true
        command=$(strategy_lab_candidate_command "${pid}")
    fi
    strategy_lab_candidate_divert_port_in_use && socket=true
    strategy_lab_require_jq
    "${STRATEGY_LAB_JQ}" -nc \
        --arg pid "${pid}" \
        --arg executable "${STRATEGY_LAB_DVTWS_BIN}" \
        --arg command "${command}" \
        --argjson divert_port "${STRATEGY_LAB_DIVERT_PORT}" \
        --argjson process_identity "${identity}" \
        --argjson socket_ready "${socket}" '
        {
          pid:(if $pid=="" then null else ($pid|tonumber) end),
          executable:$executable,
          command:$command,
          divert_port:$divert_port,
          process_identity:$process_identity,
          socket_ready:$socket_ready
        }'
}

action="${1:-}"
[ -n "${action}" ] || exit 64
shift || true

case "${action}" in
    wan)
        [ "$#" -eq 0 ] || exit 64
        strategy_lab_candidate_resolve_wan
        ;;
    prepare)
        [ "$#" -eq 4 ] || exit 64
        strategy_lab_job_id_valid "$1" || exit 64
        strategy_lab_candidate_prepare_files "$1" "$2" "$3" "$4"
        ;;
    cleanup)
        [ "$#" -eq 1 ] || exit 64
        strategy_lab_job_id_valid "$1" || exit 64
        cleanup_candidate "$1"
        ;;
    firewall-install)
        [ "$#" -eq 2 ] || exit 64
        strategy_lab_firewall_install_ipv4_rules "$1" "$2"
        ;;
    allow-access)
        [ "$#" -eq 1 ] || exit 64
        strategy_lab_job_id_valid "$1" || exit 64
        jobdir_allow_access "$1"
        ;;
    launch)
        [ "$#" -eq 1 ] || exit 64
        strategy_lab_job_id_valid "$1" || exit 64
        launch_candidate "$1"
        ;;
    snapshot)
        [ "$#" -eq 1 ] || exit 64
        strategy_lab_job_id_valid "$1" || exit 64
        runtime_snapshot "$1"
        ;;
    counter)
        [ "$#" -eq 1 ] || exit 64
        strategy_lab_firewall_rule_counters "$1"
        ;;
    *) exit 64 ;;
esac
