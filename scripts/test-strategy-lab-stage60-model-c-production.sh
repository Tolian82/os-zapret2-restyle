#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
MODULE_ROOT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
ENGINE="${MODULE_ROOT}/strategy_lab_py/stage60_model_c.py"
OWNER="${MODULE_ROOT}/strategy_lab_py/stage60_model_c_production.py"
SELECTOR="${MODULE_ROOT}/strategy_lab_model_c.lua"
ENTRY="${MODULE_ROOT}/strategy_lab_python.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
for file in "${ENGINE}" "${OWNER}" "${SELECTOR}" "${ENTRY}"; do
    [ -s "${file}" ] || fail "missing Model C production surface: ${file}"
done

PYTHONPATH="${MODULE_ROOT}" "${PYTHON_BIN}" - <<'PY'
import grp
import os
import pwd
import stat
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from strategy_lab_py import (
    model_b,
    resources,
    search_graph,
    stage60_model_c,
    stage60_model_c_production,
    stage60_parallel,
)

assert stage60_model_c.MODEL == "C-warm-bucket-source-port-dispatch"
assert stage60_model_c.WIDTH == 3
assert stage60_model_c_production.MODEL == stage60_model_c.MODEL
assert stage60_model_c_production.WIDTH == 3
assert stage60_model_c_production._requested_model() == "model-c"
assert issubclass(
    stage60_model_c_production.ModelCOnlyInfrastructureError,
    stage60_parallel.Stage60ParallelError,
)
assert not issubclass(
    stage60_model_c_production.ModelCOnlyInfrastructureError,
    stage60_parallel.WarmInfrastructureError,
)

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
    nodes = {node.candidate_id: node for node in plan.scheduled}
    ordinary = by_id["seqovl-host"]
    external = by_id[search_graph.GOLDEN_EXTERNAL_ID]
    assert ordinary.out_range == "-d10"
    assert external.out_range == "-d8"

    mixed_ids = ("fake-rnd", "fake-split-host", "syndata-1603")
    mixed = [
        search_graph.SearchDecision(
            node=nodes[candidate_id],
            reason="fixture",
            evidence_source="fixture",
            evidence_outcome="pending",
            priority=(index,),
        )
        for index, candidate_id in enumerate(mixed_ids)
    ]
    assert by_id["fake-rnd"].target_binding is True
    assert by_id["fake-split-host"].target_binding is True
    assert by_id["syndata-1603"].target_binding is False
    assert stage60_model_c._bucket_profile_key(by_id["fake-rnd"]) == (
        "ipv4", "tcp", 443, "tls", True
    )
    segments = stage60_model_c._compatible_batch_segments(mixed)
    assert [
        [decision.node.candidate_id for decision in segment] for segment in segments
    ] == [["fake-rnd", "fake-split-host"], ["syndata-1603"]]

    original_segment = stage60_model_c._bucket_segment
    calls = []
    def fake_segment(job_id, decisions, bindings, inventory, source_ports, indexes):
        ids = [decision.node.candidate_id for decision in decisions]
        calls.append(ids)
        return (
            [{"id": candidate_id} for candidate_id in ids],
            {
                "execution_model": stage60_model_c.MODEL,
                "width": len(decisions),
                "physical_worker_count": 1,
                "divert_port": 9990,
                "route_rules": [19128 + index for index in range(len(decisions))],
                "selector": stage60_model_c.SELECTOR_FUNCTION,
                "selector_ports": {candidate_id: [42000 + index] for index, candidate_id in enumerate(ids)},
                "max_overlap_observed": len(decisions),
                "pool_startup_ms": 10 * len(decisions),
                "parallel_probe_wall_ms": 20,
                "rss": {"aggregate_kb": 4300 + len(calls), "all_numeric": True},
                "worker": {},
                "runtime_arguments": [],
                "candidate_ids": ids,
                "total_ms": 50,
            },
        )
    stage60_model_c._bucket_segment = fake_segment
    try:
        candidates, evidence = stage60_model_c._bucket_batch(
            "job.fixture", mixed, (), inventory, {}, {}
        )
    finally:
        stage60_model_c._bucket_segment = original_segment
    assert calls == [["fake-rnd", "fake-split-host"], ["syndata-1603"]]
    assert [item["id"] for item in candidates] == list(mixed_ids)
    assert evidence["candidate_ids"] == list(mixed_ids)
    assert evidence["profile_segment_count"] == 2
    assert [item["candidate_ids"] for item in evidence["profile_segments"]] == calls
    assert evidence["pool_startup_ms"] == 30
    assert evidence["parallel_probe_wall_ms"] == 40
    assert evidence["rss"]["aggregate_kb"] == 4302

    selectors = {
        ordinary.candidate_id: (42000, 42001),
        external.candidate_id: (42002, 42003),
    }
    args = stage60_model_c._render_bucket_arguments(
        (ordinary, external), selectors, inventory,
        divert_port=9990, hostlist_path=hostlist, selector_lua=selector,
    )
    assert args.count("--port=9990") == 1
    assert args.count("--filter-tcp=443") == 1
    assert args.count("--filter-l7=tls") == 1
    assert f"--hostlist={hostlist}" in args
    assert f"--lua-init=@{lua_root / 'zapret-auto.lua'}" in args
    assert f"--lua-init=@{selector}" in args
    assert f"--blob=fake_tls_7:@{fake_root / 'fake_tls_7.bin'}" in args

    ordinary_cond = next(index for index, value in enumerate(args) if f"candidate_id={ordinary.candidate_id}" in value)
    external_cond = next(index for index, value in enumerate(args) if f"candidate_id={external.candidate_id}" in value)
    assert args[ordinary_cond - 3:ordinary_cond] == ("--in-range=x", "--out-range=-d10", "--payload=tls_client_hello")
    assert args[external_cond - 3:external_cond] == ("--in-range=x", "--out-range=-d8", "--payload=tls_client_hello")
    assert "source_ports=42000,42001" in args[ordinary_cond]
    assert "source_ports=42002,42003" in args[external_cond]
    assert f"instances={len(ordinary.lua_instances)}" in args[ordinary_cond]
    assert f"instances={len(external.lua_instances)}" in args[external_cond]
    assert "iff=strategy_lab_model_c_source_port" in args[ordinary_cond]
    assert not any(value == "--new" for value in args)

    # Owner-live _50 regression: dvtws2 switches to nobody *before* reopening
    # the Model-C hostlist. The random staging path must be readable to nobody
    # while the private per-worker session is not made traversable.
    staged = root / "staged-hostlist"
    staged.mkdir()
    # The hosted non-root Linux runner may have user nobody but only the
    # 'nogroup' group; actual root FreeBSD must resolve the real nobody group.
    gid = grp.getgrnam("nobody").gr_gid if os.geteuid() == 0 else os.getgid()
    if os.geteuid() == 0:
        os.chown(staged, -1, gid)
        os.chmod(root, 0o711)
        os.chmod(staged, 0o710)
    original_session_dir = model_b.session_dir
    model_b.session_dir = lambda: root / "private-session"
    chown_guard = nullcontext() if os.geteuid() == 0 else patch.object(stage60_model_c.os, "chown")
    group_guard = (
        nullcontext() if os.geteuid() == 0
        else patch.object(
            stage60_model_c.grp, "getgrnam",
            return_value=SimpleNamespace(gr_gid=gid),
        )
    )
    try:
        with chown_guard, group_guard:
            with patch.dict(os.environ, {
                "STRATEGY_LAB_MODEL_C_HOSTLIST_DIR": str(staged),
                "STRATEGY_LAB_MODEL_C_SELECTOR_LUA": str(selector),
            }):
                selection = (mixed[0],)
                bucket = stage60_model_c._write_bucket_runtime(
                    selection, [{"endpoint": "example.test", "selected_ip": "192.0.2.1"}],
                    inventory, {(1, 1): 42000},
                    {selection[0].node.candidate_id: 1},
                )
        staged_file = staged / "hostlist.txt"
        assert stat.S_IMODE(staged_file.stat().st_mode) == 0o640
        assert f"--hostlist={staged_file}" in bucket["runtime_arguments"]
        assert not (root / "private-session" / "workers" / "pass" / "hostlist.txt").exists()
        if os.geteuid() == 0:
            uid = pwd.getpwnam("nobody").pw_uid
            def drop_to_nobody():
                os.setgroups([gid])
                os.setgid(gid)
                os.setuid(uid)
            result = subprocess.run(
                [sys.executable, "-c",
                 "from pathlib import Path; import sys; assert Path(sys.argv[1]).read_text() == 'example.test\\n'",
                 str(staged_file)],
                preexec_fn=drop_to_nobody, capture_output=True, text=True,
            )
            assert result.returncode == 0, result.stderr
            assert stat.S_IMODE(staged.stat().st_mode) == 0o710
    finally:
        model_b.session_dir = original_session_dir

    routes = stage60_model_c._bucket_route_slots(3)
    assert len(routes) == 3
    assert len({slot.port for slot in routes}) == 1
    assert {slot.port for slot in routes} == {9990}
    assert len({slot.rule for slot in routes}) == 3
    assert {slot.rule for slot in routes} == {19128, 19129, 19130}

