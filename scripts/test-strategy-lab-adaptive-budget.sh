#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-${STRATEGY_LAB_PYTHON_BIN:-python3.13}}
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-adaptive-budget.XXXXXX")
trap 'rm -rf "${TEST_ROOT}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail 'Python 3.13 runtime is unavailable'
"${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)' ||
    fail 'Strategy Lab adaptive-budget test requires Python 3.13'

export STRATEGY_LAB_STANDARD_BUDGET=150
export STRATEGY_LAB_EXTENDED_BUDGET=120
export STRATEGY_LAB_STAGE80_TIMEOUT=120
export STRATEGY_LAB_NOW_EPOCH_FILE="${TEST_ROOT}/clock"
export STRATEGY_LAB_TEST_ROOT="${TEST_ROOT}"
printf '%s\n' 1000 > "${STRATEGY_LAB_NOW_EPOCH_FILE}"

PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path

from strategy_lab_py import adaptive_budget
from strategy_lab_py.orchestrator import Budget, OrchestrationError

root = Path(os.environ["STRATEGY_LAB_TEST_ROOT"])
clock = Path(os.environ["STRATEGY_LAB_NOW_EPOCH_FILE"])


def status_for(job: str, *, endpoints: int, ipv6: bool, quic: bool, udp: bool) -> tuple[Path, Path]:
    job_dir = root / "jobs" / job
    job_dir.mkdir(parents=True, exist_ok=True)
    state = job_dir / "status.json"
    value = {
        "schema": 2,
        "revision": 0,
        "job_id": job,
        "endpoints": [f"endpoint-{index}.example" for index in range(1, endpoints + 1)],
        "network": {
            "ipv4": "available",
            "ipv6": "available" if ipv6 else "unavailable",
            "quic_ipv4": "available" if quic else "closed",
        },
        "udp_request": {"configured": udp, "port": 9999 if udp else None, "payload_bytes": 4 if udp else 0},
    }
    state.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return job_dir, state


# `_25` owner-live topology remains the exact floor: two endpoints, IPv4 only,
# QUIC unavailable and no Generic UDP input.
job_dir, state = status_for("job.ADAPTBASE", endpoints=2, ipv6=False, quic=False, udp=False)
budget = Budget("extended", state, "job.ADAPTBASE")
budget.record_initial()
plan = adaptive_budget.adapt(budget, job_dir=job_dir, state_path=state)
assert plan["policy"] == "eligible-work-v1"
assert plan["additions_seconds"]["standard_total"] == 0
assert plan["additions_seconds"]["extended_total"] == 0
assert plan["effective_seconds"] == {"standard": 150, "extended": 120, "search": 270, "stage80": 120}
value = json.loads(state.read_text(encoding="utf-8"))
assert value["standard_budget_seconds"] == 150
assert value["extended_budget_seconds"] == 120
assert value["search_budget_seconds"] == 270
assert value["stage80_budget_seconds"] == 120
assert value["started_at"] == "1970-01-01T00:16:40Z"
assert value["deadline_at"] == "1970-01-01T00:21:10Z"
assert json.loads((job_dir / "adaptive-budget.json").read_text(encoding="utf-8")) == plan
telemetry = json.loads((job_dir / "timing-telemetry.json").read_text(encoding="utf-8"))
events = [event for event in telemetry["events"] if event.get("phase") == "budget_adaptation"]
assert len(events) == 1 and events[0]["stage"] == "30" and events[0]["details"] == plan

