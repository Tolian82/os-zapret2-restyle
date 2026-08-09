#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
RESULT="${SCRIPT_DIR}/strategy_lab_py/result.py"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
STAGE_ADAPTER="${SCRIPT_DIR}/strategy_lab_python_stage_adapter.sh"
RESULT_RUNNER="${SCRIPT_DIR}/strategy_lab_result_runner.sh"
PROFILE_ADAPTER="${SCRIPT_DIR}/strategy_lab_profile_candidate_adapter.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }

"${PYTHON}" -m py_compile "${RESULT}" "${SCRIPT_DIR}/strategy_lab_py/endpoint_epoch.py" ||
    fail 'result/search-epoch modules do not compile under Python 3.13'
grep -Fq 'strategy_lab_python_stage_adapter.sh' "${WORKER}" || fail 'production worker does not route final stages through Python'
grep -Fq '85)' "${STAGE_ADAPTER}" || fail 'Python stage adapter does not own Stage 85 routing'
grep -Fq 'result "$@"' "${RESULT_RUNNER}" || fail 'result runner is not a thin Python launcher'
grep -Fq 'STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER="${PROFILE_ADAPTER}"' "${RESULT_RUNNER}" || fail 'profile replay does not select the exact-profile system adapter'
grep -Fq 'prepare-profile' "${PROFILE_ADAPTER}" && fail 'profile adapter unexpectedly created a second candidate command surface'
grep -Fq 'prepare)' "${PROFILE_ADAPTER}" && fail 'profile adapter still owns standard candidate preparation policy'
grep -Fq 'prepare-protocol)' "${PROFILE_ADAPTER}" && fail 'profile adapter still owns protocol candidate preparation policy'
grep -Fq 'exec /bin/sh "${BASE_ADAPTER}" "$@"' "${PROFILE_ADAPTER}" || fail 'profile adapter does not delegate lifecycle/readiness/firewall actions to the unified candidate adapter'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-final-results.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/jobs/job.test"
export STRATEGY_LAB_JOBS_DIR="${TMP}/jobs"
export STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER="${PROFILE_ADAPTER}"
export PYTHONPATH="${SCRIPT_DIR}"

cat > "${TMP}/test.py" <<'PY'
import json
import os
from pathlib import Path

from strategy_lab_py import endpoint_epoch, result

job = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / "job.test"
status = {
    "schema":2,"revision":0,"job_id":"job.test","state":"running","outcome":"",
    "target":"example.com","target_type":"domain","mode":"extended","language":"en",
    "restoration":{},
    "stages":[{"number":n,"status":"PENDING","message":""} for n in ["00","10","20","30","40","50","60","70","80","85","90","99"]],
}
(job / "status.json").write_text(json.dumps(status)+"\n", encoding="utf-8")
(job / "endpoints.txt").write_text("example.com\n", encoding="utf-8")
epoch = endpoint_epoch.create(
    job,
    "example.com",
    "domain",
    ["example.com"],
    [{"endpoint":"example.com","dns_a":{"classification":"pass","answers":["203.0.113.10"]}}],
)
(job / "udp-payload.bin").write_bytes(b"ping")
(job / "stability.json").write_text(json.dumps({"search_epoch_id":epoch.epoch_id,"candidates":[
    {"id":"t1","family":"multisplit","strategy":"--out-range=-d8\n--lua-desync=multisplit:pos=1\n","search_epoch_id":epoch.epoch_id,"stable":True,"line_count":2,"character_count":47},
    {"id":"t2","family":"multidisorder","strategy":"--lua-desync=multidisorder:pos=1\n","search_epoch_id":epoch.epoch_id,"stable":True,"line_count":1,"character_count":35},
    {"id":"t3","family":"fake","strategy":"--out-range=-d10\n--lua-desync=fake:blob=fake_default_tls\n","search_epoch_id":epoch.epoch_id,"stable":True,"line_count":2,"character_count":58},
]})+"\n", encoding="utf-8")
(job / "extended-tcp.json").write_text(json.dumps({"protocols":{
    "tls12":{"working":{"id":"x12","family":"multisplit","strategy":"--out-range=-d10\n--lua-desync=multisplit:pos=2\n","search_epoch_id":epoch.epoch_id,"endpoints":[{"selected_ip":"203.0.113.10"}],"all_pass":True}},
    "http":{"working":{"id":"xh","family":"multidisorder","strategy":"--lua-desync=multidisorder:pos=2\n","search_epoch_id":epoch.epoch_id,"endpoints":[{"selected_ip":"203.0.113.10"}],"all_pass":True}},
}})+"\n", encoding="utf-8")
(job / "quic.json").write_text(json.dumps({"working":{"id":"xq","family":"fake","strategy":"--lua-desync=fake:blob=fake_quic\n","search_epoch_id":epoch.epoch_id,"endpoints":[{"selected_ip":"203.0.113.10"}],"all_pass":True}})+"\n", encoding="utf-8")
(job / "udp.json").write_text(json.dumps({"port":5555,"working":{"id":"xu","family":"ipfrag","strategy":"--lua-desync=ipfrag:udp=8\n","search_epoch_id":epoch.epoch_id,"endpoints":[{"selected_ip":"203.0.113.10"}],"all_pass":True}})+"\n", encoding="utf-8")

