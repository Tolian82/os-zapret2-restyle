"""Measurement-only BLOB loading/startup/RSS experiment for Strategy Lab Model C.

The experiment never installs IPFW routes and never stops or reconfigures the normal Zapret2
service.  It reuses the isolated Model-B adapter only to launch one temporary dvtws2 worker at
a time on dedicated divert ports, holding Lua/action structure constant while comparing
BLOB-free, built-in fake and external-file BLOB resource variants.
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

from . import resources, stage60_model_c

SCHEMA = 1
POLICY = "blob-startup-rss-v1"
CACHE_POLICY = "natural-cache-no-drop"
SELECTOR_LUA = "strategy_lab_model_c.lua"
COMMON_LUA = ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua")
VARIANTS = (
    ("blob-free", "pass", 9990),
    ("builtin", "builtin", 9991),
    ("external", "external", 9992),
)
DEFAULT_TRIALS = 9
MIN_TRIALS = 3
MAX_TRIALS = 15
READY_TIMEOUT_SECONDS = 4.0
POLL_SECONDS = 0.025
SETTLE_SECONDS = 0.2


class MeasurementError(RuntimeError):
    """The isolated measurement could not produce trustworthy evidence."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _adapter_path() -> Path:
    default = Path(__file__).resolve().parent.parent / "strategy_lab_model_b_adapter.sh"
    return Path(os.environ.get("STRATEGY_LAB_BLOB_MEASUREMENT_ADAPTER", str(default))).resolve(strict=False)


def _selector_path() -> Path:
    default = Path(__file__).resolve().parent.parent / SELECTOR_LUA
    return Path(os.environ.get(stage60_model_c.SELECTOR_ENV, str(default))).resolve(strict=False)


def _session_dir() -> Path:
    value = os.environ.get("STRATEGY_LAB_MODEL_B_SESSION_DIR", "").strip()
    if not value:
        raise MeasurementError("STRATEGY_LAB_MODEL_B_SESSION_DIR is required")
    path = Path(value).resolve(strict=False)
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


def _worker_dir(session: Path, worker: str) -> Path:
    path = session / "workers" / worker
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_args(
    session: Path,
    inventory: resources.ResourceInventory,
    selector: Path,
    variant: str,
    worker: str,
    port: int,
) -> list[str]:
    lua_paths = [inventory.lua_path(name) for name in COMMON_LUA]
    if not selector.is_file() or selector.stat().st_size <= 0:
        raise MeasurementError(f"Model C selector Lua is unavailable: {selector}")

    arguments = [f"--port={port}"]
    arguments.extend(f"--lua-init=@{path}" for path in lua_paths)
    arguments.append(f"--lua-init=@{selector}")
    arguments.extend(
        (
            "--filter-tcp=443",
            "--filter-l7=tls",
            "--in-range=x",
            "--out-range=-d8",
            "--payload=tls_client_hello",
        )
    )
    action = "--lua-desync=multisplit:pos=2,midsld-2:seqovl=1"
    if variant == "builtin":
        action += ":seqovl_pattern=fake_default_tls"
    elif variant == "external":
        external = inventory.external_blob_path("fake_tls_7")
        arguments.append(f"--blob=fake_tls_7:@{external}")
        action += ":seqovl_pattern=fake_tls_7"
    elif variant != "blob-free":
        raise MeasurementError(f"unknown BLOB variant: {variant}")
    arguments.append(action)

    path = _worker_dir(session, worker) / "dvtws.args"
    path.write_text("".join(f"{value}\n" for value in arguments), encoding="utf-8")
    os.chmod(path, 0o644)
    return arguments


