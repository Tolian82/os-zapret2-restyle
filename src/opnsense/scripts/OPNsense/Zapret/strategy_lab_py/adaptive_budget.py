"""Workload-derived finite parent budgets for Strategy Lab.

The calibrated IPv4/two-endpoint budgets remain the floor. After Stage 30 has measured
network capabilities, this owner extends only the parent envelopes needed by additional
eligible work. It never changes candidate/search semantics or restarts the job clock.
"""

from __future__ import annotations

import ipaddress
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

POLICY = "eligible-families-v2"
# Owner's fixed overall job budgets. The additional family budget is paid
# only when Stage 40 actually observed an A + AAAA target under opt-in.
DUAL_STANDARD_EXTRA = 50
DUAL_EXTENDED_EXTRA = 30
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


def _ipv6_literal(value: Any) -> bool:
    try:
        return ipaddress.ip_address(value).version == 6
    except (TypeError, ValueError):
        return False


def _work_matrix(status: dict[str, Any], mode: str) -> dict[str, Any]:
    """Use Stage-40 target family evidence, never route availability alone."""
    endpoints = status.get("endpoints")
    network = status.get("network")
    baseline = status.get("baseline")
    if not isinstance(endpoints, list) or not endpoints or not all(
        isinstance(item, str) and item for item in endpoints
    ):
        raise base_orchestrator.OrchestrationError(
            "Strategy Lab budget requires resolved endpoints"
        )
    if not isinstance(network, dict) or not (
        network.get("ipv4") == "available"
        or (status.get("ipv6_enabled") is True and network.get("ipv6") == "available")
    ):
        raise base_orchestrator.OrchestrationError(
            "Strategy Lab budget requires an available selected network family"
        )
    # Some existing adapters publish a valid Stage-40 PASS without recording
    # per-family evidence. That can NEVER justify extra IPv6 time, but must not
    # turn an otherwise valid IPv4 job into an internal ERROR.
    has_baseline = isinstance(baseline, dict) and isinstance(baseline.get("endpoints"), list)
    ipv6_requested = status.get("ipv6_enabled") is True
    ipv4_target = status.get("target_type") == "ip" and not _ipv6_literal(status.get("target"))
    domain = status.get("target_type") == "domain"
    family_endpoints = baseline["endpoints"] if has_baseline else []
    def has_family(family: str) -> bool:
        return any(
            isinstance(item, dict)
            and isinstance(item.get(family), dict)
            and item[family].get("status") in {"PASS", "FAIL"}
            for item in family_endpoints
        )

    ipv4_eligible = ipv4_target or (domain and has_family("ipv4"))
    ipv6_eligible = (
        (domain and has_baseline or (status.get("target_type") == "ip" and _ipv6_literal(status.get("target"))))
        and ipv6_requested
        and network.get("ipv6") == "available" and has_family("ipv6")
    )
    # No bonus for IPv6 merely present on the network, checked-only, or
    # a single IPv4 literal. An AAAA-less domain must remain single-family.
    dual_family = bool(ipv4_eligible and ipv6_eligible)
    udp = status.get("udp_request")
    return {
        "mode": mode,
        "endpoint_count": len(endpoints),
        "ipv4": bool(ipv4_eligible),
        "ipv6": bool(ipv6_eligible),
        "dual_family": dual_family,
        "ipv6_requested": ipv6_requested,
        "family_evidence_available": bool(has_baseline),
        "quic_ipv4": mode == "extended" and network.get("quic_ipv4") == "available",
        "generic_udp": (
            mode == "extended" and isinstance(udp, dict)
            and udp.get("configured") is True
        ),
    }


def calculate_plan(
    budget: base_orchestrator.Budget,
    status: dict[str, Any],
) -> dict[str, Any]:
    """One bounded job-wide deadline, never additive protocol/endpoint bonuses."""
    base = _base_seconds(budget)
    matrix = _work_matrix(status, budget.mode)
    dual = matrix["dual_family"]
    # Keep the lower custom budgets used by bounded tests; release defaults
    # remain exactly 150/270 and 200/350 with the existing 150/120 pair.
    standard = min(base["standard"], 150) + (DUAL_STANDARD_EXTRA if dual else 0)
    extended = min(base["extended"], 120) + (
        DUAL_EXTENDED_EXTRA if dual and budget.mode == "extended" else 0
    )
    search = standard + extended if budget.mode == "extended" else standard
    stage80 = min(base["stage80"] + (
        DUAL_EXTENDED_EXTRA if dual and budget.mode == "extended" else 0
    ), extended)
    return {
        "schema": 2,
        "policy": POLICY,
        "work_matrix": matrix,
        "weights_seconds": {
            "dual_family_standard": DUAL_STANDARD_EXTRA,
            "dual_family_extended": DUAL_EXTENDED_EXTRA,
        },
        "additions_seconds": {
            "standard_total": DUAL_STANDARD_EXTRA if dual else 0,
            "extended_total": (
                DUAL_EXTENDED_EXTRA if dual and budget.mode == "extended" else 0
            ),
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
    """Apply the Stage-40 family-qualified plan without restarting the job clock."""
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
        stage="40",
        outcome="pass",
        details=plan,
    )
    return plan


class AdaptiveBudgetOrchestrator(late_containment.ContainedOrchestrator):
    """Contained production orchestrator with Stage-40 family-qualified budgets."""

    def _run_regular_stage(self, stage: str) -> str | None:
        outcome = super()._run_regular_stage(stage)
        if stage == "40" and outcome is None:
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
