#!/usr/bin/env python3
"""Disposable real OPNsense 26.7 only: native pkg lock versus orphaned IPFW.

This is a hazard/mitigation measurement, NOT an atomic updater or root veto.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REVISION = "76"
OPTIN = "ZAPRET2_STAGE2_REAL_LOCKED_UNSAFE_OWNER_PKG"
NAME = "os-zapret2-restyle"

def load(file):
    spec = importlib.util.spec_from_file_location(
        file.replace("-", "_").replace(".", "_"), HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

unsafe = load("stage2-opnsense-real-unsafe-owner-replacement.py")
stopped, native, clean, old = unsafe.stopped, unsafe.native, unsafe.clean, unsafe.old
foreign = unsafe.foreign
firmware = load("stage0-opnsense-firmware-admission.py")

class Refusal(Exception):
    pass

def need(ok, why):
    if not ok:
        raise Refusal(why)

def qualify():
    need(os.geteuid() == 0 and os.environ.get("GITHUB_ACTIONS") == "true"
         and os.environ.get(OPTIN) == "1"
         and os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1"
         and os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "DISPOSABLE_LOCKED_PKG_EXPERIMENT_OPTIN_REQUIRED")
    native.gate()
    need(all(m.REVISION == REVISION for m in (unsafe, stopped, native, clean)),
         "CURRENT_NATIVE_SOURCE_REVISION_MISMATCH")

def pkg(args, timeout=40):
    return clean.run(["pkg", "-o", "REPO_AUTOUPDATE=false", *args],
                     timeout=timeout)

def locked():
    result = pkg(["lock", "-l"])
    need(result.returncode == 0, "PKG_LOCK_LIST_UNAVAILABLE")
    return any(line.strip() == NAME or line.strip().startswith(NAME + "-")
               for line in result.stdout.splitlines())

def installed_record():
    result = pkg(["info", "-R", "--raw-format", "json", NAME])
    need(result.returncode == 0 and result.stdout.strip().startswith("{"),
         "PKGDB_RAW_RECORD_UNAVAILABLE")
    return result.stdout

def classify_locked_refusal(exit_code, before, after, is_locked, unchanged):
    need(is_locked, "NATIVE_LOCK_NOT_PRESERVED")
    need(exit_code != 0, "NATIVE_PKG_SUCCESS_DESPITE_LOCK")
    need(before == after, "PKGDB_CHANGED_DESPITE_LOCK")
    need(unchanged, "FILES_OR_CONFIG_OR_IPFW_CHANGED_DESPITE_LOCK")
    return "LOCKED_REAL_PACKAGE_FORCE_ADD_REFUSED_AND_UNCHANGED"

def execute(archive):
    qualify()
    clean.plugin_absent()
    stopped.check_old_archive(archive)
    built = native.build()
    need(built["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY"
         and built["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "UNQUALIFIED_NATIVE_SUCCESSOR")
    successor = native.ROOT / built["output"]
    successor_sha = built["real_native_pkg"]["sha256"]
    need(successor.is_file() and not successor.is_symlink()
         and clean.digest(successor) == successor_sha, "UNQUALIFIED_ARCHIVE_SHA")
    installer = stopped.load("stage0-opnsense-installed-predecessor.py")
    need(installer.install_and_verify(archive)["status"]
         == "PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE",
         "OLD_INSTALLED_PROVENANCE_UNQUALIFIED")
    inspector = stopped.load("stage0-opnsense-prepkg-readonly.py")
    need(inspector.snapshot(archive)["status"] == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
         "OLD_COLD_OWNER_NOT_PROVEN")
    route = firmware.read_only_audit()
    need(route["status"] == "PASS_READ_ONLY_FIRMWARE_ROUTE_CLASSIFICATION"
         and route["stock_firmware_paths_accepted_as_safe_updates"] is False,
         "FIRMWARE_OWNER_ADMISSION_MISCLASSIFIED")
    need(unsafe.installed_identity() == NAME + "|0.6.2_1",
         "OLD_PKGDB_IDENTITY_WRONG")
    service_sha = clean.digest(Path(old.SERVICE))
    config_before = Path("/conf/config.xml").read_bytes()
    need(all(not x.exists() and not x.is_symlink() for x in inspector.MARKERS),
         "PREEXISTING_RESTART_MARKER")
    foreign.activate_kernel(inspector)
    injected = False
    was_locked = False
    pkg_rc = None
    verdict = None
    try:
        unsafe.add_test_orphan()
        injected = True
        status = foreign.command(str(old.SERVICE), "status")
        need(status.returncode == 2 and unsafe.only_orphan_loopback_divert(),
             "AUTHENTIC_OLD_STATUS_NOT_UNSAFE")
        attempt_lock = pkg(["lock", "-y", NAME])
        need(attempt_lock.returncode == 0 and locked(),
             "REAL_INSTALLED_OLD_PKG_NOT_LOCKED")
        was_locked = True
        before = installed_record()
        need(unsafe.installed_identity() == NAME + "|0.6.2_1",
             "OLD_PKG_IDENTITY_CHANGED_ON_LOCK")
        result = pkg(["add", "-f", str(successor)], timeout=230)
        pkg_rc = result.returncode
        after = installed_record()
        unchanged = (unsafe.installed_identity() == NAME + "|0.6.2_1"
                     and clean.digest(Path(old.SERVICE)) == service_sha
                     and Path("/conf/config.xml").read_bytes() == config_before
                     and all(not x.exists() and not x.is_symlink()
                             for x in inspector.MARKERS)
                     and unsafe.only_orphan_loopback_divert()
                     and clean.digest(successor) == successor_sha)
        print("STAGE2_LOCKED_PKG_PRE_CLEANUP=" + json.dumps({
            "pkg_rc": pkg_rc, "authentic_old_status_rc": status.returncode,
            "pkgdb_unchanged": before == after,
            "critical_files_config_markers_ipfw_unchanged": unchanged,
            "still_locked": locked(),
        }, sort_keys=True), flush=True)
        verdict = classify_locked_refusal(pkg_rc, before, after, locked(), unchanged)
    finally:
        if injected:
            unsafe.remove_test_orphan()
        remaining = foreign.command("/sbin/ipfw", "-q", "list")
        need(remaining.returncode == 0 and foreign.only_default(remaining.stdout),
             "TEST_IPFW_NOT_CLEANED")
        # Deliberately do not unlock old package; VM is disposed.
    need(was_locked and locked(), "PACKAGE_LOCK_NOT_RETAINED")
    need(foreign.command(str(old.SERVICE), "status").returncode == 1,
         "OLD_STATUS_NOT_STOPPED_AFTER_CLEANUP")
    return {
        "schema": 1, "status": "PASS_REAL_LOCKED_OLD_PACKAGE_NEGATIVE_ONLY",
        "verdict": verdict, "old_package": NAME + "-0.6.2_1",
        "successor": NAME + "-0.6.2_" + REVISION,
        "old_archive_sha256": old.ARCHIVE_SHA,
        "native_successor_sha256": successor_sha,
        "real_pkg_exit": pkg_rc, "old_status_with_orphan": 2,
        "native_package_lock_held": True, "old_package_and_config_unchanged": True,
        "test_owned_orphan_removed": True,
        "stock_firmware_owner_admission_proven": False,
        "root_can_unlock_and_bypass": True,
        "fd9_atomic_admission_proven": False,
        "safe_product_upgrade_accepted": False,
        "owner_appliance_modified": False, "package_published": False,
    }

def main():
    if len(sys.argv) != 2:
        print("STAGE2_LOCKED_PKG=REFUSED:OLD_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        report = execute(Path(sys.argv[1]))
    except (Refusal, unsafe.Refusal, stopped.Refusal, clean.Refusal,
            native.Refusal, foreign.Refusal, firmware.Refusal,
            old.Refusal, OSError, KeyError, ValueError, TypeError) as exc:
        print("STAGE2_LOCKED_PKG=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE2_LOCKED_PKG=" + json.dumps(report, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
