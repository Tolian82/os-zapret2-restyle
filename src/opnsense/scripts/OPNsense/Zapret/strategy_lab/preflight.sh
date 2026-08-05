#!/bin/sh

strategy_lab_preflight_cleanup()
{
    _slpf_job="$1"

    # The range and divert port are reserved exclusively for Strategy Lab.
    # Residue is removed destructively; foreign-rule ownership is not tracked.
    strategy_lab_candidate_stop "${_slpf_job}" || return 1
    strategy_lab_firewall_remove_rules || return 1
    strategy_lab_firewall_range_empty || return 1
    strategy_lab_candidate_runtime_absent || return 1
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
