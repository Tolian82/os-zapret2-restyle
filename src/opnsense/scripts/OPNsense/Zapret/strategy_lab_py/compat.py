"""Compatibility boundary for the incremental Strategy Lab Python migration."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Sequence

from . import FOUNDATION_REVISION, SUPPORTED_PYTHON
from . import candidate as candidate_screening
from . import extended as extended_orchestration
from . import family as family_screening
from . import late_containment
from . import orchestrator as stage_orchestrator
from . import probe as probe_execution
from . import request as request_execution
from . import result as final_result
from . import search as search_orchestration
from . import state as state_persistence

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
EX_TEMPFAIL = 75
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


def _run_state(args: Sequence[str]) -> int:
    try:
        return state_persistence.main(args)
    except state_persistence.UsageError as exc:
        _error(str(exc)); return EX_USAGE
    except state_persistence.LockTimeout as exc:
        _error(str(exc)); return EX_TEMPFAIL
    except state_persistence.StateError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab state persistence failed: {exc}"); return EX_SOFTWARE


def _run_orchestrator(args: Sequence[str]) -> int:
    try:
        return late_containment.orchestrator_main(args)
    except stage_orchestrator.UsageError as exc:
        _error(str(exc)); return EX_USAGE
    except stage_orchestrator.OrchestrationError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab orchestration failed: {exc}"); return EX_SOFTWARE


def _run_probe(args: Sequence[str]) -> int:
    try:
        return probe_execution.main(args)
    except probe_execution.UsageError as exc:
        _error(str(exc)); return EX_USAGE
    except probe_execution.ProbeError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except request_execution.RequestError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except RuntimeError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab probe execution failed: {exc}"); return EX_SOFTWARE


def _run_request(args: Sequence[str]) -> int:
    try:
        return request_execution.main(args)
    except request_execution.UsageError as exc:
        _error(str(exc)); return EX_USAGE
    except request_execution.RequestError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab request execution failed: {exc}"); return EX_SOFTWARE


def _run_candidate(args: Sequence[str]) -> int:
    try:
        return candidate_screening.main(args)
    except ValueError as exc:
        _error(str(exc)); return EX_USAGE
    except (RuntimeError, request_execution.RequestError) as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab candidate execution failed: {exc}"); return EX_SOFTWARE


def _run_family(args: Sequence[str]) -> int:
    try:
        return family_screening.main(args)
    except ValueError as exc:
        _error(str(exc)); return EX_USAGE
    except RuntimeError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab family screening failed: {exc}"); return EX_SOFTWARE


def _run_search(args: Sequence[str]) -> int:
    try:
        return late_containment.run_search(args)
    except ValueError as exc:
        _error(str(exc)); return EX_USAGE
    except RuntimeError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab search orchestration failed: {exc}"); return EX_SOFTWARE


def _run_extended(args: Sequence[str]) -> int:
    try:
        return late_containment.run_extended(args)
    except ValueError as exc:
        _error(str(exc)); return EX_USAGE
    except RuntimeError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab extended orchestration failed: {exc}"); return EX_SOFTWARE


def _run_result(args: Sequence[str]) -> int:
    try:
        return final_result.main(args)
    except final_result.ResultError as exc:
        _error(str(exc)); return EX_SOFTWARE
    except (RuntimeError, ValueError, request_execution.RequestError) as exc:
        _error(str(exc)); return EX_SOFTWARE
    except OSError as exc:
        _error(f"Strategy Lab final result processing failed: {exc}"); return EX_SOFTWARE


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
    if args[:1] == ["state"]: return _run_state(args[1:])
    if args[:1] == ["orchestrate"]: return _run_orchestrator(args[1:])
    if args[:1] == ["probe"]: return _run_probe(args[1:])
    if args[:1] == ["request"]: return _run_request(args[1:])
    if args[:1] == ["candidate"]: return _run_candidate(args[1:])
    if args[:1] == ["family"]: return _run_family(args[1:])
    if args[:1] == ["search"]: return _run_search(args[1:])
    if args[:1] == ["extended"]: return _run_extended(args[1:])
    if args[:1] == ["result"]: return _run_result(args[1:])
    if len(args) != 1:
        _error(
            "usage: strategy_lab_python.py job_id | --self-test | state OPERATION ... | "
            "orchestrate JOB_ID | probe OPERATION ... | request OPERATION ... | candidate run ... | "
            "family screen ... | search OPERATION ... | extended OPERATION ... | result OPERATION ..."
        )
        return EX_USAGE
    return _delegate_shell(args[0])
