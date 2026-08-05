#!/bin/sh

STRATEGY_LAB_CIRCULAR_DIR="${STRATEGY_LAB_CIRCULAR_DIR:-${STRATEGY_LAB_RUN_DIR}/circular}"
STRATEGY_LAB_CIRCULAR_SESSIONS_DIR="${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR:-${STRATEGY_LAB_CIRCULAR_DIR}/sessions}"
STRATEGY_LAB_CIRCULAR_ACTIVE_FILE="${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE:-${STRATEGY_LAB_CIRCULAR_DIR}/active.session}"
STRATEGY_LAB_CIRCULAR_LATEST_FILE="${STRATEGY_LAB_CIRCULAR_LATEST_FILE:-${STRATEGY_LAB_CIRCULAR_DIR}/latest.session}"
STRATEGY_LAB_CIRCULAR_TTL="${STRATEGY_LAB_CIRCULAR_TTL:-300}"
STRATEGY_LAB_PARENT_JOBS_DIR="${STRATEGY_LAB_PARENT_JOBS_DIR:-${STRATEGY_LAB_JOBS_DIR}}"

strategy_lab_circular_prepare_dir()
{
    mkdir -p "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}" || return 1
    chmod 0755 "${STRATEGY_LAB_CIRCULAR_DIR}"
    chmod 0700 "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}"
}

strategy_lab_circular_session_id_valid()
{
    printf '%s\n' "$1" | grep -Eq '^job\.[A-Za-z0-9]+$'
}

strategy_lab_circular_session_dir()
{
    strategy_lab_circular_session_id_valid "$1" || return 1
    printf '%s/%s\n' "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}" "$1"
}