def _ready_snapshot(worker: str, port: int) -> tuple[float, float, dict[str, Any]]:
    started = time.monotonic()
    first_ready_ms: float | None = None
    consecutive = 0
    last: dict[str, Any] | None = None
    while time.monotonic() - started < READY_TIMEOUT_SECONDS:
        snapshot = _adapter("snapshot", worker, port, expect_json=True)
        last = snapshot
        rss = snapshot.get("rss_kb")
        qualified = (
            snapshot.get("process_identity") is True
            and snapshot.get("socket_ready") is True
            and snapshot.get("log_clean") is True
            and isinstance(rss, int)
            and not isinstance(rss, bool)
            and rss > 0
        )
        if qualified:
            elapsed_ms = (time.monotonic() - started) * 1000.0
            if first_ready_ms is None:
                first_ready_ms = elapsed_ms
            consecutive += 1
            if consecutive >= 2:
                return first_ready_ms, elapsed_ms, snapshot
        else:
            consecutive = 0
            first_ready_ms = None
        time.sleep(POLL_SECONDS)
    raise MeasurementError(f"worker {worker} did not become stably ready: {last}")


def _sample(variant: str, worker: str, port: int, trial: int) -> dict[str, Any]:
    launch_started = time.monotonic()
    _adapter("launch", worker, port)
    try:
        first_ready_ms, stable_ready_ms, ready = _ready_snapshot(worker, port)
        time.sleep(SETTLE_SECONDS)
        settled = _adapter("snapshot", worker, port, expect_json=True)
        settled_rss = settled.get("rss_kb")
        if not isinstance(settled_rss, int) or isinstance(settled_rss, bool) or settled_rss <= 0:
            raise MeasurementError(f"worker {worker} settled RSS is unavailable")
        return {
            "trial": trial,
            "variant": variant,
            "worker": worker,
            "divert_port": port,
            "first_ready_ms": round(first_ready_ms, 3),
            "stable_ready_ms": round(stable_ready_ms, 3),
            "launch_to_sample_ms": round((time.monotonic() - launch_started) * 1000.0, 3),
            "ready_rss_kb": ready["rss_kb"],
            "settled_rss_kb": settled_rss,
            "process_identity": settled.get("process_identity") is True,
            "socket_ready": settled.get("socket_ready") is True,
            "log_clean": settled.get("log_clean") is True,
        }
    finally:
        _adapter("stop", worker, port)


def _p90(values: Sequence[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.90) - 1)
    return ordered[index]


def _metric(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise MeasurementError("cannot summarize an empty metric")
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "median": round(float(statistics.median(values)), 3),
        "p90": round(_p90(values), 3),
        "max": round(max(values), 3),
    }


