#!/usr/bin/env python3
"""G04 A06: native TCP+QUIC profile, installed dvtws2 and scoped lo0 Start/Stop.

Runs ONLY on a disposable OPNsense 26.7 guest AFTER the dedicated G04
first-package proof and BEFORE the same-archive saved-empty reinstall proof.
No owner appliance, release publication, foreign IPFW change or WAN traffic.
"""
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

HERE = Path(__file__).resolve().parent
ENGINE_ROOT = Path("/usr/local/etc/zapret2")
ENGINE = ENGINE_ROOT / "binaries/my/dvtws2"
ACTIVE = ENGINE_ROOT / "runtime-v2"
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
CONFIG = Path("/conf/config.xml")
PID = Path("/var/run/dvtws2.pid")
CONFIGCTL = "/usr/local/sbin/configctl"
OWNED = re.compile(r"^190(?:0[0-9]|10)\s")
YOUTUBE = [
    "youtube.com", "googlevideo.com", "yt.be", "youtu.be", "ytimg.com",
    "youtubei.googleapis.com", "youtube.googleapis.com", "youtube-nocookie.com",
    "ggpht.com", "ssl.gstatic.com"
]


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def call(args, timeout=90):
    return subprocess.run(args, check=False, capture_output=True,
                          text=True, timeout=timeout)


def required(args, code, timeout=90):
    p = call(args, timeout)
    need(p.returncode == 0, code + ":rc=" + str(p.returncode) +
         ":" + (p.stdout + p.stderr)[-350:])
    return p


def model():
    root = ET.fromstring(CONFIG.read_bytes())
    z = root.find("./OPNsense/Zapret")
    need(z is not None, "G04_PERSISTED_ZAPRET_MISSING")
    return z


def foreign_rules():
    p = call(["/sbin/ipfw", "-q", "list"], timeout=15)
    if p.returncode:
        return None
    return [x for x in p.stdout.splitlines() if not OWNED.match(x)]


def owned_rules():
    result = required(["/sbin/ipfw", "-q", "list"],
                      "G04_NATIVE_IPFW_RULES_UNREADABLE", timeout=20)
    return [x for x in result.stdout.splitlines() if OWNED.match(x)]


def set_test_only_enabled(enabled):
    """The normal native model save, exactly like an operator changing GUI fields."""
    script = r'''require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
    $m = new \OPNsense\Zapret\Zapret();
    if ($m->setNodeByReference("general.enabled", "__ENABLED__") !== true ||
        $m->setNodeByReference("general.waninterface", "__WAN__") !== true ||
        count($m->performValidation(false)) !== 0 ||
        !$m->serializeToConfig(false, true)) {
        throw new \RuntimeException("native test model rejected input");
    }
    $c->save(["description"=>"G04 disposable lo0 protocol acceptance"]);
} finally {
    $c->unlock();
}'''
    script = script.replace("__ENABLED__", "1" if enabled else "0")
    script = script.replace("__WAN__", "lo0" if enabled else "")
    required(["/usr/local/bin/php", "-r", script], "G04_GUI_MODEL_TEST_SAVE_FAILED")
    root = model()
    need(root.findtext("general/enabled") == ("1" if enabled else "0") and
         (root.findtext("general/waninterface") or "") ==
         ("lo0" if enabled else ""), "G04_TEST_GUI_MODEL_SAVE_NOT_PERSISTED")


def setup_upstream():
    spec = importlib.util.spec_from_file_location(
        "g04_existing_g03", HERE / "stage2-opnsense-g03-first-install.py")
    g03 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g03)
    need(not ENGINE.exists(), "G04_ENGINE_ALREADY_PRESENT_IN_FRESH_GUEST")
    result = g03.dispatch_and_poll()
    need(result["installed"] == "1" and result["service"] == "stopped" and
         result["version"] == "v1.0.7", "G04_G03_NATIVE_SETUP_NOT_STOPPED_READY")
    need(ENGINE.is_file() and not ENGINE.is_symlink() and
         os.access(ENGINE, os.X_OK), "G04_REAL_DVTWS2_BINARY_NOT_COMPILED")
    blob = ENGINE_ROOT / "files/fake/http_iana_org.bin"
    need(blob.is_file() and not blob.is_symlink() and
         blob.stat().st_size > 0, "G04_STOCK_HTTP_IANA_BLOB_MISSING")
    return hashlib.sha256(ENGINE.read_bytes()).hexdigest()


