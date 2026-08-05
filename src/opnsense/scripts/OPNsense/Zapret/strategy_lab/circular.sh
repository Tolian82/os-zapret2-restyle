#!/bin/sh

STRATEGY_LAB_CIRCULAR_DIR="${STRATEGY_LAB_CIRCULAR_DIR:-${STRATEGY_LAB_RUN_DIR}/circular}"
STRATEGY_LAB_CIRCULAR_STATE="${STRATEGY_LAB_CIRCULAR_STATE:-${STRATEGY_LAB_CIRCULAR_DIR}/state.json}"
STRATEGY_LAB_CIRCULAR_STOP="${STRATEGY_LAB_CIRCULAR_STOP:-${STRATEGY_LAB_CIRCULAR_DIR}/stop}"
STRATEGY_LAB_CIRCULAR_PID="${STRATEGY_LAB_CIRCULAR_PID:-${STRATEGY_LAB_CIRCULAR_DIR}/worker.pid}"
STRATEGY_LAB_CIRCULAR_LOG="${STRATEGY_LAB_CIRCULAR_LOG:-${STRATEGY_LAB_CIRCULAR_DIR}/worker.log}"
STRATEGY_LAB_CIRCULAR_TTL="${STRATEGY_LAB_CIRCULAR_TTL:-300}"

strategy_lab_circular_prepare_dir()
{
    mkdir -p "${STRATEGY_LAB_CIRCULAR_DIR}" || return 1
    chmod 0755 "${STRATEGY_LAB_CIRCULAR_DIR}"
}

strategy_lab_circular_state_write()
{
    _slcirc_state="$1"
    _slcirc_job="$2"
    _slcirc_message="$3"
    _slcirc_count="${4:-0}"
    _slcirc_reason="${5:-}"
    _slcirc_tmp=$(mktemp "${STRATEGY_LAB_CIRCULAR_DIR}/.state.XXXXXX") || return 1
    "${STRATEGY_LAB_JQ}" -nc \
        --arg state "${_slcirc_state}" \
        --arg job_id "${_slcirc_job}" \
        --arg message "${_slcirc_message}" \
        --arg reason "${_slcirc_reason}" \
        --argjson count "${_slcirc_count}" \
        '{state:$state,job_id:$job_id,message:$message,reason:$reason,candidate_count:$count}' \
        > "${_slcirc_tmp}" || {
            rm -f "${_slcirc_tmp}"
            return 1
        }
    chmod 0644 "${_slcirc_tmp}"
    mv -f "${_slcirc_tmp}" "${STRATEGY_LAB_CIRCULAR_STATE}"
}

strategy_lab_circular_shortlist_file()
{
    printf '%s/shortlist.json\n' "$(strategy_lab_job_dir "$1")"
}

strategy_lab_circular_endpoints_file()
{
    printf '%s/endpoints.txt\n' "$(strategy_lab_job_dir "$1")"
}

strategy_lab_circular_validate_job()
{
    _slcirc_job="$1"
    strategy_lab_job_id_valid "${_slcirc_job}" || return 1
    _slcirc_status=$(strategy_lab_status_file "${_slcirc_job}")
    _slcirc_shortlist=$(strategy_lab_circular_shortlist_file "${_slcirc_job}")
    _slcirc_endpoints=$(strategy_lab_circular_endpoints_file "${_slcirc_job}")
    [ -r "${_slcirc_status}" ] && [ -r "${_slcirc_shortlist}" ] && [ -s "${_slcirc_endpoints}" ] || return 1
    "${STRATEGY_LAB_JQ}" -e '
        .state == "completed" and .target_type == "domain"
    ' "${_slcirc_status}" >/dev/null || return 1
    "${STRATEGY_LAB_JQ}" -e '
        (.count >= 3 and .count <= 5) and
        ((.items | length) == .count) and
        all(.items[]; (.id | type == "string" and length > 0) and
                      (.strategy | type == "string" and length > 0))
    ' "${_slcirc_shortlist}" >/dev/null
}

strategy_lab_circular_inject_strategy()
{
    _slcirc_number="$1"
    _slcirc_strategy_file="$2"
    awk -v number="${_slcirc_number}" '
        /^--lua-desync=/ { print $0 ":strategy=" number }
    ' "${_slcirc_strategy_file}"
}

