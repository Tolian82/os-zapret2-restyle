#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
MODULE_ROOT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE="${MODULE_ROOT}/strategy_lab_py/stage60_model_c.py"
SELECTOR="${MODULE_ROOT}/strategy_lab_model_c.lua"
ENTRY="${MODULE_ROOT}/strategy_lab_python.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
for file in "${MODULE}" "${SELECTOR}" "${ENTRY}"; do
    [ -s "${file}" ] || fail "missing Model C production surface: ${file}"
done

PYTHONPATH="${MODULE_ROOT}" "${PYTHON_BIN}" - <<'PY'
import os
import tempfile
from pathlib import Path

from strategy_lab_py import resources, search_graph, stage60_model_c

assert stage60_model_c.MODEL == "C-warm-bucket-source-port-dispatch"
assert stage60_model_c.MODEL_B == "B-warm-worker-parallel-batched"
assert stage60_model_c.WIDTH == 3
assert stage60_model_c._requested_model() == "model-c"

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    lua_root = root / "lua"
    fake_root = root / "fake"
    lua_root.mkdir()
    fake_root.mkdir()
    for name in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua"):
        (lua_root / name).write_text("-- fixture\n", encoding="utf-8")
    (fake_root / "fake_tls_7.bin").write_bytes(b"fixture")
    selector = root / "strategy_lab_model_c.lua"
    selector.write_text("function strategy_lab_model_c_source_port() return true end\n", encoding="utf-8")
    hostlist = root / "hostlist.txt"
    hostlist.write_text("example.test\n", encoding="utf-8")

    inventory = resources.snapshot_inventory(lua_root, fake_root)
    graph = search_graph.native_tls13_graph()
    plan = graph.plan("expansion", (), inventory)
    by_id = {node.candidate_id: node.spec for node in plan.scheduled}
    ordinary = by_id["seqovl-host"]
    external = by_id[search_graph.GOLDEN_EXTERNAL_ID]
    assert ordinary.out_range == "-d10"
    assert external.out_range == "-d8"

    selectors = {
        ordinary.candidate_id: (42000, 42001),
        external.candidate_id: (42002, 42003),
    }
    args = stage60_model_c._render_bucket_arguments(
        (ordinary, external),
        selectors,
        inventory,
        divert_port=9990,
        hostlist_path=hostlist,
        selector_lua=selector,
    )
    assert args.count("--port=9990") == 1
    assert args.count("--filter-tcp=443") == 1
    assert args.count("--filter-l7=tls") == 1
    assert f"--hostlist={hostlist}" in args
    assert f"--lua-init=@{lua_root / 'zapret-auto.lua'}" in args
    assert f"--lua-init=@{selector}" in args
    assert f"--blob=fake_tls_7:@{fake_root / 'fake_tls_7.bin'}" in args

    ordinary_cond = next(
        index for index, value in enumerate(args)
        if f"candidate_id={ordinary.candidate_id}" in value
    )
    external_cond = next(
        index for index, value in enumerate(args)
        if f"candidate_id={external.candidate_id}" in value
    )
    assert args[ordinary_cond - 3:ordinary_cond] == (
        "--in-range=x", "--out-range=-d10", "--payload=tls_client_hello"
    )
    assert args[external_cond - 3:external_cond] == (
        "--in-range=x", "--out-range=-d8", "--payload=tls_client_hello"
    )
    assert "source_ports=42000,42001" in args[ordinary_cond]
    assert "source_ports=42002,42003" in args[external_cond]
    assert f"instances={len(ordinary.lua_instances)}" in args[ordinary_cond]
    assert f"instances={len(external.lua_instances)}" in args[external_cond]
    assert "iff=strategy_lab_model_c_source_port" in args[ordinary_cond]
    assert not any(value == "--new" for value in args)

    routes = stage60_model_c._bucket_route_slots(3)
    assert len(routes) == 3
    assert len({slot.port for slot in routes}) == 1
    assert {slot.port for slot in routes} == {9990}
    assert len({slot.rule for slot in routes}) == 3
    assert {slot.rule for slot in routes} == {19128, 19129, 19130}

os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "model-b"
assert stage60_model_c._requested_model() == "model-b"
os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "parallel"
assert stage60_model_c._requested_model() == "model-b"
os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "cold"
assert stage60_model_c._requested_model() == "cold"
os.environ.pop("STRATEGY_LAB_STAGE60_MODEL", None)
PY

grep -Fq 'from strategy_lab_py import stage60_model_c as stage60_parallel' "${ENTRY}" || fail 'production entry point is not routed through Model C'
grep -Fq 'function strategy_lab_model_c_source_port(desync)' "${SELECTOR}" || fail 'Model C selector function is missing'
grep -Fq 'tcp.th_sport' "${SELECTOR}" || fail 'Model C selector does not inspect outgoing client source port'
grep -Fq 'tcp.th_dport' "${SELECTOR}" || fail 'Model C selector does not preserve client-port identity for reverse direction'
grep -Fq 'return false' "${SELECTOR}" || fail 'Model C selector is not fail-closed'
grep -Fq 'fallback_execution_model' "${MODULE}" || fail 'Model C does not record Model B fallback'
grep -Fq 'original_batch' "${MODULE}" || fail 'accepted Model B fallback is not retained'
grep -Fq 'ThreadPoolExecutor(max_workers=len(decisions)' "${MODULE}" || fail 'Model C candidate-level width-three overlap is missing'
grep -Fq 'model_b_parallel_attribution._probe_endpoint' "${MODULE}" || fail 'Model C does not reuse exact source-port-qualified route attribution'
grep -Fq 'physical_worker_count' "${MODULE}" || fail 'Model C does not evidence one physical bucket worker'
grep -Fq 'cleanup-all' "${MODULE}" || fail 'Model C has no explicit bucket cleanup boundary'

echo 'PASS: production Stage 60 defaults to one warm Model C bucket with exact source-port candidate dispatch, preserved ranges/resources, width-three candidate overlap, Model B fallback, and cold Model A containment'
