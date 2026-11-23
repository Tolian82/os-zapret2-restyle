#!/usr/bin/env python3
"""S03e3i: real Common AUTO schema3 learning RUNNING -> Lab -> RUNNING.

Disposable OPNsense 26.7 only. Native official Mk package and upstream
v1.0.7. Authenticated installed HTTPS Strategies Apply selects AUTO; original
FD9 owns the engine, map and epochs. Lab's actual standard worker controls the
only Stop/Start. No test-written Config, PID, learning inbox, journal or IPFW.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
CONFIG = Path("/conf/config.xml")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
PID = Path("/var/run/dvtws2.pid")
LAB = "/api/zapret/strategy_lab/"
EXACT = re.compile(r"[a-f0-9]{40}\Z")


class Refused(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refused(reason)


def read_only_status():
    return subprocess.run([str(SERVICE), "status"], capture_output=True,
                          text=True, check=False, timeout=35).returncode


def native_auto_map(protected, owner_id):
    """Original map/epoch and genuine per-N inbox; no invented receipts."""
    schema, learning = protected.original_auto_generation(owner_id, True)
    need(schema == 3 and 1 <= len(learning) <= 64 and
         (protected.EPOCHS / owner_id / "epoch.json").is_file(),
         "S03E3I_GENUINE_AUTO_SCHEMA3_LEARNING_NOT_ATTESTED")
    return learning


def verify_auto_after(protected, before, after, old_learning):
    """Never skip old original epoch retirement when Lab rotates its owner."""
    need(after.get("owner") and after.get("owner") != "",
         "S03E3I_LAB_COMMON_OWNER_UNQUALIFIED")
    successor = native_auto_map(protected, after["owner"])
    if after["owner"] == before["owner"]:
        return {"epoch_owner_changed": False, "old_retired_if_changed": True,
                "learning_count": len(successor)}
    need(protected.verified_old_auto_retirement(
        before["owner"], 3, old_learning),
        "S03E3I_LAB_OLD_AUTO_EPOCH_RETIREMENT_NOT_PROVEN")
    return {"epoch_owner_changed": True, "old_retired_if_changed": True,
            "learning_count": len(successor)}


def snapshot(web, h, sha):
    return h.physical(web, engine_sha=sha)


def physical_report(h, web, before, saved, current, protected, old_learning):
    """Read-only after-state even when terminal Lab failed. No recovery."""
    status = read_only_status()
    old = h.engine_pids()
    pid = (PID.read_text().strip() if PID.is_file() and
           not PID.is_symlink() else "")
    rules, foreign = h.ipfw()
    try:
        owner = h.current_owner()
        schema, learning = protected.original_auto_generation(owner, True)
        map_ok = schema == 3 and len(learning) >= 1 and (
            protected.EPOCHS / owner / "epoch.json").is_file()
        if owner != before["owner"]:
            retired = protected.verified_old_auto_retirement(
                before["owner"], 3, old_learning)
        else:
            retired = True
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        owner, learning, map_ok, retired = "", [], False, False
    reply = web.api("POST", LAB + "status", {"job_id": "@active"})
    result = {
        "cli_status_rc": status,
        "one_real_engine": len(old) == 1,
        "actual_pid_matches_census": pid.isdecimal() and old == [int(pid)],
        "saved_config_unchanged": CONFIG.read_bytes() == saved,
        "owned_ipfw_unchanged": rules == before["owned"],
        "foreign_ipfw_unchanged": foreign == before["foreign"],
        "journal_committed": bool(owner) and map_ok and retired,
        "after_lab_active_idle": reply.get("status") == "idle",
    }
    detail = {
        "original_auto_epoch_retired_if_changed": retired,
        "after_learning_profile_count": len(learning),
        "after_schema3_map_valid": map_ok,
        "new_generation": bool(owner and owner != before["owner"]),
        "hostlist_mode_auto": current.findtext("hostlist/mode") == "auto",
    }
    return result, detail



def compare_semantic_evidence(initial, final):
    """The original Lab contract: exactly 3 hash equalities, no hash values."""
    keys = ("runtime_args_hash", "effective_config_hash", "normal_firewall_hash")
    unknown = {"evidence_present": False, "args_equal": "unknown",
               "config_equal": "unknown", "firewall_equal": "unknown"}
    if not (type(initial) is dict and type(final) is dict):
        return unknown
    for rec in (initial, final):
        if not (rec.get("schema") == 1 and rec.get("source") == "zapret_service"
                and rec.get("state") == "RUNNING"):
            return unknown
        for key in keys:
            value = rec.get(key)
            if not (type(value) is str and
                    re.fullmatch(r"[a-f0-9]{64}", value)):
                if key != "normal_firewall_hash" or value != "empty":
                    return unknown
    return {
        "evidence_present": True,
        "args_equal": initial[keys[0]] == final[keys[0]],
        "config_equal": initial[keys[1]] == final[keys[1]],
        "firewall_equal": initial[keys[2]] == final[keys[2]],
    }


def lab_semantic_comparison(job_id):
    """Read Lab's real saved semantic snapshots, never print data or digests."""
    unknown = compare_semantic_evidence(None, None)
    if type(job_id) is not str or re.fullmatch(r"job\.[a-zA-Z0-9]{4,40}", job_id) is None:
        return unknown
    root = Path("/var/run/zapret2-restyle/strategy-lab/jobs") / job_id
    items = []
    for filename in ("lifecycle-snapshot.json", "lifecycle-final.json"):
        path = root / filename
        try:
            st = path.lstat()
            if (not path.is_file() or path.is_symlink() or st.st_uid != 0
                    or st.st_nlink != 1 or st.st_size > 8192 or st.st_size < 8):
                return unknown
            items.append(json.loads(path.read_bytes()))
        except (OSError, ValueError, TypeError):
            return unknown
    return compare_semantic_evidence(*items)


