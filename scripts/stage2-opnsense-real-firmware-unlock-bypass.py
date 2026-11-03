#!/usr/bin/env python3
"""Disposable OPNsense 26.7 only: stock configd firmware Unlock bypass of pkg lock.

An investigative native pkg hazard witness, NOT an updater, Web UI click proof,
or a product transaction-safety acceptance. Never run on owner hardware.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REVISION = "82"
OPTIN = "ZAPRET2_STAGE2_REAL_FIRMWARE_UNLOCK_BYPASS"
NAME = "os-zapret2-restyle"

def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".", "_"), HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

locked = load("stage2-opnsense-real-locked-unsafe-owner.py")
unsafe, stopped, native, clean, old = (locked.unsafe, locked.stopped,
                                      locked.native, locked.clean, locked.old)
foreign, firmware = locked.foreign, locked.firmware

class Refusal(Exception):
    pass

def need(condition, reason):
    if not condition:
        raise Refusal(reason)

def qualify():
    need(os.geteuid() == 0 and os.environ.get("GITHUB_ACTIONS") == "true"
         and os.environ.get(OPTIN) == "1"
         and os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1"
         and os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "DISPOSABLE_STOCK_FIRMWARE_UNLOCK_OPTIN_REQUIRED")
    native.gate()
    need(all(module.REVISION == REVISION for module in
             (locked, unsafe, stopped, native, clean)),
         "CURRENT_NATIVE_SOURCE_REVISION_MISMATCH")

def package_locked():
    """Query the exact installed package metadata, not list exit semantics."""
    result = locked.pkg(["query", "%k", NAME])
    value = result.stdout.strip()
    need(result.returncode == 0 and value in ("0", "1"),
         "TARGET_PACKAGE_LOCK_METADATA_UNAVAILABLE")
    return value == "1"

def wait_until_unlocked(predicate, *, attempts=80, delay=0.25, sleep=time.sleep):
    """Bounded polling: stock configd firmware action launches via daemon -f."""
    need(attempts >= 1 and attempts <= 80 and delay >= 0 and delay <= 0.25,
         "UNBOUNDED_UNLOCK_POLL")
    for _ in range(attempts):
        if not predicate():
            return True
        sleep(delay)
    return False

def classify_unlock_bypass(was_locked, unlocked, pkg_exit, old_id, new_id,
                           after_id, authentic_hook_refusal, state_unchanged):
    need(was_locked and unlocked and state_unchanged,
         "UNLOCK_PRE_PKG_STATE_NOT_PROVEN")
    need(authentic_hook_refusal, "AUTHENTIC_PREINSTALL_REFUSAL_NOT_OBSERVED")
    need(pkg_exit == 0 and after_id == new_id and old_id != new_id,
         "NO_NATIVE_REPLACEMENT_AFTER_STOCK_UNLOCK")
    return "OBSERVED_STOCK_CONFIGD_UNLOCK_THEN_UNSAFE_NATIVE_PKG_REPLACEMENT"

def execute(archive):
    qualify()
    clean.plugin_absent()
    stopped.check_old_archive(archive)
    built = native.build()
    need(built["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY"
         and built["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "NATIVE_SUCCESSOR_NOT_QUALIFIED")
    successor = native.ROOT / built["output"]
    successor_sha = built["real_native_pkg"]["sha256"]
    need(successor.is_file() and not successor.is_symlink()
         and clean.digest(successor) == successor_sha,
         "NATIVE_SUCCESSOR_SHA_MISMATCH")
    installer = stopped.load("stage0-opnsense-installed-predecessor.py")
    need(installer.install_and_verify(archive)["status"]
         == "PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE",
         "GENUINE_PREDECESSOR_NOT_QUALIFIED")
    inspector = stopped.load("stage0-opnsense-prepkg-readonly.py")
    need(inspector.snapshot(archive)["status"]
         == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY",
         "OLD_COLD_STATUS_UNQUALIFIED")
    route = firmware.read_only_audit()
    need(route["status"] == "PASS_READ_ONLY_FIRMWARE_ROUTE_CLASSIFICATION"
         and not route["stock_firmware_paths_accepted_as_safe_updates"],
         "STOCK_FIRMWARE_ACTION_SOURCE_UNQUALIFIED")
    before_id = NAME + "|0.6.2_1"
    after_id = NAME + "|" + native.VERSION + "_" + REVISION
    need(unsafe.installed_identity() == before_id, "WRONG_OLD_PKGDB_IDENTITY")
    old_service_sha = clean.digest(Path(old.SERVICE))
    config_before = Path("/conf/config.xml").read_bytes()
    need(all(not p.exists() and not p.is_symlink() for p in inspector.MARKERS),
         "PREEXISTING_RESTART_MARKER")

    foreign.activate_kernel(inspector)
    injected = False
    observed = {}
    try:
        unsafe.add_test_orphan()
        injected = True
        status = foreign.command(str(old.SERVICE), "status")
        need(status.returncode == 2 and unsafe.only_orphan_loopback_divert(),
             "OLD_STATUS_2_OR_ORPHAN_NOT_CONFIRMED")
        lock_result = locked.pkg(["lock", "-y", NAME])
        need(lock_result.returncode == 0 and locked.locked() and package_locked(),
             "REAL_INSTALLED_OLD_LOCK_UNAVAILABLE")
        pkg_before = locked.installed_record()
        need(unsafe.installed_identity() == before_id,
             "OLD_IDENTITY_CHANGED_AFTER_LOCK")
        unlock = clean.run(["/usr/local/sbin/configctl", "firmware", "unlock",
                            NAME], timeout=30)
        # A zero configctl exit is just command submission, not unlock proof.
        need(unlock.returncode == 0, "CONFIGD_STOCK_UNLOCK_SUBMISSION_FAILED")
        unlocked = wait_until_unlocked(package_locked)
        need(unlocked and not package_locked(),
             "STOCK_CONFIGD_UNLOCK_NOT_OBSERVED")
        before_pkg_unchanged = (
            locked.installed_record() == pkg_before
            and unsafe.installed_identity() == before_id
            and clean.digest(Path(old.SERVICE)) == old_service_sha
            and Path("/conf/config.xml").read_bytes() == config_before
            and all(not p.exists() and not p.is_symlink() for p in inspector.MARKERS)
            and unsafe.only_orphan_loopback_divert()
            and foreign.command(str(old.SERVICE), "status").returncode == 2
            and clean.digest(successor) == successor_sha)
        need(before_pkg_unchanged, "STOCK_UNLOCK_MUTATED_UNRELATED_PKG_STATE")
        actual = locked.pkg(["add", "-f", str(successor)], timeout=230)
        installed = unsafe.installed_identity()
        out = actual.stdout + "\n" + actual.stderr
        refused = any(token in out for token in
                      ("incomplete zapret lifecycle",
                       "cannot determine zapret service state",
                       "controlled recovery before package replacement"))
        observed = {
            "schema": 1,
            "real_configd_firmware_unlock_exit": unlock.returncode,
            "old_status_with_orphan": status.returncode,
            "old_pkgdb_unchanged_after_unlock": before_pkg_unchanged,
            "old_metadata_lock_removed_by_stock_action": unlocked,
            "native_pkg_add_exit": actual.returncode,
            "installed_after_pkg": installed,
            "authentic_incoming_preinstall_refusal": refused,
            "config_bytes_unchanged_after_pkg":
                Path("/conf/config.xml").read_bytes() == config_before,
            "test_owned_orphan_preserved": unsafe.only_orphan_loopback_divert(),
            "original_service_sha256": old_service_sha,
            "original_published_archive_sha256": old.ARCHIVE_SHA,
            "successor_pkg_sha256": successor_sha,
            "successor_archive_unchanged": clean.digest(successor) == successor_sha,
        }
        print("STAGE2_CONFIGD_UNLOCK_PRE_CLEANUP="
              + json.dumps(observed, sort_keys=True), flush=True)
        need(observed["test_owned_orphan_preserved"]
             and observed["successor_archive_unchanged"],
             "KERNEL_OR_ARCHIVE_CHANGED_BY_STOCK_UNLOCK_OR_PKG")
        verdict = classify_unlock_bypass(
            True, unlocked, actual.returncode, before_id, after_id,
            installed, refused, before_pkg_unchanged)
    finally:
        if injected:
            unsafe.remove_test_orphan()
        state = foreign.command("/sbin/ipfw", "-q", "list")
        need(state.returncode == 0 and foreign.only_default(state.stdout),
             "TEST_OWNED_ORPHAN_CLEANUP_FAILED")
        # Do not reset firmware/pkg/Config and do not unload modules;
        # this one-use guest is disposed. No unrelated resources are touched.
    return {
        "schema": 1, "status": "PASS_STOCK_CONFIGD_UNLOCK_BYPASS_HAZARD_ONLY",
        "verdict": verdict, "measured": observed,
        "real_stock_configd_backend_action_tested": True,
        "browser_web_gui_click_tested": False,
        "pkg_lock_is_fd9_atomic_admission": False,
        "lh08_ac11_safe_upgrade_accepted": False,
        "owner_appliance_modified": False, "package_published": False,
        "test_orphan_removed": True
    }

def main():
    if len(sys.argv) != 2:
        print("STAGE2_CONFIGD_UNLOCK=REFUSED:OLD_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        report = execute(Path(sys.argv[1]))
    except (Refusal, locked.Refusal, unsafe.Refusal, stopped.Refusal,
            clean.Refusal, native.Refusal, foreign.Refusal, firmware.Refusal,
            old.Refusal, OSError, KeyError, ValueError, TypeError) as error:
        print("STAGE2_CONFIGD_UNLOCK=REFUSED:" + str(error), file=sys.stderr)
        return 2
    print("STAGE2_CONFIGD_UNLOCK=" + json.dumps(report, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
