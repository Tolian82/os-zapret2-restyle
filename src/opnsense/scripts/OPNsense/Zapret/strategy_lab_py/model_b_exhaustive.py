"""Experiment-only batched exhaustive Model-B benchmark.

The benchmark consumes one completed Standard no-candidate Strategy Lab job whose Stage 60
ended with graph exhaustion. It replays the exact persisted Stage-60 candidate corpus in
its original order using the already owner-proven three-worker Model-B coexistence boundary.
Candidates and all pinned reference endpoints are executed sequentially in warm batches of
at most three workers. The module never changes production Strategy Lab selection or runtime
architecture.
"""

from __future__ import annotations

import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import candidate_spec, model_b, request, resources

EX_OK = 0
SCHEMA = 1
MODEL = "B-warm-worker-exhaustive-batched"
BATCH_SLOTS = tuple(
    model_b.Slot(slot.name, slot.port, slot.rule, f"batch-slot-{index}")
    for index, slot in enumerate(model_b.SLOTS)
)


class ModelBExhaustiveError(model_b.ModelBExperimentError):
    """The exhaustive benchmark input or runtime evidence is invalid."""


def _median(values: Sequence[int | float]) -> float | None:
    if not values:
        return None
    return round(float(statistics.median(values)), 3)


def _job_total_ms(job: Path) -> int | None:
    path = job / "timing-telemetry.json"
    if not path.is_file():
        return None
    value = model_b._load_json(path)
    events = value.get("events")
    if not isinstance(events, list):
        return None
    totals = [
        item.get("duration_ms")
        for item in events
        if isinstance(item, dict) and item.get("phase") == "job_total"
    ]
    numeric = [item for item in totals if isinstance(item, int) and not isinstance(item, bool) and item >= 0]
    return numeric[-1] if numeric else None


def _reference_bindings(epoch: dict[str, Any]) -> list[dict[str, Any]]:
    raw = epoch.get("bindings")
    if not isinstance(raw, list) or not raw:
        raise ModelBExhaustiveError("exhaustive Model B requires at least one pinned endpoint")
    bindings: list[dict[str, Any]] = []
    endpoints: set[str] = set()
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ModelBExhaustiveError("reference endpoint binding is invalid")
        endpoint = item.get("endpoint")
        selected_ip = item.get("selected_ip")
        if not isinstance(endpoint, str) or not endpoint or not isinstance(selected_ip, str) or not selected_ip:
            raise ModelBExhaustiveError("reference endpoint binding is invalid")
        if endpoint in endpoints:
            raise ModelBExhaustiveError("reference endpoint binding is duplicated")
        endpoints.add(endpoint)
        bindings.append(
            {
                "index": item.get("index", index),
                "endpoint": endpoint,
                "selected_ip": selected_ip,
                "epoch_id": epoch.get("epoch_id"),
            }
        )
    return bindings


