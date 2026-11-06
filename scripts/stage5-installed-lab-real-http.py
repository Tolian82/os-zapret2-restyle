#!/usr/bin/env python3
"""One genuine installed Strategy Lab job over stock cookie/CSRF OPNsense HTTPS.

Only on a CI-disposable OPNsense 26.7 guest already running the verified
Strategies/Voice FD9 owner. Uses the unmodified shipped launcher/worker/probes,
including the genuine external Stage-30 yandex.ru TLS control; localhost is
ONLY the user-chosen target. TARGET_ACCESSIBLE is a successful job lifecycle
and explicitly NOT evidence that any DPI bypass succeeded.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sys
import time

HERE = Path(__file__).resolve().parent
FLAG = "ZAPRET2_STAGE5_REAL_LAB_POSITIVE"
TARGET = "127.0.0.1"
LAB = "/api/zapret/strategy_lab/"
STATUS = "PASS_STAGE5_INSTALLED_REAL_LAB_TARGET_ACCESSIBLE_AND_RESTORE"
JOB_PATTERN = re.compile(r"job\.[A-Za-z0-9]{4,40}\Z")
TIME_LIMIT = 360


class Refusal(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def module(name):
    spec = importlib.util.spec_from_file_location(
        "stage5_lab_positive_" + name.replace("-", "_").replace(".", "_"),
        HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def qualified_start(value):
    need(isinstance(value, dict) and value.get("status") == "ok" and
         value.get("state") == "queued" and
         isinstance(value.get("job_id"), str) and
         JOB_PATTERN.fullmatch(value["job_id"]) is not None,
         "LAB_POSITIVE_UNTRUSTED_AUTHENTICATED_START")
    return value["job_id"]


def stage(value, number):
    entries = value.get("stages")
    need(isinstance(entries, list) and len(entries) < 64,
         "LAB_POSITIVE_INVALID_STAGE_COLLECTION")
    found = [x for x in entries if isinstance(x, dict) and x.get("number") == number]
    need(len(found) == 1, "LAB_POSITIVE_UNQUALIFIED_STAGE_" + number)
    return found[0]


def qualified_terminal(value, job):
    need(isinstance(value, dict) and value.get("status") != "running" and
         value.get("job_id") == job and value.get("state") == "completed" and
         value.get("outcome") == "TARGET_ACCESSIBLE" and
         value.get("current_stage") == "99" and
         value.get("initial_service_state") == "RUNNING" and
         value.get("target") == TARGET and value.get("target_type") == "ip" and
         value.get("mode") == "standard" and
         value.get("ipv6_enabled") is False,
         "LAB_POSITIVE_UNQUALIFIED_COMPLETED_RESULT")
    for number in ("00", "10", "20", "30", "40", "90"):
        need(stage(value, number).get("status") == "PASS",
             "LAB_POSITIVE_REAL_STAGE_NOT_PASS_" + number)
    need(stage(value, "50").get("status") == "SKIPPED",
         "LAB_POSITIVE_FALSE_STRATEGY_SEARCH_CLAIM")
    net = value.get("network")
    baseline = value.get("baseline")
    need(isinstance(net, dict) and net.get("ipv4") == "available",
         "LAB_POSITIVE_REAL_EXTERNAL_CONTROL_NOT_AVAILABLE")
    need(isinstance(baseline, dict) and
         baseline.get("target") == TARGET and
         baseline.get("target_type") == "ip" and
         baseline.get("all_accessible") is True and
         isinstance(baseline.get("endpoints"), list) and
         len(baseline["endpoints"]) == 1 and
         baseline["endpoints"][0].get("endpoint") == TARGET and
         baseline["endpoints"][0].get("status") == "PASS" and
         baseline["endpoints"][0].get("transport") == "tcp-443" and
         baseline["endpoints"][0].get("exit_code") == 0,
         "LAB_POSITIVE_REAL_LOOPBACK_TCP_BASELINE_NOT_ATTESTED")
    return value


def poll(web, job):
    states = []
    deadline = time.monotonic() + TIME_LIMIT
    while time.monotonic() < deadline:
        item = web.api("POST", LAB + "status", {"job_id": job})
        need(isinstance(item, dict) and item.get("job_id") == job,
             "LAB_POSITIVE_STATUS_JOB_ID_MISMATCH")
        state = item.get("state")
        need(state in ("queued", "running", "cancel_requested", "completed", "error"),
             "LAB_POSITIVE_UNEXPECTED_JOB_STATE")
        if state not in states:
            states.append(state)
        if state in ("completed", "error"):
            result = web.api("POST", LAB + "result", {"job_id": job})
            return qualified_terminal(result, job), states
        time.sleep(1)
    raise Refusal("LAB_POSITIVE_REAL_JOB_DEADLINE_EXCEEDED")


def cancel_if_active(web, job):
    # Failure-only bounded cleanup; never turn a canceled run into PASS.
    if not job:
        return
    try:
        item = web.api("POST", LAB + "status", {"job_id": job})
        if item.get("state") not in ("queued", "running", "cancel_requested"):
            return
        web.api("POST", LAB + "cancel", {"job_id": job})
        until = time.monotonic() + 90
        while time.monotonic() < until:
            item = web.api("POST", LAB + "status", {"job_id": job})
            if item.get("state") in ("completed", "error"):
                return
            time.sleep(2)
    except (OSError, ValueError, RuntimeError, KeyError):
        pass
    print("STAGE5_REAL_LAB_FAILURE_CLEANUP=NOT_VERIFIED", file=sys.stderr)


def self_test():
    job = "job.Abc123"
    assert qualified_start({"status": "ok", "state": "queued", "job_id": job}) == job
    for value in ({"status": "ok", "state": "queued", "job_id": "../../bad"},
                  {"status": "ok", "state": "running", "job_id": job},
                  {"status": "error", "state": "queued", "job_id": job}):
        try:
            qualified_start(value)
        except Refusal:
            pass
        else:
            raise AssertionError("Unsafe Strategy Lab Start accepted")
    sample = {
        "status": "ok", "job_id": job, "state": "completed",
        "outcome": "TARGET_ACCESSIBLE", "current_stage": "99",
        "initial_service_state": "RUNNING", "target": TARGET,
        "target_type": "ip", "mode": "standard", "ipv6_enabled": False,
        "network": {"ipv4": "available"},
        "baseline": {"target": TARGET, "target_type": "ip", "all_accessible": True,
                     "endpoints": [{"endpoint": TARGET, "status": "PASS",
                                    "transport": "tcp-443", "exit_code": 0}]},
        "stages": [{"number": x, "status": ("SKIPPED" if x == "50" else "PASS")}
                   for x in ("00", "10", "20", "30", "40", "50", "90", "99")],
    }
    assert qualified_terminal(sample, job) == sample
    for broken in (
        {**sample, "outcome": "SUCCESS"},
        {**sample, "network": {"ipv4": "unavailable"}},
        {**sample, "baseline": {**sample["baseline"], "all_accessible": False}},
        {**sample, "stages": [{**x, "status": "FAIL"} if x["number"] == "90" else x
                              for x in sample["stages"]]},
    ):
        try:
            qualified_terminal(broken, job)
        except Refusal:
            pass
        else:
            raise AssertionError("Fake Strategy Lab result accepted")
    print("PASS_STAGE5_INSTALLED_REAL_LAB_POSITIVE_SOURCE_GUARDS")


def execute():
    for key in ("GITHUB_ACTIONS", "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_NATIVE_BUILD_CI",
                "ZAPRET2_STAGE5_RUNNING_VOICE_ARTIFACT", FLAG):
        need(os.environ.get(key) == ("true" if key == "GITHUB_ACTIONS" else "1"),
             "LAB_POSITIVE_DISPOSABLE_CI_OPTIN_MISSING:" + key)
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "LAB_POSITIVE_NOT_NATIVE_DISPOSABLE_OPNSENSE")
    active = module("stage2-opnsense-real-native-active-service.py")
    common = module("stage2-opnsense-real-native-shared-voice.py")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    engine_sha = active.guest_preflight()
    initial = common.witness(active, engine_sha, running=True, page="strategies")
    before_config = active.CONFIG.read_bytes()
    before_rules = active.plugin_rules()
    need(initial["id"] and initial["pid"] > 1 and len(before_rules) == 2,
         "LAB_POSITIVE_INVALID_INITIAL_FD9_AND_IPFW")
    with socket.create_connection((TARGET, 443), timeout=4):
        pass

    web = voice.GuestHttps()
    voice.login(web)
    need(web.api("POST", LAB + "status", {"job_id": "@active"}).get("status") == "idle",
         "LAB_POSITIVE_PREEXISTING_ACTIVE_JOB")
    job = None
    finished = False
    try:
        job = qualified_start(web.api("POST", LAB + "start", {
            "target": TARGET, "mode": "standard", "language": "en",
            "enable_quic": "0", "ipv6_enabled": "0",
        }))
        result, states = poll(web, job)
        finished = True
    finally:
        if not finished:
            cancel_if_active(web, job)

    need("running" in states or (
         "queued" in states and stage(result, "30").get("status") == "PASS"),
         "LAB_POSITIVE_NO_CORRELATED_RUNNING_STATE")
    need(web.api("POST", LAB + "status", {"job_id": "@active"}).get("status") == "idle",
         "LAB_POSITIVE_ACTIVE_JOB_NOT_RELEASED")
    after = common.witness(active, engine_sha, running=True, page="strategies")
    need(initial["id"] == after["id"] and initial["rules"] == after["rules"] and
         initial["pid"] != after["pid"] and
         active.CONFIG.read_bytes() == before_config and
         active.plugin_rules() == before_rules,
         "LAB_POSITIVE_INITIAL_SHARED_OWNER_OR_CONFIG_NOT_RESTORED")
    report = {
        "schema": 1, "status": STATUS, "job_terminal_outcome": "TARGET_ACCESSIBLE",
        "authenticated_stock_https_csrf_start_status_result": True,
        "real_shipped_worker_control_tls_ipv4_available": True,
        "real_local_tcp443_baseline_passed": True,
        "job_completed_and_original_fd9_restored": True,
        "saved_native_config_and_ipfw_unchanged": True,
        "real_strategy_search_or_dpi_bypass_proven": False,
        "real_external_control_site_contacted": True,
        "physical_browser_click_tested": False, "owner_appliance_modified": False,
    }
    print("STAGE5_REAL_INSTALLED_LAB_JOB=" + json.dumps(report, sort_keys=True))
    return report


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:] == ["run"]:
            execute()
        else:
            raise Refusal("LAB_POSITIVE_EXPECTED_RUN_OR_SELF_TEST")
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE5_REAL_INSTALLED_LAB_JOB=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)
