#!/bin/sh

STRATEGY_LAB_STATE_LOCKF_BIN="${STRATEGY_LAB_STATE_LOCKF_BIN:-/usr/bin/lockf}"
STRATEGY_LAB_STATE_FLOCK_BIN="${STRATEGY_LAB_STATE_FLOCK_BIN:-$(command -v flock 2>/dev/null || true)}"
STRATEGY_LAB_STATE_LOCK_TIMEOUT="${STRATEGY_LAB_STATE_LOCK_TIMEOUT:-10}"

strategy_lab_state_lock_file()
{
    printf '%s/status.lock\n' "$(strategy_lab_job_dir "$1")"
}

strategy_lab_state_lock_acquire()
{
    if [ -x "${STRATEGY_LAB_STATE_LOCKF_BIN}" ]; then
        "${STRATEGY_LAB_STATE_LOCKF_BIN}" -s -t \
            "${STRATEGY_LAB_STATE_LOCK_TIMEOUT}" 9
        return $?
    fi
    if [ -n "${STRATEGY_LAB_STATE_FLOCK_BIN}" ] &&
       [ -x "${STRATEGY_LAB_STATE_FLOCK_BIN}" ]; then
        "${STRATEGY_LAB_STATE_FLOCK_BIN}" -x -w \
            "${STRATEGY_LAB_STATE_LOCK_TIMEOUT}" 9
        return $?
    fi
    return 1
}

strategy_lab_state_transform()
{
    _strategy_lab_transform_job="$1"
    _strategy_lab_transform_filter="$2"
    shift 2
    _strategy_lab_transform_status=$(strategy_lab_status_file "${_strategy_lab_transform_job}")
    _strategy_lab_transform_lock=$(strategy_lab_state_lock_file "${_strategy_lab_transform_job}")

    [ -r "${_strategy_lab_transform_status}" ] || return 1

    (
        strategy_lab_state_lock_acquire || exit 75
        _strategy_lab_transform_tmp=$(mktemp \
            "$(dirname "${_strategy_lab_transform_status}")/.state.XXXXXX") || exit 1
        "${STRATEGY_LAB_JQ}" "$@" \
            "(${_strategy_lab_transform_filter}) | .revision=((.revision // 0)+1)" \
            "${_strategy_lab_transform_status}" > "${_strategy_lab_transform_tmp}" || {
                rm -f "${_strategy_lab_transform_tmp}"
                exit 1
            }
        chmod 0644 "${_strategy_lab_transform_tmp}"
        mv -f "${_strategy_lab_transform_tmp}" "${_strategy_lab_transform_status}"
    ) 9>"${_strategy_lab_transform_lock}"
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

    mkdir -p "${_strategy_lab_jobdir}" || return 1
    "${STRATEGY_LAB_JQ}" -nc \
        --arg job_id "${_strategy_lab_job}" \
        --arg target "${_strategy_lab_target}" \
        --arg mode "${_strategy_lab_mode}" \
        --arg language "${_strategy_lab_language}" '
        {
            schema:2,
            revision:0,
            job_id:$job_id,
            state:"queued",
            outcome:"",
            target:$target,
            target_type:"",
            endpoints:[],
            network:{},
            baseline:{},
            candidate_smoke:{},
            family_screening:{},
            parameter_expansion:{},
            stability:{},
            shortlist:{},
            extended:{},
            quic:{},
            udp:{},
            mode:$mode,
            language:$language,
            initial_service_state:"",
            cancel_requested:false,
            cancel_requested_at:"",
            current_stage:"00",
            message:"",
            progress:{percent:0,stage:"00",stage_key:"target_initialization",message:""},
            circular_eligible:false,
            circular_eligibility_reason:"not_completed",
            circular_candidate_count:0,
            stages:[
                {number:"00",key:"target_initialization",status:"PENDING",message:""},
                {number:"10",key:"lifecycle_snapshot",status:"PENDING",message:""},
                {number:"20",key:"service_stop",status:"PENDING",message:""},
                {number:"30",key:"network_precheck",status:"PENDING",message:""},
                {number:"40",key:"clean_baseline",status:"PENDING",message:""},
                {number:"50",key:"family_screening",status:"PENDING",message:""},
                {number:"60",key:"family_expansion",status:"PENDING",message:""},
                {number:"70",key:"stability",status:"PENDING",message:""},
                {number:"80",key:"extended",status:"PENDING",message:""},
                {number:"85",key:"shortlist",status:"PENDING",message:""},
                {number:"90",key:"restore",status:"PENDING",message:""},
                {number:"99",key:"report",status:"PENDING",message:""}
            ]
        }' | strategy_lab_atomic_write "${_strategy_lab_status}" || return 1
    : > "${_strategy_lab_events}" || return 1
    chmod 0644 "${_strategy_lab_events}"
}

