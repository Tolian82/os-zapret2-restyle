"""Measurement-only BLOB common-set startup/RSS experiment for Strategy Lab Model C.

The experiment never installs IPFW routes and never stops or reconfigures normal Zapret2.
It reuses one isolated Model-B adapter slot and one divert port for every controlled variant,
so worker identity/port cannot confound the comparison.  The active Lua/action shape stays
constant while resource declarations scale from none to inline, one external BLOB, and a
bounded production-width common set of three semantically compatible external TLS BLOBs.
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

SCHEMA = 2
POLICY = "blob-common-set-scaling-v1"
CACHE_POLICY = "natural-cache-no-drop"
SELECTOR_LUA = "strategy_lab_model_c.lua"
COMMON_LUA = ("zapret-lib.lua", "zapret-antidpi.lua", "zapret-auto.lua")
WORKER = "external"
DIVERT_PORT = 9992
VARIANTS = ("blob-free", "inline-small", "external-single", "external-common-3")
EXTERNAL_SINGLE = "fake_tls_7"
EXTERNAL_COMMON = (
    "fake_tls_7",
    "tls_clienthello_rutracker_org_kyber",
    "tls_clienthello_vk_com_kyber",
)
INLINE_PATTERN = "0x1603"
PRODUCTION_CANDIDATE_WIDTH = 3
DEFAULT_TRIALS = 12
MIN_TRIALS = 4
MAX_TRIALS = 16
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


def _worker_dir(session: Path) -> Path:
    path = session / "workers" / WORKER
    path.mkdir(parents=True, exist_ok=True)
    return path


def _external_entry(inventory: resources.ResourceInventory, name: str) -> dict[str, Any]:
    path = inventory.external_blob_path(name)
    stat = path.stat()
    return {"name": name, "path": str(path), "size": stat.st_size}


def _resource_sets(inventory: resources.ResourceInventory) -> dict[str, Any]:
    single = [_external_entry(inventory, EXTERNAL_SINGLE)]
    common = [_external_entry(inventory, name) for name in EXTERNAL_COMMON]
    return {
        "blob-free": {
            "resource_class": "blob-free",
            "declaration_count": 0,
            "declared_bytes": 0,
            "active_pattern": None,
            "resources": [],
        },
        "inline-small": {
            "resource_class": "inline",
            "declaration_count": 0,
            "declared_bytes": 2,
            "active_pattern": INLINE_PATTERN,
            "resources": [{"name": "inline-0x1603", "size": 2}],
        },
        "external-single": {
            "resource_class": "external",
            "declaration_count": 1,
            "declared_bytes": sum(item["size"] for item in single),
            "active_pattern": EXTERNAL_SINGLE,
            "resources": single,
        },
        "external-common-3": {
            "resource_class": "external-common-set",
            "declaration_count": len(common),
            "declared_bytes": sum(item["size"] for item in common),
            "active_pattern": EXTERNAL_SINGLE,
            "resources": common,
            "unused_eager_declarations": [name for name in EXTERNAL_COMMON if name != EXTERNAL_SINGLE],
            "synthetic_scope": "bounded-production-width-common-set-upper-bound",
        },
    }


def _arguments_for(
    inventory: resources.ResourceInventory,
    selector: Path,
    variant: str,
) -> list[str]:
    lua_paths = [inventory.lua_path(name) for name in COMMON_LUA]
    if not selector.is_file() or selector.stat().st_size <= 0:
        raise MeasurementError(f"Model C selector Lua is unavailable: {selector}")

    arguments = [f"--port={DIVERT_PORT}"]
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
    if variant == "inline-small":
        action += f":seqovl_pattern={INLINE_PATTERN}"
    elif variant == "external-single":
        path = inventory.external_blob_path(EXTERNAL_SINGLE)
        arguments.append(f"--blob={EXTERNAL_SINGLE}:@{path}")
        action += f":seqovl_pattern={EXTERNAL_SINGLE}"
    elif variant == "external-common-3":
        for name in EXTERNAL_COMMON:
            path = inventory.external_blob_path(name)
            arguments.append(f"--blob={name}:@{path}")
        action += f":seqovl_pattern={EXTERNAL_SINGLE}"
    elif variant != "blob-free":
        raise MeasurementError(f"unknown BLOB variant: {variant}")
    arguments.append(action)
    return arguments


def _write_args(session: Path, arguments: Sequence[str]) -> None:
    path = _worker_dir(session) / "dvtws.args"
    path.write_text("".join(f"{value}\n" for value in arguments), encoding="utf-8")
    os.chmod(path, 0o644)


def _ready_snapshot() -> tuple[float, float, dict[str, Any]]:
    started = time.monotonic()
    first_ready_ms: float | None = None
    consecutive = 0
    last: dict[str, Any] | None = None
    while time.monotonic() - started < READY_TIMEOUT_SECONDS:
        snapshot = _adapter("snapshot", WORKER, DIVERT_PORT, expect_json=True)
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
    raise MeasurementError(f"worker {WORKER} did not become stably ready: {last}")


def _sample(session: Path, variant: str, arguments: Sequence[str], trial: int) -> dict[str, Any]:
    _write_args(session, arguments)
    launch_started = time.monotonic()
    _adapter("launch", WORKER, DIVERT_PORT)
    try:
        first_ready_ms, stable_ready_ms, ready = _ready_snapshot()
        time.sleep(SETTLE_SECONDS)
        settled = _adapter("snapshot", WORKER, DIVERT_PORT, expect_json=True)
        settled_rss = settled.get("rss_kb")
        if not isinstance(settled_rss, int) or isinstance(settled_rss, bool) or settled_rss <= 0:
            raise MeasurementError(f"worker {WORKER} settled RSS is unavailable")
        return {
            "trial": trial,
            "variant": variant,
            "worker": WORKER,
            "divert_port": DIVERT_PORT,
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
        _adapter("stop", WORKER, DIVERT_PORT)


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
        "mean": round(float(statistics.mean(values)), 3),
        "median": round(float(statistics.median(values)), 3),
        "stdev": round(float(statistics.stdev(values)), 3) if len(values) > 1 else 0.0,
        "p90": round(_p90(values), 3),
        "max": round(max(values), 3),
    }


def _summaries(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for variant in VARIANTS:
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
        ("inline_small_vs_blob_free", "inline-small", "blob-free"),
        ("external_single_vs_blob_free", "external-single", "blob-free"),
        ("external_common_3_vs_external_single", "external-common-3", "external-single"),
        ("external_common_3_vs_blob_free", "external-common-3", "blob-free"),
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


def _rotations() -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(VARIANTS[offset:] + VARIANTS[:offset]) for offset in range(len(VARIANTS)))


def run_measurement(output: Path, trials: int) -> dict[str, Any]:
    if trials < MIN_TRIALS or trials > MAX_TRIALS or trials % len(VARIANTS) != 0:
        raise MeasurementError(
            f"trials must be a multiple of {len(VARIANTS)} between {MIN_TRIALS} and {MAX_TRIALS}"
        )
    session = _session_dir()
    inventory = resources.snapshot_inventory(resources.configured_lua_root(), resources.configured_fake_root())
    selector = _selector_path()
    resource_sets = _resource_sets(inventory)
    arguments = {variant: _arguments_for(inventory, selector, variant) for variant in VARIANTS}

    _adapter("cleanup-all")
    _adapter("preflight")
    samples: list[dict[str, Any]] = []
    rotations = _rotations()
    try:
        for trial in range(1, trials + 1):
            for variant in rotations[(trial - 1) % len(rotations)]:
                samples.append(_sample(session, variant, arguments[variant], trial))
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
        "production_candidate_width": PRODUCTION_CANDIDATE_WIDTH,
        "cache_policy": CACHE_POLICY,
        "measurement_design": "balanced-interleaved-four-variant-common-set-startup",
        "worker_identity_policy": "single-worker-single-port-all-variants",
        "worker": WORKER,
        "divert_port": DIVERT_PORT,
        "trials_per_variant": trials,
        "sample_count": len(samples),
        "resource_inventory": inventory.to_dict(),
        "variant_resource_sets": resource_sets,
        "selector_lua": str(selector),
        "variant_arguments": arguments,
        "samples": samples,
        "summaries": summaries,
        "comparisons": _comparisons(summaries),
        "checks": {
            "adapter_preflight": True,
            "expected_sample_count": len(samples) == trials * len(VARIANTS),
            "balanced_trial_count": trials % len(VARIANTS) == 0,
            "single_worker_identity": all(
                sample["worker"] == WORKER and sample["divert_port"] == DIVERT_PORT for sample in samples
            ),
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
            "balanced_trial_count",
            "single_worker_identity",
            "all_samples_ready",
            "temporary_workers_clean",
            "lifecycle_restored",
            "cleanup_ok",
        )
    )
    report["production_change_recommended"] = False
    report["conclusion"] = "measurement_accepted" if accepted else "measurement_invalid"
    report["next_step"] = (
        "evaluate_common_set_scaling_reproducibility_before_any_production_blob_change"
        if accepted
        else "repair_measurement_evidence_before_drawing_blob_conclusions"
    )
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure Model-C BLOB common-set startup/readiness/RSS scaling")
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
