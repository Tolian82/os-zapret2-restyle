#!/usr/bin/env python3
"""G07 S2 one installed OPNsense 26.7 GUI Start/Stop/Restart and lower Apply.

Reuses G04 first-install/reinstall of the same native pkg and actual dvtws2
v1.0.7. Only original authenticated HTTPS and stock original-FD9 service
actions mutate runtime; no test-specific Config, IPFW or daemon owner.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


class Refusal(RuntimeError):
    pass


def need(check, reason):
    if not check:
        raise Refusal(reason)


def load(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "g07_" + name.replace("-", "_").replace(".", "_"), ROOT / name)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def status(web, expected):
    receipt = web.api("POST", "/api/zapret/service/runtime")
    need(receipt.get("status") == "ok" and
         receipt.get("installed") is True and
         receipt.get("busy") is False and
         receipt.get("service") == expected and
         receipt.get("version") == "v1.0.7" and
         receipt.get("setup") == "ready" and
         "reason" not in receipt,
         "G07_HTTPS_NATIVE_RUNTIME_NOT_" + expected.upper())
    return receipt


def runtime_classifier(data):
    if not isinstance(data, dict) or data.get("status") != "ok":
        return "error"
    if not isinstance(data.get("installed"), bool) or not isinstance(
        data.get("busy"), bool):
        return "error"
    if data["busy"]:
        return "installing" if data.get("setup") == "installing" else "error"
    if data.get("setup") == "installing":
        return "error"
    if not data["installed"]:
        return "not-installed" if data.get("service") == "error" and (
            data.get("setup") == "unknown" and data.get("version") == "") else "error"
    if data.get("service") not in ("started", "stopped") or not re.fullmatch(
        r"v[0-9]+(?:\.[0-9]+)+", str(data.get("version", ""))):
        return "error"
    return data["service"]


def self_test():
    seed = {"status": "ok", "installed": False, "busy": False,
            "setup": "unknown", "service": "error", "version": ""}
    for args, expected in ((seed, "not-installed"),
                           ({**seed, "busy": True, "setup": "installing"}, "installing"),
                           ({**seed, "installed": True, "setup": "ready",
                             "service": "stopped", "version": "v1.0.7"}, "stopped"),
                           ({**seed, "installed": True, "setup": "ready",
                             "service": "started", "version": "v1.0.7"}, "started"),
                           ({**seed, "installed": None}, "error"),
                           ({**seed, "installed": True, "service": "started",
                             "version": ""}, "error")):
        need(runtime_classifier(args) == expected, "G07_FAST_STATUS_INCONSISTENT")
    print("G07_NATIVE_LIFECYCLE_FAST=PASS")


def refused_first_start(web, core):
    # Test the real inherited service/start API with its G05 WAN-first
    # controller guard, before ANY user WAN is persisted. No retry on loss.
    need(web.csrf_token is not None, "G07_NATIVE_HTTPS_CSRF_MISSING")
    headers = {"X-CSRFToken": web.csrf_token, "Accept": "application/json",
               "Referer": core.ORIGIN + "/ui/zapret"}
    request = urllib.request.Request(
        core.ORIGIN + "/api/zapret/service/start", data=b"", method="POST",
        headers=headers)
    try:
        with web.client.open(request, timeout=40):
            raise Refusal("G07_MISSING_WAN_GUI_START_UNEXPECTEDLY_ACCEPTED")
    except urllib.error.HTTPError as error:
        body = error.read(65536).decode("utf-8", "replace")
        need(error.code in (400, 409, 422, 500) and
             "Select a WAN interface" in body,
             "G07_MISSING_WAN_API_DID_NOT_EXPLAIN_WAN_FIRST")
    return True


def apply_wan_only(web, g05):
    old, baseline = g05.gui_wan(web)
    need(old in ("", None), "G07_G04_WAN_ALREADY_CONFIGURED")
    reply = g05.request(web, "lo0", baseline)
    need(reply.get("result") == "saved" and
         reply.get("status") == "ok" and reply.get("applied") is False,
         "G07_FIRST_WAN_SAVE_TRIGGERED_RUNTIME")
    after, _ = g05.gui_wan(web)
    need(after == "lo0", "G07_SAVED_WAN_NOT_READABLE_AFTER_GUI_REFRESH")


def action(web, name):
    need(name in ("stop", "start", "restart"), "G07_UNTRUSTED_NATIVE_ACTION")
    # Same authenticated endpoint used by the actual service control button.
    response = web.api("POST", "/api/zapret/service/" + name)
    need(isinstance(response, dict), "G07_SERVICE_ACTION_NOT_JSON")


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G07_NATIVE_LIFECYCLE") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "G07_DISPOSABLE_OPNSENSE_ROOT_REQUIRED")
    head = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(re.fullmatch(r"[a-f0-9]{40}", head) is not None,
         "G07_CI_SOURCE_SHA_NOT_ATTESTED")
    g06 = load("stage2-opnsense-g06-native-shared-voice.py")
    g05 = load("stage2-opnsense-g05-wan-save.py")
    core = load("stage2-opnsense-real-native-voice-http.py")
    boot = load("stage2-opnsense-real-native-boot-syshook.py")
    # G04 earlier in this SAME disposable VM installed and reinstalled
    # the exact real Mk archive and upstream engine with saved user-empty
    # Traffic Strategy/YouTube Domains.
    need(g06.ENGINE.is_file() and not g06.ENGINE.is_symlink(),
         "G07_REAL_INSTALLED_V1_0_7_ENGINE_REQUIRED")
    engine_sha = hashlib.sha256(g06.ENGINE.read_bytes()).hexdigest()
    original = g06.CONFIG.read_bytes()
    node = ET.fromstring(original).find("./OPNsense/Zapret")
    need(node is not None and node.findtext("general/enabled") == "0" and
         not (node.findtext("general/waninterface") or "") and
         not (node.findtext("strategy/trafficargs") or "") and
         not (node.findtext("hostlist/youtubedomains") or ""),
         "G07_G04_COLD_EMPTY_USER_CONFIG_NOT_QUALIFIED")
    current, foreign = g06.rule_sets()
    need(not current and not g06.PID.exists(), "G07_G04_LEFT_ACTIVE_SERVICE")
    foreign_config = boot.config_except_model(original)
    web = core.GuestHttps()
    core.login(web)
    status(web, "stopped")
    refused_first_start(web, core)
    need(g06.CONFIG.read_bytes() == original and
         g06.rule_sets() == ([], foreign) and not g06.PID.exists(),
         "G07_MISSING_WAN_REFUSAL_MUTATED_NATIVE_OWNER")

    apply_wan_only(web, g05)
    status(web, "stopped")
    need(g06.rule_sets() == ([], foreign) and not g06.PID.exists(),
         "G07_WAN_ONLY_SAVE_STARTED_SERVICE")

    # First real lower GUI Apply with valid saved WAN and enabled=1.
    g06.strategies(web, "", first=True)
    first = g06.running(engine_sha, foreign, voice=0, ordinary=0,
                        page="strategies")
    status(web, "started")

    # The actual lower service button (stock API), not direct kernel edits.
    action(web, "stop")
    status(web, "stopped")
    rules, unchanged = g06.rule_sets()
    need(not rules and unchanged == foreign and not g06.PID.exists(),
         "G07_GUI_STOP_LEFT_NATIVE_PID_OR_IPFW")

    action(web, "start")
    again = g06.running(engine_sha, foreign, voice=0, ordinary=0,
                        page="strategies")
    status(web, "started")
    need(again["id"] == first["id"] and again["pid"] != first["pid"],
         "G07_GUI_START_DID_NOT_RESTORE_COMMON_OWNER")

    action(web, "restart")
    restart = g06.running(engine_sha, foreign, voice=0, ordinary=0,
                          page="strategies")
    status(web, "started")
    need(restart["id"] == first["id"] and restart["pid"] != again["pid"],
         "G07_GUI_RESTART_DID_NOT_ROTATE_ONE_ENGINE")

    # Lower Apply adds one actual scoped ordinary rule to the same owner.
    g06.strategies(web, g06.ORDINARY)
    combined = g06.running(engine_sha, foreign, voice=0, ordinary=1,
                           page="strategies")
    need(combined["id"] != first["id"] and combined["pid"] != restart["pid"],
         "G07_LOWER_APPLY_DID_NOT_COMMIT_ORDINARY")
    status(web, "started")

    # Invalid strategy must fail with explicit native validation and no
    # change to saved Config, PID or IPFW; no auto-retry of ambiguous Apply.
    saved = g06.CONFIG.read_bytes()
    model = web.api("GET", "/api/zapret/settings/get")["zapret"]
    baseline = model["hostlist"]["telegramips"]
    bad = web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", baseline),
        ("zapret[strategy][trafficargs]", "--not-a-real-dvtws2-option")])
    need(bad.get("result") == "failed" and bad.get("applied") is False and
         bad.get("requires_review") is not True and
         g06.CONFIG.read_bytes() == saved and
         g06.running(engine_sha, foreign, 0, 1, "strategies") == combined,
         "G07_INVALID_LOWER_APPLY_MUTATED_NATIVE_OWNER")

    g06.strategies(web, "")
    cleared = g06.running(engine_sha, foreign, voice=0, ordinary=0,
                          page="strategies")
    need(cleared["id"] != combined["id"] and not cleared["rules"],
         "G07_REMOVING_LAST_ORDINARY_DID_NOT_CLEAR_IPFW")
    action(web, "stop")
    status(web, "stopped")
    owned, after_foreign = g06.rule_sets()
    need(not owned and not g06.PID.exists() and after_foreign == foreign and
         boot.config_except_model(g06.CONFIG.read_bytes()) == foreign_config,
         "G07_FINAL_GUI_STOP_CHANGED_FOREIGN_CONFIG_OR_IPFW")
    return {
        "status": "PASS_G07_REAL_HTTPS_GUI_LIFECYCLE_AND_LOWER_APPLY",
        "source_sha": head, "real_engine_sha256": engine_sha,
        "missing_wan_first_start_refused_no_mutation": True,
        "wan_only_save_without_engine_launch": True,
        "first_https_lower_apply_real_process": True,
        "https_stop_start_restart_real_one_engine": True,
        "lower_apply_ordinary_add_remove_exact_ipfw": True,
        "invalid_profile_apply_refused_unchanged": True,
        "saved_wan_and_foreign_config_ipfw_preserved": True,
        "original_fd9_shared_owner": True,
        "physical_owner_browser_tested": False,
        "real_network_dpi_or_voice_media_tested": False,
        "power_loss_recovery_tested": False,
    }


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "G07_RUN_OR_SELF_TEST_REQUIRED")
        record = execute()
    except (Refusal, OSError, ValueError, KeyError, TypeError,
            urllib.error.URLError, ET.ParseError) as error:
        print("G07_NATIVE_LIFECYCLE=REFUSED:" + str(error), file=sys.stderr)
        return 2
    print("G07_NATIVE_LIFECYCLE=" + json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