def g04_http_form(saved, *, stale=False):
    """Use the form's actual posted namespace, not direct Config/model writes."""
    need(isinstance(saved, dict), "G04_HTTPS_NATIVE_MODEL_MISSING")
    hostlist = saved.get("hostlist")
    strategy = saved.get("strategy")
    need(isinstance(hostlist, dict) and isinstance(strategy, dict),
         "G04_HTTPS_NATIVE_MODEL_SHAPE_INVALID")
    baseline = hostlist.get("telegramips")
    need(isinstance(baseline, str), "G04_HTTPS_BASELINE_NOT_SCALAR")
    return [
        ("zapret[sync][telegramips_baseline]",
         "__g04_intentionally_stale_baseline__" if stale else baseline),
        ("zapret[general][enabled]", "1"),
        ("zapret[general][waninterface]", "lo0"),
    ]


def authenticated_first_apply(traffic, domains):
    """Installed HTTPS cookie + CSRF; normal GUI page and Strategies API."""
    spec = importlib.util.spec_from_file_location(
        "g04_existing_authenticated_https",
        HERE / "stage2-opnsense-real-native-voice-http.py")
    voice = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(voice)
    web = voice.GuestHttps()
    voice.login(web)
    page = web.request("GET", "/ui/zapret")
    need('frm_GeneralSettings' in page and 'reconfigureAct' in page and
         '/api/zapret/settings/apply' in page,
         "G04_INSTALLED_GENERAL_APPLY_PAGE_UNAVAILABLE")
    result = web.api("GET", "/api/zapret/settings/get")
    saved = result.get("zapret")
    need(isinstance(saved, dict) and
         isinstance(saved.get("strategy"), dict) and
         isinstance(saved.get("hostlist"), dict) and
         saved["strategy"].get("trafficargs") == traffic and
         saved["hostlist"].get("youtubedomains") == domains,
         "G04_HTTPS_FRESH_MODEL_DID_NOT_RENDER_SAVED_DEFAULTS")

    before_config = CONFIG.read_bytes()
    negative = web.api(
        "POST", "/api/zapret/settings/apply",
        g04_http_form(saved, stale=True))
    need(negative.get("result") == "failed" and
         negative.get("requires_review") is not True,
         "G04_HTTPS_STALE_BASELINE_NOT_SAFELY_REJECTED")
    need(CONFIG.read_bytes() == before_config and
         not PID.exists() and not PID.is_symlink(),
         "G04_HTTPS_STALE_APPLY_MUTATED_CONFIG_OR_ENGINE")

    applied = web.api(
        "POST", "/api/zapret/settings/apply",
        g04_http_form(saved))
    need(applied.get("result") == "saved" and applied.get("status") == "ok",
         "G04_HTTPS_FIRST_STRATEGIES_APPLY_NOT_COMMITTED:" +
         str(applied.get("message", "no-receipt"))[:190])
    after = model()
    need(after.findtext("general/enabled") == "1" and
         after.findtext("general/waninterface") == "lo0" and
         after.findtext("strategy/trafficargs") == traffic and
         after.findtext("hostlist/youtubedomains") == domains,
         "G04_HTTPS_COMMITTED_CONFIG_OR_INITIAL_PROFILE_CHANGED")
    loaded = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(isinstance(loaded, dict) and
         loaded.get("strategy", {}).get("trafficargs") == traffic and
         loaded.get("hostlist", {}).get("youtubedomains") == domains,
         "G04_HTTPS_FRESH_GET_DID_NOT_READ_PERSISTED_APPLY")
    return {"authenticated": True, "csrf": True, "negative_no_write": True,
            "positive_native_apply": True, "fresh_gui_get": True}


