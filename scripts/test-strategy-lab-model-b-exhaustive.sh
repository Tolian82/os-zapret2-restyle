#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
MODULE="${SCRIPT_DIR}/strategy_lab_py/model_b_exhaustive.py"
WORKER="${SCRIPT_DIR}/strategy_lab_model_b_exhaustive_worker.sh"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_model_b_exhaustive.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"

"${PYTHON}" -m py_compile "${MODULE}" "${SCRIPT_DIR}/strategy_lab_py/compat.py"
sh -n "${WORKER}"
sh -n "${LAUNCHER}"
grep -Fq 'model-b-exhaustive run' "${WORKER}" || fail 'exhaustive worker does not invoke the exhaustive Python path'
grep -Fq '9>"${LIFECYCLE_LOCK_FILE}"' "${LAUNCHER}" || fail 'exhaustive launcher does not own the shared lifecycle lock'
grep -Fq 'parallel_probes": False' "${MODULE}" || fail 'exhaustive benchmark must remain sequential'
grep -Fq 'production_approved": False' "${MODULE}" || fail 'exhaustive benchmark accidentally claims production approval'
grep -Fq 'range(0, len(records), len(BATCH_SLOTS))' "${MODULE}" || fail 'exhaustive benchmark no longer batches the complete corpus'
grep -Fq 'observed_ids == expected_ids' "${MODULE}" || fail 'exhaustive benchmark no longer proves exact corpus order'
grep -Fq 'all_reference_endpoints_replayed' "${MODULE}" || fail 'exhaustive benchmark no longer proves complete endpoint replay'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-model-b-exhaustive.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
export MODEL_B_EXHAUSTIVE_TEST_ROOT="${ROOT_DIR}"
export MODEL_B_EXHAUSTIVE_TEST_TMP="${TMP}"

"${PYTHON}" <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

root = Path(os.environ["MODEL_B_EXHAUSTIVE_TEST_ROOT"])
tmp = Path(os.environ["MODEL_B_EXHAUSTIVE_TEST_TMP"])
script_dir = root / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(script_dir))

from strategy_lab_py import candidate_spec, model_b, model_b_exhaustive, request, resources

jobs = tmp / "jobs"
job_id = "job.EXHAUS1"
job = jobs / job_id
job.mkdir(parents=True)
lua = tmp / "lua"; fake = tmp / "fake"
lua.mkdir(); fake.mkdir()
(lua / "zapret-lib.lua").write_text("-- lib\n", encoding="utf-8")
(lua / "zapret-antidpi.lua").write_text("-- antidpi\n", encoding="utf-8")
inventory = resources.snapshot_inventory(lua, fake)
(job / "resource-inventory.json").write_text(json.dumps(inventory.to_dict()), encoding="utf-8")
bindings = [
    {"index": 1, "endpoint": "blocked.test", "addresses": ["203.0.113.20"], "selected_ip": "203.0.113.20"},
    {"index": 2, "endpoint": "web.blocked.test", "addresses": ["203.0.113.21"], "selected_ip": "203.0.113.21"},
]
(job / "search-epoch.json").write_text(json.dumps({
    "schema": 1,
    "epoch_id": "se1-exhaustive",
    "generation": 1,
    "bindings": bindings,
}), encoding="utf-8")
(job / "status.json").write_text(json.dumps({
    "job_id": job_id,
    "target": "blocked.test",
    "target_type": "domain",
    "mode": "standard",
    "state": "completed",
    "outcome": "NO_CANDIDATE",
    "restoration": {
        "verified": True,
        "initial_state": "RUNNING",
        "final_state": "RUNNING",
        "strategy_unchanged": True,
        "temporary_runtime_clean": True,
    },
}), encoding="utf-8")

