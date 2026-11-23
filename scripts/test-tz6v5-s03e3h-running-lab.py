#!/usr/bin/env python3
"""TZ6v5 S03e3h: genuine RUNNING Common → real Lab → RUNNING restoration.

Strictly disposable OPNsense 26.7: exact official Mk-installed plugin, real
upstream v1.0.7, genuine installed HTTPS Strategies Apply/FD9 and Lab. No
synthetic service, Config writer, kernel IPFW alterations or owner appliance.
A failure leaves the original receipt and emits only bounded, nonsecret
terminal stage/physical status. Never automatically retries/starts/stops.
"""
from __future__ import annotations

import hashlib
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
REPO = ROOT.parent
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
PID = Path("/var/run/dvtws2.pid")
MONITOR = Path("/var/run/zapret2-supervisor-monitor.pid")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
LAB = "/api/zapret/strategy_lab/"
TARGET = "yandex.ru"
JOB_RE = re.compile(r"job\.[A-Za-z0-9]{4,40}\Z")
END_STATES = frozenset(("completed", "error"))
VALID_STAGES = frozenset(("PASS", "FAIL", "SKIPPED", "PENDING",
                           "RUNNING", "CANCELLED", "TIMEOUT", "ERROR"))
STAGE_NUMBERS = ("00", "10", "20", "30", "40", "50", "60",
                 "70", "80", "85", "90", "99")
OUTCOME_CLASSES = frozenset((
    "TARGET_ACCESSIBLE", "WORKING", "PARTIAL", "TIMEOUT",
    "ERROR", "RESTORE_FAILED", "NO_WORKING_STRATEGY",
    "NO_WORKING", "NOT_FOUND", "CANCELLED",
))
OWNED = re.compile(r"^(190[0-9]{2}|191(?:0[0-9]|[12][0-9]|3[01]))\s")
SOURCE_HEAD = "ZAPRET2_NATIVE_PROJECT_SHA"


