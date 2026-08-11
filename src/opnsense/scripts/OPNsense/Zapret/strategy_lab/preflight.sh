#!/bin/sh

strategy_lab_parallel_residue_cleanup()
{
    _slpf_adapter="${SCRIPT_DIR}/strategy_lab_model_b_parallel_adapter.sh"
    [ -x "${_slpf_adapter}" ] || return 0
    _slpf_session="${STRATEGY_LAB_RUN_DIR:-/var/run/zapret2-restyle/strategy-lab}/stage60-parallel/preflight"
    STRATEGY_LAB_MODEL_B_SESSION_DIR="${_slpf_session}" \
        "${_slpf_adapter}" cleanup-all >/dev/null 2>&1
}

strategy_lab_preflight_cleanup()
{
    _slpf_job="$1"

    # The normal cold-candidate range/runtime and the width-three Stage-60 warm-worker
    # identity are both reserved exclusively for Strategy Lab. Residue is removed before
    # a new job starts so a killed prior run cannot poison the next preflight.
    strategy_lab_candidate_stop "${_slpf_job}" || return 1
    strategy_lab_firewall_remove_rules || return 1
    strategy_lab_firewall_range_empty || return 1
    strategy_lab_candidate_runtime_absent || return 1
    strategy_lab_parallel_residue_cleanup || return 1
}

strategy_lab_preflight_enforce()
{
    _slpf_job="$1"
    strategy_lab_preflight_cleanup "${_slpf_job}" && return 0

    strategy_lab_update_stage "${_slpf_job}" 00 FAIL \
        'Strategy Lab could not remove temporary residue from an earlier run.' || true
    strategy_lab_append_event "${_slpf_job}" 00 FAIL \
        'Preflight cleanup failed; automatic tests were not started.' || true
    strategy_lab_update_job "${_slpf_job}" error ERROR 00 false \
        'Strategy Lab preflight cleanup failed.' || true
    strategy_lab_clear_active_job "${_slpf_job}"
    return 1
}
