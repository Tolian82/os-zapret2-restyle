"""Experiment-only discovery probe agreement and cost measurement."""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from . import adaptive_validation, candidate, request, resources, search_graph

EX_OK = 0
EX_USAGE = 64
SCHEMA = 1
POLICY = "discovery-probe-agreement-v1"
PRODUCTION_MODEL = "C-warm-bucket-source-port-dispatch"
DEFAULT_CANDIDATES = 10
DEEP_TARGET_BYTES = 16384
WRITEOUT_RE = re.compile(r"(?:^|\s)code=(\d+)(?:\s+)bytes=(\d+(?:\.\d+)?)(?:\s|$)")
VARIANTS = ("head", "get-1", "get-4k", "deep-16k")


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _positive_int(raw: str, name: str) -> int:
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _replace_option(command: list[str], name: str, value: str) -> None:
    try:
        index = command.index(name)
    except ValueError as exc:
        raise RuntimeError(f"curl command is missing {name}") from exc
    if index + 1 >= len(command):
        raise RuntimeError(f"curl command has incomplete {name}")
    command[index + 1] = value


def _measurement_curl(method: str, range_value: str, max_time: int) -> Callable[..., request.CommandResult]:
    def run(
        host: str,
        *,
        scheme: str,
        family: str = "ipv4",
        tls_version: str | None = None,
        bound_ip: str | None = None,
    ) -> request.CommandResult:
        command = request._curl_command(
            host,
            scheme=scheme,
            family=family,
            tls_version=tls_version,
            bound_ip=bound_ip,
        )
        _replace_option(command, "--request", method)
        _replace_option(command, "--range", range_value)
        _replace_option(command, "--max-time", str(max_time))
        return request.run_command(command, timeout=max_time + 1)

    return run


@contextmanager
def _request_variant(name: str) -> Iterator[None]:
    previous = request.curl_request
    previous_tier = os.environ.get(adaptive_validation.PROBE_TIER_ENV)
    try:
        if name == "head":
            request.curl_request = _measurement_curl("HEAD", "0-0", 3)
        elif name == "get-1":
            request.curl_request = _measurement_curl("GET", "0-0", 3)
        elif name == "get-4k":
            os.environ[adaptive_validation.PROBE_TIER_ENV] = "discovery"
            request.curl_request = adaptive_validation._tiered_curl_request
        elif name == "deep-16k":
            os.environ[adaptive_validation.PROBE_TIER_ENV] = "deep"
            request.curl_request = adaptive_validation._tiered_curl_request
        else:
            raise ValueError(f"unknown discovery measurement variant: {name}")
        yield
    finally:
        request.curl_request = previous
        if previous_tier is None:
            os.environ.pop(adaptive_validation.PROBE_TIER_ENV, None)
        else:
            os.environ[adaptive_validation.PROBE_TIER_ENV] = previous_tier


def _writeout(endpoint: dict[str, Any]) -> tuple[int | None, int | None]:
    execution = endpoint.get("execution")
    stdout = execution.get("stdout") if isinstance(execution, dict) else None
    if not isinstance(stdout, str):
        return None, None
    match = None
    for match in WRITEOUT_RE.finditer(stdout):
        pass
    if match is None:
        return None, None
    return int(match.group(1), 10), int(float(match.group(2)))


def classify_cheap(result: dict[str, Any]) -> dict[str, Any]:
    endpoints = result.get("endpoints")
    endpoints = endpoints if isinstance(endpoints, list) else []
    if result.get("error") is True or result.get("timeout") is True or not endpoints:
        return {"classification": "inconclusive", "reason": "candidate_error_or_no_evidence"}
    statuses: list[int] = []
    byte_counts: list[int] = []
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            return {"classification": "inconclusive", "reason": "invalid_endpoint_evidence"}
        firewall = endpoint.get("firewall")
        if endpoint.get("status") != "PASS" or endpoint.get("endpoint_match") is not True:
            return {"classification": "fail", "reason": "endpoint_or_request_failed"}
        if not isinstance(firewall, dict) or firewall.get("intercepted") is not True:
            return {"classification": "inconclusive", "reason": "interception_unproven"}
        status, count = _writeout(endpoint)
        if status is None or count is None:
            return {"classification": "inconclusive", "reason": "http_evidence_unavailable"}
        statuses.append(status)
        byte_counts.append(count)
        if status < 100 or status >= 400:
            return {"classification": "fail", "reason": "http_status_failed", "http_statuses": statuses}
    return {
        "classification": "pass",
        "reason": "bounded_probe_passed",
        "http_statuses": statuses,
        "bytes_received": min(byte_counts) if byte_counts else 0,
    }


def _deep_classification(result: dict[str, Any]) -> dict[str, Any]:
    replay = dict(result)
    replay["profile_exact"] = True
    return adaptive_validation.classify_deep_replay(replay, "tls13", DEEP_TARGET_BYTES)