strategy_lab_set_target_contract()
{
    _strategy_lab_job="$1"
    _strategy_lab_target="$2"
    _strategy_lab_type="$3"
    _strategy_lab_endpoints_file="$4"
    _strategy_lab_endpoints_json=$("${STRATEGY_LAB_JQ}" -Rsc 'split("\n") | map(select(length > 0))' "${_strategy_lab_endpoints_file}") || return 1
    strategy_lab_state_transform "${_strategy_lab_job}" '.target=$target | .target_type=$target_type | .endpoints=$endpoints' \
      --arg target "${_strategy_lab_target}" --arg target_type "${_strategy_lab_type}" --argjson endpoints "${_strategy_lab_endpoints_json}"
}

strategy_lab_set_network_capabilities(){ strategy_lab_state_transform "$1" '.network=$network[0]' --slurpfile network "$2"; }
strategy_lab_set_baseline_result(){ strategy_lab_state_transform "$1" '.baseline=$baseline[0]' --slurpfile baseline "$2"; }
strategy_lab_set_candidate_smoke_result()
{
    strategy_lab_state_transform "$1" '.candidate_smoke=$candidate[0] | .family_screening=$candidate[0]' --slurpfile candidate "$2"
}

strategy_lab_request_cancel()
{
    _strategy_lab_job="$1"; _strategy_lab_message="$2"; _strategy_lab_requested_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    strategy_lab_state_transform "${_strategy_lab_job}" '
        if (.state=="completed" or .state=="error") then .
        elif (.state=="queued" or .state=="running" or .state=="cancel_requested") then
            .state="cancel_requested" | .cancel_requested=true |
            .cancel_requested_at=(if ((.cancel_requested_at // "")|length)>0 then .cancel_requested_at else $requested_at end) |
            .message=$message | .progress.message=$message
        else . end
    ' --arg requested_at "${_strategy_lab_requested_at}" --arg message "${_strategy_lab_message}"
}

strategy_lab_update_job()
{
    _strategy_lab_job="$1"; _strategy_lab_state="$2"; _strategy_lab_outcome="$3"; _strategy_lab_stage="$4"; _strategy_lab_canceled="$5"; _strategy_lab_message="$6"
    strategy_lab_state_transform "${_strategy_lab_job}" '
        def progress_percent($stage): {"00":0,"10":9,"20":18,"30":27,"40":36,"50":45,"60":55,"70":64,"80":73,"85":82,"90":91,"99":100}[$stage] // 0;
        if (.state=="completed" or .state=="error") then . else
            (.cancel_requested // false) as $existing_cancel |
            .state=(if $existing_cancel and ($state=="queued" or $state=="running") then "cancel_requested" else $state end) |
            .outcome=$outcome | .current_stage=$stage | .cancel_requested=($existing_cancel or $canceled) |
            .message=$message | .progress.percent=progress_percent($stage) | .progress.stage=$stage |
            .progress.stage_key=([.stages[]|select(.number==$stage)|.key][0] // "") | .progress.message=$message
        end
    ' --arg state "${_strategy_lab_state}" --arg outcome "${_strategy_lab_outcome}" --arg stage "${_strategy_lab_stage}" --argjson canceled "${_strategy_lab_canceled}" --arg message "${_strategy_lab_message}"
}

strategy_lab_set_initial_service_state(){ strategy_lab_state_transform "$1" '.initial_service_state=$service_state' --arg service_state "$2"; }

strategy_lab_update_stage()
{
    _strategy_lab_job="$1"; _strategy_lab_number=$(printf '%02d' "$2"); _strategy_lab_stage_status="$3"; _strategy_lab_message="$4"
    strategy_lab_state_transform "${_strategy_lab_job}" '
        def progress_percent($stage): {"00":0,"10":9,"20":18,"30":27,"40":36,"50":45,"60":55,"70":64,"80":73,"85":82,"90":91,"99":100}[$stage] // 0;
        if (.state=="completed" or .state=="error") then . else
            (.stages[]|select(.number==$number)|.status)=$status |
            (.stages[]|select(.number==$number)|.message)=$message |
            .current_stage=$number | .progress.percent=progress_percent($number) | .progress.stage=$number |
            .progress.stage_key=([.stages[]|select(.number==$number)|.key][0] // "") | .progress.message=$message
        end
    ' --arg number "${_strategy_lab_number}" --arg status "${_strategy_lab_stage_status}" --arg message "${_strategy_lab_message}"
}

strategy_lab_append_event()
{
    _strategy_lab_job="$1"; _strategy_lab_stage=$(printf '%02d' "$2"); _strategy_lab_status_value="$3"; _strategy_lab_message="$4"
    _strategy_lab_events=$(strategy_lab_event_file "${_strategy_lab_job}"); _strategy_lab_lock=$(strategy_lab_state_lock_file "${_strategy_lab_job}")
    (
        strategy_lab_state_lock_acquire || exit 75
        "${STRATEGY_LAB_JQ}" -nc --arg stage "${_strategy_lab_stage}" --arg status "${_strategy_lab_status_value}" --arg message "${_strategy_lab_message}" '{stage:$stage,status:$status,message:$message}' >> "${_strategy_lab_events}"
    ) 9>"${_strategy_lab_lock}"
}
