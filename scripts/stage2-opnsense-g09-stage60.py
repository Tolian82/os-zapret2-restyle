#!/usr/bin/env python3
"""G09 installed OPNsense negative-control: real Stage50->Stage60 before normal Start.
Qualifies a routed public IPv4 TCP/443-negative control, not an ISP DPI bypass.
"""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
JOBS = Path("/var/run/zapret2-restyle/strategy-lab/jobs")
TARGET = ""
PUBLIC_CONTROLS = ("4.2.2.2", "4.2.2.1", "208.67.222.222",
                   "208.67.220.220", "9.9.9.10")
LAB = "/api/zapret/strategy_lab/"

class Refusal(RuntimeError):
    pass

def need(value, reason):
    if not value:
        raise Refusal(reason)

def module(name):
    spec = importlib.util.spec_from_file_location("g09_" + name.replace("-", "_").replace(".", "_"), ROOT / name)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def artifact(job, name):
    path = JOBS / job / name
    need(path.is_file() and not path.is_symlink(), "G09_MISSING_NATIVE_" + name)
    result = json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(result, dict), "G09_BAD_NATIVE_" + name)
    return result

def diagnostic(job):
    record = {"job_id": job}
    for name in ("status.json", "candidate-smoke.json", "parameter-expansion.json"):
        try:
            value = artifact(job, name)
            keys = ("state", "outcome", "current_stage", "stages", "restoration") if name == "status.json" else (
                ("accepted", "completed", "search_epoch_id") if name == "candidate-smoke.json" else
                ("completed", "total_available", "working", "partial", "stopped_reason", "search_epoch_id", "parallel"))
            record[name] = {key: value.get(key) for key in keys}
        except (OSError, ValueError, Refusal) as exc:
            record[name] = {"error": str(exc)}
    try:
        family = artifact(job, "candidate-smoke.json")
        items = family.get("families", [])
        record["stage50_candidate_diagnostics"] = [
            {key: candidate.get(key)
             for key in ("id", "all_pass", "timeout", "error", "runner_status",
                         "error_code", "error_message", "message")}
            for candidate in items[:7] if isinstance(candidate, dict)
        ] if isinstance(items, list) else []
    except (OSError, ValueError, Refusal):
        pass
    return record

def qualify_negative_control():
    checked = []
    for ip in PUBLIC_CONTROLS:
        route = subprocess.run(["/sbin/route", "-n", "get", ip],
                               capture_output=True, text=True, check=False, timeout=5)
        match = re.search(r"(?m)^\s*interface:\s*(\S+)\s*$", route.stdout)
        iface = match.group(1) if match else ""
        if route.returncode or not iface or iface.startswith(("lo", "tun")):
            checked.append({"ip": ip, "route_rc": route.returncode,
                            "interface": iface, "qualifies": False})
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.5)
            try:
                connect_code = sock.connect_ex((ip, 443))
            except OSError:
                connect_code = -1
        checked.append({"ip": ip, "interface": iface,
                        "tcp443_connect_code": connect_code,
                        "qualifies": connect_code != 0})
        if connect_code != 0:
            print("G09_PUBLIC_NEGATIVE_CONTROL=" +
                  json.dumps({"selected": ip, "interface": iface,
                              "checked": checked}, sort_keys=True), flush=True)
            return ip
    raise Refusal("G09_NO_ROUTED_TCP443_NEGATIVE_CONTROL:" +
                  json.dumps(checked, sort_keys=True))

