#!/usr/bin/env python3
"""Stage 0: real disposable OPNsense reboot with private pkg lock orphan.

PREPARE runs before action-managed clean guest shutdown; VERIFY runs after
guest QEMU restart from the preserved prepared disk. A disposable boot
syshook writes ONLY a boot-time witness; recovery is explicitly invoked
AFTER boot in a separate interpreter (NOT automatic startup recovery).

Actual published Zapret2 0.6.2_1 is read-only identity/old Status evidence.
All native pkg mutations are on separate harmless private PKG_DBDIR fixtures.
No production package manager interception, actual power-loss, or user gateway.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path("/root/stage0-fresh-process-recovery-v0.6.2_45")
ARCHIVE = ROOT / "published-original-0.6.2_1.pkg"
RECORD = ROOT / "prepared-boot.json"
SYSHOOK_DIR = Path("/usr/local/etc/rc.syshook.d/start")
SYSHOOK = SYSHOOK_DIR / "99-zapret2-stage0-private-boot-witness"
BOOT_MARKER = ROOT / "start-syshook.boot-id"
SCENARIOS = ("unchanged", "direct_delete", "tampered_intent")
PKG_NAME = "zapret2-stage0-sidecar-only-fixture"
OLD = PKG_NAME + "|0.6.2_1"
OLD_BYTES = b"old\n"
BOOT_HOOK_BYTES = (
    "#!/bin/sh\n"
    "# Disposable Stage 0 syshook: emits only a guest boot witness.\n"
    "umask 077\n"
    'sysctl -n kern.boottime > "' + str(BOOT_MARKER) + '"\n'
).encode("ascii")


class Refusal(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".", "_").replace("-", "_"), HERE / name)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def root_guest():
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64", "ONLY_DISPOSABLE_ROOT_FREEBSD_AMD64")


def boot_id():
    try:
        p = subprocess.run(["sysctl", "-n", "kern.boottime"], timeout=20,
                           text=True, capture_output=True, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("KERN_BOOT_ID_QUERY_FAILED") from None
    require(p.returncode == 0 and p.stdout.strip() and not p.stderr.strip(),
            "KERN_BOOT_ID_NOT_OBSERVABLE")
    return p.stdout.strip()


def write_exclusive(path, data, mode=0o600):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_WRONLY,
                 mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    dirfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def qualified_file(path, expected_mode):
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and not path.is_symlink() and
            st.st_uid == 0 and stat.S_IMODE(st.st_mode) == expected_mode,
            "UNTRUSTED_DISPOSABLE_FILE:" + str(path))
    return path.read_bytes()


def root_scope():
    st = ROOT.lstat()
    require(stat.S_ISDIR(st.st_mode) and not ROOT.is_symlink() and
            st.st_uid == 0 and stat.S_IMODE(st.st_mode) == 0o700,
            "UNTRUSTED_DISPOSABLE_ROOT")
    return ROOT


def verify_original(archive, installed, guard):
    original = installed.pre
    host = original.run("hostname", "-s").decode().strip()
    evidence = original.run_guest(archive, host)
    require(evidence.get("status") == "PASS_READ_ONLY_PROVENANCE" and
            evidence.get("package") == "os-zapret2-restyle-0.6.2_1",
            "PUBLISHED_OLD_PKG_PROVENANCE_CHANGED")
    cold = guard.snapshot(archive)
    require(cold.get("status") == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
            cold.get("old_package") == "os-zapret2-restyle-0.6.2_1" and
            cold.get("real_old_status") == "STOPPED" and
            cold.get("safe_pkg_transaction_authorized") is False,
            "PUBLISHED_OLD_OWNER_NOT_COLD_AND_PROVEN")
    return evidence


def verify_boot_transition(previous, current, syshook_marker):
    """Require distinct real kernel boot sessions and matching OPNsense start."""
    require(isinstance(previous, str) and previous.strip() and
            isinstance(current, str) and current.strip() and
            isinstance(syshook_marker, str) and syshook_marker.strip(),
            "BOOT_WITNESS_EMPTY")
    require(current != previous,
            "ACTUAL_GUEST_REBOOT_NOT_PROVEN_SAME_KERN_BOOTTIME")
    require(syshook_marker == current,
            "OFFICIAL_OPNSENSE_START_SYSHOOK_NOT_RUN")
    return True


def prepare(guest, installed, guard, native, locks, orphan, fixture, fresh):
    root_guest()
    require(guest.evaluate(guest.observe()).get("status") ==
            "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
            "NOT_FRESH_DISPOSABLE_OPNSENSE")
    root_scope()
    require(qualified_file(ARCHIVE, 0o600), "PUBLISHED_ORIGINAL_ARCHIVE_MISSING")
    installed.install_and_verify(ARCHIVE)
    old = verify_original(ARCHIVE, installed, guard)
    for name in SCENARIOS:
        scope = ROOT / name
        scope.mkdir(mode=0o700)
        fresh.make_private_fixture(scope, native, fixture, locks)
        pkg, env = fresh.private_pkg(scope)
        marker = scope / "payload" / "fixture"
        require(locks.fixture_state(native, pkg, env, marker) ==
                (OLD, OLD_BYTES) and locks.is_locked(native, pkg, env),
                "BEFORE_BOOT_SYNTHETIC_FIXTURE_NOT_LOCKED")
        intent = scope / "pending-unlock.json"
        orphan.durable_intent(intent, scope / "pkgdb")
        require(orphan.read_intent(intent, scope / "pkgdb")["package"] ==
                PKG_NAME, "BEFORE_BOOT_DURABLE_INTENT_NOT_VERIFIED")
        guard.snapshot(ARCHIVE)
        child = orphan.kill_owned_child_after_unlock(env)
        require(child["killed_child_pid_only"] and
                child["child_native_unlock_completed"] and
                not locks.is_locked(native, pkg, env) and
                locks.fixture_state(native, pkg, env, marker) ==
                (OLD, OLD_BYTES), "BEFORE_BOOT_ORPHAN_UNLOCK_NOT_VERIFIED")
        verify_original(ARCHIVE, installed, guard)
    # The hook records only the OS start stage and never modifies pkg/IPFW.
    st = SYSHOOK_DIR.lstat()
    require(stat.S_ISDIR(st.st_mode) and not SYSHOOK_DIR.is_symlink() and
            st.st_uid == 0, "OFFICIAL_SYSHOOK_START_DIRECTORY_UNQUALIFIED")
    require(not SYSHOOK.exists() and not SYSHOOK.is_symlink(),
            "SYSHOOK_WOULD_OVERWRITE_FOREIGN_FILE")
    require(not BOOT_MARKER.exists() and not BOOT_MARKER.is_symlink(),
            "BOOT_MARKER_NOT_FRESH")
    write_exclusive(SYSHOOK, BOOT_HOOK_BYTES, 0o755)
    require(qualified_file(SYSHOOK, 0o755) == BOOT_HOOK_BYTES,
            "DISPOSABLE_BOOT_SYSHOOK_NOT_VERIFIED")
    record = {
        "schema": 1, "experiment": "private-pkgdb-opnsense-real-boot-only",
        "prepared_kern_boottime": boot_id(),
        "historical_original": old,
        "synthetic_name": PKG_NAME, "synthetic_version": OLD,
        "synthetic_payload_sha256": hashlib.sha256(OLD_BYTES).hexdigest(),
        "scenarios": list(SCENARIOS),
        "boot_hook_sha256": hashlib.sha256(BOOT_HOOK_BYTES).hexdigest(),
        "automatic_package_recovery_at_boot": False,
    }
    write_exclusive(RECORD, (json.dumps(record, sort_keys=True) + "\n").encode())
    require(qualified_file(RECORD, 0o600), "BOOT_PREPARED_RECORD_NOT_VERIFIED")
    return {
        "status": "READY_FOR_ACTION_MANAGED_REAL_OPNSENSE_GUEST_REBOOT",
        "real_published_original_package": old["package"],
        "synthetic_private_pkgdb_count": len(SCENARIOS),
        "owned_unlock_children_killed": True,
        "native_synthetic_packages_unlocked_before_reboot": True,
        "boot_hook_only_writes_boot_identity": True,
        "actual_opnsense_reboot_yet_proven": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def verify_after_reboot(installed, guard, native, locks, orphan, fresh):
    root_guest()
    root_scope()
    record = json.loads(qualified_file(RECORD, 0o600).decode())
    require(record.get("schema") == 1 and
            record.get("experiment") == "private-pkgdb-opnsense-real-boot-only" and
            record.get("synthetic_name") == PKG_NAME and
            record.get("synthetic_version") == OLD and
            record.get("synthetic_payload_sha256") ==
            hashlib.sha256(OLD_BYTES).hexdigest() and
            record.get("scenarios") == list(SCENARIOS) and
            record.get("boot_hook_sha256") ==
            hashlib.sha256(BOOT_HOOK_BYTES).hexdigest() and
            record.get("automatic_package_recovery_at_boot") is False,
            "BOOT_RECORD_IDENTITY_MISMATCH")
    prepare_boot = record["prepared_kern_boottime"]
    current_boot = boot_id()
    marker = qualified_file(BOOT_MARKER, 0o600).decode().strip()
    verify_boot_transition(prepare_boot, current_boot, marker)
    require(qualified_file(SYSHOOK, 0o755) == BOOT_HOOK_BYTES,
            "GUEST_BOOT_SYSHOOK_CHANGED")
    require(qualified_file(ARCHIVE, 0o600),
            "ORIGINAL_PUBLISHED_ARCHIVE_NOT_PERSISTENT")
    old = verify_original(ARCHIVE, installed, guard)
    require(old == record["historical_original"],
            "PUBLISHED_HISTORICAL_PREDECESSOR_CHANGED_ACROSS_BOOT")
    outcomes = {}
    for name in SCENARIOS:
        scope = ROOT / name
        fresh.scope_root(scope)
        pkg, env = fresh.private_pkg(scope)
        payload = scope / "payload" / "fixture"
        before = locks.fixture_state(native, pkg, env, payload)
        require(before == (OLD, OLD_BYTES) and
                not locks.is_locked(native, pkg, env),
                "ORPHAN_NOT_PERSISTENT_ACROSS_ACTUAL_REBOOT")
        if name == "direct_delete":
            deleted = native.call(pkg + ["delete", "-y", PKG_NAME], env)
            require(deleted.returncode == 0 and
                    locks.fixture_state(native, pkg, env, payload) ==
                    ("ABSENT", None), "POST_BOOT_DIRECT_PKG_DELETE_NOT_OBSERVED")
        if name == "tampered_intent":
            pending = scope / "pending-unlock.json"
            intent = json.loads(qualified_file(pending, 0o600))
            intent["package"] = "foreign-synthetic-name"
            pending.write_text(json.dumps(intent, sort_keys=True) + "\n",
                               encoding="utf-8")
        code, decision = fresh.invoke_fresh_recovery(scope, ARCHIVE)
        if name == "unchanged":
            require(code == 0 and decision["status"] ==
                    "RECOVERED_UNCHANGED_PRIVATE_FIXTURE",
                    "POST_REAL_BOOT_EXPLICIT_RECOVERY_NOT_PROVEN")
            require(locks.is_locked(native, pkg, env) and
                    locks.fixture_state(native, pkg, env, payload) ==
                    (OLD, OLD_BYTES), "POST_REAL_BOOT_NATIVE_RELOCK_NOT_VERIFIED")
            again, again_result = fresh.invoke_fresh_recovery(scope, ARCHIVE)
            require(again == 0 and again_result["status"] ==
                    "ALREADY_LOCKED_UNCHANGED_PRIVATE_FIXTURE",
                    "POST_REAL_BOOT_RECOVERY_NOT_IDEMPOTENT")
            rejected = native.call(pkg + ["delete", "-y", PKG_NAME], env)
            require(rejected.returncode != 0 and
                    locks.fixture_state(native, pkg, env, payload) ==
                    (OLD, OLD_BYTES), "RESTORED_PKG_DELETE_NOT_REFUSED")
            outcomes[name] = {"recovery": decision["status"],
                              "separate_interpreter_exit": code,
                              "post_relock_direct_delete_rc": rejected.returncode,
                              "locked_after": True}
        else:
            require(code == 2 and decision["status"] == "REFUSED" and
                    not locks.is_locked(native, pkg, env),
                    "POST_BOOT_UNSAFE_RECOVERY_NOT_REFUSED")
            if name == "direct_delete":
                require(decision["reason"] ==
                        "REFUSE_CHANGED_OR_MISSING_PRIVATE_FIXTURE" and
                        locks.fixture_state(native, pkg, env, payload) ==
                        ("ABSENT", None),
                        "POST_BOOT_ABSENT_SYNTHETIC_PKG_FALSE_RECOVERY")
            if name == "tampered_intent":
                require(decision["reason"] ==
                        "DURABLE_RECORD_IDENTITY_NOT_QUALIFIED" and
                        locks.fixture_state(native, pkg, env, payload) ==
                        (OLD, OLD_BYTES), "POST_BOOT_TAMPERED_RECORD_FALSE_RECOVERY")
            outcomes[name] = {"recovery": "REFUSED",
                              "separate_interpreter_exit": code,
                              "locked_after": False}
        verify_original(ARCHIVE, installed, guard)
    # Remove only the EXACT test-owned boot witness, never touch other hooks.
    require(qualified_file(SYSHOOK, 0o755) == BOOT_HOOK_BYTES,
            "BOOT_HOOK_NOT_OWNED_ON_CLEANUP")
    SYSHOOK.unlink()
    require(not SYSHOOK.exists() and not SYSHOOK.is_symlink(),
            "DISPOSABLE_BOOT_HOOK_CLEANUP_FAILED")
    return {
        "schema": 1,
        "status": "OBSERVED_REAL_DISPOSABLE_OPNSENSE_BOOT_PRIVATE_PKG_RECOVERY",
        "actual_guest_boot_id_changed": True,
        "official_start_syshook_executed": True,
        "private_unlocked_native_pkgdb_persisted_across_reboot": True,
        "scenarios": outcomes,
        "old_original_published_service_unchanged": True,
        "boot_hook_removed_after_evidence": True,
        "automatic_recovery_during_boot_implemented": False,
        "power_loss_recovery_tested": False,
        "package_manager_enforced_owner_transaction": False,
        "root_pkg_bypass_unresolved": True,
        "real_running_or_foreign_ipfw_tested": False,
        "real_original_plugin_replaced": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def main():
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in ("prepare", "verify"),
                "PREPARE_OR_VERIFY_MODE_REQUIRED")
        installed = load("stage0-opnsense-installed-predecessor.py")
        guard = load("stage0-opnsense-prepkg-readonly.py")
        native = load("stage0-opnsense-native-pkg-lock.py")
        locks = load("stage0-opnsense-pkg-relock-failures.py")
        orphan = load("stage0-opnsense-pkg-orphaned-unlock.py")
        fresh = load("stage0-opnsense-pkg-fresh-recovery.py")
        if sys.argv[1] == "prepare":
            report = prepare(load("stage0-opnsense-guest-readonly.py"),
                             installed, guard, native, locks, orphan,
                             load("stage0-opnsense-pkg-sidecar-bypass.py"),
                             fresh)
            prefix = "STAGE0_BOOT_PREPARE="
        else:
            report = verify_after_reboot(installed, guard, native, locks,
                                         orphan, fresh)
            prefix = "STAGE0_BOOT_VERIFY="
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            json.JSONDecodeError) as exc:
        print("STAGE0_BOOT=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print(prefix + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
