#!/usr/bin/env python3
"""G05: authenticated RUNNING WAN switch and reverse Apply on disposable OPNsense.

Reuse the already-installed original shared Strategies/Voice owner and FD9.
No new Config writer, lifecycle lock, firewall manager, network packet probe
or intentional post-activation fault is introduced. Reverse Apply is NOT a
proof of automatic rollback after activation failure.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OPTIN = "ZAPRET2_G05_RUNNING_WAN_NATIVE"
STATUS = "PASS_G05_RUNNING_WAN_HTTPS_APPLY_AND_REVERSE"
TARGET_WANS = ("lo0", "wan")


class Refusal(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "g05_running_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def logical_wan(model, g05):
    need(isinstance(model, dict) and isinstance(model.get("general"), dict),
         "RUNNING_WAN_GENERAL_MODEL_MISSING")
    selected = g05.selected(model["general"].get("waninterface"))
    need(isinstance(selected, str), "RUNNING_WAN_SELECT_NOT_SCALAR")
    return selected


def preserved_other_model(before, after):
    need(isinstance(before, dict) and isinstance(after, dict),
         "RUNNING_WAN_NATIVE_MODELS_MISSING")
    a, b = copy.deepcopy(before), copy.deepcopy(after)
    for item in (a, b):
        need(isinstance(item.get("general"), dict) and
             "waninterface" in item["general"], "RUNNING_WAN_FIELD_ABSENT")
        item["general"].pop("waninterface")
    need(a == b, "RUNNING_WAN_MODIFIED_FOREIGN_OR_VOICE_NATIVE_MODEL")


def native_wan_device():
    response = subprocess.run(
        ["/usr/local/sbin/pluginctl", "-4"],
        capture_output=True, text=True, timeout=20, check=False)
    need(response.returncode == 0, "RUNNING_WAN_NATIVE_MAPPING_UNAVAILABLE")
    try:
        data = json.loads(response.stdout)
        entry = data.get("wan")
        need(isinstance(entry, list) and len(entry) >= 1 and
             isinstance(entry[0], dict), "RUNNING_WAN_LOGICAL_MAPPING_MISSING")
        device = entry[0].get("device")
    except (ValueError, TypeError, AttributeError):
        raise Refusal("RUNNING_WAN_MAPPING_UNTRUSTED") from None
    need(isinstance(device, str) and
         re.fullmatch(r"[a-z][a-z0-9_.]{1,31}", device) is not None and
         device != "lo0", "RUNNING_WAN_TARGET_NOT_DISTINCT")
    return device


def rule_target(lines, device):
    need(isinstance(lines, list) and len(lines) == 2,
         "RUNNING_WAN_COMMON_RULE_COUNT_CHANGED")
    for line in lines:
        need("divert 989" in line and "not diverted" in line and
             "xmit " + device in line,
             "RUNNING_WAN_DIVERT_NOT_BOUND_TO_EXPECTED_INTERFACE")
    need(any("udp " in line and "table(zapret2_voice_telegram)" in line
             for line in lines), "RUNNING_WAN_VOICE_IPFW_NOT_PRESERVED")
    need(any("tcp " in line and "65431" in line for line in lines),
         "RUNNING_WAN_STRATEGIES_IPFW_NOT_PRESERVED")


def read_model(web):
    result = web.api("GET", "/api/zapret/settings/get")
    need(isinstance(result.get("zapret"), dict),
         "RUNNING_WAN_SETTINGS_GET_FAILED")
    baseline = result["zapret"].get("hostlist", {}).get("telegramips")
    need(isinstance(baseline, str) and
         baseline.strip() in ("192.0.2.42", "192.0.2.42/32"),
         "RUNNING_WAN_OUTSIDE_DISPOSABLE_VOICE_FIXTURE")
    return result["zapret"], baseline


def form(wan, baseline):
    need(wan in (*TARGET_WANS, "unassigned0"),
         "RUNNING_WAN_TEST_OUTSIDE_FIXED_SCOPE")
    need(isinstance(baseline, str) and
         baseline.strip() in ("192.0.2.42", "192.0.2.42/32"),
         "RUNNING_WAN_UNTRUSTED_BASELINE")
    return [("zapret[sync][telegramips_baseline]", baseline),
            ("zapret[general][waninterface]", wan)]


def shared_owner(active, common, engine_sha, device, *, page="strategies"):
    status = active.action("status")
    need(status.returncode == 0 and
         "zapret is running" in status.stdout,
         "RUNNING_WAN_ENGINE_DROPPED")
    need(hashlib.sha256(active.ENGINE.read_bytes()).hexdigest() == engine_sha,
         "RUNNING_WAN_ENGINE_BINARY_CHANGED")
    need(active.PID.is_file() and not active.PID.is_symlink(),
         "RUNNING_WAN_PIDFILE_UNTRUSTED")
    pid_text = active.PID.read_text().strip()
    need(pid_text.isdecimal() and int(pid_text) > 1,
         "RUNNING_WAN_PID_INVALID")
    pid = int(pid_text)
    process = active.cmd(["/bin/ps", "-p", str(pid), "-o", "command="], timeout=20)
    need(process.returncode == 0 and
         process.stdout.strip().split(" ")[0] == str(active.ENGINE),
         "RUNNING_WAN_ENGINE_PID_NOT_OWNED")
    report = json.loads(common.invoke(
        active, "/usr/local/sbin/configctl", "zapret", "voice_inspect", timeout=60))
    need(report.get("source") == "native-common" and
         report.get("state") == "ready" and
         report.get("rule_count") == 2 and
         report.get("table_count") == 1 and
         report.get("runtime", {}).get("engine_verified") is True and
         report.get("runtime", {}).get("supervisor_verified") is True and
         report.get("runtime", {}).get("services", {}).get("telegram", {}).get("configured") is True,
         "RUNNING_WAN_NATIVE_COMMON_VOICE_NOT_ATTESTED")
    record = json.loads(common.JOURNAL.read_text())
    owner = common.checked_journal(record, page=page)
    rules = active.plugin_rules()
    rule_target(rules, device)
    table = common.invoke(active, "/sbin/ipfw", "table",
                          "zapret2_voice_telegram", "list", timeout=20)
    need("192.0.2.42/32" in table or "192.0.2.42 " in table,
         "RUNNING_WAN_VOICE_IPSET_CHANGED")
    return {"pid": pid, "id": owner, "rules": rules}


def unchanged_after_refusal(active, common, engine_sha, web, original, witness,
                            saved_wan, device, g05, *, page="strategies"):
    need(active.CONFIG.read_bytes() == original,
         "RUNNING_WAN_REFUSED_APPLY_MODIFIED_CONFIG")
    now, _ = read_model(web)
    need(logical_wan(now, g05) == saved_wan,
         "RUNNING_WAN_REFUSAL_CHANGED_MODEL_WAN")
    need(shared_owner(active, common, engine_sha, device, page=page) == witness,
         "RUNNING_WAN_REFUSAL_MUTATED_SHARED_OWNER")


def execute():
    for key in ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_NATIVE_BUILD_CI",
                "ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_STAGE2_REAL_ACTIVE_SERVICE",
                "ZAPRET2_STAGE2_REAL_COMMON_VOICE",
                "ZAPRET2_STAGE2_REAL_VOICE_HTTP", OPTIN):
        need(os.environ.get(key) == "1",
             "RUNNING_WAN_EXPLICIT_DISPOSABLE_OPTIN_REQUIRED:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.uname().sysname == "FreeBSD" and
         os.geteuid() == 0, "RUNNING_WAN_DISPOSABLE_FREEBSD_ROOT_REQUIRED")

    active = load("stage2-opnsense-real-native-active-service.py")
    common = load("stage2-opnsense-real-native-shared-voice.py")
    voice = load("stage2-opnsense-real-native-voice-http.py")
    g05 = load("stage2-opnsense-g05-wan-save.py")
    boot = load("stage2-opnsense-real-native-boot-syshook.py")
    engine_sha = active.guest_preflight()
    target_device = native_wan_device()

    web = voice.GuestHttps()
    voice.login(web)
    page = web.request("GET", "/ui/zapret")
    need("frm_GeneralSettings" in page and
         "/api/zapret/settings/apply" in page,
         "RUNNING_WAN_AUTHENTICATED_GENERAL_PAGE_MISSING")
    before, baseline = read_model(web)
    need(logical_wan(before, g05) == "lo0" and
         before["voice"]["telegram"]["enabled"] == "1",
         "RUNNING_WAN_NOT_THE_FIXED_ENABLED_VOICE_BASELINE")
    original = active.CONFIG.read_bytes()
    old = shared_owner(active, common, engine_sha, "lo0", page="voice")

    # Both invalid mapping and stale Telegram tab must refuse BEFORE any
    # runtime, IPFW, journal or Config mutation.
    for target, token in (("unassigned0", baseline),
                          ("wan", "__g05_stale_telegram__")):
        result = web.api("POST", "/api/zapret/settings/apply",
                         form(target, token) if token == baseline else
                         [("zapret[sync][telegramips_baseline]", token),
                          ("zapret[general][waninterface]", target)])
        need(result.get("result") == "failed" and
             result.get("applied") is not True and
             result.get("requires_review") is not True,
             "RUNNING_WAN_INVALID_INPUT_NOT_SAFELY_REJECTED")
        unchanged_after_refusal(active, common, engine_sha, web, original,
                                old, "lo0", "lo0", g05, page="voice")

    # Full authenticated Apply under the original FD9, never Config-only
    # wan-saved. The first change must truly move owned divert to WAN.
    applied = web.api("POST", "/api/zapret/settings/apply",
                      form("wan", baseline))
    need(applied.get("result") == "saved" and
         applied.get("status") == "ok" and
         applied.get("applied") is True,
         "RUNNING_WAN_FULL_NATIVE_APPLY_NOT_COMMITTED")
    changed_model, changed_baseline = read_model(web)
    need(logical_wan(changed_model, g05) == "wan",
         "RUNNING_WAN_LOGICAL_INTERFACE_NOT_SAVED")
    preserved_other_model(before, changed_model)
    changed_xml = active.CONFIG.read_bytes()
    need(ET.fromstring(changed_xml).findtext(
        "./OPNsense/Zapret/general/waninterface") == "wan" and
         boot.config_except_model(original) == boot.config_except_model(changed_xml) and
         voice.native_unmanaged_xml(original) ==
         voice.native_unmanaged_xml(changed_xml),
         "RUNNING_WAN_POSITIVE_CONFIG_OR_FOREIGN_XML_INVALID")
    moved = shared_owner(active, common, engine_sha, target_device)
    need(moved["pid"] != old["pid"] and moved["id"] != old["id"],
         "RUNNING_WAN_FULL_APPLY_DID_NOT_REPLACE_ORIGINAL_OWNER")

    # Invalid WAN while active on the new interface also refuses unchanged.
    bad = web.api("POST", "/api/zapret/settings/apply",
                  form("unassigned0", changed_baseline))
    need(bad.get("result") == "failed" and
         bad.get("requires_review") is not True and
         bad.get("applied") is not True,
         "RUNNING_WAN_ACTIVE_INVALID_MAPPING_NOT_REJECTED")
    unchanged_after_refusal(active, common, engine_sha, web, changed_xml,
                            moved, "wan", target_device, g05)

    # Explicit reverse Apply through the same installed API, not a private
    # Config edit. This validates reversibility, not automatic fault rollback.
    restored = web.api("POST", "/api/zapret/settings/apply",
                       form("lo0", changed_baseline))
    need(restored.get("result") == "saved" and
         restored.get("status") == "ok" and
         restored.get("applied") is True,
         "RUNNING_WAN_REVERSE_FULL_APPLY_NOT_COMMITTED")
    final_model, _ = read_model(web)
    voice.attest_complete_native_model(before, final_model)
    final = common.witness(active, engine_sha, running=True, page="strategies")
    need(final["id"] != moved["id"] and
         final["pid"] != moved["pid"] and
         final["rules"] == old["rules"],
         "RUNNING_WAN_REVERSE_OWNER_OR_RULES_NOT_RESTORED")
    final_xml = active.CONFIG.read_bytes()
    need(boot.config_except_model(original) ==
         boot.config_except_model(final_xml) and
         voice.native_unmanaged_xml(original) ==
         voice.native_unmanaged_xml(final_xml),
         "RUNNING_WAN_REVERSE_MODIFIED_UNRELATED_CONFIG")
    return {
        "schema": 1, "status": STATUS,
        "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        "two_real_authenticated_full_wan_apply": True,
        "invalid_wan_and_stale_tab_refused_unchanged": True,
        "shared_voice_remained_attested": True,
        "original_fd9_owner_rotated": True,
        "scoped_ipfw_moved_to_resolved_wan_and_back": True,
        "whole_native_model_restored": True,
        "foreign_config_unchanged": True,
        "automatic_post_activation_rollback_tested": False,
        "voice_media_tested": False,
        "physical_owner_browser_tested": False,
        "owner_device_changed": False,
    }


def self_test():
    sample = {"general": {"enabled": "1", "waninterface": "lo0"},
              "voice": {"telegram": {"enabled": "1"}},
              "hostlist": {"telegramips": "192.0.2.42/32"}}
    moved = copy.deepcopy(sample)
    moved["general"]["waninterface"] = "wan"
    preserved_other_model(sample, moved)
    assert len(form("wan", "192.0.2.42/32")) == 2
    assert len(form("lo0", "192.0.2.42")) == 2
    for bad in ("lan", "opt0", "", "vtnet1"):
        try:
            form(bad, "192.0.2.42/32")
        except Refusal:
            pass
        else:
            raise AssertionError("unsafe WAN test target admitted")
    changed = copy.deepcopy(moved)
    changed["voice"]["telegram"]["enabled"] = "0"
    try:
        preserved_other_model(sample, changed)
    except Refusal:
        pass
    else:
        raise AssertionError("foreign Voice mutation permitted")
    lines = [
        "19000 divert 989 udp from any to table(zapret2_voice_telegram) out not diverted not sockarg xmit vtnet1",
        "19001 divert 989 tcp from any to any 65431 out not diverted not sockarg xmit vtnet1",
    ]
    rule_target(lines, "vtnet1")
    for bad in (lines[:1], [lines[0], lines[1].replace("vtnet1", "lo0")],
                [lines[0].replace("989", "999"), lines[1]]):
        try:
            rule_target(bad, "vtnet1")
        except Refusal:
            pass
        else:
            raise AssertionError("unsafe WAN IPFW ownership accepted")
    print("PASS: G05 RUNNING WAN form/Voice/IPFW scope and negative contracts")


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "RUNNING_WAN_EXPECTED_RUN_OR_SELF_TEST")
        report = execute()
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            ET.ParseError, subprocess.TimeoutExpired) as error:
        print("G05_RUNNING_NATIVE=REFUSED:" + str(error), file=sys.stderr)
        return 2
    print("G05_RUNNING_NATIVE=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
