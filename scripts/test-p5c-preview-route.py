#!/usr/bin/env python3
"""P5c fast route contract; mocks are NOT installed OPNsense evidence."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
from unittest.mock import patch

base = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret/backend"
shape = types.ModuleType("strategy_preview")


class PreviewRefused(ValueError):
    pass


shape.PreviewRefused = PreviewRefused
shape._request = lambda raw: json.loads(raw)
shape.preview = lambda item: {
    "profiles": [{"number": 1, "mode": item["target_mode"], "args": item["strategy"]}],
    "warnings": [],
}
sys.modules["strategy_preview"] = shape
build = types.ModuleType("strategy_preview_build")


class PrivateBuildRefused(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


build.PrivateBuildRefused = PrivateBuildRefused
build.MAX_XML = 16 * 1024 * 1024
build.preview_prepared_xml = lambda xml, native=True: {
    "native_validation": {
        "mapped_validation": "native_mapped_valid",
        "engine_native_dry_run": "passed",
    },
}
sys.modules["strategy_preview_build"] = build
lock = types.ModuleType("voice_ipfw_adapter")
lock.require_lifecycle_lock = lambda: None
sys.modules["voice_ipfw_adapter"] = lock
spec = importlib.util.spec_from_file_location("p5c_route", base / "strategy_preview_route.py")
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)
xml = (
    b"<opnsense><OPNsense><Zapret><hostlist><mode>list</mode>"
    b"</hostlist><strategy><trafficargs>--filter-tcp=443</trafficargs>"
    b"</strategy></Zapret></OPNsense></opnsense>"
)
report = route._read_shape(xml)
assert report["profiles"][0]["mode"] == "list"
assert report["profiles"][0]["args"] == "--filter-tcp=443"
assert route._read_shape(b"bad")["state"] == "structural_unavailable"
with patch.object(route.platform, "system", return_value="FreeBSD"), patch.object(
    route.os, "geteuid", return_value=0
), patch.object(route, "_prepared_xml", return_value=xml):
    ok = route.native_preview("YWJj")
    assert ok["status"] == "native_checked"
    assert ok["native_validation"]["engine_native_dry_run"] == "passed"
    assert ok["applied"] is False and ok["saved"] is False
    with patch.object(build, "preview_prepared_xml",
                      side_effect=PrivateBuildRefused("ORIGINAL_BUILDER_REFUSED")):
        no = route.native_preview("YWJj")
        assert no["status"] == "ORIGINAL_BUILDER_REFUSED"
        assert no["structure"]["profiles"]
    assert route.native_preview("bad=")["status"] == "REQUEST_ENCODING_REFUSED"
with patch.object(route.platform, "system", return_value="Linux"):
    assert route.native_preview("YWJj")["status"] == "NATIVE_OWNER_REQUIRED"
output = io.StringIO()
with contextlib.redirect_stdout(output):
    assert route.main(["wrong", "bad"]) == 0
assert json.loads(output.getvalue())["status"] == "REQUEST_REFUSED"
print("P5C_ROUTE_SCOPE_TEST=PASS")
