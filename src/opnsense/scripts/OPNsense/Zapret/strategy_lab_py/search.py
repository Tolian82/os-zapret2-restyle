"""Python-owned Strategy Lab parameter expansion and stability/replay search."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

from . import candidate_spec, endpoint_epoch, resources, search_graph, state as state_persistence, telemetry

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
EX_TIMEOUT = 124
EX_CANCEL = 125
JOB_RE = re.compile(r"^job\.[A-Za-z0-9]+$")


def script_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def jobs_dir() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-restyle/strategy-lab/jobs"))


def job_dir(job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise ValueError("invalid Strategy Lab job id")
    return jobs_dir() / job_id


def _positive_setting_float(name: str, default: float) -> float:
    raw = os.environ.get(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be positive") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _positive_float(name: str, default: float) -> float:
    value = _positive_setting_float(name, default)
    operation = os.environ.get("STRATEGY_LAB_OPERATION_TIMEOUT", "").strip()
    if operation:
        try:
            value = min(value, float(operation))
        except ValueError as exc:
            raise ValueError("STRATEGY_LAB_OPERATION_TIMEOUT must be positive") from exc
        if value <= 0:
            raise ValueError("STRATEGY_LAB_OPERATION_TIMEOUT must be positive")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _operation_deadline_monotonic() -> float | None:
    raw = os.environ.get("STRATEGY_LAB_OPERATION_DEADLINE_MONOTONIC", "").strip()
    if raw:
        try:
            deadline = float(raw)
        except ValueError as exc:
            raise ValueError("STRATEGY_LAB_OPERATION_DEADLINE_MONOTONIC must be positive") from exc
        if deadline <= 0:
            raise ValueError("STRATEGY_LAB_OPERATION_DEADLINE_MONOTONIC must be positive")
        return deadline
    operation = os.environ.get("STRATEGY_LAB_OPERATION_TIMEOUT", "").strip()
    if not operation:
        return None
    try:
        seconds = float(operation)
    except ValueError as exc:
        raise ValueError("STRATEGY_LAB_OPERATION_TIMEOUT must be positive") from exc
    if seconds <= 0:
        raise ValueError("STRATEGY_LAB_OPERATION_TIMEOUT must be positive")
    return time.monotonic() + seconds


def _candidate_admission(timeout: float, deadline: float | None) -> tuple[bool, float | None, float]:
    termination = _positive_setting_float("STRATEGY_LAB_CANDIDATE_TERMINATION_RESERVE", 2)
    cleanup = _positive_setting_float("STRATEGY_LAB_CANDIDATE_CLEANUP_RESERVE", 7)
    guard = _positive_setting_float("STRATEGY_LAB_CANDIDATE_ADMISSION_GUARD", 2)
    required = timeout + termination + cleanup + guard
    if deadline is None:
        return True, None, required
    remaining = max(0.0, deadline - time.monotonic())
    return remaining >= required, remaining, required


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Strategy Lab JSON is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Strategy Lab JSON root is invalid: {path}")
    return value


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, separators=(",", ":"), ensure_ascii=False)
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


def _persist_partial_result(job_id: str, field: str, output: Path, value: dict[str, Any]) -> None:
    _atomic_json(output, value)
    state_path = job_dir(job_id) / "status.json"
    if state_path.is_file():
        state_persistence.set_json_field(job_id, str(state_path), field, str(output))


def _cancel_requested(job_id: str) -> bool:
    explicit = os.environ.get("CANCEL_FILE", "").strip()
    path = Path(explicit) if explicit else job_dir(job_id) / "cancel.request"
    return path.exists()


def _candidate_runner(env_name: str) -> Path:
    return Path(os.environ.get(env_name, str(script_dir() / "strategy_lab_candidate_runner.sh")))


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=1)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def _cleanup_after_forced_stop(job_id: str) -> None:
    adapter = Path(os.environ.get("STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER", str(script_dir() / "strategy_lab_candidate_adapter.sh")))
    if not adapter.is_file():
        return
    shell = os.environ.get("STRATEGY_LAB_SH_BIN", "/bin/sh")
    cleanup_timeout = _positive_setting_float("STRATEGY_LAB_CANDIDATE_CLEANUP_RESERVE", 7)
    try:
        subprocess.run(
            [shell, str(adapter), "cleanup", job_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=cleanup_timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _run_candidate(
    command: list[str],
    timeout: float,
    job_id: str,
    *,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, bool, int]:
    started = time.monotonic()
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
    except OSError as exc:
        raise RuntimeError(f"candidate runner could not start: {exc}") from exc
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        if _cancel_requested(job_id):
            _terminate(process)
            _cleanup_after_forced_stop(job_id)
            return EX_CANCEL, False, telemetry.elapsed_ms(started)
        if time.monotonic() >= deadline:
            _terminate(process)
            _cleanup_after_forced_stop(job_id)
            return EX_TIMEOUT, True, telemetry.elapsed_ms(started)
        try:
            process.wait(timeout=min(0.1, max(0.01, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            pass
    return int(process.returncode or 0), False, telemetry.elapsed_ms(started)


def _read_candidate(path: Path, candidate_id: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Strategy Lab candidate result is missing: {candidate_id}")
    value = _load_json(path)
    return value


def _timeout_result(
    candidate_id: str,
    family: str,
    strategy: str,
    *,
    job_id: str | None = None,
    protocol: str = "tls13",
    transport: str = "tcp",
    port: int = 443,
    l7: str | None = "tls",
    target_binding: bool = True,
    attempt: int | None = None,
    description: candidate_spec.CandidateSpec | None = None,
    epoch: endpoint_epoch.SearchEpoch | None = None,
    runner_ms: int | None = None,
) -> dict[str, Any]:
    if description is None:
        description = candidate_spec.CandidateSpec.from_strategy(
            candidate_id=candidate_id,
            family=family,
            protocol=protocol,
            transport=transport,
            port=port,
            l7=l7,
            strategy=strategy,
            target_binding=target_binding,
        )
    else:
        candidate_id = description.candidate_id
        family = description.family
        strategy = description.strategy
        target_binding = description.target_binding
    result: dict[str, Any] = {
        "id": candidate_id,
        "family": family,
        "strategy": strategy,
        "candidate_spec": description.to_dict(),
        "endpoints": [],
        "all_pass": False,
        "timeout": True,
    }
    if job_id is not None:
        job = job_dir(job_id)
        inventory = resources.ensure_job_inventory(job)
        result["resource_inventory_id"] = inventory.inventory_id
        result["runtime_arguments"] = list(
            description.render_runtime_arguments(
                inventory,
                divert_port=int(os.environ.get("STRATEGY_LAB_DIVERT_PORT", "9989")),
                hostlist_path=(
                    job / "candidate-runtime/hostlist.txt" if target_binding else None
                ),
            )
        )
    if attempt is not None:
        result["attempt"] = attempt
    if epoch is not None:
        result["search_epoch_id"] = epoch.epoch_id
        result["search_epoch_generation"] = epoch.generation
        result["endpoint_bindings"] = list(epoch.bindings)
    if runner_ms is not None:
        result["runner_duration_ms"] = runner_ms
    return result


def expand(job_id: str, endpoints_file: str, family_result_file: str, result_file: str) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    family_path = Path(family_result_file)
    if not endpoints.is_file() or not family_path.is_file():
        return EX_USAGE
    output = Path(result_file)
    endpoint_values = [
        line.strip()
        for line in endpoints.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    epoch = endpoint_epoch.load(job_dir(job_id), endpoint_values)
    family_result = _load_json(family_path)
    accepted_raw = family_result.get("accepted", [])
    if not isinstance(accepted_raw, list) or not all(isinstance(item, str) for item in accepted_raw):
        raise RuntimeError("Strategy Lab Stage-50 family evidence is invalid")
    reconnaissance = family_result.get("families", [])
    if not isinstance(reconnaissance, list):
        raise RuntimeError("Strategy Lab Stage-50 candidate evidence is invalid")
    if family_result.get("search_epoch_id") != epoch.epoch_id:
        raise RuntimeError("Strategy Lab Stage-50 evidence belongs to another search epoch")
    inventory = resources.ensure_job_inventory(job_dir(job_id))
    graph = search_graph.native_tls13_graph()
    plan = graph.plan("expansion", accepted_raw, inventory)
    plan_evidence = plan.to_dict()
    plan_evidence["search_epoch_id"] = epoch.epoch_id
    _atomic_json(job_dir(job_id) / "search-graph.json", plan_evidence)
    runner = _candidate_runner("STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER")
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise RuntimeError(f"Strategy Lab expansion candidate runner is unavailable: {runner}")
    timeout = _positive_float("STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT", 5)
    operation_deadline = _operation_deadline_monotonic()
    target = _positive_int("STRATEGY_LAB_EXPANSION_TARGET", 3)
    minimum = _positive_int("STRATEGY_LAB_EXPANSION_MIN_WINNERS", min(2, target))
    if minimum > target:
        raise ValueError("STRATEGY_LAB_EXPANSION_MIN_WINNERS cannot exceed the winner target")
    work = job_dir(job_id) / "parameter-expansion"
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
    }
    _atomic_json(output, result)
    if not plan.scheduled:
        result["stopped_reason"] = "graph_exhausted"
        _atomic_json(output, result)
        return EX_OK

    observations: list[dict[str, Any]] = []
    while True:
        decision = graph.next_expansion(plan, reconnaissance, observations)
        if decision is None:
            break
        node = decision.node
        if _cancel_requested(job_id):
            return EX_CANCEL
        description = node.spec
        candidate_id = description.candidate_id
        family = description.family
        admitted, remaining, required = _candidate_admission(timeout, operation_deadline)
        if not admitted:
            result["stopped_reason"] = "insufficient_stage_budget"
            result["partial"] = True
            result["budget_admission"] = {
                "next_candidate": candidate_id,
                "remaining_seconds": round(remaining or 0.0, 3),
                "required_seconds": round(required, 3),
            }
            _persist_partial_result(job_id, "parameter_expansion", output, result)
            telemetry.record(
                job_dir(job_id),
                "candidate_admission",
                0,
                stage="60",
                candidate_id=candidate_id,
                protocol="tls13",
                outcome="deferred",
                details=result["budget_admission"],
            )
            return EX_TIMEOUT
        hostlist = "1" if description.target_binding else "0"
        strategy = description.strategy
        strategy_path = work / f"{candidate_id}.args"
        strategy_path.write_text(strategy, encoding="utf-8")
        os.chmod(strategy_path, 0o644)
        spec_path = work / f"{candidate_id}.spec.json"
        _atomic_json(spec_path, description.to_dict())
        candidate_path = work / f"{candidate_id}.json"
        try:
            candidate_path.unlink()
        except FileNotFoundError:
            pass
        command = [
            str(runner), job_id, str(endpoints), str(candidate_path), candidate_id,
            family, str(strategy_path), hostlist, str(spec_path),
        ]
        status, timed_out, runner_ms = _run_candidate(command, timeout, job_id)
        if status == EX_CANCEL:
            return EX_CANCEL
        if timed_out:
            candidate = _timeout_result(
                candidate_id,
                family,
                strategy,
                job_id=job_id,
                description=description,
                epoch=epoch,
                runner_ms=runner_ms,
            )
            _atomic_json(candidate_path, candidate)
        elif status != 0:
            raise RuntimeError(f"Strategy Lab expansion candidate runner failed for {candidate_id} with status {status}")
        else:
            candidate = _read_candidate(candidate_path, candidate_id)
        if candidate.get("search_epoch_id") != epoch.epoch_id:
            raise RuntimeError(
                f"Strategy Lab expansion candidate changed search epoch: {candidate_id}"
            )
        candidate["strategy"] = description.strategy
        candidate["candidate_spec"] = description.to_dict()
        candidate["resource_inventory_id"] = inventory.inventory_id
        candidate["graph_node"] = node.to_dict()
        candidate["runner_duration_ms"] = runner_ms
        _atomic_json(candidate_path, candidate)
        passed = candidate.get("all_pass") is True
        observations.append({"candidate_id": candidate_id, "all_pass": passed})
        schedule_item = decision.to_dict()
        schedule_item.update(
            sequence=len(observations),
            outcome="pass" if passed else "fail",
            duration_ms=runner_ms,
        )
        result["schedule"].append(schedule_item)
        result["candidates"].append(candidate)
        result["completed"] = len(result["candidates"])
        result["working"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("all_pass") is True]
        result["failed"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("all_pass") is not True]
        result["early_stop"]["winner_count"] = len(result["working"])
        _atomic_json(output, result)
        telemetry.record(
            job_dir(job_id),
            "adaptive_candidate",
            runner_ms,
            stage="60",
            candidate_id=candidate_id,
            protocol="tls13",
            outcome="pass" if passed else "fail",
            details={
                "search_epoch_id": epoch.epoch_id,
                "decision": schedule_item,
            },
        )
        if len(result["working"]) >= target:
            result["stopped_reason"] = "enough_candidates"
            result["early_stop"]["triggered"] = True
            _atomic_json(output, result)
            return EX_OK

    result["stopped_reason"] = "graph_exhausted"
    result["early_stop"]["winner_count"] = len(result["working"])
    result["early_stop"]["within_normal_band"] = (
        minimum <= len(result["working"]) <= target
    )
    _atomic_json(output, result)
    return EX_OK


def _stability_sources(expansion: dict[str, Any], family: dict[str, Any]) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    for container, key in ((expansion, "candidates"), (family, "families")):
        items = container.get(key, [])
        if not isinstance(items, list):
            raise RuntimeError("Strategy Lab stability source list is invalid")
        for item in items:
            if isinstance(item, dict) and item.get("all_pass") is True and isinstance(item.get("strategy"), str):
                combined.append(dict(item))
    by_strategy: dict[str, dict[str, Any]] = {}
    for item in sorted(combined, key=lambda value: str(value.get("strategy", ""))):
        by_strategy.setdefault(str(item["strategy"]), item)
    sources: list[dict[str, Any]] = []
    for item in by_strategy.values():
        strategy = str(item["strategy"])
        enriched = dict(item)
        enriched["line_count"] = len([line for line in strategy.split("\n") if line])
        enriched["character_count"] = len(strategy)
        sources.append(enriched)
    sources.sort(key=lambda item: (int(item["line_count"]), int(item["character_count"]), str(item.get("id", ""))))
    return sources


def _source_description(source: dict[str, Any]) -> candidate_spec.CandidateSpec:
    raw = source.get("candidate_spec")
    if isinstance(raw, dict):
        try:
            description = candidate_spec.CandidateSpec.from_dict(raw)
        except candidate_spec.CandidateSpecError as exc:
            raise RuntimeError("Strategy Lab stability candidate spec is invalid") from exc
        if (
            description.candidate_id != source.get("id")
            or description.family != source.get("family")
            or description.strategy_lines
            != tuple(line for line in str(source.get("strategy", "")).splitlines() if line)
        ):
            raise RuntimeError("Strategy Lab stability candidate spec does not match its source")
        return description
    return candidate_spec.CandidateSpec.from_strategy(
        candidate_id=str(source.get("id", "")),
        family=str(source.get("family", "")),
        protocol="tls13",
        transport="tcp",
        port=443,
        l7="tls",
        strategy=str(source.get("strategy", "")),
        target_binding=True,
        provenance="stability-compatibility-source",
    )


def stabilize(
    job_id: str,
    endpoints_file: str,
    expansion_file: str,
    family_file: str,
    result_file: str,
) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    expansion_path = Path(expansion_file)
    family_path = Path(family_file)
    if not endpoints.is_file() or not expansion_path.is_file() or not family_path.is_file():
        return EX_USAGE
    output = Path(result_file)
    endpoint_values = [
        line.strip()
        for line in endpoints.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    epoch = endpoint_epoch.load(job_dir(job_id), endpoint_values)
    expansion_result = _load_json(expansion_path)
    family_result = _load_json(family_path)
    if expansion_result.get("search_epoch_id") != epoch.epoch_id:
        raise RuntimeError("Strategy Lab Stage-60 evidence belongs to another search epoch")
    if family_result.get("search_epoch_id") != epoch.epoch_id:
        raise RuntimeError("Strategy Lab Stage-50 evidence belongs to another search epoch")
    sources = _stability_sources(expansion_result, family_result)
    attempts = _positive_int("STRATEGY_LAB_STABILITY_ATTEMPTS", 3)
    max_candidates = _positive_int("STRATEGY_LAB_STABILITY_MAX_CANDIDATES", 5)
    target = _positive_int("STRATEGY_LAB_STABILITY_TARGET", 3)
    minimum = _positive_int("STRATEGY_LAB_STABILITY_MIN_WINNERS", min(2, target))
    if minimum > target:
        raise ValueError("STRATEGY_LAB_STABILITY_MIN_WINNERS cannot exceed the winner target")
    timeout = _positive_float("STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT", 5)
    runner = _candidate_runner("STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER")
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise RuntimeError(f"Strategy Lab stability candidate runner is unavailable: {runner}")
    work = job_dir(job_id) / "stability"
    work.mkdir(parents=True, exist_ok=True)
    _atomic_json(work / "sources.json", sources)
    result: dict[str, Any] = {
        "search_epoch_id": epoch.epoch_id,
        "total_candidates": len(sources),
        "completed": 0,
        "candidates": [],
        "stable": [],
        "unstable": [],
        "winner_band": {"minimum": minimum, "target": target},
        "early_stop": {"triggered": False, "winner_count": 0},
        "stopped_reason": "",
    }
    _atomic_json(output, result)
    if not sources:
        result["stopped_reason"] = "no_working_candidate"
        _atomic_json(output, result)
        return EX_OK

    for index, source in enumerate(sources[:max_candidates], 1):
        if _cancel_requested(job_id):
            return EX_CANCEL
        candidate_id = str(source.get("id", ""))
        family = str(source.get("family", ""))
        strategy = str(source.get("strategy", ""))
        if not candidate_id or not family or not strategy:
            raise RuntimeError("Strategy Lab stability source is incomplete")
        description = _source_description(source)
        strategy_path = work / f"{index}.args"
        strategy_path.write_text(description.strategy, encoding="utf-8")
        os.chmod(strategy_path, 0o644)
        spec_path = work / f"{index}.spec.json"
        _atomic_json(spec_path, description.to_dict())
        attempt_dir = work / f"{index}-attempts"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        attempt_results: list[dict[str, Any]] = []
        for attempt in range(1, attempts + 1):
            if _cancel_requested(job_id):
                return EX_CANCEL
            attempt_path = attempt_dir / f"{attempt}.json"
            try:
                attempt_path.unlink()
            except FileNotFoundError:
                pass
            command = [
                str(runner), job_id, str(endpoints), str(attempt_path), candidate_id,
                family, str(strategy_path),
                "1" if description.target_binding else "0", str(spec_path),
            ]
            status, timed_out, runner_ms = _run_candidate(
                command, timeout, job_id,
                extra_env={"STRATEGY_LAB_ENDPOINT_PROBE_MODE": "sequential"},
            )
            if status == EX_CANCEL:
                return EX_CANCEL
            if timed_out:
                candidate = _timeout_result(
                    candidate_id,
                    family,
                    strategy,
                    job_id=job_id,
                    attempt=attempt,
                    description=description,
                    epoch=epoch,
                    runner_ms=runner_ms,
                )
                _atomic_json(attempt_path, candidate)
            elif status != 0:
                raise RuntimeError(f"Strategy Lab stability candidate runner failed for {candidate_id} with status {status}")
            else:
                candidate = _read_candidate(attempt_path, candidate_id)
            if candidate.get("search_epoch_id") != epoch.epoch_id:
                raise RuntimeError(
                    f"Strategy Lab stability candidate changed search epoch: {candidate_id}"
                )
            candidate["runner_duration_ms"] = runner_ms
            candidate["attempt"] = attempt
            _atomic_json(attempt_path, candidate)
            attempt_results.append(candidate)
            telemetry.record(
                job_dir(job_id),
                "stability_attempt",
                runner_ms,
                stage="70",
                candidate_id=candidate_id,
                protocol="tls13",
                outcome="pass" if candidate.get("all_pass") is True else "fail",
                details={
                    "attempt": attempt,
                    "search_epoch_id": epoch.epoch_id,
                    "timed_out": timed_out,
                },
            )
        stable = len(attempt_results) == attempts and all(item.get("all_pass") is True for item in attempt_results)
        candidate_result = {
            "id": candidate_id,
            "family": family,
            "strategy": description.strategy,
            "candidate_spec": description.to_dict(),
            "search_epoch_id": epoch.epoch_id,
            "search_epoch_generation": epoch.generation,
            "endpoint_bindings": list(epoch.bindings),
            "attempts": attempt_results,
            "stable": stable,
            "pass_count": len([item for item in attempt_results if item.get("all_pass") is True]),
            "line_count": len(description.strategy_lines),
            "character_count": len(description.strategy),
        }
        for key in ("resource_inventory_id", "graph_node"):
            if key in source:
                candidate_result[key] = source[key]
        _atomic_json(work / f"{index}.json", candidate_result)
        result["candidates"].append(candidate_result)
        result["completed"] = len(result["candidates"])
        result["stable"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("stable") is True]
        result["unstable"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("stable") is not True]
        result["early_stop"]["winner_count"] = len(result["stable"])
        _atomic_json(output, result)
        if len(result["stable"]) >= target:
            result["stopped_reason"] = "enough_stable_candidates"
            result["early_stop"]["triggered"] = True
            _atomic_json(output, result)
            return EX_OK

    result["stopped_reason"] = "candidates_exhausted"
    result["early_stop"]["winner_count"] = len(result["stable"])
    result["early_stop"]["within_normal_band"] = (
        minimum <= len(result["stable"]) <= target
    )
    _atomic_json(output, result)
    return EX_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise ValueError("search operation is required")
    if args[0] == "expand" and len(args) == 5:
        return expand(args[1], args[2], args[3], args[4])
    if args[0] == "stabilize" and len(args) == 6:
        return stabilize(args[1], args[2], args[3], args[4], args[5])
    raise ValueError(
        "search requires: expand JOB ENDPOINTS FAMILY_RESULT RESULT | "
        "stabilize JOB ENDPOINTS EXPANSION FAMILY_RESULT RESULT"
    )