candidates = []
schedule = []
for index in range(1, 6):
    spec = candidate_spec.CandidateSpec.from_strategy(
        candidate_id=f"candidate-{index}", family="seqovl", protocol="tls13", transport="tcp",
        port=443, l7="tls", target_binding=True,
        strategy=f"--out-range=-d10\n--lua-desync=multisplit:pos={index}:seqovl=1",
    )
    candidates.append({
        "id": spec.candidate_id,
        "family": spec.family,
        "strategy": spec.strategy,
        "all_pass": False,
        "candidate_spec": spec.to_dict(),
        "resource_inventory_id": inventory.inventory_id,
        "search_epoch_id": "se1-exhaustive",
    })
    schedule.append({"sequence": index, "outcome": "fail", "duration_ms": 1400 + index * 10})
(job / "parameter-expansion.json").write_text(json.dumps({
    "search_epoch_id": "se1-exhaustive",
    "completed": 5,
    "candidates": candidates,
    "working": [],
    "failed": [item["id"] for item in candidates],
    "schedule": schedule,
    "stopped_reason": "graph_exhausted",
}), encoding="utf-8")
(job / "timing-telemetry.json").write_text(json.dumps({
    "schema": 1,
    "events": [{"sequence": 1, "phase": "job_total", "duration_ms": 12000}],
}), encoding="utf-8")

session = tmp / "session"
session.mkdir(); session.chmod(0o711)
report = tmp / "exhaustive.json"
os.environ["STRATEGY_LAB_JOBS_DIR"] = str(jobs)
os.environ["STRATEGY_LAB_MODEL_B_SESSION_DIR"] = str(session)

class FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode; self.stdout = stdout; self.stderr = stderr

running = {slot.name: False for slot in model_b_exhaustive.BATCH_SLOTS}
active_rules: dict[int, int] = {}
counter_calls: dict[int, int] = {}
ports = {slot.name: slot.port for slot in model_b_exhaustive.BATCH_SLOTS}
pids = {slot.name: 7000 + index for index, slot in enumerate(model_b_exhaustive.BATCH_SLOTS)}
cleanup_calls = 0
launch_count = 0
route_addresses: list[str] = []
curl_endpoints: list[str] = []

def fake_adapter(action: str, *args: str, timeout: int = 15):
    global cleanup_calls, launch_count
    del timeout
    if action == "wan": return FakeCompleted(stdout="wan0\n")
    if action == "preflight": return FakeCompleted()
    if action == "cleanup-all":
        cleanup_calls += 1
        active_rules.clear()
        for worker in running: running[worker] = False
        return FakeCompleted()
    if action == "launch":
        worker, port = args
        assert int(port) == ports[worker]
        running[worker] = True
        launch_count += 1
        return FakeCompleted()
    if action == "snapshot":
        worker, port = args
        alive = running[worker]
        return FakeCompleted(stdout=json.dumps({
            "worker": worker,
            "pid": pids[worker] if alive else None,
            "divert_port": int(port),
            "process_identity": alive,
            "socket_ready": alive,
            "log_clean": True,
            "rss_kb": 4300 + (int(port) - 9990) * 10 if alive else None,
        }))
    if action == "route-add":
        rule, port, address, _wan, transport, dport = args
        assert transport == "tcp" and dport == "443"
        assert address in {"203.0.113.20", "203.0.113.21"}
        route_addresses.append(address)
        active_rules[int(rule)] = int(port); counter_calls[int(rule)] = 0
        return FakeCompleted()
    if action == "route-del":
        active_rules.pop(int(args[0]), None); return FakeCompleted()
    if action == "rule-present":
        return FakeCompleted(returncode=0 if int(args[0]) in active_rules else 1)
    if action == "counter":
        rule = int(args[0]); counter_calls[rule] = counter_calls.get(rule, 0) + 1
        return FakeCompleted(stdout=("0 0\n" if counter_calls[rule] % 2 else "1 100\n"))
    raise AssertionError((action, args))

