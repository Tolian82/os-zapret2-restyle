#!/usr/bin/env python3
"""TZ6v5 S05a JSON status: no second owner, FD9 acquisition or files written."""
from __future__ import annotations

import json
import sys
sys.dont_write_bytecode = True  # MUST precede original S04/FD9 inspector imports.

from component_inventory_opnsense import collect
from status_projection import project, timestamp_utc, unavailable


def main(argv: list[str]) -> int:
    if argv != ["status_readonly.py"]:
        print("INVALID_ARGUMENT", file=sys.stderr)
        return 64
    at = timestamp_utc()
    try:
        report = project(collect(), at)
    except (OSError, ValueError, RuntimeError, TypeError, KeyError,
            AttributeError):
        report = unavailable(at)
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return report["status_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main([__file__.rsplit("/", 1)[-1], *sys.argv[1:]]))
