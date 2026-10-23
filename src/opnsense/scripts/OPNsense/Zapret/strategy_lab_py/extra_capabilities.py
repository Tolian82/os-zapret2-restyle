"""Job-local eligibility assessment for explicitly installed extra-resource capabilities.

The inventory remains the sole filesystem discovery mechanism. Metadata alone
never grants execution permission; this is a read-only Stage-4 foundation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .resources import ResourceInventory

SHA256 = re.compile(r"^[a-f0-9]{64}$")
RESOURCE = re.compile(r"^(?:lua/[A-Za-z_][A-Za-z0-9_.-]*\.lua|files/fake/[A-Za-z_][A-Za-z0-9_.-]*\.bin)$")


def inspect_extra_capabilities(inventory: ResourceInventory, state_file: Path) -> list[dict[str, Any]]:
    """Classify descriptors against actual job inventory and managed checksums.

    Results are evidence, never executable candidate specs. Unsupported entries
    remain visible with reasons. A corrupt ownership record fails closed.
    """
    if state_file.is_symlink() or not state_file.is_file():
        return []
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [{"target": "", "status": "unsupported", "reason": "managed metadata unreadable"}]
    if not isinstance(state, dict) or state.get("schema") != 1:
        return [{"target": "", "status": "unsupported", "reason": "invalid managed metadata schema"}]
    owned = state.get("files")
    descriptors = state.get("capabilities")
    if not isinstance(owned, dict) or not isinstance(descriptors, dict) or descriptors.get("schema") != 1 or not isinstance(descriptors.get("resources"), list):
        return [{"target": "", "status": "unsupported", "reason": "managed file/capability metadata invalid"}]
    known = {"lua/" + item.name: item for item in inventory.lua}
    known.update({"files/fake/" + item.name: item for item in inventory.external_blobs})
    results = []
    seen = set()
    for desc in descriptors["resources"]:
        target = desc.get("target") if isinstance(desc, dict) else None
        if not isinstance(target, str) or not RESOURCE.fullmatch(target) or target in seen:
            results.append({"target": target if isinstance(target, str) else "", "status": "unsupported", "reason": "invalid or duplicate descriptor target"})
            continue
        seen.add(target)
        detail = {"target": target, "status": "unsupported", "reason": ""}
        digest = owned.get(target)
        entry = known.get(target)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            detail["reason"] = "not owned by verified extra-resource installation"
        elif entry is None or entry.size <= 0:
            detail.update(status="missing", reason="file absent from this job's resource inventory")
        elif not isinstance(desc.get("protocol"), str) or desc.get("protocol") != "tls13" or desc.get("transport") != "tcp":
            detail["reason"] = "unsupported protocol or transport"
        elif target.startswith("files/fake/") and not (
            desc.get("kind") == "blob" and desc.get("format") == "tls-clienthello"
            and desc.get("native_action") == "fake" and desc.get("argument") == "blob"):
            detail["reason"] = "unsupported binary capability"
        elif target.startswith("lua/") and not (
            desc.get("kind") == "lua" and desc.get("role") == "desync"
            and isinstance(desc.get("export"), str)
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", desc["export"])
            and isinstance(desc.get("dependencies"), list)
            and all(isinstance(x, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*\.lua", x) for x in desc["dependencies"])
            and isinstance(desc.get("arguments"), list)
            and all(isinstance(x, dict) and isinstance(x.get("name"), str)
                    and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x["name"])
                    and isinstance(x.get("value"), str)
                    and re.fullmatch(r"[A-Za-z0-9_.,-]+", x["value"])
                    for x in desc["arguments"])):
            detail["reason"] = "unsupported Lua capability"
        elif target.startswith("lua/") and any(
            name not in {x.name for x in inventory.lua}
            for name in desc["dependencies"]
        ):
            detail.update(status="missing", reason="Lua dependency absent from job inventory")
        else:
            path = Path(entry.path)
            # Never open through a symlink or outside the job snapshot root.
            root = Path(inventory.lua_root if target.startswith("lua/") else inventory.fake_root)
            if path.is_symlink() or path.parent != root or path.name != target.split("/")[-1]:
                detail["reason"] = "unsafe installed resource path"
            else:
                try:
                    content = path.read_bytes()
                    actual = hashlib.sha256(content).hexdigest()
                except OSError:
                    detail.update(status="missing", reason="resource unreadable")
                else:
                    if actual != digest:
                        detail["reason"] = "managed file checksum mismatch"
                    elif target.startswith("files/fake/") and not (
                        len(content) >= 6 and content[0] == 0x16 and content[1] == 0x03 and content[5] == 0x01
                    ):
                        detail["reason"] = "declared TLS record signature missing"
                    elif target.startswith("lua/") and not re.search(
                        rb"(?m)^\s*function\s+" + re.escape(desc["export"].encode("ascii")) + rb"\s*\(",
                        content,
                    ):
                        detail["reason"] = "declared top-level Lua export missing"
                    else:
                        detail.update(
                            status="eligible",
                            reason="verified installed file and reviewed capability",
                            digest=digest,
                            descriptor=desc,
                        )
        results.append(detail)
    return results
