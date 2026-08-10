#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
MODULE="${SCRIPT_DIR}/strategy_lab_py/adaptive_validation.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }

"${PYTHON}" -m py_compile "${MODULE}" || fail 'adaptive validation module does not compile under Python 3.13'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-adaptive-validation.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/jobs/job.test" "${TMP}/bin"
printf '#!/bin/sh\nexit 0\n' > "${TMP}/bin/candidate"
chmod 0755 "${TMP}/bin/candidate"

export STRATEGY_LAB_JOBS_DIR="${TMP}/jobs"
export PYTHONPATH="${SCRIPT_DIR}"
export TEST_TMP="${TMP}"

cat > "${TMP}/test.py" <<'PY'
import json
import os
from pathlib import Path

from strategy_lab_py import adaptive_validation as av
from strategy_lab_py import endpoint_epoch, request, search

root = Path(os.environ["TEST_TMP"])
job = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / "job.test"
endpoints = job / "endpoints.txt"
endpoints.write_text("example.com\n", encoding="utf-8")
epoch = endpoint_epoch.create(
    job,
    "example.com",
    "domain",
    ["example.com"],
    [{"endpoint":"example.com","dns_a":{"classification":"pass","answers":["203.0.113.10"]}}],
)

# Discovery and deep validation must be different evidence tiers while preserving
# GET, pinned endpoint/SNI behavior, and finite timeouts.
captured = []
old_binary = request.binary
old_run = request.run_command
request.binary = lambda name: f"/mock/{name}"
def fake_run(command, *, timeout, stdin_devnull=False, stdin_path=None):
    captured.append((list(command), timeout))
    return request.CommandResult(list(command), 0, "", "", False, "completed", None, 1)
request.run_command = fake_run
try:
    with av.probe_tier("discovery"):
        av._tiered_curl_request("example.com", scheme="https", tls_version="1.3", bound_ip="203.0.113.10")
    with av.probe_tier("deep"):
        av._tiered_curl_request("example.com", scheme="https", tls_version="1.3", bound_ip="203.0.113.10")
finally:
    request.binary = old_binary
    request.run_command = old_run

discovery, deep = captured
def option(command, name):
    return command[command.index(name) + 1]
assert option(discovery[0], "--request") == "GET"
assert option(deep[0], "--request") == "GET"
assert option(discovery[0], "--range") == "0-4095"
assert option(deep[0], "--range") == "0-65535"
assert int(option(discovery[0], "--max-time")) < int(option(deep[0], "--max-time"))
assert discovery[1] < deep[1]

# Deep response classification: full body PASS, short successful resource INCONCLUSIVE,
# and HTTP/protocol failure FAIL. Inconclusive remains accepted because Stage 70 owns
# the independent 3/3 connectivity evidence.
def replay(stdout, *, status="PASS", intercepted=True, all_pass=True, exact=True):
    return {
        "all_pass": all_pass,
        "profile_exact": exact,
        "endpoints":[{
            "status":status,
            "firewall":{"intercepted":intercepted},
            "execution":{"stdout":stdout},
        }],
    }
full = av.classify_deep_replay(
    replay("exit=0 remote_ip=203.0.113.10 http=1.1 code=200 bytes=20000\n"),
    "tls13", 16384,
)
short = av.classify_deep_replay(
    replay("exit=0 remote_ip=203.0.113.10 http=1.1 code=200 bytes=4096\n"),
    "tls13", 16384,
)
bad = av.classify_deep_replay(
    replay("exit=0 remote_ip=203.0.113.10 http=1.1 code=503 bytes=100\n"),
    "tls13", 16384,
)
missing = av.classify_deep_replay(
    {"all_pass":True,"profile_exact":True,"endpoints":[{"status":"PASS","firewall":{"intercepted":True}}]},
    "tls13", 16384,
)
assert full["classification"] == "pass" and full["accepted"] is True
assert short["classification"] == "inconclusive" and short["accepted"] is True
assert missing["classification"] == "inconclusive" and missing["accepted"] is True
assert bad["classification"] == "fail" and bad["accepted"] is False

