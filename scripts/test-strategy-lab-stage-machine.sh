#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODULE="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_stage_machine.sh"
WORKER="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"
FLOW="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_flow.sh"
CONTROL="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/worker_control.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-stage-machine.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

mkdir -p "${TEST_ROOT}/job"
CANCEL_FILE="${TEST_ROOT}/cancel"
rm -f "${CANCEL_FILE}"

STRATEGY_LAB_JQ=$(command -v jq)
STRATEGY_LAB_TIMEOUT_BIN="${TEST_ROOT}/timeout"
JOB_ID=job.TEST
JOB_DIR="${TEST_ROOT}/job"
LANGUAGE=en
STRATEGY_LAB_STAGE60_TIMEOUT=60
STRATEGY_LAB_STAGE70_TIMEOUT=60
STRATEGY_LAB_STAGE80_TIMEOUT=120
export STRATEGY_LAB_JQ

cat > "${STRATEGY_LAB_TIMEOUT_BIN}" <<'TIMEOUT'
#!/bin/sh
shift
exec "$@"
TIMEOUT
cat > "${TEST_ROOT}/expansion" <<'RUNNER'
#!/bin/sh
printf '%s\n' '{"working":["x"],"completed":1}' > "$4"
RUNNER
cat > "${TEST_ROOT}/stability" <<'RUNNER'
#!/bin/sh
printf '%s\n' '{"stable":["x"],"completed":1,"candidates":[{"id":"x","family":"f","strategy":"--x","stable":true,"line_count":1,"character_count":3}]}' > "$5"
RUNNER
cat > "${TEST_ROOT}/extended" <<'RUNNER'
#!/bin/sh
printf '%s\n' '{"protocols":{"tls12":{"working":null},"http":{"working":null}}}' > "$3"
RUNNER
cat > "${TEST_ROOT}/quic" <<'RUNNER'
#!/bin/sh
printf '%s\n' '{"status":"skipped"}' > "$4"
RUNNER
cat > "${TEST_ROOT}/udp" <<'RUNNER'
#!/bin/sh
printf '%s\n' '{"status":"skipped"}' > "$3"
RUNNER
chmod 0755 "${STRATEGY_LAB_TIMEOUT_BIN}" "${TEST_ROOT}/expansion" \
    "${TEST_ROOT}/stability" "${TEST_ROOT}/extended" \
    "${TEST_ROOT}/quic" "${TEST_ROOT}/udp"

EXPANSION_RUNNER="${TEST_ROOT}/expansion"
STABILITY_RUNNER="${TEST_ROOT}/stability"
EXTENDED_RUNNER="${TEST_ROOT}/extended"
QUIC_RUNNER="${TEST_ROOT}/quic"
UDP_RUNNER="${TEST_ROOT}/udp"

strategy_lab_update_stage()
{
    printf '%s %s\n' "$2" "$3" >> "${TEST_ROOT}/order"
}
strategy_lab_append_event(){ :; }
strategy_lab_set_parameter_expansion_result(){ :; }
strategy_lab_set_extended_result(){ :; }
strategy_lab_set_quic_result(){ :; }
strategy_lab_set_udp_result(){ :; }
strategy_lab_set_stability_result(){ :; }
strategy_lab_status_file(){ printf '%s\n' "${TEST_ROOT}/status.json"; }
worker_cancel(){ fail 'unexpected cancellation'; }
worker_error(){ fail "worker_error $*"; }
worker_stage_timeout(){ fail "worker_stage_timeout $*"; }
strategy_lab_shortlist_build()
{
    printf '%s\n' '{"count":1,"items":[{"id":"x"}],"recommendation":{"id":"x"}}' > "$2"
}

printf '%s\n' '{"stages":[]}' > "${TEST_ROOT}/status.json"
printf '%s\n' example.com > "${JOB_DIR}/endpoints.txt"
printf '%s\n' '{}' > "${JOB_DIR}/candidate-smoke.json"
printf '%s\n' '{}' > "${JOB_DIR}/network.json"

. "${MODULE}"

MODE=standard
: > "${TEST_ROOT}/order"
worker_run_search_stages
cat > "${TEST_ROOT}/expected-standard" <<'EXPECTED'
60 RUNNING
60 PASS
70 RUNNING
70 PASS
80 SKIPPED
85 RUNNING
85 PASS
EXPECTED
cmp -s "${TEST_ROOT}/expected-standard" "${TEST_ROOT}/order" || {
    cat "${TEST_ROOT}/order" >&2
    fail 'standard stage order is not monotonic'
}

MODE=extended
rm -f "${JOB_DIR}/parameter-expansion.json" "${JOB_DIR}/stability.json" \
    "${JOB_DIR}/shortlist.json" "${JOB_DIR}/extended-tcp.json" \
    "${JOB_DIR}/quic.json" "${JOB_DIR}/udp.json"
: > "${TEST_ROOT}/order"
worker_run_search_stages
cat > "${TEST_ROOT}/expected-extended" <<'EXPECTED'
60 RUNNING
60 PASS
70 RUNNING
70 PASS
80 RUNNING
80 PASS
85 RUNNING
85 PASS
EXPECTED
cmp -s "${TEST_ROOT}/expected-extended" "${TEST_ROOT}/order" || {
    cat "${TEST_ROOT}/order" >&2
    fail 'extended stage order is not monotonic'
}

! grep -Fq 'strategy_lab_skip_unfinished' "${FLOW}" ||
    fail 'worker flow still invokes the load-order hook'
! grep -Fq 'strategy_lab_skip_unfinished' "${CONTROL}" ||
    fail 'worker control still invokes the load-order hook'
! grep -Fq 'strategy_lab_skip_remaining' "${FLOW}" ||
    fail 'worker flow still invokes the remaining-stage hook'
grep -Fq 'worker_run_search_stages' "${FLOW}" ||
    fail 'worker flow does not call the explicit stage machine'
grep -Fq 'worker_stage_machine' "${WORKER}" ||
    fail 'worker does not load the explicit stage machine'

echo 'PASS: Strategy Lab search stages use one explicit monotonic stage machine'
