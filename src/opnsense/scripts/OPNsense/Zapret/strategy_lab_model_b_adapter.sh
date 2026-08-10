#!/bin/sh

# Narrow FreeBSD mutation boundary for the experiment-only Model-B warm-worker harness.
# It owns only the dedicated ports/rules below and never changes the normal Strategy Lab
# candidate lifecycle or the normal Zapret2 rule range.

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
set -eu
umask 022

for module in common runtime
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 69
    . "${path}"
done

STRATEGY_LAB_MODEL_B_SESSION_DIR="${STRATEGY_LAB_MODEL_B_SESSION_DIR:-}"
STRATEGY_LAB_MODEL_B_IPFW_BIN="${STRATEGY_LAB_MODEL_B_IPFW_BIN:-/sbin/ipfw}"
STRATEGY_LAB_MODEL_B_KLDSTAT_BIN="${STRATEGY_LAB_MODEL_B_KLDSTAT_BIN:-/sbin/kldstat}"
STRATEGY_LAB_MODEL_B_SYSCTL_BIN="${STRATEGY_LAB_MODEL_B_SYSCTL_BIN:-/sbin/sysctl}"
STRATEGY_LAB_MODEL_B_SOCKSTAT_BIN="${STRATEGY_LAB_MODEL_B_SOCKSTAT_BIN:-/usr/bin/sockstat}"
STRATEGY_LAB_MODEL_B_NETSTAT_BIN="${STRATEGY_LAB_MODEL_B_NETSTAT_BIN:-/usr/bin/netstat}"
MODEL_B_RULES="19128 19129 19130"
MODEL_B_PORTS="9990 9991 9992"

[ -n "${STRATEGY_LAB_MODEL_B_SESSION_DIR}" ] || exit 64

valid_worker()
{
    case "$1" in pass|builtin|external) return 0 ;; esac
    return 1
}

valid_port()
{
    case " $MODEL_B_PORTS " in *" $1 "*) return 0 ;; esac
    return 1
}

valid_rule()
{
    case " $MODEL_B_RULES " in *" $1 "*) return 0 ;; esac
    return 1
}

valid_protocol()
{
    case "$1" in tcp|udp) return 0 ;; esac
    return 1
}

valid_destination_port()
{
    case "$1" in ''|*[!0-9]*) return 1 ;; esac
    [ "$1" -ge 1 ] 2>/dev/null && [ "$1" -le 65535 ] 2>/dev/null
}

worker_dir(){ printf '%s/workers/%s\n' "${STRATEGY_LAB_MODEL_B_SESSION_DIR}" "$1"; }
worker_pidfile(){ printf '%s/dvtws2.pid\n' "$(worker_dir "$1")"; }
worker_log(){ printf '%s/dvtws2.log\n' "$(worker_dir "$1")"; }
worker_args(){ printf '%s/dvtws.args\n' "$(worker_dir "$1")"; }

pid_read()
{
    _mb_pidfile="$1"
    _mb_pid=''
    [ -r "${_mb_pidfile}" ] || return 1
    IFS= read -r _mb_pid < "${_mb_pidfile}" || true
    case "${_mb_pid}" in ''|*[!0-9]*) return 1 ;; esac
    printf '%s\n' "${_mb_pid}"
}

process_command()
{
    "${STRATEGY_LAB_PS_BIN}" -p "$1" -o command= 2>/dev/null || true
}

pid_identity()
{
    _mb_pid="$1"
    _mb_port="$2"
    case "${_mb_pid}" in ''|*[!0-9]*) return 1 ;; esac
    valid_port "${_mb_port}" || return 1
    kill -0 "${_mb_pid}" 2>/dev/null || return 1
    _mb_command=$(process_command "${_mb_pid}")
    case " ${_mb_command} " in *" ${STRATEGY_LAB_DVTWS_BIN} "*) ;; *) return 1 ;; esac
    case " ${_mb_command} " in *" --port=${_mb_port} "*) return 0 ;; *) return 1 ;; esac
}

