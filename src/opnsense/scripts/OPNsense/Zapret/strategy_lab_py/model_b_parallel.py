"""Experiment-only controlled parallel Model-B exhaustive benchmark.

This benchmark is deliberately separate from production Strategy Lab and from the accepted
sequential Model-B exhaustive harness.  It reuses the exact persisted no-candidate Stage-60
corpus, keeps at most three owner-proven warm workers per batch, and executes up to three
candidate probes concurrently.  Pinned endpoints inside one candidate remain sequential.

Concurrent traffic ownership uses one unique controlled TCP source port per
candidate/endpoint probe.  The temporary IPFW rule matches that exact source port and exact
pinned destination before diverting the flow to the candidate's dedicated worker.
"""

from __future__ import annotations

import os
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import adaptive_validation, candidate_spec, model_b, model_b_exhaustive, request, resources

EX_OK = 0
SCHEMA = 1
MODEL = "B-warm-worker-parallel-batched"
BATCH_SLOTS = model_b_exhaustive.BATCH_SLOTS
SOURCE_PORT_BASE_DEFAULT = 42000
REMOTE_IP_RE = re.compile(r"(?:^|\s)remote_ip=([^\s]+)")
LOCAL_PORT_RE = re.compile(r"(?:^|\s)local_port=(\d+)(?:\s|$)")


class ModelBParallelError(model_b.ModelBExperimentError):
    """The controlled parallel benchmark input or runtime evidence is invalid."""


def _median(values: Sequence[int | float]) -> float | None:
    if not values:
        return None
    return round(float(statistics.median(values)), 3)


def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ModelBParallelError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ModelBParallelError(f"{name} must be a positive integer")
    return value


def _source_port_plan(records: Sequence[dict[str, Any]], bindings: Sequence[dict[str, Any]]) -> dict[tuple[int, int], int]:
    base = _positive_int_env("STRATEGY_LAB_MODEL_B_SOURCE_PORT_BASE", SOURCE_PORT_BASE_DEFAULT)
    if base < 1024 or base > 65535:
        raise ModelBParallelError("Model B parallel source-port base is outside the usable TCP range")
    plan: dict[tuple[int, int], int] = {}
    for record in records:
        corpus_index = int(record["corpus_index"])
        for endpoint_index, _binding in enumerate(bindings, 1):
            port = base + ((corpus_index - 1) * len(bindings)) + endpoint_index - 1
            if port > 65535:
                raise ModelBParallelError("Model B parallel source-port plan exceeds 65535")
            plan[(corpus_index, endpoint_index)] = port
    values = list(plan.values())
    if len(values) != len(set(values)):
        raise ModelBParallelError("Model B parallel source-port plan is not unique")
    return plan


def _replace_writeout_for_local_port(command: list[str]) -> None:
    try:
        index = command.index("--write-out")
    except ValueError as exc:
        raise request.RequestError("Model B parallel curl command has no --write-out option") from exc
    if index + 1 >= len(command):
        raise request.RequestError("Model B parallel curl command has no --write-out value")
    value = command[index + 1]
    if "local_port=%{local_port}" not in value:
        command[index + 1] = value.rstrip("\\n") + " local_port=%{local_port}\\n"


def _parallel_curl_request(endpoint: str, selected_ip: str, local_port: int) -> request.CommandResult:
    command = request._curl_command(
        endpoint,
        scheme="https",
        family="ipv4",
        tls_version="1.3",
        bound_ip=selected_ip,
    )
    byte_limit = _positive_int_env(
        adaptive_validation.DISCOVERY_RANGE_BYTES_ENV,
        adaptive_validation.DISCOVERY_RANGE_BYTES_DEFAULT,
    )
    max_time = _positive_int_env(
        adaptive_validation.DISCOVERY_MAX_TIME_ENV,
        adaptive_validation.DISCOVERY_MAX_TIME_DEFAULT,
    )
    adaptive_validation._replace_option(command, "--range", f"0-{byte_limit - 1}")
    adaptive_validation._replace_option(command, "--max-time", str(max_time))
    command[-1:-1] = ["--local-port", str(local_port)]
    _replace_writeout_for_local_port(command)
    return request.run_command(command, timeout=max_time + 1)


