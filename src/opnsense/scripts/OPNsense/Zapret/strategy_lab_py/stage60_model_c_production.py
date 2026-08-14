"""Normal production Stage-60 owner for Model-C-only execution.

The adaptive Stage-60 planner and the proven Model-C bucket engine stay authoritative.
Normal production execution uses Model C only: a Model-C infrastructure/selector/rendering/
readiness/attribution/cleanup failure is a bounded structural Stage-60 error and is never
replayed through Model B or cold Model A. Explicit model-b/cold overrides remain available
only for reference, benchmark, and focused test tooling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from . import endpoint_epoch, model_b, search, search_graph, stage60_model_c, stage60_parallel

MODEL = stage60_model_c.MODEL
WIDTH = stage60_model_c.WIDTH


class ModelCOnlyInfrastructureError(stage60_parallel.Stage60ParallelError):
    """Normal production Model C failed structurally; no B/A replay is permitted."""


def _requested_model() -> str:
    return stage60_model_c._requested_model()


def _mark_model_c_only_result(result_file: str, error: str = "") -> None:
    """Make the persisted Stage-60 runtime policy truthful even on structural failure."""
    output = Path(result_file)
    if not output.is_file():
        return
    try:
        result = search._load_json(output)
    except (OSError, ValueError):
        return
    parallel = result.get("parallel")
    if not isinstance(parallel, dict):
        parallel = {}
        result["parallel"] = parallel
    parallel["cold_fallback_available"] = False
    parallel["model_c_only"] = True
    parallel["fallbacks"] = []
    if error:
        parallel["model_c_infrastructure_error"] = error
    else:
        parallel.pop("model_c_infrastructure_error", None)
    result["execution_model"] = MODEL
    search._atomic_json(output, result)


def _production_batch(*args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one planner-selected logical batch through Model C and never replay it."""
    try:
        return stage60_model_c._bucket_batch(*args, **kwargs)
    except stage60_parallel.Stage60Canceled:
        raise
    except stage60_model_c.ModelCInfrastructureError as exc:
        raise ModelCOnlyInfrastructureError(f"Model C infrastructure failure: {exc}") from exc


def _run_reference_model(model: str, *args: str) -> int:
    """Keep Model B/A reachable only when explicitly requested for reference/test work."""
    return stage60_model_c._run_existing_model(model, *args)


def expand(job_id: str, endpoints_file: str, family_result_file: str, result_file: str) -> int:
    requested = _requested_model()
    if requested == "cold":
        return _run_reference_model("cold", job_id, endpoints_file, family_result_file, result_file)
    if requested == "model-b":
        return _run_reference_model("parallel", job_id, endpoints_file, family_result_file, result_file)

    original_batch = stage60_parallel._warm_batch
    original_model = stage60_parallel.MODEL
    previous_env = os.environ.get("STRATEGY_LAB_STAGE60_MODEL")
    had_previous_env = "STRATEGY_LAB_STAGE60_MODEL" in os.environ
    infrastructure_error = ""

    os.environ["STRATEGY_LAB_STAGE60_MODEL"] = "parallel"
    stage60_parallel.MODEL = MODEL
    stage60_parallel._warm_batch = _production_batch
    try:
        return stage60_parallel.expand(job_id, endpoints_file, family_result_file, result_file)
    except ModelCOnlyInfrastructureError as exc:
        infrastructure_error = str(exc)
        raise
    finally:
        _mark_model_c_only_result(result_file, infrastructure_error)
        stage60_parallel._warm_batch = original_batch
        stage60_parallel.MODEL = original_model
        if had_previous_env:
            assert previous_env is not None
            os.environ["STRATEGY_LAB_STAGE60_MODEL"] = previous_env
        else:
            os.environ.pop("STRATEGY_LAB_STAGE60_MODEL", None)
        model_b._try_adapter("cleanup-all", timeout=25)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or [])
    if len(args) == 5 and args[0] == "expand":
        try:
            return expand(args[1], args[2], args[3], args[4])
        except stage60_parallel.Stage60Canceled:
            return stage60_parallel.EX_CANCEL
        except (
            stage60_parallel.Stage60ParallelError,
            search_graph.SearchGraphError,
            endpoint_epoch.EndpointEpochError,
        ) as exc:
            print(f"ERROR: {exc}", file=os.sys.stderr)
            return stage60_parallel.EX_SOFTWARE
    raise ValueError("stage60-model-c-production requires: expand JOB ENDPOINTS FAMILY_RESULT OUTPUT")
