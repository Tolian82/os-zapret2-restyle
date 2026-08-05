#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PREFLIGHT_UNDER_TEST="${PREFLIGHT_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/preflight.sh}"
CALLS=$(mktemp /tmp/strategy-lab-preflight.XXXXXX)
trap 'rm -f "${CALLS}"' EXIT HUP INT TERM
: > "${CALLS}"

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
[ "$(tr '\n' ' ' < "${CALLS}")" = 'candidate-stop firewall-remove range-empty runtime-absent ' ]

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

echo 'PASS: Strategy Lab removes reserved temporary residue before the baseline'
