"""Durable job-scoped timing telemetry for Strategy Lab."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TELEMETRY_SCHEMA = 1
TELEMETRY_FILE = "timing-telemetry.json"
TELEMETRY_LOCK = ".timing-telemetry.lock"


class TelemetryError(RuntimeError):
    """Timing evidence could not be validated or persisted."""


def elapsed_ms(started: float) -> int:
    """Return a non-negative monotonic elapsed duration in milliseconds."""
    return max(0, round((time.monotonic() - started) * 1000))


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(name)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o644)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def _locked(job_dir: Path) -> Iterator[None]:
    job_dir.mkdir(parents=True, exist_ok=True)
    lock_path = job_dir / TELEMETRY_LOCK
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as exc:
        raise TelemetryError(f"Strategy Lab timing lock is unavailable: {lock_path}") from exc
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema": TELEMETRY_SCHEMA, "events": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TelemetryError(f"Strategy Lab timing telemetry is unreadable: {path}") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != TELEMETRY_SCHEMA
        or not isinstance(value.get("events"), list)
    ):
        raise TelemetryError(f"Strategy Lab timing telemetry is invalid: {path}")
    return value


def record(
    job_dir: Path,
    phase: str,
    duration_ms: int,
    *,
    stage: str = "",
    candidate_id: str = "",
    protocol: str = "",
    outcome: str = "",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one measured phase to the canonical job timing document."""
    if not phase or not isinstance(phase, str):
        raise TelemetryError("Strategy Lab timing phase is invalid")
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or duration_ms < 0:
        raise TelemetryError("Strategy Lab timing duration is invalid")
    for value, label in (
        (stage, "stage"),
        (candidate_id, "candidate id"),
        (protocol, "protocol"),
        (outcome, "outcome"),
    ):
        if not isinstance(value, str):
            raise TelemetryError(f"Strategy Lab timing {label} is invalid")
    extra = {} if details is None else details
    if not isinstance(extra, dict):
        raise TelemetryError("Strategy Lab timing details are invalid")
    try:
        json.dumps(extra, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise TelemetryError("Strategy Lab timing details are not serializable") from exc

    path = job_dir / TELEMETRY_FILE
    with _locked(job_dir):
        document = _load(path)
        events = document["events"]
        event = {
            "sequence": len(events) + 1,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "phase": phase,
            "stage": stage,
            "candidate_id": candidate_id,
            "protocol": protocol,
            "outcome": outcome,
            "duration_ms": duration_ms,
            "details": extra,
        }
        events.append(event)
        _atomic_json(path, document)
    return event
