"""Compatibility boundary for the incremental Strategy Lab Python migration."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Sequence

from . import FOUNDATION_REVISION, SUPPORTED_PYTHON

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
DEFAULT_SHELL_WORKER = "/usr/local/opnsense/scripts/OPNsense/Zapret/strategy_lab_worker.sh"
JOB_ID_RE = re.compile(r"^job\.[A-Za-z0-9]{6,64}$")


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _runtime_supported() -> bool:
    current = sys.version_info[:2]
    if current == SUPPORTED_PYTHON:
        return True
    _error(
        "Strategy Lab requires Python "
        f"{SUPPORTED_PYTHON[0]}.{SUPPORTED_PYTHON[1]}; found {current[0]}.{current[1]}"
    )
    return False


def _delegate_shell(job_id: str) -> int:
    if not JOB_ID_RE.fullmatch(job_id):
        _error("invalid Strategy Lab job id")
        return EX_USAGE

    worker = os.environ.get("STRATEGY_LAB_SHELL_WORKER", DEFAULT_SHELL_WORKER)
    if not os.path.isfile(worker) or not os.access(worker, os.X_OK):
        _error(f"Strategy Lab compatibility worker is not executable: {worker}")
        return EX_SOFTWARE

    os.execv(worker, [worker, job_id])
    return EX_SOFTWARE


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not _runtime_supported():
        return EX_SOFTWARE

    if args == ["--self-test"]:
        print(
            "Strategy Lab Python foundation: OK "
            f"(Python {SUPPORTED_PYTHON[0]}.{SUPPORTED_PYTHON[1]}, revision {FOUNDATION_REVISION})"
        )
        return EX_OK

    if len(args) != 1:
        _error("usage: strategy_lab_python.py job_id | --self-test")
        return EX_USAGE

    return _delegate_shell(args[0])