# Prove the normal production owner converts a Model-C infrastructure failure into a
# structural Stage-60 failure which the legacy warm/cold fallback handler cannot catch.
original_expand = stage60_parallel.expand
original_bucket = stage60_model_c._bucket_batch
original_reference = stage60_model_c._run_existing_model
original_cleanup = model_b._try_adapter
reference_calls = []

def fail_bucket(*args, **kwargs):
    raise stage60_model_c.ModelCInfrastructureError("fixture readiness failure")

def fake_expand(*args):
    assert stage60_parallel.MODEL == stage60_model_c_production.MODEL
    return stage60_parallel._warm_batch("job.fixture", (), (), None, {}, {})

def reference_model(*args):
    reference_calls.append(args)
    return 0

stage60_parallel.expand = fake_expand
stage60_model_c._bucket_batch = fail_bucket
stage60_model_c._run_existing_model = reference_model
model_b._try_adapter = lambda *args, **kwargs: True
try:
    try:
        stage60_model_c_production.expand(
            "job.fixture", "endpoints", "family", "missing-result.json"
        )
    except stage60_model_c_production.ModelCOnlyInfrastructureError as exc:
        assert "fixture readiness failure" in str(exc)
    else:
        raise AssertionError("Model-C infrastructure failure did not fail Stage 60")
