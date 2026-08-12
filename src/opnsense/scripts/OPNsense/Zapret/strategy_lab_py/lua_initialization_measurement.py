"""Measurement-only comparison of Model-C Lua initialization sets.

This module does not start or stop dvtws2 and does not alter production Stage 60.  It
compares the Lua files that current Model C would initialize for each width-three native
TLS 1.3 batch with the smallest set implied by the selected CandidateSpec declarations.
When both sets are identical, the report explicitly suppresses runtime speedup claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import resources, search_graph, stage60_model_c

SCHEMA = 1
POLICY = "lua-init-set-equivalence-v1"
AUTO_LUA = "zapret-auto.lua"
SELECTOR_LUA = "strategy_lab_model_c.lua"


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def _candidate_minimal_set(spec: Any) -> tuple[str, ...]:
    return _ordered_unique((*spec.lua_dependencies, AUTO_LUA, SELECTOR_LUA))


def _current_batch_set(specs: Sequence[Any]) -> tuple[str, ...]:
    dependencies: list[str] = []
    for spec in specs:
        dependencies.extend(spec.lua_dependencies)
    return _ordered_unique((*dependencies, AUTO_LUA, SELECTOR_LUA))


def _set_id(values: Sequence[str]) -> str:
    encoded = "\n".join(values).encode("utf-8")
    return "lis1-" + hashlib.blake2b(encoded, digest_size=12).hexdigest()


def _file_evidence(lua_dir: Path, selector_lua: Path, names: Sequence[str]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for name in names:
        path = selector_lua if name == SELECTOR_LUA else lua_dir / name
        item: dict[str, Any] = {
            "name": name,
            "path": str(path),
            "present": path.is_file(),
            "size_bytes": None,
        }
        if path.is_file():
            item["size_bytes"] = path.stat().st_size
        evidence.append(item)
    return evidence


def build_report(
    *,
    graph: search_graph.NativeSearchGraph | None = None,
    lua_dir: Path | None = None,
    selector_lua: Path | None = None,
) -> dict[str, Any]:
    native = graph or search_graph.native_tls13_graph()
    effective_lua_dir = lua_dir or resources.configured_lua_root()
    selector = selector_lua or (Path(__file__).resolve().parent.parent / SELECTOR_LUA)
    nodes = native.stage_nodes("expansion")
    width = stage60_model_c.WIDTH

    candidates: list[dict[str, Any]] = []
    minimal_sets: dict[str, tuple[str, ...]] = {}
    for node in nodes:
        minimal = _candidate_minimal_set(node.spec)
        minimal_sets[node.candidate_id] = minimal
        candidates.append(
            {
                "candidate_id": node.candidate_id,
                "family": node.spec.family,
                "candidate_spec_id": node.spec.spec_id,
                "declared_lua_dependencies": list(node.spec.lua_dependencies),
                "candidate_minimal_init_set": list(minimal),
                "candidate_minimal_init_set_id": _set_id(minimal),
            }
        )

    batches: list[dict[str, Any]] = []
    all_batches_equivalent = True
    for batch_number, offset in enumerate(range(0, len(nodes), width), 1):
        selected = nodes[offset : offset + width]
        specs = [node.spec for node in selected]
        current = _current_batch_set(specs)
        minimal_union = _ordered_unique(
            value
            for node in selected
            for value in minimal_sets[node.candidate_id]
        )
        equivalent = current == minimal_union
        all_batches_equivalent = all_batches_equivalent and equivalent
        batches.append(
            {
                "batch": batch_number,
                "candidate_ids": [node.candidate_id for node in selected],
                "current_model_c_init_set": list(current),
                "current_model_c_init_set_id": _set_id(current),
                "candidate_minimal_union": list(minimal_union),
                "candidate_minimal_union_id": _set_id(minimal_union),
                "equivalent_init_set": equivalent,
            }
        )

    dependency_signatures = {tuple(node.spec.lua_dependencies) for node in nodes}
    all_candidates_same_dependencies = len(dependency_signatures) == 1
    effective = _ordered_unique(
        value for batch in batches for value in batch["current_model_c_init_set"]
    )
    file_evidence = _file_evidence(effective_lua_dir, selector, effective)
    runtime_comparison_required = not all_batches_equivalent

    return {
        "schema": SCHEMA,
        "policy": POLICY,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "experiment_only": True,
        "production_model_changed": False,
        "model": stage60_model_c.MODEL,
        "graph_id": native.graph_id,
        "candidate_count": len(nodes),
        "batch_width": width,
        "all_candidates_same_dependencies": all_candidates_same_dependencies,
        "declared_dependency_signatures": [list(value) for value in sorted(dependency_signatures)],
        "candidates": candidates,
        "batches": batches,
        "effective_lua_files": file_evidence,
        "checks": {
            "all_batches_equivalent": all_batches_equivalent,
            "all_required_files_present": all(item["present"] for item in file_evidence),
            "production_model_unchanged": True,
        },
        "runtime_comparison_required": runtime_comparison_required,
        "timing_claim": "not_applicable_equivalent_init_set" if not runtime_comparison_required else "measurement_required",
        "rss_claim": "not_applicable_equivalent_init_set" if not runtime_comparison_required else "measurement_required",
        "conclusion": (
            "equivalent_init_set"
            if not runtime_comparison_required
            else "distinct_init_sets_require_runtime_measurement"
        ),
        "next_step": (
            "close_lua_initialization_optimization_and_measure_blob_startup_rss"
            if not runtime_comparison_required
            else "run_controlled_runtime_ab_before_any_production_change"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure Model-C Lua initialization set equivalence")
    parser.add_argument("--output", default="", help="optional JSON output path; stdout is always emitted")
    parser.add_argument("--lua-dir", default="", help="override canonical Strategy Lab Lua root")
    parser.add_argument("--selector-lua", default="")
    args = parser.parse_args(list(argv) if argv is not None else None)

    selector = Path(args.selector_lua) if args.selector_lua else None
    lua_dir = Path(args.lua_dir) if args.lua_dir else resources.configured_lua_root()
    report = build_report(lua_dir=lua_dir, selector_lua=selector)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
