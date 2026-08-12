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
printf '%s\n' 'PASS: discovery probe measurement contract is isolated, lifecycle-owned, and production-neutral'
