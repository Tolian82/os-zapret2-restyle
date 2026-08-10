"""Strategy Lab `_33` discovery, fail-fast stability, and finalist validation.

The cold candidate lifecycle remains the correctness reference. This module only changes
which bounded GET is used at each evidence tier, stops impossible 3/3 stability checks
early, and gives the final published finalists one cold depth validation. Warm workers,
parallel probes, and dispatcher experiments remain outside this source slice.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from . import candidate as candidate_screening
from . import family as family_screening
from . import late_containment
from . import request as request_execution
from . import result as final_result
from . import search as search_orchestration
from . import telemetry

EX_OK = 0
EX_USAGE = 64
EX_TIMEOUT = 124
EX_CANCEL = 125

DISCOVERY_RANGE_BYTES_ENV = "STRATEGY_LAB_DISCOVERY_RANGE_BYTES"
DISCOVERY_RANGE_BYTES_DEFAULT = 4096
DISCOVERY_MAX_TIME_ENV = "STRATEGY_LAB_DISCOVERY_MAX_TIME"
DISCOVERY_MAX_TIME_DEFAULT = 3
FINALIST_TARGET_BYTES_ENV = "STRATEGY_LAB_FINALIST_TARGET_BYTES"
FINALIST_TARGET_BYTES_DEFAULT = 16384
FINALIST_RANGE_BYTES_ENV = "STRATEGY_LAB_FINALIST_RANGE_BYTES"
FINALIST_RANGE_BYTES_DEFAULT = 65536
FINALIST_MAX_TIME_ENV = "STRATEGY_LAB_FINALIST_MAX_TIME"
FINALIST_MAX_TIME_DEFAULT = 6
FINALIST_CANDIDATE_TIMEOUT_ENV = "STRATEGY_LAB_FINALIST_CANDIDATE_TIMEOUT"
FINALIST_CANDIDATE_TIMEOUT_DEFAULT = 15
PROBE_TIER_ENV = "STRATEGY_LAB_PROBE_TIER"
WRITEOUT_RE = re.compile(
    r"(?:^|\s)exit=(\d+)\s+remote_ip=([^\s]*)\s+http=([^\s]*)\s+code=(\d+)\s+bytes=(\d+)(?:\s|$)"
)

_ORIGINAL_CURL_REQUEST = request_execution.curl_request


def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _replace_option(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError as exc:
        raise request_execution.RequestError(
            f"Strategy Lab curl command has no {option} option"
        ) from exc
    if index + 1 >= len(command):
        raise request_execution.RequestError(
            f"Strategy Lab curl command has no {option} value"
        )
    command[index + 1] = value


def _tiered_curl_request(
    host: str,
    *,
    scheme: str,
    family: str = "ipv4",
    tls_version: str | None = None,
    bound_ip: str | None = None,
) -> request_execution.CommandResult:
    tier = os.environ.get(PROBE_TIER_ENV, "").strip()
    if tier not in {"discovery", "stability", "deep"}:
        return _ORIGINAL_CURL_REQUEST(
            host,
            scheme=scheme,
            family=family,
            tls_version=tls_version,
            bound_ip=bound_ip,
        )

    command = request_execution._curl_command(
        host,
        scheme=scheme,
        family=family,
        tls_version=tls_version,
        bound_ip=bound_ip,
    )
    if tier in {"discovery", "stability"}:
        byte_limit = _positive_int_env(
            DISCOVERY_RANGE_BYTES_ENV, DISCOVERY_RANGE_BYTES_DEFAULT
        )
        max_time = _positive_int_env(
            DISCOVERY_MAX_TIME_ENV, DISCOVERY_MAX_TIME_DEFAULT
        )
    else:
        byte_limit = _positive_int_env(
            FINALIST_RANGE_BYTES_ENV, FINALIST_RANGE_BYTES_DEFAULT
        )
        max_time = _positive_int_env(FINALIST_MAX_TIME_ENV, FINALIST_MAX_TIME_DEFAULT)
    _replace_option(command, "--range", f"0-{byte_limit - 1}")
    _replace_option(command, "--max-time", str(max_time))
    return request_execution.run_command(command, timeout=max_time + 1)


def install_candidate_probe_policy() -> None:
    """Install the request tier selected by the parent candidate operation."""
    tier = os.environ.get(PROBE_TIER_ENV, "").strip()
    if tier in {"discovery", "stability", "deep"}:
        request_execution.curl_request = _tiered_curl_request


@contextmanager
def probe_tier(tier: str) -> Iterator[None]:
    if tier not in {"discovery", "stability", "deep"}:
        raise ValueError("invalid Strategy Lab probe tier")
    previous = os.environ.get(PROBE_TIER_ENV)
    os.environ[PROBE_TIER_ENV] = tier
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(PROBE_TIER_ENV, None)
        else:
            os.environ[PROBE_TIER_ENV] = previous


def run_family(argv: Sequence[str]) -> int:
    with probe_tier("discovery"):
        return family_screening.main(argv)


def _fail_fast_reason(candidate: dict[str, Any]) -> str:
    if candidate.get("timeout") is True:
        return "attempt_timeout"
    if candidate.get("error") is True:
        return "candidate_error"
    return "network_or_protocol_fail"


def _stability_result(
    *,
    source: dict[str, Any],
    description: Any,
    epoch: Any,
    attempt_results: list[dict[str, Any]],
    attempts_required: int,
    fail_fast: dict[str, Any],
) -> dict[str, Any]:
    stable = (
        len(attempt_results) == attempts_required
        and all(item.get("all_pass") is True for item in attempt_results)
    )
    value: dict[str, Any] = {
        "id": str(source.get("id", "")),
        "family": str(source.get("family", "")),
        "strategy": description.strategy,
        "candidate_spec": description.to_dict(),
        "search_epoch_id": epoch.epoch_id,
        "search_epoch_generation": epoch.generation,
        "endpoint_bindings": list(epoch.bindings),
        "attempts": attempt_results,
        "attempts_required": attempts_required,
        "attempts_executed": len(attempt_results),
        "stable": stable,
        "pass_count": len(
            [item for item in attempt_results if item.get("all_pass") is True]
        ),
        "line_count": len(description.strategy_lines),
        "character_count": len(description.strategy),
        "fail_fast": fail_fast,
    }
    for key in ("resource_inventory_id", "graph_node"):
        if key in source:
            value[key] = source[key]
    return value


def stabilize(
    job_id: str,
    endpoints_file: str,
    expansion_file: str,
    family_file: str,
    result_file: str,
) -> int:
    if not search_orchestration.JOB_RE.fullmatch(job_id):
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
    epoch = search_orchestration.endpoint_epoch.load(
        search_orchestration.job_dir(job_id), endpoint_values
    )
    expansion_result = search_orchestration._load_json(expansion_path)
    family_result = search_orchestration._load_json(family_path)
    if expansion_result.get("search_epoch_id") != epoch.epoch_id:
        raise RuntimeError("Strategy Lab Stage-60 evidence belongs to another search epoch")
    if family_result.get("search_epoch_id") != epoch.epoch_id:
        raise RuntimeError("Strategy Lab Stage-50 evidence belongs to another search epoch")

    sources = search_orchestration._stability_sources(expansion_result, family_result)
    attempts = search_orchestration._positive_int("STRATEGY_LAB_STABILITY_ATTEMPTS", 3)
    max_candidates = search_orchestration._positive_int(
        "STRATEGY_LAB_STABILITY_MAX_CANDIDATES", 5
    )
    target = search_orchestration._positive_int("STRATEGY_LAB_STABILITY_TARGET", 3)
    minimum = search_orchestration._positive_int(
        "STRATEGY_LAB_STABILITY_MIN_WINNERS", min(2, target)
    )
    if minimum > target:
        raise ValueError(
            "STRATEGY_LAB_STABILITY_MIN_WINNERS cannot exceed the winner target"
        )
    timeout = search_orchestration._positive_float(
        "STRATEGY_LAB_STABILITY_ATTEMPT_TIMEOUT", 5
    )
    operation_deadline = search_orchestration._operation_deadline_monotonic()
    runner = search_orchestration._candidate_runner(
        "STRATEGY_LAB_STABILITY_CANDIDATE_RUNNER"
    )
    if not runner.is_file() or not os.access(runner, os.X_OK):
        raise RuntimeError(
            f"Strategy Lab stability candidate runner is unavailable: {runner}"
        )

    work = search_orchestration.job_dir(job_id) / "stability"
    work.mkdir(parents=True, exist_ok=True)
    search_orchestration._atomic_json(work / "sources.json", sources)
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
        "partial": False,
        "validation_policy": "fail_fast_3_of_3",
        "saved_attempts": 0,
    }
    search_orchestration._atomic_json(output, result)
    if not sources:
        result["stopped_reason"] = "no_working_candidate"
        search_orchestration._atomic_json(output, result)
        return EX_OK

    for index, source in enumerate(sources[:max_candidates], 1):
        if search_orchestration._cancel_requested(job_id):
            return EX_CANCEL
        candidate_id = str(source.get("id", ""))
        family = str(source.get("family", ""))
        strategy = str(source.get("strategy", ""))
        if not candidate_id or not family or not strategy:
            raise RuntimeError("Strategy Lab stability source is incomplete")
        description = search_orchestration._source_description(source)
        strategy_path = work / f"{index}.args"
        strategy_path.write_text(description.strategy, encoding="utf-8")
        os.chmod(strategy_path, 0o644)
        spec_path = work / f"{index}.spec.json"
        search_orchestration._atomic_json(spec_path, description.to_dict())
        attempt_dir = work / f"{index}-attempts"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        attempt_results: list[dict[str, Any]] = []
        fail_fast: dict[str, Any] = {
            "triggered": False,
            "failed_attempt": None,
            "skipped_attempts": [],
            "reason": "",
        }

        for attempt in range(1, attempts + 1):
            if search_orchestration._cancel_requested(job_id):
                return EX_CANCEL
            deferred = late_containment._defer_candidate(
                stage="70",
                candidate_id=candidate_id,
                protocol="tls13",
                timeout=timeout,
                deadline=operation_deadline,
                attempt=attempt,
            )
            if deferred is not None:
                return late_containment._stability_partial(
                    job_id=job_id,
                    output=output,
                    result=result,
                    exc=deferred,
                    attempt_results=attempt_results,
                )

            attempt_path = attempt_dir / f"{attempt}.json"
            try:
                attempt_path.unlink()
            except FileNotFoundError:
                pass
            command = [
                str(runner),
                job_id,
                str(endpoints),
                str(attempt_path),
                candidate_id,
                family,
                str(strategy_path),
                "1" if description.target_binding else "0",
                str(spec_path),
            ]
            status, timed_out, runner_ms = search_orchestration._run_candidate(
                command,
                timeout,
                job_id,
                extra_env={
                    "STRATEGY_LAB_ENDPOINT_PROBE_MODE": "sequential",
                    PROBE_TIER_ENV: "stability",
                },
            )
            if status == EX_CANCEL:
                return EX_CANCEL
            if timed_out:
                candidate = search_orchestration._timeout_result(
                    candidate_id,
                    family,
                    strategy,
                    job_id=job_id,
                    attempt=attempt,
                    description=description,
                    epoch=epoch,
                    runner_ms=runner_ms,
                )
                search_orchestration._atomic_json(attempt_path, candidate)
            elif status != 0:
                raise RuntimeError(
                    "Strategy Lab stability candidate runner failed for "
                    f"{candidate_id} with status {status}"
                )
            else:
                candidate = search_orchestration._read_candidate(
                    attempt_path, candidate_id
                )
            if candidate.get("search_epoch_id") != epoch.epoch_id:
                raise RuntimeError(
                    f"Strategy Lab stability candidate changed search epoch: {candidate_id}"
                )
            candidate["runner_duration_ms"] = runner_ms
            candidate["attempt"] = attempt
            search_orchestration._atomic_json(attempt_path, candidate)
            attempt_results.append(candidate)
            passed = candidate.get("all_pass") is True
            telemetry.record(
                search_orchestration.job_dir(job_id),
                "stability_attempt",
                runner_ms,
                stage="70",
                candidate_id=candidate_id,
                protocol="tls13",
                outcome="pass" if passed else "fail",
                details={
                    "attempt": attempt,
                    "search_epoch_id": epoch.epoch_id,
                    "timed_out": timed_out,
                    "validation_policy": "fail_fast_3_of_3",
                },
            )
            if not passed:
                skipped = list(range(attempt + 1, attempts + 1))
                fail_fast = {
                    "triggered": True,
                    "failed_attempt": attempt,
                    "skipped_attempts": skipped,
                    "reason": _fail_fast_reason(candidate),
                }
                result["saved_attempts"] = int(result["saved_attempts"]) + len(skipped)
                telemetry.record(
                    search_orchestration.job_dir(job_id),
                    "stability_fail_fast",
                    0,
                    stage="70",
                    candidate_id=candidate_id,
                    protocol="tls13",
                    outcome="rejected",
                    details=fail_fast,
                )
                break

        candidate_result = _stability_result(
            source=source,
            description=description,
            epoch=epoch,
            attempt_results=attempt_results,
            attempts_required=attempts,
            fail_fast=fail_fast,
        )
        search_orchestration._atomic_json(work / f"{index}.json", candidate_result)
        result["candidates"].append(candidate_result)
        result["completed"] = len(result["candidates"])
        result["stable"] = [
            str(item.get("id", ""))
            for item in result["candidates"]
            if item.get("stable") is True
        ]
        result["unstable"] = [
            str(item.get("id", ""))
            for item in result["candidates"]
            if item.get("stable") is not True
        ]
        result["early_stop"]["winner_count"] = len(result["stable"])
        search_orchestration._atomic_json(output, result)
        if len(result["stable"]) >= target:
            result["stopped_reason"] = "enough_stable_candidates"
            result["early_stop"]["triggered"] = True
            search_orchestration._atomic_json(output, result)
            return EX_OK

    result["stopped_reason"] = "candidates_exhausted"
    result["early_stop"]["winner_count"] = len(result["stable"])
    result["early_stop"]["within_normal_band"] = (
        minimum <= len(result["stable"]) <= target
    )
    search_orchestration._atomic_json(output, result)
    return EX_OK


def run_search(argv: Sequence[str]) -> int:
    args = list(argv)
    if args[:1] == ["stabilize"] and len(args) == 6:
        return stabilize(args[1], args[2], args[3], args[4], args[5])
    with probe_tier("discovery"):
        return late_containment.run_search(args)


def run_extended(argv: Sequence[str]) -> int:
    with probe_tier("discovery"):
        return late_containment.run_extended(argv)


def _writeout(endpoint: dict[str, Any]) -> tuple[int | None, int | None]:
    execution = endpoint.get("execution")
    if not isinstance(execution, dict):
        return None, None
    stdout = execution.get("stdout")
    if not isinstance(stdout, str):
        return None, None
    match = None
    for match in WRITEOUT_RE.finditer(stdout):
        pass
    if match is None:
        return None, None
    return int(match.group(4), 10), int(match.group(5), 10)


def classify_deep_replay(
    replay: dict[str, Any], protocol: str, target_bytes: int
) -> dict[str, Any]:
    base_verified = replay.get("all_pass") is True and replay.get("profile_exact") is True
    endpoints = replay.get("endpoints")
    endpoints = endpoints if isinstance(endpoints, list) else []
    if not base_verified or not endpoints:
        return {
            "classification": "fail",
            "accepted": False,
            "target_bytes": target_bytes,
            "bytes_received": 0,
            "http_statuses": [],
            "reason": "cold_replay_failed",
        }
    if protocol not in {"tls13", "tls12", "http"}:
        return {
            "classification": "not_applicable",
            "accepted": True,
            "target_bytes": target_bytes,
            "bytes_received": None,
            "http_statuses": [],
            "reason": "non_http_protocol",
        }

    statuses: list[int] = []
    byte_counts: list[int] = []
    incomplete = False
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            return {
                "classification": "fail",
                "accepted": False,
                "target_bytes": target_bytes,
                "bytes_received": 0,
                "http_statuses": statuses,
                "reason": "invalid_endpoint_evidence",
            }
        firewall = endpoint.get("firewall")
        if endpoint.get("status") != "PASS" or not isinstance(firewall, dict) or firewall.get("intercepted") is not True:
            return {
                "classification": "fail",
                "accepted": False,
                "target_bytes": target_bytes,
                "bytes_received": min(byte_counts) if byte_counts else 0,
                "http_statuses": statuses,
                "reason": "interception_or_endpoint_failed",
            }
        status, count = _writeout(endpoint)
        if status is None or count is None:
            incomplete = True
            continue
        statuses.append(status)
        byte_counts.append(count)
        if status < 100 or status >= 400:
            return {
                "classification": "fail",
                "accepted": False,
                "target_bytes": target_bytes,
                "bytes_received": min(byte_counts) if byte_counts else 0,
                "http_statuses": statuses,
                "reason": "http_status_failed",
            }

    received = min(byte_counts) if byte_counts else None
    if incomplete or received is None:
        classification = "inconclusive"
        reason = "byte_evidence_unavailable"
    elif received >= target_bytes:
        classification = "pass"
        reason = "target_bytes_received"
    else:
        classification = "inconclusive"
        reason = "resource_completed_short"
    return {
        "classification": classification,
        "accepted": True,
        "target_bytes": target_bytes,
        "bytes_received": received,
        "http_statuses": statuses,
        "reason": reason,
    }


def _deep_replay_once(
    job_id: str,
    endpoints_path: Path,
    source: dict[str, Any],
    profile_path: Path,
    target: str,
    target_type: str,
    payload_path: Path | None,
    timeout: float,
) -> tuple[dict[str, Any], int]:
    spec = final_result.contract(str(source["protocol"]), int(source["port"]))
    selector = final_result.selector_for(
        target, target_type, spec.protocol, str(source.get("selector_addresses", ""))
    )
    result_path = profile_path.with_name(f"{profile_path.stem}.deep.json")
    try:
        result_path.unlink()
    except FileNotFoundError:
        pass

    fixture_runner = final_result._fixture_replay_runner()
    if fixture_runner:
        with probe_tier("deep"):
            status = final_result._run_fixture_replay(
                fixture_runner,
                job_id,
                endpoints_path,
                result_path,
                source,
                profile_path,
                target,
                target_type,
                spec,
            )
        runner_ms = 0
    else:
        runner = search_orchestration._candidate_runner(
            "STRATEGY_LAB_FINALIST_CANDIDATE_RUNNER"
        )
        if not runner.is_file() or not os.access(runner, os.X_OK):
            raise final_result.ResultError(
                f"Strategy Lab finalist candidate runner is unavailable: {runner}"
            )
        extra_env = {
            "STRATEGY_LAB_CANDIDATE_PROTOCOL": spec.protocol,
            "STRATEGY_LAB_CANDIDATE_PORT": str(spec.port),
            "STRATEGY_LAB_CANDIDATE_L7": spec.l7 or "-",
            "STRATEGY_LAB_PROFILE_REPLAY_EXACT": "1",
            "STRATEGY_LAB_PROFILE_REPLAY_SELECTOR": selector,
            PROBE_TIER_ENV: "deep",
        }
        if payload_path is not None and spec.protocol == "udp":
            extra_env["STRATEGY_LAB_UDP_PORT"] = str(spec.port)
            extra_env["STRATEGY_LAB_UDP_PAYLOAD_FILE"] = str(payload_path)
        command = [
            str(runner),
            job_id,
            str(endpoints_path),
            str(result_path),
            str(source.get("id", "")),
            str(source.get("family", "")),
            str(profile_path),
            "1" if target_type == "domain" and spec.protocol != "udp" else "0",
        ]
        status, timed_out, runner_ms = search_orchestration._run_candidate(
            command, timeout, job_id, extra_env=extra_env
        )
        if timed_out:
            status = EX_TIMEOUT

    profile = profile_path.read_text(encoding="utf-8")
    if not result_path.is_file():
        value = final_result._attempt_failure(
            source, profile, 1, status, "finalist deep replay produced no result"
        )
        if status == EX_TIMEOUT:
            value["timeout"] = True
        return value, runner_ms
    raw = final_result._read_json(result_path)
    if not isinstance(raw, dict):
        raise final_result.ResultError("Strategy Lab finalist replay result is invalid")
    raw["profile"] = profile
    raw["target"] = target
    raw["target_type"] = target_type
    raw["protocol"] = spec.protocol
    raw["port"] = spec.port
    raw["profile_exact"] = raw.get("strategy") == profile
    raw["attempt"] = 1
    raw["runner_status"] = status
    raw["runner_duration_ms"] = runner_ms
    return raw, runner_ms


def _source_key(source: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        int(source["protocol_rank"]),
        int(source["line_count"]),
        int(source["character_count"]),
        str(source.get("id", "")),
    )


def _finalists(sources: list[dict[str, Any]], mode: str, limit: int) -> list[dict[str, Any]]:
    if mode == "standard":
        return [item for item in sources if item["protocol"] == "tls13"][:limit]
    best: dict[str, dict[str, Any]] = {}
    for item in sources:
        best.setdefault(str(item["protocol"]), item)
    return sorted(best.values(), key=_source_key)[:limit]


def build_shortlist(job_id: str) -> dict[str, Any]:
    job = final_result.job_dir(job_id)
    stability_path = job / "stability.json"
    shortlist_path = job / "shortlist.json"
    status_path = job / "status.json"
    endpoints_path = job / "endpoints.txt"
    if (
        not stability_path.is_file()
        or not status_path.is_file()
        or not endpoints_path.is_file()
        or endpoints_path.stat().st_size <= 0
    ):
        raise final_result.ResultError("Strategy Lab final shortlist inputs are unavailable")
    stability = final_result._read_json(stability_path)
    status = final_result._read_json(status_path)
    if not isinstance(stability, dict) or not isinstance(status, dict):
        raise final_result.ResultError("Strategy Lab final shortlist inputs are invalid")
    target = status.get("target")
    target_type = status.get("target_type")
    mode = status.get("mode", "standard")
    if (
        not isinstance(target, str)
        or not isinstance(target_type, str)
        or mode not in {"standard", "extended"}
    ):
        raise final_result.ResultError("Strategy Lab job identity is invalid")
    final_result.selector_for(target, target_type, "tls13", "")
    endpoint_values = [
        line.strip()
        for line in endpoints_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    epoch = final_result.endpoint_epoch.load(job, endpoint_values)
    if epoch.target != target or epoch.target_type != target_type:
        raise final_result.ResultError(
            "Strategy Lab job target changed after the search epoch was created"
        )
    if stability.get("search_epoch_id") != epoch.epoch_id:
        raise final_result.ResultError(
            "Strategy Lab stability evidence belongs to another search epoch"
        )

    try:
        limit = int(os.environ.get("STRATEGY_LAB_SHORTLIST_LIMIT", "3"))
    except ValueError as exc:
        raise final_result.ResultError("invalid Strategy Lab shortlist limit") from exc
    if limit <= 0:
        raise final_result.ResultError("invalid Strategy Lab shortlist limit")
    target_bytes = _positive_int_env(
        FINALIST_TARGET_BYTES_ENV, FINALIST_TARGET_BYTES_DEFAULT
    )
    timeout = float(
        _positive_int_env(
            FINALIST_CANDIDATE_TIMEOUT_ENV, FINALIST_CANDIDATE_TIMEOUT_DEFAULT
        )
    )
    operation_deadline = search_orchestration._operation_deadline_monotonic()
    sources = final_result.collect_sources(job, stability, mode)
    finalists = _finalists(sources, mode, limit)

    work = job / "profile-replay"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    payload = job / "udp-payload.bin"
    payload_path = payload if payload.is_file() else None
    evaluated: list[dict[str, Any]] = []
    partial = False
    budget_admission: dict[str, Any] | None = None

    for index, source in enumerate(finalists, 1):
        admitted, remaining, required = search_orchestration._candidate_admission(
            timeout, operation_deadline
        )
        if not admitted:
            partial = True
            budget_admission = {
                "next_candidate": str(source.get("id", "")),
                "remaining_seconds": round(remaining or 0.0, 3),
                "required_seconds": round(required, 3),
            }
            telemetry.record(
                job,
                "candidate_admission",
                0,
                stage="85",
                candidate_id=str(source.get("id", "")),
                protocol=str(source.get("protocol", "")),
                outcome="deferred",
                details=budget_admission,
            )
            break
        protocol = str(source["protocol"])
        port = int(source["port"])
        if source.get("search_epoch_id") != epoch.epoch_id:
            raise final_result.ResultError(
                "Strategy Lab shortlist source belongs to another search epoch"
            )
        addresses = str(source.get("selector_addresses", ""))
        if protocol == "udp" and target_type == "domain":
            try:
                final_result._selector_addresses(addresses)
            except final_result.ResultError:
                continue
        strategy = source.get("strategy")
        if not isinstance(strategy, str):
            raise final_result.ResultError("Strategy Lab source strategy is invalid")
        profile = final_result.build_profile(
            target, target_type, protocol, port, addresses, strategy
        )
        profile_path = work / f"{index}.profile.args"
        final_result._atomic_text(profile_path, profile)
        replay, runner_ms = _deep_replay_once(
            job_id,
            endpoints_path,
            source,
            profile_path,
            target,
            target_type,
            payload_path,
            timeout,
        )
        deep = classify_deep_replay(replay, protocol, target_bytes)
        accepted = bool(deep["accepted"])
        published = dict(source)
        published.update(
            target=target,
            target_type=target_type,
            profile=profile,
            search_epoch_id=epoch.epoch_id,
            resolved_addresses=sorted(
                {
                    str(endpoint.get("selected_ip"))
                    for endpoint in (
                        replay.get("endpoints")
                        if isinstance(replay.get("endpoints"), list)
                        else []
                    )
                    if isinstance(endpoint, dict)
                    and isinstance(endpoint.get("selected_ip"), str)
                    and endpoint.get("selected_ip")
                }
            ),
            profile_replay={
                "attempt_count": 1,
                "pass_count": 1 if accepted else 0,
                "search_epoch_id": epoch.epoch_id,
                "endpoint_consistent": replay.get("search_epoch_id") == epoch.epoch_id,
                "verified": accepted and replay.get("search_epoch_id") == epoch.epoch_id,
                "policy": "single_deep_after_fail_fast_3_of_3",
                "results": [replay],
            },
            deep_validation=deep,
            circular_eligible=protocol == "tls13",
        )
        evaluated.append(published)
        telemetry.record(
            job,
            "finalist_validation",
            runner_ms,
            stage="85",
            candidate_id=str(source.get("id", "")),
            protocol=protocol,
            outcome=str(deep["classification"]),
            details=deep,
        )

    verified = [
        item for item in evaluated if item["profile_replay"]["verified"] is True
    ]
    verified.sort(key=_source_key)
    tls13 = [item for item in verified if item["protocol"] == "tls13"][:limit]
    if mode == "extended":
        best: dict[str, dict[str, Any]] = {}
        for item in verified:
            best.setdefault(str(item["protocol"]), item)
        selected = sorted(best.values(), key=_source_key)[:limit]
    else:
        selected = tls13

    # Circular remains a later validation path. Only deeply verified TLS 1.3 finalists
    # are eligible here; `_33` deliberately does not relax the circular contract.
    shortlist: dict[str, Any] = {
        "search_epoch_id": epoch.epoch_id,
        "count": len(selected),
        "items": selected,
        "recommendation": selected[0] if selected else None,
        "circular_count": len(tls13),
        "circular_items": tls13,
        "validation_policy": {
            "discovery": "bounded_4k_get",
            "stability": "fail_fast_3_of_3",
            "finalist": "single_cold_deep_get",
            "target_bytes": target_bytes,
        },
        "partial": partial,
        "stopped_reason": "insufficient_stage_budget" if partial else "completed",
    }
    if budget_admission is not None:
        shortlist["budget_admission"] = budget_admission
    final_result._atomic_json(shortlist_path, shortlist)
    if partial:
        raise TimeoutError("Strategy Lab finalist validation exceeded remaining stage budget")
    return shortlist


def run_result(argv: Sequence[str]) -> int:
    args = list(argv)
    if not args:
        raise final_result.ResultError("missing Strategy Lab result operation")
    operation, rest = args[0], args[1:]
    if operation == "shortlist" and len(rest) == 1:
        try:
            build_shortlist(rest[0])
        except TimeoutError:
            return EX_TIMEOUT
        return EX_OK
    if operation == "eligibility" and len(rest) == 3:
        final_result.circular_eligibility(rest[0], rest[1], rest[2])
        return EX_OK
    raise final_result.ResultError("invalid Strategy Lab result operation")
