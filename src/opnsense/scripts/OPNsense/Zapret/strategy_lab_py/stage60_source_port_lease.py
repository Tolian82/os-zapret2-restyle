"""Stage-60 controlled source-port leasing for Model C and Model B.

The native search graph still owns candidate order. This layer changes only the concrete
client source ports used by an admitted warm batch. Preferred deterministic ports are kept
when free. A port already owned by another socket is never killed or reused; the batch gets
a free alternate above the deterministic plan instead. Model C and its Model B fallback
lease independently so a collision or race in the preferred path cannot poison fallback.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from . import model_b, stage60_model_c, stage60_parallel

SCAN_LIMIT_ENV = "STRATEGY_LAB_STAGE60_SOURCE_PORT_SCAN_LIMIT"
SCAN_LIMIT_DEFAULT = 2048
MIN_SOURCE_PORT = 1024
MAX_SOURCE_PORT = 65535


class SourcePortLeaseError(stage60_parallel.WarmInfrastructureError):
    """No exact free source-port lease can be proven for the admitted warm batch."""


def _scan_limit() -> int:
    raw = os.environ.get(SCAN_LIMIT_ENV, str(SCAN_LIMIT_DEFAULT))
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise SourcePortLeaseError(f"invalid {SCAN_LIMIT_ENV}") from exc
    if value <= 0:
        raise SourcePortLeaseError(f"invalid {SCAN_LIMIT_ENV}")
    return value


def _port_free(port: int) -> bool:
    if port < MIN_SOURCE_PORT or port > MAX_SOURCE_PORT:
        return False
    return model_b._try_adapter("source-port-free", str(port))


def _candidate_ports(
    decisions: Sequence[Any],
    bindings: Sequence[dict[str, Any]],
    ports: dict[tuple[int, int], int],
    indexes: dict[str, int],
) -> dict[str, list[int]]:
    evidence: dict[str, list[int]] = {}
    for decision in decisions:
        candidate_id = str(decision.node.candidate_id)
        if candidate_id not in indexes:
            raise SourcePortLeaseError(f"Stage-60 source-port index is missing: {candidate_id}")
        corpus_index = indexes[candidate_id]
        values: list[int] = []
        for endpoint_index in range(1, len(bindings) + 1):
            key = (corpus_index, endpoint_index)
            value = ports.get(key)
            if isinstance(value, bool) or not isinstance(value, int):
                raise SourcePortLeaseError(
                    f"Stage-60 preferred source port is missing: {candidate_id}/{endpoint_index}"
                )
            values.append(value)
        evidence[candidate_id] = values
    return evidence


def lease_batch_source_ports(
    decisions: Sequence[Any],
    bindings: Sequence[dict[str, Any]],
    preferred_ports: dict[tuple[int, int], int],
    indexes: dict[str, int],
) -> tuple[dict[tuple[int, int], int], dict[str, Any]]:
    """Return an exact free source-port map for one currently admitted warm batch."""
    if not decisions or not bindings or not preferred_ports:
        raise SourcePortLeaseError("Stage-60 source-port lease input is empty")

    preferred_evidence = _candidate_ports(decisions, bindings, preferred_ports, indexes)
    all_preferred = list(preferred_ports.values())
    if any(isinstance(value, bool) or not isinstance(value, int) for value in all_preferred):
        raise SourcePortLeaseError("Stage-60 preferred source-port plan is invalid")
    if any(value < MIN_SOURCE_PORT or value > MAX_SOURCE_PORT for value in all_preferred):
        raise SourcePortLeaseError("Stage-60 preferred source-port plan is outside TCP range")

    alternate = max(all_preferred) + 1
    scan_limit = _scan_limit()
    scanned = 0
    selected: set[int] = set()
    leased: dict[tuple[int, int], int] = {}
    collisions: list[dict[str, Any]] = []

    def next_alternate() -> int:
        nonlocal alternate, scanned
        while alternate <= MAX_SOURCE_PORT and scanned < scan_limit:
            candidate = alternate
            alternate += 1
            scanned += 1
            if candidate in selected:
                continue
            if _port_free(candidate):
                return candidate
        raise SourcePortLeaseError("Stage-60 controlled source-port alternate pool is exhausted")

    for decision in decisions:
        candidate_id = str(decision.node.candidate_id)
        corpus_index = indexes[candidate_id]
        for endpoint_index, binding in enumerate(bindings, 1):
            key = (corpus_index, endpoint_index)
            preferred = preferred_ports[key]
            if preferred not in selected and _port_free(preferred):
                chosen = preferred
            else:
                chosen = next_alternate()
                collisions.append(
                    {
                        "candidate_id": candidate_id,
                        "endpoint": str(binding.get("endpoint", "")),
                        "endpoint_index": endpoint_index,
                        "preferred_port": preferred,
                        "leased_port": chosen,
                    }
                )
            leased[key] = chosen
            selected.add(chosen)

    leased_evidence = _candidate_ports(decisions, bindings, leased, indexes)
    return leased, {
        "policy": "preferred-free-else-alternate",
        "foreign_port_action": "skip-only",
        "preferred_ports": preferred_evidence,
        "leased_ports": leased_evidence,
        "collisions": collisions,
        "replacement_count": len(collisions),
        "alternate_scan_count": scanned,
    }


@contextmanager
def install() -> Iterator[None]:
    """Patch the current Model-C owner and Model-B fallback for one Stage-60 invocation."""
    original_model_c_batch = stage60_model_c._bucket_batch
    original_model_b_batch = stage60_parallel._warm_batch

    def leased_model_c_batch(
        job_id: str,
        decisions: Sequence[Any],
        bindings: Sequence[dict[str, Any]],
        inventory: Any,
        source_ports: dict[tuple[int, int], int],
        indexes: dict[str, int],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        try:
            leased, lease_evidence = lease_batch_source_ports(
                decisions, bindings, source_ports, indexes
            )
        except SourcePortLeaseError as exc:
            raise stage60_model_c.ModelCInfrastructureError(str(exc)) from exc
        candidates, evidence = original_model_c_batch(
            job_id, decisions, bindings, inventory, leased, indexes
        )
        evidence = dict(evidence)
        evidence["source_port_lease"] = lease_evidence
        return candidates, evidence

    def leased_model_b_batch(
        job_id: str,
        decisions: Sequence[Any],
        bindings: Sequence[dict[str, Any]],
        inventory: Any,
        source_ports: dict[tuple[int, int], int],
        indexes: dict[str, int],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        leased, lease_evidence = lease_batch_source_ports(
            decisions, bindings, source_ports, indexes
        )
        candidates, evidence = original_model_b_batch(
            job_id, decisions, bindings, inventory, leased, indexes
        )
        evidence = dict(evidence)
        evidence["source_port_lease"] = lease_evidence
        return candidates, evidence

    stage60_model_c._bucket_batch = leased_model_c_batch
    stage60_parallel._warm_batch = leased_model_b_batch
    try:
        yield
    finally:
        stage60_model_c._bucket_batch = original_model_c_batch
        stage60_parallel._warm_batch = original_model_b_batch
