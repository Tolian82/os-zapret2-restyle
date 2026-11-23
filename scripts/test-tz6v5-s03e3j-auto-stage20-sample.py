#!/usr/bin/env python3
"""TZ6v5 S03e3j: real Auto Lab Stage20 refusal sampling (S03, NOT a fix).

Run exactly one genuine un-cancelled Standard Lab job. Read its already-
persisted original Python timing telemetry without any runtime instrumentation. Stop the sampling
immediately on any physical uncertainty. No custom Stop/Start, no guest
instrumentation of the native worker, no fabricated delay or forced recovery.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG = Path("/conf/config.xml")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
LAB = "/api/zapret/strategy_lab/"
SESSIONS = 1
SHA = re.compile(r"[a-f0-9]{40}\Z")
STAGES = frozenset(("00", "10", "20", "30", "40", "50", "60",
                    "70", "80", "85", "90", "99"))


class Refused(RuntimeError):
    pass


def need(ok, label):
    if not ok:
        raise Refused(label)


def helper(file, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    need(spec is not None and spec.loader is not None,
         "S03E3J_NATIVE_HELPER_NOT_FOUND")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def status_stage(response):
    """A status poll is approximate; never invent a subprocess rc."""
    value = response.get("current_stage")
    return value if value in STAGES else None


def bounded_stop_window(observed):
    """Only HTTP observation bounds, NOT exact original stop elapsed time."""
    starts = [at for stage, at in observed if stage == "20"]
    finishes = [at for stage, at in observed
                if stage is not None and stage in STAGES and int(stage) > 20]
    if not starts or not finishes:
        return "unknown"
    after = [at for at in finishes if at >= starts[0]]
    if not after:
        return "unknown"
    # Round to 1-second bins; useful for classification, not an rc or timer proof.
    seconds = max(0.0, min(after[0] - starts[0], 30.0))
    return "0-5s" if seconds < 5 else "5-9s" if seconds < 9 else "9-12s" if seconds < 12 else "12s+"



def stage20_original_telemetry(document):
    """Validate the actual Python-owned monotonic Stage20 adapter measurement.

    No source wrapper, no guessed child exit code. The duration spans the
    adapter invocation; it is not the nested native Stop duration.
    """
    need(type(document) is dict and document.get("schema") == 1 and
         type(document.get("events")) is list and
         len(document["events"]) <= 128,
         "S03E3K_TELEMETRY_SCHEMA_UNVERIFIED")
    matches = [x for x in document["events"] if type(x) is dict
               and x.get("phase") == "stage_adapter" and
               x.get("stage") == "20"]
    need(len(matches) == 1, "S03E3K_STAGE20_TIMING_NOT_UNIQUE")
    event = matches[0]
    millis = event.get("duration_ms")
    details = event.get("details")
    need(type(millis) is int and 0 <= millis <= 120000 and
         event.get("outcome") in ("pass", "error", "timeout") and
         type(details) is dict and details.get("action") == "20" and
         details.get("operation_timeout_seconds") is None,
         "S03E3K_STAGE20_TIMING_INVALID")
    return {"duration_ms": millis,
            "adapter_outcome": event["outcome"],
            "source": "original_monotonic_stage_adapter",
            "native_stop_rc": "not_recorded"}


def read_original_stage20_telemetry(job):
    """Root-owned original Lab data, bounded read-only, zero data disclosure."""
    need(type(job) is str and re.fullmatch(r"job\.[A-Za-z0-9]{4,40}", job),
         "S03E3K_JOB_ID_UNVERIFIED")
    path = Path("/var/run/zapret2-restyle/strategy-lab/jobs") / job / "timing-telemetry.json"
    stat = path.lstat()
    need(path.is_file() and not path.is_symlink() and stat.st_uid == 0 and
         stat.st_nlink == 1 and 8 <= stat.st_size <= 262144,
         "S03E3K_SOURCE_TIMING_FILE_UNTRUSTED")
    data = json.loads(path.read_bytes())
    return stage20_original_telemetry(data)

def classify_stage20(summary, physical_good, active_auto, *, original_rc=None):
    """Bounded outcome only. No observed original rc is allowed or implied."""
    statuses = summary.get("stage_statuses")
    stage = statuses.get("20") if type(statuses) is dict else None
    result = {"stage20": "unknown", "original_stop_rc": "not_recorded",
              "stop_timeout_proven": False,
              "safe_to_continue": False, "product_lab_restored": False}
    if stage in ("PASS", "FAIL", "TIMEOUT"):
        result["stage20"] = stage
    if type(original_rc) is int:
        # No stock Lab API reports the original rc, so this field is not
        # accepted as a classification source.
        return result
    good = physical_good is True and active_auto is True
    result["safe_to_continue"] = good and stage == "PASS"
    result["product_lab_restored"] = (
        good and summary.get("restoration_verified") is True and
        statuses.get("90") == "PASS" and statuses.get("99") == "PASS")
    return result


def self_test():
    good = {"stage_statuses": {"20": "PASS", "90": "FAIL", "99": "FAIL"},
            "restoration_verified": False}
    x = classify_stage20(good, True, True)
    need(x == {"stage20": "PASS", "original_stop_rc": "not_recorded",
               "stop_timeout_proven": False, "safe_to_continue": True,
               "product_lab_restored": False},
         "S03E3J_VALID_STAGE20_CLASSIFICATION_FAILED")
    for s in ("FAIL", "TIMEOUT"):
        changed = {**good, "stage_statuses":
                   {**good["stage_statuses"], "20": s}}
        result = classify_stage20(changed, True, True)
        need(result["stage20"] == s and not result["safe_to_continue"]
             and result["original_stop_rc"] == "not_recorded"
             and result["stop_timeout_proven"] is False,
             "S03E3J_REFUSAL_NOT_FAIL_CLOSED")
    need(not classify_stage20(good, False, True)["safe_to_continue"] and
         not classify_stage20(good, True, False)["safe_to_continue"] and
         not classify_stage20(good, True, True, original_rc=70)[
             "safe_to_continue"],
         "S03E3J_UNATTESTED_RC_OR_PHYSICAL_ACCEPTED")
    need(bounded_stop_window([("20", 1.0), ("30", 12.0)]) == "9-12s" and
         bounded_stop_window([]) == "unknown",
         "S03E3J_STOP_WINDOW_CLASSIFICATION_INVALID")
    original = {
        "schema": 1, "events": [
            {"phase": "stage_adapter", "stage": "10",
             "outcome": "pass", "duration_ms": 20,
             "details": {"action": "10", "operation_timeout_seconds": None}},
            {"phase": "stage_adapter", "stage": "20",
             "outcome": "error", "duration_ms": 7312,
             "details": {"action": "20", "operation_timeout_seconds": None}},
        ],
    }
    verified = stage20_original_telemetry(original)
    need(verified == {
        "duration_ms": 7312, "adapter_outcome": "error",
        "source": "original_monotonic_stage_adapter",
        "native_stop_rc": "not_recorded",
    }, "S03E3K_VALID_NATIVE_MONOTONIC_RECEIPT_REJECTED")
    for forged in (
        {**original, "schema": 2},
        {**original, "events": []},
        {**original, "events": original["events"] + [original["events"][1]]},
        {**original, "events": [original["events"][0],
            {**original["events"][1], "duration_ms": "7312"}]},
        {**original, "events": [original["events"][0],
            {**original["events"][1], "duration_ms": True}]},
        {**original, "events": [original["events"][0],
            {**original["events"][1], "details":
             {"action": "20", "operation_timeout_seconds": 10}}]},
    ):
        try:
            stage20_original_telemetry(forged)
        except Refused:
            pass
        else:
            raise Refused("S03E3K_FORGED_NATIVE_TIMING_ACCEPTED")
    print("S03E3J_STOP_SAMPLE_FAST=PASS", flush=True)


def setup():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_S03E3J_DISPOSABLE_NATIVE") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "S03E3J_DISPOSABLE_NATIVE_ONLY")
    sha = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(SHA.fullmatch(sha) is not None, "S03E3J_EXACT_SOURCE_SHA_REQUIRED")
    h = helper("test-tz6v5-s03e3h-running-lab.py", "s03e3j_h")
    old = helper("test-tz6v5-s03e3i-auto-learning-lab.py", "s03e3j_i")
    g04 = h.module("stage2-opnsense-g04-native-runtime.py")
    voice = h.module("stage2-opnsense-real-native-voice-http.py")
    protected = h.module("stage5-native-protected-update.py")
    pkg = subprocess.run(["pkg", "query", "%v", "os-zapret2-restyle"],
                         capture_output=True, text=True, timeout=30)
    revision = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$",
                         (ROOT / "Makefile").read_text())
    need(pkg.returncode == 0 and revision is not None and
         pkg.stdout.strip() ==
         (ROOT / "VERSION").read_text().strip() + "_" + revision.group(1) and
         SERVICE.read_bytes() == (ROOT /
             "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_bytes(),
         "S03E3J_NATIVE_PKG_SOURCE_NOT_ATTESTED")
    initial = g04.model()
    strategy = initial.findtext("strategy/trafficargs") or ""
    domains = initial.findtext("hostlist/youtubedomains") or ""
    need(initial.findtext("general/enabled") == "0" and
         not (initial.findtext("general/waninterface") or "") and
         strategy.count("--new") == 1 and
         domains.splitlines() == g04.YOUTUBE and
         not JOURNAL.exists() and not ENGINE.exists(),
         "S03E3J_COLD_SEEDED_CONFIG_NOT_ATTESTED")
    bytes_before = CONFIG.read_bytes()
    upstream_sha = g04.setup_upstream()
    need(CONFIG.read_bytes() == bytes_before and not JOURNAL.exists(),
         "S03E3J_UPSTREAM_SETUP_MODIFIED_CONFIG")
    g04.authenticated_first_apply(strategy, domains)
    web = voice.GuestHttps()
    voice.login(web)
    initial_normal = h.physical(web, engine_sha=upstream_sha)
    config = web.api("GET", "/api/zapret/settings/get").get("zapret")
    switched = web.api("POST", "/api/zapret/settings/apply",
                       old.test_mode_form(config))
    need(switched.get("status") == "ok" and
         switched.get("result") == "saved" and
         switched.get("requires_review") is not True and
         g04.model().findtext("hostlist/mode") == "auto",
         "S03E3J_ORIGINAL_AUTO_HTTPS_APPLY_NOT_COMMITTED")
    before = h.physical(web, engine_sha=upstream_sha)
    need(before["owner"] != initial_normal["owner"] and
         before["foreign"] == initial_normal["foreign"],
         "S03E3J_REAL_ORIGINAL_AUTO_OWNER_MISSING")
    initial_learning = old.native_auto_map(protected, before["owner"])
    need(len(initial_learning) == 2, "S03E3J_EXPECTED_2_NATIVE_LEARNING_PROFILES")
    return sha, h, old, protected, g04, web, upstream_sha


def one_lab(web, h):
    active = web.api("POST", LAB + "status", {"job_id": "@active"})
    need(active.get("status") == "idle", "S03E3J_OTHER_LAB_ACTIVE")
    started = web.api("POST", LAB + "start", {
        "target": h.TARGET, "mode": "standard", "language": "ru",
        "enable_quic": "0", "ipv6_enabled": "0"})
    job = started.get("job_id")
    need(started.get("status") == "ok" and
         started.get("state") == "queued" and type(job) is str and
         h.JOB_RE.fullmatch(job) is not None,
         "S03E3J_GENUINE_LAB_NOT_QUEUED")
    samples = []
    seen = []
    terminal = None
    cutoff = time.monotonic() + 480
    while time.monotonic() < cutoff:
        response = web.api("POST", LAB + "status", {"job_id": job})
        need(response.get("job_id") == job and response.get("state") in (
            "queued", "running", "cancel_requested", "completed", "error"),
            "S03E3J_UNTRUSTED_LAB_STATUS")
        stage = status_stage(response)
        if stage is not None and (not seen or stage != seen[-1]):
            seen.append(stage)
            samples.append((stage, time.monotonic()))
        if response["state"] in h.END_STATES:
            terminal = web.api("POST", LAB + "result", {"job_id": job})
            break
        # Polling HTTP is strictly read-only. No process or kernel tracing.
        time.sleep(0.35)
    need(type(terminal) is dict and terminal.get("job_id") == job,
         "S03E3J_LAB_TERMINAL_MISSING")
    return job, terminal, bounded_stop_window(samples)


def execute():
    sha, h, old, protected, g04, web, engine_sha = setup()
    outcomes = []
    for iteration in range(1, SESSIONS + 1):
        pre = h.physical(web, engine_sha=engine_sha)
        config = CONFIG.read_bytes()
        before_map = old.native_auto_map(protected, pre["owner"])
        before_args = old.raw_native_args()
        job, terminal, time_bin = one_lab(web, h)
        report, extra = old.physical_report(
            h, web, pre, config, g04.model(), protected, before_map)
        summary = h.summarize(terminal)
        hashed = old.lab_semantic_comparison(job)
        drift = {"provenance_verified": False,
                 "only_generation_inboxes_changed": "unknown"}
        if extra["after_schema3_map_valid"]:
            try:
                successor = old.native_auto_map(protected, h.current_owner())
                drift = old.auto_argv_drift(
                    before_args, old.raw_native_args(), before_map, successor)
            except (OSError, ValueError, TypeError, Refused, old.Refused):
                pass
        safe = h.verified_physical_report(report)
        acceptable = (safe and extra["after_schema3_map_valid"] and
                      extra["original_auto_epoch_retired_if_changed"] and
                      extra["hostlist_mode_auto"] and
                      (old.s03_expected_auto_hash_red(
                           summary, report, extra, drift, hashed, h) or
                       (h.acceptance(terminal) and hashed.get("args_equal") is True)))
        stage20 = classify_stage20(summary, safe, acceptable)
        timing = read_original_stage20_telemetry(job)
        need((stage20["stage20"] == "FAIL" and
              timing["adapter_outcome"] == "error") or
             (stage20["stage20"] == "PASS" and
              timing["adapter_outcome"] == "pass"),
             "S03E3K_TIMING_OUTCOME_AND_STAGE20_MISMATCH")
        log = {
            "sample": iteration, "exact_sha": sha,
            "stage20": stage20["stage20"],
            "stage20_http_observed_window": time_bin,
            "stage20_actual_adapter_duration_ms": timing["duration_ms"],
            "stage20_actual_adapter_outcome": timing["adapter_outcome"],
            "stage20_timing_source": timing["source"],
            "native_stop_rc": stage20["original_stop_rc"],
            "native_stop_timeout_proven": stage20["stop_timeout_proven"],
            "final_stage90": summary.get("stage90", "unknown"),
            "lab_outcome": summary.get("outcome_class", "unknown"),
            "original_service_running": safe,
            "actual_auto_map_unchanged_semantics":
                drift.get("learning_source_semantics_equal") is True,
            "only_generation_inbox_args_change":
                drift.get("only_generation_inboxes_changed") is True,
            "config_equal": hashed.get("config_equal") is True,
            "firewall_equal": hashed.get("firewall_equal") is True,
            "original_auto_epoch_retired_if_changed":
                extra["original_auto_epoch_retired_if_changed"] is True,
            "read_only_diagnostic": True,
        }
        print("S03E3J_NATIVE_STAGE20_SAMPLE=" +
              json.dumps(log, sort_keys=True), flush=True)
        outcomes.append(stage20["stage20"])
        # On Stage20 failure do not launch another Lab even if engine is
        # RUNNING at terminal. It is a distinct red original Stop path.
        if stage20["stage20"] != "PASS":
            print("S03E3J_STAGE20_RED=OBSERVED_ORIGINAL_RC_UNKNOWN",
                  flush=True)
            need(safe and extra["after_schema3_map_valid"],
                 "S03E3J_STAGE20_RED_PHYSICAL_UNCERTAIN")
            return
        need(acceptable and stage20["safe_to_continue"],
             "S03E3J_NO_FURTHER_LAB_AFTER_UNVERIFIED_STATE")
        # Only accepted physical proof authorizes the next genuine Lab.
    need(len(outcomes) == SESSIONS and all(s == "PASS" for s in outcomes),
         "S03E3J_EXPECTED_SAMPLE_COUNT_MISSING")
    print("S03E3J_STAGE20_SAMPLING=PASS_NO_STOP_FAILURE_OBSERVED",
          flush=True)


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "S03E3J_UNTRUSTED_ARGUMENTS")
        execute()
    except (Refused, OSError, ValueError, TypeError, KeyError,
            RuntimeError, subprocess.TimeoutExpired) as exc:
        label = str(exc)
        safe = label if re.fullmatch(r"S03E3J_[A-Z0-9_]{1,90}", label) else "S03E3J_REFUSED_UNATTRIBUTED"
        print("S03E3J_NATIVE=REFUSED:" + safe, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