calls = []
def replay(job_id, endpoints_file, result_file, candidate_id, family, strategy_file, use_hostlist):
    profile = Path(strategy_file).read_text(encoding="utf-8")
    protocol = os.environ.get("STRATEGY_LAB_CANDIDATE_PROTOCOL", "tls13")
    selected = "203.0.113.10"
    calls.append((candidate_id, protocol, profile, os.environ.get("STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER", "")))
    Path(result_file).write_text(json.dumps({
        "id":candidate_id,"family":family,"strategy":profile,
        "search_epoch_id":epoch.epoch_id,
        "endpoints":[{"endpoint":"example.com","selected_ip":selected,"remote_ip":selected,"status":"PASS"}],
        "all_pass":True,
    })+"\n", encoding="utf-8")
    return 0

result.candidate.run_candidate = replay
shortlist = result.build_shortlist("job.test")
assert shortlist["search_epoch_id"] == epoch.epoch_id
assert shortlist["count"] == 3
assert [item["protocol"] for item in shortlist["items"]] == ["tls13","tls12","http"]
assert shortlist["circular_count"] == 3
assert len(calls) == 21
assert all(item["profile_replay"]["verified"] for item in shortlist["items"])
assert all(item["profile_replay"]["attempt_count"] == 3 for item in shortlist["items"])
assert all(item["profile_replay"]["pass_count"] == 3 for item in shortlist["items"])
assert "--hostlist-domains=example.com" in shortlist["recommendation"]["profile"]
assert any(candidate_id == "t1" and "--out-range=-d8" in profile for candidate_id, _, profile, _ in calls)
assert any(candidate_id == "t2" and "--out-range=" not in profile for candidate_id, _, profile, _ in calls)
assert any(candidate_id == "t3" and "--out-range=-d10" in profile for candidate_id, _, profile, _ in calls)
assert any(protocol == "http" and "--out-range=" not in profile for _, protocol, profile, _ in calls)
udp_profile = next(profile for _, protocol, profile, _ in calls if protocol == "udp")
assert "--filter-udp=5555" in udp_profile
assert "--ipset-ip=203.0.113.10" in udp_profile
assert "--filter-l7=" not in udp_profile
assert all(adapter.endswith("strategy_lab_profile_candidate_adapter.sh") for *_, adapter in calls)

try:
    result.build_profile("example.com", "domain", "tls13", 443, "", "--port=9989\n--lua-desync=multisplit:pos=1\n")
except result.ResultError:
    pass
else:
    raise AssertionError("runtime-only profile argument was accepted")

status = json.loads((job / "status.json").read_text(encoding="utf-8"))
for stage in status["stages"]:
    if stage["number"] in {"85","90"}:
        stage["status"] = "PASS"
status["restoration"] = {"verified":True}
(job / "status.json").write_text(json.dumps(status)+"\n", encoding="utf-8")
eligible, reason, count = result.circular_eligibility("job.test", "completed", "SUCCESS")
assert eligible is True and reason == "eligible" and count == 3
persisted = json.loads((job / "status.json").read_text(encoding="utf-8"))
assert persisted["circular_eligible"] is True
assert persisted["circular_eligibility_reason"] == "eligible"
assert persisted["circular_candidate_count"] == 3
PY

"${PYTHON}" "${TMP}/test.py" || fail 'Python final result regression failed'
sh -n "${STAGE_ADAPTER}"
sh -n "${RESULT_RUNNER}"
sh -n "${PROFILE_ADAPTER}"

echo 'PASS: Python 3.13 owns final profile construction, exact three-pass replay, unified shortlist publication, and automated-job circular eligibility'
