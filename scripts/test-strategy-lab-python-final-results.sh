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

# Stage 6: exercise the actual Stage-85 shortlist/replay entrypoint on
# canonical IPv6 literals, AAAA-only names and dual A+AAAA search epochs.
def run_ipv6_stage85(name, target, kind, ipv4, ipv6, with_udp=False, forged_udp=False, bad_runner=False, replay_fault=""):
    job_name = "job." + name
    run_job = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / job_name
    run_job.mkdir(parents=True, exist_ok=True)
    pins = [address for address in (ipv4, ipv6) if address]
    evidence = {"endpoint": target}
    if ipv4:
        evidence["dns_a"] = {"classification": "pass", "answers": [ipv4]}
    if ipv6:
        evidence["dns_aaaa"] = {"classification": "pass", "answers": [ipv6]}
    recorded = endpoint_epoch.create(run_job, target, kind, [target], [evidence])
    (run_job / "endpoints.txt").write_text(target + "\n", encoding="utf-8")
    (run_job / "status.json").write_text(
        json.dumps({"target": target, "target_type": kind,
                    "mode": "extended" if with_udp else "standard"}) + "\n",
        encoding="utf-8",
    )
    fragment = "--lua-desync=multisplit:pos=1\n"
    source = {
        "id": "ipv6-stage85", "family": "multisplit", "strategy": fragment,
        "stable": True, "search_epoch_id": recorded.epoch_id,
        "endpoints": [{"endpoint": target, "selected_ip": address,
                       "remote_ip": address, "status": "PASS"} for address in pins],
    }
    (run_job / "stability.json").write_text(
        json.dumps({"search_epoch_id": recorded.epoch_id,
                    "candidates": [source]}) + "\n", encoding="utf-8",
    )
    if with_udp:
        (run_job / "udp-payload.bin").write_bytes(b"stage85-ipv6-probe")
        udp_source = dict(source)
        if forged_udp:
            udp_source["endpoints"] = [
                {"endpoint": target, "selected_ip": "2001:db8::ffff",
                 "remote_ip": "2001:db8::ffff", "status": "PASS"}]
        (run_job / "udp.json").write_text(
            json.dumps({"port": 50101, "working": udp_source}) + "\n",
            encoding="utf-8",
        )
    calls = []
    expected_tcp = ("--ipset-ip=" + target if kind == "ip"
                    else "--hostlist-domains=" + target)
    expected_udp = "--ipset-ip=" + ",".join(sorted(pins))
    def ipv6_replay(job_id, endpoints_file, output_file, candidate_id,
                    family, profile_file, use_hostlist):
        profile_text = Path(profile_file).read_text(encoding="utf-8")
        protocol = os.environ.get("STRATEGY_LAB_CANDIDATE_PROTOCOL")
        selector = os.environ.get("STRATEGY_LAB_PROFILE_REPLAY_SELECTOR")
        expected = expected_udp if protocol == "udp" else expected_tcp
        assert selector == expected, (name, protocol, selector, expected)
        assert profile_text.splitlines().count(expected) == 1
        calls.append((protocol, selector))
        rows = [
            {"endpoint": target, "selected_ip": pin, "remote_ip": pin,
             "status": "PASS", "endpoint_match": True,
             "firewall": {"intercepted": True}}
            for pin in pins
        ]
        if replay_fault == "address_drift":
            rows[0]["selected_ip"] = "2001:db8::dead"
            rows[0]["remote_ip"] = "2001:db8::dead"
        elif replay_fault == "missing_ipv6":
            rows.pop()
        elif replay_fault == "no_ipfw":
            rows[0]["firewall"]["intercepted"] = False
        elif replay_fault:
            raise AssertionError("unknown replay fault: " + replay_fault)
        Path(output_file).write_text(json.dumps({
            "id": candidate_id, "family": family, "strategy": profile_text,
            "search_epoch_id": recorded.epoch_id, "all_pass": True,
            "endpoints": rows,
        }) + "\n", encoding="utf-8")
        return 70 if bad_runner else 0
    old_runner = result.candidate.run_candidate
    result.candidate.run_candidate = ipv6_replay
    try:
        shortlist = result.build_shortlist(job_name)
    finally:
        result.candidate.run_candidate = old_runner
    expected_count = 0 if bad_runner or replay_fault else (2 if with_udp and not forged_udp else 1)
    assert shortlist["count"] == expected_count
    attempted_count = 2 if with_udp and not forged_udp else 1
    assert len(calls) == attempted_count * 3
    assert all(row["profile_replay"]["verified"] for row in shortlist["items"])
    if not bad_runner and not replay_fault:
        assert any(row["profile"].splitlines().count(expected_tcp) == 1
                   for row in shortlist["items"] if row["protocol"] == "tls13")
    if with_udp and not forged_udp and not bad_runner and not replay_fault:
        assert any(row["protocol"] == "udp" and expected_udp in row["profile"]
                   for row in shortlist["items"])
    else:
        assert not any(row["protocol"] == "udp" for row in shortlist["items"])
    return run_job, recorded