class Refusal(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def module(file):
    spec = importlib.util.spec_from_file_location(
        "s03e3h_" + file.replace("-", "_").replace(".", "_"), ROOT / file)
    need(spec is not None and spec.loader is not None,
         "S03E3H_NATIVE_ORIGINAL_MODULE_NOT_FOUND")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def command(*args, timeout=30):
    return subprocess.run([str(arg) for arg in args], check=False,
                          capture_output=True, text=True, timeout=timeout)


def ipfw():
    result = command("/sbin/ipfw", "-q", "list", timeout=15)
    need(result.returncode == 0, "S03E3H_IPFW_NOT_READABLE")
    owned, foreign = [], []
    for row in result.stdout.splitlines():
        (owned if OWNED.match(row) else foreign).append(row)
    return owned, foreign


def engine_pids():
    observed = command("/bin/ps", "-ax", "-o", "pid=", "-o", "command=", timeout=20)
    need(observed.returncode == 0, "S03E3H_NATIVE_PROCESS_CENSUS_UNREADABLE")
    ids = []
    for row in observed.stdout.splitlines():
        parts = row.strip().split(None, 1)
        if len(parts) == 2 and parts[0].isdecimal() and (
                parts[1] == str(ENGINE) or parts[1].startswith(str(ENGINE) + " ")):
            ids.append(int(parts[0]))
    return ids


def current_owner():
    need(JOURNAL.is_file() and not JOURNAL.is_symlink(),
         "S03E3H_MISSING_REAL_COMMON_JOURNAL")
    value = json.loads(JOURNAL.read_bytes())
    identity = value.get("detail", {}).get("id", "")
    need(value.get("phase") == "committed" and
         re.fullmatch(r"[a-f0-9]{32}", identity) is not None,
         "S03E3H_COMMON_JOURNAL_NOT_COMMITTED")
    return identity


def physical(web, *, engine_sha):
    runtime = web.api("POST", "/api/zapret/service/runtime")
    need(runtime.get("status") == "ok" and
         runtime.get("installed") is True and runtime.get("service") == "started"
         and runtime.get("busy") is False and runtime.get("setup") == "ready"
         and runtime.get("version") == "v1.0.7",
         "S03E3H_COMMON_RUNTIME_NOT_VERIFIED_RUNNING")
    cli = command(SERVICE, "status", timeout=30)
    need(cli.returncode == 0 and "zapret is running" in cli.stdout,
         "S03E3H_COMMON_SHELL_STATUS_NOT_RUNNING")
    need(ENGINE.is_file() and not ENGINE.is_symlink() and
         hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_sha,
         "S03E3H_REAL_UPSTREAM_ENGINE_CHANGED")
    need(PID.is_file() and not PID.is_symlink(),
         "S03E3H_DVTWS_CHILD_PID_MISSING")
    pid = PID.read_text().strip()
    need(pid.isdecimal() and int(pid) > 1 and engine_pids() == [int(pid)],
         "S03E3H_NOT_EXACT_ONE_REAL_ENGINE")
    need(MONITOR.is_file() and not MONITOR.is_symlink(),
         "S03E3H_REAL_SUPERVISOR_PID_MISSING")
    monitor = MONITOR.read_text().strip()
    need(monitor.isdecimal() and int(monitor) > 1,
         "S03E3H_REAL_SUPERVISOR_PID_INVALID")
    ps = command("/bin/ps", "-p", monitor, "-o", "command=", timeout=20)
    need(ps.returncode == 0 and "supervisor_loop.sh" in ps.stdout,
         "S03E3H_NATIVE_SUPERVISOR_NOT_RUNNING")
    rules, foreign = ipfw()
    need(rules and all(line.startswith("190") for line in rules),
         "S03E3H_NORMAL_OWNER_IPFW_NOT_PRESENT")
    return {"owner": current_owner(), "pid": int(pid),
            "monitor": int(monitor), "owned": rules, "foreign": foreign}


def safe_stage(result, number):
    rows = result.get("stages")
    if not isinstance(rows, list) or len(rows) > 64:
        return "unknown"
    matched = [x.get("status") for x in rows
               if isinstance(x, dict) and x.get("number") == number]
    if len(matched) != 1 or matched[0] not in VALID_STAGES:
        return "unknown"
    return matched[0]


PHYSICAL_BOOL_KEYS = (
    "one_real_engine", "actual_pid_matches_census",
    "saved_config_unchanged", "owned_ipfw_unchanged",
    "foreign_ipfw_unchanged", "journal_committed", "after_lab_active_idle",
)


def verified_physical_report(report):
    """Status exit 0 is SUCCESS, not false. All seven witnesses must be bool True."""
    return (type(report) is dict and
            set(report) == set(PHYSICAL_BOOL_KEYS) | {"cli_status_rc"} and
            type(report["cli_status_rc"]) is int and
            report["cli_status_rc"] == 0 and
            all(report[key] is True for key in PHYSICAL_BOOL_KEYS))


def summarize(result):
    """Only literal stage statuses and bounded outcome; no raw target/errors."""
    restore = result.get("restoration")
    restore = restore if isinstance(restore, dict) else {}
    outcome = result.get("outcome")
    outcome_class = outcome if type(outcome) is str and outcome in OUTCOME_CLASSES else "unknown"
    return {
        "job_terminal": result.get("state") in END_STATES,
        "stage90": safe_stage(result, "90"),
        "stage99": safe_stage(result, "99"),
        "stage_statuses": {n: safe_stage(result, n) for n in STAGE_NUMBERS},
        "outcome_class": outcome_class,
        "restoration_verified": restore.get("verified") is True,
        "restoration_initial_running": restore.get("initial_state") == "RUNNING",
        "restoration_final_running": restore.get("final_state") == "RUNNING",
        "strategy_unchanged": restore.get("strategy_unchanged") is True,
        "temporary_runtime_clean": restore.get("temporary_runtime_clean") is True,
    }


def acceptance(result):
    data = summarize(result)
    return (result.get("state") == "completed" and
            result.get("current_stage") == "99" and
            result.get("initial_service_state") == "RUNNING" and
            data["stage90"] == "PASS" and data["stage99"] == "PASS" and
            all(data[k] is True for k in (
                "restoration_verified", "restoration_initial_running",
                "restoration_final_running", "strategy_unchanged",
                "temporary_runtime_clean")))


def self_test():
    valid = {"state": "completed", "current_stage": "99",
             "initial_service_state": "RUNNING",
             "stages": [{"number": "90", "status": "PASS"},
                        {"number": "99", "status": "PASS"}],
             "restoration": {
                 "verified": True, "initial_state": "RUNNING",
                 "final_state": "RUNNING", "strategy_unchanged": True,
                 "temporary_runtime_clean": True},
             "raw_error": "sensitive.private.example",
             "target": "sensitive.private.example"}
    need(acceptance(valid), "S03E3H_GOOD_TERMINAL_REJECTED")
    need(summarize({**valid, "outcome": "sensitive.private.example"})["outcome_class"]
         == "unknown", "S03E3H_UNTRUSTED_OUTCOME_NOT_REDACTED")
    need("sensitive.private.example" not in json.dumps(summarize(valid)),
         "S03E3H_TERMINAL_REDACTION_FAILED")
    for bad in (
        {**valid, "state": "error"},
        {**valid, "restoration": {**valid["restoration"], "verified": False}},
        {**valid, "stages": [{"number": "90", "status": "FAIL"},
                            {"number": "99", "status": "FAIL"}]},
        {**valid, "restoration": {**valid["restoration"],
                                   "final_state": "STOPPED"}},
    ):
        need(not acceptance(bad),
             "S03E3H_FAKE_RESTORATION_ACCEPTED")
    need(OWNED.match("19099 foo") is not None and
         OWNED.match("19131 foo") is not None and
         OWNED.match("19140 foo") is None and
         OWNED.match("65534 foo") is None,
         "S03E3H_INVALID_IPFW_NUMERIC_OWNERSHIP")
    # Regression: Unix successful status rc0 must not be tested by all(values).
    proven = {"cli_status_rc": 0, **{k: True for k in PHYSICAL_BOOL_KEYS}}
    need(verified_physical_report(proven),
         "S03E3H_SUCCESSFUL_CLI_RC0_REJECTED")
    for changed in (
        {**proven, "cli_status_rc": 1},
        {**proven, "cli_status_rc": False},
        {**proven, "cli_status_rc": "0"},
        {**proven, "one_real_engine": False},
        {**proven, "journal_committed": 1},
        {k: v for k, v in proven.items() if k != "foreign_ipfw_unchanged"},
    ):
        need(not verified_physical_report(changed),
             "S03E3H_UNVERIFIED_PHYSICAL_STATE_ACCEPTED")
    print("S03E3H_RUNNING_LAB_FAST=PASS")


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_S03E3H_DISPOSABLE_NATIVE") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "S03E3H_DISPOSABLE_OPNSENSE_ONLY")
    sha = os.environ.get(SOURCE_HEAD, "")
    need(re.fullmatch("[a-f0-9]{40}", sha) is not None,
         "S03E3H_EXACT_CI_SOURCE_REQUIRED")
    installed = command("pkg", "query", "%v", "os-zapret2-restyle")
    revision = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$",
                         (REPO / "Makefile").read_text())
    need(revision is not None and
         installed.returncode == 0 and
         installed.stdout.strip() ==
         (REPO / "VERSION").read_text().strip() + "_" + revision.group(1) and
         SERVICE.read_bytes() == (REPO /
            "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_bytes(),
         "S03E3H_OFFICIAL_PKG_NOT_EXACT_INSTALLED_SOURCE")
    g04 = module("stage2-opnsense-g04-native-runtime.py")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    initial = g04.model()
    strategy = initial.findtext("strategy/trafficargs") or ""
    domains = initial.findtext("hostlist/youtubedomains") or ""
    need(initial.findtext("general/enabled") == "0" and
         not (initial.findtext("general/waninterface") or "") and
         strategy.count("--new") == 1 and domains.splitlines() == g04.YOUTUBE and
         not ENGINE.exists() and not JOURNAL.exists(),
         "S03E3H_NOT_CLEAN_SEEDED_NATIVE_CONFIG")
    before = CONFIG.read_bytes()
    engine_sha = g04.setup_upstream()
    need(CONFIG.read_bytes() == before and not PID.exists() and
         not JOURNAL.exists(), "S03E3H_UPSTREAM_SETUP_CHANGED_INITIAL_CONFIG")
    g04.authenticated_first_apply(strategy, domains)
    web = voice.GuestHttps()
    voice.login(web)
    config = CONFIG.read_bytes()
    engine_before = physical(web, engine_sha=engine_sha)
    need(engine_before["owned"] and
         CONFIG.read_bytes() == config,
         "S03E3H_INITIAL_RUNNING_OWNER_UNQUALIFIED")
    active = web.api("POST", LAB + "status", {"job_id": "@active"})
    need(active.get("status") == "idle",
         "S03E3H_LAB_ALREADY_ACTIVE")
    started = web.api("POST", LAB + "start", {
        "target": TARGET, "mode": "standard", "language": "ru",
        "enable_quic": "0", "ipv6_enabled": "0"})
    job = started.get("job_id")
    need(started.get("status") == "ok" and started.get("state") == "queued"
         and isinstance(job, str) and JOB_RE.fullmatch(job) is not None,
         "S03E3H_REAL_RUNNING_LAB_START_NOT_QUEUED")

    terminal = None
    deadline = time.monotonic() + 480
    while time.monotonic() < deadline:
        response = web.api("POST", LAB + "status", {"job_id": job})
        need(response.get("job_id") == job and
             response.get("state") in ("queued", "running", "cancel_requested",
                                     "completed", "error"),
             "S03E3H_LAB_JOB_STATE_UNTRUSTED")
        if response["state"] in END_STATES:
            terminal = web.api("POST", LAB + "result", {"job_id": job})
            break
        time.sleep(2)
    need(isinstance(terminal, dict),
         "S03E3H_REAL_RUNNING_LAB_TERMINAL_TIMEOUT")
    need(terminal.get("job_id") == job,
         "S03E3H_REAL_LAB_RESULT_WRONG_JOB")
    stage = summarize(terminal)
    # Read-only post-Lab snapshot even on stage90 failure. Do not restart,
    # cancel or repair an uncertain operation: disposable VM is torn down.
    run_status = command(SERVICE, "status")
    candidate_pid = (PID.read_text().strip() if PID.is_file() and
                     not PID.is_symlink() else "")
    owned, foreign = ipfw()
    try:
        journal = json.loads(JOURNAL.read_bytes())
        journal_phase = journal.get("phase")
    except (OSError, ValueError):
        journal_phase = None
    physical_report = {
        "cli_status_rc": run_status.returncode,
        "one_real_engine": len(engine_pids()) == 1,
        "actual_pid_matches_census": candidate_pid.isdecimal() and
            engine_pids() == [int(candidate_pid)],
        "saved_config_unchanged": CONFIG.read_bytes() == config,
        "owned_ipfw_unchanged": owned == engine_before["owned"],
        "foreign_ipfw_unchanged": foreign == engine_before["foreign"],
        "journal_committed": journal_phase == "committed",
        "after_lab_active_idle": web.api(
            "POST", LAB + "status", {"job_id": "@active"}).get("status") == "idle",
    }
    print("S03E3H_RUNNING_LAB_DIAGNOSTIC=" + json.dumps({
        "source_sha": sha, "real_installed_original_fd9": True,
        "mode": "standard", "initial_service": "RUNNING",
        "stage": stage, **physical_report,
        "owner_device_modified": False,
    }, sort_keys=True), flush=True)
    need(acceptance(terminal) and verified_physical_report(physical_report),
         "S03E3H_NATIVE_RUNNING_LAB_STAGE90_RESTORE_NOT_VERIFIED")
    after = physical(web, engine_sha=engine_sha)
    need(after["owned"] == engine_before["owned"] and
         after["foreign"] == engine_before["foreign"] and
         after["owner"] == engine_before["owner"] and
         CONFIG.read_bytes() == config,
         "S03E3H_RUNNING_COMMON_OWNER_NOT_RESTORED")
    print("S03E3H_RUNNING_LAB=PASS_REAL_RUNNING_STANDARD_STAGE90_99_RESTORED",
          flush=True)


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "S03E3H_ARGUMENTS_UNTRUSTED")
        execute()
    except (Refusal, OSError, KeyError, ValueError, TypeError,
            ET.ParseError, subprocess.TimeoutExpired) as exc:
        print("S03E3H_RUNNING_LAB=REFUSED:" + str(exc)[:120], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