strategy_lab_circular_build_profile()
{
    _slcirc_job="$1"
    _slcirc_runtime=$(strategy_lab_candidate_runtime_dir "${_slcirc_job}")
    _slcirc_args=$(strategy_lab_candidate_args_file "${_slcirc_job}")
    _slcirc_hostlist=$(strategy_lab_candidate_hostlist_file "${_slcirc_job}")
    _slcirc_shortlist=$(strategy_lab_circular_shortlist_file "${_slcirc_job}")
    _slcirc_endpoints=$(strategy_lab_circular_endpoints_file "${_slcirc_job}")
    _slcirc_tmp="${_slcirc_args}.tmp.$$"
    mkdir -p "${_slcirc_runtime}" || return 1
    cp "${_slcirc_endpoints}" "${_slcirc_hostlist}" || return 1
    chmod 0644 "${_slcirc_hostlist}"
    {
        printf '%s\n' "--port=${STRATEGY_LAB_DIVERT_PORT}"
        if [ -d "${STRATEGY_LAB_LUA_DIR}" ]; then
            find "${STRATEGY_LAB_LUA_DIR}" -maxdepth 1 -type f -name '*.lua' -print 2>/dev/null |
                sort | while IFS= read -r _slcirc_lua
                do
                    printf '%s\n' "--lua-init=@${_slcirc_lua}"
                done
        fi
        printf '%s\n' \
            '--filter-tcp=443' \
            '--filter-l7=tls' \
            '--payload=tls_client_hello' \
            "--hostlist=${_slcirc_hostlist}" \
            '--out-range=-d10' \
            '--in-range=-s34228' \
            '--lua-desync=circular:fails=1:time=60'
        _slcirc_index=0
        while IFS= read -r _slcirc_item
        do
            _slcirc_index=$((_slcirc_index + 1))
            _slcirc_strategy="${_slcirc_runtime}/circular-${_slcirc_index}.args"
            printf '%s' "${_slcirc_item}" | "${STRATEGY_LAB_JQ}" -r '.strategy' > "${_slcirc_strategy}" || exit 1
            strategy_lab_circular_inject_strategy "${_slcirc_index}" "${_slcirc_strategy}" || exit 1
        done <<ITEMS
$("${STRATEGY_LAB_JQ}" -c '.items[]' "${_slcirc_shortlist}")
ITEMS
    } > "${_slcirc_tmp}" || {
        rm -f "${_slcirc_tmp}"
        return 1
    }
    mv -f "${_slcirc_tmp}" "${_slcirc_args}"
    chmod 0644 "${_slcirc_args}"
}

strategy_lab_circular_install_firewall()
{
    _slcirc_addresses="$1"
    _slcirc_wan="$2"
    strategy_lab_firewall_require_ready || return 1
    strategy_lab_firewall_remove_rules
    strategy_lab_firewall_range_empty || return 1
    _slcirc_rule="${STRATEGY_LAB_RULE_BASEM"
    while IFS= read -r _slcirc_address
    do
        [ -n "${_slcirc_address}" ] || continue
        [ $((_slcirc_rule + 1)) -le "${STRATEGY_LAB_RULE_MAX}" ] || {
            strategy_lab_firewall_remove_rules
            return 1
        }
        "${STRATEGY_LAB_IPFW_BIN}" -qf add "${_slcirc_rule}" divert "${STRATEGY_LAB_DIVERT_PORT}" \
            tcp from any to "${_slcirc_address}" 443 out not diverted not sockarg xmit "${_slcirc_wan}" || {
                strategy_lab_firewall_remove_rules
                return 1
            }
        _slcirc_rule=$((_slcirc_rule + 1))
        "${STRATEGY_LAB_IPFW_BIN}" -qf add "${_slcirc_rule}" divert "${STRATEGY_LAB_DIVERT_PORT}" \
            tcp from "${_slcirc_address}" 443 to any in not diverted not sockarg recv "${_slcirc_wan}" || {
                strategy_lab_firewall_remove_rules
                return 1
            }
        _slcirc_rule=$((_slcirc_rule + 1))
    done < "${_slcirc_addresses}"
    strategy_lab_firewall_range_empty && return 1
    return 0
}