def _last_match(pattern: re.Pattern[str], text: str) -> str:
    match = None
    for match in pattern.finditer(text):
        pass
    return "" if match is None else match.group(1)


def _probe_endpoint(
    slot: model_b.Slot,
    binding: dict[str, Any],
    wan: str,
    local_port: int,
) -> dict[str, Any]:
    endpoint = str(binding["endpoint"])
    selected_ip = str(binding["selected_ip"])
    if not model_b._try_adapter("source-port-free", str(local_port)):
        raise ModelBParallelError(f"controlled source port is already in use: {local_port}")

    dispatch_started = time.monotonic()
    model_b._require_adapter(
        "route-add-source",
        str(slot.rule),
        str(slot.port),
        selected_ip,
        wan,
        "tcp",
        "443",
        str(local_port),
    )
    dispatch_ms = round((time.monotonic() - dispatch_started) * 1000)
    result: dict[str, Any] | None = None
    route_cleanup_ok = False
    try:
        before_packets, before_bytes = model_b._counter(slot.rule)
        probe_started = time.monotonic()
        execution = _parallel_curl_request(endpoint, selected_ip, local_port)
        probe_ms = round((time.monotonic() - probe_started) * 1000)
        after_packets, after_bytes = model_b._counter(slot.rule)
        remote_ip = _last_match(REMOTE_IP_RE, execution.stdout)
        observed_local_port_raw = _last_match(LOCAL_PORT_RE, execution.stdout)
        observed_local_port = int(observed_local_port_raw) if observed_local_port_raw else None
        intercepted = after_packets > before_packets
        endpoint_match = remote_ip == selected_ip
        local_port_match = observed_local_port == local_port
        classification = (
            "pass"
            if request.curl_exit(execution) == 0 and endpoint_match and intercepted and local_port_match
            else "fail"
        )
        result = {
            "slot": slot.name,
            "rule": slot.rule,
            "port": slot.port,
            "endpoint": endpoint,
            "selected_ip": selected_ip,
            "requested_local_port": local_port,
            "observed_local_port": observed_local_port,
            "local_port_match": local_port_match,
            "source_port_selector": True,
            "dispatch_ms": dispatch_ms,
            "probe_ms": probe_ms,
            "counter_before": {"packets": before_packets, "bytes": before_bytes},
            "counter_after": {"packets": after_packets, "bytes": after_bytes},
            "intercepted": intercepted,
            "remote_ip": remote_ip,
            "endpoint_match": endpoint_match,
            "classification": classification,
            "execution": execution.evidence(),
        }
    finally:
        route_cleanup_ok = model_b._try_adapter("route-del", str(slot.rule))

    if result is None:
        raise ModelBParallelError("Model B parallel endpoint probe produced no result")
    result["route_cleanup_ok"] = route_cleanup_ok
    result["attribution_ok"] = bool(
        result["source_port_selector"]
        and result["local_port_match"]
        and result["endpoint_match"]
        and result["intercepted"]
        and route_cleanup_ok
    )
    return result


def _probe_candidate(
    slot: model_b.Slot,
    slots: Sequence[model_b.Slot],
    record: dict[str, Any],
    bindings: Sequence[dict[str, Any]],
    wan: str,
    source_ports: dict[tuple[int, int], int],
    start_barrier: threading.Barrier,
) -> dict[str, Any]:
    try:
        start_barrier.wait(timeout=3)
    except threading.BrokenBarrierError as exc:
        raise ModelBParallelError("parallel candidate start barrier failed") from exc

    started = time.monotonic()
    endpoint_probes: list[dict[str, Any]] = []
    for endpoint_index, binding in enumerate(bindings, 1):
        probe = _probe_endpoint(
            slot,
            binding,
            wan,
            source_ports[(int(record["corpus_index"]), endpoint_index)],
        )
        endpoint_probes.append(probe)
    ended = time.monotonic()

    classification = "pass" if all(item.get("classification") == "pass" for item in endpoint_probes) else "fail"
    route_absent = model_b._try_adapter("rule-present", str(slot.rule)) is False
    attribution_ok = all(bool(item.get("attribution_ok")) for item in endpoint_probes) and route_absent
    return {
        "slot": slot.name,
        "rule": slot.rule,
        "port": slot.port,
        "corpus_index": record["corpus_index"],
        "candidate_id": record["spec"].get("candidate_id"),
        "spec_id": record["spec_id"],
        "cold_classification": record["classification"],
        "expected_search_classification": "non-pass",
        "classification": classification,
        "equivalent_to_cold_search": classification != "pass",
        "endpoint_count": len(endpoint_probes),
        "endpoint_probes": endpoint_probes,
        "candidate_elapsed_ms": round((ended - started) * 1000),
        "dispatch_ms": sum(int(item.get("dispatch_ms", 0)) for item in endpoint_probes),
        "probe_ms": sum(int(item.get("probe_ms", 0)) for item in endpoint_probes),
        "intercepted": all(bool(item.get("intercepted")) for item in endpoint_probes),
        "route_cleanup_ok": route_absent and all(bool(item.get("route_cleanup_ok")) for item in endpoint_probes),
        "attribution_ok": attribution_ok,
        "endpoints_sequential": True,
        "all_workers_still_ready": model_b._all_survivors_ready(slots),
        "_started": started,
        "_ended": ended,
    }


