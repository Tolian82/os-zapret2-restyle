#!/usr/bin/env python3
"""Real authenticated Strategies Exclude Domains/IPSet HTTP Apply and restore.

One disposable OPNsense 26.7 guest, installed native plugin, original FD9
and a pinned lo0 engine. Never use on an owner appliance or a WAN interface.
No external probe, real IPv6 packet, browser-click or release claim.
"""
from __future__ import annotations

import copy
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OPTIN = "ZAPRET2_STAGE5_AUTHENTICATED_EXCLUDE_APPLY"
STATUS = "PASS_STAGE5_INSTALLED_EXCLUDE_AUTHENTICATED_HTTPS_APPLY_RESTORE"
TEST_DOMAIN = "exclude.example"
TEST_IPSET = "192.0.2.88/32"
TEST_NETWORK = ipaddress.ip_network(TEST_IPSET)


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_exclude_https_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hostlist(model):
    need(isinstance(model, dict) and isinstance(model.get("hostlist"), dict),
         "EXCLUDE_HTTPS_NATIVE_MODEL_MISSING")
    data = model["hostlist"]
    for field in ("telegramips", "excludedomains", "excludeipset"):
        need(isinstance(data.get(field), str),
             "EXCLUDE_HTTPS_NATIVE_FIELD_NOT_SCALAR:" + field)
    return data


def form(model, *, domains, ipset):
    saved = hostlist(model)
    # This positive test is only meaningful against our test-only empty
    # Exclude fixture and the pinned shared Voice 192.0.2.42 destination.
    need(saved["telegramips"].strip() in ("192.0.2.42", "192.0.2.42/32"),
         "EXCLUDE_HTTPS_NOT_THE_DISPOSABLE_VOICE_BASELINE")
    need(domains in ("", TEST_DOMAIN) and
         ipset in ("", TEST_IPSET, "0.0.0.0/0"),
         "EXCLUDE_HTTPS_REQUEST_OUTSIDE_TEST_SCOPE")
    return [
        ("zapret[sync][telegramips_baseline]", saved["telegramips"]),
        ("zapret[hostlist][excludedomains]", domains),
        ("zapret[hostlist][excludeipset]", ipset),
    ]


def read_model(web):
    result = web.api("GET", "/api/zapret/settings/get")
    need(isinstance(result.get("zapret"), dict),
         "EXCLUDE_HTTPS_INSTALLED_SETTINGS_LOAD_UNAVAILABLE")
    hostlist(result["zapret"])
    return result["zapret"]


def network_equal(text):
    try:
        return ipaddress.ip_network(text.strip(), strict=False) == TEST_NETWORK
    except (ValueError, AttributeError):
        return False


def saved_fields(raw, *, domains, ipset):
    root = ET.fromstring(raw)
    items = root.findall("./OPNsense/Zapret/hostlist")
    need(len(items) == 1, "EXCLUDE_HTTPS_SAVED_HOSTLIST_AMBIGUOUS")
    actual_domain = items[0].findtext("excludedomains") or ""
    actual_ipset = items[0].findtext("excludeipset") or ""
    need(actual_domain.strip() == domains and
         (network_equal(actual_ipset) if ipset else not actual_ipset.strip()),
         "EXCLUDE_HTTPS_SAVED_FIELDS_NOT_APPLIED_OR_RESTORED")
    return True


def unchanged_other_model(before, after):
    need(isinstance(before, dict) and isinstance(after, dict),
         "EXCLUDE_HTTPS_MODEL_NOT_OBJECT")
    a, b = copy.deepcopy(before), copy.deepcopy(after)
    for item in (a, b):
        data = hostlist(item)
        for name in ("excludedomains", "excludeipset"):
            data.pop(name)
    need(a == b, "EXCLUDE_HTTPS_UNRELATED_NATIVE_MODEL_CHANGED")


def self_test():
    sample = {"general": {"enabled": "1"}, "hostlist": {
        "telegramips": "192.0.2.42/32", "excludedomains": "",
        "excludeipset": ""}, "voice": {"telegram": {"enabled": "1"}}}
    assert len(form(sample, domains=TEST_DOMAIN, ipset=TEST_IPSET)) == 3
    assert dict(form(sample, domains=TEST_DOMAIN, ipset=TEST_IPSET))[
        "zapret[hostlist][excludeipset]"] == TEST_IPSET
    assert network_equal("192.0.2.88")
    assert not network_equal("192.0.2.80/28")
    unchanged_other_model(sample, {**sample, "hostlist": {
        **sample["hostlist"], "excludedomains": TEST_DOMAIN,
        "excludeipset": TEST_IPSET}})
    for domains, ipset in (("unexpected.example", TEST_IPSET),
                           (TEST_DOMAIN, "0.0.0.0/1"),
                           (TEST_DOMAIN, "2001:db8::/32")):
        try:
            form(sample, domains=domains, ipset=ipset)
        except Refusal:
            pass
        else:
            raise AssertionError("unsafe Exclude test form accepted")
    foreign = copy.deepcopy(sample)
    foreign["hostlist"]["telegramips"] = "0.0.0.0/0"
    try:
        form(foreign, domains=TEST_DOMAIN, ipset=TEST_IPSET)
    except Refusal:
        pass
    else:
        raise AssertionError("foreign Telegram baseline accepted")
    print("PASS_STAGE5_EXCLUDE_HTTPS_FORM_SCOPE_AND_NEGATIVES=1")
    return 0


