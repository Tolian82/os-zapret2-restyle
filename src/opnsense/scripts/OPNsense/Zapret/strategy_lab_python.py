"""Packaged Strategy Lab Python compatibility entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from strategy_lab_py.compat import main as compat_main
from strategy_lab_py import adaptive_validation
from strategy_lab_py import blob_startup_measurement
from strategy_lab_py import discovery_probe_measurement
from strategy_lab_py import ip_target_support
from strategy_lab_py import lua_initialization_measurement
from strategy_lab_py import model_c_lifecycle_measurement
from strategy_lab_py import model_b_parallel_attribution as model_b_parallel
from strategy_lab_py import stage60_model_c_production as stage60_parallel
from strategy_lab_py import stage60_source_port_lease
from strategy_lab_py import truthful_result_support


def _prepare_model_c_lifecycle_runtime_permissions(args: list[str]) -> None:
    """Allow privilege-dropped dvtws2 workers to traverse the isolated replay tree."""
    if args[:1] != ["run"]:
        return
    raw = os.environ.get("STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR", "").strip()
    if not raw:
        return
    runs = Path(raw)
    session = runs.parent
    root = session.parent
    if runs.name != "runs" or not session.name.startswith("session.") or root.name != "model-c-lifecycle-measurement":
        raise RuntimeError("Model-C lifecycle measurement directory layout is invalid")
    for path in (root, session, runs):
        if not path.is_dir():
            raise RuntimeError(f"Model-C lifecycle measurement runtime directory is unavailable: {path}")
        try:
            path.chmod(0o711)
        except OSError as exc:
            raise RuntimeError(
                f"Model-C lifecycle measurement runtime directory is not traversable: {path}"
            ) from exc


def main() -> int:
    ip_target_support.install()
    truthful_result_support.install()
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
    if args[:1] == ["model-c-lifecycle-measure"]:
        try:
            _prepare_model_c_lifecycle_runtime_permissions(args[1:])
            return model_c_lifecycle_measurement.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 70
    if args[:1] == ["model-b-parallel"]:
        try:
            return model_b_parallel.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
    if args[:1] == ["stage60-parallel"]:
        try:
            # Keep the established Stage-60 compatibility command while routing normal
            # production execution through the Model-C-only owner. Explicit Model B/cold
            # Model A overrides remain reference/test tooling, never automatic replay.
            with adaptive_validation.probe_tier("discovery"):
                with stage60_source_port_lease.install():
                    return stage60_parallel.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
    return compat_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
