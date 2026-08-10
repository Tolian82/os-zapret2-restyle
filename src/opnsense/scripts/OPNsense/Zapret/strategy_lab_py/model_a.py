"""Model-A cold-reference measurement summarizer for completed Strategy Lab jobs.

This module is intentionally read-only with respect to Strategy Lab lifecycle state. It
reuses the cold candidate evidence already persisted by normal jobs and produces one
portable experiment record with per-phase distributions, candidate/resource coverage,
endpoint/interception identity, RSS when available, and explicit measurement gaps.
"""

from __future__ import annotations

import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

EX_OK = 0
EX_USAGE = 64
JOB_RE = re.compile(r"^job\.[A-Za-z0-9]{6,64}$")
SCHEMA = 1
MODEL = "A-cold-reference"


class ModelAMeasurementError(RuntimeError):
    """Completed-job evidence is insufficient or structurally invalid."""


def jobs_dir() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-restyle/strategy-lab/jobs"))


def job_dir(job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise ModelAMeasurementError(f"invalid Strategy Lab job id: {job_id}")
    return jobs_dir() / job_id


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelAMeasurementError(f"Strategy Lab JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise ModelAMeasurementError(f"Strategy Lab JSON root is invalid: {path}")
    return value


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _command_text(command: Sequence[str]) -> str | None:
    executable = shutil.which(command[0])
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    return text or None


def _system_identity() -> dict[str, Any]:
    identity: dict[str, Any] = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }
    if platform.system() == "FreeBSD":
        identity["opnsense_version"] = _command_text(["opnsense-version"])
        identity["package_version"] = _command_text(["pkg", "query", "%v", "os-zapret2-restyle"])
    return identity


def _stage_paths(job: Path) -> Iterable[tuple[str, Path]]:
    for path in sorted((job / "family-screening").glob("*.json")):
        yield "50", path
    for path in sorted((job / "parameter-expansion").glob("*.json")):
        yield "60", path
    for path in sorted((job / "stability").glob("*-attempts/*.json")):
        yield "70", path
    for path in sorted((job / "profile-replay").glob("*.deep.json")):
        yield "85", path


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0:
        return None
    return value


def _sum_numeric(mapping: dict[str, Any], names: Sequence[str]) -> int | float | None:
    values = [_number(mapping.get(name)) for name in names]
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _classification(candidate: dict[str, Any]) -> str:
    if candidate.get("timeout") is True:
        return "timeout"
    if candidate.get("error") is True:
        return "error"
    return "pass" if candidate.get("all_pass") is True else "fail"


def _endpoint_identity(candidate: dict[str, Any]) -> dict[str, Any]:
    endpoints = candidate.get("endpoints")
    endpoints = endpoints if isinstance(endpoints, list) else []
    records: list[dict[str, Any]] = []
    intercepted: list[bool] = []
    exact: list[bool] = []
    for item in endpoints:
        if not isinstance(item, dict):
            continue
        firewall = item.get("firewall") if isinstance(item.get("firewall"), dict) else {}
        selected = item.get("selected_ip")
        remote = item.get("remote_ip")
        match = item.get("endpoint_match")
        records.append(
            {
                "endpoint": item.get("endpoint"),
                "selected_ip": selected,
                "remote_ip": remote,
                "endpoint_match": match,
                "rule": firewall.get("rule"),
                "intercepted": firewall.get("intercepted"),
            }
        )
        if isinstance(firewall.get("intercepted"), bool):
            intercepted.append(bool(firewall["intercepted"]))
        if isinstance(match, bool):
            exact.append(match)
    return {
        "records": records,
        "all_intercepted": bool(intercepted) and all(intercepted),
        "all_endpoint_matches": bool(exact) and all(exact),
    }


def _sample(job_id: str, job: Path, stage: str, path: Path) -> dict[str, Any] | None:
    value = _load_json(path)
    spec = value.get("candidate_spec")
    timing = value.get("timing")
    if not isinstance(spec, dict) or not isinstance(timing, dict):
        return None
    candidate_id = spec.get("candidate_id")
    spec_id = spec.get("spec_id")
    if not isinstance(candidate_id, str) or not candidate_id or not isinstance(spec_id, str) or not spec_id:
        return None
    runtime = value.get("runtime") if isinstance(value.get("runtime"), dict) else {}
    ranges = spec.get("ranges") if isinstance(spec.get("ranges"), dict) else {}
    classes = spec.get("resource_classes") if isinstance(spec.get("resource_classes"), list) else []
    prepare_ms = _sum_numeric(
        timing,
        ("endpoint_binding_ms", "candidate_prepare_ms", "resource_render_ms", "firewall_install_ms"),
    )
    phase = {
        "pre_cleanup_ms": _number(timing.get("pre_cleanup_ms")),
        "prepare_ms": prepare_ms,
        "endpoint_binding_ms": _number(timing.get("endpoint_binding_ms")),
        "candidate_prepare_ms": _number(timing.get("candidate_prepare_ms")),
        "resource_render_ms": _number(timing.get("resource_render_ms")),
        "firewall_install_ms": _number(timing.get("firewall_install_ms")),
        "resource_init_ms": _number(timing.get("resource_init_ms")),
        "launch_ms": _number(timing.get("launch_ms")),
        "ready_ms": _number(timing.get("readiness_ms")),
        "probe_ms": _number(timing.get("probe_ms")),
        "stop_cleanup_ms": _number(timing.get("cleanup_ms")),
        "total_ms": _number(timing.get("total_ms")),
    }
    return {
        "job_id": job_id,
        "stage": stage,
        "path": str(path.relative_to(job)),
        "candidate_id": candidate_id,
        "spec_id": spec_id,
        "family": spec.get("family"),
        "protocol": spec.get("protocol"),
        "transport": spec.get("transport"),
        "port": spec.get("port"),
        "resource_classes": [item for item in classes if isinstance(item, str)],
        "out_range": ranges.get("out"),
        "classification": _classification(value),
        "rss_kb": _number(runtime.get("rss_kb")),
        "phase_ms": phase,
        "endpoint_identity": _endpoint_identity(value),
        "search_epoch_id": value.get("search_epoch_id"),
        "resource_inventory_id": value.get("resource_inventory_id"),
    }


def _nearest_rank(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def _stats(values: Iterable[int | float | None]) -> dict[str, Any] | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return {
        "count": len(numeric),
        "median": round(float(statistics.median(numeric)), 3),
        "p90": round(_nearest_rank(numeric, 0.90), 3),
        "max": round(max(numeric), 3),
    }


def _phase_statistics(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    names = (
        "pre_cleanup_ms",
        "prepare_ms",
        "endpoint_binding_ms",
        "candidate_prepare_ms",
        "resource_render_ms",
        "firewall_install_ms",
        "resource_init_ms",
        "launch_ms",
        "ready_ms",
        "probe_ms",
        "stop_cleanup_ms",
        "total_ms",
    )
    return {
        name: _stats(sample["phase_ms"].get(name) for sample in samples)
        for name in names
    }


def _candidate_statistics(samples: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        grouped.setdefault(str(sample["spec_id"]), []).append(sample)
    result: list[dict[str, Any]] = []
    for spec_id in sorted(grouped):
        group = grouped[spec_id]
        first = group[0]
        result.append(
            {
                "spec_id": spec_id,
                "candidate_id": first["candidate_id"],
                "family": first.get("family"),
                "protocol": first.get("protocol"),
                "sample_count": len(group),
                "classifications": {
                    name: len([item for item in group if item["classification"] == name])
                    for name in ("pass", "fail", "timeout", "error")
                },
                "phase_ms": _phase_statistics(group),
                "rss_kb": _stats(item.get("rss_kb") for item in group),
            }
        )
    return result


def _job_record(job_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    job = job_dir(job_id)
    status_path = job / "status.json"
    inventory_path = job / "resource-inventory.json"
    epoch_path = job / "search-epoch.json"
    if not status_path.is_file() or not inventory_path.is_file() or not epoch_path.is_file():
        raise ModelAMeasurementError(f"completed Strategy Lab evidence is incomplete: {job_id}")
    status = _load_json(status_path)
    inventory = _load_json(inventory_path)
    epoch = _load_json(epoch_path)
    samples: list[dict[str, Any]] = []
    for stage, path in _stage_paths(job):
        sample = _sample(job_id, job, stage, path)
        if sample is not None:
            samples.append(sample)
    if not samples:
        raise ModelAMeasurementError(f"no cold candidate timing samples found: {job_id}")
    restoration = status.get("restoration") if isinstance(status.get("restoration"), dict) else {}
    job_record = {
        "job_id": job_id,
        "target": status.get("target"),
        "target_type": status.get("target_type"),
        "mode": status.get("mode"),
        "state": status.get("state"),
        "outcome": status.get("outcome"),
        "search_epoch_id": epoch.get("epoch_id"),
        "resource_inventory_id": inventory.get("inventory_id"),
        "external_blob_count": len(inventory.get("external_blobs", [])) if isinstance(inventory.get("external_blobs"), list) else 0,
        "restoration": {
            "verified": restoration.get("verified"),
            "initial_state": restoration.get("initial_state"),
            "final_state": restoration.get("final_state"),
            "strategy_unchanged": restoration.get("strategy_unchanged"),
            "temporary_runtime_clean": restoration.get("temporary_runtime_clean"),
        },
        "sample_count": len(samples),
    }
    return job_record, samples


def _coverage(jobs: Sequence[dict[str, Any]], samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    spec_ids = sorted({str(item["spec_id"]) for item in samples})
    repetitions = {
        spec_id: len([item for item in samples if item["spec_id"] == spec_id])
        for spec_id in spec_ids
    }
    classes = sorted({item for sample in samples for item in sample.get("resource_classes", [])})
    ranges = sorted({"<none>" if sample.get("out_range") is None else str(sample.get("out_range")) for sample in samples})
    tls443 = {
        str(sample["spec_id"])
        for sample in samples
        if sample.get("protocol") in {"tls13", "tls12"}
        and sample.get("transport") == "tcp"
        and sample.get("port") == 443
    }
    external_installed = any(int(job.get("external_blob_count", 0)) > 0 for job in jobs)
    required_classes = {"blob-free", "builtin"}
    if external_installed:
        required_classes.add("external")
    checks = {
        "known_pass_observed": any(item["classification"] == "pass" for item in samples),
        "known_fail_observed": any(item["classification"] == "fail" for item in samples),
        "repeated_candidate_observed": any(count >= 3 for count in repetitions.values()),
        "required_resource_classes_observed": required_classes.issubset(set(classes)),
        "out_range_d8_observed": "-d8" in ranges,
        "overlapping_tls443_candidates_observed": len(tls443) >= 2,
        "rss_observed": any(item.get("rss_kb") is not None for item in samples),
        "restoration_verified_for_all_jobs": bool(jobs) and all(
            job.get("restoration", {}).get("verified") is True
            and job.get("restoration", {}).get("temporary_runtime_clean") is True
            for job in jobs
        ),
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {
        "candidate_repetitions": repetitions,
        "resource_classes_observed": classes,
        "required_resource_classes": sorted(required_classes),
        "out_ranges_observed": ranges,
        "unique_tls443_specs": len(tls443),
        "checks": checks,
        "complete": not missing,
        "missing": missing,
    }


def summarize(output: str, job_ids: Sequence[str]) -> int:
    if not job_ids:
        return EX_USAGE
    jobs: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for job_id in job_ids:
        job_record, job_samples = _job_record(job_id)
        jobs.append(job_record)
        samples.extend(job_samples)
    coverage = _coverage(jobs, samples)
    report = {
        "schema": SCHEMA,
        "model": MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "system": _system_identity(),
        "jobs": jobs,
        "sample_count": len(samples),
        "samples": samples,
        "phase_statistics_ms": _phase_statistics(samples),
        "candidate_statistics": _candidate_statistics(samples),
        "coverage": coverage,
        "limitations": [
            "resource_init_ms remains included in launch/readiness unless the runtime exposes it separately",
            "stop_ms is currently included in stop_cleanup_ms; the cold runtime still records the combined bounded teardown cost",
            "this summarizer does not execute candidates, change lifecycle ownership, or approve Models B/C",
        ],
        "conclusion": "reference_collected" if coverage["complete"] else "inconclusive",
    }
    _atomic_json(Path(output), report)
    return EX_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 3 or args[0] != "summarize":
        raise ValueError("model-a requires: summarize OUTPUT JOB_ID [JOB_ID ...]")
    return summarize(args[1], args[2:])
