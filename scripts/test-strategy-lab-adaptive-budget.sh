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

def status_for(job: str, *, ipv6_on: bool, has_a: bool = True,
               has_aaaa: bool = False, ipv6_route: bool = True,
               target_type: str = "domain", endpoints: int = 2,
               quic: bool = False, udp: bool = False):
    directory = root / "jobs" / job
    directory.mkdir(parents=True, exist_ok=True)
    state = directory / "status.json"
    baseline = []
    for i in range(endpoints):
        endpoint = {"endpoint": f"endpoint-{i+1}.example"}
        if has_a:
            endpoint["ipv4"] = {"status": "FAIL"}
        if has_aaaa and ipv6_on and ipv6_route:
            endpoint["ipv6"] = {"status": "FAIL"}
        else:
            endpoint["ipv6"] = {"status": "SKIPPED"}
        baseline.append(endpoint)
    state.write_text(json.dumps({
        "schema": 2, "revision": 0, "job_id": job,
        "target_type": target_type, "ipv6_enabled": ipv6_on,
        "endpoints": [x["endpoint"] for x in baseline],
        "baseline": {"endpoints": baseline},
        "network": {"ipv4": "available", "ipv6": "available" if ipv6_route else "unavailable",
                    "quic_ipv4": "available" if quic else "closed"},
        "udp_request": {"configured": udp},
    }) + "\n", encoding="utf-8")
    return directory, state

def case(name, mode, expected, **opts):
    directory, state = status_for("job." + name, **opts)
    budget = Budget(mode, state, "job." + name)
    budget.record_initial()
    plan = adaptive_budget.adapt(budget, job_dir=directory, state_path=state)
    assert plan["policy"] == "eligible-families-v2"
    assert plan["effective_seconds"]["search"] == expected, (name, plan)
    assert budget.overall_deadline == budget.started_epoch + expected
    assert budget.standard_deadline == budget.started_epoch + plan["effective_seconds"]["standard"]
    assert json.loads(state.read_text())["search_budget_seconds"] == expected
    assert json.loads((directory / "adaptive-budget.json").read_text()) == plan
    assert adaptive_budget.calculate_plan(budget, json.loads(state.read_text()))["effective_seconds"] == plan["effective_seconds"]
    return plan, budget

# Any ordinary IPv4 or unchecked dual-stack target keeps strict one-family budget.
plan, b = case("OFF", "standard", 150, ipv6_on=False, has_aaaa=True)
assert not plan["work_matrix"]["dual_family"]
case("OFFEXT", "extended", 270, ipv6_on=False, has_aaaa=True)
# Checkbox alone, route alone, AAAA missing, and pure IPv4 literal never earn bonus.
case("CHECKED_NO_AAAA", "extended", 270, ipv6_on=True, has_aaaa=False)
case("NO_ROUTE", "extended", 270, ipv6_on=True, has_aaaa=True, ipv6_route=False)
case("IPV4_IP", "extended", 270, ipv6_on=True, has_aaaa=True, target_type="ip")
# QUIC, UDP or endpoint count must never inflate the overall user limit.
case("EXTRAS", "extended", 270, ipv6_on=False, has_aaaa=False,
     endpoints=4, quic=True, udp=True)
# Only a real selected A+AAAA target earns the two-family increment.
plan, b = case("BOTHSTD", "standard", 200, ipv6_on=True, has_aaaa=True)
assert plan["effective_seconds"]["standard"] == 200
plan, b = case("BOTHEXT", "extended", 350, ipv6_on=True, has_aaaa=True)
assert plan["effective_seconds"] == {
    "standard": 200, "extended": 150, "search": 350, "stage80": 150
}
assert plan["additions_seconds"] == {"standard_total": 50, "extended_total": 30}
assert b.stage80_started is None
clock.write_text(str(b.started_epoch + 200) + "\n")
b.begin_stage80()
assert b.stage80_deadline == b.started_epoch + 350
# Invalid/missing Stage 40 evidence cannot qualify a guessed family.
directory, state = status_for("job.NOBASE", ipv6_on=True, has_aaaa=True)
bad = json.loads(state.read_text())
bad.pop("baseline")
state.write_text(json.dumps(bad))
try:
    adaptive_budget.calculate_plan(Budget("standard", state, "job.NOBASE"), bad)
except OrchestrationError as exc:
    assert "Stage-40" in str(exc)
else:
    raise AssertionError("budget fabricated family coverage without Stage-40 evidence")
# Single AAAA-only families get no mixed-family bonus (IPv4 network
# preflight prerequisite currently remains under Stage 6 migration).
case("AAAAONLY", "extended", 270, ipv6_on=True, has_a=False, has_aaaa=True)
print("PASS: selected actual A/AAAA eligibility controls one immutable 150/200/270/350 job budget")
PY
grep -Fq 'POLICY = "eligible-families-v2"' "${ZAPRET_DIR}/strategy_lab_py/adaptive_budget.py" ||
    fail 'adaptive budget policy marker is missing'
grep -Fq 'return AdaptiveBudgetOrchestrator(job_id).run()' "${ZAPRET_DIR}/strategy_lab_py/adaptive_budget.py" ||
    fail 'production adaptive orchestrator owner is missing'
grep -Fq 'return adaptive_budget.orchestrator_main(args)' "${ZAPRET_DIR}/strategy_lab_py/compat.py" ||
    fail 'production compatibility route does not use the adaptive budget owner'

echo 'PASS: Stage-40 target families select strict 150/200/270/350 overall budgets without duplicated IPv6/QUIC/UDP bonuses'
