#!/usr/bin/env python3
"""Dynamic managed extra-resource capability classification: offline only."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SCRIPT))
from strategy_lab_py.resources import snapshot_inventory
from strategy_lab_py.extra_capabilities import inspect_extra_capabilities

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    lua, fake = root / "lua", root / "fake"
    lua.mkdir()
    fake.mkdir()
    state = root / "installed.json"
    script = lua / "invented.lua"
    script.write_bytes(b"function invented() end")
    blob = fake / "invented.bin"
    blob.write_bytes(b"\x16\x03\x03\x00\x04\x01\x00\x00\x00")
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    def record():
        return {
            "schema": 1,
            "files": {"lua/invented.lua": digest(script), "files/fake/invented.bin": digest(blob)},
            "capabilities": {"schema": 1, "resources": [
                {"target":"lua/invented.lua","kind":"lua","role":"desync","protocol":"tls13","transport":"tcp",
                 "export":"invented","dependencies":[],"arguments":[{"name":"pos","value":"1"}]},
                {"target":"files/fake/invented.bin","kind":"blob","format":"tls-clienthello","native_action":"fake",
                 "argument":"blob","protocol":"tls13","transport":"tcp"}]}}
    data=record()
    state.write_text(json.dumps(data))
    def assess():
        return inspect_extra_capabilities(snapshot_inventory(lua, fake), state)
    assert [r["status"] for r in assess()] == ["eligible", "eligible"]
    new = fake / "another.bin"
    new.write_bytes(blob.read_bytes())
    data["files"]["files/fake/another.bin"] = digest(new)
    data["capabilities"]["resources"].append(dict(data["capabilities"]["resources"][1], target="files/fake/another.bin"))
    state.write_text(json.dumps(data))
    assert [r["status"] for r in assess()] == ["eligible", "eligible", "eligible"]
    new.unlink()
    assert assess()[2]["status"] == "missing"
    new.write_bytes(b"wrong")
    assert assess()[2]["status"] == "unsupported"
    assert "checksum" in assess()[2]["reason"]
    # Correct ownership hash never makes malformed TLS content eligible.
    data["files"]["files/fake/another.bin"] = digest(new)
    state.write_text(json.dumps(data))
    assert assess()[2]["status"] == "unsupported"
    assert "TLS record signature" in assess()[2]["reason"]
    data["capabilities"]["resources"].append({"target":"files/fake/no-descriptor.bin","kind":"blob"})
    state.write_text(json.dumps(data))
    assert assess()[-1]["status"] == "unsupported"
    state.unlink()
    assert assess() == []
print("PASS: dynamic managed Lua/BIN classification is bounded to verified job inventory")
