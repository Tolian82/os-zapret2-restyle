#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_python_launcher.sh"
JQ=$(command -v jq || true)

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"
[ -x "${JQ}" ] || fail 'jq is unavailable'

"${PYTHON}" -m py_compile \
    "${SCRIPT_DIR}/strategy_lab_py/telemetry.py" \
    "${SCRIPT_DIR}/strategy_lab_py/endpoint_epoch.py" \
    "${SCRIPT_DIR}/strategy_lab_py/search_graph.py" \
    "${SCRIPT_DIR}/strategy_lab_py/search.py"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-adaptive-planner.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
JOBS="${TMP}/jobs"
JOB="job.ADAPTIVE"
JOB_DIR="${JOBS}/${JOB}"
ENDPOINTS="${TMP}/endpoints.txt"
mkdir -p "${JOB_DIR}" "${TMP}/bin" "${TMP}/lua" "${TMP}/fake"
printf '%s\n' '-- fixture' > "${TMP}/lua/zapret-lib.lua"
printf '%s\n' '-- fixture' > "${TMP}/lua/zapret-antidpi.lua"
printf '%s\n' fake > "${TMP}/fake/fake_tls_7.bin"
printf '%s\n' example.test > "${ENDPOINTS}"

PYTHONPATH="${SCRIPT_DIR}" STRATEGY_LAB_ADAPTIVE_JOB_DIR="${JOB_DIR}" \
STRATEGY_LAB_ADAPTIVE_ENDPOINTS="${ENDPOINTS}" "${PYTHON}" - <<'PY'
import os
from pathlib import Path

from strategy_lab_py import endpoint_epoch, telemetry
from strategy_lab_py.resources import snapshot_inventory
from strategy_lab_py.search_graph import GOLDEN_BUILTIN_ID, native_tls13_graph

job = Path(os.environ["STRATEGY_LAB_ADAPTIVE_JOB_DIR"])
endpoints = Path(os.environ["STRATEGY_LAB_ADAPTIVE_ENDPOINTS"]).read_text().splitlines()
evidence = [{
    "endpoint": "example.test",
    "dns_a": {
        "classification": "pass",
        "answers": ["203.0.113.10", "203.0.113.11"],
    },
}]
first = endpoint_epoch.create(job, "example.test", "domain", endpoints, evidence)
assert first.generation == 1
assert first.bindings[0]["addresses"] == ["203.0.113.10", "203.0.113.11"]
assert first.bindings[0]["selected_ip"] == "203.0.113.10"
assert endpoint_epoch.load(job, endpoints) == first
second = endpoint_epoch.create(job, "example.test", "domain", endpoints, evidence)
assert second.generation == 2
assert second.epoch_id != first.epoch_id
assert endpoint_epoch.load(job, endpoints) == second
try:
    endpoint_epoch.load(job, ["other.example"])
except endpoint_epoch.EndpointEpochError:
    pass
else:
    raise AssertionError("changed endpoint set reused an existing search epoch")

graph = native_tls13_graph()
inventory = snapshot_inventory(
    Path(os.environ["STRATEGY_LAB_ADAPTIVE_JOB_DIR"]).parents[1] / "lua",
    Path(os.environ["STRATEGY_LAB_ADAPTIVE_JOB_DIR"]).parents[1] / "fake",
)
plan = graph.plan("expansion", ("fake",), inventory)
passed = [{"id": "04-fake", "family": "fake", "all_pass": True}]
failed = [{"id": "04-fake", "family": "fake", "all_pass": False}]
pass_decision = graph.next_expansion(plan, passed, [])
fail_decision = graph.next_expansion(plan, failed, [])
assert pass_decision is not None and pass_decision.node.candidate_id == GOLDEN_BUILTIN_ID
assert fail_decision is not None and fail_decision.node.candidate_id == "fake-repeat2"

for outcome in (True, False):
    observations = []
    while (decision := graph.next_expansion(plan, passed, observations)) is not None:
        observations.append({"candidate_id": decision.node.candidate_id, "all_pass": outcome})
    assert {item["candidate_id"] for item in observations} == {
        node.candidate_id for node in plan.scheduled
    }

telemetry.record(job, "fixture", 0, stage="test", outcome="pass")
PY

STRATEGY_LAB_JOBS_DIR="${JOBS}" STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
sh "${LAUNCHER}" state initialize "${JOB}" \
    "${JOB_DIR}/status.json" "${JOB_DIR}/events.ndjson" example.test standard en

EPOCH_ID=$("${JQ}" -r .epoch_id "${JOB_DIR}/search-epoch.json")
"${JQ}" -n --arg epoch "${EPOCH_ID}" '{
  search_epoch_id:$epoch,
  accepted:["fake"],
  rejected:["multisplit","multidisorder","seqovl","fake+split","syndata","hostfakesplit"],
  families:[{id:"04-fake",family:"fake",all_pass:true}]
}' > "${TMP}/family.json"

