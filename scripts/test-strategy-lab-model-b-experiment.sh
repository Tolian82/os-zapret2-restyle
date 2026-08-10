#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
MODEL_B="${SCRIPT_DIR}/strategy_lab_py/model_b.py"
ADAPTER="${SCRIPT_DIR}/strategy_lab_model_b_adapter.sh"
WORKER="${SCRIPT_DIR}/strategy_lab_model_b_worker.sh"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_model_b.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"

"${PYTHON}" -m py_compile "${MODEL_B}" "${SCRIPT_DIR}/strategy_lab_py/compat.py"
sh -n "${ADAPTER}"
sh -n "${WORKER}"
sh -n "${LAUNCHER}"

# Experiment isolation is intentionally static and narrow: no normal candidate cleanup,
# no normal 9989 divert endpoint, and no source-port/parallel dispatch mechanism.
grep -Fq 'MODEL_B_RULES="19128 19129 19130"' "${ADAPTER}" || fail 'Model B dedicated rules changed'
grep -Fq 'MODEL_B_PORTS="9990 9991 9992"' "${ADAPTER}" || fail 'Model B dedicated ports changed'
if grep -Fq 'strategy_lab_firewall_remove_rules' "${ADAPTER}"; then
    fail 'Model B adapter must not remove the normal Strategy Lab rule range'
fi
grep -Fq '9>"${LIFECYCLE_LOCK_FILE}"' "${LAUNCHER}" || fail 'Model B launcher does not own the shared lifecycle lock'
grep -Fq 'STRATEGY_LAB_LIFECYCLE_OWNER=1' "${LAUNCHER}" || fail 'Model B launcher does not establish lifecycle ownership'
grep -Fq 'parallel_probes": False' "${MODEL_B}" || fail 'Model B experiment no longer declares sequential probing'
grep -Fq 'production_approved": False' "${MODEL_B}" || fail 'Model B experiment accidentally claims production approval'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-model-b.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
export MODEL_B_TEST_ROOT="${ROOT_DIR}"
export MODEL_B_TEST_TMP="${TMP}"

"${PYTHON}" <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

root = Path(os.environ["MODEL_B_TEST_ROOT"])
tmp = Path(os.environ["MODEL_B_TEST_TMP"])
script_dir = root / "src/opnsense/scripts/OPNsense/Zapret"
import sys
sys.path.insert(0, str(script_dir))

from strategy_lab_py import candidate_spec, model_b, request, resources

jobs = tmp / "jobs"
job_id = "job.MODELB1"
job = jobs / job_id
for path in (
    job / "family-screening",
    job / "parameter-expansion",
    job / "stability/1-attempts",
):
    path.mkdir(parents=True, exist_ok=True)

lua = tmp / "lua"
fake = tmp / "fake"
lua.mkdir(); fake.mkdir()
(lua / "zapret-lib.lua").write_text("-- lib\n", encoding="utf-8")
(lua / "zapret-antidpi.lua").write_text("-- antidpi\n", encoding="utf-8")
(fake / "fake_tls_7.bin").write_bytes(b"x" * 64)
inventory = resources.snapshot_inventory(lua, fake)
(job / "resource-inventory.json").write_text(json.dumps(inventory.to_dict()), encoding="utf-8")

status = {
    "job_id": job_id,
    "target": "example.test",
    "target_type": "domain",
    "mode": "standard",
    "state": "completed",
    "outcome": "SUCCESS",
    "restoration": {
        "verified": True,
        "initial_state": "RUNNING",
        "final_state": "RUNNING",
        "strategy_unchanged": True,
        "temporary_runtime_clean": True,
    },
}
(job / "status.json").write_text(json.dumps(status), encoding="utf-8")
(job / "search-epoch.json").write_text(json.dumps({
    "schema": 1,
    "epoch_id": "se1-modelbfixture",
    "generation": 1,
    "bindings": [{
        "index": 1,
        "endpoint": "example.test",
        "addresses": ["203.0.113.10"],
        "selected_ip": "203.0.113.10",
    }],
}), encoding="utf-8")

pass_spec = candidate_spec.CandidateSpec.from_strategy(
    candidate_id="pass-blobfree", family="seqovl", protocol="tls13", transport="tcp",
    port=443, l7="tls", target_binding=True,
    strategy="--out-range=-d10\n--lua-desync=multisplit:pos=1",
)
builtin_spec = candidate_spec.CandidateSpec.from_strategy(
    candidate_id="fail-builtin", family="fake", protocol="tls13", transport="tcp",
    port=443, l7="tls", target_binding=True,
    strategy="--out-range=-d10\n--lua-desync=fake:blob=fake_default_tls",
)
external_spec = candidate_spec.CandidateSpec.from_strategy(
    candidate_id="fail-external", family="fake", protocol="tls13", transport="tcp",
    port=443, l7="tls", target_binding=True,
    strategy="--blob=fake_tls_7\n--out-range=-d8\n--lua-desync=fake:blob=fake_tls_7",
)

def write_candidate(path: Path, spec: candidate_spec.CandidateSpec, passed: bool) -> None:
    value = {
        "id": spec.candidate_id,
        "family": spec.family,
        "all_pass": passed,
        "candidate_spec": spec.to_dict(),
        "resource_inventory_id": inventory.inventory_id,
        "search_epoch_id": "se1-modelbfixture",
    }
    path.write_text(json.dumps(value), encoding="utf-8")

write_candidate(job / "family-screening/pass.json", pass_spec, True)
write_candidate(job / "family-screening/builtin.json", builtin_spec, False)
write_candidate(job / "parameter-expansion/external.json", external_spec, False)
for index in range(1, 4):
    write_candidate(job / f"stability/1-attempts/{index}.json", pass_spec, True)