def _max_overlap(intervals: Sequence[tuple[float, float]]) -> int:
    events: list[tuple[float, int]] = []
    for started, ended in intervals:
        events.append((started, 1))
        events.append((ended, -1))
    # Start events sort before end events at the same instant so the conservative measured
    # overlap does not lose a worker at a timestamp tie.
    events.sort(key=lambda item: (item[0], -item[1]))
    current = 0
    maximum = 0
    for _when, delta in events:
        current += delta
        maximum = max(maximum, current)
    return maximum


def run(reference_job_id: str, output: str) -> int:
    output_path = Path(output)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "model": MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "reference_job": reference_job_id,
        "experiment_only": True,
        "parallel_probes": True,
        "candidate_parallel_width": len(BATCH_SLOTS),
        "endpoint_probes_parallel": False,
        "production_approved": False,
        "cpu_policy": "measurement_only_no_cpu_gating",
        "logical_cpu_count": os.cpu_count(),
        "checks": {},
        "batches": [],
        "probes": [],
        "restoration": {"verified": False, "pending": True},
        "conclusion": "inconclusive",
    }
    try:
        _status, reference_inventory, bindings, records, reference = model_b_exhaustive._reference_contract(reference_job_id)
        current_inventory = model_b._current_inventory(reference_inventory)
        source_ports = _source_port_plan(records, bindings)
        report["reference"] = reference
        report["source_port_plan"] = {
            "base": min(source_ports.values()),
            "last": max(source_ports.values()),
            "count": len(source_ports),
            "unique": len(source_ports) == len(set(source_ports.values())),
        }
        report["checks"].update(
            reference_inventory_match=True,
            reference_graph_exhausted=True,
            reference_endpoint_bindings=True,
            source_port_plan_unique=bool(report["source_port_plan"]["unique"]),
        )

        model_b.session_dir().mkdir(parents=True, exist_ok=True)
        wan = model_b._require_adapter("wan").strip()
        if not wan:
            raise ModelBParallelError("Model B WAN interface could not be resolved")
        report["wan"] = wan
        model_b._require_adapter("cleanup-all", timeout=25)
        model_b._require_adapter("preflight")

        search_started = time.monotonic()
        observed_ids: list[str] = []
        startup_values: list[int] = []
        cleanup_values: list[int] = []
        parallel_wall_values: list[int] = []
        candidate_elapsed_values: list[int] = []
        endpoint_probe_values: list[int] = []
        aggregate_rss_values: list[int] = []
        all_ready = all_unique = all_rss = True
        all_equivalent = all_attributed = all_stable = all_cleanup = True
        all_parallel = all_limited = all_endpoints_sequential = True

        for batch_number, offset in enumerate(range(0, len(records), len(BATCH_SLOTS)), 1):
            batch_started = time.monotonic()
            batch_records = records[offset: offset + len(BATCH_SLOTS)]
            slots = BATCH_SLOTS[: len(batch_records)]
            model_b._require_adapter("preflight")
            workers: dict[str, dict[str, Any]] = {}
            by_slot: dict[str, dict[str, Any]] = {}
            for slot, record in zip(slots, batch_records):
                worker = model_b_exhaustive._write_worker_runtime(slot, record, current_inventory, bindings)
                worker["corpus_index"] = record["corpus_index"]
                workers[slot.name] = worker
                by_slot[slot.name] = record

            pool_started = time.monotonic()
            for slot in slots:
                model_b._require_adapter("launch", slot.name, str(slot.port))
            pool = model_b._wait_pool_ready(slots)
            pool_startup_ms = round((time.monotonic() - pool_started) * 1000)
            startup_values.append(pool_startup_ms)
            rss = model_b._rss_summary(pool)
            if isinstance(rss.get("aggregate_kb"), int):
                aggregate_rss_values.append(int(rss["aggregate_kb"]))
            batch_ready = all(pool.get(slot.name, {}).get("ready") is True for slot in slots)
            pids = [pool.get(slot.name, {}).get("pid") for slot in slots]
            ports = [pool.get(slot.name, {}).get("divert_port") for slot in slots]
            batch_unique = (
                batch_ready and None not in pids and len(set(pids)) == len(slots)
                and len(set(ports)) == len(slots) and set(ports) == {slot.port for slot in slots}
            )
            batch_rss = bool(rss.get("all_numeric"))
            all_ready = all_ready and batch_ready
            all_unique = all_unique and batch_unique
            all_rss = all_rss and batch_rss
            batch: dict[str, Any] = {
                "batch": batch_number,
                "corpus_start": offset + 1,
                "corpus_end": offset + len(batch_records),
                "workers": workers,
                "pool": {"startup_ms": pool_startup_ms, "snapshots": pool, "rss": rss, "unique_worker_identity": batch_unique},
                "probes": [],
            }
            if not batch_ready or not batch_unique:
                report["batches"].append(batch)
                raise ModelBParallelError("Model B parallel batch did not reach unambiguous readiness")

            barrier = threading.Barrier(len(slots))
            parallel_started = time.monotonic()
            with ThreadPoolExecutor(max_workers=len(slots), thread_name_prefix="strategy-lab-model-b") as executor:
                futures = {
                    slot.name: executor.submit(
                        _probe_candidate,
                        slot,
                        slots,
                        by_slot[slot.name],
                        bindings,
                        wan,
                        source_ports,
                        barrier,
                    )
                    for slot in slots
                }
                probes = [futures[slot.name].result() for slot in slots]
            parallel_wall_ms = round((time.monotonic() - parallel_started) * 1000)
            parallel_wall_values.append(parallel_wall_ms)
            intervals = [(float(item["_started"]), float(item["_ended"])) for item in probes]
            max_overlap = _max_overlap(intervals)
            expected_overlap = len(slots) if len(slots) > 1 else 1
            batch_parallel = max_overlap >= expected_overlap
            batch_limited = max_overlap <= len(BATCH_SLOTS)
            all_parallel = all_parallel and batch_parallel
            all_limited = all_limited and batch_limited

            for probe in probes:
                probe.pop("_started", None)
                probe.pop("_ended", None)
                batch["probes"].append(probe)
                report["probes"].append(probe)
                observed_ids.append(str(probe["candidate_id"]))
                candidate_elapsed_values.append(int(probe["candidate_elapsed_ms"]))
                for endpoint_probe in probe["endpoint_probes"]:
                    endpoint_probe_values.append(int(endpoint_probe["probe_ms"]))
                all_equivalent = all_equivalent and bool(probe["equivalent_to_cold_search"])
                all_attributed = all_attributed and bool(probe["attribution_ok"])
                all_stable = all_stable and bool(probe["all_workers_still_ready"])
                all_endpoints_sequential = all_endpoints_sequential and bool(probe["endpoints_sequential"])

            batch["parallel"] = {
                "requested_width": len(slots),
                "max_overlap_observed": max_overlap,
                "wall_ms": parallel_wall_ms,
                "overlap_observed": batch_parallel,
                "limit_respected": batch_limited,
            }
            cleanup_started = time.monotonic()
            batch_cleanup = model_b._try_adapter("cleanup-all", timeout=25)
            cleanup_ms = round((time.monotonic() - cleanup_started) * 1000)
            cleanup_values.append(cleanup_ms)
            batch["cleanup_ok"] = batch_cleanup
            batch["cleanup_ms"] = cleanup_ms
            batch["total_ms"] = round((time.monotonic() - batch_started) * 1000)
            report["batches"].append(batch)
            all_cleanup = all_cleanup and batch_cleanup
            if not batch_cleanup:
                raise ModelBParallelError("Model B parallel batch cleanup failed")

        parallel_search_ms = round((time.monotonic() - search_started) * 1000)
        expected_ids = [str(record["spec"].get("candidate_id")) for record in records]
        report["checks"].update(
            corpus_complete=observed_ids == expected_ids,
            all_batches_ready=all_ready,
            unique_worker_identity=all_unique,
            rss_observed=all_rss,
            result_equivalence=all_equivalent,
            route_attribution=all_attributed,
            coexistence_stable=all_stable,
            cleanup_between_batches=all_cleanup,
            candidate_parallelism_observed=all_parallel,
            concurrency_limit_respected=all_limited,
            endpoints_sequential_per_candidate=all_endpoints_sequential,
            all_reference_endpoints_replayed=all(
                probe.get("endpoint_count") == len(bindings) for probe in report["probes"]
            ),
        )
        report["timing"] = {
            "parallel_exhaustive_search_ms": parallel_search_ms,
            "batch_startup_total_ms": sum(startup_values),
            "batch_startup_median_ms": _median(startup_values),
            "batch_cleanup_total_ms": sum(cleanup_values),
            "batch_cleanup_median_ms": _median(cleanup_values),
            "parallel_batch_probe_wall_total_ms": sum(parallel_wall_values),
            "parallel_batch_probe_wall_median_ms": _median(parallel_wall_values),
            "candidate_elapsed_median_ms": _median(candidate_elapsed_values),
            "endpoint_probe_median_ms": _median(endpoint_probe_values),
            "endpoint_probe_count": len(endpoint_probe_values),
            "peak_batch_rss_kb": max(aggregate_rss_values) if aggregate_rss_values else None,
            "cold_candidate_runtime_ms": reference["cold_candidate_runtime_ms"],
            "cold_job_total_ms": reference["cold_job_total_ms"],
        }
        report["comparison"] = model_b_exhaustive._projection(
            reference["cold_job_total_ms"], int(reference["cold_candidate_runtime_ms"]), parallel_search_ms
        )
        required = (
            "reference_inventory_match", "reference_graph_exhausted", "reference_endpoint_bindings",
            "source_port_plan_unique", "corpus_complete", "all_batches_ready", "unique_worker_identity",
            "rss_observed", "result_equivalence", "route_attribution", "coexistence_stable",
            "cleanup_between_batches", "candidate_parallelism_observed", "concurrency_limit_respected",
            "endpoints_sequential_per_candidate", "all_reference_endpoints_replayed",
        )
        report["required_checks"] = list(required)
        report["preliminary_accept"] = all(report["checks"].get(name) is True for name in required)
        report["conclusion"] = "pending_restoration" if report["preliminary_accept"] else "reject"
    except (
        ModelBParallelError,
        model_b.ModelBExperimentError,
        model_b_exhaustive.ModelBExhaustiveError,
        candidate_spec.CandidateSpecError,
        resources.ResourceInventoryError,
        request.RequestError,
        OSError,
        ValueError,
    ) as exc:
        report["error"] = str(exc)
        report["preliminary_accept"] = False
        report["conclusion"] = "reject"
    finally:
        report["experiment_cleanup_requested"] = model_b._try_adapter("cleanup-all", timeout=25)
        model_b._write_report(output_path, report)
    return EX_OK


def finalize(output: str, initial_evidence: str, final_evidence: str, cleanup_ok: str) -> int:
    return model_b.finalize(output, initial_evidence, final_evidence, cleanup_ok)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) == 3 and args[0] == "run":
        return run(args[1], args[2])
    if len(args) == 5 and args[0] == "finalize":
        return finalize(args[1], args[2], args[3], args[4])
    raise ValueError(
        "model-b-parallel requires: run REFERENCE_JOB OUTPUT | "
        "finalize OUTPUT INITIAL_EVIDENCE FINAL_EVIDENCE CLEANUP_OK"
    )
