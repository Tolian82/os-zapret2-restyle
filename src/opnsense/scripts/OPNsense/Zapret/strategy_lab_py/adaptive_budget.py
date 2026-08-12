"""Workload-derived finite parent budgets for Strategy Lab.

The calibrated IPv4/two-endpoint budgets remain the floor. After Stage 30 has measured
network capabilities, this owner extends only the parent envelopes needed by additional
eligible work. It never changes candidate/search semantics or restarts the job clock.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import late_containment
from . import orchestrator as base_orchestrator
from . import state as state_persistence
from . import telemetry

POLICY = "eligible-work-v1"
REFERENCE_ENDPOINTS = 2
EXTRA_ENDPOINT_STANDARD_SECONDS = 30
EXTRA_ENDPOINT_EXTENDED_SECONDS = 15
IPV6_BASELINE_SECONDS_PER_ENDPOINT = 5
OPTIONAL_CANDIDATE_TIMEOUT_SECONDS = 5
QUIC_CANDIDATE_COUNT = 4
UDP_CANDIDATE_COUNT = 3
PLAN_FILE = "adaptive-budget.json"


def _load_status(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise base_orchestrator.OrchestrationError(
            f"Strategy Lab adaptive-budget state is unreadable: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise base_orchestrator.OrchestrationError(
            "Strategy Lab adaptive-budget state root is invalid"
        )
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
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


def _base_seconds(budget: base_orchestrator.Budget) -> dict[str, int]:
    cached = getattr(budget, "_adaptive_budget_base", None)
    if isinstance(cached, dict):
        return dict(cached)
    value = {
        "standard": int(budget.standard_budget),
        "extended": int(budget.extended_budget),
        "stage80": int(budget.stage80_limit),
    }
    setattr(budget, "_adaptive_budget_base", dict(value))
    return value


def _work_matrix(status: dict[str, Any], mode: str) -> dict[str, Any]:
    endpoints = status.get("endpoints")
    network = status.get("network")
    if not isinstance(endpoints, list) or not all(
        isinstance(item, str) and item for item in endpoints
    ):
        raise base_orchestrator.OrchestrationError(
            "Strategy Lab adaptive budget requires resolved endpoints"
        )
    if not endpoints:
        raise base_orchestrator.OrchestrationError(
            "Strategy Lab adaptive budget requires at least one endpoint"
        )
    if not isinstance(network, dict) or network.get("ipv4") != "available":
        raise base_orchestrator.OrchestrationError(
            "Strategy Lab adaptive budget requires the completed IPv4 network precheck"
        )
    udp = status.get("udp_request")
    udp_configured = (
        mode == "extended"
        and isinstance(udp, dict)
        and udp.get("configured") is True
    )
    return {
        "mode": mode,
        "endpoint_count": len(endpoints),
        "ipv4": True,
        "ipv6": network.get("ipv6") == "available",
        "tls13": True,
        "extended_tcp": mode == "extended",
        "quic_ipv4": mode == "extended" and network.get("quic_ipv4") == "available",
        "generic_udp": udp_configured,
    }


def calculate_plan(
    budget: base_orchestrator.Budget,
    status: dict[str, Any],
) -> dict[str, Any]:
    """Return one deterministic finite plan from the measured eligible work matrix."""
    base = _base_seconds(budget)
    matrix = _work_matrix(status, budget.mode)
    endpoint_count = int(matrix["endpoint_count"])
    extra_endpoints = max(0, endpoint_count - REFERENCE_ENDPOINTS)

    endpoint_standard = extra_endpoints * EXTRA_ENDPOINT_STANDARD_SECONDS
    endpoint_extended = (
        extra_endpoints * EXTRA_ENDPOINT_EXTENDED_SECONDS
        if budget.mode == "extended"
        else 0
    )
    ipv6 = (
        endpoint_count * IPV6_BASELINE_SECONDS_PER_ENDPOINT
        if matrix["ipv6"]
        else 0
    )
    quic = (
        QUIC_CANDIDATE_COUNT * OPTIONAL_CANDIDATE_TIMEOUT_SECONDS
        if matrix["quic_ipv4"]
        else 0
    )
    generic_udp = (
        UDP_CANDIDATE_COUNT * OPTIONAL_CANDIDATE_TIMEOUT_SECONDS
        if matrix["generic_udp"]
        else 0
    )

    standard_add = endpoint_standard + ipv6
    extended_add = endpoint_extended + quic + generic_udp
    standard = base["standard"] + standard_add
    extended = base["extended"] + extended_add
    search = standard + extended if budget.mode == "extended" else standard
    stage80 = base["stage80"] + extended_add

    return {
        "schema": 1,
        "policy": POLICY,
        "reference_endpoints": REFERENCE_ENDPOINTS,
        "work_matrix": matrix,
        "weights_seconds": {
            "extra_endpoint_standard": EXTRA_ENDPOINT_STANDARD_SECONDS,
            "extra_endpoint_extended": EXTRA_ENDPOINT_EXTENDED_SECONDS,
            "ipv6_baseline_per_endpoint": IPV6_BASELINE_SECONDS_PER_ENDPOINT,
            "optional_candidate_timeout": OPTIONAL_CANDIDATE_TIMEOUT_SECONDS,
            "quic_candidate_count": QUIC_CANDIDATE_COUNT,
            "udp_candidate_count": UDP_CANDIDATE_COUNT,
        },
        "additions_seconds": {
            "extra_endpoints_standard": endpoint_standard,
            "extra_endpoints_extended": endpoint_extended,
            "ipv6": ipv6,
            "quic": quic,
            "generic_udp": generic_udp,
            "standard_total": standard_add,
            "extended_total": extended_add,
        },
        "base_seconds": base,
        "effective_seconds": {
            "standard": standard,
            "extended": extended,
            "search": search,
            "stage80": stage80,
        },
    }


def adapt(
    budget: base_orchestrator.Budget,
    *,
    job_dir: Path,
    state_path: Path,
) -> dict[str, Any]:
    """Apply the Stage-30 plan without moving the original job start epoch."""
    status = _load_status(state_path)
    plan = calculate_plan(budget, status)
    effective = plan["effective_seconds"]

    budget.standard_budget = int(effective["standard"])
    budget.extended_budget = int(effective["extended"])
    budget.search_budget = int(effective["search"])
    budget.stage80_limit = int(effective["stage80"])
    budget.standard_deadline = budget.started_epoch + budget.standard_budget
    budget.overall_deadline = budget.started_epoch + budget.search_budget
    budget.stage80_started = None
    budget.stage80_deadline = None
    budget.record_initial()

    _atomic_json(job_dir / PLAN_FILE, plan)
    telemetry.record(
        job_dir,
        "budget_adaptation",
        0,
        stage="30",
        outcome="pass",
        details=plan,
    )
    return plan


class AdaptiveBudgetOrchestrator(late_containment.ContainedOrchestrator):
    """Contained production orchestrator with Stage-30 workload-derived deadlines."""

    def _run_regular_stage(self, stage: str) -> str | None:
        outcome = super()._run_regular_stage(stage)
        if stage == "30" and outcome is None:
            adapt(self.budget, job_dir=self.job_dir, state_path=self.state_path)
        return outcome


def orchestrator_main(argv: Sequence[str]) -> int:
    args = list(argv)
    if len(args) != 1:
        raise base_orchestrator.UsageError(
            "orchestrate requires exactly one Strategy Lab job id"
        )
    job_id = args[0]
    if not state_persistence.JOB_ID_RE.fullmatch(job_id):
        raise base_orchestrator.UsageError("invalid Strategy Lab job id")
    return AdaptiveBudgetOrchestrator(job_id).run()
