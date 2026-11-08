#!/usr/bin/env python3
"""G02: real OPNsense firmware GUI removal path on a disposable 26.7 VM.

Requires stage2-opnsense-real-native-clean-install.py to have installed the
exact source-built package first. The owner router is NEVER an allowed target.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

PKG = "os-zapret2-restyle"
ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("/conf/config.xml")
RUNTIME = Path("/usr/local/etc/zapret2")
REGISTER = Path("/usr/local/opnsense/scripts/firmware/register.php")
PHP = "/usr/local/bin/php"
MENU_XML = Path("/usr/local/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml")
REMOVE = Path("/usr/local/opnsense/scripts/firmware/remove.sh")


class GateFailure(Exception):
    pass


def require(ok, detail):
    if not ok:
        raise GateFailure(detail)


def execute(argv, *, timeout=120, expected=(0,)):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode not in expected:
        raise GateFailure("COMMAND FAILED: " + argv[0] + " rc=" + str(p.returncode) +
                          " stderr=" + p.stderr[-350:])
    return p


def config():
    return ET.fromstring(CONFIG.read_bytes())


def registered(root):
    return PKG in (root.findtext("system/firmware/plugins") or "").split(",")


def menu_cache(refresh=False):
    php = r'''
require_once("script/load_phalcon.php");
$m = new \OPNsense\Base\Menu\MenuSystem();
if (getenv("G02_REFRESH_MENU") === "1") { $m->persist(false); }
$a = new \OPNsense\Core\AppConfig();
echo rtrim($a->application->tempDir, "/") . "/opnsense_menu_cache.xml";
'''
    env = {**os.environ, "G02_REFRESH_MENU": "1" if refresh else "0"}
    p = subprocess.run([PHP, "-r", php], capture_output=True, text=True,
                       env=env, timeout=35)
    require(p.returncode == 0, "NATIVE_MENU_SYSTEM_FAILED:" + p.stderr[-200:])
    cache = Path(p.stdout.strip())
    require(cache.name == "opnsense_menu_cache.xml" and cache.is_absolute(),
            "MENU_CACHE_UNTRUSTED_PATH")
    return cache


def menu_has_zapret(cache):
    require(cache.is_file(), "OPNSENSE_MENU_CACHE_MISSING")
    menu = ET.fromstring(cache.read_bytes())
    return bool(menu.findall(".//Services/Zapret") or menu.findall(".//Zapret"))


def seed_user_config():
    php = r'''
require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
    $root = $c->object();
    if (!isset($root->OPNsense)) $root->addChild("OPNsense");
    if (!isset($root->OPNsense->Zapret)) $root->OPNsense->addChild("Zapret");
    if (isset($root->OPNsense->Zapret->g02TestMarker)) exit(73);
    $root->OPNsense->Zapret->addChild("g02TestMarker", "KEEP-G02-CONFIG");
    $c->save();
} finally { $c->unlock(); }
'''
    execute([PHP, "-r", php])
    require(config().findtext("OPNsense/Zapret/g02TestMarker") == "KEEP-G02-CONFIG",
            "G02_USER_CONFIG_SEED_FAILED")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight():
    require(os.environ.get("GITHUB_ACTIONS") == "true" and
            os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
            os.environ.get("ZAPRET2_G02_DISPOSABLE_NATIVE") == "1",
            "G02_DISPOSABLE_FLAGS_REQUIRED")
    require(os.uname().sysname == "FreeBSD" and os.uname().machine == "amd64" and
            os.geteuid() == 0, "G02_NATIVE_FREEBSD_AMD64_ROOT_REQUIRED")
    require(execute(["/usr/local/sbin/opnsense-version", "-a"]).stdout.strip() == "26.7",
            "G02_WRONG_OPNSENSE_RELEASE")
    guest = execute(["/sbin/sysctl", "-n", "kern.vm_guest"]).stdout.strip().lower()
    require(guest not in ("none", "unknown", ""), "G02_NOT_A_DISPOSABLE_VIRTUAL_MACHINE")
    require(execute(["/usr/sbin/pkg", "info", "-e", PKG], expected=(0, 1)).returncode == 0,
            "G02_PLUGIN_NOT_INSTALLED")
    require(MENU_XML.is_file() and REMOVE.is_file() and REGISTER.is_file(),
            "G02_ORIGINAL_OPNSENSE_ENTRYPOINT_MISSING")
    revision = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)\s*$",
                         (ROOT / "Makefile").read_text())
    require(revision is not None, "G02_SOURCE_REVISION_MISSING")
    ver = (ROOT / "VERSION").read_text().strip()
    archive = ROOT / "dist" / (PKG + "-" + ver + "_" + revision.group(1) + ".pkg")
    require(archive.is_file() and not archive.is_symlink(),
            "G02_ORIGINAL_PHYSICAL_PACKAGE_MISSING")
    return archive


def qualify():
    pkg = preflight()
    pkg_sha = sha(pkg)
    before_menu = menu_cache(refresh=True)
    require(menu_has_zapret(before_menu), "G02_PLUGIN_NOT_PRESENT_IN_INITIAL_MENU")
    seed_user_config()

    setup = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh")
    require(setup.is_file(), "G02_UPSTREAM_INSTALLER_MISSING")
    execute(["/bin/sh", str(setup), "install", "v1.0.7"], timeout=350)
    engine = RUNTIME / "binaries/my/dvtws2"
    require(engine.is_file() and os.access(engine, os.X_OK),
            "G02_REAL_UPSTREAM_ENGINE_NOT_INSTALLED")
    owned = RUNTIME / "lua/g02-custom-owner.lua"
    owned.parent.mkdir(parents=True, exist_ok=True)
    owned.write_text("-- G02 preserve user content\n")
    before = config()
    before_z = ET.tostring(before.find("OPNsense/Zapret"))
    before_user_sha = sha(owned)
    before_engine_sha = sha(engine)
    require(registered(before), "G02_FIRMWARE_PLUGIN_NOT_REGISTERED")

    # Native OPNsense Firmware GUI removal uses this exact stock server-side
    # path: pkg remove + firmware/register.php remove + pkg autoremove.
    execute(["/bin/sh", str(REMOVE), PKG], timeout=240)
    require(execute(["/usr/sbin/pkg", "info", "-e", PKG], expected=(0, 1)).returncode == 1,
            "G02_PACKAGE_STILL_REGISTERED")
    require(not MENU_XML.exists(), "G02_PLUGIN_MENU_FILE_SURVIVED_NATIVE_REMOVAL")
    require(not before_menu.exists(), "G02_MENU_CACHE_NOT_INVALIDATED")
    after = config()
    require(not registered(after), "G02_FIRMWARE_REGISTRATION_REMAINS")
    require(ET.tostring(after.find("OPNsense/Zapret")) == before_z,
            "G02_USER_CONFIG_CHANGED_BY_NORMAL_UNINSTALL")
    require(sha(owned) == before_user_sha and sha(engine) == before_engine_sha,
            "G02_USER_LUA_OR_UPSTREAM_ENGINE_WAS_DELETED")
    rebuilt = menu_cache(refresh=True)
    require(not menu_has_zapret(rebuilt), "G02_STALE_SERVICES_MENU_AFTER_INVALIDATION")

    # Reinstall *the physically identical* already accepted native package.
    require(sha(pkg) == pkg_sha, "G02_PACKAGE_SHA_CHANGED_BEFORE_REINSTALL")
    # The stock GUI removal may prune automatic dependencies; restore declared
    # prerequisites only on this disposable guest, not on the owner's router.
    execute(["/usr/sbin/pkg", "update", "-f"], timeout=200)
    execute(["/usr/sbin/pkg", "install", "-y", "git", "ca_root_nss", "jq",
             "gmake", "pkgconf", "luajit"], timeout=240)
    execute(["/usr/sbin/pkg", "add", "-f", str(pkg)], timeout=240)
    require(execute(["/usr/sbin/pkg", "info", "-e", PKG], expected=(0, 1)).returncode == 0,
            "G02_NATIVE_REINSTALL_FAILED")
    require(config().findtext("OPNsense/Zapret/g02TestMarker") == "KEEP-G02-CONFIG",
            "G02_REINSTALL_LOST_SAVED_CONFIG")
    require(sha(owned) == before_user_sha and sha(engine) == before_engine_sha,
            "G02_REINSTALL_CHANGED_UPSTREAM_OR_CUSTOM_RESOURCES")
    require(registered(config()), "G02_FIRMWARE_REINSTALL_NOT_REGISTERED")
    require(menu_has_zapret(menu_cache(refresh=True)),
            "G02_REINSTALLED_PLUGIN_MENU_NOT_RETURNED")
    require(sha(pkg) == pkg_sha, "G02_REINSTALL_PACKAGE_SHA_CHANGED")
    return {
        "status": "PASS_G02_NORMAL_FIRMWARE_REMOVE_AND_SAME_PACKAGE_REINSTALL",
        "package_sha256": pkg_sha,
        "real_firmware_remove_script": True,
        "native_menu_cache_invalidated_without_gui_restart": True,
        "saved_Config_and_upstream_and_customLua_preserved": True,
        "same_physical_package_reinstalled": True,
        "owner_live_browser_tested": False,
        "owner_machine_modified": False,
    }


if __name__ == "__main__":
    try:
        result = qualify()
    except (GateFailure, OSError, ValueError, ET.ParseError,
            subprocess.TimeoutExpired) as error:
        print("G02_NATIVE=FAIL:" + str(error), file=sys.stderr)
        sys.exit(2)
    print("G02_NATIVE=" + json.dumps(result, sort_keys=True))
