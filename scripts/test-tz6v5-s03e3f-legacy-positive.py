#!/usr/bin/env python3
"""S03e3f: real Legacy RUNNING HTTP Start/Restart/Stop on disposable OPNsense.

No Common Apply or shared owner journal: the first enabled/WAN choice is saved
through stock OPNsense Config::save as in G04, on the strictly qualified fresh
CI guest only. The installed original-FD9 legacy dispatcher must physically
transition a genuine pinned dvtws2 v1.0.7 and return signed-by-state PHP
terminal receipts. There is no mock daemon, fake API or new product writer.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import urllib.error
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
PID = Path("/var/run/dvtws2.pid")
MONITOR = Path("/var/run/zapret2-supervisor-monitor.pid")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
PKG_RECORD = Path("/var/db/zapret2/pkg-update/operation.json")
CONFIG = Path("/conf/config.xml")
OWNED = re.compile(r"^190[0-9]{2}\s")
EXPECTED = ("--filter-tcp=80,443", "--filter-udp=443")


class Refusal(RuntimeError):
    pass


def need(ok, code):
    if not ok:
        raise Refusal(code)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "s03e3f_" + filename.replace("-", "_").replace(".", "_"), HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def run(*args, timeout=75):
    return subprocess.run([str(x) for x in args], capture_output=True,
                          text=True, check=False, timeout=timeout)


def exact_source():
    expected = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(re.fullmatch("[0-9a-f]{40}", expected) is not None,
         "S03E3F_CI_EXACT_SHA_MISSING")
    # Host Git HEAD is sealed against every tracked source byte before tar.
    # Guest Git metadata can be stale, but actual tracked bytes cannot drift.
    manifest = load("test-tz6v5-s03e3f-source-manifest.py")
    need(manifest.attest(REPO, expected) >= 100,
         "S03E3F_SOURCE_MANIFEST_EMPTY")
    revision = re.search(r"(?m)^PLUGIN_REVISION=\s*([0-9]+)\s*$",
                         (REPO / "Makefile").read_text())
    need(revision is not None, "S03E3F_SOURCE_REVISION_MISSING")
    version = (REPO / "VERSION").read_text().strip() + "_" + revision.group(1)
    installed = run("pkg", "query", "%v", "os-zapret2-restyle")
    need(installed.returncode == 0 and installed.stdout.strip() == version,
         "S03E3F_NOT_INSTALLED_EXACT_NATIVE_PKG")
    shipped = REPO / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
    need(SERVICE.is_file() and not SERVICE.is_symlink() and
         SERVICE.read_bytes() == shipped.read_bytes(),
         "S03E3F_INSTALLED_SERVICE_NOT_EXACT_SOURCE")
    return expected


def unowned():
    for path in (JOURNAL, PKG_RECORD):
        need(not path.exists() and not path.is_symlink(),
             "S03E3F_PREEXISTING_OWNER_RECORD")
    return True


def inventory():
    observed = run("/sbin/ipfw", "-q", "list", timeout=20)
    if observed.returncode:
        # Only allowed before the first plugin load; do not kldload for test.
        return None, None
    lines = observed.stdout.splitlines()
    return [line for line in lines if OWNED.match(line)], [
        line for line in lines if not OWNED.match(line)]


def foreign_unchanged(before, after):
    need(after is not None, "S03E3F_IPFW_UNAVAILABLE_AFTER_START")
    if before is not None:
        need(after == before, "S03E3F_FOREIGN_IPFW_CHANGED")
    else:
        need(after and all(line.startswith("65535 ") for line in after),
             "S03E3F_COLD_IPFW_CREATED_FOREIGN_RULE")


def census():
    cmd = run("/bin/ps", "-ax", "-o", "pid=", "-o", "command=", timeout=20)
    need(cmd.returncode == 0, "S03E3F_PROCESS_CENSUS_UNAVAILABLE")
    found = []
    for line in cmd.stdout.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or not fields[0].isdigit():
            continue
        if fields[1] == str(ENGINE) or fields[1].startswith(str(ENGINE) + " "):
            found.append(int(fields[0]))
    return found


def status(web, state):
    value = web.api("POST", "/api/zapret/service/runtime")
    need(value.get("status") == "ok" and value.get("installed") is True and
         value.get("busy") is False and value.get("setup") == "ready" and
         value.get("version") == "v1.0.7" and value.get("service") == state,
         "S03E3F_REAL_HTTPS_STATUS_NOT_" + state.upper())


def running(web, engine_sha, foreign_before, original_args_sha=None):
    unowned()
    status(web, "started")
    result = run(SERVICE, "status", timeout=30)
    need(result.returncode == 0 and "zapret is running" in result.stdout,
         "S03E3F_REAL_LEGACY_STATUS_NOT_RUNNING")
    need(ENGINE.is_file() and not ENGINE.is_symlink() and
         hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_sha,
         "S03E3F_ENGINE_CHANGED")
    need(PID.is_file() and not PID.is_symlink(), "S03E3F_ENGINE_PID_MISSING")
    raw_pid = PID.read_text().strip()
    need(raw_pid.isdecimal() and int(raw_pid) > 1,
         "S03E3F_ENGINE_PID_INVALID")
    need(census() == [int(raw_pid)],
         "S03E3F_NOT_EXACT_ONE_REAL_DVTWS2")
    monitor = MONITOR.read_text().strip() if MONITOR.is_file() else ""
    need(monitor.isdecimal() and int(monitor) > 1 and
         not MONITOR.is_symlink(), "S03E3F_SUPERVISOR_UNQUALIFIED")
    check_monitor = run("/bin/ps", "-p", monitor, "-o", "command=", timeout=20)
    need(check_monitor.returncode == 0 and "supervisor_loop.sh" in
         check_monitor.stdout, "S03E3F_REAL_SUPERVISOR_NOT_RUNNING")
    arg_path = ACTIVE / "dvtws.args"
    need(arg_path.is_file() and not arg_path.is_symlink(),
         "S03E3F_REAL_LEGACY_ARGS_MISSING")
    args = arg_path.read_text().split()
    need(all(s in args for s in EXPECTED) and args.count("--new") == 1,
         "S03E3F_NOT_SEEDED_TCP_QUIC_PROFILES")
    args_sha = hashlib.sha256(arg_path.read_bytes()).hexdigest()
    if original_args_sha is not None:
        need(args_sha == original_args_sha,
             "S03E3F_LEGACY_RESTART_ALTERED_SAVED_PROFILES")
    owned, foreign = inventory()
    foreign_unchanged(foreign_before, foreign)
    need(owned is not None and len(owned) == 2 and
         any(x.startswith("19000 ") and " divert 989 tcp " in x and
             "out not diverted" in x and "lo0" in x for x in owned) and
         any(x.startswith("19001 ") and " divert 989 udp " in x and
             "out not diverted" in x and "lo0" in x for x in owned),
         "S03E3F_LEGACY_IPFW_NOT_EXACT_OWNED_TCP_QUIC")
    return {"pid": int(raw_pid), "monitor": int(monitor), "args_sha": args_sha}


def stopped(web, foreign_before, prior_monitor=None):
    unowned()
    status(web, "stopped")
    result = run(SERVICE, "status", timeout=30)
    need(result.returncode == 1 and "zapret is not running" in result.stdout,
         "S03E3F_LEGACY_STOP_NOT_TERMINAL")
    need(not PID.exists() and not PID.is_symlink() and
         not MONITOR.exists() and not MONITOR.is_symlink() and not census(),
         "S03E3F_STOP_LEFT_ENGINE_OR_SUPERVISOR_PID")
    if prior_monitor is not None:
        need(type(prior_monitor) is int and prior_monitor > 1,
             "S03E3F_STOP_MONITOR_IDENTITY_INVALID")
        old_monitor = run("/bin/ps", "-p", str(prior_monitor),
                          "-o", "command=", timeout=20)
        need("supervisor_loop.sh" not in old_monitor.stdout,
             "S03E3F_STOP_LEFT_OLD_MONITOR_PROCESS")
    owned, foreign = inventory()
    foreign_unchanged(foreign_before, foreign)
    need(owned == [], "S03E3F_STOP_LEFT_OWNED_IPFW")


def lifecycle_http(web, name, g07):
    need(name in ("start", "stop", "restart"), "S03E3F_BAD_VERB")
    result = web.api("POST", "/api/zapret/service/" + name)
    need(isinstance(result, dict), "S03E3F_LIFECYCLE_HTTP_NOT_JSON")
    if name in ("start", "stop", "restart"):
        need(g07.verified_lifecycle_response(name, result),
             "S03E3F_REAL_LEGACY_" + name.upper() + "_TERMINAL_RECEIPT_MISSING")
    return True



def s05c3_template_refusal(web, core, saved_config, engine_sha, foreign_before):
    """Genuine original Legacy Start template failure on test-only native guest.

    Mutate only the disposable guest's exact installed template and restore the
    original inode/bytes in finally. The PHP HTTP and configctl are unmocked.
    """
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_S03E3F_DISPOSABLE_NATIVE") == "1" and
         os.uname().sysname == "FreeBSD" and os.geteuid() == 0,
         "S05C3A_DISPOSABLE_GUEST_ONLY")
    template = Path("/usr/local/opnsense/service/templates/OPNsense/Zapret/zapret.conf")
    source = REPO / "src/opnsense/service/templates/OPNsense/Zapret/zapret.conf"
    stage = Path("/var/run/zapret2-execution.status")
    need(template.is_file() and not template.is_symlink() and
         source.is_file() and not source.is_symlink(),
         "S05C3A_REAL_INSTALLED_TEMPLATE_MISSING")
    meta = template.lstat()
    need(stat.S_ISREG(meta.st_mode) and meta.st_uid == 0 and
         meta.st_nlink == 1 and not meta.st_mode & 0o022 and
         0 < meta.st_size < 128 * 1024 and
         template.read_bytes() == source.read_bytes(),
         "S05C3A_PACKAGE_OWNED_TEMPLATE_IDENTITY")
    need(not stage.is_symlink() and
         (not stage.exists() or
          (stat.S_ISREG(stage.lstat().st_mode) and
           stage.lstat().st_uid == 0 and stage.lstat().st_nlink == 1)),
         "S05C3A_ORIGINAL_STAGE_UNSAFE")
    need(CONFIG.read_bytes() == saved_config and
         ENGINE.is_file() and not ENGINE.is_symlink() and
         hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_sha and
         not PID.exists() and not MONITOR.exists() and
         not ACTIVE.exists() and not census(),
         "S05C3A_NOT_STOPPED_LEGACY_WITH_REAL_ENGINE")
    before_owned, before_foreign = inventory()
    need(before_owned in (None, []) and before_foreign == foreign_before,
         "S05C3A_PREEXISTING_KERNEL_DRIFT")
    fd = os.open(template, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "r+b", buffering=0) as f:
        check = os.fstat(f.fileno())
        need((check.st_dev, check.st_ino) == (meta.st_dev, meta.st_ino) and
             stat.S_ISREG(check.st_mode) and check.st_nlink == 1,
             "S05C3A_TEMPLATE_OPEN_CHANGED_IDENTITY")
        old = f.read()
        need(old == source.read_bytes(), "S05C3A_TEMPLATE_PREWRITE_CHANGED")
        try:
            f.seek(0)
            f.write(b"{% S05C3A_INVALID_JINJA_TAG %}\n")
            f.truncate()
            os.fsync(f.fileno())
            # Real authenticated TLS session, original CSRF and PHP/configd.
            # Read only bounded error fields; never print configd stdout/stderr.
            request = urllib.request.Request(
                core.ORIGIN + "/api/zapret/service/start", data=b"",
                method="POST", headers={"X-CSRFToken": web.csrf_token,
                    "Referer": core.ORIGIN + "/ui/zapret/voice",
                    "Accept": "application/json"})
            try:
                with web.client.open(request, timeout=45):
                    raise Refusal("S05C3B_FALSE_SUCCESS_WITH_INVALID_TEMPLATE")
            except urllib.error.HTTPError as error:
                need(error.code == 500, "S05C3B_HTTP_STATUS_NOT_500")
                raw = error.read(8193)
                need(len(raw) <= 8192, "S05C3B_UNBOUNDED_HTTP_ERROR")
                try:
                    refusal = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    raise Refusal("S05C3B_HTTP_ERROR_NOT_JSON") from None
                need(type(refusal) is dict and
                     refusal.get("errorMessage") ==
                       "Zapret2 Start refused: configuration template generation failed." and
                     isinstance(refusal.get("errorTitle"), str) and
                     bool(refusal["errorTitle"]),
                     "S05C3B_REAL_HTTP_CAUSE_NOT_DELIVERED")
            need(stage.is_file() and not stage.is_symlink() and
                 re.fullmatch(
                    r"1\|13\|config\|failed\|[^|\r\n]{1,64}\|template generation failed\n?",
                    stage.read_text()) is not None,
                 "S05C3A_ORIGINAL_STAGE13_NOT_OBSERVED")
            need(CONFIG.read_bytes() == saved_config and
                 hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_sha and
                 not PID.exists() and not MONITOR.exists() and not ACTIVE.exists() and
                 not census(), "S05C3A_CONFIG_OR_ENGINE_CHANGED")
            after_owned, after_foreign = inventory()
            need(after_owned in (None, []) and after_foreign == foreign_before,
                 "S05C3A_IPFW_CHANGED")
        finally:
            f.seek(0)
            f.write(old)
            f.truncate()
            os.fsync(f.fileno())
    need(template.read_bytes() == source.read_bytes() and
         template.stat().st_ino == meta.st_ino and
         stat.S_IMODE(template.stat().st_mode) == stat.S_IMODE(meta.st_mode),
         "S05C3A_ORIGINAL_TEMPLATE_RESTORE_FAILED")
    print("S05C3B_REAL_STAGE13_HTTP_QUALIFIED_CAUSE=PASS")

def self_test():
    g07 = load("stage2-opnsense-g07-native-lifecycle.py")
    for name, state in (("stop", "stopped"), ("restart", "started"), ("start", "started")):
        good = {"response": "OK", "status": "ok", "verified": True,
                "action": name, "state": state}
        need(g07.verified_lifecycle_response(name, good),
             "S03E3F_GOOD_RECEIPT_REJECTED")
        for bad in ({"response": "OK"},
                    {**good, "verified": False},
                    {**good, "state": "started" if name == "stop" else "stopped"}):
            need(not g07.verified_lifecycle_response(name, bad),
                 "S03E3F_FALSE_RECEIPT_ACCEPTED")
    need(OWNED.match("19000 divert") is not None and
         OWNED.match("19099 divert") is not None and
         OWNED.match("19100 divert") is None and
         OWNED.match("19140 divert") is None and
         OWNED.match("65534 allow") is None,
         "S03E3F_IPFW_RANGE_SCOPE_REGRESSION")
    need("S05C3A_INVALID_JINJA_TAG" in Path(__file__).read_text() and
         "S05C3B_REAL_STAGE13_HTTP_QUALIFIED_CAUSE=PASS" in Path(__file__).read_text(),
         "S05C3A_SOURCE_GUARD_MISSING")
    print("S03E3F_LEGACY_FAST=PASS")


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_S03E3F_DISPOSABLE_NATIVE") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "S03E3F_DISPOSABLE_OPNSENSE_ONLY")
    # Stage0's clean-predecessor guard runs in the workflow BEFORE pkg add.
    # Here the package must be present; rerunning a *preinstall* empty
    # installation inventory would fail by definition, not qualify Legacy.
    opnsense = run("opnsense-version", "-a", timeout=15)
    abi = run("pkg", "config", "ABI", timeout=15)
    guest = run("sysctl", "-n", "kern.vm_guest", timeout=15)
    need(opnsense.returncode == 0 and opnsense.stdout.strip() == "26.7" and
         abi.returncode == 0 and abi.stdout.strip() == "FreeBSD:15:amd64" and
         guest.returncode == 0 and guest.stdout.strip().lower()
         not in ("", "none", "unknown"),
         "S03E3F_INSTALLED_VM_OS_ABI_NOT_QUALIFIED")
    source_sha = exact_source()
    unowned()
    need(not ENGINE.exists() and not ENGINE.is_symlink() and
         not PID.exists() and not MONITOR.exists() and not ACTIVE.exists(),
         "S03E3F_NOT_FRESH_LEGACY_OWNER")
    g04 = load("stage2-opnsense-g04-native-runtime.py")
    initial_model = g04.model()
    need(initial_model.findtext("general/enabled") == "0" and
         not (initial_model.findtext("general/waninterface") or "") and
         (initial_model.findtext("strategy/trafficargs") or "").count("--new") == 1 and
         (initial_model.findtext("hostlist/youtubedomains") or "").splitlines()
         == g04.YOUTUBE, "S03E3F_NOT_G04_NATIVE_SEEDED_CONFIG")
    original_config = CONFIG.read_bytes()
    foreign_before_owned, foreign_before = inventory()
    need(foreign_before_owned in (None, []),
         "S03E3F_FOREIGN_OWNED_RANGE_PREEXISTS")
    engine_sha = g04.setup_upstream()
    unowned()
    need(CONFIG.read_bytes() == original_config,
         "S03E3F_UPSTREAM_SETUP_CHANGED_CONFIG")
    need(not ACTIVE.exists() and not PID.exists(),
         "S03E3F_UPSTREAM_SETUP_STARTED_ENGINE")
    boot = load("stage2-opnsense-real-native-boot-syshook.py")
    unmanaged_before = boot.config_except_model(original_config)
    # Existing G04 test-only helper calls *stock Config::save* via MVC;
    # this is a disposable user's saved preference, not product second writer.
    g04.set_test_only_enabled(True)
    config_enabled = CONFIG.read_bytes()
    need(boot.config_except_model(config_enabled) == unmanaged_before,
         "S03E3F_FOREIGN_CONFIG_CHANGED_AT_NATIVE_SAVE")
    unowned()
    need(not PID.exists() and not ACTIVE.exists(),
         "S03E3F_TEST_MODEL_SAVE_STARTED_DAEMON")

    core = load("stage2-opnsense-real-native-voice-http.py")
    g07 = load("stage2-opnsense-g07-native-lifecycle.py")
    web = core.GuestHttps()
    core.login(web)
    status(web, "stopped")
    s05c3_template_refusal(web, core, config_enabled, engine_sha, foreign_before)

    # Every request below is authentic installed PHP -> configd -> original
    # FD9 -> unchanged legacy service. A failure leaves the disposable guest
    # for teardown; never blindly delete a journal/kill an unknown owner.
    lifecycle_http(web, "start", g07)
    first = running(web, engine_sha, foreign_before)
    need(CONFIG.read_bytes() == config_enabled,
         "S03E3F_START_REWROTE_CONFIG")
    lifecycle_http(web, "restart", g07)
    second = running(web, engine_sha, foreign_before, first["args_sha"])
    need(second["pid"] != first["pid"],
         "S03E3F_LEGACY_RESTART_DID_NOT_ROTATE_ENGINE")
    need(CONFIG.read_bytes() == config_enabled,
         "S03E3F_RESTART_REWROTE_CONFIG")
    lifecycle_http(web, "stop", g07)
    stopped(web, foreign_before, second["monitor"])
    need(CONFIG.read_bytes() == config_enabled,
         "S03E3F_STOP_REWROTE_CONFIG")
    lifecycle_http(web, "start", g07)
    third = running(web, engine_sha, foreign_before, first["args_sha"])
    need(third["pid"] not in (first["pid"], second["pid"]),
         "S03E3F_LEGACY_RESTART_OR_START_PID_NOT_FRESH")
    lifecycle_http(web, "stop", g07)
    stopped(web, foreign_before, third["monitor"])
    need(CONFIG.read_bytes() == config_enabled,
         "S03E3F_FINAL_STOP_CHANGED_CONFIG")
    g04.set_test_only_enabled(False)
    unowned()
    stopped(web, foreign_before, third["monitor"])
    need(boot.config_except_model(CONFIG.read_bytes()) == unmanaged_before,
         "S03E3F_DISPOSABLE_RESTORE_CHANGED_FOREIGN_CONFIG")
    return {
        "status": "PASS_S03E3F_REAL_LEGACY_POSITIVE_HTTP_STOP_RESTART",
        "source_sha": source_sha, "installed_upstream": "v1.0.7",
        "real_engine_sha256": engine_sha,
        "original_fd9_legacy_no_shared_apply_journal": True,
        "real_https_start_restart_stop": True,
        "real_http_start_restart_verified_running": True,
        "real_http_stop_verified_stopped": True,
        "one_engine_pid_rotated": True,
        "original_saved_config_retained_during_lifecycle": True,
        "owned_19000_19099_only_foreign_ipfw_unchanged": True,
        "disposable_config_restored": True,
        "native_real_chromium_browser_click_tested": False,
        "upstream_network_dpi_behavior_tested": False,
        "owner_appliance_modified": False,
    }


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "S03E3F_RUN_OR_SELF_TEST_REQUIRED")
        result = execute()
    except (Refusal, OSError, subprocess.TimeoutExpired, ValueError, KeyError,
            TypeError, ET.ParseError, urllib.error.URLError) as error:
        # Each fixed reason is bounded; never expose raw Config or argv.
        print("S03E3F_LEGACY=REFUSED:" + str(error)[:250], file=sys.stderr)
        return 2
    print("S03E3F_LEGACY=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
