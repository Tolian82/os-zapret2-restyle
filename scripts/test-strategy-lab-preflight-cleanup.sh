#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PREFLIGHT_UNDER_TEST="${PREFLIGHT_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/preflight.sh}"
TMP=$(mktemp -d /tmp/strategy-lab-preflight.XXXXXX)
CALLS="${TMP}/calls"
SCRIPT_DIR="${TMP}/script"
STRATEGY_LAB_RUN_DIR="${TMP}/run"
export CALLS SCRIPT_DIR STRATEGY_LAB_RUN_DIR
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${SCRIPT_DIR}" "${STRATEGY_LAB_RUN_DIR}"
: > "${CALLS}"

cat > "${SCRIPT_DIR}/strategy_lab_model_b_parallel_adapter.sh" <<'MOCK'
#!/bin/sh
printf 'parallel-%s\n' "${1:-}" >> "${CALLS}"
exit "${PARALLEL_RC:-0}"
MOCK
chmod 0755 "${SCRIPT_DIR}/strategy_lab_model_b_parallel_adapter.sh"

strategy_lab_candidate_stop() { echo candidate-stop >> "${CALLS}"; return "${STOP_RC:-0}"; }
strategy_lab_firewall_remove_rules() { echo firewall-remove >> "${CALLS}"; return "${REMOVE_RC:-0}"; }
strategy_lab_firewall_range_empty() { echo range-empty >> "${CALLS}"; return "${EMPTY_RC:-0}"; }
strategy_lab_candidate_runtime_absent() { echo runtime-absent >> "${CALLS}"; return "${ABSENT_RC:-0}"; }
strategy_lab_update_stage() { echo stage-fail >> "${CALLS}"; }
strategy_lab_append_event() { echo event-fail >> "${CALLS}"; }
strategy_lab_update_job() { echo job-error >> "${CALLS}"; }
strategy_lab_clear_active_job() { echo active-clear >> "${CALLS}"; }

. "${PREFLIGHT_UNDER_TEST}"

strategy_lab_preflight_enforce job.test
[ "$(tr '\n' ' ' < "${CALLS}")" = 'candidate-stop firewall-remove range-empty runtime-absent parallel-cleanup-all ' ]

: > "${CALLS}"
STOP_RC=1
if strategy_lab_preflight_enforce job.test; then
    echo 'preflight unexpectedly succeeded' >&2
    exit 1
fi
grep -q '^stage-fail$' "${CALLS}"
grep -q '^event-fail$' "${CALLS}"
grep -q '^job-error$' "${CALLS}"
grep -q '^active-clear$' "${CALLS}"
! grep -q '^parallel-' "${CALLS}" || {
    echo 'parallel cleanup ran after earlier preflight cleanup failure' >&2
    exit 1
}

: > "${CALLS}"
unset STOP_RC
PARALLEL_RC=1
export PARALLEL_RC
if strategy_lab_preflight_enforce job.test; then
    echo 'preflight unexpectedly succeeded after parallel residue cleanup failure' >&2
    exit 1
fi
grep -q '^parallel-cleanup-all$' "${CALLS}"
grep -q '^stage-fail$' "${CALLS}"
grep -q '^event-fail$' "${CALLS}"
grep -q '^job-error$' "${CALLS}"
grep -q '^active-clear$' "${CALLS}"

echo 'PASS: Strategy Lab removes cold and width-three parallel temporary residue before the baseline'
