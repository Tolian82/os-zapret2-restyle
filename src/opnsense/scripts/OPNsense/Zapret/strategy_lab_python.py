"""Packaged Strategy Lab Python compatibility entry point."""

from __future__ import annotations

import sys

from strategy_lab_py.compat import main as compat_main
from strategy_lab_py import adaptive_validation
from strategy_lab_py import blob_startup_measurement
from strategy_lab_py import discovery_probe_measurement
from strategy_lab_py import lua_initialization_measurement
from strategy_lab_py import model_b_parallel_attribution as model_b_parallel
from strategy_lab_py import stage60_model_c as stage60_parallel
from strategy_lab_py import stage60_source_port_lease


def main() -> int:
    args = list(sys.argv[1:])
    if args[:1] == ["lua-init-measure"]:
        return lua_initialization_measurement.main(args[1:])
    if args[:1] == ["blob-startup-measure"]:
        return blob_startup_measurement.main(args[1:])
    if args[:1] == ["discovery-probe-measure"]:
        try:
            return discovery_probe_measurement.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
    if args[:1] == ["model-b-parallel"]:
        try:
            return model_b_parallel.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
    if args[:1] == ["stage60-parallel"]:
        try:
            # Keep the established Stage-60 compatibility command while routing normal
            # production execution through Model C. Model B and cold Model A remain
            # explicit/fail-closed fallbacks inside the Model-C owner. `_25` leases exact
            # free controlled source ports independently for Model C and Model B.
            with adaptive_validation.probe_tier("discovery"):
                with stage60_source_port_lease.install():
                    return stage60_parallel.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
    return compat_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
