#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
PYTHONPATH="${SCRIPT_DIR}" "${PYTHON}" - <<'PY'
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from strategy_lab_py import candidate, extended, ip_target_support, orchestrator, request

# Unsupported HTTP/3 in the private client is a technical error, not a
# genuine negative QUIC target response or four failed strategies.
def capability_result(rc, stderr):
    def fake(command, **kwargs):
        return request.CommandResult(list(command), rc, "", stderr, False, "completed", None, 7)
    with mock.patch.object(request, "binary", return_value="/private/chrome"), mock.patch.object(request, "run_command", side_effect=fake):
        return request.quic_target_request("blocked.example", "203.0.113.10")

for rc, stderr in (
    (4, "curl: (4) A requested feature or protocol was not built in"),
    (2, "curl: option --http3-only: the installed libcurl version does not support this"),
    (1, "curl: option --http3-only: unknown option"),
):
    try:
        capability_result(rc, stderr)
        assert False, (rc, stderr)
    except request.RequestError as exc:
        assert "QUIC client" in str(exc) and "support" in str(exc)
assert capability_result(28, "curl: (28) Connection timed out").returncode == 28

TARGET = "203.0.113.10"
HOST = "blocked.example"
BASE = f"remote_ip={TARGET} http=0 code=000 bytes=0 ssl_verify=0 appconnect=0.121000"
def output(line=BASE, *, flag=True, rc=28):
    cmd = ["/private/chrome", "--http3-only", "https://blocked.example/"] if flag else ["openssl", "s_client", "-quic"]
    return request.CommandResult(cmd, rc, "exit=" + str(rc) + " " + line, "", False, "completed", None, 150)

# Proof requires QUIC-only command, observed pinned IP and valid server trust.
good = request.chrome_quic_evidence(output(), expected_ip=TARGET)
assert good["accessible"] and good["quic_verified"] and good["signal"] == "quic_handshake"
http3 = output(f"remote_ip={TARGET} http=3 code=503 bytes=0 ssl_verify=0 appconnect=0.000000",rc=18)
proof = request.chrome_quic_evidence(http3,expected_ip=TARGET)
assert proof["accessible"] and proof["http3_response"] and proof["http_status"] == 503
for wrong in (
    output(flag=False), output(BASE.replace(TARGET,"203.0.113.11")),
    output(BASE.replace("ssl_verify=0","ssl_verify=60")),
    output(BASE.replace("http=0","http=2")),
    output(BASE.replace("appconnect=0.121000","appconnect=0.000000")),
    output(f"remote_ip={TARGET} http=2 code=200 bytes=25 ssl_verify=0 appconnect=0.141000",rc=0),
):
    assert not request.chrome_quic_evidence(wrong,expected_ip=TARGET)["accessible"],wrong

# Production command is pinned Chrome HTTP3-only; no TCP HTTP2 fallback.
with mock.patch.object(request,"binary",return_value="/private/chrome"),mock.patch.object(request,"run_command",side_effect=lambda cmd,**kw: request.CommandResult(cmd,28,"", "",False,"completed",None,100)) as run:
    command=request.quic_target_request(HOST,TARGET).command
assert "--http3-only" in command and "--http3" not in command
assert command[command.index("--resolve")+1]==f"{HOST}:443:{TARGET}"
assert command[-1]==f"https://{HOST}/" and "--insecure" not in command and "-k" not in command
assert "--max-redirs" in command and command[command.index("--max-redirs")+1]=="0"

binding={"endpoint":HOST,"selected_ip":TARGET,"rule":19100}
spec=candidate.ProtocolSpec("quic","udp",443,"quic")
for probe in (candidate._probe_endpoint,ip_target_support._candidate_probe):
    for fake,interception,expected in (
        (output(),True,"PASS"),(http3,True,"PASS"),
        (output(BASE.replace(TARGET,"203.0.113.11")),True,"FAIL"),
        (output(BASE.replace("ssl_verify=0","ssl_verify=60")),True,"FAIL"),
        (output(flag=False),True,"FAIL"),(output(),False,"FAIL"),
    ):
        counter=[(0,0),(3,96)] if interception else [(0,0),(0,0)]
        with mock.patch.object(candidate,"_counter",side_effect=counter),mock.patch.object(request,"quic_target_request",return_value=fake):
            r=probe(binding,spec)
        assert r["status"]==expected,(probe.__name__,fake.stdout,r)
        assert r["remote_ip"]==request.chrome_quic_evidence(fake,expected_ip=TARGET).get("remote_ip","")
        assert r["transport"]=="quic-ipv4" and r["firewall"]["rule"]==19100