# Every currently optional measured branch extends only its owning finite parent.
clock.write_text("2000\n", encoding="utf-8")
job_dir, state = status_for("job.ADAPTFULL", endpoints=2, ipv6=True, quic=True, udp=True)
budget = Budget("extended", state, "job.ADAPTFULL")
started = budget.started_epoch
plan = adaptive_budget.adapt(budget, job_dir=job_dir, state_path=state)
assert plan["work_matrix"] == {
    "mode": "extended",
    "endpoint_count": 2,
    "ipv4": True,
    "ipv6": True,
    "tls13": True,
    "extended_tcp": True,
    "quic_ipv4": True,
    "generic_udp": True,
}
assert plan["additions_seconds"] == {
    "extra_endpoints_standard": 0,
    "extra_endpoints_extended": 0,
    "ipv6": 10,
    "quic": 20,
    "generic_udp": 15,
    "standard_total": 10,
    "extended_total": 35,
}
assert plan["effective_seconds"] == {"standard": 160, "extended": 155, "search": 315, "stage80": 155}
assert budget.started_epoch == started == 2000
assert budget.standard_deadline == 2160
assert budget.overall_deadline == 2315
clock.write_text("2160\n", encoding="utf-8")
budget.begin_stage80()
assert budget.stage80_deadline == 2315

# Standard mode does not charge QUIC or Generic UDP branches that it cannot execute.
clock.write_text("3000\n", encoding="utf-8")
job_dir, state = status_for("job.ADAPTSTD", endpoints=2, ipv6=True, quic=True, udp=True)
budget = Budget("standard", state, "job.ADAPTSTD")
plan = adaptive_budget.adapt(budget, job_dir=job_dir, state_path=state)
assert plan["work_matrix"]["quic_ipv4"] is False
assert plan["work_matrix"]["generic_udp"] is False
assert plan["effective_seconds"] == {"standard": 160, "extended": 120, "search": 160, "stage80": 120}

# Endpoint growth is bounded and linear rather than an oversized guessed timeout.
clock.write_text("4000\n", encoding="utf-8")
job_dir, state = status_for("job.ADAPTFOUR", endpoints=4, ipv6=False, quic=False, udp=False)
budget = Budget("extended", state, "job.ADAPTFOUR")
plan = adaptive_budget.adapt(budget, job_dir=job_dir, state_path=state)
assert plan["additions_seconds"]["extra_endpoints_standard"] == 60
assert plan["additions_seconds"]["extra_endpoints_extended"] == 30
assert plan["effective_seconds"] == {"standard": 210, "extended": 150, "search": 360, "stage80": 150}

# Recalculation is idempotent: the calibrated base is cached, never compounded.
again = adaptive_budget.calculate_plan(budget, json.loads(state.read_text(encoding="utf-8")))
assert again["effective_seconds"] == plan["effective_seconds"]

# A Stage-30 PASS contract without IPv4 availability cannot manufacture a budget plan.
clock.write_text("5000\n", encoding="utf-8")
job_dir, state = status_for("job.ADAPTBAD", endpoints=1, ipv6=False, quic=False, udp=False)
value = json.loads(state.read_text(encoding="utf-8"))
value["network"]["ipv4"] = "unavailable"
state.write_text(json.dumps(value) + "\n", encoding="utf-8")
budget = Budget("standard", state, "job.ADAPTBAD")
try:
    adaptive_budget.calculate_plan(budget, value)
except OrchestrationError as exc:
    assert "IPv4 network precheck" in str(exc)
else:
    raise AssertionError("adaptive budget accepted an unavailable IPv4 baseline")
PY

grep -Fq 'POLICY = "eligible-work-v1"' "${ZAPRET_DIR}/strategy_lab_py/adaptive_budget.py" ||
    fail 'adaptive budget policy marker is missing'
grep -Fq 'return AdaptiveBudgetOrchestrator(job_id).run()' "${ZAPRET_DIR}/strategy_lab_py/adaptive_budget.py" ||
    fail 'production adaptive orchestrator owner is missing'
grep -Fq 'return adaptive_budget.orchestrator_main(args)' "${ZAPRET_DIR}/strategy_lab_py/compat.py" ||
    fail 'production compatibility route does not use the adaptive budget owner'

echo 'PASS: Strategy Lab derives finite parent budgets from measured endpoint/capability/protocol work while preserving the _25 floor and original job clock'