def readonly_preflight_diagnostic():
    probes = {
        "ipfw_module": ["/sbin/kldstat", "-q", "-m", "ipfw"],
        "ipdivert_module": ["/sbin/kldstat", "-q", "-m", "ipdivert"],
        "ipfw_enabled": ["/sbin/sysctl", "-n", "net.inet.ip.fw.enable"],
        "ipfw_reserved_19128": ["/sbin/ipfw", "list", "19128"],
    }
    result = {}
    for name, argv in probes.items():
        try:
            call = subprocess.run(argv, check=False, capture_output=True,
                                  text=True, timeout=5)
            result[name] = {"exit": call.returncode,
                            "stdout": call.stdout.strip()[:250],
                            "stderr": call.stderr.strip()[:250]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            result[name] = {"error": str(exc)}
    for name, path in {
        "engine": "/usr/local/etc/zapret2/binaries/my/dvtws2",
        "daemon": "/usr/sbin/daemon",
    }.items():
        result[name] = {"exists": Path(path).is_file(),
                        "executable": os.access(path, os.X_OK)}
    return result

def accepted(g08, result, job):
    need(result.get("job_id") == job and result.get("target") == TARGET and
         result.get("target_type") == "ip" and result.get("mode") == "standard" and
         result.get("ipv6_enabled") is False and
         result.get("initial_service_state") == "STOPPED",
         "G09_NOT_REAL_STOPPED_IP_TARGET")
    need(result.get("outcome") == "NO_CANDIDATE" and result.get("state") == "completed" and
         result.get("current_stage") == "99",
         "G09_WRONG_TERMINAL_OUTCOME")
    for number in ("00", "10", "20", "30", "40", "50", "60", "70", "85", "90", "99"):
        need(g08.stage(result, number).get("status") == "PASS",
             "G09_REQUIRED_STAGE_NOT_PASS_" + number)
    restoration = result.get("restoration")
    need(isinstance(restoration, dict) and restoration.get("verified") is True and
         restoration.get("initial_state") == "STOPPED" and
         restoration.get("final_state") == "STOPPED" and
         restoration.get("strategy_unchanged") is True and
         restoration.get("temporary_runtime_clean") is True,
         "G09_STAGE90_NOT_RESTORED")
    baseline = result.get("baseline")
    need(isinstance(baseline, dict) and baseline.get("all_accessible") is False,
         "G09_NEGATIVE_CONTROL_BECAME_ACCESSIBLE")
    family = artifact(job, "candidate-smoke.json")
    expansion = artifact(job, "parameter-expansion.json")
    need(family.get("accepted") == [] and type(family.get("completed")) is int and
         family["completed"] > 0, "G09_STAGE50_NOT_ALL_REJECTED")
    need(expansion.get("search_epoch_id") == family.get("search_epoch_id") and
         type(expansion.get("completed")) is int and expansion["completed"] > 0 and
         expansion.get("working") == [] and
         expansion.get("stopped_reason") == "graph_exhausted" and
         expansion.get("partial") is False, "G09_STAGE60_NOT_EXHAUSTED")
    return {"job_id": job, "outcome": "NO_CANDIDATE",
            "stage50_completed": family["completed"],
            "stage60_completed": expansion["completed"],
            "stage60_stopped_reason": expansion["stopped_reason"],
            "stage90": "STOPPED_RESTORED"}

def poll(g08, web, job):
    deadline = time.monotonic() + 860
    failures = 0
    while time.monotonic() < deadline:
        try:
            state = web.api("POST", LAB + "status", {"job_id": job})
            need(state.get("job_id") == job, "G09_JOB_STATUS_ID_MISMATCH")
        except (RuntimeError, OSError, ValueError, http.client.HTTPException):
            failures += 1
            need(failures < 3, "G09_STATUS_UNAVAILABLE")
            time.sleep(2)
            continue
        failures = 0
        need(state.get("state") in ("queued", "running", "cancel_requested",
                                    "completed", "error"), "G09_UNKNOWN_JOB_STATE")
        if state["state"] in ("completed", "error"):
            return accepted(g08, web.api("POST", LAB + "result",
                                        {"job_id": job}), job)
        time.sleep(2)
    raise Refusal("G09_JOB_DEADLINE_EXCEEDED")

def source_test():
    g08 = module("stage2-opnsense-g08-prestart-lab.py")
    original = {"stages": [{"number": n, "status": "PASS"}
                           for n in ("00", "10", "20", "30", "40", "50", "60", "70", "85", "90", "99")]}
    need(g08.stage(original, "60")["status"] == "PASS",
         "G09_SOURCE_STAGE60_WRONG")
    for status in ("ERROR", "TIMEOUT", "SKIPPED"):
        fake = {"stages": [{"number": "60", "status": status}]}
        try:
            need(g08.stage(fake, "60")["status"] == "PASS",
                 "G09_SOURCE_REJECTS_NON_PASS")
        except Refusal:
            continue
        raise AssertionError("G09_SOURCE_FALSE_PASS")
    print("G09_STAGE60_SOURCE=PASS")

def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G09_NATIVE_STAGE60") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "G09_REQUIRES_DISPOSABLE_OPNSENSE_ROOT")
    head = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(re.fullmatch(r"[a-f0-9]{40}", head) is not None, "G09_REQUIRES_EXACT_HEAD")
    g08 = module("stage2-opnsense-g08-prestart-lab.py")
    g08.module("stage2-opnsense-g05-wan-save.py").main()
    need(not g08.ENGINE.exists() and not g08.JOURNAL.exists(),
         "G09_NOT_COLD_NO_ENGINE")
    g08.module("stage2-opnsense-g03-first-install.py").main()
    saved = g08.CONFIG.read_bytes()
    config = ET.fromstring(saved).find("./OPNsense/Zapret")
    need(config is not None and config.findtext("general/waninterface") == "wan" and
         config.findtext("general/enabled") == "0" and
         not (config.findtext("strategy/trafficargs") or ""),
         "G09_NOT_USER_EMPTY_WAN_SAVED")
    voice = g08.module("stage2-opnsense-real-native-voice-http.py")
    web = voice.GuestHttps()
    voice.login(web)
    owned, foreign = g08.partition_rules(g08.observed_rules())
    need(not owned, "G09_PREEXISTING_LAB_RULES")
    g08.stopped_truth(web, saved, foreign)
    # TEST-NET may be dropped before the WAN/IPFW rule. A Model-C packet
    # attribution control must have a genuine native route. No route changes.
    global TARGET
    TARGET = qualify_negative_control()
    need(web.api("POST", LAB + "status", {"job_id": "@active"}).get("status")
         == "idle", "G09_ACTIVE_JOB_BEFORE_START")
    job = None
    try:
        start = web.api("POST", LAB + "start", {
            "target": TARGET, "mode": "standard", "language": "ru",
            "enable_quic": "0", "ipv6_enabled": "0",
        })
        need(start.get("status") == "ok" and start.get("state") == "queued" and
             isinstance(start.get("job_id"), str) and
             g08.JOB.fullmatch(start["job_id"]) is not None,
             "G09_REAL_JOB_NOT_CREATED")
        job = start["job_id"]
        output = poll(g08, web, job)
        need(web.api("POST", LAB + "status", {"job_id": "@active"}).get("status")
             == "idle", "G09_ACTIVE_JOB_NOT_RELEASED")
        g08.stopped_truth(web, saved, foreign)
        need(not g08.JOURNAL.exists(), "G09_SHARED_FD9_JOURNAL_LEAK")
        print("G09_STAGE60_NATIVE=" + json.dumps({
            "status": "PASS_REAL_STAGE50_STAGE60_NO_CANDIDATE_RESTORED",
            "source_sha": head, "negative_control": TARGET,
            "negative_control_is_public_ip": True,
            "real_dpi_bypass_tested": False,
            "owner_blocked_youtube_tested": False,
            "ipv6_quic_cancel_timeout_tested": False,
            "native_job": output,
        }, sort_keys=True))
    except Exception:
        if job:
            print("G09_NATIVE_JOB_DIAGNOSTIC=" +
                  json.dumps(diagnostic(job), ensure_ascii=False, sort_keys=True),
                  file=sys.stderr)
            print("G09_NATIVE_PREFLIGHT_READONLY=" +
                  json.dumps(readonly_preflight_diagnostic(), sort_keys=True),
                  file=sys.stderr)
            try:
                web.api("POST", LAB + "cancel", {"job_id": job})
            except (OSError, RuntimeError, ValueError):
                pass
        raise

def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            source_test()
        elif sys.argv[1:] == ["run"]:
            execute()
        else:
            raise Refusal("G09_REQUIRES_SELF_TEST_OR_RUN")
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            ET.ParseError) as exc:
        print("G09_STAGE60_NATIVE=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
