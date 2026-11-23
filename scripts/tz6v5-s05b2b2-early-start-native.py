#!/usr/bin/env python3
"""Genuine early dvtws2 readiness loss on disposable OPNsense only."""
from __future__ import annotations
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
PID = Path("/var/run/dvtws2.pid")
ENGINE = "/usr/local/etc/zapret2/binaries/my/dvtws2"
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(obj)
    return obj


def real_native():
    s05a = load("s05b2b2_s05a", "tz6v5-s05a-status-json-native.py")
    s04 = s05a.s04
    s04.guest_gate("hot")
    s04.need(os.environ.get("GITHUB_ACTIONS") == "true" and
             os.environ.get("ZAPRET2_S05B2B2_DISPOSABLE_NATIVE") == "1",
             "S05B2B2_NOT_DISPOSABLE")
    clean = s04.load("s05b2b2_clean", "stage2-opnsense-real-native-clean-install.py")
    s04.install(clean)
    s04.upstream()
    g04 = s04.load("s05b2b2_g04", "stage2-opnsense-g04-native-runtime.py")
    model = g04.model()
    traffic = model.findtext("strategy/trafficargs") or ""
    hosts = model.findtext("hostlist/youtubedomains") or ""
    s04.need(traffic.count("--new") == 1 and len(hosts.splitlines()) == 10,
             "S05B2B2_BASELINE_UNQUALIFIED")
    voice = s04.load("s05b2b2_https", "stage2-opnsense-real-native-voice-http.py")
    web = voice.GuestHttps()
    voice.login(web)
    saved = web.api("GET", "/api/zapret/settings/get").get("zapret")
    s04.need(isinstance(saved, dict) and
             g04.same_gui_multiline(saved.get("strategy", {}).get("trafficargs"), traffic) and
             g04.same_gui_multiline(saved.get("hostlist", {}).get("youtubedomains"), hosts),
             "S05B2B2_INITIAL_HTTPS_CONFIG_CHANGED")
    before_config = g04.CONFIG.read_bytes()
    before_foreign = g04.foreign_rules()
    s04.need(not PID.exists() and not JOURNAL.exists(),
             "S05B2B2_PREEXISTING_ORIGINAL_OWNER")

    # Test-only exact process termination, *never* on operator hardware.
    # Only after a live PIDfile and matching native absolute executable OS
    # argv, and only inside the explicit disposable guest gate.
    stop = threading.Event()
    witness = {"killed": False, "error": None}
    def fault():
        deadline = time.monotonic() + 150
        while not stop.is_set() and time.monotonic() < deadline:
            try:
                pid = PID.read_text("ascii").strip()
            except (FileNotFoundError, PermissionError):
                time.sleep(.01)
                continue
            if not re.fullmatch(r"[1-9][0-9]{1,9}", pid):
                witness["error"] = "UNQUALIFIED_CHILD_PID"
                return
            p = s04.run(["/bin/ps", "-p", pid, "-o", "command="], timeout=8)
            cmd = p.stdout.strip()
            if p.returncode or not (cmd == ENGINE or cmd.startswith(ENGINE + " ")):
                time.sleep(.01)
                continue
            try:
                os.kill(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                witness["error"] = "CHILD_ALREADY_GONE"
                return
            witness["killed"] = True
            return
        witness["error"] = "NO_REAL_NATIVE_START_WINDOW"

    worker = threading.Thread(target=fault, daemon=True)
    worker.start()
    try:
        response = web.api("POST", "/api/zapret/settings/apply",
                           g04.g04_http_form(saved))
    finally:
        stop.set()
        worker.join(timeout=12)
    s04.need(witness["killed"] is True and witness["error"] is None,
             "S05B2B2_EARLY_FAULT_NOT_VERIFIED_" + str(witness["error"]))
    s04.need(response.get("result") != "saved",
             "S05B2B2_NATIVE_EARLY_ENGINE_TREATED_AS_SUCCESS")
    s04.need(g04.CONFIG.read_bytes() == before_config,
             "S05B2B2_CONFIG_CHANGED_ON_FAILED_START")
    if before_foreign is not None:
        s04.need(g04.foreign_rules() == before_foreign,
                 "S05B2B2_FOREIGN_IPFW_DRIFT")

    result = None
    for _ in range(12):
        if JOURNAL.is_file():
            try:
                candidate = json.loads(JOURNAL.read_bytes())
            except (ValueError, OSError):
                candidate = None
            if (type(candidate) is dict and candidate.get("phase") == "requires-review"
                    and isinstance(candidate.get("failure"), dict)):
                result = candidate
                break
        time.sleep(1)
    s04.need(result is not None and result["failure"]["code"] == "ENGINE_START_UNVERIFIED"
             and result["failure"]["cause"] in ("no-live-pid", "stability-unverified")
             and result["failure"]["exit_status"] is None
             and result["failure"]["operation_id"] == result["detail"]["id"],
             "S05B2B2_ORIGINAL_JOURNAL_RECEIPT_MISSING")
    before = s04.snapshot()
    status = s04.run([str(SERVICE), "status", "--json"], timeout=70)
    after = s04.snapshot()
    s04.need(before == after and status.returncode == 2,
             "S05B2B2_STATUS_NOT_READONLY_OR_INCOMPLETE")
    row = json.loads(status.stdout)
    error = row.get("last_error")
    s04.need(row.get("runtime_state") == "INCOMPLETE" and
             row.get("diagnostic_state") == "qualified" and
             type(error) is dict and error.get("code") == "ENGINE_START_UNVERIFIED"
             and error.get("stage") == "engine-start" and
             error.get("operation_id") == result["detail"]["id"] and
             error.get("exit_status") is None and error.get("stderr_excerpt") is None,
             "S05B2B2_UNQUALIFIED_JSON_DIAGNOSIS")
    s04.need(not any(s in status.stdout for s in ("--filter-", "token=",
             "/conf/config.xml", "127.0.0.1")),
             "S05B2B2_PRIVATE_DATA_LEAK")
    return {"status": "PASS", "real_native_early_fault": True,
            "original_fd9_journal": True, "read_only_status": True,
            "exit_status_unknown": True,
            "foreign_rule_check": "verified" if before_foreign is not None else "not-applicable",
            "operator_device_touched": False}


def main(argv):
    if argv == ["--self-test"]:
        src = Path(__file__).read_text()
        ast.parse(src)
        assert "s04.guest_gate(\"hot\")" in src
        assert "ZAPRET2_S05B2B2_DISPOSABLE_NATIVE" in src
        assert "os.kill(int(pid), signal.SIGTERM)" in src
        print("S05B2B2_SOURCE_GATE=PASS")
        return 0
    if argv != ["hot"]:
        return 64
    try:
        print("S05B2B2_NATIVE=" + json.dumps(real_native(), sort_keys=True))
        return 0
    except Exception as exc:
        # NO arbitrary native stderr/log/source strings to CI output.
        label = "UNQUALIFIED_NATIVE_FAILURE"  # never echo exception payload
        print("S05B2B2_NATIVE=REFUSED:" + label, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
