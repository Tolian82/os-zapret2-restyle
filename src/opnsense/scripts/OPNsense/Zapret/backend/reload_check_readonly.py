#!/usr/bin/env python3
"""S05f1 observational reload eligibility; no S08/S09 semantic authority.

Only the already-qualified S04 physical inventory and S05 pure projection
are read. Neither an engine signal nor a live reload is implemented.
"""
from __future__ import annotations

import json
import sys
sys.dont_write_bytecode = True

from component_inventory_opnsense import collect
from status_projection import project, timestamp_utc


def project_preflight(report: dict) -> dict:
    status = project(report, timestamp_utc())
    runtime = status["runtime_state"]
    stopped = runtime == "STOPPED" and status["verification"] == "verified"
    return {
        "schema": 1,
        "action": "reload-check",
        "decision": "NOT_RUNNING" if stopped else "REFUSE",
        "code": ("NOT_RUNNING" if stopped else
                 "RELOAD_NOT_SUPPORTED" if runtime == "RUNNING" else
                 "RELOAD_CHECK_UNAVAILABLE"),
        "reason": ("service-stopped" if stopped else
                   "semantic-planner-unavailable" if runtime == "RUNNING" else
                   "runtime-unverified"),
        "runtime_state": runtime,
        "runtime_verification": status["verification"],
        "verification": "verified" if stopped else "refused",
        "semantic_diff_verified": False,
        "authorization": "NONE",
        "physical_transition_allowed": False,
    }


def refused_unavailable() -> dict:
    return {
        "schema": 1, "action": "reload-check", "decision": "REFUSE",
        "code": "RELOAD_CHECK_UNAVAILABLE", "reason": "runtime-unverified",
        "runtime_state": "UNKNOWN", "runtime_verification": "uncertain",
        "verification": "refused", "semantic_diff_verified": False,
        "authorization": "NONE", "physical_transition_allowed": False,
    }


def main(argv: list[str]) -> int:
    if argv == ["reload_check_readonly.py"]:
        json_mode = False
    elif argv == ["reload_check_readonly.py", "--json"]:
        json_mode = True
    else:
        print("ERROR: INVALID_ARGUMENT", file=sys.stderr)
        return 64
    try:
        result = project_preflight(collect())
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError):
        # Never serialize exception data from kernel, Config or engine args.
        result = refused_unavailable()
    print(json.dumps(result, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":")) if json_mode else
          "reload-check=" + result["decision"])
    return 1 if result["decision"] == "NOT_RUNNING" else 2


if __name__ == "__main__":
    raise SystemExit(main([__file__.rsplit("/", 1)[-1], *sys.argv[1:]]))
