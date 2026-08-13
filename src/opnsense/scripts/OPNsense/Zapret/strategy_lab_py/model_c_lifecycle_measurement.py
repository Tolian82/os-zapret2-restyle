"""Experiment-only Model-C per-batch lifecycle amortization measurement.

This module runs the unchanged production Stage-60 Model C against an isolated copy of a
completed reference job.  It instruments the leased production bucket call from outside,
so every sample includes the same planner, source-port lease, dispatcher, readiness,
probe, and cleanup boundaries used by normal Stage 60 while leaving production code and
the reference job untouched.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import statistics
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from . import (
    adaptive_validation,
    resources,
    search,
    stage60_model_c,
    stage60_source_port_lease,
)

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
SCHEMA = 1
POLICY = "model-c-batch-lifecycle-amortization-v1"
PRODUCTION_MODEL = stage60_model_c.MODEL
DEFAULT_REPEATS = 5
MIN_REPEATS = 3
MAX_REPEATS = 12
DEFAULT_JOBS_DIR = "/var/run/zapret2-restyle/strategy-lab/jobs"


class ModelCLifecycleMeasurementError(RuntimeError):
    """The lifecycle measurement input or live evidence is invalid."""


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelCLifecycleMeasurementError(f"measurement JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise ModelCLifecycleMeasurementError(f"measurement JSON root is invalid: {path}")
    return value


def _positive_repeats(raw: str) -> int:
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError("repeat count must be an integer") from exc
    if value < MIN_REPEATS or value > MAX_REPEATS:
        raise ValueError(f"repeat count must be between {MIN_REPEATS} and {MAX_REPEATS}")
    return value


def _bool_arg(raw: str, name: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true"}:
        return True
    if value in {"0", "false"}:
        return False
    raise ValueError(f"{name} must be true/false or 1/0")


def _stats(values: Sequence[float | int]) -> dict[str, float | int | None]:
    numeric = [float(value) for value in values]
    if not numeric:
        return {
            "count": 0,
            "min": None,
            "mean": None,
            "median": None,
            "stdev": None,
            "p90": None,
            "max": None,
        }
    ordered = sorted(numeric)
    p90_index = max(0, math.ceil(len(ordered) * 0.90) - 1)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 3),
        "mean": round(statistics.fmean(ordered), 3),
        "median": round(statistics.median(ordered), 3),
        "stdev": round(statistics.stdev(ordered), 3) if len(ordered) > 1 else 0.0,
        "p90": round(ordered[p90_index], 3),
        "max": round(ordered[-1], 3),
    }


def _reference_jobs_dir() -> Path:
    return Path(
        os.environ.get(
            "STRATEGY_LAB_REFERENCE_JOBS_DIR",
            os.environ.get("STRATEGY_LAB_JOBS_DIR", DEFAULT_JOBS_DIR),
        )
    )


def _measurement_dir() -> Path:
    raw = os.environ.get("STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR", "").strip()
    if not raw:
        raise ModelCLifecycleMeasurementError("Model-C lifecycle measurement directory is unavailable")
    return Path(raw)


def _result_signature(value: dict[str, Any]) -> dict[str, Any]:
    raw_candidates = value.get("candidates")
    candidates = raw_candidates if isinstance(raw_candidates, list) else []
    outcomes: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ModelCLifecycleMeasurementError("Stage-60 candidate result is invalid")
        outcomes.append({"id": item["id"], "all_pass": item.get("all_pass") is True})
    working = value.get("working")
    failed = value.get("failed")
    if not isinstance(working, list) or not all(isinstance(item, str) for item in working):
        raise ModelCLifecycleMeasurementError("Stage-60 working set is invalid")
    if not isinstance(failed, list) or not all(isinstance(item, str) for item in failed):
        raise ModelCLifecycleMeasurementError("Stage-60 failed set is invalid")
    return {
        "outcomes": outcomes,
        "working": list(working),
        "failed": list(failed),
        "stopped_reason": value.get("stopped_reason"),
        "partial": value.get("partial") is True,
    }


def _batch_list(value: dict[str, Any]) -> list[dict[str, Any]]:
    parallel = value.get("parallel")
    batches = parallel.get("batches") if isinstance(parallel, dict) else None
    if not isinstance(batches, list) or not all(isinstance(item, dict) for item in batches):
        raise ModelCLifecycleMeasurementError("Stage-60 batch evidence is invalid")
    return list(batches)


def _model_c_only(value: dict[str, Any]) -> bool:
    parallel = value.get("parallel")
    if value.get("execution_model") != PRODUCTION_MODEL or not isinstance(parallel, dict):
        return False
    fallbacks = parallel.get("fallbacks")
    if not isinstance(fallbacks, list) or fallbacks:
        return False
    batches = parallel.get("batches")
    if not isinstance(batches, list) or not batches:
        return False
    return all(
        isinstance(item, dict)
        and item.get("outcome") == "warm"
        and item.get("execution_model") == PRODUCTION_MODEL
        for item in batches
    )


def _reference_contract(reference_job: str) -> tuple[Path, dict[str, Any], dict[str, Any], resources.ResourceInventory]:
    if not search.JOB_RE.fullmatch(reference_job):
        raise ModelCLifecycleMeasurementError("invalid Strategy Lab reference job id")
    job = _reference_jobs_dir() / reference_job
    status = _load_json(job / "status.json")
    if status.get("state") != "completed":
        raise ModelCLifecycleMeasurementError("reference Strategy Lab job is not completed")

    family = status.get("family_screening")
    expansion = status.get("parameter_expansion")
    if not isinstance(family, dict) or not isinstance(expansion, dict):
        raise ModelCLifecycleMeasurementError("reference Stage-50/60 evidence is unavailable")
    if not isinstance(family.get("accepted"), list) or not isinstance(family.get("families"), list):
        raise ModelCLifecycleMeasurementError("reference Stage-50 evidence is invalid")
    if family.get("search_epoch_id") != expansion.get("search_epoch_id"):
        raise ModelCLifecycleMeasurementError("reference Stage-50/60 search epoch does not match")
    if not _model_c_only(expansion):
        raise ModelCLifecycleMeasurementError("reference Stage 60 is not a no-fallback production Model-C run")
    if len(_batch_list(expansion)) < 2:
        raise ModelCLifecycleMeasurementError("reference Stage 60 must contain at least two reached Model-C batches")

    for name in ("endpoints.txt", "search-epoch.json", "resource-inventory.json"):
        if not (job / name).is_file():
            raise ModelCLifecycleMeasurementError(f"reference job input is unavailable: {name}")

    reference_inventory = resources.load_inventory(job / "resource-inventory.json")
    current_inventory = resources.snapshot_inventory(
        Path(reference_inventory.lua_root), Path(reference_inventory.fake_root)
    )
    if current_inventory.inventory_id != reference_inventory.inventory_id:
        raise ModelCLifecycleMeasurementError("installed Zapret2 resources differ from the reference inventory")
    return job, family, expansion, reference_inventory


def _prepare_isolated_job(reference: Path, family: dict[str, Any], run_root: Path) -> tuple[Path, Path, Path]:
    jobs = run_root / "jobs"
    job = jobs / reference.name
    job.mkdir(parents=True, exist_ok=True)
    for name in ("endpoints.txt", "search-epoch.json", "resource-inventory.json"):
        shutil.copy2(reference / name, job / name)
    family_path = job / "family-screening-reference.json"
    _atomic_json(family_path, family)
    output = job / "parameter-expansion-measurement.json"
    return jobs, family_path, output


@contextmanager
def _environment(values: dict[str, str]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in values}
    present = {name: name in os.environ for name in values}
    try:
        os.environ.update(values)
        yield
    finally:
        for name, old in previous.items():
            if present[name]:
                assert old is not None
                os.environ[name] = old
            else:
                os.environ.pop(name, None)


@contextmanager
def _instrument_batches(samples: list[dict[str, Any]], stage_started: float) -> Iterator[None]:
    original = stage60_model_c._bucket_batch

    def measured(*args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        started = time.monotonic()
        candidates, evidence = original(*args, **kwargs)
        completed = time.monotonic()
        outer_ms = max(0, round((completed - started) * 1000))
        reported_ms = int(evidence.get("total_ms", 0))
        startup_ms = int(evidence.get("pool_startup_ms", 0))
        probe_ms = int(evidence.get("parallel_probe_wall_ms", 0))
        cleanup_tail_ms = max(0, outer_ms - reported_ms)
        non_probe_ms = max(0, outer_ms - probe_ms)
        setup_bookkeeping_ms = max(0, reported_ms - startup_ms - probe_ms)
        rss = evidence.get("rss") if isinstance(evidence.get("rss"), dict) else {}
        lease = evidence.get("source_port_lease") if isinstance(evidence.get("source_port_lease"), dict) else {}
        candidate_ids = evidence.get("candidate_ids")
        if not isinstance(candidate_ids, list) or not all(isinstance(item, str) for item in candidate_ids):
            raise ModelCLifecycleMeasurementError("Model-C batch candidate attribution is invalid")
        samples.append(
            {
                "batch": len(samples) + 1,
                "candidate_ids": list(candidate_ids),
                "width": int(evidence.get("width", len(candidate_ids))),
                "execution_model": evidence.get("execution_model"),
                "outer_batch_ms": outer_ms,
                "reported_batch_total_ms": reported_ms,
                "pool_startup_ms": startup_ms,
                "parallel_probe_wall_ms": probe_ms,
                "cleanup_tail_ms": cleanup_tail_ms,
                "setup_bookkeeping_ms": setup_bookkeeping_ms,
                "non_probe_upper_bound_ms": non_probe_ms,
                "result_ready_from_stage_start_ms": max(0, round((completed - stage_started) * 1000)),
                "rss_aggregate_kb": rss.get("aggregate_kb"),
                "rss_all_numeric": rss.get("all_numeric") is True,
                "source_port_replacement_count": lease.get("replacement_count", 0),
            }
        )
        return candidates, evidence

    stage60_model_c._bucket_batch = measured
    try:
        yield
    finally:
        stage60_model_c._bucket_batch = original


def _run_once(reference: Path, family: dict[str, Any], reference_signature: dict[str, Any], repeat: int) -> dict[str, Any]:
    run_root = _measurement_dir() / f"repeat-{repeat:02d}"
    if run_root.exists():
        shutil.rmtree(run_root)
    jobs, family_path, output = _prepare_isolated_job(reference, family, run_root)
    endpoints = jobs / reference.name / "endpoints.txt"
    runtime_root = run_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)

    samples: list[dict[str, Any]] = []
    stage_started = time.monotonic()
    with _environment(
        {
            "STRATEGY_LAB_JOBS_DIR": str(jobs),
            "STRATEGY_LAB_MODEL_B_SESSION_DIR": str(runtime_root),
        }
    ):
        with adaptive_validation.probe_tier("discovery"):
            with stage60_source_port_lease.install():
                with _instrument_batches(samples, stage_started):
                    status = stage60_model_c.expand(
                        reference.name,
                        str(endpoints),
                        str(family_path),
                        str(output),
                    )
    stage60_wall_ms = max(0, round((time.monotonic() - stage_started) * 1000))
    if status != EX_OK or not output.is_file():
        raise ModelCLifecycleMeasurementError(f"isolated Stage-60 repeat {repeat} failed with status {status}")
    result = _load_json(output)
    signature = _result_signature(result)
    result_batches = _batch_list(result)
    if len(samples) != len(result_batches):
        raise ModelCLifecycleMeasurementError("instrumented and persisted Model-C batch counts differ")

    sequence = [list(item["candidate_ids"]) for item in samples]
    persisted_sequence = [list(item.get("candidate_ids", [])) for item in result_batches]
    rss_complete = all(item.get("rss_all_numeric") is True and isinstance(item.get("rss_aggregate_kb"), int) for item in samples)
    non_probe_total = sum(int(item["non_probe_upper_bound_ms"]) for item in samples)
    amortizable_upper_bound = sum(int(item["non_probe_upper_bound_ms"]) for item in samples[1:])
    upper_share = 0.0 if stage60_wall_ms <= 0 else round(amortizable_upper_bound * 100.0 / stage60_wall_ms, 3)
    lifecycle_share = 0.0 if stage60_wall_ms <= 0 else round(non_probe_total * 100.0 / stage60_wall_ms, 3)
    return {
        "repeat": repeat,
        "status": status,
        "stage60_wall_ms": stage60_wall_ms,
        "first_result_latency_ms": samples[0]["result_ready_from_stage_start_ms"] if samples else None,
        "batch_count": len(samples),
        "batch_sequence": sequence,
        "batches": samples,
        "result_signature": signature,
        "result_equivalent": signature == reference_signature,
        "batch_sequence_persisted": sequence == persisted_sequence,
        "model_c_only": _model_c_only(result) and all(item.get("execution_model") == PRODUCTION_MODEL for item in samples),
        "rss_complete": rss_complete,
        "non_probe_total_ms": non_probe_total,
        "lifecycle_share_of_stage60_pct": lifecycle_share,
        "amortizable_upper_bound_ms": amortizable_upper_bound,
        "amortizable_upper_bound_share_pct": upper_share,
    }


def _summaries(repeats: list[dict[str, Any]]) -> dict[str, Any]:
    batches = [batch for repeat in repeats for batch in repeat.get("batches", []) if isinstance(batch, dict)]
    return {
        "stage60_wall_ms": _stats([item["stage60_wall_ms"] for item in repeats]),
        "first_result_latency_ms": _stats([item["first_result_latency_ms"] for item in repeats if item.get("first_result_latency_ms") is not None]),
        "batch_count": _stats([item["batch_count"] for item in repeats]),
        "pool_startup_ms": _stats([item["pool_startup_ms"] for item in batches]),
        "cleanup_tail_ms": _stats([item["cleanup_tail_ms"] for item in batches]),
        "setup_bookkeeping_ms": _stats([item["setup_bookkeeping_ms"] for item in batches]),
        "non_probe_upper_bound_ms": _stats([item["non_probe_upper_bound_ms"] for item in batches]),
        "rss_aggregate_kb": _stats([item["rss_aggregate_kb"] for item in batches if isinstance(item.get("rss_aggregate_kb"), int)]),
        "lifecycle_share_of_stage60_pct": _stats([item["lifecycle_share_of_stage60_pct"] for item in repeats]),
        "amortizable_upper_bound_ms": _stats([item["amortizable_upper_bound_ms"] for item in repeats]),
        "amortizable_upper_bound_share_pct": _stats([item["amortizable_upper_bound_share_pct"] for item in repeats]),
    }


def run(reference_job: str, output: Path, repeats: int) -> int:
    reference, family, expansion, inventory = _reference_contract(reference_job)
    reference_signature = _result_signature(expansion)
    reference_batches = _batch_list(expansion)
    repeat_values = [_run_once(reference, family, reference_signature, index) for index in range(1, repeats + 1)]
    first_sequence = repeat_values[0]["batch_sequence"] if repeat_values else []
    checks = {
        "reference_model_c_only": _model_c_only(expansion),
        "multi_batch_reference": len(reference_batches) >= 2,
        "reference_inventory_match": True,
        "repeat_count_complete": len(repeat_values) == repeats,
        "model_c_only": all(item.get("model_c_only") is True for item in repeat_values),
        "result_equivalent": all(item.get("result_equivalent") is True for item in repeat_values),
        "batch_sequence_equivalent": all(item.get("batch_sequence") == first_sequence and item.get("batch_sequence_persisted") is True for item in repeat_values),
        "rss_complete": all(item.get("rss_complete") is True for item in repeat_values),
        "lifecycle_restored": False,
        "cleanup_ok": False,
    }
    report = {
        "schema": SCHEMA,
        "policy": POLICY,
        "experiment_only": True,
        "production_model": PRODUCTION_MODEL,
        "production_model_changed": False,
        "production_search_semantics_changed": False,
        "production_dispatch_width_changed": False,
        "production_change_recommended": False,
        "reference_job": reference_job,
        "reference_search_epoch_id": expansion.get("search_epoch_id"),
        "reference_resource_inventory_id": inventory.inventory_id,
        "reference_batch_count": len(reference_batches),
        "reference_result_signature": reference_signature,
        "repeat_count": repeats,
        "repeats": repeat_values,
        "summaries": _summaries(repeat_values),
        "checks": checks,
        "lifecycle": {},
        "conclusion": "measurement_collected",
        "next_step": "analyze_owner_live_amortizable_upper_bound_before_any_separate_cross_batch_reuse_design",
    }
    _atomic_json(output, report)
    return EX_OK


def finalize(output: Path, initial_path: Path, final_path: Path, cleanup_ok: bool) -> int:
    report = _load_json(output)
    initial = _load_json(initial_path)
    final = _load_json(final_path)
    lifecycle_restored = initial == final
    report["lifecycle"] = {"initial": initial, "final": final}
    checks = report.setdefault("checks", {})
    checks["lifecycle_restored"] = lifecycle_restored
    checks["cleanup_ok"] = cleanup_ok
    required = (
        "reference_model_c_only",
        "multi_batch_reference",
        "reference_inventory_match",
        "repeat_count_complete",
        "model_c_only",
        "result_equivalent",
        "batch_sequence_equivalent",
        "rss_complete",
        "lifecycle_restored",
        "cleanup_ok",
    )
    accepted = all(bool(checks.get(name)) for name in required)
    report["conclusion"] = "measurement_accepted" if accepted else "measurement_rejected"
    _atomic_json(output, report)
    return EX_OK if accepted else EX_SOFTWARE


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args[:1] == ["run"] and len(args) in {3, 4}:
            repeats = DEFAULT_REPEATS if len(args) == 3 else _positive_repeats(args[3])
            return run(args[1], Path(args[2]), repeats)
        if args[:1] == ["finalize"] and len(args) == 5:
            return finalize(Path(args[1]), Path(args[2]), Path(args[3]), _bool_arg(args[4], "cleanup ok"))
        raise ValueError("model-c-lifecycle-measure requires: run REFERENCE_JOB OUTPUT [REPEATS] | finalize OUTPUT INITIAL FINAL CLEANUP_OK")
    except ModelCLifecycleMeasurementError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EX_SOFTWARE