ARGS = Path("/usr/local/etc/zapret2/runtime-v2/dvtws.args")


def raw_native_args():
    """Read, never log/save actual engine argv."""
    st = ARGS.lstat()
    need(ARGS.is_file() and not ARGS.is_symlink() and st.st_uid == 0 and
         st.st_nlink == 1 and 8 < st.st_size < 262144,
         "S03E3I_NATIVE_ARGS_FILE_UNTRUSTED")
    data = ARGS.read_bytes()
    need(data.endswith(b"\n") and b"\x00" not in data,
         "S03E3I_NATIVE_ARGS_BYTES_UNTRUSTED")
    return data


def mask_verified_inboxes(data, learning):
    """Only real map-bound --hostlist-auto paths may vary across generations."""
    need(type(data) is bytes and type(learning) is list and
         1 <= len(learning) <= 64 and b"\x00" not in data,
         "S03E3I_MASK_INPUT_UNQUALIFIED")
    lines = data.decode("utf-8").splitlines()
    need(data.endswith(b"\n") and b"\r" not in data,
         "S03E3I_MASK_NEWLINES_UNQUALIFIED")
    mapping = {}
    for item in learning:
        need(type(item) is dict and
             type(item.get("native_number")) is int and
             item["native_number"] > 0 and
             type(item.get("auto_inbox")) is str and
             re.fullmatch(r"/[a-zA-Z0-9._/-]{1,250}",
                          item["auto_inbox"]) is not None,
             "S03E3I_MASK_SOURCE_UNQUALIFIED")
        token = "--hostlist-auto=" + item["auto_inbox"]
        need(token not in mapping and lines.count(token) == 1,
             "S03E3I_MASK_TOKEN_NOT_EXACT_ONE")
        mapping[token] = "--hostlist-auto=@native-" + str(item["native_number"])
    need(len(set(mapping.values())) == len(mapping) and
         sum(line.startswith("--hostlist-auto=") for line in lines) ==
         len(mapping), "S03E3I_MASK_UNEXPECTED_AUTO_TOKEN")
    return ("\n".join(mapping.get(x, x) for x in lines) + "\n").encode("utf-8")


def auto_argv_drift(before, after, before_map, after_map):
    """Return only boolean evidence; never expose hashes or argv data."""
    empty = {
        "provenance_verified": False, "raw_args_changed": "unknown",
        "only_generation_inboxes_changed": "unknown",
        "learning_source_semantics_equal": "unknown",
    }
    try:
        def source(rows):
            return sorted((row["native_number"], row["hostlist"],
                           row["found_source_id"], row["selector"],
                           row["source_sha256"]) for row in rows)
        old_mask = mask_verified_inboxes(before, before_map)
        new_mask = mask_verified_inboxes(after, after_map)
        stable = source(before_map) == source(after_map)
        return {
            "provenance_verified": True,
            "raw_args_changed": before != after,
            "only_generation_inboxes_changed": (old_mask == new_mask and
                                                  before != after and stable),
            "learning_source_semantics_equal": stable,
        }
    except (Refused, KeyError, ValueError, TypeError, UnicodeError):
        return empty