def _stats(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "mean": None, "median": None, "stdev": None, "p90": None, "max": None}
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.90) - 1)
    return {
        "count": len(values),
        "min": ordered[0],
        "mean": round(statistics.fmean(values), 3),
        "median": round(statistics.median(values), 3),
        "stdev": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
        "p90": ordered[index],
        "max": ordered[-1],
    }


def summarize(samples: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    summaries: dict[str, Any] = {}
    for variant in VARIANTS:
        current = [item for item in samples if item.get("variant") == variant]
        classes = {"pass": 0, "fail": 0, "inconclusive": 0}
        for item in current:
            name = str(item.get("classification", "inconclusive"))
            classes[name if name in classes else "inconclusive"] += 1
        summaries[variant] = {
            "samples": len(current),
            "classification_counts": classes,
            "probe_ms": _stats([int(item["probe_ms"]) for item in current if isinstance(item.get("probe_ms"), int)]),
            "total_ms": _stats([int(item["total_ms"]) for item in current if isinstance(item.get("total_ms"), int)]),
            "bytes_received": _stats([int(item["bytes_received"]) for item in current if isinstance(item.get("bytes_received"), int)]),
        }

    comparisons: dict[str, Any] = {}
    by_candidate = {(str(item["candidate_id"]), str(item["variant"])): item for item in samples}
    candidates = sorted({str(item["candidate_id"]) for item in samples})
    for variant in VARIANTS[:-1]:
        agreement = false_pass = false_fail = comparable = inconclusive = 0
        for candidate_id in candidates:
            cheap = by_candidate.get((candidate_id, variant))
            deep = by_candidate.get((candidate_id, "deep-16k"))
            if cheap is None or deep is None:
                continue
            cheap_class = str(cheap.get("classification", "inconclusive"))
            deep_class = str(deep.get("classification", "inconclusive"))
            if cheap_class not in {"pass", "fail"} or deep_class not in {"pass", "fail"}:
                inconclusive += 1
                continue
            comparable += 1
            if cheap_class == deep_class:
                agreement += 1
            elif cheap_class == "pass" and deep_class == "fail":
                false_pass += 1
            elif cheap_class == "fail" and deep_class == "pass":
                false_fail += 1
        comparisons[variant] = {
            "comparable": comparable,
            "agreement": agreement,
            "agreement_ratio": None if comparable == 0 else round(agreement / comparable, 6),
            "false_pass": false_pass,
            "false_fail": false_fail,
            "inconclusive_pairs": inconclusive,
        }
    return summaries, comparisons


def _eligible_nodes(job: Path, limit: int) -> tuple[list[search_graph.SearchNode], resources.ResourceInventory, str]:
    inventory = resources.ensure_job_inventory(job)
    graph = search_graph.native_tls13_graph()
    recon = list(graph.plan("reconnaissance", (), inventory).scheduled)
    expansion = list(graph.plan("expansion", (), inventory).scheduled)
    golden = [node for node in expansion if node.golden]
    remaining = [node for node in expansion if not node.golden]
    selected: list[search_graph.SearchNode] = []
    selected_ids: set[str] = set()
    for node in recon + golden + remaining:
        if node.candidate_id not in selected_ids:
            selected.append(node)
            selected_ids.add(node.candidate_id)
        if len(selected) >= limit:
            break
    return selected, inventory, graph.graph_id


def _run_variant(job_id: str, endpoints: Path, node: search_graph.SearchNode, variant: str, work: Path) -> dict[str, Any]:
    spec = node.spec
    stem = f"{node.candidate_id}.{variant}"
    strategy_path = work / f"{stem}.args"
    spec_path = work / f"{stem}.spec.json"
    result_path = work / f"{stem}.json"
    strategy_path.write_text(spec.strategy, encoding="utf-8")
    os.chmod(strategy_path, 0o600)
    _atomic_json(spec_path, spec.to_dict())
    try:
        result_path.unlink()
    except FileNotFoundError:
        pass
    started = time.monotonic()
    with _request_variant(variant):
        status = candidate.run_candidate(
            job_id,
            str(endpoints),
            str(result_path),
            spec.candidate_id,
            spec.family,
            str(strategy_path),
            "1" if spec.target_binding else "0",
            str(spec_path),
        )
    elapsed = max(0, round((time.monotonic() - started) * 1000))
    if status != EX_OK or not result_path.is_file():
        raise RuntimeError(f"candidate variant failed internally: {spec.candidate_id}/{variant}")
    value = json.loads(result_path.read_text(encoding="utf-8"))
    classification = _deep_classification(value) if variant == "deep-16k" else classify_cheap(value)
    timing = value.get("timing") if isinstance(value.get("timing"), dict) else {}
    endpoints_value = value.get("endpoints") if isinstance(value.get("endpoints"), list) else []
    endpoint_match = bool(endpoints_value) and all(isinstance(item, dict) and item.get("endpoint_match") is True for item in endpoints_value)
    intercepted = bool(endpoints_value) and all(isinstance(item, dict) and isinstance(item.get("firewall"), dict) and item["firewall"].get("intercepted") is True for item in endpoints_value)
    return {
        "candidate_id": spec.candidate_id,
        "family": spec.family,
        "candidate_spec_id": spec.spec_id,
        "variant": variant,
        "classification": classification.get("classification", "inconclusive"),
        "classification_reason": classification.get("reason", ""),
        "bytes_received": classification.get("bytes_received"),
        "http_statuses": classification.get("http_statuses", []),
        "probe_ms": timing.get("probe_ms"),
        "total_ms": timing.get("total_ms", elapsed),
        "endpoint_match": endpoint_match,
        "intercepted": intercepted,
        "search_epoch_id": value.get("search_epoch_id", ""),
        "error": value.get("error") is True,
        "timeout": value.get("timeout") is True,
    }


def run(reference_job: str, output: Path, candidate_count: int) -> int:
    if not candidate.JOB_RE.fullmatch(reference_job):
        return EX_USAGE
    job = candidate.job_dir(reference_job)
    endpoints = job / "endpoints.txt"
    status_path = job / "status.json"
    if not endpoints.is_file() or not status_path.is_file():
        return EX_USAGE
    work = Path(os.environ.get("STRATEGY_LAB_DISCOVERY_MEASUREMENT_DIR", str(job / "discovery-probe-measurement")))
    work.mkdir(parents=True, exist_ok=True)
    nodes, inventory, graph_id = _eligible_nodes(job, candidate_count)
    if not nodes:
        raise RuntimeError("no eligible native TLS 1.3 candidates are available")
    samples: list[dict[str, Any]] = []
    orders = [
        VARIANTS,
        VARIANTS[1:] + VARIANTS[:1],
        VARIANTS[2:] + VARIANTS[:2],
        VARIANTS[3:] + VARIANTS[:3],
    ]
    for index, node in enumerate(nodes):
        for variant in orders[index % len(orders)]:
            samples.append(_run_variant(reference_job, endpoints, node, variant, work))
    summaries, comparisons = summarize(samples)
    epoch_ids = sorted({str(item.get("search_epoch_id", "")) for item in samples if item.get("search_epoch_id")})
    report = {
        "schema": SCHEMA,
        "policy": POLICY,
        "experiment_only": True,
        "production_model": PRODUCTION_MODEL,
        "production_model_changed": False,
        "production_discovery_policy_changed": False,
        "production_change_recommended": False,
        "reference_job": reference_job,
        "graph_id": graph_id,
        "resource_inventory_id": inventory.inventory_id,
        "candidate_count": len(nodes),
        "candidate_ids": [node.candidate_id for node in nodes],
        "variants": list(VARIANTS),
        "deep_target_bytes": DEEP_TARGET_BYTES,
        "sample_count": len(samples),
        "samples": samples,
        "summaries": summaries,
        "comparisons": comparisons,
        "checks": {
            "expected_sample_count": len(samples) == len(nodes) * len(VARIANTS),
            "single_search_epoch": len(epoch_ids) == 1,
            "endpoint_attribution_complete": all(item.get("endpoint_match") is True and item.get("intercepted") is True for item in samples if item.get("classification") == "pass"),
            "lifecycle_restored": False,
            "cleanup_ok": False,
        },
        "lifecycle": {},
        "conclusion": "measurement_collected",
        "next_step": "owner_live_measurement_then_select_only_a_probe_with_zero_false_passes_and_material_cost_benefit",
    }
    _atomic_json(output, report)
    return EX_OK


def finalize(output: Path, initial_path: Path, final_path: Path, cleanup_ok: bool) -> int:
    report = json.loads(output.read_text(encoding="utf-8"))
    initial = json.loads(initial_path.read_text(encoding="utf-8"))
    final = json.loads(final_path.read_text(encoding="utf-8"))
    lifecycle_restored = initial == final
    report["lifecycle"] = {"initial": initial, "final": final}
    checks = report.setdefault("checks", {})
    checks["lifecycle_restored"] = lifecycle_restored
    checks["cleanup_ok"] = cleanup_ok
    accepted = all(bool(checks.get(name)) for name in ("expected_sample_count", "single_search_epoch", "endpoint_attribution_complete", "lifecycle_restored", "cleanup_ok"))
    report["conclusion"] = "measurement_accepted" if accepted else "measurement_rejected"
    _atomic_json(output, report)
    return EX_OK if accepted else 70


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["run"] and len(args) in {3, 4}:
        count = DEFAULT_CANDIDATES if len(args) == 3 else _positive_int(args[3], "candidate count")
        return run(args[1], Path(args[2]), count)
    if args[:1] == ["finalize"] and len(args) == 5:
        return finalize(Path(args[1]), Path(args[2]), Path(args[3]), args[4].lower() == "true")
    raise ValueError("discovery-probe-measure requires: run REFERENCE_JOB OUTPUT [COUNT] | finalize OUTPUT INITIAL FINAL CLEANUP_OK")