def _summaries(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for variant, _worker, _port in VARIANTS:
        selected = [sample for sample in samples if sample["variant"] == variant]
        result[variant] = {
            "sample_count": len(selected),
            "stable_ready_ms": _metric([float(sample["stable_ready_ms"]) for sample in selected]),
            "ready_rss_kb": _metric([float(sample["ready_rss_kb"]) for sample in selected]),
            "settled_rss_kb": _metric([float(sample["settled_rss_kb"]) for sample in selected]),
        }
    return result


def _delta(left: dict[str, Any], right: dict[str, Any], metric: str) -> dict[str, float | None]:
    left_median = float(left[metric]["median"])
    right_median = float(right[metric]["median"])
    difference = left_median - right_median
    percent = None if right_median == 0 else difference * 100.0 / right_median
    return {"delta": round(difference, 3), "percent": None if percent is None else round(percent, 3)}


def _comparisons(summaries: dict[str, Any]) -> dict[str, Any]:
    pairs = (
        ("builtin_vs_blob_free", "builtin", "blob-free"),
        ("external_vs_blob_free", "external", "blob-free"),
        ("external_vs_builtin", "external", "builtin"),
    )
    result: dict[str, Any] = {}
    for label, left_name, right_name in pairs:
        left = summaries[left_name]
        right = summaries[right_name]
        result[label] = {
            "stable_ready_ms_median": _delta(left, right, "stable_ready_ms"),
            "ready_rss_kb_median": _delta(left, right, "ready_rss_kb"),
            "settled_rss_kb_median": _delta(left, right, "settled_rss_kb"),
        }
    return result


def run_measurement(output: Path, trials: int) -> dict[str, Any]:
    if trials < MIN_TRIALS or trials > MAX_TRIALS:
        raise MeasurementError(f"trials must be between {MIN_TRIALS} and {MAX_TRIALS}")
    session = _session_dir()
    inventory = resources.snapshot_inventory(resources.configured_lua_root(), resources.configured_fake_root())
    selector = _selector_path()
    arguments: dict[str, list[str]] = {}
    for variant, worker, port in VARIANTS:
        arguments[variant] = _write_args(session, inventory, selector, variant, worker, port)

    _adapter("cleanup-all")
    _adapter("preflight")
    samples: list[dict[str, Any]] = []
    rotations = (
        VARIANTS,
        (VARIANTS[1], VARIANTS[2], VARIANTS[0]),
        (VARIANTS[2], VARIANTS[0], VARIANTS[1]),
    )
    try:
        for trial in range(1, trials + 1):
            for variant, worker, port in rotations[(trial - 1) % len(rotations)]:
                samples.append(_sample(variant, worker, port, trial))
    finally:
        _adapter("cleanup-all")
    _adapter("preflight")

    summaries = _summaries(samples)
    report = {
        "schema": SCHEMA,
        "policy": POLICY,
        "generated_at": _utc_now(),
        "experiment_only": True,
        "production_model_changed": False,
        "production_model": stage60_model_c.MODEL,
        "cache_policy": CACHE_POLICY,
        "measurement_design": "balanced-interleaved-three-variant-startup",
        "trials_per_variant": trials,
        "sample_count": len(samples),
        "resource_inventory": inventory.to_dict(),
        "selector_lua": str(selector),
        "variant_arguments": arguments,
        "samples": samples,
        "summaries": summaries,
        "comparisons": _comparisons(summaries),
        "checks": {
            "adapter_preflight": True,
            "expected_sample_count": len(samples) == trials * len(VARIANTS),
            "all_samples_ready": all(
                sample["process_identity"] and sample["socket_ready"] and sample["log_clean"]
                for sample in samples
            ),
            "temporary_workers_clean": True,
            "lifecycle_restored": False,
            "cleanup_ok": False,
        },
        "production_change_recommended": False,
        "conclusion": "pending_restoration",
        "next_step": "finalize_lifecycle_evidence",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MeasurementError(f"JSON evidence is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise MeasurementError(f"JSON evidence is not an object: {path}")
    return value


def _lifecycle_equal(initial: dict[str, Any], final: dict[str, Any]) -> bool:
    keys = (
        "state",
        "child_running",
        "supervisor_running",
        "runtime_args_hash",
        "effective_config_hash",
        "normal_firewall_hash",
    )
    return initial.get("schema") == 1 and final.get("schema") == 1 and all(
        initial.get(key) == final.get(key) for key in keys
    )


def finalize(output: Path, initial_path: Path, final_path: Path, cleanup_ok: bool) -> dict[str, Any]:
    report = _read_object(output)
    if report.get("schema") != SCHEMA or report.get("policy") != POLICY:
        raise MeasurementError("measurement report identity is invalid")
    initial = _read_object(initial_path)
    final = _read_object(final_path)
    lifecycle_restored = _lifecycle_equal(initial, final)
    checks = report.setdefault("checks", {})
    checks["lifecycle_restored"] = lifecycle_restored
    checks["cleanup_ok"] = bool(cleanup_ok)
    report["lifecycle"] = {"initial": initial, "final": final}
    accepted = all(
        checks.get(name) is True
        for name in (
            "adapter_preflight",
            "expected_sample_count",
            "all_samples_ready",
            "temporary_workers_clean",
            "lifecycle_restored",
            "cleanup_ok",
        )
    )
    report["production_change_recommended"] = False
    report["conclusion"] = "measurement_accepted" if accepted else "measurement_invalid"
    report["next_step"] = (
        "evaluate_reproducibility_before_any_production_blob_change"
        if accepted
        else "repair_measurement_evidence_before_drawing_blob_conclusions"
    )
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure Model-C BLOB startup/readiness/RSS tradeoffs")
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