def self_test():
    sample = {"hostlist": {"telegramips": "", "youtubedomains": "youtube.com"},
              "strategy": {"trafficargs": "--filter-tcp=80,443"}}
    correct = dict(g04_http_form(sample))
    stale = dict(g04_http_form(sample, stale=True))
    assert correct == {
        "zapret[sync][telegramips_baseline]": "",
        "zapret[general][enabled]": "1",
        "zapret[general][waninterface]": "lo0",
    }
    assert stale["zapret[sync][telegramips_baseline]"] != ""
    for malformed in ({}, {"hostlist": {}, "strategy": {}},
                      {"hostlist": {"telegramips": []}, "strategy": {}}):
        try:
            g04_http_form(malformed)
        except Refusal:
            pass
        else:
            raise AssertionError("G04 accepted malformed baseline")
    print("PASS: G04 exact GUI Apply form, stale baseline and malformed source contracts")


def check_compiled_argv():
    args = ACTIVE / "dvtws.args"
    need(args.is_file() and not args.is_symlink(),
         "G04_PRODUCTION_DVTWS_ARGUMENTS_MISSING")
    tokens = args.read_text().split()
    need(tokens.count("--new") == 1, "G04_NATIVE_PROFILE_SEPARATOR_NOT_ONE")
    need("--filter-tcp=80,443" in tokens and "--filter-udp=443" in tokens,
         "G04_NATIVE_TCP_UDP_FILTERS_DIFFERENT")
    need(any(t.startswith("--blob=http_iana_org:@") and
             t.endswith("/files/fake/http_iana_org.bin") for t in tokens),
         "G04_NATIVE_BLOB_SHORTHAND_UNRESOLVED")
    need("--lua-desync=fake:blob=fake_default_quic:repeats=5" in tokens,
         "G04_NATIVE_BUILTIN_QUIC_FAKE_MISSING")
    hosts = [t for t in tokens if t.startswith("--hostlist=")]
    need(len(hosts) == 2 and all("<HOSTLIST" not in t for t in tokens),
         "G04_NATIVE_HOSTLIST_PLACEHOLDER_UNRESOLVED")
    for item in hosts:
        path = Path(item.split("=", 1)[1])
        need(path.is_file() and not path.is_symlink() and
             path.read_text().splitlines() == YOUTUBE,
             "G04_NATIVE_YOUTUBE_FILE_NOT_EXACT_TEN")
    # Real native binary/argv validation; no packet capture or network request.
    required([str(ENGINE), *tokens, "--dry-run"],
             "G04_NATIVE_REAL_ENGINE_DRYRUN_REFUSED", timeout=35)
    return {"tcp_ports": "80,443", "udp_ports": "443",
            "profile_count": 2, "youtube_hosts": 10,
            "built_in_quic_fake": True, "real_dryrun": True}


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G04_DISPOSABLE_NATIVE") == "1" and
         os.environ.get("ZAPRET2_G04_RUNTIME_NATIVE") == "1",
         "G04_DISPOSABLE_RUNTIME_OPTIN_REQUIRED")
    need(os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
         Path("/usr/local/opnsense").is_dir() and CONFIG.is_file(),
         "G04_RUNTIME_NOT_A_NATIVE_DISPOSABLE_GUEST")
    initial = model()
    traffic = initial.findtext("strategy/trafficargs") or ""
    domains = initial.findtext("hostlist/youtubedomains") or ""
    need(traffic.count("--new") == 1 and domains.splitlines() == YOUTUBE and
         initial.findtext("general/enabled") == "0" and
         not (initial.findtext("general/waninterface") or ""),
         "G04_FIRST_SAVED_CONFIG_NOT_EXACT_INITIAL_PROFILE")
    initial_traffic_sha = hashlib.sha256(traffic.encode()).hexdigest()
    initial_config_sha = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    engine_sha = setup_upstream()
    need(hashlib.sha256(CONFIG.read_bytes()).hexdigest() == initial_config_sha,
         "G04_UPSTREAM_SETUP_CHANGED_SAVED_CONFIG")
    before_foreign = foreign_rules()
    started = False
    profile = None
    stop_error = None
    try:
        # Unlike the previous G04 proof (direct native model + configctl
        # Start), this is the actual installed page's authenticated/CSRF
        # Strategies Apply from a first-runtime STOPPED state. It invokes the
        # established common FD9 owner and is not a simulated GUI success.
        http_evidence = authenticated_first_apply(traffic, domains)
        started = True
        updated = model()
        need(hashlib.sha256((updated.findtext("strategy/trafficargs") or "").encode()).hexdigest()
             == initial_traffic_sha and
             (updated.findtext("hostlist/youtubedomains") or "") == domains,
             "G04_HTTPS_ENABLING_LO0_CHANGED_INITIAL_PROFILE")
        saved_after_test_enable = CONFIG.read_bytes()
        for _ in range(12):
            live = call([str(SERVICE), "status"], timeout=20)
            if live.returncode == 0 and "zapret is running" in live.stdout:
                break
            time.sleep(1)
        else:
            raise Refusal("G04_NATIVE_SERVICE_DID_NOT_REACH_RUNNING")
        need(PID.is_file() and not PID.is_symlink() and PID.read_text().strip().isdigit(),
             "G04_NATIVE_DVTWS2_PID_UNTRUSTED")
        process = required(["/bin/ps", "-p", PID.read_text().strip(),
                            "-o", "command="], "G04_NATIVE_DVTWS2_NOT_IN_PS")
        need(process.stdout.strip().split(" ")[0] == str(ENGINE) and
             hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_sha,
             "G04_RUNNING_DVTWS2_NOT_THE_REAL_COMPILED_ENGINE")
        rules = owned_rules()
        need(len(rules) == 2 and
             any(x.startswith("19000 ") and " tcp " in x and "80" in x and
                 "443" in x and "lo0" in x and "divert 989" in x for x in rules) and
             any(x.startswith("19001 ") and " udp " in x and "443" in x and
                 "lo0" in x and "divert 989" in x for x in rules),
             "G04_NATIVE_TCP_AND_QUIC_IPFW_RULES_NOT_SCOPED_LO0")
        after_foreign = foreign_rules()
        need(after_foreign is not None,
             "G04_NATIVE_FOREIGN_IPFW_INVENTORY_UNAVAILABLE")
        if before_foreign is not None:
            need(after_foreign == before_foreign,
                 "G04_NATIVE_CHANGED_FOREIGN_IPFW_RULES")
        else:
            # Cold ipfw was not yet loaded. The plugin may load it with
            # default-to-accept, but cannot introduce third-party rules.
            need(all(x.startswith("65535 ") for x in after_foreign),
                 "G04_COLD_IPFW_LOAD_CREATED_UNEXPECTED_FOREIGN_RULE")
        profile = check_compiled_argv()
        need(CONFIG.read_bytes() == saved_after_test_enable,
             "G04_NATIVE_START_DRYRUN_MODIFIED_SAVED_CONFIG")
    finally:
        # Even a failed test must not leave a disposable engine and divert
        # rules running when it can be stopped by the original native service.
        stop = call([CONFIGCTL, "zapret", "stop"], timeout=90)
        if stop.returncode:
            stop_error = "G04_NATIVE_CONFIGCTL_STOP_FAILED"
        elif owned_rules():
            stop_error = "G04_NATIVE_STOP_LEFT_OWNED_IPFW"
        if before_foreign is not None and foreign_rules() != before_foreign:
            stop_error = "G04_NATIVE_STOP_CHANGED_FOREIGN_IPFW"
        if started or model().findtext("general/enabled") == "1":
            set_test_only_enabled(False)
            required([CONFIGCTL, "template", "reload", "OPNsense/Zapret"],
                     "G04_DISABLED_TEMPLATE_RENDER_FAILED")
        need(stop_error is None, stop_error or "")
    cleared = model()
    need(cleared.findtext("general/enabled") == "0" and
         not (cleared.findtext("general/waninterface") or "") and
         cleared.findtext("strategy/trafficargs") == traffic and
         cleared.findtext("hostlist/youtubedomains") == domains,
         "G04_PROTOCOL_TEST_DID_NOT_RESTORE_INITIAL_PREFERENCES")
    need(profile is not None, "G04_NATIVE_PROTOCOL_PROOF_MISSING")
    print("G04_NATIVE_RUNTIME=" + json.dumps({
        "status": "PASS_G04_REAL_TCP_QUIC_DVTWS_DRYRUN_AND_LO0_START_STOP",
        "release": "v1.0.7", **profile,
        "real_authenticated_https_strategies_apply": http_evidence,
        "actual_native_configctl_start_stop": True,
        "only_owned_lo0_ipfw_rules": True,
        "owner_browser_tested": False, "real_wan_network_bypass_tested": False
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
            sys.exit(0)
        main()
    except (Refusal, OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print("G04_NATIVE_RUNTIME=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(1)
