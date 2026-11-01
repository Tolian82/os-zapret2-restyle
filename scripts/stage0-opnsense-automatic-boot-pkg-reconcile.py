#!/usr/bin/env python3
"""Stage 0 ONLY: automatic OPNsense start-syshook synthetic pkg reconciliation.

Disposable OPNsense 26.7 QEMU clean reboot. The guest automatically invokes
a test-owned OPNsense rc.syshook.d/start file on its NEW kernel boot.
Exactly ONE unchanged, separately named private synthetic pkgdb fixture can
be re-locked. Absent, tampered and genuinely unknown old-owner cases REFUSE.
Original published installed os-zapret2-restyle-0.6.2_1 is READ-ONLY.
No real plugin pkg mutation, production boot hook, power-loss or root exclusion.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path("/root/stage0-fresh-process-recovery-v0.6.2_45")
CODE_DIR = ROOT / "boot-code"
AUTO_HOOK = Path("/usr/local/etc/rc.syshook.d/start/98-zapret2-stage0-synthetic-reconcile")
AUTO_RESULT = ROOT / "automatic-boot-reconcile.json"
CODE_MANIFEST = ROOT / "boot-code-manifest.json"
SCENARIOS = ("unchanged", "direct_delete", "tampered_intent", "unknown_owner")
SOURCE_FILES = (
    "stage0-opnsense-automatic-boot-pkg-reconcile.py",
    "stage0-opnsense-real-boot-pkg-recovery.py",
    "stage0-opnsense-pkg-fresh-recovery.py",
    "stage0-opnsense-prepkg-readonly.py",
    "stage0-opnsense-native-pkg-lock.py",
    "stage0-opnsense-pkg-relock-failures.py",
    "stage0-opnsense-pkg-orphaned-unlock.py",
    "stage0-installed-predecessor-readonly.py",
    "stage0-opnsense-old-service-fd9.py",
    "stage0-opnsense-old-unknown-owner.py",
    "stage0-opnsense-old-deinstall.py",
    "stage0-opnsense-guest-readonly.py",
    "stage0-opnsense-installed-predecessor.py",
    "stage0-opnsense-pkg-sidecar-bypass.py",
)
HOOK_BYTES = (
    "#!/bin/sh\n"
    "# Disposable Stage 0 ONLY: synthetic pkgdb. Never install on owner gateway.\n"
    "set -eu\n"
    "/usr/local/bin/python3 " +
    str(CODE_DIR / "stage0-opnsense-automatic-boot-pkg-reconcile.py") +
    " boot > " + str(ROOT / "auto-start-hook.log") + " 2>&1\n"
).encode("ascii")


class Refusal(Exception):
    pass


def require(condition, why):
    if not condition:
        raise Refusal(why)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_").replace(".", "_"), HERE / name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def require_unchanged_boot(record, now):
    require(isinstance(record, dict) and
            record.get("schema") == 1 and
            record.get("experiment") == "private-pkgdb-opnsense-real-boot-only" and
            record.get("synthetic_name") ==
            "zapret2-stage0-sidecar-only-fixture" and
            record.get("scenarios") == ["unchanged", "direct_delete", "tampered_intent"],
            "PRIOR_DISPOSABLE_BOOT_RECORD_UNQUALIFIED")
    require(isinstance(now, str) and now.strip() and
            now != record.get("prepared_kern_boottime"),
            "AUTO_START_REAL_KERNEL_BOOT_NOT_PROVEN")
    return True


def copied_code_digest():
    require(CODE_DIR.is_dir() and not CODE_DIR.is_symlink() and
            CODE_DIR.stat().st_uid == 0 and
            stat.S_IMODE(CODE_DIR.stat().st_mode) == 0o700,
            "BOOT_CODE_DIRECTORY_NOT_OWNED")
    entries = json.loads(qualified(CODE_MANIFEST).decode())
    require(set(entries) == set(SOURCE_FILES), "BOOT_CODE_MANIFEST_MISMATCH")
    for filename in SOURCE_FILES:
        code = CODE_DIR / filename
        st = code.lstat()
        require(stat.S_ISREG(st.st_mode) and not code.is_symlink() and
                st.st_uid == 0 and stat.S_IMODE(st.st_mode) == 0o600,
                "BOOT_CODE_SOURCE_UNTRUSTED:" + filename)
        require(hashlib.sha256(code.read_bytes()).hexdigest() == entries[filename],
                "BOOT_CODE_HASH_CHANGED:" + filename)
    return True


def qualified(path, mode=0o600):
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and not path.is_symlink() and
            st.st_uid == 0 and stat.S_IMODE(st.st_mode) == mode,
            "DISPOSABLE_ROOT_FILE_UNTRUSTED:" + str(path))
    return path.read_bytes()


def require_old_cold(boot45, installed, guard):
    original = boot45.verify_original(boot45.ARCHIVE, installed, guard)
    require(original.get("status") == "PASS_READ_ONLY_PROVENANCE" and
            original.get("package") == "os-zapret2-restyle-0.6.2_1",
            "AUTHENTIC_OLD_OWNER_NOT_PROVEN")
    return original


def prepare(boot45, native, locks, orphan, fresh, fixture, guest, installed, guard):
    boot45.root_guest()
    # Existing Stage 0.13 prepares REAL original installed package and three
    # private synthetics in a disposable guest; syshook #99 is read-only.
    base = boot45.prepare(guest, installed, guard, native, locks, orphan,
                          fixture, fresh)
    require(base["status"] == "READY_FOR_ACTION_MANAGED_REAL_OPNSENSE_GUEST_REBOOT",
            "STAGE_45_PREPARE_NOT_QUALIFIED")
    require(not AUTO_RESULT.exists() and not AUTO_RESULT.is_symlink() and
            not AUTO_HOOK.exists() and not AUTO_HOOK.is_symlink() and
            not CODE_MANIFEST.exists() and not CODE_MANIFEST.is_symlink(),
            "EXPERIMENT_ARTIFACT_ALREADY_EXISTS")
    CODE_DIR.mkdir(mode=0o700)
    manifest = {}
    for name in SOURCE_FILES:
        source = HERE / name
        require(source.is_file() and not source.is_symlink(),
                "DISPOSABLE_SOURCE_MISSING:" + name)
        data = source.read_bytes()
        boot45.write_exclusive(CODE_DIR / name, data, 0o600)
        manifest[name] = hashlib.sha256(data).hexdigest()
    boot45.write_exclusive(CODE_MANIFEST, (json.dumps(manifest, sort_keys=True) +
                                          "\n").encode())
    copied_code_digest()
    # Make deliberately unsafe synthetic cases BEFORE the guest actually
    # powers off. No direct pkg on actual os-zapret2-restyle here.
    for name in ("direct_delete", "tampered_intent"):
        scope = ROOT / name
        pkg, env = fresh.private_pkg(scope)
        if name == "direct_delete":
            removed = native.call(pkg + ["delete", "-y", fresh.NAME], env)
            require(removed.returncode == 0 and
                    locks.fixture_state(native, pkg, env, scope / "payload" / "fixture")
                    == ("ABSENT", None),
                    "PREBOOT_PRIVATE_DELETE_NOT_OBSERVED")
        else:
            path = scope / "pending-unlock.json"
            value = json.loads(qualified(path).decode())
            value["package"] = "untrusted-synthetic-name"
            with path.open("w", encoding="utf-8") as out:
                json.dump(value, out, sort_keys=True)
                out.write("\n")
                out.flush()
                os.fsync(out.fileno())
    # Add fourth, unchanged unlocked synthetic package; old owner will be
    # made deliberately ambiguous ONLY in its one boot-time negative case.
    scope = ROOT / "unknown_owner"
    scope.mkdir(mode=0o700)
    pkg, env, marker = fresh.make_private_fixture(scope, native, fixture, locks)
    orphan.durable_intent(scope / "pending-unlock.json", scope / "pkgdb")
    child = orphan.kill_owned_child_after_unlock(env)
    require(child["child_exit_signal"] == "SIGKILL" and
            not locks.is_locked(native, pkg, env) and
            locks.fixture_state(native, pkg, env, marker) == (fresh.OLD, fresh.PAYLOAD),
            "PREBOOT_UNKNOWN_OWNER_FIXTURE_NOT_UNLOCKED")
    require_old_cold(boot45, installed, guard)
    boot45.write_exclusive(AUTO_HOOK, HOOK_BYTES, 0o755)
    require(qualified(AUTO_HOOK, 0o755) == HOOK_BYTES,
            "AUTOMATIC_START_HOOK_BYTES_INVALID")
    return {
        "status": "PREPARED_AUTOMATIC_START_SYSHOOK_RECONCILIATION",
        "initial_real_original_pkg": "os-zapret2-restyle-0.6.2_1",
        "private_scenario_count": len(SCENARIOS),
        "four_private_native_pkgdb_scopes": True,
        "auto_hook_will_run_during_next_os_boot": True,
        "real_os_boot_yet_verified": False,
        "production_owner_guard_implemented": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def recover_one(name, fresh, boot45, installed, guard, native, locks, orphan):
    scope = ROOT / name
    require_old_cold(boot45, installed, guard)
    try:
        value = fresh.recover(scope, boot45.ARCHIVE, guard, native, locks, orphan)
    except (fresh.Refusal, locks.Refusal, orphan.Refusal) as exc:
        return {"status": "REFUSED", "reason": str(exc)}
    require(value["status"] in ("RECOVERED_UNCHANGED_PRIVATE_FIXTURE",
                                "ALREADY_LOCKED_UNCHANGED_PRIVATE_FIXTURE"),
            "RECOVERY_RETURNED_UNKNOWN_SUCCESS:" + name)
    return {"status": value["status"]}


def auto_start(boot45, installed, guard, native, locks, orphan, fresh, unknown):
    boot45.root_guest()
    boot45.root_scope()
    require(not AUTO_RESULT.exists() and not AUTO_RESULT.is_symlink(),
            "AUTOMATIC_BOOT_RESULT_EXISTS")
    require(qualified(AUTO_HOOK, 0o755) == HOOK_BYTES,
            "AUTOMATIC_SYSHOOK_NOT_IDENTICAL")
    copied_code_digest()
    prior = json.loads(qualified(boot45.RECORD).decode())
    now = boot45.boot_id()
    require_unchanged_boot(prior, now)
    require_old_cold(boot45, installed, guard)
    results = {}
    for name in SCENARIOS:
        if name != "unknown_owner":
            results[name] = recover_one(name, fresh, boot45, installed,
                                        guard, native, locks, orphan)
            if name == "unchanged":
                require(results[name]["status"] == "RECOVERED_UNCHANGED_PRIVATE_FIXTURE",
                        "AUTOMATIC_BOOT_UNCHANGED_NOT_RELOCKED")
            if name == "direct_delete":
                require(results[name] == {
                    "status": "REFUSED",
                    "reason": "REFUSE_CHANGED_OR_MISSING_PRIVATE_FIXTURE",
                }, "AUTOMATIC_BOOT_MISSING_PKG_NOT_REFUSED")
            if name == "tampered_intent":
                require(results[name] == {
                    "status": "REFUSED",
                    "reason": "DURABLE_RECORD_IDENTITY_NOT_QUALIFIED",
                }, "AUTOMATIC_BOOT_TAMPERED_INTENT_NOT_REFUSED")
            continue
        created_parent = False
        created_journal = False
        try:
            created_parent = unknown.create_disposable_root_if_absent()
            created_journal = unknown.create_owned_corrupt_journal()
            unknown.verify_corrupt_journal()
            try:
                fresh.original_cold(guard, boot45.ARCHIVE)
            except fresh.Refusal as exc:
                reason = str(exc)
            else:
                raise Refusal("UNKNOWN_GENUINE_OWNER_NOT_REFUSED")
            require(reason.startswith(
                "ORIGINAL_OWNER_SNAPSHOT_REFUSED:UNVERIFIED_JOURNAL_MARKER_OR_PIDFILE:"),
                "WRONG_UNKNOWN_GENUINE_OWNER_DIAGNOSTIC")
            # The same verified refusal before touching the synthetic package.
            try:
                fresh.recover(ROOT / name, boot45.ARCHIVE, guard,
                              native, locks, orphan)
            except fresh.Refusal as exc:
                require(str(exc) == reason,
                        "DIFFERENT_UNKNOWN_OWNER_BOOT_RECOVERY_REFUSAL")
            else:
                raise Refusal("UNKNOWN_OWNER_PRIVATE_FIXTURE_LOCKED")
            results[name] = {"status": "REFUSED", "reason": reason}
        finally:
            if created_journal:
                unknown.remove_only_owned_journal()
            if created_parent:
                unknown.JOURNAL.parent.rmdir()
        require_old_cold(boot45, installed, guard)
    require(results["unchanged"]["status"] == "RECOVERED_UNCHANGED_PRIVATE_FIXTURE",
            "NO_AUTOMATIC_POSITIVE_RESULT")
    report = {
        "schema": 1,
        "status": "AUTO_START_PRIVATE_PKG_RECONCILIATION_BOUNDED_PASS",
        "actual_boot_kernel_id": now,
        "run_during_opnsense_rc_syshook_start": True,
        "scenarios": results,
        "real_original_published_pkg_unchanged": True,
        "only_synthetic_unchanged_package_relocked": True,
        "absent_tampered_unknown_owner_refused": True,
        "test_owned_unknown_journal_cleaned": True,
        "automatic_boot_reconciliation_only_for_private_fixture": True,
        "system_power_loss_tested": False,
        "production_boot_service_installed": False,
        "direct_root_pkg_exclusion_proved": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }
    # Once-per-boot fsynced durable witness, not a global service state.
    boot45.write_exclusive(AUTO_RESULT, (json.dumps(report, sort_keys=True) +
                                        "\n").encode())
    return report


def verify_after(boot45, installed, guard, native, locks, orphan, fresh):
    boot45.root_guest()
    boot45.root_scope()
    copied_code_digest()
    expected = json.loads(qualified(AUTO_RESULT).decode())
    require(expected.get("status") ==
            "AUTO_START_PRIVATE_PKG_RECONCILIATION_BOUNDED_PASS" and
            expected.get("run_during_opnsense_rc_syshook_start") is True and
            expected.get("only_synthetic_unchanged_package_relocked") is True and
            expected.get("absent_tampered_unknown_owner_refused") is True,
            "AUTOMATIC_START_SYSHOOK_REPORT_NOT_PROVEN")
    prior = json.loads(qualified(boot45.RECORD).decode())
    now = boot45.boot_id()
    boot45.verify_boot_transition(prior["prepared_kern_boottime"],
                                  now,
                                  qualified(boot45.BOOT_MARKER).decode().strip())
    require(expected["actual_boot_kernel_id"] == now,
            "AUTO_BOOT_SYSHOOK_RAN_IN_DIFFERENT_KERNEL")
    require_old_cold(boot45, installed, guard)
    for name in SCENARIOS:
        scope = ROOT / name
        fresh.scope_root(scope)
        pkg, env = fresh.private_pkg(scope)
        actual = locks.fixture_state(native, pkg, env, scope / "payload" / "fixture")
        locked = locks.is_locked(native, pkg, env)
        if name == "unchanged":
            require(actual == (fresh.OLD, fresh.PAYLOAD) and locked,
                    "AUTOMATIC_RELOCKED_SYNTHETIC_FIXTURE_NOT_PERSISTENT")
            native_delete = native.call(pkg + ["delete", "-y", fresh.NAME], env)
            require(native_delete.returncode != 0 and
                    locks.fixture_state(native, pkg, env, scope / "payload" / "fixture")
                    == (fresh.OLD, fresh.PAYLOAD),
                    "DIRECT_PKG_DELETE_BYPASSED_AUTOMATIC_RELOCK")
            expected["postboot_locked_delete_rc"] = native_delete.returncode
        if name == "direct_delete":
            require(actual == ("ABSENT", None) and not locked,
                    "AUTOMATIC_ABSENT_PACKAGE_MUTATED")
        if name in ("tampered_intent", "unknown_owner"):
            require(actual == (fresh.OLD, fresh.PAYLOAD) and not locked,
                    "AUTOMATIC_NEGATIVE_FIXTURE_WAS_MUTATED")
    require(qualified(AUTO_HOOK, 0o755) == HOOK_BYTES,
            "AUTOMATIC_BOOT_HOOK_CHANGED")
    AUTO_HOOK.unlink()
    require(not AUTO_HOOK.exists() and not AUTO_HOOK.is_symlink(),
            "AUTOMATIC_SYSHOOK_NOT_REMOVED")
    require(qualified(boot45.SYSHOOK, 0o755) == boot45.BOOT_HOOK_BYTES,
            "PRIOR_BOOT_WITNESS_HOOK_CHANGED")
    boot45.SYSHOOK.unlink()
    require(not boot45.SYSHOOK.exists(), "BOOT_WITNESS_HOOK_NOT_REMOVED")
    require_old_cold(boot45, installed, guard)
    return {
        "schema": 1,
        "status": "OBSERVED_GENUINE_OPNSENSE_BOOT_AUTOMATIC_PRIVATE_RECONCILIATION",
        "actual_guest_boot_changed": True,
        "automatic_syshook_recovery_executed_before_explicit_verify": True,
        "automatic_positive_native_private_pkg_lock_persisted": True,
        "automated_native_direct_delete_refusal_rc":
            expected["postboot_locked_delete_rc"],
        "automatic_absent_tampered_unknown_owner_refusals_verified": True,
        "auto_syshook_removed": True,
        "test_only_boot_witness_removed": True,
        "original_published_package_unchanged": True,
        "actual_power_loss_tested": False,
        "production_owner_guard_implemented": False,
        "all_privileged_pkg_entrypoints_enforced": False,
        "real_running_or_foreign_ipfw_tested": False,
        "real_original_plugin_replaced": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def main():
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in ("prepare", "boot", "verify"),
                "EXACT_DISPOSABLE_PHASE_REQUIRED")
        boot45 = load("stage0-opnsense-real-boot-pkg-recovery.py")
        installed = load("stage0-opnsense-installed-predecessor.py")
        guard = load("stage0-opnsense-prepkg-readonly.py")
        native = load("stage0-opnsense-native-pkg-lock.py")
        locks = load("stage0-opnsense-pkg-relock-failures.py")
        orphan = load("stage0-opnsense-pkg-orphaned-unlock.py")
        fresh = load("stage0-opnsense-pkg-fresh-recovery.py")
        if sys.argv[1] == "prepare":
            data = prepare(boot45, native, locks, orphan, fresh,
                           load("stage0-opnsense-pkg-sidecar-bypass.py"),
                           load("stage0-opnsense-guest-readonly.py"),
                           installed, guard)
        elif sys.argv[1] == "boot":
            data = auto_start(boot45, installed, guard, native, locks,
                              orphan, fresh,
                              load("stage0-opnsense-old-unknown-owner.py"))
        else:
            data = verify_after(boot45, installed, guard, native, locks,
                                orphan, fresh)
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            json.JSONDecodeError) as exc:
        print("STAGE0_AUTO_BOOT=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_AUTO_BOOT=" + json.dumps(data, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
