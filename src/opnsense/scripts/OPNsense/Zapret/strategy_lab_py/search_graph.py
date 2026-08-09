"""Native Zapret2 Strategy Lab search graph and golden candidate corpus."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from .candidate_spec import CandidateSpec
from .resources import BUILTIN_BLOBS, ResourceInventory, ResourceInventoryError

SEARCH_GRAPH_SCHEMA = 1
GOLDEN_BUILTIN_ID = "golden-fake-default-tls"
GOLDEN_EXTERNAL_ID = "golden-owner-multisplit-fake-tls-7"


class SearchGraphError(RuntimeError):
    """The native search graph is internally inconsistent."""


@dataclass(frozen=True)
class SearchNode:
    stage: str
    parent_ids: tuple[str, ...]
    spec: CandidateSpec
    golden: bool = False

    def __post_init__(self) -> None:
        if self.stage not in {"reconnaissance", "expansion"}:
            raise SearchGraphError(f"invalid search stage: {self.stage}")
        if len(set(self.parent_ids)) != len(self.parent_ids):
            raise SearchGraphError(f"duplicate search parents: {self.spec.candidate_id}")

    @property
    def candidate_id(self) -> str:
        return self.spec.candidate_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "parent_ids": list(self.parent_ids),
            "golden": self.golden,
            "candidate_spec": self.spec.to_dict(),
        }


@dataclass(frozen=True)
class SearchPlan:
    graph_id: str
    stage: str
    accepted_families: tuple[str, ...]
    total_graph_nodes: int
    golden_ids: tuple[str, ...]
    scheduled: tuple[SearchNode, ...]
    skipped: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SEARCH_GRAPH_SCHEMA,
            "graph_id": self.graph_id,
            "stage": self.stage,
            "accepted_families": list(self.accepted_families),
            "total_graph_nodes": self.total_graph_nodes,
            "golden_ids": list(self.golden_ids),
            "scheduled": [node.to_dict() for node in self.scheduled],
            "skipped": list(self.skipped),
        }


@dataclass(frozen=True)
class NativeSearchGraph:
    nodes: tuple[SearchNode, ...]

    def __post_init__(self) -> None:
        by_id = {node.candidate_id: node for node in self.nodes}
        if len(by_id) != len(self.nodes):
            raise SearchGraphError("search candidate ids are not unique")
        stage_rank = {"reconnaissance": 0, "expansion": 1}
        for node in self.nodes:
            if node.spec.candidate_id != node.candidate_id:
                raise SearchGraphError("search node candidate identity is invalid")
            for parent_id in node.parent_ids:
                parent = by_id.get(parent_id)
                if parent is None:
                    raise SearchGraphError(
                        f"search parent is unavailable: {node.candidate_id} -> {parent_id}"
                    )
                if stage_rank[parent.stage] > stage_rank[node.stage]:
                    raise SearchGraphError(
                        f"search edge points to a later stage: {node.candidate_id} -> {parent_id}"
                    )
            if node.stage == "expansion":
                frontier = list(node.parent_ids)
                visited: set[str] = set()
                reaches_reconnaissance = False
                while frontier:
                    parent_id = frontier.pop()
                    if parent_id in visited:
                        continue
                    visited.add(parent_id)
                    parent = by_id.get(parent_id)
                    if parent is None:
                        raise SearchGraphError(
                            f"search parent is unavailable: {node.candidate_id} -> {parent_id}"
                        )
                    if parent.stage == "reconnaissance":
                        reaches_reconnaissance = True
                        break
                    frontier.extend(parent.parent_ids)
                if not reaches_reconnaissance:
                    raise SearchGraphError(
                        f"expansion node has no reconnaissance path: {node.candidate_id}"
                    )
        for stage in ("reconnaissance", "expansion"):
            self._topological(stage, ())

    @property
    def graph_id(self) -> str:
        payload = {
            "schema": SEARCH_GRAPH_SCHEMA,
            "nodes": [node.to_dict() for node in self.nodes],
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return "sg1-" + hashlib.blake2b(encoded, digest_size=16).hexdigest()

    @property
    def golden_ids(self) -> tuple[str, ...]:
        return tuple(node.candidate_id for node in self.nodes if node.golden)

    def stage_nodes(self, stage: str) -> tuple[SearchNode, ...]:
        if stage not in {"reconnaissance", "expansion"}:
            raise SearchGraphError(f"invalid search stage: {stage}")
        return tuple(node for node in self.nodes if node.stage == stage)

    def _topological(
        self,
        stage: str,
        accepted_families: Iterable[str],
    ) -> tuple[SearchNode, ...]:
        nodes = self.stage_nodes(stage)
        by_id = {node.candidate_id: node for node in nodes}
        order = {node.candidate_id: index for index, node in enumerate(nodes)}
        accepted = set(accepted_families)
        remaining = set(by_id)
        result: list[SearchNode] = []
        while remaining:
            ready = [
                by_id[candidate_id]
                for candidate_id in remaining
                if all(parent not in remaining for parent in by_id[candidate_id].parent_ids if parent in by_id)
            ]
            if not ready:
                raise SearchGraphError(f"search graph contains a cycle in {stage}")
            ready.sort(
                key=lambda node: (
                    0 if node.spec.family in accepted else 1,
                    order[node.candidate_id],
                )
            )
            selected = ready[0]
            result.append(selected)
            remaining.remove(selected.candidate_id)
        return tuple(result)

    @staticmethod
    def _ineligible_reason(node: SearchNode, inventory: ResourceInventory) -> str | None:
        try:
            for name in node.spec.lua_dependencies:
                inventory.lua_path(name)
            for requirement in node.spec.blob_requirements:
                if requirement.resource_class == "external":
                    inventory.external_blob_path(requirement.filename or requirement.name)
                elif requirement.resource_class == "builtin":
                    if requirement.name not in BUILTIN_BLOBS:
                        return f"unknown built-in BLOB: {requirement.name}"
                elif requirement.resource_class == "inline":
                    if not requirement.value.lower().startswith("0x"):
                        return f"invalid inline BLOB: {requirement.name}"
                else:
                    return f"unsupported BLOB resource class: {requirement.resource_class}"
        except ResourceInventoryError as exc:
            return str(exc)
        return None

    def plan(
        self,
        stage: str,
        accepted_families: Iterable[str],
        inventory: ResourceInventory,
    ) -> SearchPlan:
        accepted = tuple(dict.fromkeys(accepted_families))
        ordered = self._topological(stage, accepted)
        scheduled: list[SearchNode] = []
        skipped: list[dict[str, Any]] = []
        for node in ordered:
            reason = self._ineligible_reason(node, inventory)
            if reason is None:
                scheduled.append(node)
            else:
                skipped.append(
                    {
                        "candidate_id": node.candidate_id,
                        "family": node.spec.family,
                        "golden": node.golden,
                        "reason": reason,
                        "candidate_spec_id": node.spec.spec_id,
                    }
                )
        return SearchPlan(
            graph_id=self.graph_id,
            stage=stage,
            accepted_families=accepted,
            total_graph_nodes=len(ordered),
            golden_ids=tuple(
                node.candidate_id for node in self.stage_nodes(stage) if node.golden
            ),
            scheduled=tuple(scheduled),
            skipped=tuple(skipped),
        )


def _spec(
    candidate_id: str,
    family: str,
    lines: tuple[str, ...],
    *,
    target_binding: bool = True,
    cost: int = 1,
    complexity: int = 1,
    stage: str,
) -> CandidateSpec:
    return CandidateSpec.from_strategy(
        candidate_id=candidate_id,
        family=family,
        protocol="tls13",
        transport="tcp",
        port=443,
        l7="tls",
        strategy="\n".join(lines),
        target_binding=target_binding,
        provenance=f"native-search-graph:v1/{stage}",
        search_cost=cost,
        complexity=complexity,
    )


def _node(
    stage: str,
    candidate_id: str,
    family: str,
    lines: tuple[str, ...],
    *,
    parents: tuple[str, ...] = (),
    target_binding: bool = True,
    cost: int = 1,
    complexity: int = 1,
    golden: bool = False,
) -> SearchNode:
    return SearchNode(
        stage=stage,
        parent_ids=parents,
        spec=_spec(
            candidate_id,
            family,
            lines,
            target_binding=target_binding,
            cost=cost,
            complexity=complexity,
            stage=stage,
        ),
        golden=golden,
    )


def native_tls13_graph() -> NativeSearchGraph:
    """Return the deterministic native Zapret2 TLS 1.3 search graph."""
    fixed = ("--out-range=-d10",)
    payload = ("--payload=tls_client_hello",)
    reconnaissance = (
        _node("reconnaissance", "01-multisplit", "multisplit", fixed + payload + ("--lua-desync=multisplit:pos=1",)),
        _node("reconnaissance", "02-multidisorder", "multidisorder", fixed + payload + ("--lua-desync=multidisorder:pos=1",)),
        _node("reconnaissance", "03-seqovl", "seqovl", fixed + payload + ("--lua-desync=multisplit:pos=1:seqovl=1",)),
        _node("reconnaissance", "04-fake", "fake", fixed + payload + ("--lua-desync=fake:blob=fake_default_tls",)),
        _node("reconnaissance", "05-fake-split", "fake+split", fixed + payload + ("--lua-desync=fake:blob=fake_default_tls", "--lua-desync=multisplit:pos=1"), complexity=2),
        _node("reconnaissance", "06-syndata", "syndata", fixed + ("--lua-desync=syndata",), target_binding=False),
        _node("reconnaissance", "07-hostfakesplit", "hostfakesplit", fixed + payload + ("--lua-desync=hostfakesplit",)),
    )
    expansion = (
        _node("expansion", "multisplit-host", "multisplit", fixed + payload + ("--lua-desync=multisplit:pos=host",), parents=("01-multisplit",), cost=2),
        _node("expansion", "multisplit-midsld", "multisplit", fixed + payload + ("--lua-desync=multisplit:pos=midsld",), parents=("multisplit-host",), cost=3),
        _node("expansion", "multidisorder-host", "multidisorder", fixed + payload + ("--lua-desync=multidisorder:pos=host",), parents=("02-multidisorder",), cost=2),
        _node("expansion", "multidisorder-midsld", "multidisorder", fixed + payload + ("--lua-desync=multidisorder:pos=midsld",), parents=("multidisorder-host",), cost=3),
        _node("expansion", "seqovl-host", "seqovl", fixed + payload + ("--lua-desync=multisplit:pos=host:seqovl=1",), parents=("03-seqovl",), cost=2),
        _node("expansion", "seqovl-midsld", "seqovl", fixed + payload + ("--lua-desync=multisplit:pos=midsld:seqovl=1",), parents=("seqovl-host",), cost=3),
        _node(
            "expansion",
            GOLDEN_EXTERNAL_ID,
            "seqovl",
            (
                "--out-range=-d8",
                "--blob=fake_tls_7",
                "--payload=tls_client_hello",
                "--lua-desync=multisplit:pos=2,midsld-2:seqovl=1:seqovl_pattern=fake_tls_7",
            ),
            parents=("seqovl-midsld",),
            cost=4,
            complexity=3,
            golden=True,
        ),
        _node("expansion", "fake-repeat2", "fake", fixed + payload + ("--lua-desync=fake:blob=fake_default_tls:repeats=2",), parents=("04-fake",), cost=2),
        _node("expansion", "fake-rnd", "fake", fixed + payload + ("--lua-desync=fake:blob=fake_default_tls:tls_mod=rnd",), parents=("fake-repeat2",), cost=3),
        _node(
            "expansion",
            GOLDEN_BUILTIN_ID,
            "fake",
            payload + ("--lua-desync=fake:blob=fake_default_tls",),
            parents=("04-fake",),
            cost=2,
            golden=True,
        ),
        _node("expansion", "fake-split-host", "fake+split", fixed + payload + ("--lua-desync=fake:blob=fake_default_tls", "--lua-desync=multisplit:pos=host"), parents=("05-fake-split",), cost=2, complexity=2),
        _node("expansion", "fake-split-midsld", "fake+split", fixed + payload + ("--lua-desync=fake:blob=fake_default_tls", "--lua-desync=multisplit:pos=midsld"), parents=("fake-split-host",), cost=3, complexity=2),
        _node("expansion", "syndata-1603", "syndata", fixed + ("--lua-desync=syndata:blob=0x1603",), parents=("06-syndata",), target_binding=False, cost=2),
        _node("expansion", "syndata-160301", "syndata", fixed + ("--lua-desync=syndata:blob=0x160301",), parents=("syndata-1603",), target_binding=False, cost=3),
        _node("expansion", "hostfakesplit-mid", "hostfakesplit", fixed + payload + ("--lua-desync=hostfakesplit:midhost=midsld",), parents=("07-hostfakesplit",), cost=2),
        _node("expansion", "hostfakesplit-disorder", "hostfakesplit", fixed + payload + ("--lua-desync=hostfakesplit:midhost=midsld:disorder_after=-1",), parents=("hostfakesplit-mid",), cost=3),
    )
    return NativeSearchGraph(reconnaissance + expansion)
