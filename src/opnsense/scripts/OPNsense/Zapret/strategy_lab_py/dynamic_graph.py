"""Conservative, data-driven extra-candidate extension of the existing TLS graph.

Only the existing per-job ResourceInventory plus an owned/verified capability
record may authorize a node. The stock graph and golden IDs are never edited.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import extra_capabilities, search_graph
from .candidate_spec import CandidateSpec, CandidateSpecError, DEFAULT_LUA_DEPENDENCIES
from .resources import ResourceInventory

MANAGED_STATE = Path("/var/db/zapret2-restyle/extra-resources/installed.json")
MAX_EXTRA_NODES = 8


def _native_node(item: dict[str, Any]) -> search_graph.SearchNode:
    descriptor = item["descriptor"]
    digest = item["digest"]
    target = item["target"]
    identity = json.dumps(
        {"target": target, "sha256": digest, "descriptor": descriptor},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    name = "extra-" + hashlib.blake2b(identity, digest_size=10).hexdigest()
    if target.startswith("files/fake/"):
        if descriptor.get("family") != "fake":
            raise CandidateSpecError("binary family must be native fake")
        blob = target.rsplit("/", 1)[1].removesuffix(".bin")
        lines = (
            "--out-range=-d10",
            f"--blob={blob}",
            "--payload=tls_client_hello",
            f"--lua-desync=fake:blob={blob}",
        )
        dependencies = DEFAULT_LUA_DEPENDENCIES
        family, parent = "fake", "04-fake"
    elif target.startswith("lua/"):
        if descriptor.get("family") != "fake+split":
            raise CandidateSpecError("Lua family must be reviewed fake+split")
        arguments = descriptor["arguments"]
        values = {arg["name"]: arg["value"] for arg in arguments}
        if set(values) != {"fake_blob", "pos"} or len(arguments) != 2:
            raise CandidateSpecError("Lua requires exactly fake_blob and pos")
        if values["fake_blob"] != "fake_default_tls":
            raise CandidateSpecError("Lua fake_blob must be the native TLS default")
        pos = values["pos"]
        if len(pos) > 96 or not pos or any(c not in "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_+,-" for c in pos):
            raise CandidateSpecError("Lua split positions are invalid")
        action = descriptor["export"]
        lines = (
            "--out-range=-d10",
            "--payload=tls_client_hello",
            f"--lua-desync={action}:fake_blob={values['fake_blob']}:pos={pos}",
        )
        dependencies = tuple(dict.fromkeys(
            (*DEFAULT_LUA_DEPENDENCIES, *descriptor["dependencies"], target.rsplit("/", 1)[1])
        ))
        family, parent = "fake+split", "05-fake-split"
    else:
        raise CandidateSpecError("unknown installed resource class")
    spec = CandidateSpec.from_strategy(
        candidate_id=name,
        family=family,
        protocol="tls13",
        transport="tcp",
        port=443,
        l7="tls",
        strategy="\n".join(lines),
        target_binding=True,
        lua_dependencies=dependencies,
        provenance="managed-extra:" + digest,
        search_cost=4,
        complexity=2,
    )
    return search_graph.SearchNode(
        stage="expansion", parent_ids=(parent,), spec=spec,
    )


def job_tls13_graph(
    inventory: ResourceInventory,
    state_path: Path = MANAGED_STATE,
) -> tuple[search_graph.NativeSearchGraph, list[dict[str, str]]]:
    """Build a bounded runnable graph and per-resource decision evidence.

    No descriptor -> no extra node; bad metadata -> explicit unsupported or
    missing result; excess compatible nodes -> pruned. The source file names
    and membership are supplied entirely by the installed inventory/metadata.
    """
    base = search_graph.native_tls13_graph()
    observations = extra_capabilities.inspect_extra_capabilities(inventory, state_path)
    nodes: list[search_graph.SearchNode] = []
    evidence: list[dict[str, str]] = []
    for item in observations:
        decision: dict[str, str] = {
            "target": str(item.get("target", "")),
            "status": str(item.get("status", "unsupported")),
            "reason": str(item.get("reason", "")),
        }
        if item.get("status") == "eligible":
            if len(nodes) >= MAX_EXTRA_NODES:
                decision.update(status="pruned", reason="extra-candidate graph limit")
            else:
                try:
                    node = _native_node(item)
                except (CandidateSpecError, KeyError, TypeError, ValueError) as exc:
                    decision.update(status="unsupported", reason=f"native capability not supported: {exc}")
                else:
                    nodes.append(node)
                    decision["candidate_id"] = node.candidate_id
        evidence.append(decision)
    return search_graph.NativeSearchGraph(base.nodes + tuple(nodes)), evidence
