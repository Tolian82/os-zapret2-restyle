#!/usr/bin/env python3
"""Offline package replacement regression for owner's v0.5.7_10 cold kernel.

A newer PRE-INSTALL may execute against OLD v0.5.7_10 runtime scripts.
The package must never recurse into that script's already-held FD9 status.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
hook = root / "pkg/+PRE_INSTALL"

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    service = base / "service"
    trace = base / "trace"
    service.write_text(
        '#!/bin/sh\n'
        '# marker from installed native status dispatcher:\n'
        '# service_with_lifecycle_lock "${LIFECYCLE_LOCK_TIMEOUT}" "$@"\n'
        'printf "%s\\n" "$1" >> "$TEST_TRACE"\n'
        'if [ "$1" = status ]; then exit 2; fi\n'
        'echo "FAIL: preinstall attempted to mutate cold owner" >&2\n'
        'exit 99\n'
    )
    service.chmod(0o755)
    kld = base / "kldstat"
    kld.write_text('#!/bin/sh\n[ "$3" = "$MOCK_LOADED_MODULE" ] && exit 0\nexit 1\n')
    kld.chmod(0o755)
    ipfw = base / "ipfw"
    ipfw.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$MOCK_IPFW_OUTPUT" >&2\n'
        'exit "$MOCK_IPFW_RC"\n'
    )
    ipfw.chmod(0o755)
    lockf = base / "lockf"
    lockf.write_text('#!/bin/sh\n[ "$1" = -s ] && [ "$2" = -t ] && [ "$4" = 9 ]\n')
    lockf.chmod(0o755)
    inspect = base / "inspect.py"
    inspect.write_text(
        'import json,os,sys\n'
        'print(json.dumps(dict(source="native-common", '
        'state="foreign-or-modified-rules", '
        'condition="common-stopped-with-kernel-objects", '
        'runtime=dict(state=os.getenv("MOCK_NATIVE_STATE", "stopped")))))\n'
        'sys.exit(2)\n'
    )
    journal = base / "operation.json"
    journal.write_text('{"phase":"committed"}')
    env = {**os.environ,
           "SERVICE_SCRIPT": str(service),
           "TEST_TRACE": str(trace),
           "LIFECYCLE_LOCK_FILE": str(base / "lifecycle.lock"),
           "UPGRADE_STATE_DIR": str(base / "state"),
           "UPGRADE_RESTART_MARKER": str(base / "state" / "pkg-upgrade.restart"),
           "REPLACEMENT_RESTART_MARKER": str(base / "state" / "pkg-replacement.restart"),
           "SHARED_APPLY_JOURNAL": str(journal),
           "LOCKF_BIN": str(lockf), "KLDSTAT_BIN": str(kld),
           "IPFW_BIN": str(ipfw), "PYTHON_BIN": sys.executable,
           "COLD_INSPECT_BIN": str(inspect),
           "MOCK_LOADED_MODULE": "none", "MOCK_IPFW_RC": "71",
           "MOCK_IPFW_OUTPUT": "retrieving config failed: Protocol not available",
           "MOCK_NATIVE_STATE": "stopped"}
    def run(**overrides):
        trace.unlink(missing_ok=True)
        result = subprocess.run(["sh", str(hook)], env={**env, **overrides},
                                capture_output=True, text=True)
        assert not (base / "state" / "pkg-replacement.restart").exists()
        assert trace.read_text().splitlines() == ["status"], (
            "status reentered its own FD9 or hook tried to stop an unknown service"
        )
        return result

    safe_refusal = run()
    assert safe_refusal.returncode != 0, "unsafe old hook transition was permitted"
    assert "old PRE-DEINSTALL" in safe_refusal.stderr, (
        "missing actionable refusal for installed old package's unsafe hook"
    )
    # The old installed PRE-DEINSTALL is unpatched during incoming pre-install.
    # It still calls its OLD service with status (2) then stop, not a safe
    # stopped-state no-op. Do not claim that this incoming hook can fix it.
    trace.unlink(missing_ok=True)
    old_hook = root / "pkg/+PRE_DEINSTALL"
    old_result = subprocess.run(["sh", str(old_hook)], env=env,
                                capture_output=True, text=True)
    assert old_result.returncode != 0
    assert trace.read_text().splitlines() == ["status", "stop"], (
        "old package's PRE-DEINSTALL failure path changed"
    )
    for overrides in (
        {"MOCK_LOADED_MODULE": "ipfw"},
        {"MOCK_LOADED_MODULE": "ipdivert"},
        {"MOCK_IPFW_RC": "70"},
        {"MOCK_IPFW_OUTPUT": "permission denied"},
        {"MOCK_NATIVE_STATE": "partial"},
    ):
        response = run(**overrides)
        assert response.returncode != 0, f"unsafe preinstall accepted {overrides}"
    journal.unlink()
    assert run().returncode != 0, "missing committed journal accepted"

print("PASS: preinstall refuses unsafe old PRE-DEINSTALL after verified cold kernel")
