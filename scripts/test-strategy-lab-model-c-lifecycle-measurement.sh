#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
MODULE_ROOT="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE="${MODULE_ROOT}/strategy_lab_py/model_c_lifecycle_measurement.py"
ENTRY="${MODULE_ROOT}/strategy_lab_python.py"
WRAPPER="${MODULE_ROOT}/strategy_lab_model_c_lifecycle_measurement.sh"
WORKER="${MODULE_ROOT}/strategy_lab_model_c_lifecycle_measurement_worker.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }
for file in "${MODULE}" "${ENTRY}" "${WRAPPER}" "${WORKER}"; do [ -s "${file}" ] || fail "missing ${file}"; done

PYTHONPATH="${MODULE_ROOT}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import tempfile
import time
from pathlib import Path

import strategy_lab_python as entry
from strategy_lab_py import model_c_lifecycle_measurement as m
from strategy_lab_py import stage60_model_c

assert m.POLICY == "model-c-batch-lifecycle-amortization-v1"
assert m.PRODUCTION_MODEL == stage60_model_c.MODEL
assert m._positive_repeats("3") == 3
assert m._positive_repeats("12") == 12
for raw in ("0", "2", "13", "x"):
    try:
        m._positive_repeats(raw)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid repeat count accepted")

stats = m._stats([10, 20, 30, 40, 50])
assert stats["count"] == 5
assert stats["median"] == 30.0
assert stats["p90"] == 50.0

candidate = {"id": "c1", "all_pass": True}
model_c = {
    "execution_model": m.PRODUCTION_MODEL,
    "candidates": [candidate],
    "working": ["c1"],
    "failed": [],
    "stopped_reason": "catalog_exhausted",
    "partial": False,
    "parallel": {
        "fallbacks": [],
        "batches": [
            {"outcome": "warm", "execution_model": m.PRODUCTION_MODEL, "candidate_ids": ["c1"]},
            {"outcome": "warm", "execution_model": m.PRODUCTION_MODEL, "candidate_ids": ["c2"]},
        ],
    },
}
assert m._model_c_only(model_c) is True
assert m._result_signature(model_c) == {
    "outcomes": [{"id": "c1", "all_pass": True}],
    "working": ["c1"],
    "failed": [],
    "stopped_reason": "catalog_exhausted",
    "partial": False,
}
with_fallback = json.loads(json.dumps(model_c))
with_fallback["parallel"]["fallbacks"] = [{"batch": 1}]
assert m._model_c_only(with_fallback) is False

real_bucket = stage60_model_c._bucket_batch

def fake_bucket(*args, **kwargs):
    time.sleep(0.002)
    return ([candidate], {
        "total_ms": 1,
        "pool_startup_ms": 1,
        "parallel_probe_wall_ms": 0,
        "rss": {"aggregate_kb": 4360, "all_numeric": True},
        "source_port_lease": {"replacement_count": 0},
        "candidate_ids": ["c1"],
        "width": 1,
        "execution_model": m.PRODUCTION_MODEL,
    })

try:
    stage60_model_c._bucket_batch = fake_bucket
    samples = []
    with m._instrument_batches(samples, time.monotonic() - 0.005):
        result, evidence = stage60_model_c._bucket_batch()
    assert result == [candidate]
    assert evidence["execution_model"] == m.PRODUCTION_MODEL
    assert stage60_model_c._bucket_batch is fake_bucket
    assert len(samples) == 1
    sample = samples[0]
    assert sample["candidate_ids"] == ["c1"]
    assert sample["rss_aggregate_kb"] == 4360
    assert sample["rss_all_numeric"] is True
    assert sample["outer_batch_ms"] >= sample["reported_batch_total_ms"]
    assert sample["non_probe_upper_bound_ms"] >= 0
finally:
    stage60_model_c._bucket_batch = real_bucket

# `_7` created these three ancestors as 0700 even though the launched dvtws2 workers
# drop privileges to nobody. The `_8` entry boundary must make only the expected replay
# ancestors execute-traversable (0711) before any Model-C/Model-B/cold runtime starts.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "model-c-lifecycle-measurement"
    session = root / "session.12345"
    runs = session / "runs"
    cleanup = session / "cleanup-runtime"
    cleanup.mkdir(parents=True)
    runs.mkdir()
    for path in (root, session, runs, cleanup):
        path.chmod(0o700)
    previous = os.environ.get("STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR")
    os.environ["STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR"] = str(runs)
    try:
        entry._prepare_model_c_lifecycle_runtime_permissions(["run", "job.reference", "/tmp/out.json", "5"])
    finally:
        if previous is None:
            os.environ.pop("STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR", None)
        else:
            os.environ["STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR"] = previous
    assert (root.stat().st_mode & 0o777) == 0o711
    assert (session.stat().st_mode & 0o777) == 0o711
    assert (runs.stat().st_mode & 0o777) == 0o711
    assert (cleanup.stat().st_mode & 0o777) == 0o700

