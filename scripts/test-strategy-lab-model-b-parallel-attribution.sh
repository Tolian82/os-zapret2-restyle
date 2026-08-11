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


def run_case(execution: request.CommandResult):
    counter_calls = 0
    def fake_adapter(action, *args, timeout=15):
        nonlocal counter_calls
        del timeout
        if action == "source-port-free":
            assert args == ("42000",)
            return FakeCompleted()
        if action == "route-add-source":
            assert args == (str(slot.rule), str(slot.port), "203.0.113.20", "wan0", "tcp", "443", "42000")
            return FakeCompleted()
        if action == "counter":
            assert args == (str(slot.rule),)
            counter_calls += 1
            return FakeCompleted(stdout="0 0\n" if counter_calls == 1 else "1 60\n")
        if action == "route-del":
            assert args == (str(slot.rule),)
            return FakeCompleted()
        raise AssertionError((action, args))

    with mock.patch.object(model_b, "_adapter", side_effect=fake_adapter), \
         mock.patch.object(model_b_parallel, "_parallel_curl_request", return_value=execution):
        return corrective._probe_endpoint(slot, binding, "wan0", 42000)

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

# Successful probes retain the stricter success contract: connected remote IP and local
# port must both be reported exactly before PASS is possible.
success = request.CommandResult(
    command=["curl", "--resolve", "blocked.test:443:203.0.113.20", "--local-port", "42000", "https://blocked.test/"],
    returncode=0,
    stdout="exit=0 remote_ip=203.0.113.20 http=1.1 code=200 bytes=10 local_port=42000\n",
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
PY

sh -n "$0"
echo 'PASS: parallel Model B attributes blocked probes by exact command binding plus exact IPFW counter growth while retaining strict connected-socket evidence for PASS'
