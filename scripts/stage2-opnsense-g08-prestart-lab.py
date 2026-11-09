#!/usr/bin/env python3
"""G08 S2: real Standard and Extended Lab BEFORE any ordinary Zapret2 Start.

ONE disposable OPNsense 26.7: G05 authentic WAN Save without upstream,
G03 authentic upstream setup while STOPPED, then two real stock HTTPS Lab
jobs. Never start the normal service to prepare this witness.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
PID = Path("/var/run/dvtws2.pid")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
LAB_PATH = "/api/zapret/strategy_lab/"
TARGET = "yandex.ru"
OWNED = re.compile(r"^19(?:0[0-9]{2}|1(?:0[0-9]|[12][0-9]|3[01]))\s")
JOB = re.compile(r"job\.[A-Za-z0-9]{4,40}\Z")
TIMEOUT_SECONDS = 440


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def module(name):
    spec = importlib.util.spec_from_file_location(
        "g08_" + name.replace("-", "_").replace(".", "_"),
        ROOT / name)
    target = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(target)
    return target


def command(*argv, timeout=30):
    return subprocess.run(list(argv), check=False, capture_output=True,
                          text=True, timeout=timeout)


def observed_rules():
    result = command("/sbin/ipfw", "-q", "list", timeout=15)
    # IPFW may be unloaded until Lab loads it. Native 71 is not a rule.
    if result.returncode and not result.stdout.strip():
        return None
    need(result.returncode == 0, "G08_IPFW_CANNOT_BE_INSPECTED")
    return result.stdout.splitlines()


def partition_rules(rows):
    if rows is None:
        return [], []
    return ([line for line in rows if OWNED.match(line)],
            [line for line in rows if not OWNED.match(line)])


def state(web, expected):
    record = web.api("POST", "/api/zapret/service/runtime")
    need(record.get("status") == "ok" and
         record.get("installed") is True and record.get("busy") is False and
         record.get("service") == expected and
         record.get("setup") == "ready" and
         record.get("version") == "v1.0.7" and
         "reason" not in record,
         "G08_GENUINE_NATIVE_STATUS_NOT_" + expected.upper())


def stopped_truth(web, saved, foreign_before):
    state(web, "stopped")
    result = command(str(SERVICE), "status")
    need(result.returncode == 1 and "not running" in result.stdout,
         "G08_NATIVE_SERVICE_NOT_STOPPED")
    need(not PID.exists() and not PID.is_symlink() and
         CONFIG.read_bytes() == saved,
         "G08_LAB_CHANGED_SAVED_CONFIG_OR_NORMAL_PID")
    ps = command("/bin/ps", "-ax", "-o", "command=")
    need(ps.returncode == 0 and
         not any(line.startswith(str(ENGINE)) for line in ps.stdout.splitlines()),
         "G08_LAB_LEFT_REAL_DVTWS_ENGINE")
    owned, foreign = partition_rules(observed_rules())
    need(not owned, "G08_LAB_LEFT_19000_19131_IPFW")
    # The kernel's default allow line may first appear when Lab loads IPFW.
    if foreign_before:
        need(foreign == foreign_before, "G08_LAB_CHANGED_FOREIGN_IPFW")
    else:
        need(all(row.startswith("65535 ") for row in foreign),
             "G08_LAB_ADDED_UNOWNED_FIREWALL_RULES")


def stage(result, number):
    stages = result.get("stages")
    need(isinstance(stages, list) and len(stages) < 64,
         "G08_TERMINAL_STAGES_MISSING")
    entries = [row for row in stages if isinstance(row, dict) and
               row.get("number") == number]
    need(len(entries) == 1, "G08_MISSING_NATIVE_STAGE_" + number)
    return entries[0]


def terminal(result, job, mode, language):
    need(result.get("job_id") == job and
         result.get("state") == "completed" and
         result.get("current_stage") == "99" and
         result.get("initial_service_state") == "STOPPED" and
         result.get("mode") == mode and
         result.get("target") == TARGET and
         result.get("target_type") == "domain" and
         result.get("ipv6_enabled") is False,
         "G08_TERMINAL_NOT_PRESTART_" + mode.upper())
    # Same genuine public verified-TLS control used by accepted Stage5
    # running-service job. It may legitimately be accessible before search:
    # do NOT claim Strategy Search/Stage-50 or DPI bypass in that branch.
    need(result.get("outcome") == "TARGET_ACCESSIBLE" and
         stage(result, "50").get("status") == "SKIPPED",
         "G08_REAL_BASELINE_NOT_ACCESSIBLE_" + mode.upper())
    for n in ("00", "10", "20", "30", "40", "90"):
        need(stage(result, n).get("status") == "PASS",
             "G08_NATIVE_STAGE_" + n + "_FAILED_" + mode.upper())
    restoration = result.get("restoration")
    need(isinstance(restoration, dict) and
         restoration.get("verified") is True and
         restoration.get("initial_state") == "STOPPED" and
         restoration.get("final_state") == "STOPPED" and
         restoration.get("strategy_unchanged") is True and
         restoration.get("temporary_runtime_clean") is True,
         "G08_NATIVE_STAGE90_STOPPED_NOT_VERIFIED_" + mode.upper())
    network = result.get("network")
    baseline = result.get("baseline")
    need(isinstance(network, dict) and network.get("ipv4") == "available" and
         isinstance(baseline, dict) and
         baseline.get("all_accessible") is True and
         baseline.get("target") == TARGET,
         "G08_NATIVE_EXTERNAL_TLS_CONTROL_NOT_QUALIFIED")
    return {"mode": mode, "language": language, "job_id": job,
            "outcome": result["outcome"], "restore": "STOPPED",
            "stage30": "PASS", "stage40": "PASS", "stage90": "PASS",
            "stage50_search_performed": False}


def poll(web, job, mode, language):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    failures = 0
    while time.monotonic() < deadline:
        try:
            response = web.api("POST", LAB_PATH + "status", {"job_id": job})
        except (OSError, RuntimeError, ValueError):
            failures += 1
            need(failures < 3, "G08_READONLY_JOB_STATUS_UNAVAILABLE")
            time.sleep(2)
            continue
        failures = 0
        need(isinstance(response, dict) and response.get("job_id") == job,
             "G08_JOB_STATUS_WRONG_ID")
        current = response.get("state")
        need(current in ("queued", "running", "cancel_requested",
                         "completed", "error"),
             "G08_JOB_UNTRUSTED_STATE")
        if current in ("completed", "error"):
            return terminal(web.api("POST", LAB_PATH + "result",
                                    {"job_id": job}), job, mode, language)
        time.sleep(2)
    raise Refusal("G08_NATIVE_JOB_TIMED_OUT_" + mode.upper())


def run_job(web, mode, language, saved, foreign):
    need(web.api("POST", LAB_PATH + "status", {"job_id": "@active"}).get("status")
         == "idle", "G08_PREVIOUS_JOB_STILL_ACTIVE")
    job = None
    finished = False
    try:
        started = web.api("POST", LAB_PATH + "start", {
            "target": TARGET, "mode": mode, "language": language,
            "enable_quic": "0", "ipv6_enabled": "0",
        })
        need(started.get("status") == "ok" and
             started.get("state") == "queued" and
             isinstance(started.get("job_id"), str) and
             JOB.fullmatch(started["job_id"]) is not None,
             "G08_PRESTART_JOB_NOT_CREATED_" + mode.upper())
        job = started["job_id"]
        report = poll(web, job, mode, language)
        finished = True
    finally:
        if job is not None and not finished:
            try:
                web.api("POST", LAB_PATH + "cancel", {"job_id": job})
            except (RuntimeError, OSError):
                pass
            # A failed or ambiguous job stays a native failure: never
            # label a cancel request as verified recovery.
    need(web.api("POST", LAB_PATH + "status", {"job_id": "@active"}).get("status")
         == "idle", "G08_JOB_ACTIVE_POINTER_NOT_RELEASED")
    stopped_truth(web, saved, foreign)
    return report


def self_test():
    known = {"job_id": "job.Abc123", "state": "completed",
             "outcome": "TARGET_ACCESSIBLE", "current_stage": "99",
             "initial_service_state": "STOPPED", "mode": "standard",
             "target": TARGET, "target_type": "domain", "ipv6_enabled": False,
             "network": {"ipv4": "available"},
             "baseline": {"all_accessible": True, "target": TARGET},
             "restoration": {"verified": True, "initial_state": "STOPPED",
                             "final_state": "STOPPED", "strategy_unchanged": True,
                             "temporary_runtime_clean": True},
             "stages": [{"number": n, "status": ("SKIPPED" if n == "50" else "PASS")}
                        for n in ("00", "10", "20", "30", "40", "50", "90", "99")]}
    need(terminal(known, "job.Abc123", "standard", "en")["restore"] == "STOPPED",
         "G08_SOURCE_POSITIVE_NOT_VERIFIED")
    for fake in (
        {**known, "initial_service_state": "RUNNING"},
        {**known, "outcome": "ERROR"},
        {**known, "restoration": {**known["restoration"], "verified": False}},
        {**known, "stages": [{**x, "status": "FAIL"} if x["number"] == "90" else x
                             for x in known["stages"]]},
        {**known, "mode": "extended"},
    ):
        try:
            terminal(fake, "job.Abc123", "standard", "en")
        except Refusal:
            continue
        raise AssertionError("G08_UNVERIFIED_NATIVE_JOB_ACCEPTED")
    print("G08_PRESTART_NATIVE_SOURCE=PASS")


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G08_NATIVE_PRESTART") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "G08_ONE_DISPOSABLE_OPNSENSE_ROOT_REQUIRED")
    head = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(re.fullmatch(r"[a-f0-9]{40}", head) is not None,
         "G08_EXACT_GITHUB_SOURCE_ID_REQUIRED")
    g05 = module("stage2-opnsense-g05-wan-save.py")
    g03 = module("stage2-opnsense-g03-first-install.py")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    # G05 builds the real Mk archive, proves no-WAN precedence, then SAVES
    # a real WAN with genuinely no upstream or ordinary engine Start.
    g05.main()
    need(not ENGINE.exists() and not JOURNAL.exists(),
         "G08_G05_DID_NOT_LEAVE_NEVER_STARTED_RUNTIME")
    # G03 installs genuine upstream by stock configd, never starts service.
    g03.main()
    need(ENGINE.is_file() and not ENGINE.is_symlink() and
         not JOURNAL.exists() and not PID.exists(),
         "G08_G03_ENGINE_NOT_CLEAN_STOPPED_PRESTART")
    initial = CONFIG.read_bytes()
    model = ET.fromstring(initial).find("./OPNsense/Zapret")
    need(model is not None and model.findtext("general/enabled") == "0" and
         model.findtext("general/waninterface") == "wan" and
         not (model.findtext("strategy/trafficargs") or "") and
         not (model.findtext("hostlist/youtubedomains") or ""),
         "G08_LAB_DOES_NOT_START_WITH_TRULY_EMPTY_STOPPED_CONFIG")

    web = voice.GuestHttps()
    voice.login(web)
    state(web, "stopped")
    owned, foreign = partition_rules(observed_rules())
    need(not owned and not PID.exists(), "G08_PRESTART_OWNED_IPFW_OR_PID")
    stopped_truth(web, initial, foreign)
    standard = run_job(web, "standard", "ru", initial, foreign)
    extended = run_job(web, "extended", "en", initial, foreign)
    need(standard["job_id"] != extended["job_id"] and
         not JOURNAL.exists(), "G08_LAB_FABRICATED_COMMON_APPLY_OWNER")
    stopped_truth(web, initial, foreign)
    print("G08_NATIVE_PRESTART=" + json.dumps({
        "status": "PASS_G08_REAL_STANDARD_EXTENDED_BEFORE_FIRST_NORMAL_START",
        "source_sha": head,
        "g05_wan_first_and_engine_second_proven": True,
        "g03_native_upstream_installed_without_first_start": True,
        "ordinary_enabled": False,
        "ordinary_strategy": "user_empty",
        "initial_and_final_service": "STOPPED",
        "real_auth_https_jobs": [standard, extended],
        "stock_fd9_no_foreign_config_ipfw_mutation": True,
        "real_strategy_search_tested": False,
        "real_DPI_bypass_tested": False,
        "physical_owner_browser_tested": False,
        "IPv6_and_reboot_tested": False,
    }, sort_keys=True))


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:] == ["run"]:
            execute()
        else:
            raise Refusal("G08_SELF_TEST_OR_RUN_REQUIRED")
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            subprocess.TimeoutExpired, ET.ParseError) as error:
        print("G08_NATIVE_PRESTART=REFUSED:" + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
