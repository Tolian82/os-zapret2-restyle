#!/usr/bin/env python3
"""Offline, no-root regression of the installed _10 cold-IPFW preflight."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT = Path(__file__).with_name("legacy-cold-ipfw-preflight.sh")
source = SCRIPT.read_text()
assert "kldload " not in source
assert "pkg add " not in source.split("set -u", 1)[-1]

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    trace = base / "trace"

    def executable(name, body):
        p = base / name
        p.write_text("#!/bin/sh\n" + body)
        p.chmod(0o755)
        return str(p)

    id_bin = executable("id", 'echo "id:$*" >> "$TRACE"\n[ "$*" = -u ] && echo "$MOCK_UID"\n')
    pkg_bin = executable("pkg", 'echo "pkg:$*" >> "$TRACE"\n'
                         '[ "$*" = "query %v os-zapret2-restyle" ] || exit 99\n'
                         'echo "$MOCK_VERSION"\n')
    lock_bin = executable("lockf", 'echo "lockf:$*" >> "$TRACE"\n'
                          '[ "$*" = "-s -t 5 9" ] || exit 99\n'
                          '[ "$MOCK_LOCK" != busy ] || exit 75\n'
                          '(: >&9) 2>/dev/null || exit 99\n')
    kld_bin = executable("kldstat", 'echo "kldstat:$*" >> "$TRACE"\n'
                         '[ "$1" = -q ] && [ "$2" = -m ] || exit 99\n'
                         '[ "$MOCK_MODULE" != error ] || exit 69\n'
                         '[ "$3" != "$MOCK_MODULE" ] || exit 0\nexit 1\n')
    ipfw_bin = executable("ipfw", 'echo "ipfw:$*" >> "$TRACE"\n'
                          'echo "$MOCK_IPFW_TEXT" >&2\nexit "$MOCK_IPFW_RC"\n')
    ps_bin = executable("ps", 'echo "ps:$*" >> "$TRACE"\n'
                        '[ "$*" = "ax -o pid= -o command=" ] || exit 99\n'
                        'echo "$MOCK_PROCESSES"\n')
    service = executable("service", 'echo "service:$*" >> "$TRACE"\n'
                         '[ "$*" = status ] || exit 99\nexit "$MOCK_STATUS"\n')
    inspector = base / "inspect.py"
    inspector.write_text(
        'import json,os,sys\n'
        'with open(os.environ["TRACE"],"a") as f: f.write("inspector\\n")\n'
        'os.fstat(9)\n'
        'print(json.dumps(dict(source="native-common",'
        'state=os.getenv("MOCK_STATE","foreign-or-modified-rules"),'
        'condition=os.getenv("MOCK_CONDITION","common-stopped-with-kernel-objects"),'
        'can_activate=os.getenv("MOCK_CAN_ACTIVATE","0")=="1",'
        'runtime=dict(state=os.getenv("MOCK_RUNTIME_STATE","stopped")))))\n'
        'sys.exit(int(os.getenv("MOCK_INSPECT_RC","2")))\n'
    )
    journal = base / "operation.json"
    journal.write_text('{"phase":"committed","sentinel":"unchanged"}')
    marker1, marker2 = base / "pkg-replacement.restart", base / "pkg-upgrade.restart"
    marker1.write_text("recovery marker")
    marker2.write_text("upgrade marker")
    journal_original = journal.read_bytes()
    marker_original = [marker1.read_bytes(), marker2.read_bytes()]
    env = {**os.environ, "TRACE": str(trace), "ID_BIN": id_bin,
           "PKG_BIN": pkg_bin, "LOCKF_BIN": lock_bin, "KLDSTAT_BIN": kld_bin,
           "IPFW_BIN": ipfw_bin, "PS_BIN": ps_bin, "PYTHON_BIN": sys.executable,
           "SERVICE_SCRIPT": service, "COLD_INSPECT_BIN": str(inspector),
           "SHARED_APPLY_JOURNAL": str(journal),
           "LIFECYCLE_LOCK_FILE": str(base / "lifecycle.lock"),
           "DVTWS_BIN": "/usr/local/etc/zapret2/binaries/my/dvtws2",
           "MOCK_VERSION": "0.5.7_10", "MOCK_UID": "0",
           "MOCK_LOCK": "free", "MOCK_MODULE": "none",
           "MOCK_IPFW_RC": "71",
           "MOCK_IPFW_TEXT": "ipfw: retrieving config failed: Protocol not available",
           "MOCK_STATUS": "2", "MOCK_PROCESSES": "1234 /usr/sbin/syslogd -s",
           "MOCK_STATE": "foreign-or-modified-rules",
           "MOCK_CONDITION": "common-stopped-with-kernel-objects",
           "MOCK_CAN_ACTIVATE": "0", "MOCK_RUNTIME_STATE": "stopped",
           "MOCK_INSPECT_RC": "2"}

    def run(**changes):
        trace.write_text("")
        result = subprocess.run(["sh", str(SCRIPT)], capture_output=True,
                                text=True, env={**env, **changes})
        events = trace.read_text().splitlines()
        assert all(not any(word in event for word in
                           ("stop", "start", "add", "delete", "flush", "kldload"))
                   for event in events), events
        assert [marker1.read_bytes(), marker2.read_bytes()] == marker_original
        if journal.exists():
            assert journal.read_bytes() == journal_original
        return result, events

    good, events = run()
    assert good.returncode == 0, (good, events)
    assert good.stdout.splitlines() == [
        "PACKAGE=0.5.7_10", "DIAGNOSIS=cold-ipfw-committed-stopped",
        "UPGRADE_AUTHORIZED=no", "NEXT=owner-reviewed-recovery-required"]
    assert events.count("lockf:-s -t 5 9") == 1
    assert events.count("inspector") == 1
    assert events.count("service:status") == 2
    assert events.count("ipfw:-q list") == 2

    for variant in (
        {"MOCK_UID": "1000"}, {"MOCK_VERSION": "0.5.7_1"},
        {"MOCK_VERSION": "0.5.7_29"}, {"MOCK_MODULE": "ipfw"},
        {"MOCK_MODULE": "ipdivert"}, {"MOCK_MODULE": "error"},
        {"MOCK_IPFW_RC": "0"}, {"MOCK_IPFW_RC": "70"},
        {"MOCK_IPFW_TEXT": "permission denied"}, {"MOCK_LOCK": "busy"},
        {"MOCK_STATUS": "0"}, {"MOCK_STATUS": "1"},
        {"MOCK_RUNTIME_STATE": "running"}, {"MOCK_RUNTIME_STATE": "partial"},
        {"MOCK_STATE": "ready"}, {"MOCK_STATE": "stopped"},
        {"MOCK_CONDITION": "unexpected"}, {"MOCK_CAN_ACTIVATE": "1"},
        {"MOCK_INSPECT_RC": "3"},
        {"MOCK_PROCESSES": "2233 /usr/local/etc/zapret2/binaries/my/dvtws2 --port=989"},
        {"MOCK_PROCESSES": "2233 /bin/sh /usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"},
    ):
        response, events = run(**variant)
        assert response.returncode != 0, (variant, response, events)
        assert "UPGRADE_AUTHORIZED=no" in response.stderr, variant
        assert "DIAGNOSIS=" not in response.stdout, variant

    journal.unlink()
    failed, _ = run()
    assert failed.returncode != 0
    journal.write_bytes(journal_original)
    inspector.unlink()
    inspector.symlink_to(service)
    failed, _ = run()
    assert failed.returncode != 0

print("PASS: legacy cold-IPFW preflight is read-only, exact and fail-closed")
