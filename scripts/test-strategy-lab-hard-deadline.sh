#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WATCHDOG_UNDER_TEST="${WATCHDOG_UNDER_TEST:-${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_watchdog.sh}"
ROOT=$(mktemp -d /tmp/strategy-lab-watchdog.XXXXXX)
trap 'rm -rf "${ROOT}"' EXIT HUP INT TERM
STATUS_FILE="${ROOT}/status.json"
CANCEL_FILE="${ROOT}/cancel"
printf '%s\n' '{"current_stage":"50"}' > "${STATUS_FILE}"

STRATEGY_LAB_STANDARD_BUDGET=1
STRATEGY_LAB_EXTENDED_BUDGET=1
MODE=standard
WORKER_FINALIZING=0
STRATEGY_LAB_JQ=$(command -v jq)

worker_error()
{
    echo watchdog-start-error > "${ROOT}/result"
    exit 1
}

worker_stage_timeout()
{
    [ -e "${CANCEL_FILE}" ] || {
        echo cancel-not-requested > "${ROOT}/result"
        exit 1
    }
    echo "$1" > "${ROOT}/result"
    exit 0
}

. "${WATCHDOG_UNDER_TEST}"

while [ ! -e "${ROOT}/result" ]
do
    sleep 1
done

[ "$(cat "${ROOT}/result")" = 50 ]
[ -e "${CANCEL_FILE}" ]

echo 'PASS: Strategy Lab hard deadline records the persisted stage and requests child cancellation'
