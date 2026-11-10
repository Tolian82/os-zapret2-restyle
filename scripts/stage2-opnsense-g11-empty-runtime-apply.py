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
    need("'The zapret2 service must be installed': 'Требуется установка службы zapret2'" in view,
         "G11_RU_LOCALE_NOT_WIRED")
    need(source.index("WanRequirement::missingBeforeActivation($plan['candidate'])") <
         source.index("SettingsApply::isInertEmptyStrategiesPlan($plan)") <
         source.index("$nativeApplyDispatched = true;"),
         "G11_WAN_FIRST_OR_PRE_DISPATCH_ORDER_CHANGED")
    print("G11_EMPTY_RUNTIME_SOURCE=PASS")


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
    g05 = module("stage2-opnsense-g05-wan-save.py")
    g05.main()
    need(not ENGINE.exists(), "G11_UPSTREAM_ALREADY_INSTALLED")
    xml = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    need(xml is not None and xml.findtext("general/enabled") == "0" and
         xml.findtext("general/waninterface") == "wan" and
         not (xml.findtext("strategy/trafficargs") or "") and
         not (xml.findtext("hostlist/youtubedomains") or ""),
         "G11_NOT_REAL_EMPTY_SAVED_MODEL")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    web = voice.GuestHttps()
    voice.login(web)
    status = web.api("POST", "/api/zapret/service/runtime", {})
    need(status.get("status") == "ok" and status.get("installed") is False and
         status.get("busy") is False and status.get("version") == "",
         "G11_MISSING_RUNTIME_NOT_NATIVELY_ATTESTED")
    node = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(isinstance(node, dict) and isinstance(node.get("hostlist"), dict),
         "G11_EMPTY_STRATEGIES_NOT_READABLE")
    baseline = node["hostlist"].get("telegramips")
    need(isinstance(baseline, str) and baseline == "",
         "G11_EMPTY_TELEGRAM_BASELINE_INVALID")
    before = CONFIG.read_bytes()
    rules = subprocess.run(["/sbin/ipfw", "-q", "list"], capture_output=True,
                           text=True, check=False, timeout=10)
    before_kernel = (rules.returncode, rules.stdout, rules.stderr)
    result = web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", baseline),
    ])
    need(result.get("result") == "failed" and result.get("applied") is False and
         result.get("requires_review") is False and
         result.get("message") == "The zapret2 service must be installed",
         "G11_NATIVE_INERT_NO_ENGINE_WRONG_API_REPLY:" +
         str({k: result.get(k) for k in ("result", "message", "requires_review")})[:300])
    need(CONFIG.read_bytes() == before and not ENGINE.exists(),
         "G11_RUNTIME_DIAGNOSTIC_MUTATED_CONFIG_OR_ENGINE")
    current = subprocess.run(["/sbin/ipfw", "-q", "list"], capture_output=True,
                             text=True, check=False, timeout=10)
    need((current.returncode, current.stdout, current.stderr) == before_kernel,
         "G11_RUNTIME_DIAGNOSTIC_MUTATED_IPFW")
    for pid in ("dvtws2.pid", "zapret2-supervisor-monitor.pid",
                "zapret2-supervisor-daemon.pid"):
        need(not (Path("/var/run") / pid).exists(),
             "G11_RUNTIME_DIAGNOSTIC_STARTED_SERVICE")
    print("G11_EMPTY_RUNTIME_NATIVE=" + json.dumps({
        "status": "PASS_NATIVE_NOOP_UPSTREAM_MISSING_EXACT_MESSAGE",
        "source_sha": head, "original_fd9_apply_not_dispatched": True,
        "engine_missing_verified": True, "wan_unchanged": True,
        "config_unchanged": True, "ipfw_unchanged": True,
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
