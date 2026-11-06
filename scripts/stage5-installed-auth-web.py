#!/usr/bin/env python3
"""Authenticated installed OPNsense Web/API read-only and refusal acceptance.

Disposable OPNsense 26.7 loopback only. Reuses the already proven native
Voice HTTPS cookie/CSRF login. Does not start Strategy Lab jobs, fetch resources,
perform Install/Remove, mutate Config, or claim an actual browser button click.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OPTIN = "ZAPRET2_STAGE5_AUTHENTICATED_WEB_READONLY"
STATUS = "PASS_STAGE5_INSTALLED_AUTHENTICATED_LAB_EXTRA_HTTP_READONLY"
LAB_BASE = "/api/zapret/strategy_lab/"
RESOURCE_BASE = "/api/zapret/service/"


class Refusal(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def module(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_web_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resource_status(data):
    need(isinstance(data, dict) and data.get("status") == "ok",
         "INSTALLED_EXTRA_HTTP_RESOURCE_STATUS_NOT_OK")
    need(type(data.get("busy")) is bool and
         (data.get("installed") is None or type(data["installed"]) is bool),
         "INSTALLED_EXTRA_HTTP_RESOURCE_STATUS_UNTRUSTED")
    need(data.get("phase") in {
        "unknown", "ready", "not_installed", "failed", "restored",
        "no_recovery_needed", "recovery_required", "restore_failed",
    }, "INSTALLED_EXTRA_HTTP_RESOURCE_PHASE_UNEXPECTED")
    need(type(data.get("lua")) is int and 0 <= data["lua"] <= 10000 and
         type(data.get("bin")) is int and 0 <= data["bin"] <= 10000,
         "INSTALLED_EXTRA_HTTP_RESOURCE_COUNTS_INVALID")
    need(data["busy"] is False,
         "INSTALLED_EXTRA_HTTP_RESOURCE_OPERATION_BUSY")
    return {"status_ok": True, "busy": False, "installed": data["installed"]}


def inventory_status(data):
    need(isinstance(data, dict) and
         data.get("status") in ("ok", "unavailable"),
         "INSTALLED_EXTRA_HTTP_INVENTORY_NOT_AVAILABLE_OR_EXPLICIT_REFUSAL")
    if data["status"] == "unavailable":
        return False
    need(type(data.get("installed")) is bool,
         "INSTALLED_EXTRA_HTTP_INVENTORY_INSTALLED_NOT_BOOLEAN")
    for ext in ("lua", "bin"):
        items = data.get(ext)
        need(isinstance(items, list) and len(items) <= 4096,
             "INSTALLED_EXTRA_HTTP_INVENTORY_INVALID_LIST")
        for item in items:
            need(isinstance(item, dict) and
                 item.get("origin") in ("upstream", "other") and
                 isinstance(item.get("name"), str) and
                 re.fullmatch(r"[A-Za-z0-9_.+-]+\." + ext, item["name"]) is not None,
                 "INSTALLED_EXTRA_HTTP_INVENTORY_ITEM_UNTRUSTED")
    return True


def self_test():
    good = {"status":"ok","busy":False,"installed":False,"phase":"not_installed",
            "lua":0,"bin":0}
    assert resource_status(good)["status_ok"]
    assert not inventory_status({"status":"unavailable"})
    assert inventory_status({"status":"ok","installed":False,"lua":[],"bin":[]})
    for data in (
        dict(good, busy=True), dict(good, phase="downloading"),
        dict(good, installed="0"), dict(good, lua=-1),
    ):
        try:
            resource_status(data)
        except Refusal:
            pass
        else:
            raise AssertionError("untrusted resource HTTP status accepted")
    for data in ({"status":"ok","installed":False,"lua":[{"name":"../x.lua",
                   "origin":"upstream"}],"bin":[]},
                 {"status":"ok","installed":False,"lua":[],"bin":"bad"},
                 {"status":"other"}):
        try:
            inventory_status(data)
        except Refusal:
            pass
        else:
            raise AssertionError("untrusted inventory HTTP status accepted")
    # Prevent a future source-only test typo from consuming a costly native VM.
    menu = ET.parse(HERE.parent / "src/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml").getroot()
    assert menu.find(".//General").get("url") == "/ui/zapret"
    assert menu.find(".//Diagnostics").get("url") == "/ui/zapret/diagnostics"
    print("PASS_STAGE5_AUTH_WEB_SAFE_JSON_AND_REFUSAL_CONTRACTS=1")
    return 0


def execute():
    for key in ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_NATIVE_BUILD_CI", OPTIN):
        need(os.environ.get(key) == "1",
             "INSTALLED_AUTH_WEB_MISSING_DISPOSABLE_OPTIN:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true",
         "INSTALLED_AUTH_WEB_NOT_GITHUB_DISPOSABLE_CI")
    active = module("stage2-opnsense-real-native-active-service.py")
    common = module("stage2-opnsense-real-native-shared-voice.py")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    engine_sha = active.guest_preflight()
    before = common.witness(active, engine_sha, running=True)
    config = active.CONFIG.read_bytes()
    journal = common.JOURNAL.read_bytes()
    ipfw = active.plugin_rules()

    web = voice.GuestHttps()
    voice.login(web)
    # Real PHP/Volt render through installed OPNsense, no browser emulation.
    general = web.request("GET", "/ui/zapret")
    diagnostics = web.request("GET", "/ui/zapret/diagnostics")
    need("resourcesStatus" in general and "resourcesInventory" in general,
         "INSTALLED_GENERAL_RESOURCE_WEB_PAGE_MISSING")
    need("strategyLabBtn" in diagnostics and
         "/api/zapret/strategy_lab/status" in diagnostics,
         "INSTALLED_DIAGNOSTICS_LAB_WEB_PAGE_MISSING")

    resources = resource_status(
        web.api("POST", RESOURCE_BASE + "resourcesStatus", {}))
    inventory_present = inventory_status(
        web.api("POST", RESOURCE_BASE + "resourcesInventory", {}))
    need(web.api("GET", RESOURCE_BASE + "resourcesStatus").get("status") == "failed",
         "INSTALLED_EXTRA_HTTP_GET_STATUS_ACCEPTED")
    need(web.api("GET", RESOURCE_BASE + "resourcesInventory").get("status") == "failed",
         "INSTALLED_EXTRA_HTTP_GET_INVENTORY_ACCEPTED")

    idle = web.api("POST", LAB_BASE + "status", {"job_id": "@active"})
    need(idle.get("status") == "idle",
         "INSTALLED_LAB_HTTP_ACTIVE_JOB_NOT_IDLE")
    need(web.api("GET", LAB_BASE + "status").get("status") == "error",
         "INSTALLED_LAB_HTTP_GET_STATUS_ACCEPTED")
    for path in ("cancel", "result"):
        rejected = web.api("POST", LAB_BASE + path,
                           {"job_id": "../invalid"})
        need(rejected.get("status") == "error" and
             "Invalid Strategy Lab job id" in rejected.get("message", ""),
             "INSTALLED_LAB_HTTP_INVALID_JOB_NOT_REFUSED:" + path)
    invalid_start = web.api("POST", LAB_BASE + "start",
                            {"target": "", "mode": "standard", "language": "en"})
    need(invalid_start.get("status") == "error" and
         "Invalid Strategy Lab" in invalid_start.get("message", ""),
         "INSTALLED_LAB_HTTP_INVALID_START_NOT_REFUSED")

    after = common.witness(active, engine_sha, running=True)
    need(before == after and active.CONFIG.read_bytes() == config and
         common.JOURNAL.read_bytes() == journal and
         active.plugin_rules() == ipfw,
         "INSTALLED_AUTH_WEB_MODIFIED_REAL_CONFIG_FD9_ENGINE_IPFW")
    report = {
        "schema": 1, "status": STATUS,
        "installed_general_and_diagnostics_pages_served": True,
        "stock_cookie_csrf_authenticated_https": True,
        "installed_lab_http_idle_status": True,
        "installed_lab_http_invalid_start_cancel_result_refused": True,
        "installed_extra_http_status_and_inventory_endpoint": True,
        "installed_extra_cached_inventory_present": inventory_present,
        "installed_extra_status_was_not_busy": True,
        "saved_config_original_fd9_engine_ipfw_unchanged": True,
        "network_targets_loopback_only": True,
        "real_lab_probe_or_job_started": False,
        "extra_resources_install_remove_tested": False,
        "physical_browser_button_click_tested": False,
        "voice_media_or_wan_ipv6_packets_tested": False,
        "owner_appliance_modified": False,
    }
    print("STAGE5_INSTALLED_AUTH_WEB=" + json.dumps(report, sort_keys=True))
    return report


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            execute()
            return 0
        raise Refusal("INSTALLED_AUTH_WEB_EXPECTED_SELF_TEST_OR_RUN")
    except (Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        print("STAGE5_INSTALLED_AUTH_WEB=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
