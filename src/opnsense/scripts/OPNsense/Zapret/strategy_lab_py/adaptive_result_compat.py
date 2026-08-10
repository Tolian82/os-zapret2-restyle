"""Preserve the private circular handoff while `_33` deep-validates publication finalists."""

from __future__ import annotations

import os
from collections.abc import Sequence

from . import adaptive_validation
from . import result as final_result

EX_OK = 0


def _backfill_circular(job_id: str) -> None:
    job = final_result.job_dir(job_id)
    shortlist_path = job / "shortlist.json"
    stability_path = job / "stability.json"
    status_path = job / "status.json"
    if not shortlist_path.is_file() or not stability_path.is_file() or not status_path.is_file():
        return
    shortlist = final_result._read_json(shortlist_path)
    stability = final_result._read_json(stability_path)
    status = final_result._read_json(status_path)
    if not isinstance(shortlist, dict) or not isinstance(stability, dict) or not isinstance(status, dict):
        return
    target = status.get("target")
    target_type = status.get("target_type")
    if not isinstance(target, str) or not isinstance(target_type, str):
        return
    try:
        limit = int(os.environ.get("STRATEGY_LAB_SHORTLIST_LIMIT", "3"))
    except ValueError:
        return
    if limit <= 0:
        return

    current = shortlist.get("circular_items")
    circular: list[dict] = [dict(item) for item in current if isinstance(item, dict)] if isinstance(current, list) else []
    seen = {str(item.get("id", "")) for item in circular}
    candidates = stability.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    for source in candidates:
        if len(circular) >= limit:
            break
        if not isinstance(source, dict) or source.get("stable") is not True:
            continue
        candidate_id = source.get("id")
        family = source.get("family")
        strategy = source.get("strategy")
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in seen:
            continue
        if not isinstance(family, str) or not family or not isinstance(strategy, str) or not strategy:
            continue
        profile = final_result.build_profile(target, target_type, "tls13", 443, "", strategy)
        item = dict(source)
        item.update(
            protocol="tls13",
            port=443,
            protocol_rank=final_result.protocol_rank("tls13"),
            target=target,
            target_type=target_type,
            profile=profile,
            circular_eligible=True,
            finalist_validation="stability_only_pending_circular",
        )
        circular.append(item)
        seen.add(candidate_id)
    shortlist["circular_items"] = circular
    shortlist["circular_count"] = len(circular)
    final_result._atomic_json(shortlist_path, shortlist)


def run_result(argv: Sequence[str]) -> int:
    args = list(argv)
    status = adaptive_validation.run_result(args)
    if status == EX_OK and args[:1] == ["shortlist"] and len(args) == 2:
        _backfill_circular(args[1])
    return status
