"""Measurement-only comparison of current and faster warm-worker readiness confirmation.

The production readiness predicate is unchanged. This experiment uses the same isolated
worker/port and representative Model-C common-set startup surface for both policies, then
requires the worker to remain qualified at the legacy one-second horizon before any
candidate policy can be considered for a later production patch.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import blob_startup_measurement as blob
from . import resources, stage60_model_c

SCHEMA = 1
POLICY = "model-c-fast-warm-readiness-v1"
WORKER = blob.WORKER
DIVERT_PORT = blob.DIVERT_PORT
RUNTIME_VARIANT = "external-common-3"
BASELINE_INTERVAL_SECONDS = 1.0
CANDIDATE_INTERVAL_SECONDS = 0.05
READY_TIMEOUT_SECONDS = 3.2
LEGACY_CONFIRM_HORIZON_SECONDS = 1.10
DEFAULT_TRIALS = 8
MIN_TRIALS = 4
MAX_TRIALS = 20
VARIANTS = ("baseline-1000ms", "candidate-50ms")


class MeasurementError(RuntimeError):
    """Fast-readiness evidence is incomplete or invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _adapter_path() -> Path:
    default = Path(__file__).resolve().parent.parent / "strategy_lab_model_b_adapter.sh"
    return Path(os.environ.get("STRATEGY_LAB_FAST_READINESS_ADAPTER", str(default))).resolve(strict=False)


