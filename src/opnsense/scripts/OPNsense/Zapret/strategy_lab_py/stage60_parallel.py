"""Production Stage-60 controlled-parallel warm-worker search with cold Model-A fallback.

The adaptive graph remains authoritative. Each batch contains only candidates that are
already on the currently-resolved frontier; unresolved parent/child edges are never crossed
speculatively. Up to three independent candidates run concurrently, while pinned endpoints
inside each candidate remain sequential. Any warm-runtime infrastructure failure disables
the warm path for the rest of the stage and replays the affected candidates through the
existing cold candidate runner.
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

from . import (
    adaptive_validation,
    candidate_spec,
    endpoint_epoch,
    model_b,
    model_b_exhaustive,
    model_b_parallel,
    model_b_parallel_attribution,
    request,
    resources,
    search,
    search_graph,
    telemetry,
)

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
EX_TIMEOUT = 124
EX_CANCEL = 125
MODEL = "B-warm-worker-parallel-batched"
WIDTH = 3


class Stage60ParallelError(RuntimeError):
    """Production Stage-60 warm execution failed structurally."""


class WarmInfrastructureError(Stage60ParallelError):
    """Warm execution is unsafe/unavailable and must fall back to cold Model A."""


class Stage60Canceled(Stage60ParallelError):
    """Cancellation was observed by the Stage-60 production owner."""


def _execution_model() -> str:
    value = os.environ.get("STRATEGY_LAB_STAGE60_MODEL", "parallel").strip().lower()
    if value not in {"parallel", "cold"}:
        raise ValueError("STRATEGY_LAB_STAGE60_MODEL must be parallel or cold")
    return value


def _startup_reserve() -> float:
    return search._positive_setting_float("STRATEGY_LAB_STAGE60_WARM_STARTUP_RESERVE", 4)


def _warm_runtime_bound(bindings: Sequence[dict[str, Any]], cold_timeout: float) -> float:
    per_endpoint = model_b_parallel._positive_int_env(
        adaptive_validation.DISCOVERY_MAX_TIME_ENV,
        adaptive_validation.DISCOVERY_MAX_TIME_DEFAULT,
    ) + 1
    return max(cold_timeout, float(len(bindings) * per_endpoint))


def _bindings(epoch: endpoint_epoch.SearchEpoch) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for raw in epoch.bindings:
        if not isinstance(raw, dict):
            raise Stage60ParallelError("Stage-60 search epoch binding is invalid")
        endpoint = raw.get("endpoint")
        selected_ip = raw.get("selected_ip")
        if not isinstance(endpoint, str) or not endpoint or not isinstance(selected_ip, str) or not selected_ip:
            raise Stage60ParallelError("Stage-60 search epoch binding is invalid")
        bindings.append(dict(raw))
    if not bindings:
        raise Stage60ParallelError("Stage-60 search epoch has no pinned endpoints")
    return bindings


def _batch_decisions(
    graph: search_graph.NativeSearchGraph,
    plan: search_graph.SearchPlan,
    reconnaissance: Sequence[dict[str, Any]],
    observations: Sequence[dict[str, Any]],
    width: int,
) -> list[search_graph.SearchDecision]:
    """Choose up to width currently-ready candidates without unlocking descendants."""
    if width <= 0:
        return []
    observed_ids = {str(item.get("candidate_id", "")) for item in observations}
    skipped_ids = {
        str(item.get("candidate_id", ""))
        for item in plan.skipped
        if isinstance(item, dict)
    }
    all_expansion = {node.candidate_id: node for node in graph.stage_nodes("expansion")}
    resolved = observed_ids | skipped_ids
    ready: list[search_graph.SearchNode] = []
    for node in plan.scheduled:
        if node.candidate_id in observed_ids:
            continue
        expansion_parents = [
            parent_id for parent_id in node.parent_ids if parent_id in all_expansion
        ]
        if all(parent_id in resolved for parent_id in expansion_parents):
            ready.append(node)
    if not ready:
        if len(observed_ids) == len(plan.scheduled):
            return []
        raise Stage60ParallelError("Stage-60 adaptive planner has no reachable frontier")

    # Ask the authoritative planner to score every already-ready node against exactly the
    # same observation set. Each temporary plan retains all observed candidates plus one
    # ready candidate, so no unresolved sibling/child can be unlocked speculatively.
    decisions: list[search_graph.SearchDecision] = []
    keep_observed = observed_ids
    for node in ready:
        temporary = replace(
            plan,
            scheduled=tuple(
                item for item in plan.scheduled
                if item.candidate_id in keep_observed or item.candidate_id == node.candidate_id
            ),
        )
        decision = graph.next_expansion(temporary, reconnaissance, observations)
        if decision is None or decision.node.candidate_id != node.candidate_id:
            raise Stage60ParallelError("Stage-60 adaptive frontier scoring is inconsistent")
        decisions.append(decision)
    decisions.sort(key=lambda item: item.priority)
    return decisions[:width]


def _source_port_plan(
    plan: search_graph.SearchPlan,
    bindings: Sequence[dict[str, Any]],
) -> dict[tuple[int, int], int]:
    records = [
        {"corpus_index": index}
        for index, _node in enumerate(plan.scheduled, 1)
    ]
    return model_b_parallel._source_port_plan(records, bindings)


def _plan_index(plan: search_graph.SearchPlan) -> dict[str, int]:
    return {node.candidate_id: index for index, node in enumerate(plan.scheduled, 1)}


def _warm_record(
    decision: search_graph.SearchDecision,
    index: int,
) -> dict[str, Any]:
    description = decision.node.spec
    return {
        "path": f"stage60-parallel/{description.candidate_id}.json",
        "spec": description.to_dict(),
        "spec_id": description.spec_id,
        "classification": "unknown",
        "corpus_index": index,
    }


def _warm_endpoint_result(probe: dict[str, Any]) -> dict[str, Any]:
    execution = probe.get("execution") if isinstance(probe.get("execution"), dict) else {}
    timed_out = execution.get("timed_out") is True
    returncode = execution.get("returncode")
    if timed_out:
        exit_code = EX_TIMEOUT
    elif isinstance(returncode, int) and not isinstance(returncode, bool):
        exit_code = returncode
    else:
        exit_code = 1
    passed = probe.get("classification") == "pass"
    before = probe.get("counter_before") if isinstance(probe.get("counter_before"), dict) else {}
    after = probe.get("counter_after") if isinstance(probe.get("counter_after"), dict) else {}
    return {
        "endpoint": probe.get("endpoint"),
        "status": "PASS" if passed else "FAIL",
        "exit_code": int(exit_code),
        "transport": "tls13-ipv4",
        "detail": "",
        "selected_ip": probe.get("selected_ip"),
        "remote_ip": probe.get("remote_ip", ""),
        "endpoint_match": probe.get("endpoint_match") is True,
        "requested_local_port": probe.get("requested_local_port"),
        "observed_local_port": probe.get("observed_local_port"),
        "local_port_match": probe.get("local_port_match") is True,
        "command_source_port_match": probe.get("command_source_port_match") is True,
        "command_endpoint_match": probe.get("command_endpoint_match") is True,
        "attribution_ok": probe.get("attribution_ok") is True,
        "firewall": {
            "rule": probe.get("rule"),
            "packets_before": before.get("packets"),
            "packets_after": after.get("packets"),
            "bytes_before": before.get("bytes"),
            "bytes_after": after.get("bytes"),
            "intercepted": probe.get("intercepted") is True,
        },
        "execution": execution,
    }


def _warm_probe_candidate(
    job_id: str,
    slot: model_b.Slot,
    record: dict[str, Any],
    bindings: Sequence[dict[str, Any]],
    wan: str,
    source_ports: dict[tuple[int, int], int],
    start_barrier: threading.Barrier,
) -> dict[str, Any]:
    try:
        start_barrier.wait(timeout=3)
    except threading.BrokenBarrierError as exc:
        raise WarmInfrastructureError("Stage-60 warm batch start barrier failed") from exc
    started = time.monotonic()
    endpoint_probes: list[dict[str, Any]] = []
    for endpoint_index, binding in enumerate(bindings, 1):
        if search._cancel_requested(job_id):
            raise Stage60Canceled("Strategy Lab cancellation requested")
        probe = model_b_parallel_attribution._probe_endpoint(
            slot,
            binding,
            wan,
            source_ports[(int(record["corpus_index"]), endpoint_index)],
        )
        if probe.get("attribution_ok") is not True:
            raise WarmInfrastructureError(
                f"Stage-60 warm route attribution failed for {record['spec_id']}"
            )
        endpoint_probes.append(probe)
    ended = time.monotonic()
    classification = "pass" if endpoint_probes and all(
        item.get("classification") == "pass" for item in endpoint_probes
    ) else "fail"
    return {
        "slot": slot.name,
        "candidate_id": record["spec"].get("candidate_id"),
        "spec_id": record["spec_id"],
        "corpus_index": record["corpus_index"],
        "classification": classification,
        "endpoint_probes": endpoint_probes,
        "candidate_elapsed_ms": round((ended - started) * 1000),
        "_started": started,
        "_ended": ended,
    }


def _warm_batch(
    job_id: str,
    decisions: Sequence[search_graph.SearchDecision],
    bindings: Sequence[dict[str, Any]],
    inventory: resources.ResourceInventory,
    source_ports: dict[tuple[int, int], int],
    indexes: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not decisions or len(decisions) > WIDTH:
        raise WarmInfrastructureError("Stage-60 warm batch width is invalid")
    slots = model_b_exhaustive.BATCH_SLOTS[: len(decisions)]
    cleanup_ok = False
    batch_started = time.monotonic()
    try:
        model_b._require_adapter("cleanup-all", timeout=25)
        model_b._require_adapter("preflight")
        wan = model_b._require_adapter("wan").strip()
        if not wan:
            raise WarmInfrastructureError("Stage-60 warm WAN interface could not be resolved")

        records: dict[str, dict[str, Any]] = {}
        workers: dict[str, dict[str, Any]] = {}
        for slot, decision in zip(slots, decisions):
            record = _warm_record(decision, indexes[decision.node.candidate_id])
            records[slot.name] = record
            workers[slot.name] = model_b_exhaustive._write_worker_runtime(
                slot, record, inventory, bindings
            )

        pool_started = time.monotonic()
        for slot in slots:
            model_b._require_adapter("launch", slot.name, str(slot.port))
        pool = model_b._wait_pool_ready(slots)
        startup_ms = round((time.monotonic() - pool_started) * 1000)
        ready = all(pool.get(slot.name, {}).get("ready") is True for slot in slots)
        pids = [pool.get(slot.name, {}).get("pid") for slot in slots]
        ports = [pool.get(slot.name, {}).get("divert_port") for slot in slots]
        unique = (
            ready
            and None not in pids
            and len(set(pids)) == len(slots)
            and len(set(ports)) == len(slots)
            and set(ports) == {slot.port for slot in slots}
        )
        rss = model_b._rss_summary(pool)
        if not ready or not unique or not bool(rss.get("all_numeric")):
            raise WarmInfrastructureError("Stage-60 warm worker pool did not reach unambiguous readiness")

        barrier = threading.Barrier(len(slots))
        parallel_started = time.monotonic()
        with ThreadPoolExecutor(max_workers=len(slots), thread_name_prefix="strategy-lab-stage60") as executor:
            futures = {
                slot.name: executor.submit(
                    _warm_probe_candidate,
                    job_id,
                    slot,
                    records[slot.name],
                    bindings,
                    wan,
                    source_ports,
                    barrier,
                )
                for slot in slots
            }
            probes = [futures[slot.name].result() for slot in slots]
        parallel_wall_ms = round((time.monotonic() - parallel_started) * 1000)
        intervals = [(float(item["_started"]), float(item["_ended"])) for item in probes]
        max_overlap = model_b_parallel._max_overlap(intervals)
        if len(slots) > 1 and max_overlap < len(slots):
            raise WarmInfrastructureError("Stage-60 warm candidate overlap was not observed")
        if max_overlap > WIDTH:
            raise WarmInfrastructureError("Stage-60 warm concurrency exceeded the production width")
        if not model_b._all_survivors_ready(slots):
            raise WarmInfrastructureError("Stage-60 warm worker pool became unstable during probing")

        candidates: list[dict[str, Any]] = []
        for slot, decision, probe in zip(slots, decisions, probes):
            probe.pop("_started", None)
            probe.pop("_ended", None)
            description = decision.node.spec
            endpoint_results = [_warm_endpoint_result(item) for item in probe["endpoint_probes"]]
            candidate = {
                "id": description.candidate_id,
                "family": description.family,
                "strategy": description.strategy,
                "candidate_spec": description.to_dict(),
                "resource_inventory_id": inventory.inventory_id,
                "runtime_arguments": list(workers[slot.name]["runtime_arguments"]),
                "search_epoch_id": bindings[0].get("epoch_id") or "",
                "endpoint_bindings": list(bindings),
                "endpoints": endpoint_results,
                "all_pass": probe["classification"] == "pass",
                "runtime": {
                    "execution_model": MODEL,
                    "slot": slot.name,
                    "divert_port": slot.port,
                    "rule": slot.rule,
                    "snapshot": pool.get(slot.name),
                },
                "timing": {
                    "total_ms": int(probe["candidate_elapsed_ms"]),
                    "parallel_batch_wall_ms": parallel_wall_ms,
                    "pool_startup_ms": startup_ms,
                },
            }
            candidates.append(candidate)

        batch = {
            "execution_model": MODEL,
            "width": len(slots),
            "max_overlap_observed": max_overlap,
            "pool_startup_ms": startup_ms,
            "parallel_probe_wall_ms": parallel_wall_ms,
            "rss": rss,
            "workers": workers,
            "candidate_ids": [decision.node.candidate_id for decision in decisions],
            "total_ms": round((time.monotonic() - batch_started) * 1000),
        }
        return candidates, batch
    except Stage60Canceled:
        raise
    except (
        model_b.ModelBExperimentError,
        model_b_parallel.ModelBParallelError,
        candidate_spec.CandidateSpecError,
        request.RequestError,
        resources.ResourceInventoryError,
        OSError,
        ValueError,
    ) as exc:
        raise WarmInfrastructureError(str(exc)) from exc
    finally:
        cleanup_ok = model_b._try_adapter("cleanup-all", timeout=25)
        if not cleanup_ok and not search._cancel_requested(job_id):
            # The shell runner also owns an unconditional exit trap. Raising here makes the
            # warm path fail closed and prevents another warm batch from being admitted.
            raise WarmInfrastructureError("Stage-60 warm batch cleanup failed")


def _cold_candidate(
    job_id: str,
    endpoints: Path,
    work: Path,
    runner: Path,
    decision: search_graph.SearchDecision,
    epoch: endpoint_epoch.SearchEpoch,
    inventory: resources.ResourceInventory,
    timeout: float,
) -> tuple[dict[str, Any], int]:
    description = decision.node.spec
    candidate_id = description.candidate_id
    family = description.family
    strategy = description.strategy
    strategy_path = work / f"{candidate_id}.args"
    strategy_path.write_text(strategy, encoding="utf-8")
    os.chmod(strategy_path, 0o644)
    spec_path = work / f"{candidate_id}.spec.json"
    search._atomic_json(spec_path, description.to_dict())
    candidate_path = work / f"{candidate_id}.json"
    try:
        candidate_path.unlink()
    except FileNotFoundError:
        pass
    command = [
        str(runner), job_id, str(endpoints), str(candidate_path), candidate_id,
        family, str(strategy_path), "1" if description.target_binding else "0", str(spec_path),
    ]
    status, timed_out, runner_ms = search._run_candidate(command, timeout, job_id)
    if status == EX_CANCEL:
        raise Stage60Canceled("Strategy Lab cancellation requested")
    if timed_out:
        candidate = search._timeout_result(
            candidate_id,
            family,
            strategy,
            job_id=job_id,
            description=description,
            epoch=epoch,
            runner_ms=runner_ms,
        )
        search._atomic_json(candidate_path, candidate)
    elif status != 0:
        raise Stage60ParallelError(
            f"Strategy Lab expansion candidate runner failed for {candidate_id} with status {status}"
        )
    else:
        candidate = search._read_candidate(candidate_path, candidate_id)
    return candidate, runner_ms


def _persist_candidate(
    job_id: str,
    output: Path,
    result: dict[str, Any],
    candidate: dict[str, Any],
    decision: search_graph.SearchDecision,
    epoch: endpoint_epoch.SearchEpoch,
    inventory: resources.ResourceInventory,
    duration_ms: int,
    execution_model: str,
) -> None:
    description = decision.node.spec
    candidate_id = description.candidate_id
    if candidate.get("search_epoch_id") not in {None, "", epoch.epoch_id}:
        raise Stage60ParallelError(
            f"Strategy Lab expansion candidate changed search epoch: {candidate_id}"
        )
    candidate["search_epoch_id"] = epoch.epoch_id
    candidate["search_epoch_generation"] = epoch.generation
    candidate["endpoint_bindings"] = list(epoch.bindings)
    candidate["strategy"] = description.strategy
    candidate["candidate_spec"] = description.to_dict()
    candidate["resource_inventory_id"] = inventory.inventory_id
    candidate["graph_node"] = decision.node.to_dict()
    candidate["runner_duration_ms"] = duration_ms
    candidate["stage60_execution_model"] = execution_model
    passed = candidate.get("all_pass") is True
    schedule_item = decision.to_dict()
    schedule_item.update(
        sequence=len(result["candidates"]) + 1,
        outcome="pass" if passed else "fail",
        duration_ms=duration_ms,
        execution_model=execution_model,
    )
    result["schedule"].append(schedule_item)
    result["candidates"].append(candidate)
    result["completed"] = len(result["candidates"])
    result["working"] = [
        str(item.get("id", "")) for item in result["candidates"] if item.get("all_pass") is True
    ]
    result["failed"] = [
        str(item.get("id", "")) for item in result["candidates"] if item.get("all_pass") is not True
    ]
    result["early_stop"]["winner_count"] = len(result["working"])
    search._atomic_json(output, result)
    telemetry.record(
        search.job_dir(job_id),
        "adaptive_candidate",
        duration_ms,
        stage="60",
        candidate_id=candidate_id,
        protocol="tls13",
        outcome="pass" if passed else "fail",
        details={
            "search_epoch_id": epoch.epoch_id,
            "decision": schedule_item,
            "execution_model": execution_model,
        },
    )


def _budget_timeout_result(
    job_id: str,
    output: Path,
    result: dict[str, Any],
    candidate_id: str,
    remaining: float | None,
    required: float,
    execution_model: str,
) -> int:
    result["stopped_reason"] = "insufficient_stage_budget"
    result["partial"] = True
    result["budget_admission"] = {
        "next_candidate": candidate_id,
        "remaining_seconds": round(remaining or 0.0, 3),
        "required_seconds": round(required, 3),
        "execution_model": execution_model,
    }
    search._persist_partial_result(job_id, "parameter_expansion", output, result)
    telemetry.record(
        search.job_dir(job_id),
        "candidate_admission",
        0,
        stage="60",
        candidate_id=candidate_id,
        protocol="tls13",
        outcome="deferred",
        details=result["budget_admission"],
    )
    return EX_TIMEOUT


def expand(job_id: str, endpoints_file: str, family_result_file: str, result_file: str) -> int:
    if not search.JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    family_path = Path(family_result_file)
    if not endpoints.is_file() or not family_path.is_file():
        return EX_USAGE
    if _execution_model() == "cold":
        return search.expand(job_id, endpoints_file, family_result_file, result_file)

    output = Path(result_file)
    endpoint_values = [
        line.strip() for line in endpoints.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    epoch = endpoint_epoch.load(search.job_dir(job_id), endpoint_values)
    bindings = _bindings(epoch)
    family_result = search._load_json(family_path)
    accepted_raw = family_result.get("accepted", [])
    if not isinstance(accepted_raw, list) or not all(isinstance(item, str) for item in accepted_raw):
        raise Stage60ParallelError("Strategy Lab Stage-50 family evidence is invalid")
    reconnaissance = family_result.get("families", [])
    if not isinstance(reconnaissance, list):
        raise Stage60ParallelError("Strategy Lab Stage-50 candidate evidence is invalid")
    if family_result.get("search_epoch_id") != epoch.epoch_id:
        raise Stage60ParallelError("Strategy Lab Stage-50 evidence belongs to another search epoch")

    inventory = resources.ensure_job_inventory(search.job_dir(job_id))
    graph = search_graph.native_tls13_graph()
    plan = graph.plan("expansion", accepted_raw, inventory)
    plan_evidence = plan.to_dict()
    plan_evidence["search_epoch_id"] = epoch.epoch_id
    search._atomic_json(search.job_dir(job_id) / "search-graph.json", plan_evidence)

    runner = search._candidate_runner("STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER")
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise Stage60ParallelError(f"Strategy Lab expansion candidate runner is unavailable: {runner}")
    timeout = search._positive_float("STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT", 5)
    operation_deadline = search._operation_deadline_monotonic()
    target = search._positive_int("STRATEGY_LAB_EXPANSION_TARGET", 3)
    minimum = search._positive_int("STRATEGY_LAB_EXPANSION_MIN_WINNERS", min(2, target))
    if minimum > target:
        raise ValueError("STRATEGY_LAB_EXPANSION_MIN_WINNERS cannot exceed the winner target")

    work = search.job_dir(job_id) / "parameter-expansion"
    work.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "search_graph_id": plan.graph_id,
        "search_epoch_id": epoch.epoch_id,
        "planner_schema": search_graph.ADAPTIVE_PLANNER_SCHEMA,
        "total_graph_nodes": plan.total_graph_nodes,
        "total_available": len(plan.scheduled),
        "completed": 0,
        "candidates": [],
        "working": [],
        "failed": [],
        "golden_ids": list(plan.golden_ids),
        "skipped": list(plan.skipped),
        "schedule": [],
        "winner_band": {"minimum": minimum, "target": target},
        "early_stop": {"triggered": False, "winner_count": 0},
        "stopped_reason": "",
        "partial": False,
        "execution_model": MODEL,
        "parallel": {
            "width": WIDTH,
            "cpu_policy": "no_cpu_gating",
            "endpoint_probes_parallel": False,
            "batches": [],
            "fallbacks": [],
            "cold_fallback_available": True,
        },
    }
    search._atomic_json(output, result)
    if not plan.scheduled:
        result["stopped_reason"] = "graph_exhausted"
        search._atomic_json(output, result)
        return EX_OK

    observations: list[dict[str, Any]] = []
    indexes = _plan_index(plan)
    source_ports = _source_port_plan(plan, bindings)
    warm_enabled = True
    batch_number = 0

    try:
        while True:
            if search._cancel_requested(job_id):
                return EX_CANCEL
            remaining_winners = max(1, target - len(result["working"]))
            width = min(WIDTH if warm_enabled else 1, remaining_winners)
            decisions = _batch_decisions(graph, plan, reconnaissance, observations, width)
            if not decisions:
                break
            first_id = decisions[0].node.candidate_id

            admission_timeout = (
                _warm_runtime_bound(bindings, timeout) + _startup_reserve()
                if warm_enabled else timeout
            )
            admitted, remaining, required = search._candidate_admission(
                admission_timeout, operation_deadline
            )
            if not admitted:
                return _budget_timeout_result(
                    job_id,
                    output,
                    result,
                    first_id,
                    remaining,
                    required,
                    MODEL if warm_enabled else "A-cold-fallback",
                )

            batch_number += 1
            batch_candidates: list[dict[str, Any]] = []
            batch_evidence: dict[str, Any] = {
                "batch": batch_number,
                "candidate_ids": [item.node.candidate_id for item in decisions],
                "requested_width": len(decisions),
            }
            if warm_enabled:
                try:
                    batch_candidates, warm_evidence = _warm_batch(
                        job_id, decisions, bindings, inventory, source_ports, indexes
                    )
                    batch_evidence.update(warm_evidence)
                    batch_evidence["outcome"] = "warm"
                except Stage60Canceled:
                    return EX_CANCEL
                except WarmInfrastructureError as exc:
                    model_b._try_adapter("cleanup-all", timeout=25)
                    warm_enabled = False
                    fallback = {
                        "batch": batch_number,
                        "candidate_ids": [item.node.candidate_id for item in decisions],
                        "reason": str(exc),
                        "fallback_model": "A-cold",
                    }
                    result["parallel"]["fallbacks"].append(fallback)
                    batch_evidence["outcome"] = "cold-fallback"
                    batch_evidence["warm_error"] = str(exc)
                    telemetry.record(
                        search.job_dir(job_id),
                        "stage60_parallel_fallback",
                        0,
                        stage="60",
                        outcome="fallback",
                        details=fallback,
                    )

            if not warm_enabled and not batch_candidates:
                batch_candidates = []
                for decision in decisions:
                    admitted, remaining, required = search._candidate_admission(
                        timeout, operation_deadline
                    )
                    if not admitted:
                        result["parallel"]["batches"].append(batch_evidence)
                        return _budget_timeout_result(
                            job_id,
                            output,
                            result,
                            decision.node.candidate_id,
                            remaining,
                            required,
                            "A-cold-fallback",
                        )
                    candidate, runner_ms = _cold_candidate(
                        job_id, endpoints, work, runner, decision, epoch, inventory, timeout
                    )
                    candidate["_stage60_duration_ms"] = runner_ms
                    batch_candidates.append(candidate)
                batch_evidence["execution_model"] = "A-cold-fallback"

            for decision, candidate in zip(decisions, batch_candidates):
                duration_ms = int(
                    candidate.pop(
                        "_stage60_duration_ms",
                        (candidate.get("timing") or {}).get("total_ms", 0),
                    )
                )
                execution_model = (
                    MODEL if batch_evidence.get("outcome") == "warm" else "A-cold-fallback"
                )
                _persist_candidate(
                    job_id,
                    output,
                    result,
                    candidate,
                    decision,
                    epoch,
                    inventory,
                    duration_ms,
                    execution_model,
                )
                observations.append(
                    {
                        "candidate_id": decision.node.candidate_id,
                        "all_pass": candidate.get("all_pass") is True,
                    }
                )

            result["parallel"]["batches"].append(batch_evidence)
            result["parallel"]["warm_enabled"] = warm_enabled
            search._atomic_json(output, result)
            if len(result["working"]) >= target:
                result["stopped_reason"] = "enough_candidates"
                result["early_stop"]["triggered"] = True
                search._atomic_json(output, result)
                return EX_OK

        result["stopped_reason"] = "graph_exhausted"
        result["early_stop"]["winner_count"] = len(result["working"])
        result["early_stop"]["within_normal_band"] = minimum <= len(result["working"]) <= target
        search._atomic_json(output, result)
        return EX_OK
    finally:
        model_b._try_adapter("cleanup-all", timeout=25)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) == 5 and args[0] == "expand":
        try:
            return expand(args[1], args[2], args[3], args[4])
        except Stage60Canceled:
            return EX_CANCEL
        except (Stage60ParallelError, search_graph.SearchGraphError, endpoint_epoch.EndpointEpochError) as exc:
            print(f"ERROR: {exc}", file=os.sys.stderr)
            return EX_SOFTWARE
    raise ValueError("stage60-parallel requires: expand JOB ENDPOINTS FAMILY_RESULT OUTPUT")
