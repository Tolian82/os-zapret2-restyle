#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
MODULE="${SCRIPT_DIR}/strategy_lab_py/model_b_parallel_attribution.py"
ENTRY="${SCRIPT_DIR}/strategy_lab_python.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is unavailable: ${PYTHON}"
"${PYTHON}" -m py_compile "${MODULE}" "${ENTRY}"
grep -Fq 'model_b_parallel_attribution as model_b_parallel' "${ENTRY}" || fail 'parallel CLI does not use the attribution corrective'

MODEL_B_ATTR_TEST_ROOT="${ROOT_DIR}" "${PYTHON}" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

root = Path(os.environ["MODEL_B_ATTR_TEST_ROOT"])
script_dir = root / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(script_dir))

from strategy_lab_py import model_b, model_b_parallel, model_b_parallel_attribution as corrective, request

slot = model_b_parallel.BATCH_SLOTS[0]
binding = {"endpoint": "blocked.test", "selected_ip": "203.0.113.20"}

class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_case(execution: request.CommandResult, after_counter=None, endpoint_binding=binding):
    counter_calls = 0
    def fake_adapter(action, *args, timeout=15):
        nonlocal counter_calls
        del timeout
        if action == "source-port-free":
            assert args == ("42000",)
            return FakeCompleted()
        if action == "route-add-source":
            assert args == (str(slot.rule), str(slot.port), endpoint_binding["selected_ip"], "wan0", "tcp", "443", "42000")
            return FakeCompleted()
        if action == "counter":
            assert args == (str(slot.rule),)
            counter_calls += 1
            return FakeCompleted(stdout="0 0\n" if counter_calls == 1 else (after_counter if after_counter is not None else "1 60\n"))
        if action == "route-del":
            assert args == (str(slot.rule),)
            return FakeCompleted()
        raise AssertionError((action, args))

    with mock.patch.object(model_b, "_adapter", side_effect=fake_adapter), \
         mock.patch.object(model_b_parallel, "_parallel_curl_request", return_value=execution):
        return corrective._probe_endpoint(slot, endpoint_binding, "wan0", 42000)

# Real blocked/failed connection shape: command binding is exact and IPFW sees the packet,
# but curl has no connected remote/local write-out values. Attribution must still succeed,
# while candidate classification remains FAIL.
failed = request.CommandResult(
    command=["curl", "--resolve", "blocked.test:443:203.0.113.20", "--local-port", "42000", "https://blocked.test/"],
    returncode=28,
    stdout="",
    stderr="curl: (28) Connection timed out",
    timed_out=False,
    termination="completed",
    signal=None,
    duration_ms=2000,
)
result = run_case(failed)
assert result["classification"] == "fail"
assert result["endpoint_match"] is False
assert result["local_port_match"] is False
assert result["command_endpoint_match"] is True
assert result["command_source_port_match"] is True
assert result["intercepted"] is True
assert result["route_cleanup_ok"] is True
assert result["attribution_ok"] is True

# Counter growth alone must never be enough: execution evidence must carry the exact
# source-port selector that the IPFW rule was created for.
wrong_source = request.CommandResult(
    command=["curl", "--resolve", "blocked.test:443:203.0.113.20", "--local-port", "42001", "https://blocked.test/"],
    returncode=28,
    stdout="",
    stderr="timeout",
    timed_out=False,
    termination="completed",
    signal=None,
    duration_ms=2000,
)
result = run_case(wrong_source)
assert result["command_source_port_match"] is False
assert result["intercepted"] is True
assert result["attribution_ok"] is False

