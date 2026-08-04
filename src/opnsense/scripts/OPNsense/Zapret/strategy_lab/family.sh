#!/bin/sh

STRATEGY_LAB_FAMILY_CATALOG="${STRATEGY_LAB_FAMILY_CATALOG:-${MODULE_DIR}/catalog/tls13-families.tsv}"
STRATEGY_LAB_FAMILY_ARGS_DIR="${STRATEGY_LAB_FAMILY_ARGS_DIR:-${MODULE_DIR}/catalog/tls13}"
STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER:-${SCRIPT_DIR}/strategy_lab_candidate_runner.sh}"
STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT="${STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT:-5}"

strategy_lab_family_result_initialize()
{
    _slfri_output="$1"
    "${STRATEGY_LAB_JQ}" -nc \
        '{total:7,completed:0,families:[],accepted:[],rejected:[],all_pass:false}' |
        strategy_lab_atomic_write "${_slfri_output}"
}

strategy_lab_family_result_append()
{
    _slfra_output="$1"
    _slfra_candidate="$2"
    _slfra_tmp=$(mktemp "$(dirname "${_slfra_output}")/.family.XXXXXX") || return 1

    "${STRATEGY_LAB_JQ}" --slurpfile candidate "${_slfra_candidate}" '
        .families += $candidate |
        .completed = (.families | length) |
        .accepted = [.families[] | select(.all_pass == true) | .family] |
        .rejected = [.families[] | select(.all_pass != true) | .family] |
        .all_pass = ((.accepted | length) > 0)
    ' "${_slfra_output}" > "${_slfra_tmp}" || {
        rm -f "${_slfra_tmp}"
        return 1
    }
    chmod 0644 "${_slfra_tmp}"
    mv -f "${_slfra_tmp}" "${_slfra_output}"
}

strategy_lab_family_timeout_result()
{
    _slfrt_id="$1"
    _slfrt_name="$2"
    _slfrt_args="$3"
    _slfrt_output="$4"

    "${STRATEGY_LAB_JQ}" -nc \
        --arg id "${_slfrt_id}" \
        --arg family "${_slfrt_name}" \
        --rawfile strategy "${_slfrt_args}" \
        '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false,timeout:true}' \
        > "${_slfrt_output}"
}

strategy_lab_family_screen()
{
    _slfs_job="$1"
    _slfs_endpoints="$2"
    _slfs_output="$3"
    _slfs_work=$(strategy_lab_job_dir "${_slfs_job}")/family-screening
    _slfs_tab=$(printf '\t')

    [ -r "${STRATEGY_LAB_FAMILY_CATALOG}" ] || return 1
    [ -x "${STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER}" ] || return 1
    mkdir -p "${_slfs_work}" || return 1
    strategy_lab_family_result_initialize "${_slfs_output}" || return 1

    while IFS="${_slfs_tab}" read -r _slfs_id _slfs_name _slfs_hostlist _slfs_args_name
    do
        [ -n "${_slfs_id}" ] || continue
        _slfs_args="${STRATEGY_LAB_FAMILY_ARGS_DIR}/${_slfs_args_name}"
        _slfs_candidate="${_slfs_work}/${_slfs_id}.json"
        [ -r "${_slfs_args}" ] || return 1

        if "${STRATEGY_LAB_TIMEOUT_BIN}" "${STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT}" \
            "${STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER}" \
            "${_slfs_job}" "${_slfs_endpoints}" "${_slfs_candidate}" \
            "${_slfs_id}" "${_slfs_name}" "${_slfs_args}" "${_slfs_hostlist}"
        then
            _slfs_status=0
        else
            _slfs_status=$?
        fi

        case "${_slfs_status}" in
            0)
                [ -r "${_slfs_candidate}" ] || return 1
                ;;
            124)
                strategy_lab_family_timeout_result \
                    "${_slfs_id}" "${_slfs_name}" "${_slfs_args}" \
                    "${_slfs_candidate}" || return 1
                ;;
            *)
                return "${_slfs_status}"
                ;;
        esac

        strategy_lab_family_result_append \
            "${_slfs_output}" "${_slfs_candidate}" || return 1
    done < "${STRATEGY_LAB_FAMILY_CATALOG}"

    [ "$("${STRATEGY_LAB_JQ}" -r '.completed' "${_slfs_output}")" -eq 7 ]
}

strategy_lab_set_candidate_smoke_result()
{
    _slfss_job="$1"
    _slfss_result_file="$2"
    _slfss_status=$(strategy_lab_status_file "${_slfss_job}")
    _slfss_tmp=$(mktemp "$(dirname "${_slfss_status}")/.family-state.XXXXXX") || return 1

    "${STRATEGY_LAB_JQ}" --slurpfile result "${_slfss_result_file}" \
        '.candidate_smoke=$result[0] | .family_screening=$result[0]' \
        "${_slfss_status}" > "${_slfss_tmp}" || {
            rm -f "${_slfss_tmp}"
            return 1
        }
    chmod 0644 "${_slfss_tmp}"
    mv -f "${_slfss_tmp}" "${_slfss_status}"
}
