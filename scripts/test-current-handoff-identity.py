#!/usr/bin/env python3
"""Require active handoff identity to agree with VERSION and Makefile."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text().strip()
match = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)\s*$",
                  (root / "Makefile").read_text())
if not match:
    raise SystemExit("FAIL: missing Makefile PLUGIN_REVISION")
revision = match.group(1)
candidate = f"v{version}_{revision}"
package = f"os-zapret2-restyle-{version}_{revision}.pkg"
q = chr(96)
expect = {
    "docs/START_HERE.md": [
        f"**Current handoff identity:** {q}{candidate}{q}.",
        f"{q}PLUGIN_REVISION={revision}{q}",
    ],
    "docs/PROJECT_STATE.md": [
        f"Текущий этап — **{q}{candidate}{q}**",
        f"{q}PLUGIN_REVISION={revision}{q}",
        f"package candidate: {q}{package}{q}",
    ],
    "docs/releases/v0.5.2.md": [
        f"{q}PLUGIN_REVISION={revision}{q}, candidate {q}{candidate}{q}",
        f"{q}{package}{q}",
    ],
}
for path, tokens in expect.items():
    body = (root / path).read_text()
    for token in tokens:
        if token not in body:
            raise SystemExit(f"FAIL: primary identity mismatch in {path}: {token}")
print(f"PASS: all current handoff metadata agrees on {candidate}")