run_job_literal, literal_epoch = run_ipv6_stage85("literal6", "2001:db8::5", "ip", None, "2001:db8::5")
run_ipv6_stage85("aaaaonly", "aaaa.example", "domain", None, "2001:db8::6", with_udp=True)
run_ipv6_stage85("dualfamily", "dual.example", "domain", "198.51.100.31", "2001:db8::7", with_udp=True)
run_ipv6_stage85("forgedudp", "forged.example", "domain", None, "2001:db8::8",
                 with_udp=True, forged_udp=True)
run_ipv6_stage85("failedrunner", "failure.example", "domain", None, "2001:db8::9",
                 bad_runner=True)
run_ipv6_stage85("addressdrift", "drift.example", "domain", None, "2001:db8::10",
                 replay_fault="address_drift")
run_ipv6_stage85("missingipv6", "partial.example", "domain", "198.51.100.51", "2001:db8::11",
                 replay_fault="missing_ipv6")
run_ipv6_stage85("ipfwmissing", "intercept.example", "domain", None, "2001:db8::12",
                 replay_fault="no_ipfw")
stale = json.loads((run_job_literal / "stability.json").read_text(encoding="utf-8"))
stale["search_epoch_id"] = "se1-stale-search-epoch"
(run_job_literal / "stability.json").write_text(json.dumps(stale) + "\n", encoding="utf-8")
try:
    result.build_shortlist("job.literal6")
except result.ResultError:
    pass
else:
    raise AssertionError("Stage85 accepted stale search-epoch source")

for wrong in ("fe80::1%lo0", "[2001:db8::1]", "2001:DB8::1",
              "2001:db8::1/128", "::/0", "2001:db8::1,,203.0.113.8"):
    try:
        result.selector_for(wrong, "ip", "tls13")
    except result.ResultError:
        pass
    else:
        raise AssertionError("noncanonical IPv6 selector accepted: " + wrong)
    try:
        result._selector_addresses(wrong)
    except result.ResultError:
        pass
    else:
        raise AssertionError("noncanonical UDP pin accepted: " + wrong)
assert result._selector_addresses(
    "2001:db8::5,198.51.100.31,2001:db8::5"
) == ["2001:db8::5", "198.51.100.31"]
print("PASS: Stage85 IPv6 literal, AAAA-only and A+AAAA mock replay; forged UDP, runner error, stale epoch, address drift, missing family and missing IPFW refused")

PY

"${PYTHON}" "${TMP}/test.py" || fail 'Python final result regression failed'
sh -n "${STAGE_ADAPTER}"
sh -n "${RESULT_RUNNER}"
sh -n "${PROFILE_ADAPTER}"

echo 'PASS: Python 3.13 owns final profile construction, exact three-pass replay, unified shortlist publication, and automated-job circular eligibility'
