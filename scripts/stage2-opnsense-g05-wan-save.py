#!/usr/bin/env python3
"""G05 LC-06: authenticated WAN-only Apply in one genuine disposable OPNsense VM.

No simulated configd, no runtime install requirement for the first WAN save.
Uses same physical qualified package; never targets the owner's firewall.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONF = Path("/conf/config.xml")
PKGNAME = "os-zapret2-restyle"


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(path, tag):
    spec = importlib.util.spec_from_file_location(tag, ROOT / "scripts" / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(argv, timeout=180):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=timeout, check=False)


def node():
    root = ET.fromstring(CONF.read_bytes())
    n = root.find("./OPNsense/Zapret")
    need(n is not None, "G05_NATIVE_ZAPRET_SUBTREE_ABSENT")
    return n


def exact_saved_wan(value):
    n = node()
    need(n.findtext("general/waninterface", "") == value,
         "G05_NATIVE_CONFIG_WAN_NOT_PERSISTED")
    need(n.findtext("general/enabled", "0") == "0",
         "G05_NATIVE_WAN_CHANGE_UNEXPECTEDLY_ENABLED_SERVICE")


def selected(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        selected_items = [key for key, option in value.items()
                          if isinstance(option, dict) and
                          str(option.get("selected")) in ("1", "True")]
        return selected_items[0] if len(selected_items) == 1 else None
    return None


def no_runtime_mutation(before_engine, before_ipfw, before_config=None):
    if before_config is not None:
        need(CONF.read_bytes() == before_config,
             "G05_FAILED_WAN_APPLY_MUTATED_CONFIG")
    engine = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    need(engine.exists() == before_engine,
         "G05_WAN_ONLY_INSTALLED_OR_DELETED_UPSTREAM_ENGINE")
    for name in ("dvtws2.pid", "zapret2-supervisor-monitor.pid",
                 "zapret2-supervisor-daemon.pid"):
        need(not (Path("/var/run") / name).exists(),
             "G05_WAN_ONLY_CREATED_ENGINE_PROCESS")
    ipfw = run(["/sbin/ipfw", "-q", "list"], timeout=10)
    # Kernel may be unloaded in a genuinely fresh guest. The exact raw
    # before/after rc/output pair must remain unchanged in WAN-only Apply.
    now = (ipfw.returncode, ipfw.stdout, ipfw.stderr)
    need(now == before_ipfw, "G05_WAN_ONLY_MODIFIED_IPFW_OR_LOADED_KERNEL")


def request(web, wan, baseline):
    return web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", baseline),
        ("zapret[general][waninterface]", wan),
    ])


def gui_wan(web):
    model = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(isinstance(model, dict), "G05_WAN_GUI_MODEL_NOT_READABLE")
    general = model.get("general")
    hostlist = model.get("hostlist")
    need(isinstance(general, dict) and isinstance(hostlist, dict),
         "G05_WAN_GUI_MODEL_INCOMPLETE")
    baseline = hostlist.get("telegramips")
    need(isinstance(baseline, str), "G05_WAN_TELEGRAM_BASELINE_MISSING")
    return selected(general.get("waninterface")), baseline



def _wan_first_jobs():
    """Only real Lab jobs/sessions count; launcher lockfiles are not jobs."""
    roots = (Path("/var/run/zapret2-restyle/strategy-lab/jobs"),
             Path("/var/run/zapret2-restyle/strategy-lab/circular/sessions"))
    return tuple(sorted(str(p) for root in roots if root.is_dir()
                        for p in root.glob("job.*")))


def _wan_first_unchanged(config_bytes, ipfw_baseline, jobs, label):
    no_runtime_mutation(False, ipfw_baseline, config_bytes)
    need(_wan_first_jobs() == jobs,
         "G05_WAN_FIRST_CREATED_LAB_JOB_" + label)


def _wan_first_command(argv, code, fragment, name):
    status = run(argv, timeout=50)
    need(status.returncode == code and
         fragment in (status.stdout + status.stderr),
         "G05_WAN_FIRST_" + name + "_WRONG_REFUSAL")
    return status


def _wan_first_lab_form(mode, language):
    # Deliberately invalid target: WAN / engine must win over target grammar.
    return [("target", "invalid_target"), ("mode", mode),
            ("language", language), ("enable_quic", "0"),
            ("ipv6_enabled", "0")]


def _wan_first_cold_matrix(web, baseline, ipfw_baseline):
    """Actual cookie/CSRF and installed configd/Voice/Lab before first WAN Save."""
    saved = CONF.read_bytes()
    jobs = _wan_first_jobs()
    script = "/usr/local/opnsense/scripts/OPNsense/Zapret/"
    _wan_first_command([script + "wan_preflight.sh", "require"],
                       0, "wan-required", "SAVED_PROBE")
    _wan_first_command(["/usr/local/sbin/configctl", "zapret", "wan_preflight"],
                       0, "wan-required", "CONFIGD_PROBE")
    _wan_first_command([script + "zapret_service.sh", "start"],
                       64, "WAN_REQUIRED", "DIRECT_START")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "START")

    missing = web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", baseline),
        ("zapret[general][enabled]", "1"),
        ("zapret[strategy][trafficargs]", "--not-a-valid-strategy")])
    need(missing.get("result") == "failed" and
         missing.get("applied") is not True and
         missing.get("requires_review") is not True and
         "Select a WAN interface" in str(missing.get("message", "")),
         "G05_WAN_FIRST_GUI_STRATEGIES_MASKED_MISSING_WAN")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "STRATEGIES")

    voice = web.api("GET", "/api/zapret/voice/load")
    model, snapshot = voice.get("zapret"), voice.get("snapshot")
    need(isinstance(model, dict) and isinstance(snapshot, str) and
         len(snapshot) == 64 and
         all(c in "0123456789abcdef" for c in snapshot),
         "G05_WAN_FIRST_NATIVE_VOICE_LOAD_MISSING")
    form = [("zapret[sync][snapshot]", snapshot)]
    for name in ("telegram", "discord", "x", "sip", "custom"):
        item = model["voice"][name]
        need(str(item["enabled"]) == "0",
             "G05_WAN_FIRST_NOT_COLD_VOICE_OFF")
        form.extend([
            ("zapret[voice][" + name + "][enabled]",
             "1" if name == "telegram" else "0"),
            ("zapret[voice][" + name + "][args]", str(item["args"])),
            ("zapret[hostlist][" + name + "ips]",
             str(model["hostlist"][name + "ips"]))])
    voice_rejected = web.api("POST", "/api/zapret/voice/apply", form)
    need(voice_rejected.get("result") == "failed" and
         voice_rejected.get("requires_review") is not True and
         "Select a WAN interface" in str(
             voice_rejected.get("validations", {}).get(
                 "zapret.voice.waninterface", "")),
         "G05_WAN_FIRST_GUI_VOICE_MASKED_MISSING_WAN")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "VOICE")

    for mode, language, expected in (
        ("standard", "ru", "Укажите WAN интерфейс"),
        ("extended", "en", "Select a WAN interface"),
    ):
        refused = web.api("POST", "/api/zapret/strategy_lab/start",
                          _wan_first_lab_form(mode, language))
        need(refused.get("status") == "error" and
             refused.get("reason") == "wan-required" and
             refused.get("message") == expected,
             "G05_WAN_FIRST_GUI_LAB_" + mode.upper())
        _wan_first_unchanged(saved, ipfw_baseline, jobs, "LAB_" + mode.upper())

    # Original launchers and configd, not a synthetic WAN resolver.
    _wan_first_command([
        "/usr/local/sbin/configctl", "zapret", "strategy_lab_start",
        "invalid_target", "standard", "ru", "0", "-", "-", "-", "0"],
        64, "Укажите WAN интерфейс", "CONFIGD_LAB")
    _wan_first_command([
        script + "strategy_lab_circular_launcher.sh",
        "start", "job.G05WithoutWAN"],
        64, "Select a WAN interface", "CIRCULAR_LAB")
    _wan_first_command([script + "zapret_service.sh", "telegram-voice-enable"],
                       64, "WAN_REQUIRED", "DIRECT_VOICE_ON")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "INTERNAL")
    return True


def _wan_first_saved_no_engine_matrix(web, ipfw_baseline):
    """WAN now saved; engine is the second prerequisite, before Job/target."""
    saved = CONF.read_bytes()
    jobs = _wan_first_jobs()
    script = "/usr/local/opnsense/scripts/OPNsense/Zapret/"
    _wan_first_command([script + "wan_preflight.sh", "require"],
                       0, "wan-ready", "SAVED_WAN_READY")
    _wan_first_command([script + "zapret_service.sh", "start"],
                       1, "runtime is not installed", "ENGINE_SECOND")
    for mode, language, expected in (
        ("standard", "ru", "Служба zapret2 не установлена"),
        ("extended", "en", "The zapret2 service is not installed"),
    ):
        refused = web.api("POST", "/api/zapret/strategy_lab/start",
                          _wan_first_lab_form(mode, language))
        need(refused.get("status") == "error" and
             refused.get("reason") == "engine-not-installed" and
             refused.get("message") == expected,
             "G05_WAN_FIRST_NO_ENGINE_BEFORE_LAB_" + mode.upper())
    _wan_first_command([
        script + "strategy_lab_launcher.sh", "start", "invalid_target",
        "standard", "en", "0", "-", "-", "-", "0"],
        64, "The zapret2 service is not installed", "DIRECT_LAB_ENGINE")
    _wan_first_command([
        script + "strategy_lab_circular_launcher.sh",
        "start", "job.G05NoEngine"],
        64, "The zapret2 service is not installed", "CIRCULAR_NO_ENGINE")
    _wan_first_unchanged(saved, ipfw_baseline, jobs, "ENGINE_PRE_JOB")
    return True


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G05_DISPOSABLE_NATIVE") == "1" and
         os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
         Path("/usr/local/opnsense").is_dir(),
         "G05_GENUINE_DISPOSABLE_ROOT_GUEST_REQUIRED")
    g04 = load("stage2-opnsense-g04-native-config.py", "g05_g04_builder")
    sha = g04.verify_native_pkg_and_first_config()
    package = g04.PACKAGE
    need(hashlib.sha256(package.read_bytes()).hexdigest() == sha,
         "G05_NATIVE_INITIAL_ARCHIVE_SHA_CHANGED")
    engine = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    need(not engine.exists(), "G05_NOT_A_COLD_UPSTREAM_GUEST")
    ipfw = run(["/sbin/ipfw", "-q", "list"], timeout=10)
    ipfw_before = (ipfw.returncode, ipfw.stdout, ipfw.stderr)
    core = load("stage2-opnsense-real-native-voice-http.py", "g05_https")
    web = core.GuestHttps()
    core.login(web)
    page = web.request("GET", "/ui/zapret")
    need("frm_GeneralSettings" in page and
         "/api/zapret/settings/apply" in page,
         "G05_NATIVE_AUTHENTICATED_GUI_APPLY_MISSING")
    old, baseline = gui_wan(web)
    need(old in ("", None), "G05_FIRST_WAN_NOT_EMPTY")

    # Existing no-engine native guest: WAN-first GUI/configd/Voice/Lab matrix.
    _wan_first_cold_matrix(web, baseline, ipfw_before)

    # Stale tab + unknown logical interface must refuse with no mutation.
    initial = CONF.read_bytes()
    stale = request(web, "lo0", "__g05_stale_telegram__")
    need(stale.get("result") == "failed" and
         stale.get("requires_review") is not True,
         "G05_STALE_TAB_DID_NOT_FAIL_BEFORE_CONFIG")
    no_runtime_mutation(False, ipfw_before, initial)
    invalid = request(web, "unassigned0", baseline)
    need(invalid.get("result") == "failed" and
         invalid.get("requires_review") is not True,
         "G05_UNASSIGNED_WAN_NOT_REJECTED")
    no_runtime_mutation(False, ipfw_before, initial)

    # Actual first GUI/API Save with NO upstream engine and original FD9.
    result = request(web, "lo0", baseline)
    need(result.get("result") == "saved" and
         result.get("status") == "ok" and
         result.get("applied") is False,
         "G05_COLD_FIRST_WAN_CONFIG_ONLY_APPLY_FAILED:" +
         str(result.get("message", "no-message"))[:150])
    exact_saved_wan("lo0")
    no_runtime_mutation(False, ipfw_before)
    reread, baseline = gui_wan(web)
    need(reread == "lo0", "G05_WAN_NOT_VISIBLE_AFTER_FRESH_GET")

    _wan_first_saved_no_engine_matrix(web, ipfw_before)

    # Manual emptying of previously populated strategy/domains MUST NOT
    # obstruct the next WAN-only Save, trigger backend compilation, or
    # recreate either empty user field.
    g04.clear_as_user_save()
    saved_empty = node()
    need((saved_empty.findtext("strategy/trafficargs") or "") == "" and
         (saved_empty.findtext("hostlist/youtubedomains") or "") == "",
         "G05_EMPTY_SAVED_FIELDS_NOT_PRESERVED")
    result = request(web, "wan", baseline)
    need(result.get("result") == "saved" and
         result.get("applied") is False,
         "G05_EMPTY_STRATEGY_WAN_ONLY_SAVE_FAILED")
    exact_saved_wan("wan")
    no_runtime_mutation(False, ipfw_before)
    after, _ = gui_wan(web)
    need(after == "wan", "G05_SECOND_WAN_NOT_VISIBLE_AFTER_F5_GET")
    need((node().findtext("strategy/trafficargs") or "") == "" and
         (node().findtext("hostlist/youtubedomains") or "") == "",
         "G05_WAN_SAVE_BACKFILLED_EXPLICIT_EMPTY_FIELDS")

    # Same archive reinstall may update pkgdb/firmware metadata, but must
    # never change the saved Zapret WAN or regenerate the erased fields.
    previous = ET.tostring(node(), encoding="utf-8")
    again = run(["pkg", "-o", "REPO_AUTOUPDATE=false", "add", "-f",
                 str(package)], timeout=240)
    need(again.returncode == 0 and "zapret-config=preserved" in again.stdout,
         "G05_NATIVE_SAME_ARCHIVE_REINSTALL_FAILED")
    need(hashlib.sha256(package.read_bytes()).hexdigest() == sha and
         ET.tostring(node(), encoding="utf-8") == previous,
         "G05_REINSTALL_MODIFIED_USER_WAN_OR_EMPTY_FIELDS")
    print("G05_NATIVE=" + json.dumps({
        "status": "PASS_G05_COLD_NO_ENGINE_WAN_ONLY_HTTPS_CONFIG_AND_REINSTALL",
        "first_api_authenticated": True,
        "first_save_without_upstream_engine": True,
        "wan_first_gui_configd_voice_lab_ru_en": True,
        "wan_first_engine_second_before_job": True,
        "empty_strategy_and_domains_preserved": True,
        "wan_get_after_f5": True,
        "no_dvtws_or_ipfw_mutation": True,
        "same_archive_sha256": sha,
        "owner_browser_tested": False,
        "running_wan_rollback_tested": False,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as e:
        print("G05_NATIVE=REFUSED:" + str(e), file=sys.stderr)
        sys.exit(1)
