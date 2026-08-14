#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
MODULE_ROOT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE="${MODULE_ROOT}/strategy_lab_py/stage60_parallel.py"
ENTRY="${MODULE_ROOT}/strategy_lab_python.py"
EXPANSION_RUNNER="${MODULE_ROOT}/strategy_lab_expansion_runner.sh"
OWNER_RUNNER="${MODULE_ROOT}/strategy_lab_stage60_parallel_runner.sh"
PREFLIGHT="${MODULE_ROOT}/strategy_lab/preflight.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }
for file in "${MODULE}" "${ENTRY}" "${EXPANSION_RUNNER}" "${OWNER_RUNNER}" "${PREFLIGHT}"; do
    [ -s "${file}" ] || fail "missing Stage-60 Model-B reference/fallback surface: ${file}"
done

PYTHONPATH="${MODULE_ROOT}" "${PYTHON_BIN}" - <<'PY'
import tempfile
from pathlib import Path

from strategy_lab_py import resources, search_graph, stage60_parallel

assert stage60_parallel.MODEL == "B-warm-worker-parallel-batched"
assert stage60_parallel.WIDTH == 3

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    lua_root = root / "lua"
    fake_root = root / "fake"
    lua_root.mkdir()
    fake_root.mkdir()
    for name in ("zapret-lib.lua", "zapret-antidpi.lua"):
        (lua_root / name).write_text("-- fixture\n", encoding="utf-8")
    (fake_root / "fake_tls_7.bin").write_bytes(b"fixture")

    inventory = resources.snapshot_inventory(lua_root, fake_root)
    graph = search_graph.native_tls13_graph()
    plan = graph.plan("expansion", (), inventory)
    assert len(plan.scheduled) == 16
    reconnaissance = [
        {"id": node.candidate_id, "family": node.spec.family, "all_pass": False}
        for node in graph.stage_nodes("reconnaissance")
    ]
    first = stage60_parallel._batch_decisions(graph, plan, reconnaissance, [], 3)
    assert 1 <= len(first) <= 3
    selected = {item.node.candidate_id for item in first}
    expansion_ids = {node.candidate_id for node in graph.stage_nodes("expansion")}
    for decision in first:
        parents = {parent for parent in decision.node.parent_ids if parent in expansion_ids}
        assert not (parents & selected)

    observations = [
        {"candidate_id": item.node.candidate_id, "all_pass": False}
        for item in first
    ]
    second = stage60_parallel._batch_decisions(graph, plan, reconnaissance, observations, 3)
    assert all(item.node.candidate_id not in selected for item in second)

    limited = stage60_parallel._batch_decisions(graph, plan, reconnaissance, [], 1)
    assert len(limited) == 1

    bindings = [
        {"endpoint": "one.example", "selected_ip": "192.0.2.1"},
        {"endpoint": "two.example", "selected_ip": "192.0.2.2"},
    ]
    ports = stage60_parallel._source_port_plan(plan, bindings)
    assert ports
    assert len(ports) == len(set(ports.values()))
    assert min(ports.values()) >= 1024
    assert max(ports.values()) <= 65535

failed = stage60_parallel._warm_endpoint_result(
    {
        "endpoint": "one.example",
        "selected_ip": "192.0.2.1",
        "requested_local_port": 42000,
        "observed_local_port": None,
        "local_port_match": False,
        "command_source_port_match": True,
        "command_endpoint_match": True,
        "attribution_ok": True,
        "rule": 19128,
        "counter_before": {"packets": 0, "bytes": 0},
        "counter_after": {"packets": 1, "bytes": 60},
        "intercepted": True,
        "remote_ip": "",
        "endpoint_match": False,
        "classification": "fail",
        "execution": {"returncode": 28, "timed_out": False},
    }
)
assert failed["status"] == "FAIL"
assert failed["attribution_ok"] is True
assert failed["command_source_port_match"] is True
assert failed["command_endpoint_match"] is True
PY

grep -Fq 'stage60-parallel expand' "${OWNER_RUNNER}" || fail 'Stage-60 compatibility owner does not invoke stage60-parallel'
grep -Fq 'strategy_lab_stage60_parallel_runner.sh' "${EXPANSION_RUNNER}" || fail 'Stage-60 expansion runner is not routed to the compatibility owner'
grep -Fq 'from strategy_lab_py import stage60_model_c_production as stage60_parallel' "${ENTRY}" || fail 'Python entry point does not route normal production Stage 60 through the Model-C-only owner'
grep -Fq 'return search.expand(job_id, endpoints_file, family_result_file, result_file)' "${MODULE}" || fail 'explicit cold Model A reference/fallback is missing'
grep -Fq 'warm_enabled = False' "${MODULE}" || fail 'explicit Model B warm infrastructure failure does not disable its warm path'
grep -Fq 'A-cold-fallback' "${MODULE}" || fail 'explicit Model B cold fallback evidence is missing'
grep -Fq '_candidate_admission' "${MODULE}" || fail 'Model-B reference batch/cold budget admission is missing'
grep -Fq '_cancel_requested' "${MODULE}" || fail 'Model-B reference cancellation checks are missing'
grep -Fq 'remaining_winners = max(1, target - len(result["working"]))' "${MODULE}" || fail 'winner-band batch width reduction is missing'
grep -Fq 'ThreadPoolExecutor(max_workers=len(slots)' "${MODULE}" || fail 'Model-B reference candidate parallel execution is missing'
grep -Fq 'model_b_parallel_attribution._probe_endpoint' "${MODULE}" || fail '_21 attribution contract is not retained by Model B reference tooling'
grep -Fq 'cleanup-all' "${OWNER_RUNNER}" || fail 'Stage-60 compatibility owner has no unconditional dedicated cleanup'
grep -Fq 'trap on_signal HUP INT TERM' "${OWNER_RUNNER}" || fail 'Stage-60 compatibility owner has no cancellation/termination cleanup trap'
grep -Fq 'strategy_lab_parallel_residue_cleanup' "${PREFLIGHT}" || fail 'next-job preflight does not remove warm-worker residue'

sh -n "${OWNER_RUNNER}"
sh -n "${EXPANSION_RUNNER}"

echo 'PASS: explicit Model B reference/override retains resolved-frontier scheduling, exact _21 attribution, cold Model A fallback, budget/cancel containment, and stale-residue cleanup without being normal production fallback'
