#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
PYTHONPATH="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON}" - <<'PY'
import json
import os
import tempfile
import time
from pathlib import Path

from strategy_lab_py import late_containment as late


def check(condition, message):
    if not condition:
        raise AssertionError(message)


# Stage 85 is no longer an unbounded adapter call. The configured stage limit is
# first capped by the remaining job budget and then passed to the adapter.
obj = object.__new__(late.ContainedOrchestrator)
seen = {}
obj._begin = lambda stage: seen.setdefault("begin", stage)

class FakeBudget:
    def timeout_for(self, stage, operation_limit):
        seen["budget_stage"] = stage
        seen["budget_limit"] = operation_limit
        return min(operation_limit, 9)

obj.budget = FakeBudget()
obj._operation_limit = lambda stage: 999
obj._run_adapter = lambda action, **kwargs: (
    seen.update(action=action, timeout=kwargs.get("operation_timeout"))
    or late.base_orchestrator.AdapterResult("pass", "ok")
)
obj._handle_result = lambda stage, result: None
os.environ[late.STAGE85_TIMEOUT_ENV] = "17"
obj._run_regular_stage("85")
check(seen["begin"] == "85", "Stage 85 did not begin")
check(seen["budget_stage"] == "85", "Stage 85 did not use the job deadline")
check(seen["budget_limit"] == 17, "Stage 85 configured limit was not applied")
check(seen["timeout"] == 9, "Stage 85 adapter did not receive the capped timeout")
os.environ.pop(late.STAGE85_TIMEOUT_ENV, None)


# Mandatory restoration is bounded separately from the exhausted search budget.
obj = object.__new__(late.ContainedOrchestrator)
obj.job_id = "job.Test01"
obj.state_path = Path("/tmp/status.json")
obj.events_path = Path("/tmp/events.ndjson")
obj.language = "en"
obj.current_stage = ""
restore_seen = {}
obj._update_stage = lambda stage, status, message: restore_seen.update(
    final_stage=stage, final_status=status
)
obj._run_adapter = lambda action, **kwargs: (
    restore_seen.update(action=action, timeout=kwargs.get("operation_timeout"))
    or late.base_orchestrator.AdapterResult("pass", "", "RUNNING")
)
orig_update_stage = late.state_persistence.update_stage
orig_append_event = late.state_persistence.append_event
late.state_persistence.update_stage = lambda *args, **kwargs: None
late.state_persistence.append_event = lambda *args, **kwargs: None
os.environ[late.RESTORE_PARENT_TIMEOUT_ENV] = "181"
try:
    outcome = obj._restore("TIMEOUT")
finally:
    late.state_persistence.update_stage = orig_update_stage
    late.state_persistence.append_event = orig_append_event
    os.environ.pop(late.RESTORE_PARENT_TIMEOUT_ENV, None)
check(outcome == "TIMEOUT", "successful restoration changed the search outcome")
check(restore_seen["action"] == "restore", "restoration adapter was not called")
check(restore_seen["timeout"] == 181, "restoration parent bound was not applied")
check(restore_seen["final_status"] == "PASS", "successful restoration was not persisted as PASS")


# Candidate admission includes execution, termination, cleanup, and guard reserves.
short = late._defer_candidate(
    stage="70",
    candidate_id="candidate-a",
    protocol="tls13",
    timeout=8,
    deadline=time.monotonic() + 1,
    attempt=1,
)
check(short is not None, "insufficient Stage-70 budget was admitted")
check(short.evidence()["next_attempt"] == 1, "Stage-70 attempt evidence is incomplete")
roomy = late._defer_candidate(
    stage="70",
    candidate_id="candidate-a",
    protocol="tls13",
    timeout=8,
    deadline=time.monotonic() + 30,
    attempt=1,
)
check(roomy is None, "sufficient Stage-70 budget was rejected")


# Stage 80 refuses a new candidate before launch when the action envelope cannot fit,
# persists a structured partial result, and returns timeout status to the stage adapter.
with tempfile.TemporaryDirectory() as temp_dir:
    temp = Path(temp_dir)
    output = temp / "extended.json"
    endpoint = temp / "endpoints.txt"
    endpoint.write_text("example.test\n", encoding="utf-8")
    calls = {"candidate": 0, "field": ""}

    original_main = late.extended_orchestration.main
    original_candidate = late.extended_orchestration._candidate
    original_persist = late.search_orchestration._persist_partial_result
    original_record = late.telemetry.record

    def fake_candidate(*args, **kwargs):
        calls["candidate"] += 1
        return {"all_pass": False}

    def fake_main(args):
        output.write_text('{"protocols":{}}\n', encoding="utf-8")
        late.extended_orchestration._candidate(
            "job.Test01",
            endpoint,
            temp / "candidate.json",
            "extended-a",
            "fake",
            temp / "strategy.args",
            "1",
            runner=temp / "runner",
            timeout=8,
            protocol="tls12",
            port="443",
            l7="tls",
        )
        return 0

    def fake_persist(job_id, field, path, value):
        calls["field"] = field
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    late.extended_orchestration.main = fake_main
    late.extended_orchestration._candidate = fake_candidate
    late.search_orchestration._persist_partial_result = fake_persist
    late.telemetry.record = lambda *args, **kwargs: None
    try:
        os.environ["STRATEGY_LAB_OPERATION_TIMEOUT"] = "1"
        status = late.run_extended(["tcp", "job.Test01", str(endpoint), str(output)])
        value = json.loads(output.read_text(encoding="utf-8"))
        check(status == late.EX_TIMEOUT, "Stage 80 did not return timeout after admission rejection")
        check(calls["candidate"] == 0, "Stage 80 launched a candidate without enough parent budget")
        check(calls["field"] == "extended", "Stage 80 partial result was not persisted")
        check(value["partial"] is True, "Stage 80 partial flag is missing")
        check(value["stopped_reason"] == "insufficient_stage_budget", "Stage 80 stop reason is incorrect")

        output.unlink()
        os.environ["STRATEGY_LAB_OPERATION_TIMEOUT"] = "30"
        status = late.run_extended(["tcp", "job.Test01", str(endpoint), str(output)])
        check(status == 0, "Stage 80 rejected a candidate with sufficient parent budget")
        check(calls["candidate"] == 1, "Stage 80 did not launch an admitted candidate")
    finally:
        os.environ.pop("STRATEGY_LAB_OPERATION_TIMEOUT", None)
        late.extended_orchestration.main = original_main
        late.extended_orchestration._candidate = original_candidate
        late.search_orchestration._persist_partial_result = original_persist
        late.telemetry.record = original_record

print("PASS: Strategy Lab late-stage candidate admission and parent bounds")
PY