with tempfile.TemporaryDirectory() as root:
    root=Path(root)
    endpoints=root/"endpoints.txt";endpoints.write_text(HOST+"\\n")
    epoch=SimpleNamespace(epoch_id="se1-test",bindings=({"endpoint":HOST,"selected_ip":TARGET},))
    direct_result=root/"direct.json"
    with mock.patch.object(extended,"_search_epoch",return_value=epoch),mock.patch.object(extended,"job_dir",return_value=root),mock.patch.object(extended.search,"_cancel_requested",return_value=False),mock.patch.object(request,"quic_target_request",return_value=output()),mock.patch.object(extended,"_runner",side_effect=AssertionError("no candidate on direct success")):
        assert extended.quic("job.test",str(endpoints),"ignored",str(direct_result))==0
    data=json.loads(direct_result.read_text())
    assert data["status"]=="direct_accessible" and data["tested"]==[] and data["working"] is None
    assert data["direct"][0]["reachability"]["quic_verified"]

    argsdir=root/"args";argsdir.mkdir();(argsdir/"one.args").write_text("--lua-desync=drop\\n")
    passed=[]
    def fake_candidate(*args,**kwargs):
        passed.append(1)
        return {"id":"candidate-1","family":"fake","strategy":"--lua-desync=drop\\n","search_epoch_id":"se1-test",
                "endpoints":[{"endpoint":HOST,"selected_ip":TARGET,"status":"PASS"}],"all_pass":True}
    with mock.patch.object(extended,"_search_epoch",return_value=epoch),mock.patch.object(extended,"job_dir",return_value=root),mock.patch.object(extended.search,"_cancel_requested",return_value=False),mock.patch.object(request,"quic_target_request",return_value=output(BASE.replace("appconnect=0.121000","appconnect=0.000000"))),mock.patch.object(extended,"_catalog",return_value=[("candidate-1","fake","1","one.args")]),mock.patch.object(extended,"_runner",return_value=Path("/bin/true")),mock.patch.object(extended,"_candidate",side_effect=fake_candidate),mock.patch.dict(extended.os.environ,{"STRATEGY_LAB_QUIC_ARGS_DIR":str(argsdir)}):
        assert extended.quic("job.test",str(endpoints),"ignored",str(root/"candidate.json"))==0
    data=json.loads((root/"candidate.json").read_text())
    assert len(passed)==3 and data["status"]=="working" and data["working"]["stable"] is True
    assert data["working"]["pass_count"]==3 and data["working"]["attempts_executed"]==3
    assert len(data["working"]["attempts"])==3 and data["direct"][0]["status"]=="FAIL"

    # Fail-fast: 1/3 or 2/3 cannot become a working recommendation.
    failed=[True,False]
    def unstable(*args,**kwargs):
        ok=failed.pop(0)
        return {"id":"candidate-1","family":"fake","strategy":"--lua-desync=drop\\n",
                "search_epoch_id":"se1-test","endpoints":[],"all_pass":ok}
    with mock.patch.object(extended,"_search_epoch",return_value=epoch),mock.patch.object(extended,"job_dir",return_value=root),mock.patch.object(extended.search,"_cancel_requested",return_value=False),mock.patch.object(request,"quic_target_request",return_value=output(BASE.replace("appconnect=0.121000","appconnect=0.000000"))),mock.patch.object(extended,"_catalog",return_value=[("candidate-1","fake","1","one.args")]),mock.patch.object(extended,"_runner",return_value=Path("/bin/true")),mock.patch.object(extended,"_candidate",side_effect=unstable),mock.patch.dict(extended.os.environ,{"STRATEGY_LAB_QUIC_ARGS_DIR":str(argsdir)}):
        assert extended.quic("job.test",str(endpoints),"ignored",str(root/"unstable.json"))==0
    data=json.loads((root/"unstable.json").read_text())
    assert data["status"]=="not_found" and data["working"] is None and data["tested"][0]["pass_count"]==1
    assert data["tested"][0]["attempts_executed"]==2 and not data["tested"][0]["stable"]

    # Actual Stage80 orchestrator returns TARGET_ACCESSIBLE before 85/99, and
    # its caller's established finish() path still performs Stage90 restoration.
    (root/"quic.json").write_text(json.dumps({"status":"direct_accessible"}))
    seen=[]
    budget=SimpleNamespace(begin_stage80=lambda:None,timeout_for=lambda *args:60)
    def adapter(action,**kwargs):
        seen.append(action)
        return orchestrator.AdapterResult(kind="pass",message="PASS",initial_state=None)
    fake=SimpleNamespace(mode="extended",job_dir=root,language="ru",budget=budget,
      _begin=lambda stage:seen.append("begin-"+stage),_operation_limit=lambda stage:60,
      check_cancel=lambda:None,_run_adapter=adapter,_pass=lambda stage,msg:seen.append("pass-"+stage))
    assert orchestrator.Orchestrator._run_stage80(fake)=="TARGET_ACCESSIBLE"
    assert seen==["begin-80","80-tcp","80-quic","pass-80"],seen

print("PASS: pinned Chrome QUIC-only identity, direct target outcome, 3/3, IPFW, no TCP fallback")
PY
