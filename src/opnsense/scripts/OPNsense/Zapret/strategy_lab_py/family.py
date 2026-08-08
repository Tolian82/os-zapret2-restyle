"""Python-owned Strategy Lab Stage-50 family ordering and candidate screening."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
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


def _positive_timeout() -> float:
    raw = os.environ.get("STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT", "5")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT must be positive") from exc
    if value <= 0:
        raise ValueError("STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT must be positive")
    operation = os.environ.get("STRATEGY_LAB_OPERATION_TIMEOUT", "").strip()
    if operation:
        try:
            op_value = float(operation)
        except ValueError as exc:
            raise ValueError("STRATEGY_LAB_OPERATION_TIMEOUT must be positive") from exc
        if op_value <= 0:
            raise ValueError("STRATEGY_LAB_OPERATION_TIMEOUT must be positive")
        value = min(value, op_value)
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


def _catalog() -> list[tuple[str, str, str, str]]:
    path = Path(os.environ.get("STRATEGY_LAB_FAMILY_CATALOG", str(module_dir() / "catalog/tls13-families.tsv")))
    if not path.is_file():
        raise RuntimeError(f"Strategy Lab family catalog is unavailable: {path}")
    rows: list[tuple[str, str, str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 4 or not fields[0].strip():
            raise RuntimeError("invalid Strategy Lab family catalog row")
        rows.append((fields[0].strip(), fields[1].strip(), fields[2].strip(), fields[3].strip()))
    if not rows:
        raise RuntimeError("Strategy Lab family catalog is empty")
    return rows


def _cancel_requested(job_id: str) -> bool:
    explicit = os.environ.get("CANCEL_FILE", "").strip()
    path = Path(explicit) if explicit else jobs_dir() / job_id / "cancel.request"
    return path.exists()


def _candidate_runner() -> Path:
    return Path(os.environ.get("STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER", str(script_dir() / "strategy_lab_candidate_runner.sh")))


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
    process.wait(timeout=1)


def _run_candidate(command: list[str], timeout: float, job_id: str) -> tuple[int, bool]:
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
    except OSError as exc:
        raise RuntimeError(f"candidate runner could not start: {exc}") from exc
    elapsed = 0.0
    poll = 0.1
    while process.poll() is None:
        if _cancel_requested(job_id):
            _terminate(process)
            return EX_CANCEL, False
        if elapsed >= timeout:
            _terminate(process)
            return EX_TIMEOUT, True
        try:
            process.wait(timeout=poll)
        except subprocess.TimeoutExpired:
            elapsed += poll
    return int(process.returncode or 0), False


def _timeout_result(candidate_id: str, family: str, strategy: str) -> dict[str, Any]:
    return {
        "id": candidate_id,
        "family": family,
        "strategy": strategy,
        "endpoints": [],
        "all_pass": False,
        "timeout": True,
    }


def _candidate_result(path: Path, candidate_id: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Strategy Lab candidate result is missing: {candidate_id}")
    try:
        candidate = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid Strategy Lab candidate result: {candidate_id}") from exc
    if not isinstance(candidate, dict):
        raise RuntimeError(f"invalid Strategy Lab candidate result object: {candidate_id}")
    return candidate


def screen(job_id: str, endpoints_file: str, result_file: str) -> int:
    if not JOB_RE.fullmatch(job_id):
        return EX_USAGE
    endpoints = Path(endpoints_file)
    if not endpoints.is_file():
        return EX_USAGE
    output = Path(result_file)
    rows = _catalog()
    args_dir = Path(os.environ.get("STRATEGY_LAB_FAMILY_ARGS_DIR", str(module_dir() / "catalog/tls13")))
    runner = _candidate_runner()
    if not runner.is_file():
        raise RuntimeError(f"Strategy Lab candidate runner is unavailable: {runner}")
    timeout = _positive_timeout()
    work = jobs_dir() / job_id / "family-screening"
    work.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "total": len(rows),
        "completed": 0,
        "families": [],
        "accepted": [],
        "rejected": [],
        "all_pass": False,
    }
    _atomic_json(output, result)

    for candidate_id, family, hostlist, args_name in rows:
        if _cancel_requested(job_id):
            return EX_CANCEL
        strategy_path = args_dir / args_name
        if not strategy_path.is_file():
            raise RuntimeError(f"Strategy Lab candidate args are unavailable: {strategy_path}")
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
            candidate = _timeout_result(candidate_id, family, strategy_path.read_text(encoding="utf-8"))
            _atomic_json(candidate_path, candidate)
        else:
            candidate = _candidate_result(candidate_path, candidate_id)
            if status != 0:
                if candidate.get("error") is not True:
                    raise RuntimeError(
                        f"Strategy Lab candidate runner failed for {candidate_id} with status {status} "
                        "without structured candidate error evidence"
                    )
                candidate["runner_status"] = status
                _atomic_json(candidate_path, candidate)
        result["families"].append(candidate)
        result["completed"] = len(result["families"])
        result["accepted"] = [item.get("family", "") for item in result["families"] if item.get("all_pass") is True]
        result["rejected"] = [item.get("family", "") for item in result["families"] if item.get("all_pass") is not True]
        result["all_pass"] = bool(result["accepted"])
        _atomic_json(output, result)

    return EX_OK if result["completed"] == result["total"] else EX_SOFTWARE


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 4 or args[0] != "screen":
        raise ValueError("family requires: screen JOB ENDPOINTS RESULT")
    return screen(args[1], args[2], args[3])
