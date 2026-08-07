#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMMON_UNDER_TEST="${COMMON_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/common.sh}"
STATE_UNDER_TEST="${STATE_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/state.sh}"
STAGE_MACHINE_UNDER_TEST="${STAGE_MACHINE_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_stage_machine.sh}"
ROOT=$(mktemp -d /tmp/strategy-lab-state-race.XXXXXX)
trap 'rm -rf "${ROOT}"' EXIT HUP INT TERM

STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_RUN_DIR="${ROOT}/run"
STRATEGY_LAB_JOBS_DIR="${STRATEGY_LAB_RUN_DIR}/jobs"
STRATEGY_LAB_LOG_DIR="${ROOT}/log"
export STRATEGY_LAB_JQ STRATEGY_LAB_RUN_DIR STRATEGY_LAB_JOBS_DIR
export STRATEGY_LAB_LOG_DIR

if command -v lockf >/dev/null 2>&1; then
    STRATEGY_LAB_STATE_LOCKF_BIN=$(command -v lockf)
else
    FLOCK_BIN=$(command -v flock)
    cat > "${ROOT}/lockf" <<EOS
#!/bin/sh
while [ "\$#" -gt 0 ]
do
    case "\$1" in
        -s) shift ;;
        -t) shift 2 ;;
        9) shift; break ;;
        *) shift ;;
    esac
done
exec "${FLOCK_BIN}" -x 9
EOS
    chmod +x "${ROOT}/lockf"
    STRATEGY_LAB_STATE_LOCKF_BIN="${ROOT}/lockf"
fi
export STRATEGY_LAB_STATE_LOCKF_BIN

. "${COMMON_UNDER_TEST}"
. "${STATE_UNDER_TEST}"
. "${STAGE_MACHINE_UNDER_TEST}"

strategy_lab_prepare_directories
strategy_lab_initialize_state job.race example.com standard en
status=$(strategy_lab_status_file job.race)

iteration=1
while [ "${iteration}" -le 20 ]
do
    strategy_lab_set_initial_service_state job.race "RUNNING-${iteration}" &
    iteration=$((iteration + 1))
done
wait
[ "$("${STRATEGY_LAB_JQ}" -r '.revision' "${status}")" -eq 20 ]

strategy_lab_update_stage job.race 60 RUNNING active
[ "$("${STRATEGY_LAB_JQ}" -r '.revision' "${status}")" -eq 21 ]

# This is the third-audit regression: cancel persistence and unfinished-stage skipping
# mutate the same status document concurrently and therefore must share one state lock.
strategy_lab_request_cancel job.race cancel &
worker_skip_unfinished job.race skipped &
wait

"${STRATEGY_LAB_JQ}" -e '
    .state=="cancel_requested" and
    .cancel_requested==true and
    ((.cancel_requested_at // "")|length)>0 and
    (.stages[] | select(.number=="60") | .status)=="SKIPPED" and
    (.stages[] | select(.number=="90") | .status)=="PENDING" and
    (.stages[] | select(.number=="99") | .status)=="PENDING" and
    .revision==23
' "${status}" >/dev/null
cancel_at=$("${STRATEGY_LAB_JQ}" -r '.cancel_requested_at' "${status}")

# Repeated cancel is idempotent in value while still being a serialized revisioned write.
worker_skip_unfinished job.race skipped-again &
strategy_lab_request_cancel job.race cancel-again &
wait
"${STRATEGY_LAB_JQ}" -e --arg requested_at "${cancel_at}" '
    .state=="cancel_requested" and
    .cancel_requested==true and
    .cancel_requested_at==$requested_at and
    .revision==25
' "${status}" >/dev/null

strategy_lab_update_job job.race completed PARTIAL 99 true done
"${STRATEGY_LAB_JQ}" -e --arg requested_at "${cancel_at}" '
    .state=="completed" and
    .outcome=="PARTIAL" and
    .current_stage=="99" and
    .cancel_requested==true and
    .cancel_requested_at==$requested_at and
    .revision==26
' "${status}" >/dev/null

strategy_lab_request_cancel job.race late
strategy_lab_update_stage job.race 50 RUNNING late
"${STRATEGY_LAB_JQ}" -e --arg requested_at "${cancel_at}" '
    .state=="completed" and
    .outcome=="PARTIAL" and
    .current_stage=="99" and
    .cancel_requested_at==$requested_at and
    (.stages[] | select(.number=="50") | .status)!="RUNNING" and
    .revision==28
' "${status}" >/dev/null

# The worker path must not reintroduce a private read/jq/mv writer.
grep -Fq 'strategy_lab_state_transform "${_wsm_job}"' "${STAGE_MACHINE_UNDER_TEST}"
! grep -Fq '.worker-skip.' "${STAGE_MACHINE_UNDER_TEST}"

"${STRATEGY_LAB_JQ}" -e . "${status}" >/dev/null

echo 'PASS: cancel, skip, and finalization state updates share the canonical lock/revision transform and preserve cancellation evidence'