RUNNER="${TMP}/bin/candidate"
LOG="${TMP}/order.txt"
cat > "${RUNNER}" <<'MOCK'
#!/bin/sh
set -eu
output="$3"; id="$4"; family="$5"; strategy="$6"
epoch=$(jq -r .epoch_id "${STRATEGY_LAB_JOBS_DIR}/${1}/search-epoch.json")
case "${id}" in
  golden-fake-default-tls|fake-rnd|syndata-1603) pass=true ;;
  *) pass=false ;;
esac
printf '%s:%s\n' "${id}" "${pass}" >> "${MOCK_ORDER}"
jq -n --arg id "${id}" --arg family "${family}" --arg epoch "${epoch}" \
  --rawfile strategy "${strategy}" --argjson pass "${pass}" '{
    id:$id,family:$family,strategy:$strategy,search_epoch_id:$epoch,
    endpoints:[{endpoint:"example.test",selected_ip:"203.0.113.10",status:(if $pass then "PASS" else "FAIL" end)}],
    all_pass:$pass
  }' > "${output}"
MOCK
chmod 0755 "${RUNNER}"

STRATEGY_LAB_JOBS_DIR="${JOBS}" \
STRATEGY_LAB_LUA_DIR="${TMP}/lua" \
STRATEGY_LAB_FAKE_DIR="${TMP}/fake" \
STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${RUNNER}" \
STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
MOCK_ORDER="${LOG}" \
sh "${LAUNCHER}" search expand \
    "${JOB}" "${ENDPOINTS}" "${TMP}/family.json" "${TMP}/expansion.json"

"${JQ}" -e --arg epoch "${EPOCH_ID}" '
  .search_epoch_id==$epoch and
  .winner_band=={minimum:2,target:3} and
  .completed==4 and
  .working==["golden-fake-default-tls","fake-rnd","syndata-1603"] and
  .failed==["fake-repeat2"] and
  .partial==false and
  .early_stop=={triggered:true,winner_count:3} and
  .stopped_reason=="enough_candidates" and
  [.schedule[].candidate_id]==["golden-fake-default-tls","fake-repeat2","fake-rnd","syndata-1603"] and
  .schedule[2].reason=="parent_fail_stronger_neighbor"
' "${TMP}/expansion.json" >/dev/null || {
    cat "${TMP}/expansion.json" >&2
    fail 'adaptive scheduling or three-winner early stop is invalid'
}

"${JQ}" -e '
  .schema==1 and
  ([.events[]|select(.phase=="adaptive_candidate")]|length)==4 and
  all(.events[]; (.duration_ms|type)=="number" and .duration_ms>=0)
' "${JOB_DIR}/timing-telemetry.json" >/dev/null ||
  fail 'adaptive candidate timing telemetry is invalid'

: > "${LOG}"
DEADLINE=$("${PYTHON}" -c 'import time; print(time.monotonic() + 1.0)')
if STRATEGY_LAB_JOBS_DIR="${JOBS}" \
    STRATEGY_LAB_LUA_DIR="${TMP}/lua" \
    STRATEGY_LAB_FAKE_DIR="${TMP}/fake" \
    STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${RUNNER}" \
    STRATEGY_LAB_OPERATION_DEADLINE_MONOTONIC="${DEADLINE}" \
    STRATEGY_LAB_EXPANSION_TARGET=99 \
    STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
    MOCK_ORDER="${LOG}" \
    sh "${LAUNCHER}" search expand \
        "${JOB}" "${ENDPOINTS}" "${TMP}/family.json" "${TMP}/deadline-expansion.json"
then
    fail 'Stage-60 admission accepted a candidate that cannot fit its parent deadline'
else
    DEADLINE_STATUS=$?
fi
[ "${DEADLINE_STATUS}" -eq 124 ] || fail "Stage-60 deadline admission returned ${DEADLINE_STATUS}, expected 124"
[ ! -s "${LOG}" ] || fail 'Stage-60 deadline admission started a candidate before rejecting the budget'
"${JQ}" -e '
  .partial==true and .completed==0 and .stopped_reason=="insufficient_stage_budget" and
  .budget_admission.next_candidate=="golden-fake-default-tls" and
  .budget_admission.required_seconds==19.0 and
  .budget_admission.remaining_seconds>=0 and .budget_admission.remaining_seconds<2
' "${TMP}/deadline-expansion.json" >/dev/null ||
  fail 'Stage-60 partial deadline result is invalid'
"${JQ}" -e '
  .parameter_expansion.partial==true and
  .parameter_expansion.stopped_reason=="insufficient_stage_budget" and
  .parameter_expansion.completed==0
' "${JOB_DIR}/status.json" >/dev/null ||
  fail 'Stage-60 partial deadline result was not persisted into job state'
"${JQ}" -e '
  ([.events[]|select(.phase=="candidate_admission" and .stage=="60" and .outcome=="deferred")]|length)==1
' "${JOB_DIR}/timing-telemetry.json" >/dev/null ||
  fail 'Stage-60 deadline admission telemetry is missing'

echo 'PASS: Strategy Lab pins a search epoch, adapts from live evidence, stops at the winner target, and rejects Stage-60 work that cannot fit its parent deadline'
