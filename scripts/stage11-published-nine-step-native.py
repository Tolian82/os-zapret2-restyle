#!/usr/bin/env python3
"""G10A: ordered published-byte native nine-stage *smoke*, NOT full A01-A22.

Only disposable GitHub Actions OPNsense 26.7 VMs, never the owner router.
Reuse historic G11/G02 read-only and native test helpers. Explicitly do NOT
use the historic file:// repo or checkout purge for any installation/removal.
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

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
ASSETS = ROOT / "dist/g11-nine-published"
REPORT = ROOT / "dist/g11-nine-published.json"
OLD = ("0.6.3_1", "eecae7fd21665dd74311323e9359467065663ba6a5662bd0d1c31d847296d0be")
NEW = ("0.6.3_33", "59f38d12bcd09496f8178af597a383062f7045c3e63f8120b964076fdae01b64")
INSTALLER_SHA = "b7cef59e26e73c361f719d098e2a33f177de0bc506a113d9606f8237721f09ba"
INSTALLER = ASSETS / "install-os-zapret2-restyle-0.6.3_33.sh"
LOCAL_PURGE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh")
SOURCE_PURGE = ROOT / "scripts/purge-os-zapret2-restyle.sh"
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
RUNTIME = Path("/usr/local/etc/zapret2")
CUSTOM = RUNTIME / "lua/g11-disposable-user.lua"
BACKUPS = Path("/root/zapret2-restyle-purge-backups")
MENU = Path("/usr/local/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml")
REMOVE = Path("/usr/local/opnsense/scripts/firmware/remove.sh")

class Refusal(RuntimeError):
    pass

def need(ok, why):
    if not ok:
        raise Refusal(why)

def load(module_name, filename):
    spec = importlib.util.spec_from_file_location(module_name, HERE / filename)
    need(spec is not None and spec.loader is not None, "MISSING_NATIVE_LIBRARY")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

historical = load("g11_published_old_runner", "stage11-published-upgrade-purge-clean.py")
firmware = load("g02_native_remove", "stage2-opnsense-real-native-normal-uninstall.py")
historical.NEW = NEW
historical.ASSETS = ASSETS
historical.REPORT = REPORT

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def call(argv, *, timeout=250, env=None):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                           env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refusal("NATIVE_COMMAND_UNAVAILABLE:" + Path(argv[0]).name) from exc
    need(p.returncode == 0, "NATIVE_COMMAND_REFUSED:" +
         Path(argv[0]).name + ":rc=" + str(p.returncode))
    return p.stdout

def version():
    return historical.pkg_version()

def attested_local_purge():
    need(LOCAL_PURGE.is_file() and not LOCAL_PURGE.is_symlink() and
         LOCAL_PURGE.lstat().st_uid == 0 and
         stat.S_IMODE(LOCAL_PURGE.stat().st_mode) == 0o755 and
         LOCAL_PURGE.read_bytes() == SOURCE_PURGE.read_bytes(),
         "PUBLISHED_PACKAGE_PURGE_PATH_OR_BYTES_MISMATCH")

def published_installer(target, label):
    need(sha(target) == NEW[1] and sha(INSTALLER) == INSTALLER_SHA,
         "PUBLISHED_ASSET_MUTATED_" + label)
    env = dict(os.environ)
    env["ZAPRET2_STAGE5_CROSS_VM"] = "1"
    env["ZAPRET2_CI_LOCAL_ARCHIVE"] = str(target)
    result = call(["/bin/sh", str(INSTALLER)], env=env, timeout=440)
    need("PASS: installed " + NEW[0] in result and version() == NEW[0],
         "SAME_COMPANION_NATIVE_PKG_ADD_FAILED_" + label)
    attested_local_purge()
    historical.check_registered()

def saved():
    return historical.clean_element(historical.xml().find("./OPNsense/Zapret"))

def clean_rules():
    historical.assert_no_capture()

def live(label):
    need(version() == NEW[0] and SERVICE.is_file(),
         "MISSING_REAL_NATIVE_SERVICE_" + label)
    need("zapret is running" in call([str(SERVICE), "status"], timeout=40),
         "SERVICE_NOT_RUNNING_" + label)
    pid = Path("/var/run/dvtws2.pid")
    need(pid.is_file() and pid.read_text().strip().isdecimal(),
         "ENGINE_PID_NOT_PRESENT_" + label)
    rules = call(["/sbin/ipfw", "-q", "list"], timeout=30)
    need(any(re.match(r"^\s*0*19000\s+", row) and "divert 989" in row and
             "65431" in row and "lo0" in row for row in rules.splitlines()),
         "NATIVE_LOOPBACK_IPFW_NOT_INSTALLED_" + label)

def functional_smoke(label, first=False):
    if first:
        historical.exercise_running_on_loopback()
    else:
        call([str(SERVICE), "start"], timeout=180)
    live(label)
    call([str(SERVICE), "stop"], timeout=180)
    clean_rules()
    call([str(SERVICE), "start"], timeout=180)
    live(label + "_AFTER_RESTART")
    need(historical.xml().findtext("./OPNsense/Zapret/g11Sentinel") ==
         "g11-disposable-published-package", "USER_SETTINGS_LOST_" + label)
    return "PASS_NATIVE_LOOPBACK_START_STOP_RESTART_SMOKE_ONLY"

def native_gate():
    historical.gate()
    need(os.environ.get("ZAPRET2_G10A_NINE_PUBLISHED") == "1",
         "NINE_PHASE_DISPOSABLE_OPT_IN_REQUIRED")
    need(not LOCAL_PURGE.exists() and not BACKUPS.exists(),
         "GUEST_NOT_FRESH_FOR_NINE_PHASES")
    need(not historical.REPOFILE.exists(), "FOREIGN_CI_PKG_REPOSITORY_PRESENT")

def run():
    native_gate()
    oldpkg = historical.package(*OLD)
    newpkg = historical.package(*NEW)
    need(INSTALLER.is_file() and not INSTALLER.is_symlink() and
         sha(INSTALLER) == INSTALLER_SHA and
         "PACKAGE_SHA256='" + NEW[1] + "'" in INSTALLER.read_text() and
         "pkg add -f" in INSTALLER.read_text(), "PUBLISHED_INSTALLER_INVALID")
    stages = {}

    # 1. Pre-existing immutable stable _1, never removed before upgrade.
    call(["/usr/sbin/pkg", "add", "-f", str(oldpkg)], timeout=320)
    need(version() == OLD[0], "STABLE_PREDECESSOR_NOT_INSTALLED")
    historical.seed_existing_saved_config()
    original_user = saved()
    original_foreign = historical.other_config(historical.xml())
    clean_rules()
    published_installer(newpkg, "UPGRADE")
    need(saved() == original_user and
         historical.other_config(historical.xml()) == original_foreign,
         "EXISTING_STABLE_CONFIG_CHANGED_DURING_UPGRADE")
    stages["1"] = "PASS_STABLE_STOPPED_UPGRADE_WITH_NATIVE_COMPANION"

    # 2. Post-upgrade real engine + original FD9/lo0 and Stop/Restart smoke.
    stages["2"] = functional_smoke("UPGRADED", first=True)
    CUSTOM.write_text("-- user-owned disposable Lua\n")
    custom_sha = sha(CUSTOM)
    engine_sha = sha(RUNTIME / "binaries/my/dvtws2")
    existing = saved()
    foreign = historical.other_config(historical.xml())

    # 3. Actual stock OPNsense Firmware GUI remove server-side entrypoint.
    menu = firmware.menu_cache(refresh=True)
    need(firmware.menu_has_zapret(menu), "PRE_UNINSTALL_GUI_MENU_MISSING")
    call(["/bin/sh", str(REMOVE), "os-zapret2-restyle"], timeout=360)
    need(version() is None and not MENU.exists() and not LOCAL_PURGE.exists() and
         not menu.exists(), "NATIVE_GUI_UNINSTALL_INCOMPLETE")
    need(saved() == existing and historical.other_config(historical.xml()) == foreign,
         "GUI_UNINSTALL_DAMAGED_CONFIG")
    need(sha(CUSTOM) == custom_sha and
         sha(RUNTIME / "binaries/my/dvtws2") == engine_sha,
         "GUI_UNINSTALL_DELETED_UPSTREAM_OR_USER_RESOURCES")
    need(not firmware.menu_has_zapret(firmware.menu_cache(refresh=True)),
         "STALE_SERVICES_MENU_AFTER_GUI_UNINSTALL")
    clean_rules()
    stages["3"] = "PASS_FIRMWARE_REMOVE_AND_MENU_INVALIDATION"

    # 4. Exactly the same published companion installer, without new repo.
    published_installer(newpkg, "NORMAL_REINSTALL")
    stages["4"] = "PASS_SAME_PUBLISHED_LOCAL_COMPANION_REINSTALL"

    # 5. Exact saved subtree including intentionally empty fields; runtime.
    need(saved() == existing and historical.other_config(historical.xml()) == foreign,
         "EXISTING_SAVED_CONFIG_CHANGED_BY_REINSTALL")
    need(sha(CUSTOM) == custom_sha and
         sha(RUNTIME / "binaries/my/dvtws2") == engine_sha and
         firmware.menu_has_zapret(firmware.menu_cache(refresh=True)),
         "USER_FILES_OR_GUI_MENU_LOST_ON_REINSTALL")
    stages["5"] = "PASS_EXISTING_CONFIG_AND_UPSTREAM_EXACT"

    # 6. Repeat the same native real service regression smoke.
    stages["6"] = functional_smoke("REINSTALLED", first=False)
    before_purge_foreign = historical.other_config(historical.xml())

    # 7. Actually RUN the installed package purger, check its own deletion.
    attested_local_purge()
    before_purge_bytes = historical.CONFIG.read_bytes()
    need("DRY RUN:" in call(["/bin/sh", str(LOCAL_PURGE), "--dry-run"]) and
         before_purge_bytes == historical.CONFIG.read_bytes(),
         "INSTALLED_DRY_RUN_NOT_INERT")
    done = call(["/bin/sh", str(LOCAL_PURGE), "--purge", "--yes-disposable"], timeout=350)
    need("PURGE COMPLETE" in done and "POSTCHECK:" in done and
         not os.path.lexists(LOCAL_PURGE) and
         version() is None and not SERVICE.exists() and
         not RUNTIME.exists() and
         historical.xml().find("./OPNsense/Zapret") is None,
         "PACKAGED_FULL_PURGE_DID_NOT_SELF_REMOVE")
    need(historical.other_config(historical.xml()) == before_purge_foreign,
         "PACKAGED_PURGE_ALTERED_FOREIGN_CONFIG")
    backups = sorted(BACKUPS.glob("config-*.xml"))
    need(len(backups) == 1 and sha(backups[0]) ==
         hashlib.sha256(before_purge_bytes).hexdigest() and
         stat.S_IMODE(BACKUPS.stat().st_mode) == 0o700 and
         stat.S_IMODE(backups[0].stat().st_mode) == 0o600,
         "G01_ORIGINAL_PRIVATE_BACKUP_UNVERIFIED")
    clean_rules()
    stages["7"] = "PASS_INSTALLED_SELF_DELETING_G01_AND_BACKUP"

    # 8. Reinstall immutable published bytes with the very same script.
    published_installer(newpkg, "AFTER_FULL_PURGE")
    stages["8"] = "PASS_SAME_PUBLISHED_COMPANION_CLEAN_INSTALL"

    # 9. Clean defaults, first upstream setup and loopback engine; not A01-A22.
    historical.verify_clean_defaults()
    historical.seed_existing_saved_config()
    historical.exercise_running_on_loopback()
    live("FRESH_FIRST_START")
    call([str(SERVICE), "stop"], timeout=180)
    clean_rules()
    stages["9"] = "PASS_CLEAN_DEFAULTS_AND_FIRST_NATIVE_LOOPBACK_SMOKE_ONLY"

    need(sha(oldpkg) == OLD[1] and sha(newpkg) == NEW[1] and
         sha(INSTALLER) == INSTALLER_SHA and
         not historical.REPOFILE.exists(), "PUBLISHED_BYTES_OR_REPO_CHANGED")
    receipt = {
        "schema": 1, "status": "PASS_G10A_NINE_PUBLISHED_NATIVE_SMOKE_ONLY",
        "stages": stages,
        "source_published_candidate": NEW[0],
        "published_package_sha256": NEW[1],
        "published_installer_sha256": INSTALLER_SHA,
        "original_stable_predecessor_was_stopped": True,
        "original_stable_running_upgrade_tested": False,
        "complete_functional_regression_twice_tested": False,
        "all_A01_A22_live_acceptance_tested": False,
        "used_disposable_file_pkg_repository": False,
        "native_GUI_server_uninstall_menu": True,
        "local_installed_purger_self_deleted": True,
        "owner_appliance_modified": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print("G10A_NINE_PUBLISHED_NATIVE=" + json.dumps(receipt, sort_keys=True), flush=True)

def self_test():
    need(OLD[0] != NEW[0] and
         all(re.fullmatch("[0-9a-f]{64}", x) for x in (OLD[1], NEW[1], INSTALLER_SHA))
         and "G11PublishedAcceptance" in str(historical.REPOFILE),
         "NINE_PUBLISHED_PINS_OR_BOUNDARY_INVALID")
    print("PASS_G10A_NINE_PUBLISHED_SOURCE_SHAPES=1")

if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif not sys.argv[1:]:
            run()
        else:
            raise Refusal("UNKNOWN_ARGUMENTS")
    except (Refusal, historical.Refusal, firmware.GateFailure, OSError,
            ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        print("G10A_NINE_PUBLISHED_NATIVE=REFUSED:" + str(exc)[:180], file=sys.stderr)
        sys.exit(2)
