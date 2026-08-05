#!/bin/sh

strategy_lab_state_lock_acquire()
{
    _strategy_lab_lock_status="$1"
    _strategy_lab_lock_dir="${_strategy_lab_lock_status}.lock"
    _strategy_lab_lock_attempt=0

    while ! mkdir "${_strategy_lab_lock_dir}" 2>/dev/null
    do
        _strategy_lab_lock_owner=""
        if [ -r "${_strategy_lab_lock_dir}/owner" ]; then
            IFS= read -r _strategy_lab_lock_owner < "${_strategy_lab_lock_dir}/owner" || true
        fi
        case "${_strategy_lab_lock_owner}" in
            ''|*[!0-9]*)
                ;;
            *)
                if ! kill -0 "${_strategy_lab_lock_owner}" 2>/dev/null; then
                    rm -rf "${_strategy_lab_lock_dir}"
                    continue
                fi
                ;;
        esac
        _strategy_lab_lock_attempt=$((_strategy_lab_lock_attempt + 1))
        [ "${_strategy_lab_lock_attempt}" -lt 100 ] || return 1
        sleep 0.05
    done

    printf '%s\n' "$$" > "${_strategy_lab_lock_dir}/owner" || {
        rm -rf "${_strategy_lab_lock_dir}"
        return 1
    }
}

strategy_lab_state_lock_release()
{
    rm -rf "${1}.lock"
}

strategy_lab_state_apply()
{
    _strategy_lab_apply_status="$1"
    _strategy_lab_apply_prefix="$2"
    shift 2

    strategy_lab_state_lock_acquire "${_strategy_lab_apply_status}" || return 1
    _strategy_lab_apply_tmp=$(mktemp "$(dirname "${_strategy_lab_apply_status}")/.${_strategy_lab_apply_prefix}.XXXXXX") || {
        strategy_lab_state_lock_release "${_strategy_lab_apply_status}"
        return 1
    }

    _strategy_lab_apply_result=0
    "$@" > "${_strategy_lab_apply_tmp}" || _strategy_lab_apply_result=$?
    if [ "${_strategy_lab_apply_result}" -eq 0 ]; then
        chmod 0644 "${_strategy_lab_apply_tmp}" || _strategy_lab_apply_result=$?
    fi
    if [ "${_strategy_lab_apply_result}" -eq 0 ]; then
        mv -f "${_strategy_lab_apply_tmp}" "${_strategy_lab_apply_status}" || _strategy_lab_apply_result=$?
    fi
    if [ "${_strategy_lab_apply_result}" -ne 0 ]; then
        rm -f "${_strategy_lab_apply_tmp}"
    fi
    strategy_lab_state_lock_release "${_strategy_lab_apply_status}"
    return "${_strategy_lab_apply_result}"
}

strategy_lab_initialize_state()
{
    _strategy_lab_job="$1"
    _strategy_lab_target="$2"
    _strategy_lab_mode="$3"
    _strategy_lab_language="$4"
    _strategy_lab_jobdir=$(strategy_lab_job_dir "${_strategy_lab_job}")
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    _strategy_lab_events=$(strategy_lab_event_file "${_strategy_lab_job}")

    mkdir -p "${_strategy_lab_jobdir}"
    : > "${_strategy_lab_events}"

    "${STRATEGY_LAB_JQ}" -nc \
        --arg job_id "${_strategy_lab_job}" \
        --arg target "${_strategy_lab_target}" \
        --arg mode "${_strategy_lab_mode}" \
        --arg language "${_strategy_lab_language}" \
        '{
            schema: 2,
            job_id: $job_id,
            state: "queued",
            outcome: "",
            target: $target,
            target_type: "",
            endpoints: [],
            network: {},
            baseline: {},
            candidate_smoke: {},
            mode: $mode,
            language: $language,
            initial_service_state: "",
            cancel_requested: false,
            cancel_requested_at: "",
            current_stage: "00",
            message: "",
            stages: [
                {number:"00", key:"target_initialization", status:"PENDING", message:""},
                {number:"10", key:"lifecycle_snapshot", status:"PENDING", message:""},
                {number:"20", key:"service_stop", status:"PENDING", message:""},
                {number:"30", key:"network_precheck", status:"PENDING", message:""},
                {number:"40", key:"clean_baseline", status:"PENDING", message:""},
                {number:"50", key:"family_screening", status:"PENDING", message:""},
                {number:"60", key:"family_expansion", status:"PENDING", message:""},
                {number:"70", key:"stability", status:"PENDING", message:""},
                {number:"80", key:"extended", status:"PENDING", message:""},
                {number:"85", key:"shortlist", status:"PENDING", message:""},
                {number:"90", key:"restore", status:"PENDING", message:""},
                {number:"99", key:"report", status:"PENDING", message:""}
            ]
        }' | strategy_lab_atomic_write "${_strategy_lab_status}"
}

strategy_lab_set_target_contract()
{
    _strategy_lab_job="$1"
    _strategy_lab_target="$2"
    _strategy_lab_type="$3"
    _strategy_lab_endpoints_file="$4"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    _strategy_lab_endpoints_json=$("${STRATEGY_LAB_JQ}" -Rsc 'split("\n") | map(select(length > 0))' "${_strategy_lab_endpoints_file}") || return 1

    strategy_lab_state_apply "${_strategy_lab_status}" target-contract \
        "${STRATEGY_LAB_JQ}" \
        --arg target "${_strategy_lab_target}" \
        --arg target_type "${_strategy_lab_type}" \
        --argjson endpoints "${_strategy_lab_endpoints_json}" \
        '.target=$target | .target_type=$target_type | .endpoints=$endpoints' \
        "${_strategy_lab_status}"
}

