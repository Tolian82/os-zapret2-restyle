#!/bin/sh

STRATEGY_LAB_RETENTION_MAX_JOBS="${STRATEGY_LAB_RETENTION_MAX_JOBS:-20}"
STRATEGY_LAB_RETENTION_MAX_CIRCULAR="${STRATEGY_LAB_RETENTION_MAX_CIRCULAR:-20}"

strategy_lab_retention_limit_valid()
{
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$1" -ge 1 ] && [ "$1" -le 1000 ]
}

strategy_lab_retention_sorted_dirs()
{
    _slret_root="$1"
    set -- "${_slret_root}"/job.*
    [ "$1" != "${_slret_root}/job.*" ] || return 0
    ls -1dt "$@" 2>/dev/null || true
}

strategy_lab_retention_automated_deletable()
{
    _slret_job="$1"
    _slret_active="$2"
    _slret_latest="$3"
    strategy_lab_job_id_valid "${_slret_job}" || return 1
    [ "${_slret_job}" != "${_slret_active}" ] || return 1
    [ "${_slret_job}" != "${_slret_latest}" ] || return 1
    _slret_status=$(strategy_lab_status_file "${_slret_job}")
    [ -r "${_slret_status}" ] || return 1
    "${STRATEGY_LAB_JQ}" -e '
        (.state=="completed" or .state=="error") and
        ((.outcome // "") != "RESTORE_FAILED") and
        (.restoration.verified==true)
    ' "${_slret_status}" >/dev/null 2>&1
}

strategy_lab_retention_prune_automated()
{
    strategy_lab_retention_limit_valid "${STRATEGY_LAB_RETENTION_MAX_JOBS}" || return 1
    _slret_active=$(strategy_lab_read_active_job 2>/dev/null || true)
    _slret_latest=$(strategy_lab_read_latest_job 2>/dev/null || true)
    _slret_kept=0

    strategy_lab_retention_sorted_dirs "${STRATEGY_LAB_JOBS_DIR}" |
        while IFS= read -r _slret_dir
        do
            _slret_job=$(basename "${_slret_dir}")
            strategy_lab_retention_automated_deletable "${_slret_job}" \
                "${_slret_active}" "${_slret_latest}" || continue
            _slret_kept=$((_slret_kept + 1))
            [ "${_slret_kept}" -le "${STRATEGY_LAB_RETENTION_MAX_JOBS}" ] && continue
            rm -rf "${_slret_dir}" || exit 1
            rm -f "$(strategy_lab_log_file "${_slret_job}")" || exit 1
        done
}

strategy_lab_retention_circular_deletable()
{
    _slret_session="$1"
    _slret_active="$2"
    _slret_latest="$3"
    strategy_lab_circular_session_id_valid "${_slret_session}" || return 1
    [ "${_slret_session}" != "${_slret_active}" ] || return 1
    [ "${_slret_session}" != "${_slret_latest}" ] || return 1
    _slret_state=$(strategy_lab_circular_session_state_file "${_slret_session}")
    [ -r "${_slret_state}" ] || return 1
    "${STRATEGY_LAB_JQ}" -e '
        (.state=="completed" or .state=="error") and
        (.state!="restore_failed") and
        ((.reason // "") != "RESTORE_FAILED") and
        (
            (.restoration.verified==true) or
            ((.reason // "") as $reason |
                ["lifecycle_lock","launch_failed","owner_unavailable","stale_before_mutation"] |
                index($reason) != null)
        )
    ' "${_slret_state}" >/dev/null 2>&1
}

strategy_lab_retention_prune_circular()
{
    strategy_lab_retention_limit_valid "${STRATEGY_LAB_RETENTION_MAX_CIRCULAR}" || return 1
    _slret_active=$(strategy_lab_circular_active_session_read 2>/dev/null || true)
    _slret_latest=$(strategy_lab_circular_latest_session_read 2>/dev/null || true)
    _slret_kept=0

    strategy_lab_retention_sorted_dirs "${STRATEGY_LAB_CIRCULAR_SESSIONS_DIR}" |
        while IFS= read -r _slret_dir
        do
            _slret_session=$(basename "${_slret_dir}")
            strategy_lab_retention_circular_deletable "${_slret_session}" \
                "${_slret_active}" "${_slret_latest}" || continue
            _slret_kept=$((_slret_kept + 1))
            [ "${_slret_kept}" -le "${STRATEGY_LAB_RETENTION_MAX_CIRCULAR}" ] && continue
            rm -rf "${_slret_dir}" || exit 1
        done
}
