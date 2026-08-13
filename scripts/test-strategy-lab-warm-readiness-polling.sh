#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
MODULE_ROOT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"

PYTHONPATH="${MODULE_ROOT}" "${PYTHON_BIN}" - <<'PY'
from strategy_lab_py import model_b

assert model_b.READY_TIMEOUT_SECONDS == 4.0
assert model_b.READY_POLL_SECONDS == 0.025
assert model_b.READY_STABLE_CHECKS == 2

slot = model_b.Slot("fixture", 9990, 19128, "fixture")
original_snapshot = model_b._snapshot
original_monotonic = model_b.time.monotonic
original_sleep = model_b.time.sleep


def run_case(sequence):
    clock = {"now": 0.0}
    sleeps = []
    calls = {"count": 0}

    def fake_monotonic():
        return clock["now"]

    def fake_sleep(value):
        sleeps.append(float(value))
        clock["now"] += float(value)

    def fake_snapshot(_slot):
        index = calls["count"]
        calls["count"] += 1
        good = sequence[index] if index < len(sequence) else sequence[-1]
        return {
            "process_identity": good,
            "socket_ready": good,
            "log_clean": good,
            "rss_kb": 4360,
            "divert_port": 9990,
        }

    model_b._snapshot = fake_snapshot
    model_b.time.monotonic = fake_monotonic
    model_b.time.sleep = fake_sleep
    try:
        result = model_b._wait_pool_ready((slot,))
    finally:
        model_b._snapshot = original_snapshot
        model_b.time.monotonic = original_monotonic
        model_b.time.sleep = original_sleep
    return result, sleeps, calls["count"], clock["now"]


ready, sleeps, calls, elapsed = run_case([True, True])
assert ready["fixture"]["ready"] is True
assert ready["fixture"]["stable_checks"] == 2
assert calls == 2
assert sleeps == [0.025]
assert elapsed == 0.025

transient, sleeps, calls, elapsed = run_case([True, False, True, True])
assert transient["fixture"]["ready"] is True
assert transient["fixture"]["stable_checks"] == 2
assert calls == 4
assert sleeps == [0.025, 0.025, 0.025]
assert elapsed == 0.07500000000000001 or abs(elapsed - 0.075) < 1e-12

timeout, sleeps, calls, elapsed = run_case([False])
assert timeout["fixture"]["ready"] is False
assert timeout["fixture"]["stable_checks"] == 0
assert calls > 100
assert 3.999 <= elapsed <= 4.001
assert sleeps
assert max(sleeps) <= 0.0250001
assert all(value > 0 for value in sleeps)
PY

echo 'PASS: warm-worker readiness keeps two stable snapshots and a four-second bound while polling at 25 ms instead of one-second cadence'
