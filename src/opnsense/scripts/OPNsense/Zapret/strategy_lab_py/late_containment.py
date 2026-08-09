"""Telemetry-derived late-stage containment for Strategy Lab.

This module keeps the `_32` timeout work narrow: Stage 60 remains owned by the
existing search implementation, while Stage 70/80 gain candidate admission and
Stage 85/restoration gain explicit parent bounds. `_33` still owns discovery,
fail-fast stability, and finalist deep-validation semantics.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from . import extended as extended_orchestration
from . import orchestrator as base_orchestrator
from . import search as search_orchestration
from . import state as state_persistence
from . import telemetry

EX_OK = 0
EX_USAGE = 64
EX_TIMEOUT = 124
EX_CANCEL = 125

STAGE85_TIMEOUT_ENV = "STRATEGY_LAB_STAGE85_TIMEOUT"
STAGE85_TIMEOUT_DEFAULT = 120
RESTORE_PARENT_TIMEOUT_ENV = "STRATEGY_LAB_RESTORE_PARENT_TIMEOUT"
RESTORE_PARENT_TIMEOUT_DEFAULT = 180


class LateStageBudgetExhausted(RuntimeError):
    def __init__(
        self,
        *,
        stage: str,
        candidate_id: str,
        protocol: str,
        remaining: float | None,
        required: float,
        attempt: int | None = None,
    ) -> None:
        super().__init__(candidate_id)
        self.stage = stage
        self.candidate_id = candidate_id
        self.protocol = protocol
        self.remaining = remaining
        self.required = required
        self.attempt = attempt

    def evidence(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "next_candidate": self.candidate_id,
            "remaining_seconds": round(self.remaining or 0.0, 3),
            "required_seconds": round(self.required, 3),
        }
        if self.attempt is not None:
            value["next_attempt"] = self.attempt
        return value


def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise base_orchestrator.UsageError(f"invalid Strategy Lab setting: {name}") from exc
    if value <= 0:
        raise base_orchestrator.UsageError(f"invalid Strategy Lab setting: {name}")
    return value


def _defer_candidate(
    *,
    stage: str,
    candidate_id: str,
    protocol: str,
    timeout: float,
    deadline: float | None,
    attempt: int | None = None,
) -> LateStageBudgetExhausted | None:
    admitted, remaining, required = search_orchestration._candidate_admission(timeout, deadline)
    if admitted:
        return None
    return LateStageBudgetExhausted(
        stage=stage,
        candidate_id=candidate_id,
        protocol=protocol,
        remaining=remaining,
        required=required,
        attempt=attempt,
    )


def _record_deferred(job_id: str, exc: LateStageBudgetExhausted) -> None:
    telemetry.record(
        search_orchestration.job_dir(job_id),
        "candidate_admission",
        0,
        stage=exc.stage,
        candidate_id=exc.candidate_id,
        protocol=exc.protocol,
        outcome="deferred",
        details=exc.evidence(),
    )


class ContainedOrchestrator(base_orchestrator.Orchestrator):
    """Base orchestrator with explicit Stage-85 and restoration parent bounds."""

    def _run_regular_stage(self, stage: str) -> str | None:
        self._begin(stage)
        timeout = None
        if stage == "85":
            timeout = self.budget.timeout_for(
                stage,
                _positive_int_env(STAGE85_TIMEOUT_ENV, STAGE85_TIMEOUT_DEFAULT),
            )
        elif stage in base_orchestrator.STAGE_LIMIT_ENV:
            timeout = self.budget.timeout_for(stage, self._operation_limit(stage))
        result = self._run_adapter(
            stage,
            operation_timeout=timeout,
            cancel_interruptible=stage not in {"00", "10", "20"},
        )
        return self._handle_result(stage, result)

    def _restore(self, outcome: str) -> str:
        self.current_stage = "90"
        state_persistence.update_stage(
            self.job_id, str(self.state_path), "90", "RUNNING", ""
        )
        state_persistence.append_event(
            self.job_id,
            str(self.state_path),
            str(self.events_path),
            "90",
            "RUNNING",
            base_orchestrator.RUNNING_EVENTS["90"],
        )
        try:
            result = self._run_adapter(
                "restore",
                operation_timeout=_positive_int_env(
                    RESTORE_PARENT_TIMEOUT_ENV, RESTORE_PARENT_TIMEOUT_DEFAULT
                ),
                cancel_interruptible=False,
            )
        except Exception:
            result = base_orchestrator.AdapterResult("error", "")
        if result.kind == "pass":
            key = {
                "RUNNING": "restore_running",
                "STOPPED": "restore_stopped",
            }.get(result.initial_state, "restore_noop")
            message = base_orchestrator._message(self.language, key)
            self._update_stage("90", "PASS", message)
            return outcome
        message = base_orchestrator._message(self.language, "restore_failed")
        self._update_stage("90", "FAIL", message)
        return "RESTORE_FAILED"


def orchestrator_main(argv: Sequence[str]) -> int:
    args = list(argv)
    if len(args) != 1:
        raise base_orchestrator.UsageError("orchestrate requires exactly one Strategy Lab job id")
    job_id = args[0]
    if not state_persistence.JOB_ID_RE.fullmatch(job_id):
        raise base_orchestrator.UsageError("invalid Strategy Lab job id")
    return ContainedOrchestrator(job_id).run()


def _stability_partial(
    *,
    job_id: str,
    output: Path,
    result: dict[str, Any],
    exc: LateStageBudgetExhausted,
    attempt_results: list[dict[str, Any]],
) -> int:
    result["partial"] = True
    result["stopped_reason"] = "insufficient_stage_budget"
    result["budget_admission"] = exc.evidence()
    if attempt_results:
        result["partial_candidate"] = {
            "id": exc.candidate_id,
            "completed_attempts": len(attempt_results),
            "attempts": attempt_results,
        }
    search_orchestration._persist_partial_result(
        job_id, "stability", output, result
    )
    _record_deferred(job_id, exc)
    return EX_TIMEOUT


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
        attempt_results: list[dict[str, Any]] = []

        first_admission = _defer_candidate(
            stage="70",
            candidate_id=candidate_id,
            protocol="tls13",
            timeout=timeout,
            deadline=operation_deadline,
            attempt=1,
        )
        if first_admission is not None:
            return _stability_partial(
                job_id=job_id,
                output=output,
                result=result,
                exc=first_admission,
                attempt_results=attempt_results,
            )

        strategy_path = work / f"{index}.args"
        strategy_path.write_text(description.strategy, encoding="utf-8")
        os.chmod(strategy_path, 0o644)
        spec_path = work / f"{index}.spec.json"
        search_orchestration._atomic_json(spec_path, description.to_dict())
        attempt_dir = work / f"{index}-attempts"
        attempt_dir.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, attempts + 1):
            if search_orchestration._cancel_requested(job_id):
                return EX_CANCEL
            if attempt > 1:
                deferred = _defer_candidate(
                    stage="70",
                    candidate_id=candidate_id,
                    protocol="tls13",
                    timeout=timeout,
                    deadline=operation_deadline,
                    attempt=attempt,
                )
                if deferred is not None:
                    return _stability_partial(
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
                extra_env={"STRATEGY_LAB_ENDPOINT_PROBE_MODE": "sequential"},
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
            telemetry.record(
                search_orchestration.job_dir(job_id),
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

        stable = len(attempt_results) == attempts and all(
            item.get("all_pass") is True for item in attempt_results
        )
        candidate_result: dict[str, Any] = {
            "id": candidate_id,
            "family": family,
            "strategy": description.strategy,
            "candidate_spec": description.to_dict(),
            "search_epoch_id": epoch.epoch_id,
            "search_epoch_generation": epoch.generation,
            "endpoint_bindings": list(epoch.bindings),
            "attempts": attempt_results,
            "stable": stable,
            "pass_count": len(
                [item for item in attempt_results if item.get("all_pass") is True]
            ),
            "line_count": len(description.strategy_lines),
            "character_count": len(description.strategy),
        }
        for key in ("resource_inventory_id", "graph_node"):
            if key in source:
                candidate_result[key] = source[key]
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
    return search_orchestration.main(args)


def _persist_extended_partial(
    *,
    job_id: str,
    field: str,
    output: Path,
    exc: LateStageBudgetExhausted,
) -> int:
    if output.is_file():
        value = search_orchestration._load_json(output)
    else:
        value = {}
    value["partial"] = True
    value["stopped_reason"] = "insufficient_stage_budget"
    value["budget_admission"] = exc.evidence()
    search_orchestration._persist_partial_result(job_id, field, output, value)
    _record_deferred(job_id, exc)
    return EX_TIMEOUT


def run_extended(argv: Sequence[str]) -> int:
    args = list(argv)
    if not args:
        return extended_orchestration.main(args)
    operation = args[0]
    if operation not in {"tcp", "quic", "udp"}:
        return extended_orchestration.main(args)
    expected = {"tcp": 4, "quic": 5, "udp": 4}[operation]
    if len(args) != expected:
        return extended_orchestration.main(args)

    job_id = args[1]
    output = Path(args[-1])
    field = {"tcp": "extended", "quic": "quic", "udp": "udp"}[operation]
    deadline = search_orchestration._operation_deadline_monotonic()
    original_candidate = extended_orchestration._candidate

    def admitted_candidate(
        candidate_job_id: str,
        endpoints: Path,
        candidate_path: Path,
        candidate_id: str,
        family: str,
        strategy_path: Path,
        use_hostlist: str,
        *,
        runner: Path,
        timeout: float,
        protocol: str,
        port: str,
        l7: str,
        extra_env: dict[str, str] | None = None,
    ) -> dict[str, Any] | int:
        deferred = _defer_candidate(
            stage="80",
            candidate_id=candidate_id,
            protocol=protocol,
            timeout=timeout,
            deadline=deadline,
        )
        if deferred is not None:
            raise deferred
        return original_candidate(
            candidate_job_id,
            endpoints,
            candidate_path,
            candidate_id,
            family,
            strategy_path,
            use_hostlist,
            runner=runner,
            timeout=timeout,
            protocol=protocol,
            port=port,
            l7=l7,
            extra_env=extra_env,
        )

    extended_orchestration._candidate = admitted_candidate
    try:
        return extended_orchestration.main(args)
    except LateStageBudgetExhausted as exc:
        return _persist_extended_partial(
            job_id=job_id,
            field=field,
            output=output,
            exc=exc,
        )
    finally:
        extended_orchestration._candidate = original_candidate
