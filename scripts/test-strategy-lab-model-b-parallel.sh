#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
MODULE="${SCRIPT_DIR}/strategy_lab_py/model_b_parallel.py"
ADAPTER="${SCRIPT_DIR}/strategy_lab_model_b_parallel_adapter.sh"
WORKER="${SCRIPT_DIR}/strategy_lab_model_b_parallel_worker.sh"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_model_b_parallel.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"

"${PYTHON}" -m py_compile "${MODULE}" "${SCRIPT_DIR}/strategy_lab_python.py"
sh -n "${ADAPTER}"
sh -n "${WORKER}"
sh -n "${LAUNCHER}"
grep -Fq 'parallel_probes": True' "${MODULE}" || fail 'parallel benchmark does not declare true candidate parallelism'
grep -Fq 'endpoint_probes_parallel": False' "${MODULE}" || fail 'parallel benchmark must keep endpoints sequential inside one candidate'
grep -Fq 'ThreadPoolExecutor(max_workers=len(slots)' "${MODULE}" || fail 'parallel benchmark does not bound concurrency to the warm batch width'
grep -Fq 'source-port-free' "${MODULE}" || fail 'parallel benchmark does not preflight controlled source ports'
grep -Fq 'route-add-source' "${MODULE}" || fail 'parallel benchmark does not use source-port-qualified routes'
grep -Fq 'from me "${_mb_source_port}" to "${_mb_address}"' "${ADAPTER}" || fail 'parallel adapter does not bind the IPFW route to the controlled source port'
grep -Fq 'model-b-parallel run' "${WORKER}" || fail 'parallel lifecycle worker does not invoke the parallel Python path'
grep -Fq '9>"${LIFECYCLE_LOCK_FILE}"' "${LAUNCHER}" || fail 'parallel launcher does not retain the shared lifecycle lock'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-model-b-parallel.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
export MODEL_B_PARALLEL_TEST_ROOT="${ROOT_DIR}"
export MODEL_B_PARALLEL_TEST_TMP="${TMP}"

"${PYTHON}" <<'PY'
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from unittest import mock

root = Path(os.environ["MODEL_B_PARALLEL_TEST_ROOT"])
tmp = Path(os.environ["MODEL_B_PARALLEL_TEST_TMP"])
script_dir = root / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(script_dir))

from strategy_lab_py import candidate_spec, model_b, model_b_parallel, request, resources

jobs = tmp / "jobs"
job_id = "job.PARAL01"
job = jobs / job_id
job.mkdir(parents=True)
lua = tmp / "lua"; fake = tmp / "fake"
lua.mkdir(); fake.mkdir()
(lua / "zapret-lib.lua").write_text("-- lib\n", encoding="utf-8")
(lua / "zapret-antidpi.lua").write_text("-- antidpi\n", encoding="utf-8")
inventory = resources.snapshot_inventory(lua, fake)
(job / "resource-inventory.json").write_text(json.dumps(inventory.to_dict()), encoding="utf-8")
bindings = [
    {"index": 1, "endpoint": "blocked.test", "addresses": ["203.0.113.20"], "selected_ip": "203.0.113.20"},
    {"index": 2, "endpoint": "web.blocked.test", "addresses": ["203.0.113.21"], "selected_ip": "203.0.113.21"},
]
(job / "search-epoch.json").write_text(json.dumps({"schema":1,"epoch_id":"se1-parallel","generation":1,"bindings":bindings}), encoding="utf-8")
(job / "status.json").write_text(json.dumps({
    "job_id": job_id, "target": "blocked.test", "target_type": "domain", "mode": "standard",
    "state": "completed", "outcome": "NO_CANDIDATE",
    "restoration": {"verified":True,"initial_state":"RUNNING","final_state":"RUNNING","strategy_unchanged":True,"temporary_runtime_clean":True},
}), encoding="utf-8")

