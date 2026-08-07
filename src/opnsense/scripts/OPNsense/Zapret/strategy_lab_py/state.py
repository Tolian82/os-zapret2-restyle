"""Atomic Strategy Lab automated-job state/progress persistence."""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EX_OK = 0
JOB_ID_RE = re.compile(r"^job\.[A-Za-z0-9]+$")
TERMINAL = {"completed", "error"}
PROGRESS = {
    "00": 0, "10": 9, "20": 18, "30": 27, "40": 36, "50": 45,
    "60": 55, "70": 64, "80": 73, "85": 82, "90": 91, "99": 100,
}
STAGES = [
    ("00", "target_initialization"), ("10", "lifecycle_snapshot"),
    ("20", "service_stop"), ("30", "network_precheck"),
    ("40", "clean_baseline"), ("50", "family_screening"),
    ("60", "family_expansion"), ("70", "stability"), ("80", "extended"),
    ("85", "shortlist"), ("90", "restore"), ("99", "report"),
]
JSON_FIELDS = {
    "network", "baseline", "parameter_expansion", "extended", "quic", "udp",
    "lifecycle_snapshot", "restoration",
}


class StateError(RuntimeError):
    pass


class UsageError(StateError):
    pass


class LockTimeout(StateError):
    pass


def _job(value: str) -> str:
    if not JOB_ID_RE.fullmatch(value):
        raise UsageError("invalid Strategy Lab job id")
    return value


def _state(job_id: str, value: str) -> Path:
    job_id = _job(job_id)
    path = Path(value)
    if path.name != "status.json" or path.parent.name != job_id:
        raise UsageError("invalid Strategy Lab automated-job state path")
    return path


def _events(job_id: str, value: str, state: Path) -> Path:
    path = Path(value)
    if path.name != "events.ndjson" or path.parent.name != _job(job_id) or path.parent != state.parent:
        raise UsageError("invalid Strategy Lab event path")
    return path


def _timeout() -> float:
    try:
        value = float(os.environ.get("STRATEGY_LAB_STATE_LOCK_TIMEOUT", "10"))
    except ValueError as exc:
        raise UsageError("invalid Strategy Lab state lock timeout") from exc
    if value < 0:
        raise UsageError("invalid Strategy Lab state lock timeout")
    return value