finally:
    stage60_parallel.expand = original_expand
    stage60_model_c._bucket_batch = original_bucket
    stage60_model_c._run_existing_model = original_reference
    model_b._try_adapter = original_cleanup
assert reference_calls == []

os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "model-b"
assert stage60_model_c_production._requested_model() == "model-b"
os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "parallel"
assert stage60_model_c_production._requested_model() == "model-b"
os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "cold"
assert stage60_model_c_production._requested_model() == "cold"
os.environ.pop("STRATEGY_LAB_STAGE60_MODEL", None)
PY

grep -Fq 'from strategy_lab_py import stage60_model_c_production as stage60_parallel' "${ENTRY}" || fail 'production entry point is not routed through the Model-C-only owner'
grep -Fq 'function strategy_lab_model_c_source_port(desync)' "${SELECTOR}" || fail 'Model C selector function is missing'
grep -Fq 'tcp.th_sport' "${SELECTOR}" || fail 'Model C selector does not inspect outgoing client source port'
grep -Fq 'tcp.th_dport' "${SELECTOR}" || fail 'Model C selector does not preserve client-port identity for reverse direction'
grep -Fq 'return false' "${SELECTOR}" || fail 'Model C selector is not fail-closed'
grep -Fq 'ModelCOnlyInfrastructureError(stage60_parallel.Stage60ParallelError)' "${OWNER}" || fail 'Model-C-only infrastructure failure is not structural'
if grep -Fq 'fallback_execution_model' "${OWNER}"; then
    fail 'normal Model-C-only production owner still records Model B replay'
fi
if grep -Fq 'except stage60_parallel.WarmInfrastructureError' "${OWNER}"; then
    fail 'normal Model-C-only production owner can still catch the legacy Model-B fallback signal'
fi
if grep -Fq 'model_c_enabled' "${OWNER}" || grep -Fq 'disable_reason' "${OWNER}"; then
    fail 'normal Model-C-only production owner still carries transitional Model-C-disable replay state'
fi
grep -Fq 'cold_fallback_available"] = False' "${OWNER}" || fail 'Model-C-only result does not explicitly disable cold fallback'
grep -Fq 'model_c_only"] = True' "${OWNER}" || fail 'Model-C-only result policy evidence is missing'
grep -Fq 'STRATEGY_LAB_MODEL_C_HOSTLIST_DIR' "${MODULE_ROOT}/strategy_lab_stage60_parallel_runner.sh" || fail 'Model-C production runner does not stage its hostlist'
grep -Fq 'chgrp nobody' "${MODULE_ROOT}/strategy_lab_stage60_parallel_runner.sh" || fail 'Model-C staged hostlist directory is not nobody-searchable'
grep -Fq 'rmdir "${HOSTLIST_STAGING_DIR}"' "${MODULE_ROOT}/strategy_lab_stage60_parallel_runner.sh" || fail 'Model-C staging directory is not removed after cleanup'
grep -Fq 'os.chown(hostlist, -1, grp.getgrnam("nobody").gr_gid)' "${ENGINE}" || fail 'Model-C hostlist is not assigned the nobody group'
grep -Fq 'os.chmod(hostlist, 0o640)' "${ENGINE}" || fail 'Model-C hostlist is not root:nobody 0640'
grep -Fq '_compatible_batch_segments' "${ENGINE}" || fail 'Model C does not split incompatible profile segments'
grep -Fq 'profile_segments' "${ENGINE}" || fail 'Model C does not persist profile-segment evidence'
if grep -Fq 'stage60_parallel._batch_decisions =' "${ENGINE}"; then
    fail 'Model C must not replace the authoritative adaptive batch chooser'
fi
grep -Fq 'ThreadPoolExecutor(max_workers=len(decisions)' "${ENGINE}" || fail 'Model C candidate-level width-three overlap is missing'
grep -Fq 'model_b_parallel_attribution._probe_endpoint' "${ENGINE}" || fail 'Model C does not reuse exact source-port-qualified route attribution'
grep -Fq 'physical_worker_count' "${ENGINE}" || fail 'Model C does not evidence one physical bucket worker'
grep -Fq 'cleanup-all' "${ENGINE}" || fail 'Model C has no explicit bucket cleanup boundary'

echo 'PASS: normal production Stage 60 is Model-C-only with explicit bounded infrastructure failure, while planner batches, profile segmentation, exact source-port dispatch, and cleanup remain intact'