# Stage 70 must actually stop an impossible 3/3 after the first failure. Candidate c1
# is PASS/FAIL and must consume two attempts, not three. Candidate c2 is 3/3 PASS.
family_path = job / "family.json"
expansion_path = job / "expansion.json"
stability_path = job / "stability.json"
family_path.write_text(json.dumps({"search_epoch_id":epoch.epoch_id,"families":[]})+"\n", encoding="utf-8")
expansion_path.write_text(json.dumps({
    "search_epoch_id":epoch.epoch_id,
    "candidates":[
        {"id":"c1","family":"multisplit","strategy":"--lua-desync=multisplit:pos=1\n","all_pass":True,"search_epoch_id":epoch.epoch_id},
        {"id":"c2","family":"multidisorder","strategy":"--lua-desync=multidisorder:pos=1\n","all_pass":True,"search_epoch_id":epoch.epoch_id},
    ],
})+"\n", encoding="utf-8")

outcomes = {"c1":[True,False,True], "c2":[True,True,True]}
calls = []
old_runner = search._candidate_runner
old_run_candidate = search._run_candidate
old_record = av.telemetry.record
search._candidate_runner = lambda name: root / "bin/candidate"
def fake_candidate(command, timeout, job_id, extra_env=None):
    candidate_id = command[4]
    sequence = len([item for item in calls if item == candidate_id])
    passed = outcomes[candidate_id][sequence]
    calls.append(candidate_id)
    result_path = Path(command[3])
    result_path.write_text(json.dumps({
        "id":candidate_id,
        "family":command[5],
        "strategy":Path(command[6]).read_text(encoding="utf-8"),
        "search_epoch_id":epoch.epoch_id,
        "endpoints":[{"status":"PASS" if passed else "FAIL"}],
        "all_pass":passed,
    })+"\n", encoding="utf-8")
    return 0, False, 10
search._run_candidate = fake_candidate
av.telemetry.record = lambda *args, **kwargs: None
try:
    status = av.stabilize(
        "job.test", str(endpoints), str(expansion_path), str(family_path), str(stability_path)
    )
finally:
    search._candidate_runner = old_runner
    search._run_candidate = old_run_candidate
    av.telemetry.record = old_record
assert status == 0
stability = json.loads(stability_path.read_text(encoding="utf-8"))
assert calls == ["c1","c1","c2","c2","c2"], calls
c1, c2 = stability["candidates"]
assert c1["stable"] is False
assert c1["attempts_executed"] == 2
assert c1["fail_fast"]["triggered"] is True
assert c1["fail_fast"]["failed_attempt"] == 2
assert c1["fail_fast"]["skipped_attempts"] == [3]
assert c2["stable"] is True and c2["attempts_executed"] == 3
assert stability["saved_attempts"] == 1

# Final shortlist uses one cold deep replay after the separate 3/3 stability gate.
status_path = job / "status.json"
status_path.write_text(json.dumps({
    "job_id":"job.test","target":"example.com","target_type":"domain","mode":"standard","language":"en"
})+"\n", encoding="utf-8")
stability_path.write_text(json.dumps({
    "search_epoch_id":epoch.epoch_id,
    "candidates":[{
        "id":"c2","family":"multidisorder","strategy":"--lua-desync=multidisorder:pos=1\n",
        "search_epoch_id":epoch.epoch_id,"stable":True,"line_count":1,"character_count":35,
    }],
})+"\n", encoding="utf-8")
old_deep = av._deep_replay_once
old_record = av.telemetry.record
def fake_deep(*args, **kwargs):
    source = args[2]
    profile = Path(args[3]).read_text(encoding="utf-8")
    return ({
        "id":source["id"],"family":source["family"],"strategy":profile,"profile":profile,
        "search_epoch_id":epoch.epoch_id,"all_pass":True,"profile_exact":True,
        "endpoints":[{
            "status":"PASS","selected_ip":"203.0.113.10","remote_ip":"203.0.113.10",
            "firewall":{"intercepted":True}
        }],
    }, 20)
av._deep_replay_once = fake_deep
av.telemetry.record = lambda *args, **kwargs: None
try:
    shortlist = av.build_shortlist("job.test")
finally:
    av._deep_replay_once = old_deep
    av.telemetry.record = old_record
assert shortlist["count"] == 1
item = shortlist["items"][0]
assert item["profile_replay"]["attempt_count"] == 1
assert item["profile_replay"]["verified"] is True
assert item["deep_validation"]["classification"] == "inconclusive"
assert shortlist["validation_policy"]["stability"] == "fail_fast_3_of_3"
assert shortlist["validation_policy"]["finalist"] == "single_cold_deep_get"
PY

"${PYTHON}" "${TMP}/test.py" || fail 'adaptive validation regression failed'
sh -n "$0"

echo 'PASS: Strategy Lab uses bounded discovery GETs, fail-fast 3/3 stability, and cold finalist depth classification'