def s03_expected_auto_hash_red(stage, report, detail, drift, hashes, h):
    """This is an EXPECTED RED, never a healthy Lab PASS.

    Must prove the service, Config/IPFW, genuine schema3 epoch, and source
    profile semantics remain valid while the original Stage90 falsely
    classifies only new native Auto inbox paths as a changed strategy.
    """
    return (
        stage.get("outcome_class") == "RESTORE_FAILED" and
        stage.get("job_terminal") is True and
        stage.get("restoration_initial_running") is True and
        stage.get("restoration_final_running") is True and
        stage.get("restoration_verified") is False and
        stage.get("strategy_unchanged") is False and
        stage.get("temporary_runtime_clean") is True and
        type(stage.get("stage_statuses")) is dict and
        all(stage["stage_statuses"].get(x) == "PASS"
            for x in ("00", "10", "20", "30", "40")) and
        all(stage["stage_statuses"].get(x) == "SKIPPED"
            for x in ("50", "60", "70", "80", "85")) and
        stage.get("stage90") == "FAIL" and
        stage.get("stage99") == "FAIL" and
        type(hashes) is dict and
        hashes == {"evidence_present": True, "args_equal": False,
                   "config_equal": True, "firewall_equal": True} and
        type(drift) is dict and
        drift == {"provenance_verified": True, "raw_args_changed": True,
                  "only_generation_inboxes_changed": True,
                  "learning_source_semantics_equal": True} and
        type(detail) is dict and
        detail.get("after_schema3_map_valid") is True and
        detail.get("after_learning_profile_count", 0) >= 1 and
        detail.get("hostlist_mode_auto") is True and
        detail.get("original_auto_epoch_retired_if_changed") is True and
        detail.get("new_generation") is True and
        h.verified_physical_report(report)
    )


def test_mode_form(saved):
    need(type(saved) is dict and
         type(saved.get("hostlist")) is dict and
         type(saved["hostlist"].get("telegramips")) is str,
         "S03E3I_HTTPS_SAVED_BASELINE_NOT_SCALAR")
    return [
        ("zapret[sync][telegramips_baseline]",
         saved["hostlist"]["telegramips"]),
        ("zapret[hostlist][mode]", "auto"),
    ]


