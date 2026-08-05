#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMMON_UNDER_TEST="${COMMON_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/common.sh}"
STATE_UNDER_TEST="${STATE_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/state.sh}"
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

strategy_lab_prepare_directories
strategy_lab_initialize_state job.race example.com standard en

iteration=1
while [ "${iteration}" -le 20 ]
do
    strategy_lab_set_initial_service_state \
        job.race "RUNNING-${iteration}" &
    iteration=$((iteration + 1))
done
wait

status=$(strategy_lab_status_file job.race)
[ "$("${STRATEGY_LAB_JQ}" -r '.revision' "${status}")" -eq 20 ]

strategy_lab_request_cancel job.race cancel &
strategy_lab_update_job job.race completed SUCCESS 99 false done &
wait

"${STRATEGY_LAB_JQ}" -e '
    .state=="completed" and
    .outcome=="SUCCESS" and
    .current_stage=="99" and
    .revision==22
' "${status}" >/dev/null

strategy_lab_request_cancel job.race late
"${STRATEGY_LAB_JQ}" -e '
    .state=="completed" and
    .outcome=="SUCCESS" and
    .current_stage=="99" and
    .revision==23
' "${status}" >/dev/null

strategy_lab_update_stage job.race 50 RUNNING late
"${STRATEGY_LAB_JQ}" -e '
    .state=="completed" and
    .outcome=="SUCCESS" and
    .current_stage=="99" and
    (.stages[] | select(.number=="50") | .status)!="RUNNING" and
    .revision==24
' "${status}" >/dev/null

echo 'PASS: Strategy Lab state updates are serialized and terminal state is irreversible'