strategy_lab_circular_session_state_file()
{
    printf '%s/state.json\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_session_pid_file()
{
    printf '%s/worker.pid\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_session_stop_file()
{
    printf '%s/stop.request\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_session_log_file()
{
    printf '%s/worker.log\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_session_shortlist_file()
{
    printf '%s/shortlist.json\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_session_endpoints_file()
{
    printf '%s/endpoints.txt\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_session_parent_status_file()
{
    printf '%s/parent-status.json\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_session_parent_file()
{
    printf '%s/parent.job\n' "$(strategy_lab_circular_session_dir "$1")"
}

strategy_lab_circular_parent_job_dir()
{
    printf '%s/%s\n' "${STRATEGY_LAB_PARENT_JOBS_DIR}" "$1"
}

strategy_lab_circular_parent_status_file()
{
    printf '%s/status.json\n' "$(strategy_lab_circular_parent_job_dir "$1")"
}

strategy_lab_circular_parent_shortlist_file()
{
    printf '%s/shortlist.json\n' "$(strategy_lab_circular_parent_job_dir "$1")"
}

strategy_lab_circular_parent_endpoints_file()
{
    printf '%s/endpoints.txt\n' "$(strategy_lab_circular_parent_job_dir "$1")"
}

strategy_lab_circular_pointer_write()
{
    _slcirc_pointer="$1"
    _slcirc_session="$2"
    strategy_lab_circular_session_id_valid "${_slcirc_session}" || return 1
    _slcirc_tmp=$(mktemp "${STRATEGY_LAB_CIRCULAR_DIR}/.pointer.XXXXXX") || return 1
    printf '%s\n' "${_slcirc_session}" > "${_slcirc_tmp}" || {
        rm -f "${_slcirc_tmp}"
        return 1
    }
    chmod 0600 "${_slcirc_tmp}"
    mv -f "${_slcirc_tmp}" "${_slcirc_pointer}"
}

strategy_lab_circular_pointer_read()
{
    _slcirc_pointer="$1"
    [ -r "${_slcirc_pointer}" ] || return 1
    IFS= read -r _slcirc_session < "${_slcirc_pointer}" || return 1
    strategy_lab_circular_session_id_valid "${_slcirc_session}" || return 1
    [ -d "$(strategy_lab_circular_session_dir "${_slcirc_session}")" ] || return 1
    printf '%s\n' "${_slcirc_session}"
}

strategy_lab_circular_active_session_read()
{
    strategy_lab_circular_pointer_read "${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE}"
}

strategy_lab_circular_latest_session_read()
{
    strategy_lab_circular_pointer_read "${STRATEGY_LAB_CIRCULAR_LATEST_FILE}"
}

strategy_lab_circular_active_session_write()
{
    strategy_lab_circular_pointer_write "${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE}" "$1"
}

strategy_lab_circular_latest_session_write()
{
    strategy_lab_circular_pointer_write "${STRATEGY_LAB_CIRCULAR_LATEST_FILE}" "$1"
}

strategy_lab_circular_active_session_clear()
{
    _slcirc_expected="$1"
    _slcirc_current=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
    [ "${_slcirc_current}" = "${_slcirc_expected}" ] && rm -f "${STRATEGY_LAB_CIRCULAR_ACTIVE_FILE}"
    return 0
}

strategy_lab_circular_state_write()
{
    _slcirc_session="$1"
    _slcirc_state="$2"
    _slcirc_parent="$3"
    _slcirc_message="$4"
    _slcirc_count="${5:-0}"
    _slcirc_reason="${6:-}"
    _slcirc_state_file=$(strategy_lab_circular_session_state_file "${_slcirc_session}") || return 1
    _slcirc_now=$(date +%s)
    _slcirc_tmp=$(mktemp "$(dirname "${_slcirc_state_file}")/.state.XXXXXX") || return 1

    if [ -r "${_slcirc_state_file}" ]; then
        "${STRATEGY_LAB_JQ}" \
            --arg state "${_slcirc_state}" \
            --arg session_id "${_slcirc_session}" \
            --arg parent_job_id "${_slcirc_parent}" \
            --arg message "${_slcirc_message}" \
            --arg reason "${_slcirc_reason}" \
            --argjson count "${_slcirc_count}" \
            --argjson now "${_slcirc_now}" '
            .state=$state |
            .session_id=$session_id |
            .parent_job_id=$parent_job_id |
            .job_id=$parent_job_id |
            .message=$message |
            .reason=$reason |
            .candidate_count=$count |
            .updated_at=$now |
            .created_at=(.created_at // $now)
        ' "${_slcirc_state_file}" > "${_slcirc_tmp}" || {
            rm -f "${_slcirc_tmp}"
            return 1
        }
    else
        "${STRATEGY_LAB_JQ}" -nc \
            --arg state "${_slcirc_state}" \
            --arg session_id "${_slcirc_session}" \
            --arg parent_job_id "${_slcirc_parent}" \
            --arg message "${_slcirc_message}" \
            --arg reason "${_slcirc_reason}" \
            --argjson count "${_slcirc_count}" \
            --argjson now "${_slcirc_now}" '
            {state:$state,session_id:$session_id,parent_job_id:$parent_job_id,
             job_id:$parent_job_id,message:$message,reason:$reason,
             candidate_count:$count,created_at:$now,updated_at:$now}
        ' > "${_slcirc_tmp}" || {
            rm -f "${_slcirc_tmp}"
            return 1
        }
    fi
    chmod 0600 "${_slcirc_tmp}"
    mv -f "${_slcirc_tmp}" "${_slcirc_state_file}"
}

strategy_lab_circular_current_state_file()
{
    _slcirc_session=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
    if [ -z "${_slcirc_session}" ]; then
        _slcirc_session=$(strategy_lab_circular_latest_session_read 2>/dev/null || true)
    fi
    [ -n "${_slcirc_session}" ] || return 1
    _slcirc_state=$(strategy_lab_circular_session_state_file "${_slcirc_session}") || return 1
    [ -r "${_slcirc_state}" ] || return 1
    printf '%s\n' "${_slcirc_state}"
}

strategy_lab_circular_session_create()
{
    _slcirc_parent="$1"
    _slcirc_parent_status=$(strategy_lab_circular_parent_status_file "${_slcirc_parent}")
    _slcirc_parent_shortlist=$(strategy_lab_circular_parent_shortlist_file "${_slcirc_parent}")
    _slcirc_parent_endpoints=$(strategy_lab_circular_parent_endpoints_file "${_slcirc_parent}")
    [ -r "${_slcirc_parent_status}" ] || return 1
    [ -r "${_slcirc_parent_shortlist}" ] || return 1
    [ -s "${_slcirc_parent_endpoints}" ] || return 1

    _slcirc_dir=$(mktemp -d "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}/job.XXXXXX") || return 1
    chmod 0700 "${_slcirc_dir}"
    _slcirc_session=$(basename "${_slcirc_dir}")
    cp "${_slcirc_parent_status}" "${_slcirc_dir}/parent-status.json" &&
        cp "${_slcirc_parent_shortlist}" "${_slcirc_dir}/shortlist.json" &&
        cp "${_slcirc_parent_endpoints}" "${_slcirc_dir}/endpoints.txt" &&
        printf '%s\n' "${_slcirc_parent}" > "${_slcirc_dir}/parent.job" || {
            rm -rf "${_slcirc_dir}"
            return 1
        }
    chmod 0600 "${_slcirc_dir}/parent-status.json" \
        "${_slcirc_dir}/shortlist.json" "${_slcirc_dir}/endpoints.txt" \
        "${_slcirc_dir}/parent.job"
    strategy_lab_circular_active_session_write "${_slcirc_session}" &&
        strategy_lab_circular_latest_session_write "${_slcirc_session}" || {
            rm -rf "${_slcirc_dir}"
            return 1
        }
    printf '%s\n' "${_slcirc_session}"
}

strategy_lab_circular_session_parent_read()
{
    _slcirc_parent_file=$(strategy_lab_circular_session_parent_file "$1") || return 1
    [ -r "${_slcirc_parent_file}" ] || return 1
    IFS= read -r _slcirc_parent < "${_slcirc_parent_file}" || return 1
    strategy_lab_job_id_valid "${_slcirc_parent}" || return 1
    printf '%s\n' "${_slcirc_parent}"
}

strategy_lab_circular_session_validate()
{
    _slcirc_session="$1"
    _slcirc_parent="$2"
    strategy_lab_circular_session_id_valid "${_slcirc_session}" || return 1
    [ "$(strategy_lab_circular_session_parent_read "${_slcirc_session}" 2>/dev/null || true)" = "${_slcirc_parent}" ] || return 1
    [ -r "$(strategy_lab_circular_session_parent_status_file "${_slcirc_session}")" ] || return 1
    [ -r "$(strategy_lab_circular_session_shortlist_file "${_slcirc_session}")" ] || return 1
    [ -s "$(strategy_lab_circular_session_endpoints_file "${_slcirc_session}")" ] || return 1
}

strategy_lab_circular_candidate_count()
{
    "${STRATEGY_LAB_JQ}" -r '
        if has("circular_count") then .circular_count
        elif has("circular_items") then (.circular_items | length)
        else (.items | length) end
    ' "$1"
}

strategy_lab_circular_eligibility()
{
    _slcirc_job="$1"
    _slcirc_eligible=false
    _slcirc_reason=invalid_job
    _slcirc_count=0

    if strategy_lab_job_id_valid "${_slcirc_job}"; then
        _slcirc_status=$(strategy_lab_circular_parent_status_file "${_slcirc_job}")
        _slcirc_shortlist=$(strategy_lab_circular_parent_shortlist_file "${_slcirc_job}")
        _slcirc_endpoints=$(strategy_lab_circular_parent_endpoints_file "${_slcirc_job}")
        if [ ! -r "${_slcirc_status}" ]; then
            _slcirc_reason=job_not_found
        elif [ ! -r "${_slcirc_shortlist}" ] || [ ! -s "${_slcirc_endpoints}" ]; then
            _slcirc_reason=artifacts_missing
        else
            _slcirc_count=$(strategy_lab_circular_candidate_count "${_slcirc_shortlist}" 2>/dev/null || printf '%s\n' 0)
            if ! "${STRATEGY_LAB_JQ}" -e '
                .state=="completed" and .outcome=="SUCCESS"
            ' "${_slcirc_status}" >/dev/null; then
                _slcirc_reason=terminal_outcome
            elif ! "${STRATEGY_LAB_JQ}" -e '.target_type=="domain"' \
                "${_slcirc_status}" >/dev/null; then
                _slcirc_reason=domain_required
            elif ! "${STRATEGY_LAB_JQ}" -e '
                any(.stages[]; .number=="85" and .status=="PASS") and
                any(.stages[]; .number=="90" and .status=="PASS") and
                (.restoration.verified==true)
            ' "${_slcirc_status}" >/dev/null; then
                _slcirc_reason=restoration_required
            elif ! "${STRATEGY_LAB_JQ}" -e '
                (.circular_items //
                    [.items[] | . + {protocol:(.protocol // "tls13"),
                                     circular_eligible:(.circular_eligible // true)}]) as $items |
                (($items | length) >= 3 and ($items | length) <= 5) and
                all($items[];
                    .protocol=="tls13" and .circular_eligible==true and
                    (.id | type == "string" and length > 0) and
                    (.strategy | type == "string" and length > 0))
            ' "${_slcirc_shortlist}" >/dev/null; then
                _slcirc_reason=shortlist_size
            elif ! "${STRATEGY_LAB_JQ}" -e --argjson count "${_slcirc_count}" '
                .circular_eligible==true and
                .circular_eligibility_reason=="eligible" and
                .circular_candidate_count==$count
            ' "${_slcirc_status}" >/dev/null; then
                _slcirc_reason=eligibility_not_persisted
            else
                _slcirc_eligible=true
                _slcirc_reason=eligible
            fi
        fi
    fi

    "${STRATEGY_LAB_JQ}" -nc \
        --arg job_id "${_slcirc_job}" \
        --argjson eligible "${_slcirc_eligible}" \
        --arg reason "${_slcirc_reason}" \
        --argjson count "${_slcirc_count}" \
        '{status:(if $eligible then "ok" else "error" end),job_id:$job_id,
          circular_eligible:$eligible,reason:$reason,candidate_count:$count}'
    [ "${_slcirc_eligible}" = true ]
}

strategy_lab_circular_validate_job()
{
    strategy_lab_circular_eligibility "$1" >/dev/null
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
    _slcirc_session="$1"
    _slcirc_runtime=$(strategy_lab_candidate_runtime_dir "${_slcirc_session}")
    _slcirc_args=$(strategy_lab_candidate_args_file "${_slcirc_session}")
    _slcirc_hostlist=$(strategy_lab_candidate_hostlist_file "${_slcirc_session}")
    _slcirc_shortlist=$(strategy_lab_circular_session_shortlist_file "${_slcirc_session}")
    _slcirc_endpoints=$(strategy_lab_circular_session_endpoints_file "${_slcirc_session}")
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
$("${STRATEGY_LAB_JQ}" -c '(.circular_items // .items)[]' "${_slcirc_shortlist}")
ITEMS
    } > "${_slcirc_tmp}" || {
        rm -f "${_slcirc_tmp}"
        return 1
    }
    mv -f "${_slcirc_tmp}" "${_slcirc_args}"
    chmod 0600 "${_slcirc_args}"
}

strategy_lab_circular_install_firewall()
{
    _slcirc_addresses="$1"
    _slcirc_wan="$2"
    strategy_lab_firewall_require_ready || return 1
    strategy_lab_firewall_remove_rules
    strategy_lab_firewall_range_empty || return 1
    _slcirc_rule="${STRATEGY_LAB_RULE_BASE}"
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
