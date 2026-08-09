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
    "${SCRIPT_DIR}/strategy_lab_py/resources.py" \
    "${SCRIPT_DIR}/strategy_lab_py/candidate_spec.py" \
    "${SCRIPT_DIR}/strategy_lab_py/search_graph.py" \
    "${SCRIPT_DIR}/strategy_lab_py/search.py" \
    "${SCRIPT_DIR}/strategy_lab_py/result.py"

if grep -Fq 'STRATEGY_LAB_EXPANSION_CATALOG' "${SCRIPT_DIR}/strategy_lab_py/search.py"; then
    fail 'active Python Stage 60 still reads the flat expansion catalog'
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-search-graph.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
LUA_DIR="${TMP}/lua"
FAKE_DIR="${TMP}/fake"
JOBS="${TMP}/jobs"
JOB="job.GRAPH"
JOB_DIR="${JOBS}/${JOB}"
mkdir -p "${LUA_DIR}" "${FAKE_DIR}" "${JOB_DIR}" "${TMP}/bin"
for lua in zapret-lib.lua zapret-antidpi.lua
do
    printf '%s\n' '-- fixture' > "${LUA_DIR}/${lua}"
done
printf '%s\n' fake > "${FAKE_DIR}/fake_tls_7.bin"
printf '%s\n' unrelated > "${FAKE_DIR}/wireguard_initiation.bin"
printf '%s\n' example.test > "${TMP}/endpoints.txt"
printf '%s\n' '{"accepted":["fake"]}' > "${TMP}/family.json"

PYTHONPATH="${SCRIPT_DIR}" \
STRATEGY_LAB_GRAPH_LUA_DIR="${LUA_DIR}" \
STRATEGY_LAB_GRAPH_FAKE_DIR="${FAKE_DIR}" \
STRATEGY_LAB_GRAPH_TMP="${TMP}" \
"${PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

from strategy_lab_py.candidate import ProtocolSpec, _candidate_description
from strategy_lab_py.candidate_spec import CandidateSpec
from strategy_lab_py.resources import snapshot_inventory
from strategy_lab_py.result import build_profile
from strategy_lab_py.search_graph import (
    GOLDEN_BUILTIN_ID,
    GOLDEN_EXTERNAL_ID,
    native_tls13_graph,
)

root = Path(os.environ["STRATEGY_LAB_GRAPH_TMP"])
lua = Path(os.environ["STRATEGY_LAB_GRAPH_LUA_DIR"])
fake = Path(os.environ["STRATEGY_LAB_GRAPH_FAKE_DIR"])
graph = native_tls13_graph()
inventory = snapshot_inventory(lua, fake)

assert len(graph.stage_nodes("reconnaissance")) == 7
assert len(graph.stage_nodes("expansion")) == 16
assert graph.graph_id == native_tls13_graph().graph_id
assert graph.golden_ids == (GOLDEN_EXTERNAL_ID, GOLDEN_BUILTIN_ID)

expansion = graph.stage_nodes("expansion")
classes = {item for node in expansion for item in node.spec.to_dict()["resource_classes"]}
assert classes == {"blob-free", "builtin", "inline", "external"}
assert {node.spec.out_range for node in expansion} == {None, "-d8", "-d10"}

by_id = {node.candidate_id: node for node in graph.nodes}
builtin = by_id[GOLDEN_BUILTIN_ID].spec
external = by_id[GOLDEN_EXTERNAL_ID].spec
assert builtin.strategy == (
    "--payload=tls_client_hello\n"
    "--lua-desync=fake:blob=fake_default_tls\n"
)
assert external.strategy == (
    "--out-range=-d8\n"
    "--blob=fake_tls_7\n"
    "--payload=tls_client_hello\n"
    "--lua-desync=multisplit:pos=2,midsld-2:seqovl=1:seqovl_pattern=fake_tls_7\n"
)
assert CandidateSpec.from_dict(external.to_dict()) == external
spec_file = root / "external.spec.json"
spec_file.write_text(json.dumps(external.to_dict()) + "\n", encoding="utf-8")
assert _candidate_description(
    external.candidate_id,
    external.family,
    ProtocolSpec("tls13", "tcp", 443, "tls"),
    external.strategy,
    "1",
    str(spec_file),
) == external

for accepted in ((), ("unrelated-stage-50-family",)):
    plan = graph.plan("expansion", accepted, inventory)
    scheduled = {node.candidate_id for node in plan.scheduled}
    assert plan.total_graph_nodes == 16 and not plan.skipped
    assert {GOLDEN_BUILTIN_ID, GOLDEN_EXTERNAL_ID} <= scheduled

