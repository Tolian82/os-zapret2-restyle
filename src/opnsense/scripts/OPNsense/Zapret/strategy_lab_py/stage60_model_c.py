"""Production Stage-60 Model C: one warm dvtws2 bucket with exact source-port dispatch.

The existing adaptive Stage-60 planner remains authoritative. A batch contains at most
three already-ready candidates. One physical dvtws2 process owns the batch; each candidate
keeps a unique controlled client source-port set, and a small Lua condition selects exactly
that candidate's existing Lua action chain. Candidate-specific payload/range/BLOB semantics
are preserved when the bucket is rendered. Any Model-C infrastructure/dispatcher failure
fails closed to the accepted production Model-B batch; Model B retains its cold Model-A
fallback in the underlying Stage-60 owner.
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Sequence

from . import (
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
    stage60_parallel,
)

MODEL = "C-warm-bucket-source-port-dispatch"
MODEL_B = stage60_parallel.MODEL
WIDTH = stage60_parallel.WIDTH
SELECTOR_FUNCTION = "strategy_lab_model_c_source_port"
SELECTOR_ENV = "STRATEGY_LAB_MODEL_C_SELECTOR_LUA"


class ModelCInfrastructureError(stage60_parallel.WarmInfrastructureError):
    """Model C cannot prove exact dispatcher/runtime ownership and must fall back."""


def _requested_model() -> str:
    value = os.environ.get("STRATEGY_LAB_STAGE60_MODEL", "model-c").strip().lower()
    aliases = {
        "model-c": "model-c",
        "bucket": "model-c",
        "model-b": "model-b",
        "parallel": "model-b",
        "cold": "cold",
    }
    if value not in aliases:
        raise ValueError("STRATEGY_LAB_STAGE60_MODEL must be model-c, model-b, or cold")
    return aliases[value]


def _selector_lua_path() -> Path:
    default = Path(__file__).resolve().parent.parent / "strategy_lab_model_c.lua"
    path = Path(os.environ.get(SELECTOR_ENV, str(default))).resolve(strict=False)
    if not path.is_file() or path.stat().st_size <= 0:
        raise ModelCInfrastructureError(f"Model C selector Lua is unavailable: {path}")
    return path


def _mapped_blob_declaration(line: str, inventory: resources.ResourceInventory) -> str:
    value = line.removeprefix("--blob=")
    name, separator, _source = value.partition(":")
    if separator:
        return line
    return f"--blob={name}:@{inventory.external_blob_path(name)}"


def _candidate_payload(spec: candidate_spec.CandidateSpec) -> str:
    payloads = [
        line.removeprefix("--payload=")
        for line in spec.strategy_lines
        if line.startswith("--payload=")
    ]
    if len(payloads) > 1:
        raise ModelCInfrastructureError(
            f"Model C candidate has multiple payload filters: {spec.candidate_id}"
        )
    return payloads[0] if payloads else "all"


def _bucket_profile_key(spec: candidate_spec.CandidateSpec) -> tuple[str, str, int, str | None, bool]:
    return (spec.l3, spec.transport, spec.port, spec.l7, spec.target_binding)


def _compatible_batch_segments(
    decisions: Sequence[search_graph.SearchDecision],
) -> list[list[search_graph.SearchDecision]]:
    segments: list[list[search_graph.SearchDecision]] = []
    current: list[search_graph.SearchDecision] = []
    profile: tuple[str, str, int, str | None, bool] | None = None
    for decision in decisions:
        decision_profile = _bucket_profile_key(decision.node.spec)
        if current and decision_profile != profile:
            segments.append(current)
            current = []
        if not current:
            profile = decision_profile
        current.append(decision)
    if current:
        segments.append(current)
    return segments


def _validate_bucket_spec(spec: candidate_spec.CandidateSpec) -> None:
    if (
        spec.render_mode != "fragment"
        or spec.l3 != "ipv4"
        or spec.transport != "tcp"
        or spec.port != 443
        or spec.l7 != "tls"
    ):
        raise ModelCInfrastructureError(
            f"Model C candidate is outside the compatible TLS/IPv4/TCP/443 bucket: {spec.candidate_id}"
        )
    allowed = ("--blob=", "--payload=", "--in-range=", "--out-range=", "--lua-desync=")
    unsupported = [line for line in spec.strategy_lines if not line.startswith(allowed)]
    if unsupported:
        raise ModelCInfrastructureError(
            f"Model C candidate has unsupported profile directives: {spec.candidate_id}"
        )
    if not spec.lua_instances:
        raise ModelCInfrastructureError(f"Model C candidate has no Lua actions: {spec.candidate_id}")


def _render_bucket_arguments(
    specs: Sequence[candidate_spec.CandidateSpec],
    selector_ports: dict[str, Sequence[int]],
    inventory: resources.ResourceInventory,
    *,
    divert_port: int,
    hostlist_path: Path | None,
    selector_lua: Path,
) -> tuple[str, ...]:
    if not specs or len(specs) > WIDTH:
        raise ModelCInfrastructureError("Model C bucket width is invalid")
    for spec in specs:
        _validate_bucket_spec(spec)

    compatibility = {_bucket_profile_key(spec) for spec in specs}
    if len(compatibility) != 1:
        raise ModelCInfrastructureError("Model C bucket candidates are not profile-compatible")
    if specs[0].target_binding and hostlist_path is None:
        raise ModelCInfrastructureError("Model C target hostlist is unavailable")

    lua_names: list[str] = []
    for spec in specs:
        for name in spec.lua_dependencies:
            if name not in lua_names:
                lua_names.append(name)
    if "zapret-auto.lua" not in lua_names:
        lua_names.append("zapret-auto.lua")

    arguments: list[str] = [f"--port={divert_port}"]
    arguments.extend(f"--lua-init=@{inventory.lua_path(name)}" for name in lua_names)
    arguments.append(f"--lua-init=@{selector_lua}")
    arguments.extend(("--filter-tcp=443", "--filter-l7=tls"))
    if specs[0].target_binding:
        assert hostlist_path is not None
        arguments.append(f"--hostlist={hostlist_path}")

    declarations: dict[str, str] = {}
    for spec in specs:
        for line in spec.strategy_lines:
            if not line.startswith("--blob="):
                continue
            mapped = _mapped_blob_declaration(line, inventory)
            name = mapped.removeprefix("--blob=").partition(":")[0]
            previous = declarations.get(name)
            if previous is not None and previous != mapped:
                raise ModelCInfrastructureError(f"Model C BLOB declaration conflicts: {name}")
            declarations[name] = mapped
    arguments.extend(declarations.values())

    for spec in specs:
        ports = tuple(int(value) for value in selector_ports.get(spec.candidate_id, ()))
        if not ports or len(set(ports)) != len(ports) or any(not 1 <= value <= 65535 for value in ports):
            raise ModelCInfrastructureError(
                f"Model C selector source-port set is invalid: {spec.candidate_id}"
            )
        arguments.append(f"--in-range={spec.in_range or 'x'}")
        arguments.append(f"--out-range={spec.out_range or 'a'}")
        arguments.append(f"--payload={_candidate_payload(spec)}")
        arguments.append(
            "--lua-desync=condition"
            f":iff={SELECTOR_FUNCTION}"
            f":candidate_id={spec.candidate_id}"
            f":source_ports={','.join(str(value) for value in ports)}"
            f":instances={len(spec.lua_instances)}"
        )
        arguments.extend(instance.raw for instance in spec.lua_instances)
    return tuple(arguments)


def _bucket_route_slots(width: int) -> tuple[model_b.Slot, ...]:
    physical = model_b_exhaustive.BATCH_SLOTS[0]
    return tuple(
        model_b.Slot(slot.name, physical.port, slot.rule, f"model-c-route-{index}")
        for index, slot in enumerate(model_b_exhaustive.BATCH_SLOTS[:width], 1)
    )


def _write_bucket_runtime(
    decisions: Sequence[search_graph.SearchDecision],
    bindings: Sequence[dict[str, Any]],
    inventory: resources.ResourceInventory,
    source_ports: dict[tuple[int, int], int],
    indexes: dict[str, int],
) -> dict[str, Any]:
    physical = model_b_exhaustive.BATCH_SLOTS[0]
    root = model_b.session_dir() / "workers" / physical.name
    root.mkdir(parents=True, exist_ok=True)
    endpoints = [str(binding["endpoint"]) for binding in bindings]
    specs = [decision.node.spec for decision in decisions]
    hostlist: Path | None = None
    if specs[0].target_binding:
        hostlist = root / "hostlist.txt"
        hostlist.write_text("".join(f"{endpoint}\n" for endpoint in endpoints), encoding="utf-8")
        os.chmod(hostlist, 0o644)

    selector_ports: dict[str, tuple[int, ...]] = {}
    for decision in decisions:
        index = indexes[decision.node.candidate_id]
        selector_ports[decision.node.candidate_id] = tuple(
            source_ports[(index, endpoint_index)]
            for endpoint_index in range(1, len(bindings) + 1)
        )
    selector_lua = _selector_lua_path()
    arguments = _render_bucket_arguments(
        specs,
        selector_ports,
        inventory,
        divert_port=physical.port,
        hostlist_path=hostlist,
        selector_lua=selector_lua,
    )
    args_path = root / "dvtws.args"
    args_path.write_text("".join(f"{item}\n" for item in arguments), encoding="utf-8")
    os.chmod(args_path, 0o644)
    return {
        "physical_slot": physical.name,
        "divert_port": physical.port,
        "selector": SELECTOR_FUNCTION,
        "selector_lua": str(selector_lua),
        "candidate_ids": [spec.candidate_id for spec in specs],
        "selector_ports": {key: list(value) for key, value in selector_ports.items()},
        "target_endpoints": endpoints,
        "runtime_arguments": list(arguments),
    }


def _bucket_probe_candidate(
    job_id: str,
    route_slot: model_b.Slot,
    record: dict[str, Any],
    bindings: Sequence[dict[str, Any]],
    wan: str,
    source_ports: dict[tuple[int, int], int],
    start_barrier: threading.Barrier,
) -> dict[str, Any]:
    try:
        start_barrier.wait(timeout=3)
    except threading.BrokenBarrierError as exc:
        raise ModelCInfrastructureError("Model C batch start barrier failed") from exc
    started = time.monotonic()
    endpoint_probes: list[dict[str, Any]] = []
    for endpoint_index, binding in enumerate(bindings, 1):
        if search._cancel_requested(job_id):
            raise stage60_parallel.Stage60Canceled("Strategy Lab cancellation requested")
        local_port = source_ports[(int(record["corpus_index"]), endpoint_index)]
        probe = model_b_parallel_attribution._probe_endpoint(
            route_slot, binding, wan, local_port
        )
        if probe.get("attribution_ok") is not True:
            raise ModelCInfrastructureError(
                f"Model C route attribution failed for {record['spec_id']}"
            )
        endpoint_probes.append(probe)
    ended = time.monotonic()
    classification = "pass" if endpoint_probes and all(
        item.get("classification") == "pass" for item in endpoint_probes
    ) else "fail"
    return {
        "slot": route_slot.name,
        "candidate_id": record["spec"].get("candidate_id"),
        "spec_id": record["spec_id"],
        "corpus_index": record["corpus_index"],
        "classification": classification,
        "endpoint_probes": endpoint_probes,
        "candidate_elapsed_ms": round((ended - started) * 1000),
        "_started": started,
        "_ended": ended,
    }


def _bucket_segment(
    job_id: str,
    decisions: Sequence[search_graph.SearchDecision],
    bindings: Sequence[dict[str, Any]],
    inventory: resources.ResourceInventory,
    source_ports: dict[tuple[int, int], int],
    indexes: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not decisions or len(decisions) > WIDTH:
        raise ModelCInfrastructureError("Model C batch width is invalid")
    physical = model_b_exhaustive.BATCH_SLOTS[0]
    routes = _bucket_route_slots(len(decisions))
    batch_started = time.monotonic()
    try:
        model_b._require_adapter("cleanup-all", timeout=25)
        model_b._require_adapter("preflight")
        wan = model_b._require_adapter("wan").strip()
        if not wan:
            raise ModelCInfrastructureError("Model C WAN interface could not be resolved")

        records = [
            stage60_parallel._warm_record(decision, indexes[decision.node.candidate_id])
            for decision in decisions
        ]
        bucket = _write_bucket_runtime(
            decisions, bindings, inventory, source_ports, indexes
        )

        pool_started = time.monotonic()
        model_b._require_adapter("launch", physical.name, str(physical.port))
        pool = model_b._wait_pool_ready((physical,))
        startup_ms = round((time.monotonic() - pool_started) * 1000)
        snapshot = pool.get(physical.name, {})
        rss = model_b._rss_summary(pool)
        if (
            snapshot.get("ready") is not True
            or snapshot.get("divert_port") != physical.port
            or not bool(rss.get("all_numeric"))
        ):
            raise ModelCInfrastructureError("Model C bucket did not reach unambiguous readiness")

        barrier = threading.Barrier(len(decisions))
        parallel_started = time.monotonic()
        with ThreadPoolExecutor(max_workers=len(decisions), thread_name_prefix="strategy-lab-model-c") as executor:
            futures = [
                executor.submit(
                    _bucket_probe_candidate,
                    job_id,
                    route_slot,
                    record,
                    bindings,
                    wan,
                    source_ports,
                    barrier,
                )
                for route_slot, record in zip(routes, records)
            ]
            probes = [future.result() for future in futures]
        parallel_wall_ms = round((time.monotonic() - parallel_started) * 1000)
        intervals = [(float(item["_started"]), float(item["_ended"])) for item in probes]
        max_overlap = model_b_parallel._max_overlap(intervals)
        if len(decisions) > 1 and max_overlap < len(decisions):
            raise ModelCInfrastructureError("Model C candidate overlap was not observed")
        if max_overlap > WIDTH:
            raise ModelCInfrastructureError("Model C concurrency exceeded production width")
        if not model_b._all_survivors_ready((physical,)):
            raise ModelCInfrastructureError("Model C bucket became unstable during probing")

        candidates: list[dict[str, Any]] = []
        for route_slot, decision, probe in zip(routes, decisions, probes):
            probe.pop("_started", None)
            probe.pop("_ended", None)
            description = decision.node.spec
            candidate_ports = bucket["selector_ports"][description.candidate_id]
            endpoint_results = [
                stage60_parallel._warm_endpoint_result(item)
                for item in probe["endpoint_probes"]
            ]
            candidates.append(
                {
                    "id": description.candidate_id,
                    "family": description.family,
                    "strategy": description.strategy,
                    "candidate_spec": description.to_dict(),
                    "resource_inventory_id": inventory.inventory_id,
                    "runtime_arguments": list(bucket["runtime_arguments"]),
                    "search_epoch_id": bindings[0].get("epoch_id") or "",
                    "endpoint_bindings": list(bindings),
                    "endpoints": endpoint_results,
                    "all_pass": probe["classification"] == "pass",
                    "runtime": {
                        "execution_model": MODEL,
                        "physical_worker_count": 1,
                        "bucket_slot": physical.name,
                        "bucket_pid": snapshot.get("pid"),
                        "divert_port": physical.port,
                        "route_rule": route_slot.rule,
                        "selector": SELECTOR_FUNCTION,
                        "selector_source_ports": list(candidate_ports),
                        "snapshot": snapshot,
                    },
                    "timing": {
                        "total_ms": int(probe["candidate_elapsed_ms"]),
                        "parallel_batch_wall_ms": parallel_wall_ms,
                        "pool_startup_ms": startup_ms,
                    },
                }
            )

        batch = {
            "execution_model": MODEL,
            "width": len(decisions),
            "physical_worker_count": 1,
            "divert_port": physical.port,
            "route_rules": [slot.rule for slot in routes],
            "selector": SELECTOR_FUNCTION,
            "selector_ports": bucket["selector_ports"],
            "max_overlap_observed": max_overlap,
            "pool_startup_ms": startup_ms,
            "parallel_probe_wall_ms": parallel_wall_ms,
            "rss": rss,
            "worker": snapshot,
            "runtime_arguments": bucket["runtime_arguments"],
            "candidate_ids": [decision.node.candidate_id for decision in decisions],
            "total_ms": round((time.monotonic() - batch_started) * 1000),
        }
        return candidates, batch
    except stage60_parallel.Stage60Canceled:
        raise
    except ModelCInfrastructureError:
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
        raise ModelCInfrastructureError(str(exc)) from exc
    finally:
        cleanup_ok = model_b._try_adapter("cleanup-all", timeout=25)
        if not cleanup_ok and not search._cancel_requested(job_id):
            raise ModelCInfrastructureError("Model C bucket cleanup failed")


def _bucket_batch(
    job_id: str,
    decisions: Sequence[search_graph.SearchDecision],
    bindings: Sequence[dict[str, Any]],
    inventory: resources.ResourceInventory,
    source_ports: dict[tuple[int, int], int],
    indexes: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not decisions or len(decisions) > WIDTH:
        raise ModelCInfrastructureError("Model C batch width is invalid")
    segments = _compatible_batch_segments(decisions)
    if len(segments) == 1:
        return _bucket_segment(job_id, decisions, bindings, inventory, source_ports, indexes)

    batch_started = time.monotonic()
    candidates: list[dict[str, Any]] = []
    segment_evidence: list[dict[str, Any]] = []
    for segment in segments:
        segment_candidates, evidence = _bucket_segment(
            job_id, segment, bindings, inventory, source_ports, indexes
        )
        candidates.extend(segment_candidates)
        segment_evidence.append(evidence)

    rss_values = [
        item.get("rss") for item in segment_evidence
        if isinstance(item.get("rss"), dict)
    ]
    peak_rss = max(
        rss_values,
        key=lambda item: int(item.get("aggregate_kb", -1))
        if isinstance(item.get("aggregate_kb"), int) else -1,
    ) if rss_values else {"aggregate_kb": None, "all_numeric": False}
    selector_ports: dict[str, Any] = {}
    for item in segment_evidence:
        raw_ports = item.get("selector_ports")
        if isinstance(raw_ports, dict):
            selector_ports.update(raw_ports)

    batch = dict(segment_evidence[-1])
    batch.update(
        {
            "execution_model": MODEL,
            "width": len(decisions),
            "physical_worker_count": 1,
            "candidate_ids": [decision.node.candidate_id for decision in decisions],
            "profile_segment_count": len(segment_evidence),
            "profile_segments": [dict(item) for item in segment_evidence],
            "selector_ports": selector_ports,
            "max_overlap_observed": max(
                int(item.get("max_overlap_observed", 0)) for item in segment_evidence
            ),
            "pool_startup_ms": sum(
                int(item.get("pool_startup_ms", 0)) for item in segment_evidence
            ),
            "parallel_probe_wall_ms": sum(
                int(item.get("parallel_probe_wall_ms", 0)) for item in segment_evidence
            ),
            "rss": peak_rss,
            "total_ms": round((time.monotonic() - batch_started) * 1000),
        }
    )
    return candidates, batch


def _run_existing_model(model: str, *args: str) -> int:
    previous = os.environ.get("STRATEGY_LAB_STAGE60_MODEL")
    had_previous = "STRATEGY_LAB_STAGE60_MODEL" in os.environ
    os.environ["STRATEGY_LAB_STAGE60_MODEL"] = model
    try:
        return stage60_parallel.expand(*args)
    finally:
        if had_previous:
            assert previous is not None
            os.environ["STRATEGY_LAB_STAGE60_MODEL"] = previous
        else:
            os.environ.pop("STRATEGY_LAB_STAGE60_MODEL", None)


def expand(job_id: str, endpoints_file: str, family_result_file: str, result_file: str) -> int:
    requested = _requested_model()
    if requested == "cold":
        return _run_existing_model("cold", job_id, endpoints_file, family_result_file, result_file)
    if requested == "model-b":
        return _run_existing_model("parallel", job_id, endpoints_file, family_result_file, result_file)

    original_batch = stage60_parallel._warm_batch
    original_model = stage60_parallel.MODEL
    previous_env = os.environ.get("STRATEGY_LAB_STAGE60_MODEL")
    had_previous_env = "STRATEGY_LAB_STAGE60_MODEL" in os.environ
    model_c_enabled = True
    disable_reason = ""

    def production_batch(*batch_args: Any, **batch_kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        nonlocal model_c_enabled, disable_reason
        if model_c_enabled:
            try:
                return _bucket_batch(*batch_args, **batch_kwargs)
            except stage60_parallel.Stage60Canceled:
                raise
            except ModelCInfrastructureError as exc:
                model_c_enabled = False
                disable_reason = str(exc)
                model_b._try_adapter("cleanup-all", timeout=25)

        stage60_parallel.MODEL = MODEL_B
        try:
            candidates, evidence = original_batch(*batch_args, **batch_kwargs)
        except stage60_parallel.WarmInfrastructureError as exc:
            prefix = f"Model C unavailable ({disable_reason}); " if disable_reason else ""
            raise stage60_parallel.WarmInfrastructureError(
                f"{prefix}Model B fallback failed ({exc})"
            ) from exc
        finally:
            stage60_parallel.MODEL = MODEL
        enriched = dict(evidence)
        enriched["preferred_execution_model"] = MODEL
        enriched["fallback_execution_model"] = MODEL_B
        enriched["model_c"] = {
            "attempted": bool(disable_reason),
            "enabled": False,
            "fallback_reason": disable_reason,
        }
        return candidates, enriched

    os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "parallel"
    stage60_parallel.MODEL = MODEL
    stage60_parallel._warm_batch = production_batch
    try:
        return stage60_parallel.expand(job_id, endpoints_file, family_result_file, result_file)
    finally:
        stage60_parallel._warm_batch = original_batch
        stage60_parallel.MODEL = original_model
        if had_previous_env:
            assert previous_env is not None
            os.environ["STRATEGY_LAB_STAGE60_MODEL"] = previous_env
        else:
            os.environ.pop("STRATEGY_LAB_STAGE60_MODEL", None)
        model_b._try_adapter("cleanup-all", timeout=25)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) == 5 and args[0] == "expand":
        try:
            return expand(args[1], args[2], args[3], args[4])
        except stage60_parallel.Stage60Canceled:
            return stage60_parallel.EX_CANCEL
        except (
            stage60_parallel.Stage60ParallelError,
            search_graph.SearchGraphError,
            endpoint_epoch.EndpointEpochError,
        ) as exc:
            print(f"ERROR: {exc}", file=os.sys.stderr)
            return stage60_parallel.EX_SOFTWARE
    raise ValueError("stage60-model-c requires: expand JOB ENDPOINTS FAMILY_RESULT OUTPUT")
