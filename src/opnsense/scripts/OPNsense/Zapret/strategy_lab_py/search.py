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

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
EX_TIMEOUT = 124
EX_CANCEL = 125
JOB_RE = re.compile(r"^job\.[A-Za-z0-9]+$")


def script_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def module_dir() -> Path:
    return Path(os.environ.get("MODULE_DIR", str(script_dir() / "strategy_lab")))


def jobs_dir() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_JOBS_DIR", "/var/run/zapret2-restyle/strategy-lab/jobs"))


def job_dir(job_id: str) -> Path:
    if not JOB_RE.fullmatch(job_id):
        raise ValueError("invalid Strategy Lab job id")
    return jobs_dir() / job_id


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be positive") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
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


def _catalog(path: Path, fields: int) -> list[tuple[str, ...]]:
    if not path.is_file():
        raise RuntimeError(f"Strategy Lab catalog is unavailable: {path}")
    rows: list[tuple[str, ...]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        values = tuple(part.strip() for part in raw.split("\t"))
        if len(values) != fields or not all(values):
            raise RuntimeError(f"invalid Strategy Lab catalog row: {path}")
        rows.append(values)
    return rows


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
    try:
        subprocess.run(
            [shell, str(adapter), "cleanup", job_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
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
) -> tuple[int, bool]:
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
            return EX_CANCEL, False
        if time.monotonic() >= deadline:
            _terminate(process)
            _cleanup_after_forced_stop(job_id)
            return EX_TIMEOUT, True
        try:
            process.wait(timeout=min(0.1, max(0.01, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            pass
    return int(process.returncode or 0), False


def _read_candidate(path: Path, candidate_id: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Strategy Lab candidate result is missing: {candidate_id}")
    value = _load_json(path)
    return value


def _timeout_result(candidate_id: str, family: str, strategy: str, *, attempt: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": candidate_id,
        "family": family,
        "strategy": strategy,
        "endpoints": [],
        "all_pass": False,
        "timeout": True,
    }
    if attempt is not None:
        result["attempt"] = attempt
    return result


def expand(job_id: str, endpoints_file: str, family_result_file: str, result_file: str) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    family_path = Path(family_result_file)
    if not endpoints.is_file() or not family_path.is_file():
        return EX_USAGE
    output = Path(result_file)
    family_result = _load_json(family_path)
    accepted_raw = family_result.get("accepted", [])
    if not isinstance(accepted_raw, list) or not all(isinstance(item, str) for item in accepted_raw):
        raise RuntimeError("Strategy Lab accepted-family result is invalid")
    accepted = set(accepted_raw)
    catalog_path = Path(os.environ.get("STRATEGY_LAB_EXPANSION_CATALOG", str(module_dir() / "catalog/tls13-expansion.tsv")))
    args_dir = Path(os.environ.get("STRATEGY_LAB_EXPANSION_ARGS_DIR", str(module_dir() / "catalog/tls13-expansion")))
    rows = _catalog(catalog_path, 4)
    selected = [row for row in rows if row[0] in accepted]
    runner = _candidate_runner("STRATEGY_LAB_EXPANSION_CANDIDATE_RUNNER")
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise RuntimeError(f"Strategy Lab expansion candidate runner is unavailable: {runner}")
    timeout = _positive_float("STRATEGY_LAB_EXPANSION_CANDIDATE_TIMEOUT", 5)
    target = _positive_int("STRATEGY_LAB_EXPANSION_TARGET", 5)
    work = job_dir(job_id) / "parameter-expansion"
    work.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "total_available": len(selected),
        "completed": 0,
        "candidates": [],
        "working": [],
        "failed": [],
        "stopped_reason": "",
    }
    _atomic_json(output, result)
    if not selected:
        result["stopped_reason"] = "no_accepted_family"
        _atomic_json(output, result)
        return EX_OK

    for family, candidate_id, hostlist, args_name in selected:
        if _cancel_requested(job_id):
            return EX_CANCEL
        strategy_path = args_dir / args_name
        if not strategy_path.is_file():
            raise RuntimeError(f"Strategy Lab expansion args are unavailable: {strategy_path}")
        strategy = strategy_path.read_text(encoding="utf-8")
        candidate_path = work / f"{candidate_id}.json"
        try:
            candidate_path.unlink()
        except FileNotFoundError:
            pass
        command = [
            str(runner), job_id, str(endpoints), str(candidate_path), candidate_id,
            family, str(strategy_path), hostlist,
        ]
        status, timed_out = _run_candidate(command, timeout, job_id)
        if status == EX_CANCEL:
            return EX_CANCEL
        if timed_out:
            candidate = _timeout_result(candidate_id, family, strategy)
            _atomic_json(candidate_path, candidate)
        elif status != 0:
            raise RuntimeError(f"Strategy Lab expansion candidate runner failed for {candidate_id} with status {status}")
        else:
            candidate = _read_candidate(candidate_path, candidate_id)
        result["candidates"].append(candidate)
        result["completed"] = len(result["candidates"])
        result["working"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("all_pass") is True]
        result["failed"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("all_pass") is not True]
        _atomic_json(output, result)
        if len(result["working"]) >= target:
            result["stopped_reason"] = "enough_candidates"
            _atomic_json(output, result)
            return EX_OK

    result["stopped_reason"] = "catalog_exhausted"
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
    sources = _stability_sources(_load_json(expansion_path), _load_json(family_path))
    attempts = _positive_int("STRATEGY_LAB_STABILITY_ATTEMPTS", 3)
    max_candidates = _positive_int("STRATEGY_LAB_STABILITY_MAX_CANDIDATES", 5)
    target = _positive_int("STRATEGY_LAB_STABILITY_TARGET", 3)
    timeout = _positive_float("STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT", 5)
    runner = _candidate_runner("STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER")
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise RuntimeError(f"Strategy Lab stability candidate runner is unavailable: {runner}")
    work = job_dir(job_id) / "stability"
    work.mkdir(parents=True, exist_ok=True)
    _atomic_json(work / "sources.json", sources)
    result: dict[str, Any] = {
        "total_candidates": len(sources),
        "completed": 0,
        "candidates": [],
        "stable": [],
        "unstable": [],
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
        strategy_path = work / f"{index}.args"
        strategy_path.write_text(strategy, encoding="utf-8")
        os.chmod(strategy_path, 0o644)
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
                family, str(strategy_path), "1",
            ]
            status, timed_out = _run_candidate(
                command, timeout, job_id,
                extra_env={"STRATEGY_LAB_ENDPOINT_PROBE_MODE": "sequential"},
            )
            if status == EX_CANCEL:
                return EX_CANCEL
            if timed_out:
                candidate = _timeout_result(candidate_id, family, strategy, attempt=attempt)
                _atomic_json(attempt_path, candidate)
            elif status != 0:
                raise RuntimeError(f"Strategy Lab stability candidate runner failed for {candidate_id} with status {status}")
            else:
                candidate = _read_candidate(attempt_path, candidate_id)
            attempt_results.append(candidate)
        stable = len(attempt_results) == attempts and all(item.get("all_pass") is True for item in attempt_results)
        candidate_result = {
            "id": candidate_id,
            "family": family,
            "strategy": strategy,
            "attempts": attempt_results,
            "stable": stable,
            "pass_count": len([item for item in attempt_results if item.get("all_pass") is True]),
            "line_count": len([line for line in strategy.split("\n") if line]),
            "character_count": len(strategy),
        }
        _atomic_json(work / f"{index}.json", candidate_result)
        result["candidates"].append(candidate_result)
        result["completed"] = len(result["candidates"])
        result["stable"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("stable") is True]
        result["unstable"] = [str(item.get("id", "")) for item in result["candidates"] if item.get("stable") is not True]
        _atomic_json(output, result)
        if len(result["stable"]) >= target:
            result["stopped_reason"] = "enough_stable_candidates"
            _atomic_json(output, result)
            return EX_OK

    result["stopped_reason"] = "candidates_exhausted"
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