def execute():
    for key in ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_NATIVE_BUILD_CI", OPTIN):
        need(os.environ.get(key) == "1",
             "EXCLUDE_HTTPS_DISPOSABLE_OPTIN_REQUIRED:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true",
         "EXCLUDE_HTTPS_GITHUB_DISPOSABLE_GUEST_REQUIRED")

    active = load("stage2-opnsense-real-native-active-service.py")
    common = load("stage2-opnsense-real-native-shared-voice.py")
    boot = load("stage2-opnsense-real-native-boot-syshook.py")
    voice = load("stage2-opnsense-real-native-voice-http.py")
    engine_sha = active.guest_preflight()
    baseline = common.witness(active, engine_sha, running=True)
    original_xml = active.CONFIG.read_bytes()

    web = voice.GuestHttps()
    voice.login(web)
    general = web.request("GET", "/ui/zapret")
    need("frm_GeneralSettings" in general and
         "/api/zapret/settings/apply" in general and
         "telegramips_baseline" in general,
         "EXCLUDE_HTTPS_REAL_GENERAL_PAGE_NOT_INSTALLED")
    before = read_model(web)
    initial = hostlist(before)
    need(not initial["excludedomains"].strip() and
         not initial["excludeipset"].strip(),
         "EXCLUDE_HTTPS_NOT_AN_EMPTY_DISPOSABLE_EXCLUDE_FIXTURE")

    # Negative input must fail at the real PHP -> native policy preflight;
    # no Config, FD9, engine or IPFW mutation is permitted.
    bad = web.api("POST", "/api/zapret/settings/apply",
                  form(before, domains=TEST_DOMAIN, ipset="0.0.0.0/0"))
    need(bad.get("result") == "failed" and
         (isinstance(bad.get("validations"), dict) or
          bad.get("applied") is False),
         "EXCLUDE_HTTPS_FULL_FAMILY_NOT_REJECTED")
    need(active.CONFIG.read_bytes() == original_xml and
         common.witness(active, engine_sha, running=True) == baseline,
         "EXCLUDE_HTTPS_INVALID_REQUEST_MUTATED_OWNER")

    applied = web.api("POST", "/api/zapret/settings/apply",
                      form(before, domains=TEST_DOMAIN, ipset=TEST_IPSET))
    need(applied.get("result") == "saved" and applied.get("status") == "ok",
         "EXCLUDE_HTTPS_POSITIVE_NATIVE_APPLY_NOT_COMMITTED")
    changed = read_model(web)
    fields = hostlist(changed)
    need(fields["excludedomains"].strip() == TEST_DOMAIN and
         network_equal(fields["excludeipset"]),
         "EXCLUDE_HTTPS_POSITIVE_MODEL_NOT_PERSISTED")
    unchanged_other_model(before, changed)
    saved_fields(active.CONFIG.read_bytes(), domains=TEST_DOMAIN, ipset=TEST_IPSET)
    new = common.witness(active, engine_sha, running=True)
    need(new["id"] != baseline["id"] and new["pid"] != baseline["pid"] and
         new["rules"] == baseline["rules"],
         "EXCLUDE_HTTPS_POSITIVE_COMMON_FD9_OR_SCOPED_IPFW_INVALID")

    # Reuse the installed Settings API for the reverse Apply, not a direct
    # filesystem rollback or an alternative service/controller.
    restored = web.api("POST", "/api/zapret/settings/apply",
                       form(changed, domains="", ipset=""))
    need(restored.get("result") == "saved" and restored.get("status") == "ok",
         "EXCLUDE_HTTPS_RESTORE_APPLY_NOT_COMMITTED")
    final_model = read_model(web)
    voice.attest_complete_native_model(before, final_model)
    saved_fields(active.CONFIG.read_bytes(), domains="", ipset="")
    final = common.witness(active, engine_sha, running=True)
    need(final["id"] != new["id"] and final["pid"] != new["pid"] and
         final["rules"] == baseline["rules"],
         "EXCLUDE_HTTPS_RESTORED_NATIVE_OWNER_OR_IPFW_INVALID")
    final_xml = active.CONFIG.read_bytes()
    need(boot.config_except_model(original_xml) ==
         boot.config_except_model(final_xml) and
         voice.native_unmanaged_xml(original_xml) ==
         voice.native_unmanaged_xml(final_xml),
         "EXCLUDE_HTTPS_FOREIGN_OR_UNKNOWN_XML_CHANGED")

    report = {
        "schema": 1, "status": STATUS,
        "stock_cookie_csrf_authenticated_https": True,
        "installed_strategies_api_positive_exclude_apply": True,
        "real_invalid_full_family_refused_before_mutation": True,
        "native_exclude_domains_and_ipset_applied": True,
        "native_exclude_domains_and_ipset_restored": True,
        "real_fd9_dvtws2_restarted_twice": True,
        "native_config_other_model_and_ipfw_preserved": True,
        "only_disposable_loopback_services": True,
        "real_wan_ipv6_packets_tested": False,
        "physical_browser_button_click_tested": False,
        "owner_appliance_modified": False,
    }
    print("STAGE5_INSTALLED_EXCLUDE_HTTPS=" + json.dumps(report, sort_keys=True))
    return report


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            execute()
            return 0
        raise Refusal("EXCLUDE_HTTPS_EXPECTED_RUN_OR_SELF_TEST")
    except (Refusal, OSError, ValueError, TypeError, KeyError, ET.ParseError) as exc:
        print("STAGE5_INSTALLED_EXCLUDE_HTTPS=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
