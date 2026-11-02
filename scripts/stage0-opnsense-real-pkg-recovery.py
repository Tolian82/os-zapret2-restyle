#!/usr/bin/env python3
"""Stage 0: authentic published pkg hook-failure/recovery in disposable OPNsense.

This is a real root pkgdb, genuine immutable 0.6.2_1 archive and genuine hooks.
A forced SAME-VERSION reinstall is not a new-version upgrade, atomic rollback,
RUNNING replacement, or protection against direct privileged pkg bypass.

Never run on a gateway: require opt-in, CI, fresh KVM guest and exact SHA.
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
OPTIN = "ZAPRET2_STAGE0_DISPOSABLE_REAL_PKG_RECOVERY"
REGISTER_HELPER = Path("/usr/local/opnsense/scripts/firmware/register.php")
FAULT_SIGNATURE = "OPNsense plugin registration helper is unavailable"
PACKAGE = "os-zapret2-restyle-0.6.2_1"


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def module(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace(".", "_").replace("-", "_"), HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def qualify_disposable():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "DISPOSABLE_CI_EXPLICIT_OPTIN_REQUIRED")
    guest = module("stage0-opnsense-guest-readonly.py")
    need(guest.evaluate(guest.observe()).get("status") ==
         "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
         "FRESH_OPNSENSE_26_7_KVM_REQUIRED")


def real_pkg_add(archive):
    # Deliberately do not hold FD9 across native pkg: original hook/service
    # re-acquire it. This is a bounded test, NOT an atomic admission protocol.
    need(archive.is_file() and not archive.is_symlink() and
         stat.S_ISREG(archive.lstat().st_mode), "UNQUALIFIED_PKG_ARCHIVE")
    env = dict(os.environ)
    env.pop("FIRMWARE_REGISTER", None)
    env.pop("PKG_DBDIR", None)
    env.pop("PKG_CACHEDIR", None)
    # A real native pkg may sanitize hook environment; never rely on a
    # caller-provided FIRMWARE_REGISTER override as fault evidence.
    try:
        return subprocess.run(
            ["pkg", "-o", "REPO_AUTOUPDATE=false", "add", "-f", str(archive)],
            env=env, capture_output=True, text=True, timeout=180, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_PKG_REINSTALL_UNAVAILABLE_OR_TIMEOUT") from None


def faulted_real_pkg_add(archive):
    """Temporarily remove executable bits from the genuine OPNsense helper.

    Allowed only in a freshly proven disposable KVM guest. The authentic
    historical POST_INSTALL checks -x before using the helper, so this forces
    an observable pre-configd hook failure. Never run on the owner gateway.
    """
    path = REGISTER_HELPER
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and
         info.st_nlink == 1 and info.st_uid == 0 and
         stat.S_IMODE(info.st_mode) & 0o111,
         "REGISTER_HELPER_NOT_UNAMBIGUOUS_ROOT_OWNED_EXECUTABLE")
    owner = subprocess.run(["pkg", "which", "-q", str(path)],
                           capture_output=True, text=True, timeout=20,
                           check=False)
    need(owner.returncode == 0 and
         owner.stdout.strip().split("-")[0] == "opnsense",
         "REGISTER_HELPER_NOT_OWNED_BY_OPNSENSE")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    before = (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_nlink)
    mode = stat.S_IMODE(info.st_mode)
    try:
        os.chmod(path, mode & ~0o111, follow_symlinks=False)
        need(not os.access(path, os.X_OK), "REGISTER_HELPER_FAULT_NOT_ACTIVE")
        return real_pkg_add(archive)
    finally:
        now = path.lstat()
        need(not path.is_symlink() and stat.S_ISREG(now.st_mode) and
             (now.st_dev, now.st_ino, now.st_uid, now.st_gid, now.st_nlink) ==
             before and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
             "REGISTER_HELPER_CHANGED_DURING_FAULT_REFUSE_OVERWRITE")
        os.chmod(path, mode, follow_symlinks=False)
        need(stat.S_IMODE(path.lstat().st_mode) == mode,
             "REGISTER_HELPER_MODE_NOT_RESTORED")


def classify_fault(result):
    output = result.stdout + "\n" + result.stderr
    need(FAULT_SIGNATURE in output,
         "INJECTED_REAL_POST_INSTALL_FAILURE_NOT_OBSERVED:rc=" +
         str(result.returncode))
    return {"pkg_returncode": result.returncode,
            "hook_failure_observed": True,
            "pkg_exit_cannot_prove_transaction_success": True}


def check_success(result):
    need(result.returncode == 0, "COMPENSATING_NATIVE_PKG_FAILED:" +
         str(result.returncode))
    need("os-zapret2-restyle was installed." in result.stdout,
         "COMPENSATING_ORIGINAL_POST_INSTALL_NOT_CONFIRMED")


def snapshot(archive, guard):
    evidence = guard.snapshot(archive)
    need(evidence.get("status") == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
         evidence.get("old_package") == PACKAGE and
         evidence.get("real_old_status") == "STOPPED" and
         evidence.get("safe_pkg_transaction_authorized") is False,
         "ORIGINAL_FD9_OWNER_PROCESS_KERNEL_COLD_GATE_FAILED")
    return evidence


def immutable_config():
    path = Path("/conf/config.xml")
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and
         info.st_nlink == 1, "CONFIG_NOT_REGULAR_OR_UNQUALIFIED")
    return (hashlib.sha256(path.read_bytes()).hexdigest(),
            stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


def same_config(previous):
    need(immutable_config() == previous,
         "ORIGINAL_CONFIG_CHANGED_REFUSE_UNVERIFIED_COMPENSATION")


def hook_allows_fault(archive, original):
    manifest, _ = original.archive_data(archive)
    scripts = manifest.get("scripts", {})
    hook = scripts.get("post-install", "")
    need(isinstance(hook, str) and
         'FIRMWARE_REGISTER="${FIRMWARE_REGISTER:-' in hook and
         "OPNsense plugin registration helper is unavailable" in hook,
         "ARCHIVED_ORIGINAL_POST_INSTALL_NOT_FAULT_INJECTABLE")


def identity(archive, original):
    hostname = original.run("hostname", "-s").decode().strip()
    evidence = original.run_guest(archive, hostname)
    need(evidence.get("status") == "PASS_READ_ONLY_PROVENANCE" and
         evidence.get("package") == PACKAGE,
         "GENUINE_INSTALLED_PKGDB_HOOKS_SERVICE_IDENTITY_FAILED")
    return evidence


def run(archive):
    # No target manipulation until all guest, package and hook identities
    # are authenticated. Actual old pkg is installed only on fresh KVM CI.
    qualify_disposable()
    installer = module("stage0-opnsense-installed-predecessor.py")
    guard = module("stage0-opnsense-prepkg-readonly.py")
    original = module("stage0-installed-predecessor-readonly.py")
    hook_allows_fault(archive, original)
    installer.install_and_verify(archive)
    before = identity(archive, original)
    config = immutable_config()
    snapshot(archive, guard)
    fault = faulted_real_pkg_add(archive)
    injected = classify_fault(fault)
    # Even if pkg returned zero, check the actual persisted pkgdb and
    # old service/FD9, absence of ambiguous processes and unloaded IPFW.
    # Never blindly re-add after a partial/foreign process or kernel state.
    need(identity(archive, original) == before,
         "INJECTED_FAILURE_CHANGED_INSTALLED_PREDECESSOR_PROVENANCE")
    same_config(config)
    snapshot(archive, guard)
    need(hashlib.sha256(archive.read_bytes()).hexdigest() ==
         original.ARCHIVE_SHA, "ARCHIVE_CHANGED_BEFORE_COMPENSATION")
    restored = real_pkg_add(archive)
    check_success(restored)
    need(identity(archive, original) == before,
         "COMPENSATION_DID_NOT_RESTORE_EXACT_OLD_PKGDB_AND_SERVICE")
    same_config(config)
    snapshot(archive, guard)
    return {"schema": 1,
            "status": "PASS_REAL_ARCHIVED_PKG_HOOK_FAILURE_AND_REINSTALL",
            "archive_sha256": original.ARCHIVE_SHA,
            "real_published_old_package": PACKAGE,
            "real_pkgdb_mutated_and_compensated": True,
            "real_original_hook_injected_failure": injected,
            "opnsense_register_helper_mode_restored": True,
            "final_pkg_returncode": restored.returncode,
            "final_service_status": "STOPPED",
            "fd9_owner_process_and_cold_ipfw_rechecked": True,
            "same_version_forced_reinstall_only": True,
            "real_new_version_successor_tested": False,
            "running_replacement_tested": False,
            "atomic_pkg_rollback_proved": False,
            "direct_root_pkg_bypass_excluded": False,
            "stage0_closed": False}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("STAGE0_REAL_PKG_RECOVERY=REFUSED:EXACT_ARCHIVE_REQUIRED",
              file=sys.stderr)
        return 2
    try:
        report = run(Path(args[0]))
    except (Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        print("STAGE0_REAL_PKG_RECOVERY=REFUSED:" + str(exc),
              file=sys.stderr)
        return 2
    print("STAGE0_REAL_PKG_RECOVERY=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