with tempfile.TemporaryDirectory() as tmp:
    unexpected = Path(tmp) / "wrong" / "session.1" / "runs"
    unexpected.mkdir(parents=True)
    previous = os.environ.get("STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR")
    os.environ["STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR"] = str(unexpected)
    try:
        try:
            entry._prepare_model_c_lifecycle_runtime_permissions(["run"])
        except RuntimeError:
            pass
        else:
            raise AssertionError("unexpected lifecycle measurement directory layout accepted")
    finally:
        if previous is None:
            os.environ.pop("STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR", None)
        else:
            os.environ["STRATEGY_LAB_MODEL_C_LIFECYCLE_MEASUREMENT_DIR"] = previous

assert m._bool_arg("1", "cleanup ok") is True
assert m._bool_arg("true", "cleanup ok") is True
assert m._bool_arg("0", "cleanup ok") is False
assert m._bool_arg("false", "cleanup ok") is False
try:
    m._bool_arg("yes", "cleanup ok")
except ValueError:
    pass
else:
    raise AssertionError("invalid cleanup boolean accepted")

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    output = root / "report.json"
    initial = root / "initial.json"
    final = root / "final.json"
    lifecycle = {"schema": 1, "source": "zapret_service", "state": "RUNNING", "marker": "same"}
    initial.write_text(json.dumps(lifecycle), encoding="utf-8")
    final.write_text(json.dumps(lifecycle), encoding="utf-8")

    checks = {
        "reference_model_c_only": True,
        "multi_batch_reference": True,
        "reference_inventory_match": True,
        "repeat_count_complete": True,
        "model_c_only": True,
        "result_equivalent": True,
        "batch_sequence_equivalent": True,
        "rss_complete": True,
        "lifecycle_restored": False,
        "cleanup_ok": False,
    }
    base = {"checks": checks, "conclusion": "measurement_collected"}
    output.write_text(json.dumps(base), encoding="utf-8")
    assert m.finalize(output, initial, final, True) == 0
    accepted = json.loads(output.read_text(encoding="utf-8"))
    assert accepted["conclusion"] == "measurement_accepted"
    assert accepted["checks"]["lifecycle_restored"] is True
    assert accepted["checks"]["cleanup_ok"] is True

    output.write_text(json.dumps(base), encoding="utf-8")
    assert m.finalize(output, initial, final, False) == 70
    rejected = json.loads(output.read_text(encoding="utf-8"))
    assert rejected["conclusion"] == "measurement_rejected"
PY

grep -Fq 'model-c-lifecycle-measure' "${ENTRY}" || fail 'measurement entry point missing'
grep -Fq '_prepare_model_c_lifecycle_runtime_permissions' "${ENTRY}" || fail 'lifecycle replay traversal corrective missing'
grep -Fq 'path.chmod(0o711)' "${ENTRY}" || fail 'lifecycle replay ancestors are not made execute-traversable'
grep -Fq 'zapret2-lifecycle.lock' "${WRAPPER}" || fail 'lifecycle lock missing'
grep -Fq 'strategy-lab-stop' "${WORKER}" || fail 'normal service stop boundary missing'
grep -Fq 'strategy-lab-start' "${WORKER}" || fail 'normal service restore boundary missing'
grep -Fq 'strategy-lab-evidence' "${WORKER}" || fail 'semantic lifecycle evidence missing'
grep -Fq 'cleanup-all' "${WORKER}" || fail 'reserved Model-C runtime cleanup missing'
grep -Fq 'chmod 0600 "${_output}"' "${WORKER}" || fail 'lifecycle evidence privacy boundary missing'
grep -Fq 'stage60_source_port_lease.install()' "${MODULE}" || fail 'production source-port lease path is not measured'
grep -Fq 'stage60_model_c.expand(' "${MODULE}" || fail 'production Model-C expansion path is not measured'
grep -Fq '"production_model_changed": False' "${MODULE}" || fail 'production Model-C immutability gate missing'
grep -Fq '"production_search_semantics_changed": False' "${MODULE}" || fail 'production search immutability gate missing'
grep -Fq '"production_dispatch_width_changed": False' "${MODULE}" || fail 'production width immutability gate missing'
grep -Fq '"production_change_recommended": False' "${MODULE}" || fail 'measurement-only decision gate missing'

echo 'PASS: Model-C lifecycle measurement is isolated, production-path faithful, lifecycle-owned, cleanup-gated, and production-neutral'