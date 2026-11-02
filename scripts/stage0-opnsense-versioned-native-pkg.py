#!/usr/bin/env python3
"""Stage0 disposable OPNsense: real native pkgdb version transition + fault recovery.

A version-distinct, byte-preserving test-only archive is derived from the
immutable published 0.6.2_1 package. This does NOT qualify the official
Mk/plugins.mk builder or a new production successor. Only isolated KVM CI.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
NAME = "os-zapret2-restyle"
OLD_VERSION = "0.6.2_1"
TEST_VERSION = "0.6.2_56"
OPTIN = "ZAPRET2_STAGE0_DISPOSABLE_VERSIONED_PKG_TEST"


class Refusal(Exception):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace(".", "_").replace("-", "_"), HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def command(args, timeout=180):
    try:
        return subprocess.run(args, check=False, capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_COMMAND_FAILED_OR_TIMEOUT:" + args[0]) from None


def qualify():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "DISPOSABLE_KVM_CI_OPTIN_AND_FREEBSD_ROOT_REQUIRED")
    guest = load("stage0-opnsense-guest-readonly.py")
    need(guest.evaluate(guest.observe()).get("status") ==
         "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
         "FRESH_26_7_OPNSENSE_GUEST_UNQUALIFIED")


def compare_manifest(original, candidate):
    need(candidate.get("name") == NAME and candidate.get("version") == TEST_VERSION,
         "TEST_ARCHIVE_IDENTITY_MISMATCH")
    for field in ("origin", "arch", "abi", "prefix"):
        need(candidate.get(field) == original.get(field),
             "TEST_ARCHIVE_PROVENANCE_CHANGED:" + field)
    need(isinstance(original.get("scripts"), dict) and
         set(original["scripts"]) ==
         {"pre-install", "post-install", "pre-deinstall", "post-deinstall"} and
         candidate.get("scripts") == original["scripts"],
         "TEST_ARCHIVE_ORIGINAL_HOOKS_CHANGED")
    need(candidate.get("files") == original.get("files") and
         isinstance(original.get("files"), dict) and bool(original["files"]),
         "TEST_ARCHIVE_FILE_MANIFEST_CHANGED")
    need(candidate.get("deps") == original.get("deps"),
         "TEST_ARCHIVE_DEPENDENCIES_CHANGED:old=" +
         json.dumps(original.get("deps"), sort_keys=True)[:350] +
         ":created=" + json.dumps(candidate.get("deps"), sort_keys=True)[:350])


def build_test_successor(archive, work, old):
    """A test artifact with genuine published payload and exactly original hooks."""
    original, old_service = old.archive_data(archive)  # pinned SHA-256
    need(original.get("version") == OLD_VERSION and
         original.get("name") == NAME, "PUBLISHED_ARCHIVE_VERSION_UNQUALIFIED")
    need(isinstance(original.get("files"), dict) and
         len(original["files"]) > 15, "PUBLISHED_ARCHIVE_FILE_LIST_MISSING")
    root = work / "stage"
    dest = work / "packages"
    root.mkdir(mode=0o700)
    dest.mkdir(mode=0o700)
    # The original archive's bytes and manifest are already authenticated;
    # untrusted arbitrary archive extraction is not permitted.
    extracted = command(["tar", "-xpf", str(archive), "-C", str(root)])
    need(extracted.returncode == 0, "PINNED_ARCHIVE_EXTRACT_FAILED")
    original_path = root / old.SERVICE.lstrip("/")
    need(original_path.is_file() and not original_path.is_symlink() and
         stat.S_IMODE(original_path.lstat().st_mode) == 0o755 and
         original_path.read_bytes() == old_service,
         "DERIVED_STAGING_SERVICE_NOT_AUTHENTIC")
    candidate = dict(original)
    candidate["version"] = TEST_VERSION
    # Preserve original install payload, dependencies and four hook bodies.
    # The result exercises pkg version replacement, not new runtime behavior.
    compare_manifest(original, candidate)
    m = work / "successor-manifest.json"
    m.write_text(json.dumps(candidate, sort_keys=True), encoding="utf-8")
    made = command(["pkg", "create", "-M", str(m), "-r", str(root), "-o", str(dest)])
    need(made.returncode == 0,
         "NATIVE_SUCCESSOR_PACKAGE_CREATION_FAILED:" +
         (made.stdout + made.stderr)[-450:])
    package = dest / (NAME + "-" + TEST_VERSION + ".pkg")
    need(package.is_file() and not package.is_symlink(),
         "NATIVE_VERSIONED_SUCCESSOR_ARCHIVE_MISSING")
    raw = command(["tar", "-xOf", str(package), "+MANIFEST"])
    need(raw.returncode == 0, "DERIVED_ARCHIVE_MANIFEST_UNAVAILABLE")
    try:
        actual = json.loads(raw.stdout)
    except ValueError:
        raise Refusal("DERIVED_ARCHIVE_MANIFEST_INVALID") from None
    compare_manifest(original, actual)
    sha = hashlib.sha256(package.read_bytes()).hexdigest()
    return package, sha, old_service, original


def installed_successor(archive, sha, service_bytes, original, old, inspector):
    need(hashlib.sha256(archive.read_bytes()).hexdigest() == sha,
         "DERIVED_ARCHIVE_CHANGED")
    record = command(["pkg", "info", "-R", "--raw-format", "json", NAME])
    need(record.returncode == 0, "NEW_VERSION_PKGDB_MISSING")
    current = old.installed_manifest_from_json(record.stdout)
    # Test-only generated package uses exactly the previous hooks/files.
    compare_manifest(original, current)
    service = Path(old.SERVICE)
    info = service.lstat()
    need(stat.S_ISREG(info.st_mode) and not service.is_symlink() and
         stat.S_IMODE(info.st_mode) == 0o755 and
         service.read_bytes() == service_bytes,
         "SUCCESSOR_INSTALLED_SERVICE_NOT_IDENTICAL")
    owner = command(["pkg", "which", "-q", old.SERVICE])
    need(owner.returncode == 0 and owner.stdout.strip() in
         (NAME, NAME + "-" + TEST_VERSION), "SUCCESSOR_SERVICE_OWNER_UNKNOWN")
    # The real original Status acquires FD9 itself. Never keep an outer
    # lockf around it, nor carry FD9 into pkg hooks.
    fd9 = load("stage0-opnsense-old-service-fd9.py")
    with tempfile.TemporaryDirectory(prefix="stage0-native-successor-fd9-") as td:
        observed = fd9.call_status(Path(td) / "lock")
    need(observed.returncode == 1 and
         observed.stdout.strip() == inspector.STOPPED_TEXT,
         "SUCCESSOR_SERVICE_NOT_PROVEN_STOPPED:" + str(observed.returncode))
    inspector.check_no_owners((inspector.JOURNAL, *inspector.MARKERS,
                               *inspector.PIDFILES, inspector.PENDING_EXTRA))
    inspector.check_process_census(inspector.checked_process_census())
    ipfw = inspector.command(["/sbin/ipfw", "-q", "list"])
    inspector.check_kernel_cold(
        inspector.command(["/sbin/kldstat", "-q", "-m", "ipfw"]).returncode,
        inspector.command(["/sbin/kldstat", "-q", "-m", "ipdivert"]).returncode,
        ipfw.returncode, ipfw.stdout + ipfw.stderr)
    return {"installed_version": TEST_VERSION, "old_hooks_unchanged": True,
            "real_service_fd9_stopped": True, "kernel_unloaded_cold": True}


def run(archive):
    qualify()
    installer = load("stage0-opnsense-installed-predecessor.py")
    old = load("stage0-installed-predecessor-readonly.py")
    inspector = load("stage0-opnsense-prepkg-readonly.py")
    pkg = load("stage0-opnsense-real-pkg-recovery.py")
    installer.install_and_verify(archive)
    hostname = old.run("hostname", "-s").decode().strip()
    initial = old.run_guest(archive, hostname)
    need(initial.get("status") == "PASS_READ_ONLY_PROVENANCE",
         "ORIGINAL_INSTALLED_PACKAGE_NOT_PROVEN")
    original_config = pkg.immutable_config()
    pkg.snapshot(archive, inspector)
    with tempfile.TemporaryDirectory(prefix="stage0-versioned-native-pkg-") as td:
        successor, digest, service, original = build_test_successor(
            archive, Path(td), old)
        need(old.run_guest(archive, hostname) == initial,
             "SUCCESSOR_BUILD_MUTATED_ORIGINAL_PKG")
        # Positive version transfer: real native pkg and original install hooks.
        normal = pkg.real_pkg_add(successor)
        pkg.check_success(normal)
        positive = installed_successor(
            successor, digest, service, original, old, inspector)
        pkg.same_config(original_config)
        # Compensate the successful test-only version transition to old.
        back = pkg.real_pkg_add(archive)
        pkg.check_success(back)
        need(old.run_guest(archive, hostname) == initial,
             "POSITIVE_TRANSITION_ORIGINAL_ROLLBACK_FAILED")
        pkg.same_config(original_config)
        pkg.snapshot(archive, inspector)
        # The exact same new-version archive now encounters a genuine
        # post-install helper failure; actual pkgdb may still advance.
        failed = pkg.faulted_real_pkg_add(successor)
        observed = pkg.classify_fault(failed)
        after_fault = installed_successor(
            successor, digest, service, original, old, inspector)
        pkg.same_config(original_config)
        # Independently admitted compensation, not native pkg atomicity.
        need(hashlib.sha256(archive.read_bytes()).hexdigest() ==
             old.ARCHIVE_SHA, "OLD_ARCHIVE_CHANGED_BEFORE_COMPENSATION")
        restored = pkg.real_pkg_add(archive)
        pkg.check_success(restored)
        need(old.run_guest(archive, hostname) == initial,
             "FAILED_SUCCESSOR_ORIGINAL_COMPENSATION_FAILED")
        pkg.same_config(original_config)
        pkg.snapshot(archive, inspector)
    return {"schema": 1, "status": "PASS_TEST_ONLY_VERSIONED_NATIVE_PKG_REPLACEMENT",
            "published_old_package": NAME + "-" + OLD_VERSION,
            "test_only_derived_successor_version": TEST_VERSION,
            "test_successor_sha256": digest,
            "successful_new_version_install": positive,
            "failed_new_version_hook": observed,
            "pkgdb_after_hook_failure": after_fault,
            "compensation_restored_exact_old_provenance": True,
            "original_config_unchanged": True,
            "real_cold_fd9_process_ipfw_verified": True,
            "official_native_opnsense_build_tested": False,
            "production_new_code_successor_tested": False,
            "running_replacement_tested": False,
            "crash_atomicity_proved": False,
            "direct_root_pkg_bypass_excluded": False,
            "stage0_closed": False}


def main():
    if len(sys.argv) != 2:
        print("STAGE0_VERSIONED_PKG=REFUSED:PINNED_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        report = run(Path(sys.argv[1]))
    except (Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        print("STAGE0_VERSIONED_PKG=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_VERSIONED_PKG=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