process_pids_for_port()
{
    _mb_port="$1"
    valid_port "${_mb_port}" || return 1
    "${STRATEGY_LAB_PS_BIN}" ax -o pid= -o command= 2>/dev/null |
        awk -v bin="${STRATEGY_LAB_DVTWS_BIN}" -v port="--port=${_mb_port}" '
            index($0, bin) && index($0, port) { print $1 }
        '
}

port_in_use()
{
    _mb_port="$1"
    valid_port "${_mb_port}" || return 1
    if [ -x "${STRATEGY_LAB_MODEL_B_SOCKSTAT_BIN}" ]; then
        "${STRATEGY_LAB_MODEL_B_SOCKSTAT_BIN}" -4 -l 2>/dev/null |
            awk -v port="${_mb_port}" '
                $0 ~ ("[:.]" port "([[:space:]]|$)") { found=1 }
                END { exit found ? 0 : 1 }
            ' && return 0
    fi
    if [ -x "${STRATEGY_LAB_MODEL_B_NETSTAT_BIN}" ]; then
        "${STRATEGY_LAB_MODEL_B_NETSTAT_BIN}" -an -f inet 2>/dev/null |
            awk -v port="${_mb_port}" '
                tolower($0) ~ /divert/ && $0 ~ ("[.:]" port "([[:space:]]|$)") { found=1 }
                END { exit found ? 0 : 1 }
            ' && return 0
    fi
    for _mb_pid in $(process_pids_for_port "${_mb_port}" 2>/dev/null || true)
    do
        pid_identity "${_mb_pid}" "${_mb_port}" && return 0
    done
    return 1
}

rule_present()
{
    _mb_rule="$1"
    valid_rule "${_mb_rule}" || return 1
    "${STRATEGY_LAB_MODEL_B_IPFW_BIN}" list "${_mb_rule}" 2>/dev/null |
        grep -q '^[0-9]'
}

firewall_ready()
{
    [ -x "${STRATEGY_LAB_MODEL_B_IPFW_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_MODEL_B_KLDSTAT_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_MODEL_B_SYSCTL_BIN}" ] || return 1
    "${STRATEGY_LAB_MODEL_B_KLDSTAT_BIN}" -q -m ipfw || return 1
    "${STRATEGY_LAB_MODEL_B_KLDSTAT_BIN}" -q -m ipdivert || return 1
    [ "$("${STRATEGY_LAB_MODEL_B_SYSCTL_BIN}" -n net.inet.ip.fw.enable 2>/dev/null || true)" = 1 ]
}

log_clean()
{
    _mb_log="$1"
    [ -r "${_mb_log}" ] || return 1
    ! grep -Eqi '(^|[^a-z])(fatal|panic|syntax error|unknown option|invalid (argument|option)|cannot (bind|open|load)|failed to (bind|load))([^a-z]|$)' \
        "${_mb_log}"
}

cleanup_port()
{
    _mb_port="$1"
    valid_port "${_mb_port}" || return 1
    for _mb_pid in $(process_pids_for_port "${_mb_port}" 2>/dev/null || true)
    do
        pid_identity "${_mb_pid}" "${_mb_port}" || continue
        kill -TERM "${_mb_pid}" 2>/dev/null || true
    done
    _mb_wait=0
    while [ "${_mb_wait}" -lt 3 ]
    do
        port_in_use "${_mb_port}" || return 0
        sleep 1
        _mb_wait=$((_mb_wait + 1))
    done
    for _mb_pid in $(process_pids_for_port "${_mb_port}" 2>/dev/null || true)
    do
        pid_identity "${_mb_pid}" "${_mb_port}" || continue
        kill -KILL "${_mb_pid}" 2>/dev/null || true
    done
    sleep 1
    ! port_in_use "${_mb_port}"
}

cleanup_all()
{
    _mb_status=0
    for _mb_rule in $MODEL_B_RULES
    do
        "${STRATEGY_LAB_MODEL_B_IPFW_BIN}" -q delete "${_mb_rule}" 2>/dev/null || true
    done
    for _mb_port in $MODEL_B_PORTS
    do
        cleanup_port "${_mb_port}" || _mb_status=1
    done
    for _mb_rule in $MODEL_B_RULES
    do
        rule_present "${_mb_rule}" && _mb_status=1
    done
    return "${_mb_status}"
}

