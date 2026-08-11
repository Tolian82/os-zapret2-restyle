"""Packaged Strategy Lab Python compatibility entry point."""

from __future__ import annotations

import sys

from strategy_lab_py.compat import main as compat_main
from strategy_lab_py import model_b_parallel_attribution as model_b_parallel
from strategy_lab_py import stage60_parallel


def main() -> int:
    args = list(sys.argv[1:])
    if args[:1] == ["model-b-parallel"]:
        try:
            return model_b_parallel.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
    if args[:1] == ["stage60-parallel"]:
        try:
            return stage60_parallel.main(args[1:])
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 64
    return compat_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
