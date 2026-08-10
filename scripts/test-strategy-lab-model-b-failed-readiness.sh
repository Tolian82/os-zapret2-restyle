#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
MODEL_B="${SCRIPT_DIR}/strategy_lab_py/model_b.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"
"${PYTHON}" -m py_compile "${MODEL_B}"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-model-b-readiness.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
export MODEL_B_TEST_ROOT="${ROOT_DIR}"
export MODEL_B_TEST_TMP="${TMP}"

"${PYTHON}" <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

root = Path(os.environ["MODEL_B_TEST_ROOT"])
tmp = Path(os.environ["MODEL_B_TEST_TMP"])
script_dir = root / "src/opnsense/scripts/OPNsense/Zapret"
import sys
sys.path.insert(0, str(script_dir))

from strategy_lab_py import model_b

session = tmp / "session"
report = tmp / "model-b.json"
os.environ["STRATEGY_LAB_MODEL_B_SESSION_DIR"] = str(session)

status = {
    "target": "example.test",
    "mode": "standard",
    "restoration": {"initial_state": "RUNNING"},
}
inventory = SimpleNamespace(inventory_id="ri1-readiness")
binding = {
    "endpoint": "example.test",
    "selected_ip": "203.0.113.10",
    "epoch_id": "se1-readiness",
}
selected = {slot.name: {"classification": "pass"} for slot in model_b.SLOTS}
workers = {
    slot.name: {
        "slot": slot.name,
        "expected_classification": "pass",
    }
    for slot in model_b.SLOTS
}
pool = {
    "pass": {
        "worker": "pass",
        "pid": 5101,
        "divert_port": 9990,
        "process_identity": True,
        "socket_ready": True,
        "log_clean": True,
        "rss_kb": 4300,
        "ready": True,
    },
    "builtin": {
        "worker": "builtin",
        "pid": None,
        "divert_port": 9991,
        "process_identity": False,
        "socket_ready": False,
        "log_clean": False,
        "rss_kb": None,
        "ready": False,
    },
    "external": {
        "worker": "external",
        "pid": 5103,
        "divert_port": 9992,
        "process_identity": True,
        "socket_ready": True,
        "log_clean": True,
        "rss_kb": 4310,
        "ready": True,
    },
}

required_actions: list[str] = []
cleanup_actions: list[str] = []

def fake_require(action: str, *args: str, timeout: int = 15) -> str:
    del args, timeout
    required_actions.append(action)
    if action == "wan":
        return "wan0\n"
    if action in {"preflight", "launch"}:
        return ""
    raise AssertionError(f"unexpected downstream adapter action after failed readiness: {action}")

def fake_try(action: str, *args: str, timeout: int = 15) -> bool:
    del args, timeout
    cleanup_actions.append(action)
    if action == "cleanup-all":
        return True
    raise AssertionError(f"unexpected best-effort adapter action: {action}")

with mock.patch.object(model_b, "_reference_contract", return_value=(status, inventory, binding, selected)), \
     mock.patch.object(model_b, "_current_inventory", return_value=inventory), \
     mock.patch.object(model_b, "_write_worker_runtime", side_effect=lambda slot, *_: workers[slot.name]), \
     mock.patch.object(model_b, "_require_adapter", side_effect=fake_require), \
     mock.patch.object(model_b, "_wait_pool_ready", return_value=pool), \
     mock.patch.object(model_b, "_try_adapter", side_effect=fake_try), \
     mock.patch.object(model_b, "_probe", side_effect=AssertionError("probe executed after failed readiness")), \
     mock.patch.object(model_b, "_all_survivors_ready", side_effect=AssertionError("survivor check executed after failed readiness")):
    rc = model_b.run("job.READY1", str(report))

assert rc == 0
value = json.loads(report.read_text(encoding="utf-8"))
assert value["conclusion"] == "reject", value
assert value["preliminary_accept"] is False
assert value["checks"]["all_workers_ready"] is False
assert value["checks"]["unique_worker_identity"] is False
assert value["checks"]["rss_observed"] is False
assert value["error"] == "Model B worker pool did not reach readiness"
assert value["failed_readiness"] == {
    "failed_slots": ["builtin"],
    "downstream_actions_skipped": True,
}
assert "probes" not in value
assert "independent_stop" not in value
assert "controlled_worker_death" not in value
assert "timing" not in value
assert value["experiment_cleanup_requested"] is True
assert required_actions == ["wan", "preflight", "launch", "launch", "launch"], required_actions
assert cleanup_actions == ["cleanup-all"], cleanup_actions
assert not any(
    action in {"route-add", "route-del", "counter", "rule-present", "stop", "kill-owned"}
    for action in required_actions
), required_actions
PY

sh -n "$0"
echo 'PASS: Model B failed pool readiness rejects immediately, skips probes/stop/death, and still requests bounded cleanup'