preflight()
{
    firewall_ready || return 1
    [ -x "${STRATEGY_LAB_DVTWS_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_DAEMON_BIN}" ] || return 1
    for _mb_rule in $MODEL_B_RULES
    do
        rule_present "${_mb_rule}" && return 1
    done
    for _mb_port in $MODEL_B_PORTS
    do
        port_in_use "${_mb_port}" && return 1
    done
}

launch_worker()
{
    _mb_worker="$1"
    _mb_port="$2"
    valid_worker "${_mb_worker}" || return 1
    valid_port "${_mb_port}" || return 1
    _mb_dir=$(worker_dir "${_mb_worker}")
    _mb_args=$(worker_args "${_mb_worker}")
    _mb_pidfile=$(worker_pidfile "${_mb_worker}")
    _mb_log=$(worker_log "${_mb_worker}")
    [ -d "${_mb_dir}" ] && [ -r "${_mb_args}" ] && [ -s "${_mb_args}" ] || return 1
    [ "$(grep -c "^--port=${_mb_port}$" "${_mb_args}" 2>/dev/null || true)" -eq 1 ] || return 1
    [ "$(grep -c '^--port=' "${_mb_args}" 2>/dev/null || true)" -eq 1 ] || return 1
    port_in_use "${_mb_port}" && return 1
    : > "${_mb_log}" || return 1
    rm -f "${_mb_pidfile}"

    set -- "${STRATEGY_LAB_DVTWS_BIN}"
    while IFS= read -r _mb_argument || [ -n "${_mb_argument}" ]
    do
        [ -n "${_mb_argument}" ] || continue
        set -- "$@" "${_mb_argument}"
    done < "${_mb_args}"
    set -- "$@" '--sockarg=0x200' '--user=nobody'
    "${STRATEGY_LAB_DAEMON_BIN}" -p "${_mb_pidfile}" -o "${_mb_log}" -f "$@" 9>&- </dev/null >/dev/null 2>&1 &
}

snapshot_worker()
{
    _mb_worker="$1"
    _mb_port="$2"
    valid_worker "${_mb_worker}" || return 1
    valid_port "${_mb_port}" || return 1
    _mb_pidfile=$(worker_pidfile "${_mb_worker}")
    _mb_log=$(worker_log "${_mb_worker}")
    _mb_pid=$(pid_read "${_mb_pidfile}" 2>/dev/null || true)
    _mb_identity=false
    _mb_socket=false
    _mb_clean=false
    _mb_command=''
    _mb_rss=''
    if [ -n "${_mb_pid}" ] && pid_identity "${_mb_pid}" "${_mb_port}"; then
        _mb_identity=true
        _mb_command=$(process_command "${_mb_pid}")
        _mb_rss=$("${STRATEGY_LAB_PS_BIN}" -p "${_mb_pid}" -o rss= 2>/dev/null | awk 'NF { print $1; exit }' || true)
        case "${_mb_rss}" in ''|*[!0-9]*) _mb_rss='' ;; esac
    fi
    port_in_use "${_mb_port}" && _mb_socket=true
    log_clean "${_mb_log}" && _mb_clean=true
    strategy_lab_require_jq
    "${STRATEGY_LAB_JQ}" -nc \
        --arg worker "${_mb_worker}" --arg pid "${_mb_pid}" --arg command "${_mb_command}" \
        --arg rss "${_mb_rss}" --argjson port "${_mb_port}" \
        --argjson identity "${_mb_identity}" --argjson socket "${_mb_socket}" \
        --argjson clean "${_mb_clean}" '
        {worker:$worker,pid:(if $pid=="" then null else ($pid|tonumber) end),
         command:$command,divert_port:$port,process_identity:$identity,socket_ready:$socket,
         log_clean:$clean,rss_kb:(if $rss=="" then null else ($rss|tonumber) end)}'
}

