#!/usr/bin/env python3
"""G11 LC-06D native HTTPS: no-op empty Strategies + no upstream diagnostic.

Starts only in a disposable OPNsense 26.7 VM. Reuses the already-qualified
G05 same-archive WAN-only test; no native process, IPFW or Config edits here.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def module(name):
    spec = importlib.util.spec_from_file_location(
        "g11_" + name.replace(".", "_").replace("-", "_"), ROOT / name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def self_test():
    view = (ROOT.parent / "src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt").read_text()
    source = (ROOT.parent / "src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php").read_text()
    need("reason === 'runtime-not-installed'" in view and
         "localizeStrategiesApplyError(data.message, data.reason)" in view,
         "G11_RU_LOCALE_NOT_WIRED")
    need(source.index("WanRequirement::missingBeforeActivation($current, $post)") <
         source.index("SettingsApply::isPassiveStrategiesRequest($current, $post)") <
         source.index("SettingsApply::prepareStrategies(") <
         source.index("$nativeApplyDispatched = true;"),
         "G11_WAN_FIRST_OR_PRE_DISPATCH_ORDER_CHANGED")
    print("G11_EMPTY_RUNTIME_SOURCE=PASS")


def _single_apply(web, baseline, label, extra, expected_config):
    before = CONFIG.read_bytes()
    need(before == expected_config, "G11_" + label + "_BASELINE_CONFIG_DRIFT")
    ipfw = subprocess.run(["/sbin/ipfw", "-q", "list"],
                          capture_output=True, text=True, check=False, timeout=10)
    kernel_before = (ipfw.returncode, ipfw.stdout, ipfw.stderr)
    form = [("zapret[sync][telegramips_baseline]", baseline)] + list(extra)
    result = web.api("POST", "/api/zapret/settings/apply", form)
    need(result.get("result") == "failed" and
         result.get("applied") is False and
         result.get("requires_review") is False and
         result.get("message") == "The zapret2 service must be installed" and
         result.get("reason") == "runtime-not-installed",
         "G11_" + label + "_WRONG_NO_ENGINE_MESSAGE:" +
         str({k: result.get(k) for k in ("result", "message", "requires_review")})[:300])
    after = subprocess.run(["/sbin/ipfw", "-q", "list"],
                           capture_output=True, text=True, check=False, timeout=10)
    need(CONFIG.read_bytes() == before and
         (after.returncode, after.stdout, after.stderr) == kernel_before and
         not ENGINE.exists(), "G11_" + label + "_MUTATED_CONFIG_IPFW_OR_ENGINE")
    for pid in ("dvtws2.pid", "zapret2-supervisor-monitor.pid",
                "zapret2-supervisor-daemon.pid"):
        need(not (Path("/var/run") / pid).exists(),
             "G11_" + label + "_SPAWNED_SERVICE")
    return True


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G05_DISPOSABLE_NATIVE") == "1" and
         os.environ.get("ZAPRET2_G11_EMPTY_RUNTIME_NATIVE") == "1" and
         os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
         Path("/usr/local/opnsense").is_dir(),
         "G11_REQUIRES_DISPOSABLE_OPNSENSE")
    head = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    import re
    need(re.fullmatch(r"[a-f0-9]{40}", head) is not None, "G11_EXACT_HEAD_MISSING")
    # Real first native package installation MUST have approved YouTube defaults.
    # Do NOT call G05.main(): that deliberately erases these before reporting
    # WAN-only PASS and previously hid the owner's actual initial-Apply bug.
    g04 = module("stage2-opnsense-g04-native-config.py")
    g04.verify_native_pkg_and_first_config()
    need(not ENGINE.exists(), "G11_UPSTREAM_ALREADY_INSTALLED")
    first = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    need(first is not None, "G11_FIRST_CONFIG_MISSING")
    strategy = first.findtext("strategy/trafficargs") or ""
    domains = first.findtext("hostlist/youtubedomains") or ""
    need("--filter-tcp=80,443" in strategy and
         "--filter-udp=443" in strategy and
         domains.splitlines() == [
             "youtube.com", "googlevideo.com", "yt.be", "youtu.be", "ytimg.com",
             "youtubei.googleapis.com", "youtube.googleapis.com",
             "youtube-nocookie.com", "ggpht.com", "ssl.gstatic.com"],
         "G11_FIRST_INSTALL_DEFAULTS_NOT_ACTUALLY_PRESENT")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    web = voice.GuestHttps()
    voice.login(web)
    g05 = module("stage2-opnsense-g05-wan-save.py")
    previous_wan, baseline = g05.gui_wan(web)
    need(not previous_wan, "G11_FIRST_WAN_NOT_EMPTY")
    # WAN-first MUST win over missing-engine before a valid WAN is saved.
    before_wan = CONFIG.read_bytes()
    blocked = web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", baseline),
        ("zapret[general][enabled]", "1")])
    need(blocked.get("result") == "failed" and
         "Select a WAN interface" in str(blocked.get("message", "")) and
         CONFIG.read_bytes() == before_wan,
         "G11_ACTIVATION_DID_NOT_PRESERVE_WAN_FIRST")
    # Actual WAN-only Apply with the preseeded first-install strategy still
    # works without upstream; the persisted default profile must stay intact.
    saved = g05.request(web, "wan", baseline)
    need(saved.get("result") == "saved" and saved.get("applied") is False,
         "G11_DEFAULTS_BLOCKED_FIRST_WAN_ONLY_SAVE")
    seeded = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    need(seeded is not None and
         seeded.findtext("general/waninterface") == "wan" and
         seeded.findtext("strategy/trafficargs") == strategy and
         seeded.findtext("hostlist/youtubedomains") == domains,
         "G11_WAN_ONLY_MODIFIED_APPROVED_SEED")
    installed = web.api("POST", "/api/zapret/service/runtime", {})
    need(installed.get("status") == "ok" and
         installed.get("installed") is False and
         installed.get("busy") is False,
         "G11_REAL_MISSING_RUNTIME_NOT_CONFIRMED")
    baseline = web.api("GET", "/api/zapret/settings/get")["zapret"]["hostlist"]["telegramips"]
    need(isinstance(baseline, str), "G11_NATIVE_BASELINE_NOT_STRING")
    snapshot = CONFIG.read_bytes()

    # Three owner-relevant cases, not a synthetic empty-only POST:
    # (a) native first defaults, (b) user clearing unsaved preseeded fields,
    # (c) actual user-empty saved Config, all with verified missing upstream.
    _single_apply(web, baseline, "SEEDED_NOOP", [], snapshot)
    _single_apply(web, baseline, "SEEDED_FULL_FORM", [
        ("zapret[general][enabled]", "0"),
        ("zapret[general][waninterface]", "wan"),
        ("zapret[strategy][trafficargs]", strategy),
        ("zapret[hostlist][youtubedomains]", domains)], snapshot)
    _single_apply(web, baseline, "UNSAVED_CLEAR", [
        ("zapret[strategy][trafficargs]", ""),
        ("zapret[hostlist][youtubedomains]", "")], snapshot)

    g04.clear_as_user_save()
    saved_empty = CONFIG.read_bytes()
    empty = ET.fromstring(saved_empty).find("./OPNsense/Zapret")
    need(empty is not None and
         (empty.findtext("strategy/trafficargs") or "") == "" and
         (empty.findtext("hostlist/youtubedomains") or "") == "",
         "G11_SAVED_EMPTY_NOT_ACTUAL_CONFIG")
    _single_apply(web, baseline, "PERSISTED_EMPTY", [], saved_empty)

    print("G11_EMPTY_RUNTIME_NATIVE=" + json.dumps({
        "status": "PASS_REAL_SEEDED_AND_CLEARED_MISSING_UPSTREAM_APPLY",
        "source_sha": head, "wan_only_saved_with_defaults": True,
        "preseeded_traffic_and_youtube_verified": True,
        "seeded_noop": True, "seeded_full_form": True,
        "unsaved_clear": True, "persisted_user_empty": True,
        "original_fd9_apply_not_dispatched": True,
        "config_and_ipfw_unchanged_for_failed_apply": True,
        "owner_browser_ru_locale_not_tested": True,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:] == ["run"]:
            main()
        else:
            raise Refusal("G11_EXPECTS_SELF_TEST_OR_RUN")
    except (Refusal, OSError, ValueError, TypeError, KeyError, ET.ParseError,
            subprocess.TimeoutExpired) as error:
        print("G11_EMPTY_RUNTIME_NATIVE=REFUSED:" + str(error), file=sys.stderr)
        raise SystemExit(2)
