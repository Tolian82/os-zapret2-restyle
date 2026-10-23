#!/usr/bin/env python3
"""Dynamic runnable Lua/BIN Stage-60 graph: offline, no native service changes."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SCRIPT))
from strategy_lab_py import dynamic_graph, search_graph
from strategy_lab_py.candidate_spec import CandidateSpec
from strategy_lab_py.resources import snapshot_inventory

def sha(data):
    return hashlib.sha256(data).hexdigest()

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    lua, fake = root / "lua", root / "fake"
    lua.mkdir()
    fake.mkdir()
    state = root / "installed.json"
    for n in ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua"):
        (lua / n).write_text(f"function {n.replace('-', '_').replace('.', '_')}() end\n")
    custom = lua / "invented_dynamic.lua"
    custom.write_text("function testdynamic(ctx, desync) return nil end\n")
    binary = fake / "invented_tls.bin"
    binary.write_bytes(b"\x16\x03\x03\x00\x04\x01\x00\x00\x00")
    records = [
        {"target": "files/fake/invented_tls.bin", "kind": "blob",
         "format": "tls-clienthello", "transport": "tcp", "protocol": "tls13",
         "family": "fake", "native_action": "fake", "argument": "blob"},
        {"target": "lua/invented_dynamic.lua", "kind": "lua", "role": "desync",
         "transport": "tcp", "protocol": "tls13", "family": "fake+split",
         "export": "testdynamic",
         "dependencies": ["zapret-lib.lua", "zapret-antidpi.lua"],
         "arguments": [{"name": "fake_blob", "value": "fake_default_tls"},
                       {"name": "pos", "value": "1"}]},
    ]
    owner = {"schema": 1, "source_commit": "a" * 40,
             "files": {"lua/invented_dynamic.lua": sha(custom.read_bytes()),
                       "files/fake/invented_tls.bin": sha(binary.read_bytes())},
             "capabilities": {"schema": 1, "resources": records}}
    def graph():
        state.write_text(json.dumps(owner))
        inv = snapshot_inventory(lua, fake)
        return (*dynamic_graph.job_tls13_graph(inv, state), inv)
    # The common inventory must never resolve a Lua/BIN symlink into an
    # executable resource, even when the target is readable.
    outside_lua = root / "outside.lua"
    outside_lua.write_text("function outside() end\n")
    (lua / "foreign.lua").symlink_to(outside_lua)
    assert all(item.name != "foreign.lua"
               for item in snapshot_inventory(lua, fake).lua)
    base = search_graph.native_tls13_graph()
    g, evidence, inv = graph()
    assert g.golden_ids == base.golden_ids
    assert len(g.nodes) == len(base.nodes) + 2
    assert [x["status"] for x in evidence] == ["eligible", "eligible"], evidence
    # A formerly managed BIN replaced by a symlink must disappear from the
    # next job's inventory and become "missing", not a runnable extra.
    moved_blob = root / "elsewhere.bin"
    binary.rename(moved_blob)
    binary.symlink_to(moved_blob)
    try:
        g_link, e_link, i_link = graph()
        assert all(item.name != "invented_tls.bin" for item in i_link.external_blobs)
        assert e_link[0]["status"] == "missing", e_link
        assert len(g_link.nodes) == len(base.nodes) + 1
    finally:
        binary.unlink()
        moved_blob.rename(binary)
    extension = g.nodes[len(base.nodes):]
    assert {x.spec.family for x in extension} == {"fake", "fake+split"}
    plan = g.plan("expansion", ["fake", "fake+split"], inv)
    assert {x.candidate_id for x in extension}.issubset(
        {x.candidate_id for x in plan.scheduled})
    by_family = {x.spec.family: x.spec for x in extension}
    blob_spec = by_family["fake"]
    lua_spec = by_family["fake+split"]
    for spec in (blob_spec, lua_spec):
        assert CandidateSpec.from_dict(spec.to_dict()) == spec
        argv = spec.render_runtime_arguments(
            inv, divert_port=9989, hostlist_path=root / "hostlist")
        assert "--filter-tcp=443" in argv
        assert any(v.startswith("--lua-init=@") for v in argv)
    blob_args = blob_spec.render_runtime_arguments(
        inv, divert_port=9989, hostlist_path=root / "hostlist")
    assert f"--blob=invented_tls:@{binary}" in blob_args
    lua_args = lua_spec.render_runtime_arguments(
        inv, divert_port=9989, hostlist_path=root / "hostlist")
    assert f"--lua-init=@{custom}" in lua_args
    assert any(s == "--lua-desync=testdynamic:fake_blob=fake_default_tls:pos=1"
               for s in lua_args)
    assert any(r.name == "fake_default_tls" and r.resource_class == "builtin"
               for r in lua_spec.blob_requirements)
    # A new filename/descriptor changes the next graph, no Python changes.
    extra = fake / "unseen_future.bin"
    extra.write_bytes(binary.read_bytes())
    owner["files"]["files/fake/unseen_future.bin"] = sha(extra.read_bytes())
    owner["capabilities"]["resources"].append({
        **records[0], "target": "files/fake/unseen_future.bin",
    })
    g2, ev2, _ = graph()
    assert len(g2.nodes) == len(base.nodes) + 3
    assert g2.graph_id != g.graph_id
    assert [x["status"] for x in ev2] == ["eligible"] * 3
    extra.unlink()
    g3, ev3, _ = graph()
    assert len(g3.nodes) == len(base.nodes) + 2
    assert ev3[-1]["status"] == "missing"
    # A modified installed blob is never run, even if metadata claims support.
    binary.write_bytes(b"changed by another actor")
    g4, ev4, _ = graph()
    assert len(g4.nodes) == len(base.nodes) + 1
    assert ev4[0]["status"] == "unsupported"
    binary.write_bytes(b"\x16\x03\x03\x00\x04\x01\x00\x00\x00")
    # Unsupported protocol and unsupported Lua arguments are explainable.
    owner["capabilities"]["resources"][0]["protocol"] = "udp"
    owner["capabilities"]["resources"][1]["arguments"][1]["name"] = "shell"
    g5, ev5, _ = graph()
    assert len(g5.nodes) == len(base.nodes)
    assert all(r["status"] == "unsupported" for r in ev5[:2])
    # Bounds cap the graph; the rest are clearly marked as pruned.
    owner["capabilities"]["resources"] = [records[0]]
    owner["capabilities"]["resources"][0]["protocol"] = "tls13"
    owner["files"].pop("lua/invented_dynamic.lua")
    for i in range(dynamic_graph.MAX_EXTRA_NODES + 2):
        name = f"future_{i}.bin"
        (fake / name).write_bytes(binary.read_bytes())
        owner["files"]["files/fake/" + name] = sha(binary.read_bytes())
        owner["capabilities"]["resources"].append({
            **records[0], "target": "files/fake/" + name
        })
    g6, ev6, _ = graph()
    assert len(g6.nodes) == len(base.nodes) + dynamic_graph.MAX_EXTRA_NODES
    assert sum(r["status"] == "pruned" for r in ev6) == 3
    # Existing graph stays independent of job-owned extras.
    assert search_graph.native_tls13_graph().graph_id == base.graph_id
print("PASS: dynamic native TLS BIN/Lua candidates, dependencies and bounds")
