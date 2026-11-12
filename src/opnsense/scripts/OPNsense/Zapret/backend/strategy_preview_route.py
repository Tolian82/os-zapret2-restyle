#!/usr/bin/env python3
"""Authenticated read-only Strategies preview, original FD9, no Apply owner.

The shared PHP candidate serializer operates on unsaved form fields in memory.
The verified P5b2b original builder/validator owns only a private workspace.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import strategy_preview
import strategy_preview_build
from voice_ipfw_adapter import require_lifecycle_lock

PHP = "/usr/local/bin/php"
PREPARE = Path(__file__).resolve().parent.parent / "strategy_preview_candidate.php"
MAX_ENVELOPE = 65536
MAX_XML = strategy_preview_build.MAX_XML
MAX_RESPONSE = 65536
ENCODED = re.compile(r"[A-Za-z0-9_-]{1,65536}\Z")


def _prepared_xml(encoded: str) -> bytes:
    result = subprocess.run(
        [PHP, str(PREPARE)], input=encoded.encode("ascii"),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=30, check=False, pass_fds=(9,),
        env={"PATH": "/usr/local/bin:/usr/bin:/bin:/sbin:/usr/sbin", "LANG": "C"},
    )
    if result.returncode or not (0 < len(result.stdout) <= MAX_XML):
        raise strategy_preview_build.PrivateBuildRefused("NATIVE_CANDIDATE_REFUSED")
    return result.stdout


def _read_shape(xml: bytes) -> dict[str, object]:
    try:
        root = ET.fromstring(xml)
        source = root.find("./OPNsense/Zapret")
        if source is None:
            raise ValueError("no model")

        def field(path: str) -> str:
            node = source.find(path)
            return "" if node is None or node.text is None else node.text

        candidate = {
            "strategy": field("strategy/trafficargs"),
            "target_mode": field("hostlist/mode") or "all",
            "extra_arguments": field("strategy/extraargs"),
            "exclude_domains_configured": bool(field("hostlist/excludedomains")),
            "exclude_ipset_configured": bool(field("hostlist/excludeipset")),
        }
        # The approved canonical Python profile-policy split, not another parser.
        return strategy_preview.preview(strategy_preview._request(
            json.dumps(candidate).encode("utf-8")
        ))
    except (ValueError, UnicodeError, ET.ParseError, strategy_preview.PreviewRefused):
        return {"state": "structural_unavailable", "profiles": [], "warnings": []}


def _receipt(code: str, structural: dict[str, object] | None = None,
             native: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "result": "preview", "status": code,
        "structure": structural if structural is not None else {
            "state": "structural_unavailable", "profiles": [], "warnings": [],
        },
        "native_validation": native if native is not None else {
            "mapped_validation": "not_run", "engine_native_dry_run": "not_run",
        },
        "applied": False, "saved": False, "safe_to_apply": False,
        "real_network_bypass": "not_tested",
    }


def native_preview(encoded: str) -> dict[str, object]:
    if platform.system() != "FreeBSD" or os.geteuid() != 0:
        return _receipt("NATIVE_OWNER_REQUIRED")
    if not ENCODED.fullmatch(encoded):
        return _receipt("REQUEST_ENCODING_REFUSED")
    require_lifecycle_lock()
    xml = _prepared_xml(encoded)
    structural = _read_shape(xml)
    try:
        report = strategy_preview_build.preview_prepared_xml(xml, native=True)
    except strategy_preview_build.PrivateBuildRefused as exc:
        return _receipt(exc.code, structural)
    return _receipt("native_checked", structural, report["native_validation"])


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "preview" or len(argv[1]) > MAX_ENVELOPE:
        print(json.dumps(_receipt("REQUEST_REFUSED"), separators=(",", ":")))
        return 0
    try:
        report = native_preview(argv[1])
    except Exception as exc:
        # Never leak model, engine output, Config, or submitted form strings.
        code = (exc.code if isinstance(exc, strategy_preview_build.PrivateBuildRefused)
                else "NATIVE_PREVIEW_UNAVAILABLE")
        report = _receipt(code)
    raw = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > MAX_RESPONSE:
        raw = json.dumps(_receipt("PREVIEW_REPORT_TOO_LARGE"), separators=(",", ":"))
    print(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
