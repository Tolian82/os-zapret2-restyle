"""Strategy Lab Python migration foundation; version comes from compatibility.json."""

import json
import os
from pathlib import Path
import sys


def _qualified_python():
    override = os.environ.get("ZAPRET_PYTHON_POLICY")
    if override:
        policy_file = Path(override)
    else:
        policy_file = Path("/usr/local/share/zapret2-restyle/compatibility.json")
        # The source-only test checkout has no installed package. This relative
        # path cannot resolve inside the installed OPNsense package layout.
        if not policy_file.is_file():
            candidate = Path(__file__).resolve().parents[5] / "compatibility.json"
            if candidate.is_file():
                policy_file = candidate

    with policy_file.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if data.get("schema_version") != 1 or data.get("target_product") != "OPNsense":
        raise RuntimeError("invalid installed OPNsense compatibility manifest")

    branches = set()
    for item in data.get("supported_platforms", []):
        py = item.get("python", {}) if isinstance(item, dict) else {}
        if (py.get("policy") != "opnsense-PLUGIN_PYTHON" or
                py.get("entrypoint") != "/usr/local/bin/python3"):
            continue
        for name in py.get("supported", []):
            if not isinstance(name, str):
                raise RuntimeError("invalid qualified Python branch")
            parts = name.split(".")
            if len(parts) != 2 or not all(x.isdigit() for x in parts):
                raise RuntimeError("invalid qualified Python branch")
            branches.add(tuple(map(int, parts)))
    if not branches:
        raise RuntimeError("no qualified Python branch in compatibility manifest")
    current = sys.version_info[:2]
    return current if current in branches else sorted(branches)[0]


SUPPORTED_PYTHON = _qualified_python()
FOUNDATION_REVISION = 1