stop_worker()
{
    _mb_worker="$1"
    _mb_port="$2"
    valid_worker "${_mb_worker}" || return 1
    valid_port "${_mb_port}" || return 1
    _mb_pidfile=$(worker_pidfile "${_mb_worker}")
    _mb_pid=$(pid_read "${_mb_pidfile}" 2>/dev/null || true)
    if [ -n "${_mb_pid}" ] && pid_identity "${_mb_pid}" "${_mb_port}"; then
        kill -TERM "${_mb_pid}" 2>/dev/null || true
    fi
    cleanup_port "${_mb_port}" || return 1
    rm -f "${_mb_pidfile}"
}

kill_owned()
{
    _mb_worker="$1"
    _mb_port="$2"
    valid_worker "${_mb_worker}" || return 1
    valid_port "${_mb_port}" || return 1
    _mb_pid=$(pid_read "$(worker_pidfile "${_mb_worker}")" 2>/dev/null || true)
    [ -n "${_mb_pid}" ] || return 1
    pid_identity "${_mb_pid}" "${_mb_port}" || return 1
    kill -KILL "${_mb_pid}"
}

route_add()
{
    _mb_rule="$1"; _mb_port="$2"; _mb_address="$3"; _mb_wan="$4"; _mb_transport="$5"; _mb_dport="$6"
    valid_rule "${_mb_rule}" || return 1
    valid_port "${_mb_port}" || return 1
    valid_protocol "${_mb_transport}" || return 1
    valid_destination_port "${_mb_dport}" || return 1
    [ -n "${_mb_address}" ] && [ -n "${_mb_wan}" ] || return 1
    firewall_ready || return 1
    rule_present "${_mb_rule}" && return 1
    "${STRATEGY_LAB_MODEL_B_IPFW_BIN}" -qf add "${_mb_rule}" divert "${_mb_port}" \
        "${_mb_transport}" from me to "${_mb_address}" "${_mb_dport}" \
        out not diverted not sockarg xmit "${_mb_wan}"
}

route_del()
{
    _mb_rule="$1"
    valid_rule "${_mb_rule}" || return 1
    "${STRATEGY_LAB_MODEL_B_IPFW_BIN}" -q delete "${_mb_rule}" 2>/dev/null || true
    ! rule_present "${_mb_rule}"
}

counter()
{
    _mb_rule="$1"
    valid_rule "${_mb_rule}" || return 1
    "${STRATEGY_LAB_MODEL_B_IPFW_BIN}" -a list "${_mb_rule}" 2>/dev/null |
        awk -v wanted="${_mb_rule}" '
            ($1 + 0) == (wanted + 0) && $2 ~ /^[0-9]+$/ && $3 ~ /^[0-9]+$/ {
                print $2, $3; found=1; exit
            }
            END { if (!found) exit 1 }
        '
}

action="${1:-}"
[ -n "${action}" ] || exit 64
shift || true

case "${action}" in
    wan)
        [ "$#" -eq 0 ] || exit 64
        strategy_lab_candidate_resolve_wan
        ;;
    preflight)
        [ "$#" -eq 0 ] || exit 64
        preflight
        ;;
    launch)
        [ "$#" -eq 2 ] || exit 64
        launch_worker "$1" "$2"
        ;;
    snapshot)
        [ "$#" -eq 2 ] || exit 64
        snapshot_worker "$1" "$2"
        ;;
    stop)
        [ "$#" -eq 2 ] || exit 64
        stop_worker "$1" "$2"
        ;;
    kill-owned)
        [ "$#" -eq 2 ] || exit 64
        kill_owned "$1" "$2"
        ;;
    route-add)
        [ "$#" -eq 6 ] || exit 64
        route_add "$1" "$2" "$3" "$4" "$5" "$6"
        ;;
    route-del)
        [ "$#" -eq 1 ] || exit 64
        route_del "$1"
        ;;
    rule-present)
        [ "$#" -eq 1 ] || exit 64
        rule_present "$1"
        ;;
    counter)
        [ "$#" -eq 1 ] || exit 64
        counter "$1"
        ;;
    cleanup-all)
        [ "$#" -eq 0 ] || exit 64
        cleanup_all
        ;;
    *) exit 64 ;;
esac