def _reference_contract(reference_job_id: str) -> tuple[
    dict[str, Any],
    resources.ResourceInventory,
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    job = model_b.job_dir(reference_job_id)
    status = model_b._load_json(job / "status.json")
    if status.get("state") != "completed" or status.get("outcome") != "NO_CANDIDATE":
        raise ModelBExhaustiveError("exhaustive Model B requires a completed NO_CANDIDATE reference job")
    if status.get("mode") != "standard" or status.get("target_type") != "domain":
        raise ModelBExhaustiveError("exhaustive Model B requires a Standard domain reference job")
    restoration = status.get("restoration") if isinstance(status.get("restoration"), dict) else {}
    if not (
        restoration.get("verified") is True
        and restoration.get("temporary_runtime_clean") is True
        and restoration.get("strategy_unchanged") is True
    ):
        raise ModelBExhaustiveError("reference job restoration evidence is not verified")

    inventory = resources.load_inventory(job / "resource-inventory.json")
    epoch = model_b._load_json(job / "search-epoch.json")
    bindings = _reference_bindings(epoch)

    expansion = model_b._load_json(job / "parameter-expansion.json")
    candidates = expansion.get("candidates")
    schedule = expansion.get("schedule")
    working = expansion.get("working")
    completed = expansion.get("completed")
    if expansion.get("stopped_reason") != "graph_exhausted":
        raise ModelBExhaustiveError("reference Stage 60 did not end with graph exhaustion")
    if not isinstance(working, list) or working:
        raise ModelBExhaustiveError("reference Stage 60 unexpectedly contains a working candidate")
    if isinstance(completed, bool) or not isinstance(completed, int) or completed <= 0:
        raise ModelBExhaustiveError("reference Stage-60 completed count is invalid")
    if not isinstance(candidates, list) or len(candidates) != completed:
        raise ModelBExhaustiveError("reference Stage-60 candidate corpus is incomplete")
    if not isinstance(schedule, list) or len(schedule) != completed:
        raise ModelBExhaustiveError("reference Stage-60 schedule is incomplete")

    records: list[dict[str, Any]] = []
    cold_durations: list[int] = []
    for index, (candidate, schedule_item) in enumerate(zip(candidates, schedule), 1):
        if not isinstance(candidate, dict) or not isinstance(schedule_item, dict):
            raise ModelBExhaustiveError("reference Stage-60 candidate or schedule entry is invalid")
        spec_raw = candidate.get("candidate_spec")
        if not isinstance(spec_raw, dict):
            raise ModelBExhaustiveError("reference Stage-60 candidate spec is missing")
        try:
            spec = candidate_spec.CandidateSpec.from_dict(spec_raw)
        except candidate_spec.CandidateSpecError as exc:
            raise ModelBExhaustiveError("reference Stage-60 candidate spec is invalid") from exc
        if candidate.get("id") != spec.candidate_id:
            raise ModelBExhaustiveError("reference Stage-60 candidate id does not match CandidateSpec")
        if candidate.get("all_pass") is True:
            raise ModelBExhaustiveError("NO_CANDIDATE reference contains a passing Stage-60 candidate")
        if candidate.get("search_epoch_id") != epoch.get("epoch_id"):
            raise ModelBExhaustiveError("reference Stage-60 candidate belongs to another search epoch")
        inventory_id = candidate.get("resource_inventory_id")
        if isinstance(inventory_id, str) and inventory_id and inventory_id != inventory.inventory_id:
            raise ModelBExhaustiveError("reference Stage-60 candidate belongs to another resource inventory")
        if schedule_item.get("sequence") != index:
            raise ModelBExhaustiveError("reference Stage-60 schedule sequence is not contiguous")
        duration = schedule_item.get("duration_ms")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise ModelBExhaustiveError("reference Stage-60 schedule duration is invalid")
        cold_durations.append(duration)
        records.append(
            {
                "path": f"parameter-expansion/{spec.candidate_id}.json",
                "value": candidate,
                "spec": spec.to_dict(),
                "spec_id": spec.spec_id,
                "classification": model_b._classification(candidate),
                "cold_duration_ms": duration,
                "corpus_index": index,
            }
        )

    cold_candidate_runtime_ms = sum(cold_durations)
    reference = {
        "target": status.get("target"),
        "mode": status.get("mode"),
        "search_epoch_id": epoch.get("epoch_id"),
        "resource_inventory_id": inventory.inventory_id,
        "initial_service_state": restoration.get("initial_state"),
        "candidate_count": completed,
        "endpoint_count": len(bindings),
        "bindings": bindings,
        "cold_candidate_runtime_ms": cold_candidate_runtime_ms,
        "cold_job_total_ms": _job_total_ms(job),
        "stopped_reason": expansion.get("stopped_reason"),
    }
    return status, inventory, bindings, records, reference


def _write_worker_runtime(
    slot: model_b.Slot,
    record: dict[str, Any],
    inventory: resources.ResourceInventory,
    bindings: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    root = model_b.session_dir() / "workers" / slot.name
    root.mkdir(parents=True, exist_ok=True)
    spec = candidate_spec.CandidateSpec.from_dict(record["spec"])
    hostlist: Path | None = None
    endpoints = [str(binding["endpoint"]) for binding in bindings]
    if spec.target_binding:
        hostlist = root / "hostlist.txt"
        hostlist.write_text("".join(f"{endpoint}\n" for endpoint in endpoints), encoding="utf-8")
        os.chmod(hostlist, 0o644)
    arguments = spec.render_runtime_arguments(inventory, divert_port=slot.port, hostlist_path=hostlist)
    args_path = root / "dvtws.args"
    args_path.write_text("".join(f"{item}\n" for item in arguments), encoding="utf-8")
    os.chmod(args_path, 0o644)
    return {
        "slot": slot.name,
        "role": slot.role,
        "port": slot.port,
        "rule": slot.rule,
        "candidate_id": spec.candidate_id,
        "spec_id": spec.spec_id,
        "family": spec.family,
        "expected_classification": record["classification"],
        "resource_classes": list(record["spec"].get("resource_classes", [])),
        "out_range": (record["spec"].get("ranges") or {}).get("out"),
        "reference_path": record["path"],
        "target_endpoints": endpoints,
        "runtime_arguments": list(arguments),
    }


def _probe_candidate(
    slot: model_b.Slot,
    slots: Sequence[model_b.Slot],
    record: dict[str, Any],
    bindings: Sequence[dict[str, Any]],
    wan: str,
) -> dict[str, Any]:
    endpoint_probes: list[dict[str, Any]] = []
    for binding in bindings:
        endpoint_probes.append(
            model_b._probe(
                slot,
                slots,
                str(binding["endpoint"]),
                str(binding["selected_ip"]),
                wan,
            )
        )
    classification = "pass" if all(item.get("classification") == "pass" for item in endpoint_probes) else "fail"
    dispatch_ms = sum(int(item.get("dispatch_ms", 0)) for item in endpoint_probes)
    probe_ms = sum(int(item.get("probe_ms", 0)) for item in endpoint_probes)
    probe: dict[str, Any] = {
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
        "dispatch_ms": dispatch_ms,
        "probe_ms": probe_ms,
        "intercepted": all(bool(item.get("intercepted")) for item in endpoint_probes),
        "inactive_rules_absent": all(bool(item.get("inactive_rules_absent")) for item in endpoint_probes),
    }
    probe["all_workers_still_ready"] = model_b._all_survivors_ready(slots)
    return probe


def _projection(cold_job_total_ms: int | None, cold_candidate_runtime_ms: int, warm_search_ms: int) -> dict[str, Any]:
    candidate_speedup = None
    if cold_candidate_runtime_ms > 0:
        candidate_speedup = round((1.0 - (warm_search_ms / cold_candidate_runtime_ms)) * 100.0, 3)
    projected_job_ms = None
    projected_speedup = None
    if cold_job_total_ms is not None and cold_job_total_ms >= cold_candidate_runtime_ms:
        projected_job_ms = cold_job_total_ms - cold_candidate_runtime_ms + warm_search_ms
        if cold_job_total_ms > 0:
            projected_speedup = round((1.0 - (projected_job_ms / cold_job_total_ms)) * 100.0, 3)
    return {
        "candidate_runtime_speedup_percent": candidate_speedup,
        "projected_full_job_ms": projected_job_ms,
        "projected_full_job_speedup_percent": projected_speedup,
        "projection_method": "cold_job_total - cold_stage60_candidate_runtime + warm_exhaustive_search",
        "projection_is_measured_full_job": False,
    }


def run(reference_job_id: str, output: str) -> int:
    output_path = Path(output)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "model": MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "reference_job": reference_job_id,
        "experiment_only": True,
        "parallel_probes": False,
        "production_approved": False,
        "batch_size": len(BATCH_SLOTS),
        "checks": {},
        "batches": [],
        "probes": [],
        "restoration": {"verified": False, "pending": True},
        "conclusion": "inconclusive",
    }
    try:
        _status, reference_inventory, bindings, records, reference = _reference_contract(reference_job_id)
        current_inventory = model_b._current_inventory(reference_inventory)
        report["reference"] = reference
        report["checks"]["reference_inventory_match"] = True
        report["checks"]["reference_graph_exhausted"] = True
        report["checks"]["reference_endpoint_bindings"] = True
        model_b.session_dir().mkdir(parents=True, exist_ok=True)
        wan = model_b._require_adapter("wan").strip()
        if not wan:
            raise ModelBExhaustiveError("Model B WAN interface could not be resolved")
        report["wan"] = wan
        model_b._require_adapter("cleanup-all", timeout=25)
        model_b._require_adapter("preflight")

        search_started = time.monotonic()
        all_ready = True
        all_unique = True
        all_rss = True
        all_equivalent = True
        all_attributed = True
        all_stable = True
        all_cleanup = True
        observed_ids: list[str] = []
        startup_values: list[int] = []
        cleanup_values: list[int] = []
        dispatch_values: list[int] = []
        probe_values: list[int] = []
        endpoint_dispatch_values: list[int] = []
        endpoint_probe_values: list[int] = []
        aggregate_rss_values: list[int] = []

        for batch_number, offset in enumerate(range(0, len(records), len(BATCH_SLOTS)), 1):
            batch_started = time.monotonic()
            batch_records = records[offset: offset + len(BATCH_SLOTS)]
            slots = BATCH_SLOTS[: len(batch_records)]
            model_b._require_adapter("preflight")
            workers: dict[str, dict[str, Any]] = {}
            by_slot: dict[str, dict[str, Any]] = {}
            for slot, record in zip(slots, batch_records):
                worker = _write_worker_runtime(slot, record, current_inventory, bindings)
                worker["corpus_index"] = record["corpus_index"]
                worker["cold_duration_ms"] = record["cold_duration_ms"]
                worker["cold_classification"] = record["classification"]
                worker["expected_search_classification"] = "non-pass"
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
                batch_ready
                and None not in pids
                and len(set(pids)) == len(slots)
                and len(set(ports)) == len(slots)
                and set(ports) == {slot.port for slot in slots}
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
                "pool": {
                    "startup_ms": pool_startup_ms,
                    "snapshots": pool,
                    "rss": rss,
                    "unique_worker_identity": batch_unique,
                },
                "probes": [],
            }
            if not batch_ready:
                batch["failed_readiness"] = {
                    "failed_slots": [
                        slot.name for slot in slots if pool.get(slot.name, {}).get("ready") is not True
                    ],
                    "downstream_actions_skipped": True,
                }
                report["batches"].append(batch)
                report["failed_readiness"] = {"batch": batch_number, **batch["failed_readiness"]}
                raise ModelBExhaustiveError("Model B exhaustive batch did not reach readiness")
            if not batch_unique:
                batch["failed_identity"] = {"downstream_actions_skipped": True}
                report["batches"].append(batch)
                report["failed_identity"] = {"batch": batch_number, "downstream_actions_skipped": True}
                raise ModelBExhaustiveError("Model B exhaustive batch worker identity is ambiguous")

            for slot in slots:
                record = by_slot[slot.name]
                probe = _probe_candidate(slot, slots, record, bindings, wan)
                batch["probes"].append(probe)
                report["probes"].append(probe)
                observed_ids.append(str(probe["candidate_id"]))
                dispatch_values.append(int(probe["dispatch_ms"]))
                probe_values.append(int(probe["probe_ms"]))
                for endpoint_probe in probe["endpoint_probes"]:
                    endpoint_dispatch_values.append(int(endpoint_probe["dispatch_ms"]))
                    endpoint_probe_values.append(int(endpoint_probe["probe_ms"]))
                all_equivalent = all_equivalent and bool(probe["equivalent_to_cold_search"])
                all_attributed = all_attributed and bool(probe["intercepted"]) and bool(probe["inactive_rules_absent"])
                all_stable = all_stable and bool(probe["all_workers_still_ready"])

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
                raise ModelBExhaustiveError("Model B exhaustive batch cleanup failed")

        warm_search_ms = round((time.monotonic() - search_started) * 1000)
        expected_ids = [str(record["spec"].get("candidate_id")) for record in records]
        corpus_complete = observed_ids == expected_ids
        report["checks"].update(
            corpus_complete=corpus_complete,
            all_batches_ready=all_ready,
            unique_worker_identity=all_unique,
            rss_observed=all_rss,
            result_equivalence=all_equivalent,
            route_attribution=all_attributed,
            coexistence_stable=all_stable,
            cleanup_between_batches=all_cleanup,
            sequential_probe_contract=True,
            all_reference_endpoints_replayed=all(
                probe.get("endpoint_count") == len(bindings) for probe in report["probes"]
            ),
        )
        report["timing"] = {
            "warm_exhaustive_search_ms": warm_search_ms,
            "batch_startup_total_ms": sum(startup_values),
            "batch_startup_median_ms": _median(startup_values),
            "batch_cleanup_total_ms": sum(cleanup_values),
            "batch_cleanup_median_ms": _median(cleanup_values),
            "candidate_dispatch_median_ms": _median(dispatch_values),
            "candidate_probe_median_ms": _median(probe_values),
            "dispatch_median_ms": _median(endpoint_dispatch_values),
            "probe_median_ms": _median(endpoint_probe_values),
            "endpoint_probe_count": len(endpoint_probe_values),
            "peak_batch_rss_kb": max(aggregate_rss_values) if aggregate_rss_values else None,
            "cold_candidate_runtime_ms": reference["cold_candidate_runtime_ms"],
            "cold_job_total_ms": reference["cold_job_total_ms"],
        }
        report["comparison"] = _projection(
            reference["cold_job_total_ms"],
            int(reference["cold_candidate_runtime_ms"]),
            warm_search_ms,
        )
        required = (
            "reference_inventory_match",
            "reference_graph_exhausted",
            "reference_endpoint_bindings",
            "corpus_complete",
            "all_batches_ready",
            "unique_worker_identity",
            "rss_observed",
            "result_equivalence",
            "route_attribution",
            "coexistence_stable",
            "cleanup_between_batches",
            "sequential_probe_contract",
            "all_reference_endpoints_replayed",
        )
        report["required_checks"] = list(required)
        report["preliminary_accept"] = all(report["checks"].get(name) is True for name in required)
        report["conclusion"] = "pending_restoration" if report["preliminary_accept"] else "reject"
    except (
        ModelBExhaustiveError,
        model_b.ModelBExperimentError,
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
        "model-b-exhaustive requires: run REFERENCE_JOB OUTPUT | "
        "finalize OUTPUT INITIAL_EVIDENCE FINAL_EVIDENCE CLEANUP_OK"
    )