# IP-literal target: production curl correctly sends HTTPS directly to the IP
# without --resolve. Exact URL/family/pinned address + controlled source port +
# IPFW packet counter is still a strict attribution proof for a failed probe.
literal_binding = {"endpoint": "4.2.2.2", "selected_ip": "4.2.2.2"}
literal_command = request._curl_command(
    "4.2.2.2", scheme="https", family="ipv4", bound_ip="4.2.2.2"
)
literal_command[-1:-1] = ["--local-port", "42000"]
assert "--resolve" not in literal_command
literal_failure = request.CommandResult(
    command=literal_command, returncode=28, stdout="", stderr="timeout",
    timed_out=False, termination="completed", signal=None, duration_ms=1500,
)
literal_result = run_case(literal_failure, endpoint_binding=literal_binding)
assert literal_result["classification"] == "fail"
assert literal_result["intercepted"] is True
assert literal_result["command_endpoint_match"] is True
assert literal_result["attribution_ok"] is True

for forged_command in (
    literal_command[:-1] + ["https://4.2.2.3/"],
    literal_command[:-1] + ["--resolve", "4.2.2.2:443:4.2.2.2", "https://4.2.2.2/"],
    [part for part in literal_command if part != "--ipv4"],
):
    forged = request.CommandResult(
        command=forged_command, returncode=28, stdout="", stderr="timeout",
        timed_out=False, termination="completed", signal=None, duration_ms=1500,
    )
    probe = run_case(forged, endpoint_binding=literal_binding)
    assert probe["intercepted"] is True and probe["attribution_ok"] is False, probe

wrong_literal_binding = {"endpoint": "4.2.2.2", "selected_ip": "4.2.2.3"}
probe = run_case(literal_failure, endpoint_binding=wrong_literal_binding)
assert probe["attribution_ok"] is False, probe

# Successful probes retain the stricter success contract: connected remote IP and local
# port must both be reported exactly before PASS is possible.
success = request.CommandResult(
    command=["curl", "--resolve", "blocked.test:443:203.0.113.20", "--local-port", "42000", "https://blocked.test/"],
    returncode=0,
    stdout="exit=0 remote_ip=203.0.113.20 http=1.1 code=200 bytes=10 ssl_verify=0 appconnect=0.153000 local_port=42000\n",
    stderr="",
    timed_out=False,
    termination="completed",
    signal=None,
    duration_ms=100,
)
result = run_case(success)
assert result["classification"] == "pass"
assert result["endpoint_match"] is True
assert result["local_port_match"] is True
assert result["attribution_ok"] is True

# The same attribution helper is invoked directly by production Model C.
# Source-port/pinned IP command match alone never makes a failed HTTPS response win.
def executed(stdout, exit_code=0):
    return request.CommandResult(
        command=["curl", "--resolve", "blocked.test:443:203.0.113.20",
                 "--local-port", "42000", "https://blocked.test/"],
        returncode=exit_code, stdout=stdout, stderr="", timed_out=False,
        termination="completed", signal=None, duration_ms=120,
    )

response503 = executed(
    "exit=18 remote_ip=203.0.113.20 http=1.1 code=503 "
    "bytes=0 ssl_verify=0 appconnect=0.000000 local_port=42000\n",18)
r = run_case(response503)
assert r["classification"]=="pass" and r["attribution_ok"] is True

for bad in (
    "exit=0 remote_ip=203.0.113.21 http=2 code=200 bytes=10 ssl_verify=0 appconnect=0.121 local_port=42000\n",
    "exit=0 remote_ip=203.0.113.20 http=2 code=200 bytes=10 ssl_verify=60 appconnect=0.121 local_port=42000\n",
    "exit=0 remote_ip=203.0.113.20 http=2 code=200 bytes=10 ssl_verify=0 appconnect=0.121 local_port=42001\n",
):
    r=run_case(executed(bad))
    assert r["classification"]=="fail",r
    assert r["attribution_ok"] is True,r # route attribution != candidate success

r=run_case(success, after_counter="0 0\n")
assert r["classification"]=="fail" and r["attribution_ok"] is False
PY

sh -n "$0"
echo 'PASS: Model B/Model C exact domain --resolve and IP-literal direct HTTPS attribution, source port, IPFW counters and anti-forgery'
