#!/bin/sh

strategy_lab_candidate_readiness_file()
{
    printf '%s/readiness.json\n' "$(strategy_lab_candidate_runtime_dir "$1")"
}

strategy_lab_candidate_readiness_write()
{
    _slready_job="$1"
    _slready_stable="$2"
    _slready_output=$(strategy_lab_candidate_readiness_file "${_slready_job}")
    _slready_pidfile=$(strategy_lab_candidate_pid_file "${_slready_job}")
    _slready_log=$(strategy_lab_candidate_log_file "${_slready_job}")
    _slready_pid=$(strategy_lab_candidate_pid_read "${_slready_pidfile}" 2>/dev/null || true)
    _slready_command=""
    _slready_identity=false
    _slready_socket=false
    _slready_log_clean=false

    if [ -n "${_slready_pid}" ] && strategy_lab_candidate_pid_identity "${_slready_pid}"; then
        _slready_identity=true
        _slready_command=$(strategy_lab_candidate_command "${_slready_pid}")
    fi
    strategy_lab_candidate_divert_port_in_use && _slready_socket=true
    strategy_lab_candidate_log_clean "${_slready_log}" && _slready_log_clean=true

    _slready_ready=false
    if [ "${_slready_identity}" = true ] &&
       [ "${_slready_socket}" = true ] &&
       [ "${_slready_log_clean}" = true ] &&
       [ "${_slready_stable}" = true ]; then
        _slready_ready=true
    fi

    "${STRATEGY_LAB_JQ}" -nc \
        --arg job_id "${_slready_job}" \
        --arg pid "${_slready_pid}" \
        --arg executable "${STRATEGY_LAB_DVTWS_BIN}" \
        --arg command "${_slready_command}" \
        --argjson divert_port "${STRATEGY_LAB_DIVERT_PORT}" \
        --argjson process_identity "${_slready_identity}" \
        --argjson socket_ready "${_slready_socket}" \
        --argjson log_clean "${_slready_log_clean}" \
        --argjson stable "${_slready_stable}" \
        --argjson ready "${_slready_ready}" '
        {
            job_id:$job_id,
            pid:(if $pid=="" then null else ($pid|tonumber) end),
            executable:$executable,
            command:$command,
            divert_port:$divert_port,
            process_identity:$process_identity,
            socket_ready:$socket_ready,
            log_clean:$log_clean,
            stable:$stable,
            ready:$ready
        }' | strategy_lab_atomic_write "${_slready_output}" || return 1

    [ "${_slready_ready}" = true ]
}

strategy_lab_candidate_attach_runtime_evidence()
{
    _slready_job="$1"
    _slready_result="$2"
    _slready_evidence=$(strategy_lab_candidate_readiness_file "${_slready_job}")
    [ -r "${_slready_result}" ] && [ -r "${_slready_evidence}" ] || return 1
    "${STRATEGY_LAB_JQ}" -e '.ready==true' "${_slready_evidence}" >/dev/null || return 1
    _slready_tmp="${_slready_result}.runtime.$$"
    "${STRATEGY_LAB_JQ}" --slurpfile runtime "${_slready_evidence}" '
        .runtime=$runtime[0] |
        .all_pass=((.all_pass==true) and ($runtime[0].ready==true))
    ' "${_slready_result}" > "${_slready_tmp}" || {
        rm -f "${_slready_tmp}"
        return 1
    }
    chmod 0644 "${_slready_tmp}"
    mv -f "${_slready_tmp}" "${_slready_result}"
}

strategy_lab_candidate_start()
{
    _slready_job="$1"
    _slready_args=$(strategy_lab_candidate_args_file "${_slready_job}")
    _slready_pidfile=$(strategy_lab_candidate_pid_file "${_slready_job}")
    _slready_log=$(strategy_lab_candidate_log_file "${_slready_job}")

    [ -x "${STRATEGY_LAB_DVTWS_BIN}" ] || return 1
    [ -x "${STRATEGY_LAB_DAEMON_BIN}" ] || return 1
    [ -r "${_slready_args}" ] && [ -s "${_slready_args}" ] || return 1
    strategy_lab_candidate_stop "${_slready_job}" || return 1
    : > "${_slready_log}" || return 1
    rm -f "$(strategy_lab_candidate_readiness_file "${_slready_job}")"

    set -- "${STRATEGY_LAB_DVTWS_BIN}"
    while IFS= read -r _slready_argument || [ -n "${_slready_argument}" ]
    do
        [ -n "${_slready_argument}" ] || continue
        set -- "$@" "${_slready_argument}"
    done < "${_slready_args}"
    set -- "$@" '--sockarg=0x200' '--user=nobody'

    "${STRATEGY_LAB_DAEMON_BIN}" -p "${_slready_pidfile}" -o "${_slready_log}" -f "$@" 9>&- || return 1
    _slready_wait=0
    while [ "${_slready_wait}" -lt "${STRATEGY_LAB_RUNTIME_START_TIMEOUT}" ]
    do
        if strategy_lab_candidate_ready "${_slready_job}"; then
            sleep 1
            if strategy_lab_candidate_ready "${_slready_job}" &&
               strategy_lab_candidate_readiness_write "${_slready_job}" true; then
                return 0
            fi
        fi
        sleep 1
        _slready_wait=$((_slready_wait + 1))
    done
    strategy_lab_candidate_readiness_write "${_slready_job}" false || true
    strategy_lab_candidate_stop "${_slready_job}" || true
    return 1
}