candidates=[]; schedule=[]
for index in range(1,6):
    spec = candidate_spec.CandidateSpec.from_strategy(
        candidate_id=f"candidate-{index}", family="seqovl", protocol="tls13", transport="tcp",
        port=443, l7="tls", target_binding=True,
        strategy=f"--out-range=-d10\n--lua-desync=multisplit:pos={index}:seqovl=1",
    )
    candidates.append({"id":spec.candidate_id,"family":spec.family,"strategy":spec.strategy,"all_pass":False,
                       "candidate_spec":spec.to_dict(),"resource_inventory_id":inventory.inventory_id,"search_epoch_id":"se1-parallel"})
    schedule.append({"sequence":index,"outcome":"fail","duration_ms":1400+index*10})
(job / "parameter-expansion.json").write_text(json.dumps({
    "search_epoch_id":"se1-parallel","completed":5,"candidates":candidates,"working":[],
    "failed":[item["id"] for item in candidates],"schedule":schedule,"stopped_reason":"graph_exhausted",
}), encoding="utf-8")
(job / "timing-telemetry.json").write_text(json.dumps({"schema":1,"events":[{"sequence":1,"phase":"job_total","duration_ms":12000}]}), encoding="utf-8")

session=tmp/"session"; session.mkdir(); session.chmod(0o711)
report=tmp/"parallel.json"
os.environ["STRATEGY_LAB_JOBS_DIR"]=str(jobs)
os.environ["STRATEGY_LAB_MODEL_B_SESSION_DIR"]=str(session)
os.environ["STRATEGY_LAB_MODEL_B_SOURCE_PORT_BASE"]="42000"

class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr

running={slot.name:False for slot in model_b_parallel.BATCH_SLOTS}
ports={slot.name:slot.port for slot in model_b_parallel.BATCH_SLOTS}
pids={slot.name:8000+i for i,slot in enumerate(model_b_parallel.BATCH_SLOTS)}
active_rules={}
counter_calls={}
route_source_ports=[]
lock=threading.Lock()
cleanup_calls=0

def fake_adapter(action,*args,timeout=15):
    global cleanup_calls
    del timeout
    with lock:
        if action=="wan": return FakeCompleted(stdout="wan0\n")
        if action=="preflight": return FakeCompleted()
        if action=="cleanup-all":
            cleanup_calls += 1; active_rules.clear()
            for worker in running: running[worker]=False
            return FakeCompleted()
        if action=="launch":
            worker,port=args; assert int(port)==ports[worker]; running[worker]=True; return FakeCompleted()
        if action=="snapshot":
            worker,port=args; alive=running[worker]
            return FakeCompleted(stdout=json.dumps({"worker":worker,"pid":pids[worker] if alive else None,
                "divert_port":int(port),"process_identity":alive,"socket_ready":alive,"log_clean":True,
                "rss_kb":4300+(int(port)-9990)*10 if alive else None}))
        if action=="source-port-free": return FakeCompleted()
        if action=="route-add-source":
            rule,port,address,_wan,transport,dport,source_port=args
            assert transport=="tcp" and dport=="443"
            assert address in {"203.0.113.20","203.0.113.21"}
            assert int(source_port) not in route_source_ports
            route_source_ports.append(int(source_port)); active_rules[int(rule)]=int(port); counter_calls[int(rule)]=0
            return FakeCompleted()
        if action=="route-del": active_rules.pop(int(args[0]),None); return FakeCompleted()
        if action=="rule-present": return FakeCompleted(returncode=0 if int(args[0]) in active_rules else 1)
        if action=="counter":
            rule=int(args[0]); counter_calls[rule]=counter_calls.get(rule,0)+1
            return FakeCompleted(stdout=("0 0\n" if counter_calls[rule] % 2 else "1 100\n"))
    raise AssertionError((action,args))

def fake_parallel_curl(endpoint,selected_ip,local_port):
    # Deliberate real delay: the synthetic gate must prove overlapping candidate windows.
    time.sleep(0.04)
    return request.CommandResult(command=["curl","--local-port",str(local_port)], returncode=28,
        stdout=f"exit=28 remote_ip={selected_ip} http=1.1 code=000 bytes=0 local_port={local_port}\n",
        stderr="timeout", timed_out=False, termination="completed", signal=None, duration_ms=40)

