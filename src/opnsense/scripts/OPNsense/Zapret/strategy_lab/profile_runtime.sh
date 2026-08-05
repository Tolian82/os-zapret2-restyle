#!/bin/sh

strategy_lab_candidate_prepare_files()
{
    _slpr_job="$1"
    _slpr_endpoints="$2"
    _slpr_profile="$3"
    _slpr_target="${STRATEGY_LAB_PROFILE_TARGET:-}"
    _slpr_type="${STRATEGY_LAB_PROFILE_TARGET_TYPE:-}"
    _slpr_protocol="${STRATEGY_LAB_PROFILE_PROTOCOL:-tls13}"
    _slpr_port="${STRATEGY_LAB_PROFILE_PORT:-443}"
    _slpr_addresses="${STRATEGY_LAB_PROFILE_SELECTOR_ADDRESSES:-}"
    _slpr_runtime=$(strategy_lab_candidate_runtime_dir "${_slpr_job}")
    _slpr_args=$(strategy_lab_candidate_args_file "${_slpr_job}")
    _slpr_hostlist=$(strategy_lab_candidate_hostlist_file "${_slpr_job}")
    _slpr_tmp="${_slpr_args}.tmp.$$"

    [ -s "${_slpr_endpoints}" ] || return 1
    strategy_lab_profile_validate_protocol \
        "${_slpr_target}" "${_slpr_type}" "${_slpr_protocol}" "${_slpr_port}" \
        "${_slpr_addresses}" "${_slpr_profile}" || return 1
    _slpr_selector=$(strategy_lab_profile_selector_for \
        "${_slpr_target}" "${_slpr_type}" "${_slpr_protocol}" "${_slpr_addresses}") || return 1
    mkdir -p "${_slpr_runtime}" || return 1
    cp "${_slpr_endpoints}" "${_slpr_hostlist}" || return 1
    chmod 0644 "${_slpr_hostlist}"

    (
        printf '%s\n' "--port=${STRATEGY_LAB_DIVERT_PORT}"
        if [ -d "${STRATEGY_LAB_LUA_DIR}" ]; then
            find "${STRATEGY_LAB_LUA_DIR}" -maxdepth 1 -type f -name '*.lua' -print 2>/dev/null |
                sort | while IFS= read -r _slpr_lua
                do
                    printf '%s\n' "--lua-init=@${_slpr_lua}"
                done
        fi
        while IFS= read -r _slpr_line || [ -n "${_slpr_line}" ]
        do
            if [ "${_slpr_line}" = "${_slpr_selector}" ] &&
               [ "${_slpr_type}" = domain ] &&
               [ "${_slpr_protocol}" != udp ]; then
                printf '%s\n' "--hostlist=${_slpr_hostlist}"
            else
                printf '%s\n' "${_slpr_line}"
            fi
        done < "${_slpr_profile}"
    ) > "${_slpr_tmp}" || {
        rm -f "${_slpr_tmp}"
        return 1
    }
    mv -f "${_slpr_tmp}" "${_slpr_args}"
    chmod 0644 "${_slpr_args}"
}