def fake_curl(endpoint: str, **kwargs):
    expected_ip = "203.0.113.20" if endpoint == "blocked.test" else "203.0.113.21"
    assert kwargs.get("bound_ip") == expected_ip
    curl_endpoints.append(endpoint)
    return request.CommandResult(
        command=["curl"], returncode=28, stdout="", stderr="timeout",
        timed_out=False, termination="completed", signal=None, duration_ms=10,
    )

with mock.patch.object(model_b, "_adapter", side_effect=fake_adapter), \
     mock.patch.object(model_b.resources, "snapshot_inventory", return_value=inventory), \
     mock.patch.object(model_b.request, "curl_request", side_effect=fake_curl), \
     mock.patch.object(model_b.time, "sleep", return_value=None):
    assert model_b_exhaustive.run(job_id, str(report)) == 0

value = json.loads(report.read_text(encoding="utf-8"))
assert value["model"] == "B-warm-worker-exhaustive-batched"
assert value["batch_size"] == 3
assert value["experiment_only"] is True
assert value["parallel_probes"] is False
assert value["production_approved"] is False
assert value["reference"]["endpoint_count"] == 2
assert [item["endpoint"] for item in value["reference"]["bindings"]] == ["blocked.test", "web.blocked.test"]
assert value["preliminary_accept"] is True, value
assert value["conclusion"] == "pending_restoration"
assert len(value["batches"]) == 2
assert [len(batch["probes"]) for batch in value["batches"]] == [3, 2]
assert [probe["candidate_id"] for probe in value["probes"]] == [f"candidate-{index}" for index in range(1, 6)]
assert all(probe["endpoint_count"] == 2 for probe in value["probes"])
assert all([item["endpoint"] for item in probe["endpoint_probes"]] == ["blocked.test", "web.blocked.test"] for probe in value["probes"])
assert all(probe["classification"] == "fail" for probe in value["probes"])
assert all(probe["equivalent_to_cold_search"] is True for probe in value["probes"])
assert value["checks"]["reference_endpoint_bindings"] is True
assert value["checks"]["all_reference_endpoints_replayed"] is True
assert value["checks"]["corpus_complete"] is True
assert value["checks"]["route_attribution"] is True
assert value["checks"]["cleanup_between_batches"] is True
assert value["timing"]["endpoint_probe_count"] == 10
assert value["timing"]["cold_candidate_runtime_ms"] == sum(1400 + index * 10 for index in range(1, 6))
assert value["timing"]["cold_job_total_ms"] == 12000
assert value["comparison"]["projection_is_measured_full_job"] is False
assert launch_count == 5
assert cleanup_calls >= 4
assert route_addresses.count("203.0.113.20") == 5
assert route_addresses.count("203.0.113.21") == 5
assert curl_endpoints == ["blocked.test", "web.blocked.test"] * 5
for slot in model_b_exhaustive.BATCH_SLOTS:
    hostlist = session / "workers" / slot.name / "hostlist.txt"
    if hostlist.is_file():
        assert hostlist.read_text(encoding="utf-8").splitlines() == ["blocked.test", "web.blocked.test"]

initial = tmp / "initial.json"; final = tmp / "final.json"
evidence = {"state": "RUNNING", "effective_config_hash": "cfg", "runtime_args_hash": "args", "normal_firewall_hash": "fw"}
initial.write_text(json.dumps(evidence), encoding="utf-8")
final.write_text(json.dumps(evidence), encoding="utf-8")
assert model_b_exhaustive.finalize(str(report), str(initial), str(final), "1") == 0
value = json.loads(report.read_text(encoding="utf-8"))
assert value["conclusion"] == "accept"
assert value["checks"]["restoration_verified"] is True
assert value["production_approved"] is False
PY

sh -n "$0"
echo 'PASS: exhaustive Model B benchmark replays a complete graph-exhausted multi-endpoint corpus in exact order with three-worker warm batches, sequential attribution, between-batch cleanup, timing/RSS comparison, and semantic restoration'
