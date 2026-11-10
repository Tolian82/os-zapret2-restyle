#!/usr/bin/env python3
"""G11 pre-owner acceptance: REAL published _1 -> _29 pkg upgrade -> purge -> clean.

A single isolated OPNsense 26.7 VM, two immutable published .pkg archives.
The successor is installed by a real LOCAL pkg repository + pkg upgrade,
NOT pkg add -f. The CI-only file:// repo is never an owner/Pages repository.
This must not execute on a real appliance or produce a GUI PASS claim.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PKGNAME = "os-zapret2-restyle"
OLD = ("0.6.3_1", "eecae7fd21665dd74311323e9359467065663ba6a5662bd0d1c31d847296d0be")
NEW = ("0.6.3_29", "c5ceab0088d22205f46b2260e25e1d93c1500a59d8a19afa7b63b4d8f7f6e852")
ASSETS = ROOT / "dist/g11-published"
CIROOT = Path("/root/g11-acceptance-published")
CATALOG = CIROOT / "catalog"
REPOFILE = Path("/usr/local/etc/pkg/repos/G11PublishedAcceptance.conf")
REPONAME = "G11PublishedAcceptance"
CONFIG = Path("/conf/config.xml")
PURGER = ROOT / "scripts/purge-os-zapret2-restyle.sh"
BACKUPS = Path("/root/zapret2-restyle-purge-backups")
RUNTIME = Path("/usr/local/etc/zapret2")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
REPORT = ROOT / "dist/g11-published-upgrade-purge-clean.json"
SENTINEL = "g11-disposable-published-package"

class Refusal(RuntimeError):
    pass

def need(value, reason):
    if not value:
        raise Refusal(reason)

def command(argv, *, timeout=180, allowed=(0,)):
    try:
        result = subprocess.run(argv, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refusal("COMMAND_EXECUTION_FAILED:" + argv[0]) from exc
    if result.returncode not in allowed:
        # Never print arbitrary command stdout, Config values or filenames.
        raise Refusal("NATIVE_COMMAND_FAILED:" + Path(argv[0]).name +
                      ":rc=" + str(result.returncode))
    return result

def pkg_version():
    present = command(["/usr/sbin/pkg", "info", "-e", PKGNAME],
                      allowed=(0, 1))
    if present.returncode == 1:
        return None
    value = command(["/usr/sbin/pkg", "query", "%v", PKGNAME]).stdout.strip()
    need(bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+_[0-9]+", value)),
         "INSTALLED_PACKAGE_VERSION_UNEXPECTED")
    return value

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def package(version, digest):
    path = ASSETS / (PKGNAME + "-" + version + ".pkg")
    need(path.is_file() and not path.is_symlink(), "PUBLISHED_PACKAGE_MISSING:" + version)
    need(sha(path) == digest, "PUBLISHED_PACKAGE_SHA_MISMATCH:" + version)
    result = command(["/usr/bin/tar", "-xOf", str(path), "+MANIFEST"])
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise Refusal("PUBLISHED_PKG_MANIFEST_INVALID") from exc
    need(data.get("name") == PKGNAME and data.get("version") == version and
         data.get("abi") == "FreeBSD:15:amd64" and
         data.get("arch") == "freebsd:15:x86:64",
         "PUBLISHED_PKG_IDENTITY_OR_ABI_MISMATCH:" + version)
    return path

def gate():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G11_PUBLISHED_DISPOSABLE") == "1" and
         os.environ.get("ZAPRET2_G01_DISPOSABLE_NATIVE") == "1" and
         os.environ.get("ZAPRET2_PURGE_DISPOSABLE_GUEST") == "1",
         "ONLY_ISOLATED_GITHUB_VM_EXPLICIT_OPTIN")
    need(os.geteuid() == 0 and sys.platform.startswith("freebsd") and
         os.uname().machine == "amd64", "ONLY_ROOT_FREEBSD_AMD64")
    need(command(["/usr/local/sbin/opnsense-version", "-a"]).stdout.strip().startswith("26.7"),
         "OPNSENSE_26_7_REQUIRED")
    need(command(["/usr/sbin/pkg", "config", "ABI"]).stdout.strip() ==
         "FreeBSD:15:amd64", "FREEBSD_15_ABI_REQUIRED")
    guest = command(["/sbin/sysctl", "-n", "kern.vm_guest"]).stdout.strip().lower()
    need(guest not in ("", "none", "unknown"), "NOT_A_DISPOSABLE_VM")
    need(not REPOFILE.exists() and not CIROOT.exists() and not BACKUPS.exists() and
         not REPORT.exists(), "CI_GUEST_NOT_FRESH")
    need(pkg_version() is None and not RUNTIME.exists(), "OLD_PACKAGE_OR_ENGINE_PRESENT")
    need(PURGER.is_file() and not PURGER.is_symlink(), "G01_PURGER_NOT_PRESENT")
    need(ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret") is None,
         "OLD_USER_CONFIG_IN_DISPOSABLE_VM")

def xml():
    root = ET.fromstring(CONFIG.read_bytes())
    need(root.tag == "opnsense", "NATIVE_CONFIG_ROOT_CHANGED")
    return root

def clean_element(elem):
    if elem is None:
        return None
    other = copy.deepcopy(elem)
    for child in other.iter():
        if not (child.text or "").strip():
            child.text = None
        child.tail = None
    return ET.tostring(other, encoding="utf-8")

def other_config(root):
    root = copy.deepcopy(root)
    for revision in root.findall("revision"):
        root.remove(revision)
    firmware = root.find("./system/firmware")
    if firmware is not None:
        for reg in firmware.findall("plugins"):
            firmware.remove(reg)
    zapret = root.find("./OPNsense/Zapret")
    if zapret is not None:
        root.find("./OPNsense").remove(zapret)
    return clean_element(root)

def seed_existing_saved_config():
    # User-visible settings through the native Config API, never a second
    # writer to config.xml. This is disposable-only, NOT an owner command.
    php = r'''
require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
    $root = $c->object();
    if (!isset($root->OPNsense)) $root->addChild("OPNsense");
    if (!isset($root->OPNsense->Zapret)) $root->OPNsense->addChild("Zapret");
    $z = $root->OPNsense->Zapret;
    if (!isset($z->general)) $z->addChild("general");
    $z->general->enabled = "0";
    $z->general->waninterface = "lo0";
    $z->general->divertport = "989";
    $z->general->ports = "65431";
    if (!isset($z->strategy)) $z->addChild("strategy");
    $z->strategy->trafficargs = "--filter-tcp=65431\n--filter-l7=tls\n--lua-desync=pktmod:ip_ttl=23";
    if (!isset($z->hostlist)) $z->addChild("hostlist");
    $z->hostlist->mode = "all";
    $z->hostlist->youtubedomains = "example.org";
    $z->g11Sentinel = "g11-disposable-published-package";
    $c->save();
} finally { $c->unlock(); }
'''
    command(["/usr/local/bin/php", "-r", php], timeout=60)
    node = xml().find("./OPNsense/Zapret")
    need(node is not None and node.findtext("g11Sentinel") == SENTINEL and
         node.findtext("general/enabled") == "0" and
         node.findtext("strategy/trafficargs", "").startswith("--filter-tcp=65431"),
         "EXISTING_SAVED_USER_CONFIGURATION_NOT_SEEDED")

def prepare_file_repository(target):
    # The only package in this isolated CI repo is a copy of the IMMUTABLE
    # GitHub testing release asset. No stable Pages/pkg and no owner repos.
    CATALOG.mkdir(parents=True, mode=0o700)
    shutil.copyfile(target, CATALOG / target.name)
    need(sha(CATALOG / target.name) == NEW[1], "REPO_COPIED_ARCHIVE_CHANGED")
    command(["/usr/sbin/pkg", "repo", str(CATALOG)], timeout=90)
    need((CATALOG / "meta.conf").is_file() and
         (CATALOG / "packagesite.pkg").is_file(),
         "NATIVE_PKG_CATALOG_NOT_CREATED")
    REPOFILE.write_text(
        'G11PublishedAcceptance: {\n' +
        '  url: "file://' + str(CATALOG) + '",\n' +
        '  enabled: yes,\n  signature_type: "none",\n  priority: 90\n}\n',
        encoding="ascii")
    REPOFILE.chmod(0o600)
    command(["/usr/sbin/pkg", "update", "-r", REPONAME, "-f"], timeout=90)

def check_registered():
    root = xml()
    text = root.findtext("./system/firmware/plugins") or ""
    need(PKGNAME in text.split(","), "NATIVE_FIRMWARE_REGISTRATION_MISSING")

def assert_no_capture():
    if command(["/sbin/kldstat", "-q", "-m", "ipfw"], allowed=(0, 1)).returncode == 0:
        rules = command(["/sbin/ipfw", "-q", "list"]).stdout
        need(not any(re.match(r"^\s*(?:1900[0-9]|19010|191(?:0[0-9]|[12][0-9]|3[01]))\s+", row)
                     for row in rules.splitlines()), "OWNED_IPFW_PRESENT_BEFORE_START")

def exercise_running_on_loopback():
    # Real upstream, native service, original FD9, only lo0:65431; no WAN
    # DPI bypass is claimed. The G01 test already used this safe profile.
    setup = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh")
    need(setup.is_file() and not setup.is_symlink(), "UPSTREAM_INSTALLER_MISSING")
    native_setup = subprocess.run(
        ["/bin/sh", str(setup), "install", "v1.0.7"],
        capture_output=True, text=True, timeout=360, check=False)
    if native_setup.returncode:
        # No Config contents, tokens, hostnames or raw command output in CI.
        observed = (native_setup.stdout + native_setup.stderr).lower()
        rules = (
            ("could not obtain bol-van/zapret2 releases", "GITHUB_RELEASES_UNAVAILABLE"),
            ("no cached stable bol-van", "GITHUB_RELEASES_CACHE_UNAVAILABLE"),
            ("stable bol-van/zapret2 release not found", "UNEXPECTED_STABLE_TAG"),
            ("stock freebsd repository is enabled", "FOREIGN_FREEBSD_REPO_ENABLED"),
            ("legacy freebsd repository backup remains", "LEGACY_FREEBSD_REPO_BACKUP"),
            ("missing opnsense package", "MISSING_NATIVE_DEPENDENCY"),
            ("an incomplete or unknown state", "INCOMPLETE_NATIVE_OWNER"),
            ("zapret service is in an incomplete or unknown state", "INCOMPLETE_NATIVE_OWNER"),
            ("original git", "GIT_RESOURCE_GUARD_REFUSED"),
            ("could not install", "RUNTIME_BUILD_FAILED"),
        )
        matches = [label for phrase, label in rules if phrase in observed]
        raise Refusal("EXACT_NATIVE_RUNTIME_SETUP_REFUSED:rc=" +
                      str(native_setup.returncode) +
                      ":class=" + (matches[0] if matches else "UNCLASSIFIED"))
    engine = RUNTIME / "binaries/my/dvtws2"
    need(engine.is_file() and os.access(engine, os.X_OK), "NATIVE_ENGINE_NOT_BUILT")
    need(SERVICE.is_file() and not SERVICE.is_symlink(), "INSTALLED_SERVICE_MISSING")
    command([str(SERVICE), "start"], timeout=180)
    check = command([str(SERVICE), "status"], timeout=30)
    need("zapret is running" in check.stdout, "SERVICE_NOT_ACTUALLY_RUNNING")
    pid = Path("/var/run/dvtws2.pid")
    need(pid.is_file() and pid.read_text().strip().isdecimal(), "REAL_ENGINE_PID_MISSING")
    rules = command(["/sbin/ipfw", "-q", "list"]).stdout
    need(any(re.match(r"^\s*0*19000\s+", row) and "divert 989" in row and
             "65431" in row and "lo0" in row for row in rules.splitlines()),
         "LOOPBACK_SCOPED_RULE_NOT_INSTALLED")

def exercise_purge():
    before = CONFIG.read_bytes()
    dry = command(["/bin/sh", str(PURGER), "--dry-run"], timeout=90)
    need("DRY RUN:" in dry.stdout and CONFIG.read_bytes() == before,
         "G01_DRY_RUN_MUTATED_CONFIG")
    done = command(["/bin/sh", str(PURGER), "--purge", "--yes-disposable"], timeout=300)
    need("PURGE COMPLETE" in done.stdout and "POSTCHECK:" in done.stdout,
         "G01_COMPLETE_POSTCHECK_MISSING")
    need(pkg_version() is None and xml().find("./OPNsense/Zapret") is None,
         "G01_STALE_PKG_OR_SAVED_USER_CONFIG")
    need(not RUNTIME.exists() and not SERVICE.exists() and
         not Path("/var/run/dvtws2.pid").exists(),
         "G01_STALE_ENGINE_SERVICE_OR_PID")
    need(REPOFILE.exists(), "G01_REMOVED_FOREIGN_DISPOSABLE_REPO")
    copies = list(BACKUPS.glob("config-*.xml"))
    need(len(copies) == 1 and sha(copies[0]) == hashlib.sha256(before).hexdigest() and
         stat.S_IMODE(copies[0].stat().st_mode) == 0o600,
         "G01_PRIVATE_CONFIG_BACKUP_MISSING_OR_ALTERED")
    assert_no_capture()

def verify_clean_defaults():
    root = xml()
    z = root.find("./OPNsense/Zapret")
    need(z is not None and z.find("g11Sentinel") is None, "G11_PREVIOUS_CONFIG_REAPPEARED")
    domains = (z.findtext("hostlist/youtubedomains") or "").strip().splitlines()
    need(domains == ["youtube.com", "googlevideo.com", "yt.be", "youtu.be",
                     "ytimg.com", "youtubei.googleapis.com", "youtube.googleapis.com",
                     "youtube-nocookie.com", "ggpht.com", "ssl.gstatic.com"],
         "CLEAN_INITIAL_TEN_DOMAINS_MISMATCH")
    strategy = z.findtext("strategy/trafficargs") or ""
    need(strategy.count("--new") == 1 and "--filter-tcp=80,443" in strategy and
         "--filter-udp=443" in strategy and
         "--lua-desync=fake:blob=fake_default_quic:repeats=5" in strategy and
         "--blob=http_iana_org" in strategy,
         "CLEAN_INITIAL_TCP_QUIC_PROFILE_MISMATCH")
    need((z.findtext("general/waninterface") or "") == "" and
         (z.findtext("general/enabled") or "0") == "0",
         "CLEAN_INITIAL_WAN_OR_ENABLED_UNSAFE")
    check_registered()
    assert_no_capture()

def execute():
    gate()
    older = package(*OLD)
    newer = package(*NEW)
    # Run only native commands against the two SHA-pinned published bytes.
    prepare_file_repository(newer)
    command(["/usr/sbin/pkg", "add", "-f", str(older)], timeout=200)
    need(pkg_version() == OLD[0], "OLD_PUBLISHED_STABLE_NOT_INSTALLED")
    check_registered()
    seed_existing_saved_config()
    original = xml()
    old_user = clean_element(original.find("./OPNsense/Zapret"))
    foreign = other_config(original)
    assert_no_capture()
    # This is the real stock repo-driven pkg UPGRADE path, not pkg add -f.
    command(["/usr/sbin/pkg", "upgrade", "-y", "-r", REPONAME, PKGNAME],
            timeout=250)
    need(pkg_version() == NEW[0], "STOCK_PKG_UPGRADE_DID_NOT_SELECT_NEW_RELEASE")
    upgraded = xml()
    need(clean_element(upgraded.find("./OPNsense/Zapret")) == old_user,
         "STOCK_UPGRADE_OVERWROTE_EXISTING_USER_CONFIG")
    need(other_config(upgraded) == foreign, "STOCK_UPGRADE_MODIFIED_FOREIGN_CONFIG")
    check_registered()
    assert_no_capture()
    print("PASS_G11_PUBLISHED_STOCK_PKG_UPGRADE_WITH_USER_CONFIG=1", flush=True)

    # After verifying the existing installation, test its actual full purge.
    exercise_running_on_loopback()
    exercise_purge()
    need(other_config(xml()) == foreign, "G01_PURGE_CHANGED_FOREIGN_CONFIG")
    print("PASS_G11_PUBLISHED_RUNNING_FULL_PURGE=1", flush=True)

    # Clean again, from the VERY SAME published package via stock pkg repo.
    command(["/usr/sbin/pkg", "install", "-y", "-r", REPONAME, PKGNAME],
            timeout=250)
    need(pkg_version() == NEW[0], "CLEAN_REINSTALL_PACKAGE_VERSION_MISMATCH")
    verify_clean_defaults()
    need(other_config(xml()) == foreign,
         "G11_CLEAN_REINSTALL_CHANGED_FOREIGN_CONFIG")
    need(sha(older) == OLD[1] and sha(newer) == NEW[1] and
         sha(CATALOG / newer.name) == NEW[1],
         "PHYSICAL_PUBLISHED_ARCHIVES_CHANGED_DURING_ACCEPTANCE")
    result = {
        "schema": 1, "status": "PASS_G11_EXACT_PUBLISHED_UPGRADE_PURGE_CLEAN",
        "source_old": "v0.6.3_1", "source_new": "v0.6.3_29",
        "published_old_pkg_sha256": OLD[1],
        "published_new_pkg_sha256": NEW[1],
        "official_opnsense_abi": "FreeBSD:15:amd64",
        "old_exact_published_pkg_installed": True,
        "real_file_pkg_repository_upgrade": True,
        "existing_user_and_foreign_config_preserved": True,
        "real_runtime_loopback_fd9_ipfw": True,
        "real_native_full_purge_after_upgrade": True,
        "foreign_ci_repo_not_purged": True,
        "original_config_private_backup_verified": True,
        "same_published_package_clean_reinstall_from_catalog": True,
        "clean_initial_domains_and_tcp_quic_strategy": True,
        "no_auto_wan_or_service_start": True,
        "owner_appliance_modified": False,
        "browser_firmware_gui_tested": False,
        "real_wan_dpi_or_voice_media_tested": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    REPOFILE.unlink()
    print("G11_EXACT_PUBLISHED_ACCEPTANCE=" + json.dumps(result, sort_keys=True),
          flush=True)

def self_test():
    assert re.fullmatch(r"[0-9a-f]{64}", OLD[1])
    assert re.fullmatch(r"[0-9a-f]{64}", NEW[1])
    assert OLD[0] != NEW[0] and OLD[1] != NEW[1]
    assert "G11PublishedAcceptance" not in "Zapret2Restyle"
    assert pkg_version.__name__ == "pkg_version"
    assert OLD[0] == "0.6.3_1" and NEW[0] == "0.6.3_29"
    print("PASS_G11_PUBLISHED_SOURCE_SHAPES=1")

if __name__ == "__main__":
    if sys.argv == [sys.argv[0], "--self-test"]:
        self_test()
    elif len(sys.argv) == 1:
        try:
            execute()
        except (Refusal, ET.ParseError, OSError) as error:
            print("G11_PUBLISHED_ACCEPTANCE_REFUSED=" + type(error).__name__ +
                  ":" + (str(error) if isinstance(error, Refusal) else "native preflight"),
                  file=sys.stderr)
            sys.exit(2)
    else:
        sys.exit("Usage: stage11-published-upgrade-purge-clean.py [--self-test]")