with mock.patch.object(model_b,"_adapter",side_effect=fake_adapter), \
     mock.patch.object(model_b.resources,"snapshot_inventory",return_value=inventory), \
     mock.patch.object(model_b_parallel,"_parallel_curl_request",side_effect=fake_parallel_curl):
    assert model_b_parallel.run(job_id,str(report))==0

value=json.loads(report.read_text(encoding="utf-8"))
assert value["model"]=="B-warm-worker-parallel-batched"
assert value["parallel_probes"] is True
assert value["candidate_parallel_width"]==3
assert value["endpoint_probes_parallel"] is False
assert value["production_approved"] is False
assert value["source_port_plan"]=={"base":42000,"last":42009,"count":10,"unique":True}
assert value["preliminary_accept"] is True, value
assert value["conclusion"]=="pending_restoration"
assert len(value["batches"])==2
assert [batch["parallel"]["max_overlap_observed"] for batch in value["batches"]]==[3,2]
assert all(batch["parallel"]["overlap_observed"] is True for batch in value["batches"])
assert all(batch["parallel"]["limit_respected"] is True for batch in value["batches"])
assert [probe["candidate_id"] for probe in value["probes"]]==[f"candidate-{i}" for i in range(1,6)]
assert all(probe["endpoint_count"]==2 for probe in value["probes"])
assert all(probe["endpoints_sequential"] is True for probe in value["probes"])
assert all(probe["equivalent_to_cold_search"] is True for probe in value["probes"])
assert all(probe["intercepted"] is True for probe in value["probes"])
assert value["checks"]["candidate_parallelism_observed"] is True
assert value["checks"]["concurrency_limit_respected"] is True
assert value["checks"]["endpoints_sequential_per_candidate"] is True
assert value["checks"]["route_attribution"] is True
assert value["checks"]["corpus_complete"] is True
assert value["timing"]["endpoint_probe_count"]==10
assert sorted(route_source_ports)==list(range(42000,42010))
assert cleanup_calls>=4

# Command-shaping regression: discovery limits stay identical while --local-port is added.
base_command=["curl","--range","0-65535","--max-time","3","--write-out","exit=%{exitcode} remote_ip=%{remote_ip} http=%{http_version} code=%{response_code} bytes=%{size_download}\\n","https://blocked.test/"]
observed={}
def fake_run(command,timeout):
    observed["command"]=command; observed["timeout"]=timeout
    return request.CommandResult(command=command,returncode=28,stdout="",stderr="",timed_out=False,termination="completed",signal=None,duration_ms=1)
with mock.patch.object(request,"_curl_command",return_value=list(base_command)), mock.patch.object(request,"run_command",side_effect=fake_run):
    model_b_parallel._parallel_curl_request("blocked.test","203.0.113.20",42424)
assert observed["command"][-3:]==["--local-port","42424","https://blocked.test/"]
assert "local_port=%{local_port}" in observed["command"][observed["command"].index("--write-out")+1]

initial=tmp/"initial.json"; final=tmp/"final.json"
evidence={"state":"RUNNING","effective_config_hash":"cfg","runtime_args_hash":"args","normal_firewall_hash":"fw"}
initial.write_text(json.dumps(evidence),encoding="utf-8"); final.write_text(json.dumps(evidence),encoding="utf-8")
assert model_b_parallel.finalize(str(report),str(initial),str(final),"1")==0
value=json.loads(report.read_text(encoding="utf-8"))
assert value["conclusion"]=="accept"
assert value["checks"]["restoration_verified"] is True
PY

sh -n "$0"
echo 'PASS: controlled parallel Model B uses three isolated warm workers with unique source-port routing, concurrent candidate probes, sequential endpoints, exact attribution, bounded concurrency, cleanup, and semantic restoration'