@contextmanager
def _locked(state: Path):
    state.parent.mkdir(parents=True, exist_ok=True)
    lock = state.with_name("status.lock")
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT, 0o644)
    deadline = time.monotonic() + _timeout()
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockTimeout("Strategy Lab state lock timed out")
                time.sleep(0.025)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _fsync_dir(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.stem}.", dir=path.parent)
    tmp = Path(name)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o644)
        _fsync_dir(path.parent)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(
        path,
        (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
    )


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"Strategy Lab state is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise StateError("Strategy Lab state root must be an object")
    return value


def _input(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"Strategy Lab JSON input is unreadable: {path}") from exc


def _revision(value: dict[str, Any]) -> int:
    revision = value.get("revision", 0)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise StateError("Strategy Lab state revision must be a non-negative integer")
    return revision


def _mutate(path: Path, fn: Callable[[dict[str, Any]], None]) -> None:
    with _locked(path):
        value = _load(path)
        revision = _revision(value)
        fn(value)
        value["revision"] = revision + 1
        _atomic_json(path, value)


def _stage(value: dict[str, Any], number: str) -> dict[str, Any] | None:
    stages = value.get("stages")
    if not isinstance(stages, list):
        return None
    return next(
        (item for item in stages if isinstance(item, dict) and item.get("number") == number),
        None,
    )


def _stage_key(value: dict[str, Any], number: str) -> str:
    item = _stage(value, number)
    key = item.get("key", "") if item else ""
    return key if isinstance(key, str) else ""


def _progress(value: dict[str, Any]) -> dict[str, Any]:
    progress = value.get("progress")
    if not isinstance(progress, dict):
        progress = {}
        value["progress"] = progress
    return progress


def _number(value: str) -> str:
    if value in PROGRESS:
        return value
    try:
        result = f"{int(value, 10):02d}"
    except ValueError as exc:
        raise UsageError("invalid Strategy Lab stage") from exc
    if result not in PROGRESS:
        raise UsageError("invalid Strategy Lab stage")
    return result


def _bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise UsageError("expected boolean true or false")


def initialize(job_id: str, state_name: str, events_name: str, target: str, mode: str, language: str) -> None:
    state = _state(job_id, state_name)
    events = _events(job_id, events_name, state)
    value = {
        "schema": 2, "revision": 0, "job_id": job_id, "state": "queued",
        "outcome": "", "target": target, "target_type": "", "endpoints": [],
        "network": {}, "baseline": {}, "candidate_smoke": {}, "family_screening": {},
        "parameter_expansion": {}, "stability": {}, "shortlist": {}, "extended": {},
        "quic": {}, "udp": {}, "mode": mode, "language": language,
        "initial_service_state": "", "cancel_requested": False,
        "cancel_requested_at": "", "current_stage": "00", "message": "",
        "progress": {"percent": 0, "stage": "00", "stage_key": "target_initialization", "message": ""},
        "circular_eligible": False, "circular_eligibility_reason": "not_completed",
        "circular_candidate_count": 0,
        "stages": [
            {"number": number, "key": key, "status": "PENDING", "message": ""}
            for number, key in STAGES
        ],
    }
    with _locked(state):
        _atomic_json(state, value)
        _atomic_bytes(events, b"")


def set_target(job: str, state_name: str, target: str, target_type: str, endpoints_name: str) -> None:
    state = _state(job, state_name)
    try:
        endpoints = [line for line in Path(endpoints_name).read_text(encoding="utf-8").splitlines() if line]
    except OSError as exc:
        raise StateError(f"Strategy Lab endpoints are unreadable: {endpoints_name}") from exc

    def apply(value: dict[str, Any]) -> None:
        value.update(target=target, target_type=target_type, endpoints=endpoints)

    _mutate(state, apply)


def set_json_field(job: str, state_name: str, field: str, input_name: str) -> None:
    if field not in JSON_FIELDS:
        raise UsageError(f"unsupported Strategy Lab state field: {field}")
    data = _input(input_name)
    _mutate(_state(job, state_name), lambda value: value.__setitem__(field, data))


def set_candidate(job: str, state_name: str, input_name: str) -> None:
    data = _input(input_name)

    def apply(value: dict[str, Any]) -> None:
        value["candidate_smoke"] = data
        value["family_screening"] = data

    _mutate(_state(job, state_name), apply)


def set_stability(job: str, state_name: str, stability_name: str, shortlist_name: str) -> None:
    stability, shortlist = _input(stability_name), _input(shortlist_name)

    def apply(value: dict[str, Any]) -> None:
        value["stability"], value["shortlist"] = stability, shortlist

    _mutate(_state(job, state_name), apply)


def request_cancel(job: str, state_name: str, message: str) -> None:
    requested = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def apply(value: dict[str, Any]) -> None:
        if value.get("state") in TERMINAL:
            return
        if value.get("state") in {"queued", "running", "cancel_requested"}:
            value["state"], value["cancel_requested"] = "cancel_requested", True
            if not isinstance(value.get("cancel_requested_at"), str) or not value["cancel_requested_at"]:
                value["cancel_requested_at"] = requested
            value["message"] = message
            _progress(value)["message"] = message

    _mutate(_state(job, state_name), apply)


def update_job(job: str, state_name: str, new_state: str, outcome: str, stage: str, canceled: bool, message: str) -> None:
    number = _number(stage)

    def apply(value: dict[str, Any]) -> None:
        if value.get("state") in TERMINAL:
            return
        existing = bool(value.get("cancel_requested", False))
        value["state"] = "cancel_requested" if existing and new_state in {"queued", "running"} else new_state
        value["outcome"], value["current_stage"] = outcome, number
        value["cancel_requested"], value["message"] = existing or canceled, message
        _progress(value).update(
            percent=PROGRESS.get(number, 0), stage=number,
            stage_key=_stage_key(value, number), message=message,
        )

    _mutate(_state(job, state_name), apply)


def set_initial_service_state(job: str, state_name: str, service_state: str) -> None:
    _mutate(_state(job, state_name), lambda value: value.__setitem__("initial_service_state", service_state))


def update_stage(job: str, state_name: str, stage: str, status: str, message: str) -> None:
    number = _number(stage)

    def apply(value: dict[str, Any]) -> None:
        if value.get("state") in TERMINAL:
            return
        item = _stage(value, number)
        if item is not None:
            item["status"], item["message"] = status, message
        value["current_stage"] = number
        _progress(value).update(
            percent=PROGRESS.get(number, 0), stage=number,
            stage_key=_stage_key(value, number), message=message,
        )

    _mutate(_state(job, state_name), apply)


def append_event(job: str, state_name: str, events_name: str, stage: str, status: str, message: str) -> None:
    state = _state(job, state_name)
    events = _events(job, events_name, state)
    line = (
        json.dumps(
            {"stage": _number(stage), "status": status, "message": message},
            ensure_ascii=False, separators=(",", ":"),
        ) + "\n"
    ).encode()
    with _locked(state):
        try:
            old = events.read_bytes()
        except FileNotFoundError:
            old = b""
        except OSError as exc:
            raise StateError(f"Strategy Lab event log is unreadable: {events}") from exc
        _atomic_bytes(events, old + line)


def skip_unfinished(job: str, state_name: str, message: str) -> None:
    def apply(value: dict[str, Any]) -> None:
        stages = value.get("stages")
        if not isinstance(stages, list):
            return
        for item in stages:
            if not isinstance(item, dict) or item.get("number") in {"90", "99"}:
                continue
            if item.get("status") in {"PENDING", "RUNNING"}:
                item["status"] = "SKIPPED"
                if not item.get("message"):
                    item["message"] = message

    _mutate(_state(job, state_name), apply)


def set_circular_eligibility(job: str, state_name: str, eligible: bool, reason: str, count: int) -> None:
    if count < 0:
        raise UsageError("invalid circular candidate count")

    def apply(value: dict[str, Any]) -> None:
        value["circular_eligible"] = eligible
        value["circular_eligibility_reason"] = reason
        value["circular_candidate_count"] = count

    _mutate(_state(job, state_name), apply)


def finalize_stale_recovery(job: str, state_name: str, outcome: str, message: str, restore_status: str, restored: bool) -> None:
    def apply(value: dict[str, Any]) -> None:
        value.update(
            state="error", outcome=outcome, current_stage="99", message=message,
            stale_worker_recovered=True,
        )
        if not restored:
            restoration = value.get("restoration")
            if not isinstance(restoration, dict):
                restoration = {}
                value["restoration"] = restoration
            restoration["verified"] = False
        stages = value.get("stages")
        if not isinstance(stages, list):
            return
        for item in stages:
            if not isinstance(item, dict):
                continue
            number = item.get("number")
            if number not in {"90", "99"} and item.get("status") in {"PENDING", "RUNNING"}:
                item["status"] = "SKIPPED"
            elif number == "90":
                item["status"], item["message"] = restore_status, message
            elif number == "99":
                item["status"], item["message"] = "FAIL", message

    _mutate(_state(job, state_name), apply)


def _integer(value: str) -> int:
    try:
        return int(value, 10)
    except ValueError as exc:
        raise UsageError("invalid circular candidate count") from exc


def main(argv: Sequence[str]) -> int:
    args = list(argv)
    if not args:
        raise UsageError("missing Strategy Lab state operation")
    op, args = args[0], args[1:]
    if op == "initialize" and len(args) == 6:
        initialize(*args)
    elif op == "set-target" and len(args) == 5:
        set_target(*args)
    elif op == "set-json-field" and len(args) == 4:
        set_json_field(*args)
    elif op == "set-candidate" and len(args) == 3:
        set_candidate(*args)
    elif op == "set-stability" and len(args) == 4:
        set_stability(*args)
    elif op == "request-cancel" and len(args) == 3:
        request_cancel(*args)
    elif op == "update-job" and len(args) == 7:
        update_job(args[0], args[1], args[2], args[3], args[4], _bool(args[5]), args[6])
    elif op == "set-initial-service-state" and len(args) == 3:
        set_initial_service_state(*args)
    elif op == "update-stage" and len(args) == 5:
        update_stage(*args)
    elif op == "append-event" and len(args) == 6:
        append_event(*args)
    elif op == "skip-unfinished" and len(args) == 3:
        skip_unfinished(*args)
    elif op == "set-circular-eligibility" and len(args) == 5:
        set_circular_eligibility(args[0], args[1], _bool(args[2]), args[3], _integer(args[4]))
    elif op == "finalize-stale-recovery" and len(args) == 6:
        finalize_stale_recovery(args[0], args[1], args[2], args[3], args[4], _bool(args[5]))
    else:
        raise UsageError(f"invalid Strategy Lab state operation: {op}")
    return EX_OK