def _session_dir() -> Path:
    raw = os.environ.get("STRATEGY_LAB_MODEL_B_SESSION_DIR", "").strip()
    if not raw:
        raise MeasurementError("STRATEGY_LAB_MODEL_B_SESSION_DIR is required")
    path = Path(raw).resolve(strict=False)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _adapter(action: str, *args: object, expect_json: bool = False) -> Any:
    adapter = _adapter_path()
    if not adapter.is_file():
        raise MeasurementError(f"measurement adapter is unavailable: {adapter}")
    result = subprocess.run(
        ["/bin/sh", str(adapter), action, *(str(value) for value in args)],
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise MeasurementError(f"adapter {action} failed ({result.returncode}): {detail}")
    if not expect_json:
        return result.stdout
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MeasurementError(f"adapter {action} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise MeasurementError(f"adapter {action} returned non-object JSON")
    return value


def _worker_dir(session: Path) -> Path:
    path = session / "workers" / WORKER
    path.mkdir(parents=True, exist_ok=True)
    return path


def _qualified(snapshot: dict[str, Any]) -> bool:
    rss = snapshot.get("rss_kb")
    return (
        snapshot.get("process_identity") is True
        and snapshot.get("socket_ready") is True
        and snapshot.get("log_clean") is True
        and isinstance(rss, int)
        and not isinstance(rss, bool)
        and rss > 0
    )


def _snapshot() -> dict[str, Any]:
    return _adapter("snapshot", WORKER, DIVERT_PORT, expect_json=True)


def _wait_ready(interval: float) -> tuple[float, float, dict[str, Any]]:
    started = time.monotonic()
    first_ms: float | None = None
    consecutive = 0
    latest: dict[str, Any] | None = None
    while time.monotonic() - started < READY_TIMEOUT_SECONDS:
        latest = _snapshot()
        if _qualified(latest):
            elapsed_ms = (time.monotonic() - started) * 1000.0
            if first_ms is None:
                first_ms = elapsed_ms
            consecutive += 1
            if consecutive >= 2:
                return first_ms, elapsed_ms, latest
        else:
            consecutive = 0
            first_ms = None
        time.sleep(interval)
    raise MeasurementError(f"worker did not become stably ready: {latest}")


def _write_runtime(session: Path, arguments: Sequence[str]) -> None:
    args_path = _worker_dir(session) / "dvtws.args"
    args_path.write_text("".join(f"{item}\n" for item in arguments), encoding="utf-8")
    os.chmod(args_path, 0o644)


def _sample(session: Path, arguments: Sequence[str], variant: str, trial: int) -> dict[str, Any]:
    interval = BASELINE_INTERVAL_SECONDS if variant == "baseline-1000ms" else CANDIDATE_INTERVAL_SECONDS
    _write_runtime(session, arguments)
    launch_started = time.monotonic()
    _adapter("launch", WORKER, DIVERT_PORT)
    try:
        first_ms, stable_ms, ready = _wait_ready(interval)
        remaining = LEGACY_CONFIRM_HORIZON_SECONDS - (time.monotonic() - launch_started)
        if remaining > 0:
            time.sleep(remaining)
        confirmed = _snapshot()
        if not _qualified(confirmed):
            raise MeasurementError(f"worker lost readiness by legacy confirmation horizon: {confirmed}")
        ready_pid = ready.get("pid")
        confirmed_pid = confirmed.get("pid")
        same_pid = not (
            isinstance(ready_pid, int)
            and isinstance(confirmed_pid, int)
            and ready_pid != confirmed_pid
        )
        if not same_pid:
            raise MeasurementError("worker identity changed before legacy confirmation horizon")
        return {
            "trial": trial,
            "variant": variant,
            "interval_ms": round(interval * 1000.0, 3),
            "first_qualified_ms": round(first_ms, 3),
            "stable_ready_ms": round(stable_ms, 3),
            "legacy_confirmation_ms": round((time.monotonic() - launch_started) * 1000.0, 3),
            "ready_rss_kb": ready.get("rss_kb"),
            "confirmed_rss_kb": confirmed.get("rss_kb"),
            "same_pid_at_legacy_horizon": same_pid,
            "confirmed_qualified": True,
        }
    finally:
        _adapter("stop", WORKER, DIVERT_PORT)


def _p90(values: Sequence[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.90) - 1)]


def _metric(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise MeasurementError("cannot summarize empty metric")
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "mean": round(float(statistics.mean(values)), 3),
        "median": round(float(statistics.median(values)), 3),
        "stdev": round(float(statistics.stdev(values)), 3) if len(values) > 1 else 0.0,
        "p90": round(_p90(values), 3),
        "max": round(max(values), 3),
    }


def _summaries(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for variant in VARIANTS:
        selected = [item for item in samples if item["variant"] == variant]
        result[variant] = {
            "sample_count": len(selected),
            "stable_ready_ms": _metric([float(item["stable_ready_ms"]) for item in selected]),
            "ready_rss_kb": _metric([float(item["ready_rss_kb"]) for item in selected]),
            "confirmed_rss_kb": _metric([float(item["confirmed_rss_kb"]) for item in selected]),
        }
    return result


def _comparison(summaries: dict[str, Any]) -> dict[str, Any]:
    baseline = summaries["baseline-1000ms"]["stable_ready_ms"]
    candidate = summaries["candidate-50ms"]["stable_ready_ms"]
    delta = float(candidate["median"]) - float(baseline["median"])
    percent = None if float(baseline["median"]) == 0 else delta * 100.0 / float(baseline["median"])
    return {
        "candidate_minus_baseline_median_ms": round(delta, 3),
        "candidate_minus_baseline_median_pct": None if percent is None else round(percent, 3),
        "median_savings_ms": round(-delta, 3),
        "candidate_p90_ms": candidate["p90"],
        "baseline_median_ms": baseline["median"],
    }


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MeasurementError(f"JSON evidence is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise MeasurementError(f"JSON evidence is not an object: {path}")
    return value


def _lifecycle_equal(initial: dict[str, Any], final: dict[str, Any]) -> bool:
    keys = ("state", "child_running", "supervisor_running", "runtime_args_hash", "effective_config_hash", "normal_firewall_hash")
    return initial.get("schema") == 1 and final.get("schema") == 1 and all(initial.get(key) == final.get(key) for key in keys)


def run_measurement(output: Path, trials: int) -> dict[str, Any]:
    if trials < MIN_TRIALS or trials > MAX_TRIALS or trials % 2 != 0:
        raise MeasurementError(f"trials must be an even number between {MIN_TRIALS} and {MAX_TRIALS}")
    session = _session_dir()
    inventory = resources.snapshot_inventory(resources.configured_lua_root(), resources.configured_fake_root())
    selector = blob._selector_path()
    arguments = blob._arguments_for(inventory, selector, RUNTIME_VARIANT)
    _adapter("cleanup-all")
    _adapter("preflight")
    samples: list[dict[str, Any]] = []
    try:
        for trial in range(1, trials + 1):
            order = VARIANTS if trial % 2 else tuple(reversed(VARIANTS))
            for variant in order:
                samples.append(_sample(session, arguments, variant, trial))
    finally:
        _adapter("cleanup-all")
    _adapter("preflight")
    summaries = _summaries(samples)
    comparison = _comparison(summaries)
    safety_ok = all(item["confirmed_qualified"] and item["same_pid_at_legacy_horizon"] for item in samples)
    materially_faster = comparison["median_savings_ms"] >= 500.0
    report = {
        "schema": SCHEMA,
        "policy": POLICY,
        "generated_at": _utc_now(),
        "experiment_only": True,
        "production_model": stage60_model_c.MODEL,
        "production_readiness_changed": False,
        "runtime_variant": RUNTIME_VARIANT,
        "worker": WORKER,
        "divert_port": DIVERT_PORT,
        "baseline_interval_ms": BASELINE_INTERVAL_SECONDS * 1000.0,
        "candidate_interval_ms": CANDIDATE_INTERVAL_SECONDS * 1000.0,
        "legacy_confirmation_horizon_ms": LEGACY_CONFIRM_HORIZON_SECONDS * 1000.0,
        "trials_per_policy": trials,
        "sample_count": len(samples),
        "samples": samples,
        "summaries": summaries,
        "comparison": comparison,
        "checks": {
            "adapter_preflight": True,
            "expected_sample_count": len(samples) == trials * len(VARIANTS),
            "balanced_trial_count": trials % 2 == 0,
            "single_worker_identity": all(item.get("same_pid_at_legacy_horizon") is True for item in samples),
            "all_samples_confirmed_at_legacy_horizon": safety_ok,
            "material_readiness_savings_observed": materially_faster,
            "temporary_workers_clean": True,
            "lifecycle_restored": False,
            "cleanup_ok": False,
        },
        "candidate_supported": safety_ok and materially_faster,
        "production_change_recommended": False,
        "conclusion": "pending_restoration",
        "next_step": "finalize_lifecycle_evidence",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def finalize(output: Path, initial_path: Path, final_path: Path, cleanup_ok: bool) -> dict[str, Any]:
    report = _read_object(output)
    if report.get("schema") != SCHEMA or report.get("policy") != POLICY:
        raise MeasurementError("measurement report identity is invalid")
    initial = _read_object(initial_path)
    final = _read_object(final_path)
    checks = report.setdefault("checks", {})
    checks["lifecycle_restored"] = _lifecycle_equal(initial, final)
    checks["cleanup_ok"] = bool(cleanup_ok)
    report["lifecycle"] = {"initial": initial, "final": final}
    required = (
        "adapter_preflight",
        "expected_sample_count",
        "balanced_trial_count",
        "single_worker_identity",
        "all_samples_confirmed_at_legacy_horizon",
        "temporary_workers_clean",
        "lifecycle_restored",
        "cleanup_ok",
    )
    accepted = all(checks.get(name) is True for name in required)
    report["conclusion"] = "measurement_accepted" if accepted else "measurement_invalid"
    report["production_change_recommended"] = False
    report["next_step"] = (
        "consider_separate_production_readiness_interval_patch_with_owner_live_stage60_verification"
        if accepted and report.get("candidate_supported") is True
        else "do_not_change_production_readiness_policy"
    )
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure faster Model-C warm readiness confirmation without changing production")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("output")
    run_parser.add_argument("trials", nargs="?", type=int, default=DEFAULT_TRIALS)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("output")
    finalize_parser.add_argument("initial")
    finalize_parser.add_argument("final")
    finalize_parser.add_argument("cleanup_ok", choices=("true", "false"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.action == "run":
        _emit(run_measurement(Path(args.output), args.trials))
        return 0
    if args.action == "finalize":
        _emit(finalize(Path(args.output), Path(args.initial), Path(args.final), args.cleanup_ok == "true"))
        return 0
    raise AssertionError(args.action)


if __name__ == "__main__":
    raise SystemExit(main())