strategy_lab_set_network_capabilities()
{
    _strategy_lab_job="$1"
    _strategy_lab_network_file="$2"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")

    strategy_lab_state_apply "${_strategy_lab_status}" network \
        "${STRATEGY_LAB_JQ}" --slurpfile network "${_strategy_lab_network_file}" \
        '.network=$network[0]' "${_strategy_lab_status}"
}

strategy_lab_set_baseline_result()
{
    _strategy_lab_job="$1"
    _strategy_lab_baseline_file="$2"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")

    strategy_lab_state_apply "${_strategy_lab_status}" baseline \
        "${STRATEGY_LAB_JQ}" --slurpfile baseline "${_strategy_lab_baseline_file}" \
        '.baseline=$baseline[0]' "${_strategy_lab_status}"
}

strategy_lab_set_candidate_smoke_result()
{
    _strategy_lab_job="$1"
    _strategy_lab_candidate_file="$2"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")

    strategy_lab_state_apply "${_strategy_lab_status}" candidate-smoke \
        "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_strategy_lab_candidate_file}" \
        '.candidate_smoke=$candidate[0]' "${_strategy_lab_status}"
}

strategy_lab_request_cancel()
{
    _strategy_lab_job="$1"
    _strategy_lab_message="$2"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")
    _strategy_lab_requested_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    strategy_lab_state_apply "${_strategy_lab_status}" cancel-state \
        "${STRATEGY_LAB_JQ}" \
        --arg requested_at "${_strategy_lab_requested_at}" \
        --arg message "${_strategy_lab_message}" \
        'if (.state=="queued" or .state=="running" or .state=="cancel_requested") then
             .state="cancel_requested" |
             .cancel_requested=true |
             .cancel_requested_at=(if ((.cancel_requested_at // "") | length) > 0 then .cancel_requested_at else $requested_at end) |
             .message=$message
         else . end' \
        "${_strategy_lab_status}"
}

strategy_lab_update_job()
{
    _strategy_lab_job="$1"
    _strategy_lab_state="$2"
    _strategy_lab_outcome="$3"
    _strategy_lab_stage="$4"
    _strategy_lab_canceled="$5"
    _strategy_lab_message="$6"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")

    strategy_lab_state_apply "${_strategy_lab_status}" job \
        "${STRATEGY_LAB_JQ}" \
        --arg state "${_strategy_lab_state}" \
        --arg outcome "${_strategy_lab_outcome}" \
        --arg stage "${_strategy_lab_stage}" \
        --argjson canceled "${_strategy_lab_canceled}" \
        --arg message "${_strategy_lab_message}" \
        '(.cancel_requested // false) as $existing_cancel |
         .state=(if $existing_cancel and ($state=="queued" or $state=="running") then "cancel_requested" else $state end) |
         .outcome=$outcome | .current_stage=$stage |
         .cancel_requested=($existing_cancel or $canceled) | .message=$message' \
        "${_strategy_lab_status}"
}

strategy_lab_set_initial_service_state()
{
    _strategy_lab_job="$1"
    _strategy_lab_service_state="$2"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")

    strategy_lab_state_apply "${_strategy_lab_status}" service-state \
        "${STRATEGY_LAB_JQ}" \
        --arg service_state "${_strategy_lab_service_state}" \
        '.initial_service_state=$service_state' \
        "${_strategy_lab_status}"
}

strategy_lab_update_stage()
{
    _strategy_lab_job="$1"
    _strategy_lab_number="$2"
    _strategy_lab_stage_status="$3"
    _strategy_lab_message="$4"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")

    strategy_lab_state_apply "${_strategy_lab_status}" stage \
        "${STRATEGY_LAB_JQ}" \
        --arg number "${_strategy_lab_number}" \
        --arg status "${_strategy_lab_stage_status}" \
        --arg message "${_strategy_lab_message}" \
        '(.stages[] | select(.number==$number) | .status)=$status |
         (.stages[] | select(.number==$number) | .message)=$message |
         .current_stage=$number' \
        "${_strategy_lab_status}"
}

strategy_lab_skip_unfinished()
{
    _strategy_lab_job="$1"
    _strategy_lab_message="$2"
    _strategy_lab_status=$(strategy_lab_status_file "${_strategy_lab_job}")

    strategy_lab_state_apply "${_strategy_lab_status}" skip \
        "${STRATEGY_LAB_JQ}" \
        --arg message "${_strategy_lab_message}" \
        '(.stages[] | select((.status=="PENDING" or .status=="RUNNING") and .number!="90" and .number!="99") | .status)="SKIPPED" |
         (.stages[] | select(.status=="SKIPPED" and .message=="") | .message)=$message' \
        "${_strategy_lab_status}"
}

strategy_lab_append_event()
{
    _strategy_lab_job="$1"
    _strategy_lab_stage="$2"
    _strategy_lab_status_value="$3"
    _strategy_lab_message="$4"
    _strategy_lab_events=$(strategy_lab_event_file "${_strategy_lab_job}")

    "${STRATEGY_LAB_JQ}" -nc \
        --arg stage "${_strategy_lab_stage}" \
        --arg status "${_strategy_lab_status_value}" \
        --arg message "${_strategy_lab_message}" \
        '{stage:$stage,status:$status,message:$message}' >> "${_strategy_lab_events}"
}