session = tmp / "session"
session.mkdir()
report = tmp / "model-b.json"
os.environ["STRATEGY_LAB_JOBS_DIR"] = str(jobs)
os.environ["STRATEGY_LAB_MODEL_B_SESSION_DIR"] = str(session)

class FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

running: dict[str, bool] = {slot.name: False for slot in model_b.SLOTS}
active_rules: dict[int, int] = {}
counter_calls: dict[int, int] = {}
ports = {slot.name: slot.port for slot in model_b.SLOTS}
pids = {slot.name: 5000 + index for index, slot in enumerate(model_b.SLOTS)}

def fake_adapter(action: str, *args: str, timeout: int = 15):
    del timeout
    if action == "wan":
        return FakeCompleted(stdout="wan0\n")
    if action in {"preflight", "cleanup-all"}:
        if action == "cleanup-all":
            active_rules.clear()
        return FakeCompleted()
    if action == "launch":
        worker, port = args
        assert int(port) == ports[worker]
        running[worker] = True
        return FakeCompleted()
    if action == "snapshot":
        worker, port = args
        alive = running[worker]
        payload = {
            "worker": worker,
            "pid": pids[worker] if alive else None,
            "divert_port": int(port),
            "process_identity": alive,
            "socket_ready": alive,
            "log_clean": True,
            "rss_kb": 4300 + (int(port) - 9990) * 10 if alive else None,
        }
        return FakeCompleted(stdout=json.dumps(payload))
    if action == "route-add":
        rule, port, _address, _wan, transport, dport = args
        assert transport == "tcp" and dport == "443"
        active_rules[int(rule)] = int(port)
        counter_calls[int(rule)] = 0
        return FakeCompleted()
    if action == "route-del":
        active_rules.pop(int(args[0]), None)
        return FakeCompleted()
    if action == "rule-present":
        return FakeCompleted(returncode=0 if int(args[0]) in active_rules else 1)
    if action == "counter":
        rule = int(args[0])
        counter_calls[rule] = counter_calls.get(rule, 0) + 1
        return FakeCompleted(stdout=("0 0\n" if counter_calls[rule] % 2 else "1 100\n"))
    if action == "stop":
        worker, _port = args
        running[worker] = False
        return FakeCompleted()
    if action == "kill-owned":
        worker, _port = args
        running[worker] = False
        return FakeCompleted()
    raise AssertionError((action, args))

def fake_curl(endpoint: str, **kwargs):
    assert endpoint == "example.test"
    active_port = next(iter(active_rules.values()))
    passed = active_port == 9990
    return request.CommandResult(
        command=["curl"],
        returncode=0 if passed else 28,
        stdout="remote_ip=203.0.113.10\n" if passed else "",
        stderr="" if passed else "timeout",
        timed_out=False,
        termination="completed",
        signal=None,
        duration_ms=10,
    )

with mock.patch.object(model_b, "_adapter", side_effect=fake_adapter), \
     mock.patch.object(model_b.resources, "snapshot_inventory", return_value=inventory), \
     mock.patch.object(model_b.request, "curl_request", side_effect=fake_curl), \
     mock.patch.object(model_b.time, "sleep", return_value=None):
    rc = model_b.run(job_id, str(report))
assert rc == 0
value = json.loads(report.read_text(encoding="utf-8"))
assert value["model"] == "B-warm-worker-coexistence"
assert value["experiment_only"] is True
assert value["parallel_probes"] is False
assert value["production_approved"] is False
assert value["preliminary_accept"] is True, value
assert value["conclusion"] == "pending_restoration"
assert all(value["checks"][name] is True for name in value["required_checks"])
assert value["pool"]["rss"]["all_numeric"] is True
assert value["pool"]["rss"]["aggregate_kb"] == 12930
assert [item["slot"] for item in value["probes"]] == ["pass", "builtin", "external", "pass"]
assert [item["classification"] for item in value["probes"]] == ["pass", "fail", "fail", "pass"]
assert value["independent_stop"]["survivors_ready"] is True
assert value["controlled_worker_death"]["dead_worker_absent"] is True
assert value["controlled_worker_death"]["survivor_ready"] is True

initial = tmp / "initial.json"
final = tmp / "final.json"
evidence = {
    "state": "RUNNING",
    "effective_config_hash": "cfg",
    "runtime_args_hash": "args",
    "normal_firewall_hash": "fw",
}
initial.write_text(json.dumps(evidence), encoding="utf-8")
final.write_text(json.dumps(evidence), encoding="utf-8")
assert model_b.finalize(str(report), str(initial), str(final), "1") == 0
value = json.loads(report.read_text(encoding="utf-8"))
assert value["conclusion"] == "accept"
assert value["checks"]["restoration_verified"] is True
assert value["restoration"]["temporary_runtime_clean"] is True
assert value["production_approved"] is False

# A semantic-restoration mismatch must reject the experiment even after a successful
# coexistence phase.
value["preliminary_accept"] = True
report.write_text(json.dumps(value), encoding="utf-8")
bad = dict(evidence); bad["normal_firewall_hash"] = "changed"
final.write_text(json.dumps(bad), encoding="utf-8")
assert model_b.finalize(str(report), str(initial), str(final), "1") == 0
value = json.loads(report.read_text(encoding="utf-8"))
assert value["conclusion"] == "reject"
assert value["checks"]["restoration_verified"] is False
PY

sh -n "$0"
echo 'PASS: Model B experiment keeps three warm workers isolated, probes sequentially, matches Model A outcomes, measures RSS, survives independent stop/death, and requires semantic restoration'
