#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3}"
MODULE_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE="${MODULE_DIR}/strategy_lab_py/discovery_probe_measurement.py"
ENTRY="${MODULE_DIR}/strategy_lab_python.py"
WRAPPER="${MODULE_DIR}/strategy_lab_discovery_probe_measurement.sh"
WORKER="${MODULE_DIR}/strategy_lab_discovery_probe_measurement_worker.sh"

for file in "${MODULE}" "${ENTRY}" "${WRAPPER}" "${WORKER}"; do [ -s "${file}" ] || { echo "FAIL: missing ${file}" >&2; exit 1; }; done
PYTHONPATH="${MODULE_DIR}" "${PYTHON_BIN}" - <<'PY'
import json
import tempfile
from pathlib import Path

from strategy_lab_py import discovery_probe_measurement as m


def endpoint(status="PASS", code=200, size=4096, intercepted=True, match=True):
    return {
        "status": status,
        "endpoint_match": match,
        "firewall": {"intercepted": intercepted},
        "execution": {"stdout": f"exit=0 remote_ip=192.0.2.1 http=1.1 code={code} bytes={size}\n"},
    }


assert m.POLICY == "discovery-probe-agreement-v1"
assert m.VARIANTS == ("head", "get-1", "get-4k", "deep-16k")
assert m.classify_cheap({"endpoints": [endpoint(size=0)]})["classification"] == "pass"
assert m.classify_cheap({"endpoints": [endpoint(code=503)]})["classification"] == "fail"
assert m.classify_cheap({"endpoints": [endpoint(intercepted=False)]})["classification"] == "inconclusive"

samples=[]
classes={
    "a": {"head":"pass","get-1":"pass","get-4k":"pass","deep-16k":"pass"},
    "b": {"head":"pass","get-1":"fail","get-4k":"fail","deep-16k":"fail"},
}
for candidate_id, values in classes.items():
    for variant, classification in values.items():
        samples.append({"candidate_id":candidate_id,"variant":variant,"classification":classification,"probe_ms":10,"total_ms":20,"bytes_received":1})
summary, comparisons=m.summarize(samples)
assert summary["head"]["probe_ms"]["median"] == 10.0
assert comparisons["head"]["false_pass"] == 1
assert comparisons["get-1"]["false_pass"] == 0
assert comparisons["get-4k"]["agreement"] == 2

assert m._bool_arg("1", "cleanup ok") is True
assert m._bool_arg("true", "cleanup ok") is True
assert m._bool_arg("TRUE", "cleanup ok") is True
assert m._bool_arg("0", "cleanup ok") is False
assert m._bool_arg("false", "cleanup ok") is False
try:
    m._bool_arg("yes", "cleanup ok")
except ValueError:
    pass
else:
    raise AssertionError("invalid cleanup boolean must be rejected")

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    output = root / "report.json"
    initial = root / "initial.json"
    final = root / "final.json"
    lifecycle = {"schema": 1, "source": "zapret_service", "state": "RUNNING", "marker": "same"}
    initial.write_text(json.dumps(lifecycle), encoding="utf-8")
    final.write_text(json.dumps(lifecycle), encoding="utf-8")

    def base_report():
        return {
            "checks": {
                "expected_sample_count": True,
                "single_search_epoch": True,
                "endpoint_attribution_complete": True,
                "lifecycle_restored": False,
                "cleanup_ok": False,
            },
            "conclusion": "measurement_collected",
        }

    output.write_text(json.dumps(base_report()), encoding="utf-8")
    assert m.finalize(output, initial, final, m._bool_arg("1", "cleanup ok")) == 0
    accepted = json.loads(output.read_text(encoding="utf-8"))
    assert accepted["checks"]["cleanup_ok"] is True
    assert accepted["checks"]["lifecycle_restored"] is True
    assert accepted["conclusion"] == "measurement_accepted"

    output.write_text(json.dumps(base_report()), encoding="utf-8")
    assert m.finalize(output, initial, final, m._bool_arg("0", "cleanup ok")) == 70
    rejected = json.loads(output.read_text(encoding="utf-8"))
    assert rejected["checks"]["cleanup_ok"] is False
    assert rejected["checks"]["lifecycle_restored"] is True
    assert rejected["conclusion"] == "measurement_rejected"
PY

grep -Fq 'discovery-probe-measure' "${ENTRY}" || { echo 'FAIL: entry point missing' >&2; exit 1; }
grep -Fq 'zapret2-lifecycle.lock' "${WRAPPER}" || { echo 'FAIL: lifecycle lock missing' >&2; exit 1; }
grep -Fq 'strategy-lab-stop' "${WORKER}" || { echo 'FAIL: normal service stop boundary missing' >&2; exit 1; }
grep -Fq 'strategy-lab-start' "${WORKER}" || { echo 'FAIL: normal service restore boundary missing' >&2; exit 1; }
grep -Fq 'strategy-lab-evidence' "${WORKER}" || { echo 'FAIL: lifecycle evidence missing' >&2; exit 1; }
if grep -Fq 'route-add' "${WORKER}" || grep -Fq 'route-add' "${MODULE}"; then
    echo 'FAIL: discovery measurement must not install an independent traffic route' >&2
    exit 1
fi
grep -Fq 'production_discovery_policy_changed": False' "${MODULE}" || { echo 'FAIL: production immutability evidence missing' >&2; exit 1; }
grep -Fq 'production_change_recommended": False' "${MODULE}" || { echo 'FAIL: no-change measurement gate missing' >&2; exit 1; }
printf '%s\n' 'PASS: discovery probe measurement contract is isolated, lifecycle-owned, cleanup-finalizer-safe, and production-neutral'