def self_test():
    import importlib.util
    def module(filename, name):
        spec = importlib.util.spec_from_file_location(name, HERE / filename)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    h = module("test-tz6v5-s03e3h-running-lab.py", "s03e3i_fast_h")
    data = {"hostlist": {"telegramips": ""}}
    need(test_mode_form(data) == [
        ("zapret[sync][telegramips_baseline]", ""),
        ("zapret[hostlist][mode]", "auto")],
        "S03E3I_MODE_FORM_NOT_ORIGINAL")
    for bad in ({"hostlist": {}},
                {"hostlist": {"telegramips": []}}, {}):
        try:
            test_mode_form(bad)
        except Refused:
            pass
        else:
            raise Refused("S03E3I_UNSAFE_BASELINE_ACCEPTED")
    good = {"cli_status_rc": 0, **{
        k: True for k in h.PHYSICAL_BOOL_KEYS}}
    need(h.verified_physical_report(good),
         "S03E3I_GENUINE_SUCCESS_RC0_NOT_ACCEPTED")
    for bad in (
        {**good, "cli_status_rc": 1},
        {**good, "cli_status_rc": "0"},
        {**good, "journal_committed": False},
        {**good, "one_real_engine": False},
    ):
        need(not h.verified_physical_report(bad),
             "S03E3I_FALSE_NATIVE_TERMINAL_ACCEPTED")
    need(h.OWNED.match("19099 foo") is not None and
         h.OWNED.match("19131 foo") is not None and
         h.OWNED.match("19140 foo") is None and
         h.OWNED.match("65534 foo") is None,
         "S03E3I_IPFW_OWNED_RANGE_UNSAFE")
    sample = {"schema": 1, "source": "zapret_service", "state": "RUNNING",
              "runtime_args_hash": "a" * 64,
              "effective_config_hash": "b" * 64,
              "normal_firewall_hash": "c" * 64}
    same = compare_semantic_evidence(sample, dict(sample))
    need(same == {"evidence_present": True, "args_equal": True,
                  "config_equal": True, "firewall_equal": True},
         "S03E3I_EQUAL_SEMANTIC_HASHES_REJECTED")
    changed_args = compare_semantic_evidence(
        sample, {**sample, "runtime_args_hash": "d" * 64})
    need(changed_args == {
        "evidence_present": True, "args_equal": False,
        "config_equal": True, "firewall_equal": True},
        "S03E3I_ARGS_DIFFERENCE_NOT_CLASSIFIED")
    for malformed in (
        {**sample, "runtime_args_hash": "private.example"},
        {**sample, "schema": 2},
        {**sample, "state": "STOPPED"},
    ):
        need(compare_semantic_evidence(sample, malformed)
             ["evidence_present"] is False,
             "S03E3I_UNVERIFIED_SNAPSHOT_ACCEPTED")
    need("private.example" not in json.dumps(changed_args),
         "S03E3I_SEMANTIC_DIGEST_VALUES_EXPOSED")
    old = [{"native_number": 5, "hostlist": "youtube",
            "found_source_id": "youtube_found", "selector": "<HOSTLIST:youtube>",
            "source_sha256": "c" * 64,
            "auto_inbox": "/var/db/zapret2/native/learning-old-5.txt"}]
    new = [{**old[0], "auto_inbox":
            "/var/db/zapret2/native/learning-new-5.txt"}]
    first = ("--port=989\n--filter-tcp=443\n--new\n--hostlist-auto=" +
             old[0]["auto_inbox"] + "\n--hostlist-auto-retrans-reset=0\n").encode()
    second = first.replace(old[0]["auto_inbox"].encode(),
                           new[0]["auto_inbox"].encode())
    observed = auto_argv_drift(first, second, old, new)
    need(observed == {
        "provenance_verified": True, "raw_args_changed": True,
        "only_generation_inboxes_changed": True,
        "learning_source_semantics_equal": True},
        "S03E3I_GENUINE_INBOX_CHANGE_NOT_RECOGNIZED")
    changed = second.replace(b"--filter-tcp=443", b"--filter-tcp=80")
    need(auto_argv_drift(first, changed, old, new)[
         "only_generation_inboxes_changed"] is False,
         "S03E3I_REAL_FILTER_CHANGE_INCORRECTLY_MASKED")
    forged = [{**new[0], "auto_inbox": "/tmp/forged.txt"}]
    need(auto_argv_drift(first, second, old, forged)[
         "provenance_verified"] is False,
         "S03E3I_UNATTESTED_INBOX_PATH_ACCEPTED")
    valid_red = {
        "outcome_class": "RESTORE_FAILED", "job_terminal": True,
        "restoration_initial_running": True,
        "restoration_final_running": True, "restoration_verified": False,
        "strategy_unchanged": False, "temporary_runtime_clean": True,
        "stage90": "FAIL", "stage99": "FAIL",
        "stage_statuses": {
            **{n: "PASS" for n in ("00", "10", "20", "30", "40")},
            **{n: "SKIPPED" for n in ("50", "60", "70", "80", "85")},
            "90": "FAIL", "99": "FAIL",
        },
    }
    safe_physical = {"cli_status_rc": 0, **{
        k: True for k in h.PHYSICAL_BOOL_KEYS}}
    valid_map = {
        "after_schema3_map_valid": True, "after_learning_profile_count": 2,
        "hostlist_mode_auto": True,
        "original_auto_epoch_retired_if_changed": True, "new_generation": True,
    }
    hashes = {"evidence_present": True, "args_equal": False,
              "config_equal": True, "firewall_equal": True}
    need(s03_expected_auto_hash_red(
        valid_red, safe_physical, valid_map, observed, hashes, h),
        "S03E3I_GENUINE_EXPECTED_RED_NOT_ACCEPTED")
    for payload in (
        ({**valid_red, "stage90": "PASS"}, safe_physical, valid_map, observed, hashes),
        ({**valid_red, "stage_statuses": {**valid_red["stage_statuses"],
                                         "20": "FAIL"}},
         safe_physical, valid_map, observed, hashes),
        (valid_red, {**safe_physical, "one_real_engine": False},
         valid_map, observed, hashes),
        (valid_red, safe_physical, valid_map,
         {**observed, "only_generation_inboxes_changed": False}, hashes),
        (valid_red, safe_physical, valid_map, observed,
         {**hashes, "firewall_equal": False}),
    ):
        need(not s03_expected_auto_hash_red(*payload, h),
             "S03E3I_FAKE_OR_UNSAFE_RED_RECEIPT_ACCEPTED")
    print("S03E3I_REAL_AUTO_LAB_FAST=PASS", flush=True)


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_S03E3I_DISPOSABLE_NATIVE") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "S03E3I_DISPOSABLE_OPNSENSE_ONLY")
    sha = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(EXACT.fullmatch(sha) is not None,
         "S03E3I_EXACT_SOURCE_SHA_REQUIRED")
    h = load("test-tz6v5-s03e3h-running-lab.py", "s03e3i_native_h")
    g04 = h.module("stage2-opnsense-g04-native-runtime.py")
    voice = h.module("stage2-opnsense-real-native-voice-http.py")
    protected = h.module("stage5-native-protected-update.py")
    installed = subprocess.run(
        ["pkg", "query", "%v", "os-zapret2-restyle"], capture_output=True,
        text=True, check=False, timeout=30)
    revision = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$",
                         (ROOT / "Makefile").read_text())
    need(installed.returncode == 0 and revision is not None and
         installed.stdout.strip() ==
         (ROOT / "VERSION").read_text().strip() + "_" + revision.group(1) and
         SERVICE.read_bytes() == (ROOT /
             "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_bytes(),
         "S03E3I_EXACT_INSTALLED_NATIVE_SOURCE_NOT_ATTESTED")
    initial = g04.model()
    strategy = initial.findtext("strategy/trafficargs") or ""
    domains = initial.findtext("hostlist/youtubedomains") or ""
    need(initial.findtext("general/enabled") == "0" and
         not (initial.findtext("general/waninterface") or "") and
         strategy.count("--new") == 1 and
         domains.splitlines() == g04.YOUTUBE and
         not JOURNAL.exists() and not ENGINE.exists(),
         "S03E3I_INITIAL_FRESH_SEEDED_CONFIG_UNQUALIFIED")
    original = CONFIG.read_bytes()
    engine_sha = g04.setup_upstream()
    need(CONFIG.read_bytes() == original and not JOURNAL.exists(),
         "S03E3I_UPSTREAM_SETUP_MUTATED_CONFIG_OR_OWNER")
    # Real installed PHP/HTTPS Apply, never direct writes to Config.
    g04.authenticated_first_apply(strategy, domains)
    web = voice.GuestHttps()
    voice.login(web)
    manual = snapshot(web, h, engine_sha)
    saved = web.api("GET", "/api/zapret/settings/get").get("zapret")
    changed = web.api("POST", "/api/zapret/settings/apply",
                      test_mode_form(saved))
    need(changed.get("result") == "saved" and
         changed.get("status") == "ok" and
         changed.get("requires_review") is not True,
         "S03E3I_REAL_HTTPS_TARGET_AUTO_APPLY_NOT_COMMITTED")
    model = g04.model()
    before = snapshot(web, h, engine_sha)
    need(model.findtext("hostlist/mode") == "auto" and
         before["owner"] != manual["owner"] and
         before["foreign"] == manual["foreign"],
         "S03E3I_COMMON_AUTO_OWNER_OR_MODE_NOT_QUALIFIED")
    learning = native_auto_map(protected, before["owner"])
    native_args_before = raw_native_args()
    config = CONFIG.read_bytes()
    active = web.api("POST", LAB + "status", {"job_id": "@active"})
    need(active.get("status") == "idle",
         "S03E3I_PREEXISTING_LAB_ACTIVE")
    started = web.api("POST", LAB + "start", {
        "target": h.TARGET, "mode": "standard", "language": "ru",
        "enable_quic": "0", "ipv6_enabled": "0"})
    job = started.get("job_id")
    need(started.get("status") == "ok" and
         started.get("state") == "queued" and type(job) is str and
         h.JOB_RE.fullmatch(job) is not None,
         "S03E3I_AUTHENTIC_LAB_NOT_QUEUED")
    terminal = None
    cutoff = time.monotonic() + 480
    while time.monotonic() < cutoff:
        state = web.api("POST", LAB + "status", {"job_id": job})
        need(state.get("job_id") == job and
             state.get("state") in (
                 "queued", "running", "cancel_requested", "completed", "error"),
             "S03E3I_LAB_JOB_STATUS_UNVERIFIED")
        if state["state"] in h.END_STATES:
            terminal = web.api("POST", LAB + "result", {"job_id": job})
            break
        time.sleep(2)
    need(type(terminal) is dict and terminal.get("job_id") == job,
         "S03E3I_LAB_TERMINAL_NOT_AVAILABLE")
    result, extra = physical_report(
        h, web, before, config, g04.model(), protected, learning)
    drift = {
        "provenance_verified": False, "raw_args_changed": "unknown",
        "only_generation_inboxes_changed": "unknown",
        "learning_source_semantics_equal": "unknown",
    }
    if extra["after_schema3_map_valid"]:
        try:
            successor_id = h.current_owner()
            successor_map = native_auto_map(protected, successor_id)
            drift = auto_argv_drift(
                native_args_before, raw_native_args(), learning, successor_map)
        except (Refused, OSError, ValueError, KeyError, TypeError):
            pass
    safe = h.summarize(terminal)
    hashes = lab_semantic_comparison(job)
    print("S03E3I_RUNNING_AUTO_LAB_DIAGNOSTIC=" + json.dumps({
        "source_sha": sha, "mode": "auto", "initial_running": True,
        "before_schema3_learning_count": len(learning), "stage": safe,
        "semantic_hash_equalities": hashes,
        "native_auto_argv_drift": drift,
        "cli_status_rc": result["cli_status_rc"],
        "restored_physical": h.verified_physical_report(result),
        **extra, "owner_appliance_modified": False,
    }, sort_keys=True), flush=True)
    if s03_expected_auto_hash_red(safe, result, extra, drift, hashes, h):
        # Strictly source-level RED fixture accepted; original Lab still FAIL.
        # Only read-only post-state witnesses; NEVER retry/repair/Start/Stop.
        after_red = snapshot(web, h, engine_sha)
        verify_auto_after(protected, before, after_red, learning)
        need(after_red["owned"] == before["owned"] and
             after_red["foreign"] == before["foreign"] and
             before["pid"] != after_red["pid"] and
             CONFIG.read_bytes() == config,
             "S03E3I_EXPECTED_RED_PHYSICAL_STATE_INCOMPLETE")
        print("S03E3I_LAB_PRODUCT=RESTORE_FAILED_CONFIRMED", flush=True)
        print("S03E3I_S03_EXPECTED_RED=PASS_INBOX_ONLY_HASH_FALSE_RESTORE",
              flush=True)
        return
    need(h.acceptance(terminal) and
         h.verified_physical_report(result) and
         extra["hostlist_mode_auto"] and
         extra["after_schema3_map_valid"] and
         extra["original_auto_epoch_retired_if_changed"],
         "S03E3I_NATIVE_AUTO_LAB_RESTORATION_NOT_VERIFIED")
    after = snapshot(web, h, engine_sha)
    verify_auto_after(protected, before, after, learning)
    need(after["owned"] == before["owned"] and
         after["foreign"] == before["foreign"] and
         before["pid"] != after["pid"] and
         CONFIG.read_bytes() == config,
         "S03E3I_AUTO_NATIVE_PHYSICAL_TRANSITION_NOT_RESTORED")
    print("S03E3I_RUNNING_AUTO_LAB=PASS_SCHEMA3_LEARNING_STAGE90_99",
          flush=True)


def load(filename, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    need(spec is not None and spec.loader is not None,
         "S03E3I_NATIVE_MODULE_UNAVAILABLE")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "S03E3I_INVALID_TEST_ARGUMENT")
        execute()
    except (Refused, OSError, ValueError, TypeError, KeyError,
            subprocess.TimeoutExpired, RuntimeError) as exc:
        # The CI reports only fixed test reason, no Config/hostlist/argv.
        message = str(exc)
        code = message if re.fullmatch(r"S03E3I_[A-Z0-9_]{1,100}", message) else "S03E3I_NATIVE_GUARD_REFUSED"
        print("S03E3I_RUNNING_AUTO_LAB=REFUSED:" + code, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
