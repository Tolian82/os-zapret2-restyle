#!/usr/bin/env python3
"""TZ6v5 S05a JSON status: no second owner, FD9 acquisition or files written."""
from __future__ import annotations

import json
import sys
sys.dont_write_bytecode = True  # MUST precede original S04/FD9 inspector imports.

from component_inventory_opnsense import collect
from status_projection import project, timestamp_utc, unavailable
from status_error_original import read_qualified_failure


def main(argv: list[str]) -> int:
    if argv != ["status_readonly.py"]:
        print("INVALID_ARGUMENT", file=sys.stderr)
        return 64
    at = timestamp_utc()
    try:
        original = collect()
        report = project(original, at)
        # The existing original owner records genuine Apply terminal failures.
        # The reader has no write path and never changes physical Status rc.
        try:
            receipt = read_qualified_failure(original)
        except (OSError, ValueError, RuntimeError, TypeError, KeyError,
                AttributeError):
            # An untrusted, racing or unreadable record is NOT a last error.
            # Preserve the S04 physical fact and expose the uncertainty.
            report["diagnostic_state"] = "unavailable"
        else:
            if receipt is not None:
                report["last_error"] = receipt
                report["diagnostic_state"] = "qualified"
                report["stage"] = receipt["stage"]
                report["operation_id"] = receipt["operation_id"]
    except (OSError, ValueError, RuntimeError, TypeError, KeyError,
            AttributeError):
        report = unavailable(at)
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return report["status_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main([__file__.rsplit("/", 1)[-1], *sys.argv[1:]]))
