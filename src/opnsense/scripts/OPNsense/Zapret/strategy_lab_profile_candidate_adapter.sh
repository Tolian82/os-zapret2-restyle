#!/bin/sh

SCRIPT_DIR="${SCRIPT_DIR:-/usr/local/opnsense/scripts/OPNsense/Zapret}"
MODULE_DIR="${MODULE_DIR:-${SCRIPT_DIR}/strategy_lab}"
BASE_ADAPTER="${STRATEGY_LAB_BASE_CANDIDATE_SYSTEM_ADAPTER:-${SCRIPT_DIR}/strategy_lab_candidate_adapter.sh}"
set -eu
umask 022

for module in common runtime
do
    path="${MODULE_DIR}/${module}.sh"
    [ -r "${path}" ] || exit 69
    . "${path}"
done

prepare_profile()
{
    job="$1"
    endpoints="$2"
    profile="$3"
    use_hostlist="$4"
    selector="${STRATEGY_LAB_PROFILE_REPLAY_SELECTOR:-}"

    strategy_lab_job_id_valid "${job}" || return 1
    [ "${use_hostlist}" = 0 ] || [ "${use_hostlist}" = 1 ] || return 1
    [ -r "${endpoints}" ] && [ -s "${endpoints}" ] && [ -r "${profile}" ] && [ -s "${profile}" ] || return 1

    runtime=$(strategy_lab_candidate_runtime_dir "${job}")
    args=$(strategy_lab_candidate_args_file "${job}")
    hostlist=$(strategy_lab_candidate_hostlist_file "${job}")
    tmp="${args}.tmp.$$"
    mkdir -p "${runtime}" || return 1

    if [ "${use_hostlist}" = 1 ]; then
        [ -n "${selector}" ] || return 1
        cp "${endpoints}" "${hostlist}" || return 1
        chmod 0644 "${hostlist}" || return 1
    else
        rm -f "${hostlist}"
    fi

    : > "${tmp}" || return 1
    printf '%s\n' "--port=${STRATEGY_LAB_DIVERT_PORT}" >> "${tmp}"
    if [ -d "${STRATEGY_LAB_LUA_DIR}" ]; then
        find "${STRATEGY_LAB_LUA_DIR}" -maxdepth 1 -type f -name '*.lua' -print 2>/dev/null |
            sort | while IFS= read -r lua
            do
                printf '%s\n' "--lua-init=@${lua}"
            done >> "${tmp}"
    fi
    while IFS= read -r line || [ -n "${line}" ]
    do
        if [ "${use_hostlist}" = 1 ] && [ "${line}" = "${selector}" ]; then
            printf '%s\n' "--hostlist=${hostlist}"
        else
            printf '%s\n' "${line}"
        fi
    done < "${profile}" >> "${tmp}" || {
        rm -f "${tmp}"
        return 1
    }
    mv -f "${tmp}" "${args}"
    chmod 0644 "${args}"
}

action="${1:-}"
[ -n "${action}" ] || exit 64
case "${action}" in
    prepare)
        [ "$#" -eq 5 ] || exit 64
        prepare_profile "$2" "$3" "$4" "$5"
        ;;
    prepare-protocol)
        [ "$#" -eq 8 ] || exit 64
        prepare_profile "$2" "$3" "$4" "$5"
        ;;
    *)
        [ -x "${BASE_ADAPTER}" ] || exit 69
        exec /bin/sh "${BASE_ADAPTER}" "$@"
        ;;
esac