fake_priority = graph.plan("expansion", ("fake",), inventory)
assert fake_priority.scheduled[0].candidate_id == "fake-repeat2"
assert {node.candidate_id for node in fake_priority.scheduled} == {
    node.candidate_id for node in expansion
}

without_owner = root / "fake-without-owner"
without_owner.mkdir()
(without_owner / "wireguard_initiation.bin").write_bytes(b"unrelated")
missing_plan = graph.plan("expansion", (), snapshot_inventory(lua, without_owner))
assert [item["candidate_id"] for item in missing_plan.skipped] == [GOLDEN_EXTERNAL_ID]
assert len(missing_plan.scheduled) == 15
assert GOLDEN_BUILTIN_ID in {node.candidate_id for node in missing_plan.scheduled}

assert all("wireguard" not in node.spec.strategy for node in graph.nodes)
assert all(
    "wireguard" not in requirement.name
    for node in graph.nodes
    for requirement in node.spec.blob_requirements
)

mapped = external.render_runtime_arguments(
    inventory,
    divert_port=9989,
    hostlist_path=root / "hostlist.txt",
)
assert "--out-range=-d8" in mapped and "--out-range=-d10" not in mapped
assert any(value.startswith("--blob=fake_tls_7:@") for value in mapped)

profile_d8 = build_profile("example.test", "domain", "tls13", 443, "", external.strategy)
profile_none = build_profile("example.test", "domain", "tls13", 443, "", builtin.strategy)
other_range = CandidateSpec.from_strategy(
    candidate_id="other-native-range",
    family="range",
    protocol="tls13",
    transport="tcp",
    port=443,
    l7="tls",
    strategy="--out-range=<s1\n--lua-desync=multisplit:pos=1\n",
    target_binding=True,
)
profile_other = build_profile(
    "example.test", "domain", "tls13", 443, "", other_range.strategy
)
assert "--out-range=-d8\n" in profile_d8 and "--out-range=-d10\n" not in profile_d8
assert "--out-range=" not in profile_none
assert "--out-range=<s1\n" in profile_other
PY

RUNNER="${TMP}/bin/candidate"
LOG="${TMP}/candidate-order.txt"
cat > "${RUNNER}" <<'MOCK'
#!/bin/sh
set -eu
result="$3"
id="$4"
family="$5"
strategy="$6"
spec="$8"
jq -e --arg id "${id}" --arg family "${family}" \
    '.candidate_id==$id and .family==$family and (.spec_id|startswith("cs1-"))' \
    "${spec}" >/dev/null
printf '%s\n' "${id}" >> "${MOCK_LOG}"
jq -n --arg id "${id}" --arg family "${family}" --rawfile strategy "${strategy}" \
    '{id:$id,family:$family,strategy:$strategy,endpoints:[],all_pass:false}' > "${result}"
MOCK
chmod 0755 "${RUNNER}"

STRATEGY_LAB_JOBS_DIR="${JOBS}" \
STRATEGY_LAB_LUA_DIR="${LUA_DIR}" \
STRATEGY_LAB_FAKE_DIR="${FAKE_DIR}" \
STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER="${RUNNER}" \
STRATEGY_LAB_EXPANSION_TARGET=99 \
STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
MOCK_LOG="${LOG}" \
sh "${LAUNCHER}" search expand \
    "${JOB}" "${TMP}/endpoints.txt" "${TMP}/family.json" "${TMP}/expansion.json"

"${JQ}" -e '
  (.search_graph_id|startswith("sg1-")) and
  .total_graph_nodes==16 and .total_available==16 and .completed==16 and
  (.working|length)==0 and (.failed|length)==16 and
  .golden_ids==["golden-owner-multisplit-fake-tls-7","golden-fake-default-tls"] and
  (.skipped|length)==0 and .stopped_reason=="graph_exhausted" and
  ([.candidates[].id]|index("golden-owner-multisplit-fake-tls-7"))!=null and
  ([.candidates[].id]|index("golden-fake-default-tls"))!=null
' "${TMP}/expansion.json" >/dev/null || {
    cat "${TMP}/expansion.json" >&2
    fail 'native graph Stage-60 execution evidence is invalid'
}
[ "$(sed -n '1p' "${LOG}")" = 'fake-repeat2' ] || fail 'accepted family did not affect graph priority'
"${JQ}" -e '.stage=="expansion" and .total_graph_nodes==16 and (.scheduled|length)==16' \
    "${JOB_DIR}/search-graph.json" >/dev/null || fail 'job search graph evidence is missing'

echo 'PASS: native Zapret2 DAG preserves golden reachability, exact candidate ranges, four resource classes, semantic external-resource skips, and Stage-50 priority without gating'
